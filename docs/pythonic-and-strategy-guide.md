# Pythonic + Strategy 구현 가이드

## 기본 원칙
- 타입힌트 필수
- 함수는 한 가지 책임만
- 예외는 의미 있는 메시지로 래핑
- 로깅은 구조화(`logger.info(..., extra=...)`)
- 테스트 없는 신규 전략 금지

## 전략 패턴 규칙
- 모든 구현은 `ConversionStrategy`를 상속
- 입력/출력은 `ConversionInput`, `ConversionOutput` 사용
- 전략별 하드코딩 금지 (config-driven)
- 동일 샘플셋에서 전략별 결과를 비교 가능해야 함

## 파일 규칙
- 전략 구현: `src/img2dwg/strategies/*.py`
- 공통 벤치: `src/img2dwg/pipeline/benchmark.py`
- 실행 스크립트: `scripts/benchmark_strategies.py`
- 결과물: `output/benchmark/benchmark_results.json`

## 구현 체크리스트
1. 전략 클래스 추가 + registry 등록
2. 샘플 10건 벤치 실행
3. 결과 JSON 첨부
4. Linear 코멘트 템플릿으로 보고
