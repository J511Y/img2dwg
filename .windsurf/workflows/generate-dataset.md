---
description: OpenAI GPT-4o 파인튜닝용 JSONL 데이터셋을 생성하는 워크플로우입니다.
auto_execution_mode: 3
---

# Generate Dataset Workflow

OpenAI GPT-4o 파인튜닝용 JSONL 데이터셋을 생성하는 워크플로우입니다.

## 작업 순서

1. **변환된 JSON 로드**
   - `output/json/` 폴더에서 모든 JSON 파일 읽기
   - 유효성 검증 통과한 파일만 선택

2. **이미지 처리**
   - 각 JSON에 대응하는 이미지 파일 찾기
   - 이미지 전처리:
     - 해상도 정규화 (최대 2048x2048)
     - 노이즈 제거
     - 왜곡 보정 (필요시)
   - 이미지를 base64 인코딩 또는 URL로 준비

3. **JSONL 레코드 생성**
   - OpenAI 파인튜닝 형식에 맞춰 변환
   - 각 레코드 구조:
     ```json
     {
       "messages": [
         {
           "role": "system",
           "content": "당신은 2D 건축 평면도 이미지를 분석하여 AutoCAD 호환 JSON 형태로 변환하는 전문가입니다. 선, 곡선, 점선, 텍스트, 치수를 정확하게 추출해야 합니다."
         },
         {
           "role": "user",
           "content": [
             {
               "type": "text",
               "text": "다음 평면도 이미지를 분석하여 CAD 엔티티를 추출해주세요."
             },
             {
               "type": "image_url",
               "image_url": {"url": "data:image/jpeg;base64,..."}
             }
           ]
         },
         {
           "role": "assistant",
           "content": "{\"metadata\": {...}, \"entities\": [...]}"
         }
     }
     ```

4. **데이터 분할**
   - 전체 데이터를 Train / Validation으로 분할
   - Train: 80%, Validation: 20%
   - 프로젝트별로 stratified split

## 5. 데이터셋 검증**
   - 각 레코드 형식 검증
   - 이미지 크기 확인
   - JSON 파싱 가능 여부 확인

## 6. **저장**
   - `output/finetune_train.jsonl`: 학습 데이터셋
   - `output/finetune_val.jsonl`: 검증 데이터셋
   - `output/dataset_stats.json`: 데이터셋 통계
  "total_samples": 120,
  "train_samples": 96,
  "val_samples": 24,
  "변경_samples": 75,
  "단면도_samples": 45,
  "avg_entities_per_sample": 42.5,
  "entity_type_distribution": {
    "line": 1200,
    "polyline": 450,
    "text": 380,
    "circle": 120
  }
}
```

## OpenAI 파인튜닝 가이드

1. **데이터셋 업로드**
   ```bash
   openai files create -f output/finetune_train.jsonl -p fine-tune
   ```

2. **파인튜닝 작업 생성**
   ```bash
   openai fine-tuning jobs create \
     -t <train_file_id> \
     -v <val_file_id> \
     -m gpt-4o-2024-08-06
   ```

3. **작업 모니터링**
   ```bash
   openai fine-tuning jobs get <job_id>
   ```

## 주의사항

- 이미지 크기가 너무 크면 토큰 비용 증가
- 최소 10개 이상의 샘플 권장
- JSON 출력 형식을 일관되게 유지
