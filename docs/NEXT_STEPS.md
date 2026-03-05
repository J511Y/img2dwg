# 다음 단계: Vision Encoder-Decoder 학습

프로젝트가 **LLM 파인튜닝**에서 **Vision Encoder-Decoder 모델 학습**으로 전환되었습니다.

## ✅ 완료된 작업

1. ✅ **VED 모듈 구축** (`src/img2dwg/ved/`)
   - Config, Tokenizer, Dataset, Model, Metrics, Utils
   
2. ✅ **Long-Context 모델 설정**
   - **Llama-3-8B-262k** (262K 토큰 지원)
   
3. ✅ **학습/추론 스크립트 작성**
   - `scripts/train_ved.py`
   - `scripts/inference_ved.py`

4. ✅ **데이터셋 생성**
   - Train: 337개 샘플
   - Val: 85개 샘플
   - 평균 토큰: ~40K (Llama-3로 처리 가능)

## 🚀 다음 단계

### Step 1: 의존성 설치

```bash
# 가상환경 활성화
& c:/Users/Ace/Desktop/개발/img2dwg/.venv/Scripts/Activate.ps1

# 의존성 설치 (이미 완료)
uv sync

# 추가 의존성 확인
pip show transformers torch torchvision accelerate
```

### Step 2: 데이터 확인

```bash
# 데이터셋 통계 확인
cat output/dataset_stats.json

# 샘플 확인
head -n 1 output/finetune_train.jsonl | python -m json.tool
```

### Step 3: 모델 학습 시작

```bash
# 학습 시작 (GPU 필요)
python scripts/train_ved.py

# 예상 시간: 20-30시간 (A100 40GB 기준)
# 메모리: ~35GB VRAM
```

**⚠️ GPU 요구사항**:
- **권장**: NVIDIA A100 40GB 이상
- **최소**: NVIDIA V100 32GB (빡빡)
- **불가**: RTX 3090/4090 24GB (OOM 발생 가능)

### Step 4: 학습 모니터링

```bash
# 로그 확인
tail -f logs/train_ved.log

# TensorBoard (선택사항)
tensorboard --logdir output/ved_checkpoints
```

### Step 5: 추론 테스트

```bash
# 학습 완료 후 추론
python scripts/inference_ved.py \
  --model-path output/ved_checkpoints/best \
  --image path/to/test_image.jpg \
  --output output/predicted.json
```

## 📊 예상 결과

### 학습 곡선
- **Epoch 1-10**: Loss 빠르게 감소
- **Epoch 10-30**: Loss 천천히 감소
- **Epoch 30-50**: Fine-tuning

### 성능 목표
- **JSON 파싱 성공률**: >95%
- **엔티티 정확도**: >85%
- **추론 시간**: <1초/이미지

## 🔧 문제 해결

### GPU 메모리 부족 (OOM)

```python
# config.py 수정
batch_size: int = 1  # 이미 최소값
gradient_accumulation_steps: int = 32  # 16 → 32로 증가
max_length: int = 65536  # 131072 → 65536으로 감소
```

또는 데이터 재생성:

```bash
# 토큰 수 줄이기
python scripts/generate_dataset.py --max-tokens=50000
```

### 학습 속도 느림

```python
# config.py 수정
num_workers: int = 8  # 4 → 8로 증가
mixed_precision: str = "bf16"  # fp16 → bf16 (A100)
```

### 모델 다운로드 실패

```bash
# HuggingFace 토큰 설정
export HF_TOKEN="your_token_here"

# 또는 수동 다운로드
git lfs install
git clone https://huggingface.co/gradientai/Llama-3-8B-Instruct-262k
```

## 📈 성능 비교 (예상)

| 지표 | GPT-4V (API) | VED (자체) | 개선 |
|------|-------------|-----------|------|
| **추론 시간** | ~5초 | <1초 | **5배** |
| **비용/이미지** | $0.01-0.05 | <$0.0001 | **100~500배** |
| **정확도** | ? | >85% | - |
| **제어성** | 프롬프트 의존 | 완전 제어 | ✅ |
| **Hallucination** | 있음 | 없음 | ✅ |

## 🎯 마일스톤

- [ ] **Week 1**: 학습 환경 구축 및 첫 학습 시작
- [ ] **Week 2**: 하이퍼파라미터 튜닝
- [ ] **Week 3**: 평가 및 오류 분석
- [ ] **Week 4**: 프로덕션 배포 준비

## 📚 참고 문서

- [VED 모듈 README](../src/img2dwg/ved/README.md)
- [VED 리서치](ved-research.md)
- [토큰 길이 가이드](token-length-guide.md)
- [최적화 가이드](optimization-guide.md)

## 💬 질문?

- **학습이 안 시작됨**: GPU 메모리 확인, 데이터 경로 확인
- **Loss가 안 떨어짐**: Learning rate 조정, 데이터 품질 확인
- **JSON이 이상함**: 토크나이저 확인, max_length 조정

## ✨ 성공 후

학습이 완료되면:

1. **모델 평가**: `scripts/evaluate_ved.py`
   ```bash
   python scripts/evaluate_ved.py \
     --model-path output/ved_checkpoints/best \
     --data-file output/finetune_val.jsonl \
     --output output/ved_eval
   ```
   - 산출물: `output/ved_eval/metrics.json`, `output/ved_eval/failures.jsonl`
2. **프로덕션 배포**: FastAPI 서버 구축
3. **A/B 테스트**: GPT-4V vs VED 비교
4. **최적화**: ONNX 변환, Quantization

---

**🎉 준비 완료! 이제 `python scripts/train_ved.py`로 학습을 시작하세요!**
