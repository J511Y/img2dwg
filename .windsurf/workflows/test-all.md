---
description: 전체 프로젝트 테스트를 실행하는 워크플로우입니다.
auto_execution_mode: 1
---

# Test All Workflow

전체 프로젝트 테스트를 실행하는 워크플로우입니다.

## 작업 순서

1. **환경 확인**
   - Python 버전 확인 (>= 3.10)
   - 필수 라이브러리 설치 여부 확인
   - `uv sync` 실행 (필요시)

2. **유닛 테스트 실행**
   ```bash
   pytest tests/ -v --cov=src/img2dwg --cov-report=html
   ```
   - 모든 모듈의 유닛 테스트 실행
   - 코드 커버리지 측정

3. **통합 테스트 실행**
   - 데이터 스캔 기능 테스트
   - DWG→JSON 변환 파이프라인 테스트
   - JSON→DWG 역변환 테스트

4. **타입 체크**
   ```bash
   mypy src/img2dwg
   ```
   - 정적 타입 검사 수행

5. **린트 검사**
   ```bash
   ruff check src/ tests/ scripts/
   ```
   - 코드 스타일 및 잠재적 오류 검사

6. **결과 요약**
   - 성공/실패한 테스트 수
   - 코드 커버리지 퍼센티지
   - 타입 체크 오류 수
   - 린트 오류/경고 수

## 실행 명령어

```bash
# 전체 테스트
pytest tests/ -v

# 커버리지와 함께
pytest tests/ -v --cov=src/img2dwg --cov-report=html

# 특정 모듈만
pytest tests/test_scanner.py -v
```

## 테스트 구조

```
tests/
├── __init__.py
├── test_scanner.py          # 데이터 스캔 테스트
├── test_dwg_parser.py       # DWG 파싱 테스트
├── test_image_processor.py  # 이미지 처리 테스트
├── test_schema.py           # JSON 스키마 테스트
└── test_converter.py        # JSON→DWG 변환 테스트
```

## 성공 기준

- 모든 테스트 통과
- 코드 커버리지 >= 80%
- 타입 체크 오류 없음
- 린트 critical 오류 없음
