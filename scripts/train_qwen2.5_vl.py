#!/usr/bin/env python
# coding=utf-8
"""Qwen2.5-VL 모델 파인튜닝 스크립트."""

import logging
import os
import sys
import json
from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence
from io import BytesIO

import torch
import transformers
from torch.utils.data import Dataset
from transformers import HfArgumentParser, Trainer
from PIL import Image
import requests

from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers.trainer_utils import get_last_checkpoint

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from img2dwg.utils.logger import setup_logging

logger = logging.getLogger(__name__)

IGNORE_INDEX = -100
DEFAULT_IMAGE_TOKEN = "<image>"

# --- 데이터 클래스 정의 ---
@dataclass
class ModelArguments:
    model_name_or_path: Optional[str] = field(default="Qwen/Qwen2.5-VL-7B-Instruct")
    bits: int = field(default=16, metadata={"help": "Quantization bits for training (16, 8, 4)"})

@dataclass
class DataArguments:
    data_path: str = field(default=None, metadata={"help": "Path to the training data."})
    image_folder: Optional[str] = field(default=None, metadata={"help": "Path to the image folder."})

@dataclass
class TrainingArguments(transformers.TrainingArguments):
    cache_dir: Optional[str] = field(default=None)
    optim: str = field(default="adamw_torch")
    model_max_length: int = field(default=8192, metadata={"help": "Maximum sequence length."})
    lora_enable: bool = field(default=True, metadata={"help": "Enable LoRA fine-tuning."})
    lora_rank: int = field(default=128, metadata={"help": "LoRA rank."})
    lora_alpha: int = field(default=256, metadata={"help": "LoRA alpha."})
    lora_dropout: float = field(default=0.05, metadata={"help": "LoRA dropout."})

# --- 데이터셋 및 콜레이터 --- 
class LazySupervisedDataset(Dataset):
    """Dataset for supervised fine-tuning.
    It loads data and images lazily to save memory.
    """
    def __init__(self, data_path: str, tokenizer: transformers.PreTrainedTokenizer, processor: transformers.ProcessorMixin, data_args: DataArguments):
        super(LazySupervisedDataset, self).__init__()
        try:
            with open(data_path, "r") as f:
                self.list_data_dict = json.load(f)
        except json.JSONDecodeError:
            # Handle JSONL format
            with open(data_path, "r") as f:
                self.list_data_dict = [json.loads(line) for line in f]

        self.tokenizer = tokenizer
        self.processor = processor
        self.data_args = data_args

    def __len__(self):
        return len(self.list_data_dict)

    def __getitem__(self, i) -> Dict[str, torch.Tensor]:
        source = self.list_data_dict[i]

        # 데이터 포맷 변환 (OpenAI -> Qwen)
        raw_messages = source["messages"]
        system_prompt = ""
        if raw_messages[0]["role"] == "system":
            system_prompt = raw_messages[0]["content"] + "\n\n"
            raw_messages = raw_messages[1:]

        # Qwen-VL 포맷에 맞게 대화 구성
        text_chunks = []
        images = []
        for msg in raw_messages:
            if msg["role"] == "user":
                content = msg["content"]
                if isinstance(content, list):
                    for item in content:
                        if item["type"] == "text":
                            text_chunks.append(item["text"])
                        elif item["type"] == "image_url":
                            url = item["image_url"]["url"]
                            if url.startswith("http"):
                                response = requests.get(url)
                                image = Image.open(BytesIO(response.content)).convert("RGB")
                            else: # 로컬 파일 경로
                                image_path = os.path.join(self.data_args.image_folder, os.path.basename(url))
                                image = Image.open(image_path).convert("RGB")
                            images.append(image)
                            text_chunks.append(DEFAULT_IMAGE_TOKEN)
                else:
                    text_chunks.append(content)
            elif msg["role"] == "assistant":
                text_chunks.append(msg["content"])

        # 시스템 프롬프트를 첫 user 메시지에 추가
        if text_chunks:
            text_chunks[0] = system_prompt + text_chunks[0]

        # 대화를 단일 문자열로 결합 (Qwen-VL 템플릿 적용 필요)
        # 여기서는 간단히 결합. 실제로는 tokenizer.apply_chat_template 사용 권장
        full_text = "\n".join(text_chunks)

        # 이미지 처리
        image_tensors = None
        if images:
            image_tensors = self.processor(images=images, return_tensors=\'pt\')["pixel_values"]

        # 토크나이징
        inputs = self.tokenizer(full_text, return_tensors="pt", padding="max_length", max_length=self.tokenizer.model_max_length, truncation=True)
        input_ids = inputs.input_ids[0]
        labels = input_ids.clone()

        # TODO: 레이블에서 user 프롬프트 부분 마스킹 (IGNORE_INDEX)
        # 이 부분은 정확한 템플릿 적용 후, assistant 응답 부분만 학습하도록 구현해야 함

        return dict(
            input_ids=input_ids,
            labels=labels,
            pixel_values=image_tensors
        )

@dataclass
class DataCollatorForSupervisedDataset(object):
    tokenizer: transformers.PreTrainedTokenizer

    def __call__(self, instances: Sequence[Dict]) -> Dict[str, torch.Tensor]:
        input_ids, labels = tuple([instance[key] for instance in instances] for key in ("input_ids", "labels"))
        input_ids = torch.nn.utils.rnn.pad_sequence(input_ids, batch_first=True, padding_value=self.tokenizer.pad_token_id)
        labels = torch.nn.utils.rnn.pad_sequence(labels, batch_first=True, padding_value=IGNORE_INDEX)

        batch = dict(
            input_ids=input_ids,
            labels=labels,
            attention_mask=input_ids.ne(self.tokenizer.pad_token_id),
        )

        if "pixel_values" in instances[0] and instances[0]["pixel_values"] is not None:
            pixel_values = [instance["pixel_values"] for instance in instances]
            # 이미지 텐서들을 단일 텐서로 결합 (필요 시)
            # 현재는 리스트로 전달. Trainer가 내부적으로 처리할 수 있음.
            batch["pixel_values"] = pixel_values

        return batch

# --- 메인 학습 함수 ---
def main():
    parser = HfArgumentParser((ModelArguments, DataArguments, TrainingArguments))
    model_args, data_args, training_args = parser.parse_args_into_dataclasses()

    # 로깅 설정
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_level="INFO", log_file=os.path.join(log_dir, "train_qwen2.5_vl.log"))
    logger.info(f"Training/evaluation parameters {training_args}")

    # 마지막 체크포인트 확인
    last_checkpoint = None
    if os.path.isdir(training_args.output_dir) and training_args.do_train and not training_args.overwrite_output_dir:
        last_checkpoint = get_last_checkpoint(training_args.output_dir)
        if last_checkpoint is None and len(os.listdir(training_args.output_dir)) > 0:
            raise ValueError(f"Output directory ({training_args.output_dir}) already exists and is not empty.")
        elif last_checkpoint is not None:
            logger.info(f"Checkpoint detected, resuming training at {last_checkpoint}.")

    # 모델, 토크나이저, 프로세서 로딩
    logger.info("Loading model, tokenizer, and processor...")
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        model_args.model_name_or_path, cache_dir=training_args.cache_dir, model_max_length=training_args.model_max_length, padding_side="right", use_fast=False
    )
    processor = transformers.AutoProcessor.from_pretrained(model_args.model_name_or_path, cache_dir=training_args.cache_dir)

    model_load_kwargs = {
        "low_cpu_mem_usage": True,
        "torch_dtype": torch.bfloat16 if training_args.bf16 else torch.float32,
        "cache_dir": training_args.cache_dir,
    }

    if model_args.bits in [4, 8]:
        logger.info(f"Quantizing model to {model_args.bits} bits")
        model_load_kwargs.update({
            "quantization_config": transformers.BitsAndBytesConfig(
                load_in_4bit=model_args.bits == 4,
                load_in_8bit=model_args.bits == 8,
                bnb_4bit_compute_dtype=torch.bfloat16 if training_args.bf16 else torch.float32,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            ),
            "device_map": "auto",
        })

    model = transformers.Qwen2_5_VLForConditionalGeneration.from_pretrained(model_args.model_name_or_path, **model_load_kwargs)

    if model_args.bits in [4, 8]:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=training_args.gradient_checkpointing)

    if training_args.lora_enable:
        logger.info("Adding LoRA adapters...")
        lora_config = LoraConfig(
            r=training_args.lora_rank, lora_alpha=training_args.lora_alpha, 
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            lora_dropout=training_args.lora_dropout, bias="none", task_type="CAUSAL_LM"
        )
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

    # 데이터셋 생성
    logger.info("Creating dataset...")
    train_dataset = LazySupervisedDataset(data_path=data_args.data_path, tokenizer=tokenizer, processor=processor, data_args=data_args)
    data_collator = DataCollatorForSupervisedDataset(tokenizer=tokenizer)

    # 트레이너 설정
    trainer = Trainer(
        model=model, tokenizer=tokenizer, args=training_args, 
        train_dataset=train_dataset, eval_dataset=None, 
        data_collator=data_collator
    )

    # 학습 시작
    if training_args.do_train:
        logger.info("*** Starting Training ***")
        trainer.train(resume_from_checkpoint=last_checkpoint)
        trainer.save_model() # LoRA 가중치 저장
        trainer.save_state()

    logger.info("Training finished successfully.")

if __name__ == "__main__":
    main()

