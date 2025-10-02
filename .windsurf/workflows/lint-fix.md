---
description: 코드 린트 및 포맷을 자동으로 수정하는 워크플로우입니다.
auto_execution_mode: 3
---

# Lint Fix Workflow

코드 린트 및 포맷을 자동으로 수정하는 워크플로우입니다.

## 작업 순서

1. **Ruff 자동 수정**
   ```bash
   ruff check --fix src/ tests/ scripts/
   ```
   - 자동으로 수정 가능한 린트 오류 수정
   - import 정렬
   - 사용하지 않는 import 제거

2. **코드 포맷팅**
   ```bash
   ruff format src/ tests/ scripts/
   ```
   - PEP 8 스타일 가이드에 맞춰 코드 포맷
   - 일관된 들여쓰기 및 줄바꿈

3. **타입 힌트 추가 확인**
   - 함수 시그니처에 타입 힌트 누락 확인
   - 필요시 타입 힌트 추가 제안

4. **Docstring 검사**
   - 모든 공개 함수/클래스에 docstring 존재 확인
   - docstring 형식 검사 (Google style)

5. **변경사항 확인**
   ```bash
   git diff
   ```
   - 자동 수정된 내용 확인
   - 필요시 추가 수정

6. **테스트 실행**
   - 자동 수정 후 테스트가 여전히 통과하는지 확인
   - `/test-all` 워크플로우 호출

## 실행 명령어

```bash
# Ruff 자동 수정
ruff check --fix src/ tests/ scripts/

# 포맷팅
ruff format src/ tests/ scripts/

# 또는 한 번에
ruff check --fix src/ tests/ scripts/ && ruff format src/ tests/ scripts/
```

## Ruff 설정 (pyproject.toml)

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

## 주의사항

- 자동 수정 전 변경사항 커밋 권장
- 자동 수정 결과를 항상 검토할 것
- 테스트가 실패하면 수정 내용 되돌리기
