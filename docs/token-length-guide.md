# 토큰 길이 문제 해결 가이드

Vision Encoder-Decoder 모델의 토큰 길이 제한과 해결 방법입니다.

## 🚨 문제 상황

현재 데이터셋의 평균 토큰 수: **~100,000 토큰**
VED 모델 처리 가능 범위: **512~2,048 토큰**

→ **50배 초과!**

## 📊 모델별 최대 길이

| 모델 | 최대 토큰 | 메모리 사용량 | 추천 |
|------|----------|--------------|------|
| **GPT-2** | 1,024 | 낮음 | ⭐ 기본 |
| **GPT-2 Medium** | 1,024 | 중간 | - |
| **GPT-2 Large** | 1,024 | 높음 | - |
| **BART** | 1,024 | 중간 | ⭐ 대안 |
| **T5-base** | 512 | 낮음 | - |
| **T5-large** | 512 | 높음 | - |
| **LongT5** | 16,384 | 매우 높음 | 🔥 긴 시퀀스 |
| **LED** | 16,384 | 매우 높음 | 🔥 긴 시퀀스 |

## 💡 해결 방안

### **방안 1: 토큰 압축 (필수, 권장)**

#### 1.1 Layout Analysis 사용

```bash
# DWG 변환 시 고수준 레이아웃 분석
python scripts/convert_dwg.py \
  --input datas/ \
  --output output/json/ \
  --layout-analysis

# 효과: 95~99% 토큰 절감
# 100,000 토큰 → 1,000~5,000 토큰
```

**원리**:
- 수천 개의 LINE → 수십 개의 WALL/ROOM 객체
- 의미론적 그룹화 (벽, 방, 문, 창문)
- 반복 패턴 템플릿화

#### 1.2 Compact Schema 사용

```bash
# 데이터셋 생성 시 Compact Schema 적용
python scripts/generate_dataset.py \
  --max-tokens=2000 \
  --compact-schema

# 효과: 추가 20~30% 절감
# 키 단축: "type" → "t"
# 배열 평탄화: [{"x":0,"y":0}] → [0,0]
```

#### 1.3 조합 사용 (최고 효과)

```bash
# 1단계: Layout Analysis로 DWG 변환
python scripts/convert_dwg.py --layout-analysis

# 2단계: Compact Schema로 데이터셋 생성
python scripts/generate_dataset.py --max-tokens=2000 --compact-schema

# 최종 효과: 97~99% 절감
# 100,000 토큰 → 1,000~3,000 토큰 ✅
```

### **방안 2: 긴 시퀀스 모델 사용**

#### 2.1 LongT5 (16K 토큰)

```python
# config.py 수정
encoder_model: str = "microsoft/swin-base-patch4-window7-224"
decoder_model: str = "google/long-t5-tglobal-base"  # 16K 토큰
max_length: int = 16384
```

**장점**:
- 16K 토큰 처리 가능
- Efficient attention mechanism

**단점**:
- 메모리 사용량 높음 (A100 40GB 권장)
- 학습 시간 증가

#### 2.2 LED (Longformer Encoder-Decoder)

```python
decoder_model: str = "allenai/led-base-16384"
max_length: int = 16384
```

**장점**:
- 16K 토큰 처리
- Sparse attention (메모리 효율적)

**단점**:
- 여전히 메모리 많이 사용

### **방안 3: 타일링 (분할 처리)**

큰 JSON을 여러 타일로 분할하여 학습:

```bash
# 타일링 활성화 (이미 기본값)
python scripts/generate_dataset.py \
  --max-tokens=2000 \
  --enable-tiling

# 효과: 100,000 토큰 → 50개의 2,000 토큰 타일
```

**문제점**:
- 샘플 수 50배 증가 (학습 시간 증가)
- 전체 구조 파악 어려움

### **방안 4: 데이터 필터링**

너무 긴 샘플 제외:

```python
# config.py
filter_max_tokens: int = 2000  # 이보다 긴 샘플 제외
```

**문제점**:
- 데이터 손실 (복잡한 평면도 제외됨)

## 🎯 권장 전략

### **단계별 접근**

#### Phase 1: 토큰 압축 (필수)
```bash
# 1. Layout Analysis로 DWG 재변환
python scripts/convert_dwg.py --layout-analysis

# 2. Compact Schema로 데이터셋 재생성
python scripts/generate_dataset.py --max-tokens=2000 --compact-schema

# 목표: 평균 1,000~2,000 토큰
```

#### Phase 2: 모델 선택
- **평균 <2K 토큰**: GPT-2 (권장)
- **평균 2K~16K 토큰**: LongT5
- **평균 >16K 토큰**: 추가 압축 필요

#### Phase 3: 학습 시작
```bash
python scripts/train_ved.py
```

## 📈 예상 결과

### 압축 전
```
평균 토큰: 100,000
최대 토큰: 150,000
학습 가능: ❌
```

### 압축 후 (Layout Analysis + Compact)
```
평균 토큰: 1,500
최대 토큰: 3,000
학습 가능: ✅ (GPT-2)
메모리: RTX 3090 (24GB) 충분
```

## 🔧 실행 명령어

### 추천 설정 (최적화)

```bash
# 1단계: DWG 재변환 (Layout Analysis)
python scripts/convert_dwg.py \
  --input datas/ \
  --output output/json_optimized/ \
  --layout-analysis

# 2단계: 데이터셋 재생성 (Compact Schema)
python scripts/generate_dataset.py \
  --input-json output/json_optimized/ \
  --output output/ \
  --max-tokens=2000 \
  --compact-schema \
  --use-image-url \
  --image-service=github

# 3단계: 통계 확인
cat output/dataset_stats.json

# 4단계: 학습 시작 (다음 단계)
python scripts/train_ved.py
```

## 📊 비교표

| 방법 | 토큰 절감 | 구현 난이도 | 정보 손실 | 권장도 |
|------|----------|------------|----------|--------|
| **Layout Analysis** | 95~99% | 낮음 | 거의 없음 | ⭐⭐⭐⭐⭐ |
| **Compact Schema** | 20~30% | 낮음 | 없음 | ⭐⭐⭐⭐⭐ |
| **LongT5** | 0% | 중간 | 없음 | ⭐⭐⭐ |
| **타일링** | 0% | 낮음 | 있음 | ⭐⭐ |
| **필터링** | 0% | 낮음 | 많음 | ⭐ |

## ✅ 결론

**반드시 Layout Analysis + Compact Schema를 사용하세요!**

이 조합으로 100,000 토큰을 1,000~2,000 토큰으로 줄일 수 있으며, 일반 GPT-2 모델로 학습 가능합니다.
