# Qwen2.5-VL 파인튜닝 방법론 가이드

## 개요

이 문서는 img2dwg 프로젝트를 위한 Qwen2.5-VL-7B-Instruct 모델의 파인튜닝 방법론을 정리한 것입니다.

## 주요 참고 자료

- **공식 GitHub**: https://github.com/2U1/Qwen2-VL-Finetune
- **Qwen 공식 문서**: https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct
- **Roboflow 가이드**: https://blog.roboflow.com/fine-tune-qwen-2-5/
- **F22Labs 가이드**: https://www.f22labs.com/blogs/complete-guide-to-fine-tuning-qwen2-5-vl-model/

## 파인튜닝 방법

### 1. Full Fine-tuning
모든 모델 파라미터를 업데이트하는 방식으로, 최고의 성능을 얻을 수 있지만 가장 많은 GPU 메모리를 필요로 합니다.

**명령어**: `bash scripts/finetune.sh`

**GPU 메모리 요구사항**: 
- 7B 모델: 약 60-80GB (H100 80GB에서 가능)
- 배치 크기 조정으로 메모리 사용량 조절 가능

### 2. LoRA Fine-tuning (추천)
Low-Rank Adaptation을 사용하여 일부 파라미터만 학습하는 방식으로, 메모리 효율적이면서도 좋은 성능을 제공합니다.

**명령어**: `bash scripts/finetune_lora.sh`

**GPU 메모리 요구사항**: 
- 7B 모델: 약 30-40GB
- H100 80GB에서 충분히 가능

**LoRA 설정 파라미터**:
- `--lora_enable`: LoRA 활성화
- `--lora_rank`: LoRA rank (기본값: 128, 범위: 8-256)
- `--lora_alpha`: LoRA alpha (기본값: 256, 일반적으로 rank의 2배)
- `--lora_dropout`: LoRA dropout (기본값: 0.05)

### 3. LoRA with Vision Fine-tuning
비전 인코더까지 LoRA로 파인튜닝하는 방식입니다.

**명령어**: `bash scripts/finetune_lora_vision.sh`

**추가 옵션**:
- `--vision_lora`: 비전 인코더에도 LoRA 적용
- `--vision_lr`: 비전 인코더 학습률 (일반적으로 언어 모델보다 낮게 설정)

### 4. QLoRA Fine-tuning
양자화된 모델에 LoRA를 적용하여 메모리를 더욱 절약하는 방식입니다.

**설정 방법**:
- `--bits 4` 또는 `--bits 8`: 4비트 또는 8비트 양자화

**GPU 메모리 요구사항**: 
- 7B 모델 (4-bit): 약 20-25GB
- 7B 모델 (8-bit): 약 25-30GB

## 데이터셋 포맷

### 단일 이미지 데이터

```json
{
  "id": "project_001",
  "image": "path/to/image.jpg",
  "conversations": [
    {
      "from": "human",
      "value": "<image>\n다음 평면도 이미지를 분석하여 CAD 엔티티를 추출해주세요."
    },
    {
      "from": "gpt",
      "value": "{\"metadata\": {...}, \"entities\": [...]}"
    }
  ]
}
```

### 다중 이미지 데이터 (img2dwg 프로젝트에 적합)

```json
{
  "id": "project_001_change",
  "image": [
    "path/to/before.jpg",
    "path/to/after.jpg"
  ],
  "conversations": [
    {
      "from": "human",
      "value": "<image>\n<image>\n다음은 건축 평면도의 변경 전/후 이미지입니다. 이 이미지들을 분석하여 CAD 엔티티를 추출해주세요."
    },
    {
      "from": "gpt",
      "value": "{\"metadata\": {\"type\": \"변경\", \"project\": \"project_001\"}, \"entities\": [...]}"
    }
  ]
}
```

### 비디오 데이터 (선택사항)

```json
{
  "id": "project_video_001",
  "video": "path/to/video.mp4",
  "conversations": [
    {
      "from": "human",
      "value": "<video>\n이 비디오에서 무슨 일이 일어나고 있나요?"
    },
    {
      "from": "gpt",
      "value": "비디오 설명..."
    }
  ]
}
```

## 하이퍼파라미터 설정

### 기본 학습 파라미터

```bash
# 학습률
--learning_rate 2e-5           # 언어 모델 학습률
--vision_lr 2e-6               # 비전 인코더 학습률 (vision LoRA 사용 시)
--merger_lr 2e-5               # 프로젝터 학습률

# 배치 크기
--per_device_train_batch_size 2
--per_device_eval_batch_size 2
--gradient_accumulation_steps 8  # 실제 배치 크기 = 2 * 8 = 16

# 에포크 및 스텝
--num_train_epochs 3
--save_steps 500
--eval_steps 500
--logging_steps 10

# 최적화
--optim "adamw_torch"
--warmup_ratio 0.03
--weight_decay 0.0
--max_grad_norm 1.0

# 시퀀스 길이
--max_seq_length 8192          # 기본 8K, 필요시 16K 또는 32K로 증가
```

### LoRA 파라미터

```bash
# LoRA 설정
--lora_enable True
--lora_rank 128                # 작을수록 메모리 절약, 클수록 성능 향상
--lora_alpha 256               # 일반적으로 rank의 2배
--lora_dropout 0.05

# Vision LoRA (선택사항)
--vision_lora True
--vision_lora_rank 64          # 비전 인코더는 더 작은 rank 사용
--vision_lora_alpha 128
```

### 이미지/비디오 설정

```bash
# 이미지 크기 조정
--min_pixels 256*28*28         # 최소 픽셀 수
--max_pixels 1024*28*28        # 최대 픽셀 수

# 또는 고정 크기 지정
--image_resized_width 1024
--image_resized_height 1024

# 비디오 설정 (사용 시)
--video_fps 1                  # 초당 프레임 수
--video_resized_width 1024
--video_resized_height 1024
```

### 메모리 최적화

```bash
# Flash Attention 2 사용
--disable_flash_attn2 False

# Gradient Checkpointing
--gradient_checkpointing True

# Liger Kernel 사용 (메모리 효율 향상)
--use_liger True

# 양자화 (QLoRA)
--bits 4                       # 4비트 양자화
```

## 학습 스크립트 예시

### LoRA 파인튜닝 스크립트 (finetune_lora.sh)

```bash
#!/bin/bash

MODEL_PATH="Qwen/Qwen2.5-VL-7B-Instruct"
DATA_PATH="output/finetune_train.json"
OUTPUT_DIR="output/checkpoints/qwen2.5-vl-7b-lora"

deepspeed src/training/train.py \
    --deepspeed scripts/zero2.json \
    --model_name_or_path $MODEL_PATH \
    --data_path $DATA_PATH \
    --image_folder output/images \
    --output_dir $OUTPUT_DIR \
    --num_train_epochs 3 \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --gradient_accumulation_steps 8 \
    --evaluation_strategy "steps" \
    --eval_steps 500 \
    --save_strategy "steps" \
    --save_steps 500 \
    --save_total_limit 3 \
    --learning_rate 2e-5 \
    --weight_decay 0.0 \
    --warmup_ratio 0.03 \
    --lr_scheduler_type "cosine" \
    --logging_steps 10 \
    --model_max_length 8192 \
    --gradient_checkpointing True \
    --dataloader_num_workers 4 \
    --bf16 True \
    --report_to "tensorboard" \
    --lora_enable True \
    --lora_rank 128 \
    --lora_alpha 256 \
    --lora_dropout 0.05 \
    --use_liger True \
    --disable_flash_attn2 False
```

## img2dwg 프로젝트 적용 방안

### 1. 데이터셋 변환

현재 img2dwg 프로젝트의 JSONL 포맷을 Qwen2.5-VL 포맷으로 변환해야 합니다.

**현재 포맷 (OpenAI 스타일)**:
```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": [...]},
    {"role": "assistant", "content": "{...}"}
  ]
}
```

**Qwen2.5-VL 포맷**:
```json
{
  "id": "unique_id",
  "image": ["url1", "url2"],
  "conversations": [
    {"from": "human", "value": "<image>\n<image>\n..."},
    {"from": "gpt", "value": "{...}"}
  ]
}
```

### 2. 이미지 처리

- **이미지 URL**: GitHub raw URL을 그대로 사용 가능
- **로컬 이미지**: 상대 경로 또는 절대 경로 지정
- **다중 이미지**: 리스트로 제공

### 3. 시스템 프롬프트 통합

시스템 프롬프트를 user 메시지의 텍스트 부분에 통합:

```python
system_prompt = "당신은 2D 건축 평면도 이미지를 분석하여 AutoCAD 호환 JSON 형태로 변환하는 전문가입니다."
user_text = "다음은 건축 평면도의 변경 전/후 이미지입니다. 이 이미지들을 분석하여 CAD 엔티티를 추출해주세요."

combined_text = f"{system_prompt}\n\n{user_text}"
```

### 4. JSON 출력 보장

Qwen2.5-VL은 구조화된 출력을 지원하므로, 학습 시 일관된 JSON 포맷을 사용하면 추론 시에도 JSON을 출력합니다.

**추가 옵션**: Outlines 라이브러리를 사용하여 JSON 스키마 강제 가능

```python
import outlines
from pydantic import BaseModel

class DWGOutput(BaseModel):
    metadata: dict
    entities: list

generator = outlines.generate.json(model, DWGOutput)
```

## 학습 프로세스

### 1. 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt

# 또는 conda 환경
conda env create -f environment.yaml
conda activate qwen2vl
```

### 2. 데이터 준비

```bash
# img2dwg 데이터셋을 Qwen2.5-VL 포맷으로 변환
python scripts/convert_dataset_to_qwen_format.py \
    --input output/finetune_train.jsonl \
    --output output/qwen_train.json
```

### 3. 학습 실행

```bash
# LoRA 파인튜닝 (추천)
bash scripts/finetune_lora.sh

# 또는 Full 파인튜닝
bash scripts/finetune.sh
```

### 4. 학습 모니터링

```bash
# TensorBoard로 모니터링
tensorboard --logdir output/checkpoints/qwen2.5-vl-7b-lora
```

### 5. LoRA 가중치 병합 (선택사항)

```bash
# LoRA 가중치를 베이스 모델과 병합
bash scripts/merge_lora.sh
```

### 6. 추론 테스트

```python
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
import torch

model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    "output/checkpoints/qwen2.5-vl-7b-lora",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")

# 추론 코드...
```

## 고급 기능

### 1. DPO (Direct Preference Optimization)

선호도 기반 학습으로 모델 출력 품질 향상:

```bash
bash scripts/finetune_dpo.sh
```

### 2. GRPO (Group Relative Policy Optimization)

강화학습 기반 파인튜닝:

```bash
bash scripts/finetune_grpo.sh
```

### 3. Classification Fine-tuning

분류 작업을 위한 파인튜닝:

```bash
bash scripts/finetune_cls.sh
```

### 4. DoRA (Weight-Decomposed Low-Rank Adaptation)

LoRA의 개선 버전으로 더 나은 성능:

```bash
--use_dora True
```

## 주의사항 및 팁

### 메모리 관리

1. **배치 크기 조정**: OOM 에러 발생 시 `per_device_train_batch_size` 감소
2. **Gradient Accumulation**: 배치 크기를 줄이고 accumulation steps 증가
3. **Gradient Checkpointing**: 메모리 절약, 학습 속도 약간 감소
4. **Flash Attention 2**: 메모리 효율 및 속도 향상
5. **Liger Kernel**: 추가 메모리 최적화

### 학습률 설정

- **언어 모델**: 2e-5 ~ 5e-5
- **비전 인코더**: 2e-6 ~ 5e-6 (언어 모델의 1/10)
- **프로젝터**: 2e-5 ~ 5e-5

### 컨텍스트 길이

- **기본**: 8K 토큰 (대부분의 경우 충분)
- **긴 문서**: 16K 또는 32K 토큰
- **메모리 고려**: 컨텍스트 길이가 길수록 메모리 사용량 증가

### 이미지 해상도

- **낮은 해상도**: 256×28×28 ~ 512×28×28 (빠른 학습)
- **중간 해상도**: 512×28×28 ~ 1024×28×28 (균형)
- **높은 해상도**: 1024×28×28 ~ 2048×28×28 (최고 품질)

## 예상 학습 시간

### H100 80GB 기준

- **LoRA (7B)**: 
  - 400 샘플, 3 epochs: 약 2-3시간
  - 1000 샘플, 3 epochs: 약 6-8시간
  
- **Full Fine-tuning (7B)**:
  - 400 샘플, 3 epochs: 약 6-8시간
  - 1000 샘플, 3 epochs: 약 15-20시간

- **QLoRA (7B, 4-bit)**:
  - 400 샘플, 3 epochs: 약 3-4시간
  - 1000 샘플, 3 epochs: 약 8-10시간

## 참고 자료

- **Qwen2.5-VL 공식 문서**: https://qwenlm.github.io/blog/qwen2.5-vl/
- **Transformers 문서**: https://huggingface.co/docs/transformers/model_doc/qwen2_5_vl
- **LoRA 논문**: https://arxiv.org/abs/2106.09685
- **QLoRA 논문**: https://arxiv.org/abs/2305.14314
- **Liger Kernel**: https://github.com/linkedin/Liger-Kernel
