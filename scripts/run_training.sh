#!/bin/bash

# --- 환경 변수 설정 ---
export WANDB_PROJECT="img2dwg-qwen2.5-vl"
export WANDB_DISABLED="true" # wandb 사용 안함

# --- 모델 및 데이터 경로 ---
MODEL_NAME="Qwen/Qwen2.5-VL-7B-Instruct"
DATA_DIR="output"
TRAIN_FILE="${DATA_DIR}/finetune_train.jsonl"
IMAGE_DIR="${DATA_DIR}/images/finetune"
OUTPUT_DIR="output/checkpoints/qwen2.5-vl-7b-lora-finetune"

# --- 데이터셋 변환 ---
CONVERTED_DATA_FILE="${DATA_DIR}/qwen_finetune_train.json"

if [ ! -f "$CONVERTED_DATA_FILE" ]; then
    echo "--- Converting dataset to Qwen-VL format ---"
    python scripts/convert_dataset_to_qwen_format.py \
        --input_file "$TRAIN_FILE" \
        --output_file "$CONVERTED_DATA_FILE"
else
    echo "--- Converted dataset already exists. Skipping conversion. ---"
fi

# --- 학습 파라미터 ---
NUM_EPOCHS=3
BATCH_SIZE=1
GRAD_ACCUM_STEPS=16
LEARNING_RATE=2e-5
LORA_RANK=128
LORA_ALPHA=256
LORA_DROPOUT=0.05
MAX_LENGTH=8192

# --- DeepSpeed 설정 파일 ---
DEEPSPEED_CONFIG="scripts/zero2.json"

# --- 학습 실행 ---
echo "--- Starting Qwen2.5-VL Fine-tuning ---"

deepspeed --include localhost:0,1,2,3 --master_port 29501 scripts/train_qwen2.5_vl.py \
    --deepspeed "$DEEPSPEED_CONFIG" \
    --model_name_or_path "$MODEL_NAME" \
    --data_path "$CONVERTED_DATA_FILE" \
    --image_folder "$IMAGE_DIR" \
    --output_dir "$OUTPUT_DIR" \
    --num_train_epochs "$NUM_EPOCHS" \
    --per_device_train_batch_size "$BATCH_SIZE" \
    --gradient_accumulation_steps "$GRAD_ACCUM_STEPS" \
    --evaluation_strategy "no" \
    --save_strategy "steps" \
    --save_steps 500 \
    --save_total_limit 3 \
    --learning_rate "$LEARNING_RATE" \
    --weight_decay 0.0 \
    --warmup_ratio 0.03 \
    --lr_scheduler_type "cosine" \
    --logging_steps 10 \
    --model_max_length "$MAX_LENGTH" \
    --gradient_checkpointing True \
    --dataloader_num_workers 4 \
    --bf16 True \
    --report_to "tensorboard" \
    --lora_enable True \
    --lora_rank "$LORA_RANK" \
    --lora_alpha "$LORA_ALPHA" \
    --lora_dropout "$LORA_DROPOUT" \
    --bits 16 # 16-bit training (bf16)

echo "--- Training finished ---"

