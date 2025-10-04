# Vision Encoder-Decoder (VED) 모듈

이미지→DWG 변환을 위한 Vision Encoder-Decoder 모델 학습 및 추론 모듈입니다.

## 📋 최종 목표

**건축 평면도 이미지를 입력받아 DWG 호환 JSON을 생성하는 전문 Vision-to-Structured-Output 모델 개발**

### 핵심 목표
1. ✅ **LLM 대체**: OpenAI API 의존성 제거, 자체 모델 운영
2. ✅ **비용 절감**: API 비용 → GPU 인프라 비용 (30배+ 절감)
3. ✅ **성능 향상**: 도메인 특화 학습으로 정확도 향상
4. ✅ **속도 개선**: 추론 시간 5초 → 0.1초 (50배 향상)
5. ✅ **제어 가능성**: 출력 형식 완전 제어, hallucination 방지

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Vision Encoder-Decoder                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  [평면도 이미지]                                              │
│         ↓                                                     │
│  ┌──────────────────┐                                        │
│  │ Vision Encoder   │  (Swin Transformer / ViT)             │
│  │  - Patch Embed   │                                        │
│  │  - Self-Attention│                                        │
│  │  - Feature Maps  │                                        │
│  └──────────────────┘                                        │
│         ↓                                                     │
│  [Visual Features: 768/1024-dim vectors]                     │
│         ↓                                                     │
│  ┌──────────────────┐                                        │
│  │ Language Decoder │  (GPT2 / BART)                        │
│  │  - Cross-Attn    │  ← Visual Features                    │
│  │  - Self-Attn     │                                        │
│  │  - Token Gen     │                                        │
│  └──────────────────┘                                        │
│         ↓                                                     │
│  [JSON Tokens: {"entities": [...]}]                          │
│         ↓                                                     │
│  [DWG 호환 JSON]                                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 모델 구성
- **Encoder**: `microsoft/swin-base-patch4-window7-224` (88M params)
- **Decoder**: `gpt2` (124M params) - JSON 생성 특화 fine-tuning
- **Total**: ~212M parameters (GPT-4의 1/10000 크기)

## 📂 모듈 구조

```
src/img2dwg/ved/
├── __init__.py
├── README.md                    # 본 문서
├── config.py                    # 모델 설정 (하이퍼파라미터)
├── dataset.py                   # 데이터셋 클래스
├── model.py                     # VED 모델 정의
├── tokenizer.py                 # JSON 토크나이저 (CAD 토큰 추가)
├── trainer.py                   # 학습 루프
├── inference.py                 # 추론 엔진
├── metrics.py                   # 평가 지표 (JSON 정확도, 구조 유사도)
└── utils.py                     # 유틸리티 함수
```

## 🚀 진행 방향

### Phase 1: 데이터 준비 (완료)
- ✅ 이미지-JSON 쌍 데이터셋 생성 (`output/finetune_*.jsonl`)
- ✅ 토큰 최적화 (RDP, Compact Schema, Layout Analysis)
- ✅ 이미지 전처리 파이프라인

### Phase 2: 모델 구축 (진행 중)
- [ ] **2.1 토크나이저 확장**
  - GPT2 토크나이저에 CAD 특화 토큰 추가
  - `{"type": "LINE", "start": [x, y], ...}` 형식 학습
  
- [ ] **2.2 데이터셋 클래스 구현**
  - HuggingFace `datasets` 형식으로 변환
  - 이미지 전처리 + JSON 토큰화
  - Train/Val split
  
- [ ] **2.3 모델 초기화**
  - Pre-trained encoder + decoder 결합
  - Cross-attention 레이어 초기화
  - 학습 가능 파라미터 설정

### Phase 3: 학습 (예정)
- [ ] **3.1 기본 학습**
  - Teacher forcing 방식
  - Cross-entropy loss
  - Learning rate scheduling
  
- [ ] **3.2 고급 최적화**
  - Mixed precision training (FP16)
  - Gradient accumulation
  - LoRA/QLoRA (파라미터 효율적 학습)
  
- [ ] **3.3 실험 추적**
  - TensorBoard / Weights & Biases
  - 학습 곡선, 샘플 출력 모니터링

### Phase 4: 평가 및 개선 (예정)
- [ ] **4.1 정량 평가**
  - JSON 파싱 성공률
  - 엔티티 정확도 (type, coordinates)
  - BLEU/ROUGE 스코어 (구조 유사도)
  
- [ ] **4.2 정성 평가**
  - 생성된 JSON → DWG 변환
  - 시각적 비교 (원본 vs 생성)
  
- [ ] **4.3 오류 분석**
  - 실패 케이스 분석
  - 데이터 증강 전략
  - 모델 개선 방향

### Phase 5: 배포 (예정)
- [ ] **5.1 모델 최적화**
  - ONNX 변환
  - Quantization (INT8)
  - TorchScript 컴파일
  
- [ ] **5.2 추론 서버**
  - FastAPI 엔드포인트
  - Batch inference
  - GPU 리소스 관리
  
- [ ] **5.3 프로덕션 배포**
  - Docker 컨테이너화
  - 모니터링 및 로깅
  - A/B 테스트 (vs LLM)

## 🎯 성능 목표

| 지표 | 현재 (GPT-4V) | 목표 (VED) |
|------|--------------|-----------|
| **추론 시간** | ~5초 | **<0.5초** |
| **비용/이미지** | $0.01-0.05 | **<$0.0001** |
| **정확도** | ? | **>90%** |
| **JSON 파싱률** | ~95% | **>98%** |
| **Hallucination** | 있음 | **없음** |

## 📊 데이터셋 통계

현재 사용 가능한 데이터:
- **Train**: ~80개 샘플 (이미지-JSON 쌍)
- **Validation**: ~20개 샘플
- **이미지 해상도**: 다양 (전처리 후 224x224 또는 384x384)
- **JSON 크기**: 평균 ~10-50KB (최적화 후)

## 🔧 학습 설정 (예상)

```python
# config.py 예시
ENCODER_MODEL = "microsoft/swin-base-patch4-window7-224"
DECODER_MODEL = "gpt2"
IMAGE_SIZE = 384  # Swin Transformer 입력 크기
MAX_LENGTH = 2048  # JSON 최대 토큰 수
BATCH_SIZE = 8
LEARNING_RATE = 5e-5
NUM_EPOCHS = 50
WARMUP_STEPS = 500
```

## 📚 참고 자료

### 논문
- [TrOCR: Transformer-based OCR (2021)](https://arxiv.org/abs/2109.10282)
- [Donut: OCR-free Document Understanding (2022)](https://arxiv.org/abs/2111.15664)
- [Pix2Seq: Language Modeling for Object Detection (2021)](https://arxiv.org/abs/2109.10852)
- [FloorplanTransformation: Raster-to-Vector (2017)](https://jiajunwu.com/papers/im2cad_iccv.pdf)

### 코드 예시
- [HuggingFace VisionEncoderDecoder](https://huggingface.co/docs/transformers/model_doc/vision-encoder-decoder)
- [TrOCR Fine-tuning Notebook](https://github.com/NielsRogge/Transformers-Tutorials/tree/master/TrOCR)

## 🤝 기여 가이드

1. 각 모듈은 독립적으로 테스트 가능해야 함
2. Docstring은 Google Style 사용
3. 타입 힌트 필수
4. 학습 재현성 보장 (random seed 고정)

## 📝 TODO

- [ ] `config.py`: 하이퍼파라미터 설정
- [ ] `tokenizer.py`: CAD 토큰 추가
- [ ] `dataset.py`: 데이터 로더 구현
- [ ] `model.py`: VED 모델 래퍼
- [ ] `trainer.py`: 학습 루프
- [ ] `inference.py`: 추론 파이프라인
- [ ] `metrics.py`: 평가 지표
- [ ] `scripts/train_ved.py`: 학습 스크립트
- [ ] `scripts/evaluate_ved.py`: 평가 스크립트
- [ ] `notebooks/ved_exploration.ipynb`: 탐색 노트북

## 🔗 관련 문서

- [프로젝트 아키텍처](../../docs/ARCHITECTURE.md)
- [개발 가이드](../../docs/DEVELOPMENT_GUIDE.md)
- [토큰 최적화 가이드](../../docs/optimization-guide.md)
