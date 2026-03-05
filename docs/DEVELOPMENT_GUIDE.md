# 개발 가이드

img2dwg 프로젝트 개발을 위한 가이드라인입니다.

## 📋 개발 원칙

### 1. 코드 스타일

- **포매터**: Ruff 사용
- **라인 길이**: 최대 100자
- **Import 순서**: 표준 라이브러리 → 서드파티 → 로컬 모듈
- **Docstring**: Google Style 사용
- **타입 힌트**: 모든 함수 시그니처에 필수

#### 예시

```python
"""모듈 설명."""
from typing import Dict, List, Optional
import json
from pathlib import Path

import pandas as pd
from ezdxf import DXFDocument

from img2dwg.utils.logger import get_logger


def parse_dwg_file(
    dwg_path: Path,
    output_format: str = "json"
) -> Dict[str, any]:
    """
    DWG 파일을 파싱하여 중간 표현 형태로 변환한다.

    Args:
        dwg_path: DWG 파일 경로
        output_format: 출력 형식 (json, dict 등)

    Returns:
        파싱된 데이터를 담은 딕셔너리

    Raises:
        FileNotFoundError: DWG 파일이 존재하지 않을 때
        ValueError: 지원하지 않는 출력 형식일 때
    """
    logger = get_logger(__name__)
    logger.info(f"DWG 파일 파싱 시작: {dwg_path}")
    
    # 구현...
    
    return result
```

### 2. 파일 구조

```
src/img2dwg/
├── __init__.py
├── data/                    # 데이터 처리
│   ├── __init__.py
│   ├── scanner.py          # 데이터 스캔 및 분류
│   ├── dwg_parser.py       # DWG→JSON 변환
│   └── image_processor.py  # 이미지 전처리
├── models/                  # 데이터 모델
│   ├── __init__.py
│   ├── schema.py           # JSON 스키마 정의
│   └── converter.py        # JSON→DWG 변환
└── utils/                   # 유틸리티
    ├── __init__.py
    ├── file_utils.py       # 파일 입출력
    └── logger.py           # 로깅 설정
```

### 3. 테스트

- **프레임워크**: pytest
- **커버리지**: 최소 80% 이상
- **명명 규칙**: `test_<모듈명>.py`
- **테스트 구조**: Arrange-Act-Assert (AAA) 패턴

#### 예시

```python
"""scanner 모듈 테스트."""
from pathlib import Path
import pytest

from img2dwg.data.scanner import DataScanner


def test_scan_data_folder_returns_projects():
    """데이터 폴더 스캔 시 프로젝트 목록을 반환한다."""
    # Arrange
    scanner = DataScanner(data_path=Path("tests/fixtures/sample_data"))
    
    # Act
    projects = scanner.scan()
    
    # Assert
    assert len(projects) > 0
    assert all(p.has_images for p in projects)


def test_scan_with_invalid_path_raises_error():
    """존재하지 않는 경로로 스캔 시 에러를 발생시킨다."""
    # Arrange
    scanner = DataScanner(data_path=Path("invalid/path"))
    
    # Act & Assert
    with pytest.raises(FileNotFoundError):
        scanner.scan()
```

#### VED 원격 이미지 로딩 안정화 옵션

`ImageToJSONDataset`는 원격 이미지(URL) 로딩 시 아래 정책을 지원합니다.

- `timeout_seconds`: HTTP 요청 타임아웃(초)
- `max_retries`: 재시도 횟수
- `backoff_seconds`: 재시도 백오프 기본값 (지수 증가)
- `cache_dir`: URL 해시 기반 캐시 디렉토리
- `offline`: 네트워크 차단 모드 (캐시/로컬만 허용)

```python
from img2dwg.ved.dataset import ImageToJSONDataset, RemoteImagePolicy

policy = RemoteImagePolicy(
    timeout_seconds=10.0,
    max_retries=2,
    backoff_seconds=0.5,
    cache_dir=Path("output/.ved_image_cache"),
    offline=False,
)

dataset = ImageToJSONDataset(
    jsonl_path=Path("output/finetune_train.jsonl"),
    tokenizer=tokenizer,
    remote_policy=policy,
)
```

사전 검증/캐시 준비:

```bash
uv run python scripts/validate_ved_dataset_images.py \
  --jsonl output/finetune_train.jsonl \
  --cache-dir output/.ved_image_cache \
  --timeout 10 \
  --max-retries 2
```

- `--offline` 사용 시 캐시 미존재 URL은 `[FAIL]`로 보고되고 non-zero 종료됩니다.

### 4. 로깅

- **레벨**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **형식**: `[시간] [레벨] [모듈명] 메시지`
- **파일 출력**: `logs/img2dwg.log`

```python
from img2dwg.utils.logger import get_logger

logger = get_logger(__name__)

logger.debug("디버그 메시지")
logger.info("정보 메시지")
logger.warning("경고 메시지")
logger.error("에러 메시지")
logger.critical("치명적 에러")
```

### 5. 에러 처리

- **명시적 예외**: 구체적인 예외 타입 사용
- **예외 체이닝**: `raise ... from e` 사용
- **재시도 로직**: 외부 API 호출 시 적용

```python
try:
    result = parse_dwg_file(path)
except FileNotFoundError as e:
    logger.error(f"파일을 찾을 수 없음: {path}")
    raise
except Exception as e:
    logger.error(f"DWG 파싱 중 예상치 못한 오류: {e}")
    raise RuntimeError("DWG 파싱 실패") from e
```

## 🔧 개발 환경 설정

### 1. 초기 설정

```bash
# 저장소 클론
git clone https://github.com/your-org/img2dwg.git
cd img2dwg

# uv 설치 (없는 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치
uv sync

# pre-commit 훅 설정 (선택사항)
pre-commit install
```

### 2. 브랜치 전략

- **main**: 프로덕션 브랜치
- **develop**: 개발 브랜치
- **feature/***: 기능 개발
- **bugfix/***: 버그 수정
- **hotfix/***: 긴급 수정

### 3. 커밋 메시지 규칙

[Conventional Commits](https://www.conventionalcommits.org/) 규칙을 따릅니다.

```
<타입>(<범위>): <제목>

<본문>

<푸터>
```

**타입**:
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 스타일 변경 (기능 변경 없음)
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드, 설정 파일 수정

**예시**:
```
feat(scanner): 데이터 스캔 기능 추가

- 프로젝트 폴더별 파일 분류
- 변경/단면도 타입 자동 감지
- 불완전한 쌍 검출 로직 구현

Closes #123
```

## 🚀 워크플로우

### 기능 개발 프로세스

1. **이슈 생성** → GitHub Issues
2. **브랜치 생성** → `feature/기능명`
3. **개발 진행** → 코드 작성 + 테스트
4. **린트 & 포맷** → `ruff check --fix && ruff format`
5. **테스트 실행** → `pytest tests/`
6. **커밋** → Conventional Commits 규칙 준수
7. **Push** → 원격 브랜치에 푸시
8. **PR 생성** → develop 브랜치로
9. **코드 리뷰** → 팀 리뷰 후 머지

### Windsurf 워크플로우 사용

```
/scan-data          # 데이터 스캔
/convert-dwg        # DWG 변환
/generate-dataset   # 데이터셋 생성
/test-all          # 전체 테스트
/lint-fix          # 린트 자동 수정
```

## 📦 의존성 관리

### 새로운 라이브러리 추가

```bash
# 프로덕션 의존성
uv add <package-name>

# 개발 의존성
uv add --dev <package-name>

# 특정 버전
uv add <package-name>==<version>
```

### 의존성 업데이트

```bash
# 모든 의존성 업데이트
uv lock --upgrade

# 특정 패키지만
uv add <package-name>@latest
```

## 🔍 디버깅 팁

### 1. VSCode/Windsurf 디버거 설정

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "justMyCode": true
    },
    {
      "name": "Python: Scan Data",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/scripts/scan_data.py",
      "console": "integratedTerminal"
    }
  ]
}
```

### 2. 로그 레벨 조정

```bash
# 환경변수로 로그 레벨 설정
export LOG_LEVEL=DEBUG
python scripts/scan_data.py
```

### 3. 중단점(Breakpoint) 활용

```python
# 코드 중단점
import pdb; pdb.set_trace()

# 또는
breakpoint()  # Python 3.7+
```

## 📚 참고 자료

- [Python 공식 문서](https://docs.python.org/3/)
- [ezdxf 문서](https://ezdxf.readthedocs.io/)
- [OpenAI Fine-tuning](https://platform.openai.com/docs/guides/fine-tuning)
- [Ruff 문서](https://docs.astral.sh/ruff/)
- [pytest 문서](https://docs.pytest.org/)

## ❓ 자주 묻는 질문

### Q: DWG 파일을 직접 읽을 수 없나요?
A: DWG는 AutoDesk의 독점 이진 포맷이므로 DXF로 변환 후 처리합니다. ODAFileConverter를 사용하세요.

### Q: 테스트 데이터는 어디에 두나요?
A: `tests/fixtures/` 폴더에 샘플 데이터를 저장합니다.

### Q: 이미지 전처리가 왜 필요한가요?
A: 스마트폰 촬영 시 왜곡, 노이즈, 조명 불균형이 발생할 수 있어 정규화가 필요합니다.

### Q: JSON 스키마 변경 시 주의사항은?
A: 기존 변환된 데이터와의 호환성을 고려하고, 버전 필드를 추가하세요.
