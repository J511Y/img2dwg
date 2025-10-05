# img2dwg VLM 모델 선정 및 학습 가이드

## 프로젝트 개요

본 문서는 img2dwg 프로젝트를 위한 Vision-Language Model (VLM) 선정, 파인튜닝 방법론, 그리고 학습 코드 구현에 대한 종합 가이드입니다. 이 프로젝트는 건축 평면도 이미지를 분석하여 AutoCAD 호환 JSON 형태로 변환하는 것을 목표로 하며, 다중 이미지 입력을 지원하여 변경 전후 이미지를 동시에 처리할 수 있습니다.

## 요구사항

프로젝트에서 요구하는 VLM 모델의 조건은 다음과 같습니다:

1. **JSON 출력 지원**: 구조화된 JSON 형식으로 CAD 엔티티를 출력할 수 있어야 합니다.
2. **16K 이상의 컨텍스트**: 긴 대화 및 복잡한 입력을 처리하기 위해 충분한 컨텍스트 길이가 필요합니다.
3. **H100 80GB에서 학습 가능**: 파인튜닝이 H100 80GB GPU에서 실행 가능해야 합니다.
4. **다중 이미지 입력 지원**: 변경 전후 이미지를 동시에 처리할 수 있어야 합니다.

## 모델 리서치 결과

### 후보 모델 비교

다음은 요구사항을 기준으로 평가한 주요 VLM 모델들의 비교표입니다:

| 모델 | 크기 | 컨텍스트 | 다중 이미지 | JSON 출력 | H100 80GB | 종합 평가 |
|------|------|----------|-------------|-----------|-----------|-----------|
| **Qwen2.5-VL-7B** | 7B | 32K (128K 확장) | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **Qwen2.5-VL-3B** | 3B | 32K (128K 확장) | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **LLaVA-OneVision-7B** | 7B | 32K | ✅ | ✅ | ✅ | ⭐⭐⭐⭐ |
| **Pixtral-12B** | 12B | 128K | ✅ | ✅ | ✅ (메모리 많이 사용) | ⭐⭐⭐ |
| **InternVL2-8B** | 8B | 8K | ✅ | ✅ | ✅ | ⭐⭐ (컨텍스트 부족) |

### 최종 선정 모델: Qwen2.5-VL-7B-Instruct

**선정 이유:**

Qwen2.5-VL-7B-Instruct 모델은 모든 요구사항을 완벽하게 충족하며, 다음과 같은 장점을 제공합니다:

- **32K 기본 컨텍스트**: YaRN을 사용하여 128K까지 확장 가능하여 긴 대화 및 복잡한 입력을 처리할 수 있습니다.
- **다중 이미지 및 비디오 지원**: 변경 전후 이미지를 동시에 처리하는 데 적합합니다.
- **구조화된 JSON 출력**: 송장, 양식, 표 등의 구조화된 데이터 추출에 강점을 보입니다.
- **H100 80GB 파인튜닝 가능**: LoRA/QLoRA를 사용하여 효율적인 파인튜닝이 가능합니다.
- **문서 및 차트 이해 우수**: DocVQA 95.7, ChartQA 87.3의 높은 성능을 보입니다.
- **Apache 2.0 라이센스**: 상업적 사용이 가능합니다.
- **활발한 커뮤니티**: 풍부한 문서와 예제가 제공됩니다.

**예상 GPU 메모리 사용량:**

- 추론 (bfloat16): ~16GB
- LoRA 파인튜닝: ~30-40GB
- QLoRA 파인튜닝 (4-bit): ~20-25GB

## 파인튜닝 방법론

### 1. LoRA Fine-tuning (추천)

Low-Rank Adaptation (LoRA)은 모델의 일부 파라미터만 학습하여 메모리 효율적이면서도 좋은 성능을 제공합니다.

**주요 파라미터:**

- `lora_rank`: 128 (기본값, 범위: 8-256)
- `lora_alpha`: 256 (일반적으로 rank의 2배)
- `lora_dropout`: 0.05

**GPU 메모리 요구사항:** 7B 모델 기준 약 30-40GB

### 2. QLoRA Fine-tuning

양자화된 모델에 LoRA를 적용하여 메모리를 더욱 절약합니다.

**설정:**

- 4비트 양자화: ~20-25GB
- 8비트 양자화: ~25-30GB

### 3. Full Fine-tuning

모든 파라미터를 업데이트하여 최고의 성능을 얻을 수 있지만, 가장 많은 메모리를 필요로 합니다.

**GPU 메모리 요구사항:** 7B 모델 기준 약 60-80GB

## 데이터셋 포맷

### 현재 포맷 (OpenAI 스타일)

```json
{
  "messages": [
    {"role": "system", "content": "당신은 2D 건축 평면도 이미지를 분석하여 AutoCAD 호환 JSON 형태로 변환하는 전문가입니다."},
    {"role": "user", "content": [
      {"type": "image_url", "image_url": {"url": "https://..."}},
      {"type": "image_url", "image_url": {"url": "https://..."}},
      {"type": "text", "text": "다음은 건축 평면도의 변경 전/후 이미지입니다..."}
    ]},
    {"role": "assistant", "content": "{\"metadata\": {...}, \"entities\": [...]}"}
  ]
}
```

### Qwen2.5-VL 포맷

```json
{
  "id": "project_001",
  "image": ["before.jpg", "after.jpg"],
  "conversations": [
    {
      "from": "human",
      "value": "<image>\n<image>\n당신은 2D 건축 평면도 이미지를 분석하여 AutoCAD 호환 JSON 형태로 변환하는 전문가입니다.\n\n다음은 건축 평면도의 변경 전/후 이미지입니다..."
    },
    {
      "from": "gpt",
      "value": "{\"metadata\": {...}, \"entities\": [...]}"
    }
  ]
}
```

## 구현된 코드

### 1. 데이터셋 변환 스크립트

**파일:** `scripts/convert_dataset_to_qwen_format.py`

OpenAI 스타일의 JSONL 데이터를 Qwen2.5-VL 포맷으로 변환합니다.

**사용법:**

```bash
python scripts/convert_dataset_to_qwen_format.py \
    --input_file output/finetune_train.jsonl \
    --output_file output/qwen_finetune_train.json
```

### 2. 학습 스크립트

**파일:** `scripts/train_qwen2.5_vl.py`

Qwen2.5-VL 모델을 파인튜닝하는 메인 스크립트입니다.

**주요 기능:**

- LoRA/QLoRA 파인튜닝 지원
- 다중 이미지 입력 처리
- DeepSpeed 통합
- 자동 체크포인트 관리

### 3. 학습 실행 스크립트

**파일:** `scripts/run_training.sh`

학습을 실행하는 쉘 스크립트로, 모든 하이퍼파라미터가 사전 설정되어 있습니다.

**사용법:**

```bash
bash scripts/run_training.sh
```

**주요 하이퍼파라미터:**

- Epochs: 3
- Batch Size: 1 (per device)
- Gradient Accumulation Steps: 16 (effective batch size: 16)
- Learning Rate: 2e-5
- LoRA Rank: 128
- LoRA Alpha: 256
- Max Sequence Length: 8192

### 4. DeepSpeed 설정

**파일:** `scripts/zero2.json`

DeepSpeed ZeRO Stage 2 최적화를 위한 설정 파일입니다.

**주요 기능:**

- Optimizer Offload (CPU)
- BF16 학습
- Gradient Clipping

## 학습 프로세스

### 1. 환경 설정

```bash
# 필요한 라이브러리 설치
pip install transformers==4.56.1
pip install torch==2.5.0
pip install peft==0.13.2
pip install deepspeed==0.15.4
pip install bitsandbytes==0.44.1
pip install accelerate==1.1.1
```

### 2. 데이터 준비

```bash
# 데이터셋 변환
python scripts/convert_dataset_to_qwen_format.py \
    --input_file output/finetune_train.jsonl \
    --output_file output/qwen_finetune_train.json
```

### 3. 학습 실행

```bash
# 학습 시작
bash scripts/run_training.sh
```

### 4. 학습 모니터링

```bash
# TensorBoard로 모니터링
tensorboard --logdir output/checkpoints/qwen2.5-vl-7b-lora-finetune
```

### 5. 추론 테스트

```python
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
import torch

# 모델 로드
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    "output/checkpoints/qwen2.5-vl-7b-lora-finetune",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")

# 추론 수행
# ... (추론 코드)
```

## 예상 학습 시간 (H100 80GB 기준)

### LoRA 파인튜닝

- 400 샘플, 3 epochs: 약 2-3시간
- 1000 샘플, 3 epochs: 약 6-8시간

### QLoRA 파인튜닝 (4-bit)

- 400 샘플, 3 epochs: 약 3-4시간
- 1000 샘플, 3 epochs: 약 8-10시간

### Full 파인튜닝

- 400 샘플, 3 epochs: 약 6-8시간
- 1000 샘플, 3 epochs: 약 15-20시간

## 주의사항 및 팁

### 메모리 관리

1. **배치 크기 조정**: OOM 에러 발생 시 `per_device_train_batch_size`를 줄입니다.
2. **Gradient Accumulation**: 배치 크기를 줄이고 accumulation steps를 증가시킵니다.
3. **Gradient Checkpointing**: 메모리 절약을 위해 활성화합니다 (학습 속도 약간 감소).
4. **Flash Attention 2**: 메모리 효율 및 속도 향상을 위해 사용합니다.

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

## 다음 단계

### 1. 모델 평가

학습된 모델을 검증 데이터셋으로 평가하여 성능을 측정합니다.

```python
# 평가 스크립트 작성 필요
# - JSON 출력 정확도
# - 엔티티 추출 정확도
# - 다중 이미지 처리 성능
```

### 2. 하이퍼파라미터 튜닝

다양한 하이퍼파라미터 조합을 실험하여 최적의 설정을 찾습니다:

- Learning Rate: [1e-5, 2e-5, 5e-5]
- LoRA Rank: [64, 128, 256]
- Batch Size & Accumulation Steps

### 3. 추론 최적화

학습된 모델의 추론 속도를 최적화합니다:

- LoRA 가중치 병합
- 양자화 (4-bit, 8-bit)
- vLLM 또는 TensorRT-LLM 사용

### 4. 프로덕션 배포

모델을 실제 서비스에 배포합니다:

- API 서버 구축
- 배치 처리 파이프라인
- 모니터링 및 로깅

## 참고 자료

### 공식 문서

- [Qwen2.5-VL 공식 문서](https://qwenlm.github.io/blog/qwen2.5-vl/)
- [Transformers 문서](https://huggingface.co/docs/transformers/model_doc/qwen2_5_vl)
- [PEFT (LoRA) 문서](https://huggingface.co/docs/peft/)

### 파인튜닝 가이드

- [Qwen2-VL-Finetune GitHub](https://github.com/2U1/Qwen2-VL-Finetune)
- [Roboflow: Fine-Tune Qwen2.5-VL](https://blog.roboflow.com/fine-tune-qwen-2-5/)
- [F22Labs: Complete Guide to Fine-tuning Qwen2.5 VL](https://www.f22labs.com/blogs/complete-guide-to-fine-tuning-qwen2-5-vl-model/)

### 논문

- [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- [QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314)

## 결론

본 가이드는 img2dwg 프로젝트를 위한 VLM 모델 선정부터 파인튜닝 코드 구현까지의 전체 프로세스를 다룹니다. Qwen2.5-VL-7B-Instruct 모델은 프로젝트의 모든 요구사항을 충족하며, 제공된 학습 스크립트를 사용하여 즉시 파인튜닝을 시작할 수 있습니다. 학습 후에는 평가, 최적화, 배포 단계를 거쳐 실제 서비스에 적용할 수 있습니다.

---

**작성자**: Manus AI  
**작성일**: 2025-10-05  
**버전**: 1.0
