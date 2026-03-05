# img2dwg

LLM 파인튜닝을 위한 이미지→DWG 데이터셋 변환 프로젝트

## 📋 프로젝트 개요

건축 평면도 이미지(JPG/PNG)를 입력받아 AutoCAD DWG 파일을 생성할 수 있도록 LLM을 파인튜닝하기 위한 데이터셋 변환 도구입니다.

### 주요 목표

1. **DWG→JSON 변환**: 기존 DWG 파일을 JSON 형태의 중간 표현으로 변환
2. **이미지 전처리**: 스마트폰으로 촬영한 평면도 이미지 정제 및 정규화
3. **데이터셋 생성**: OpenAI GPT-4o 파인튜닝용 JSONL 데이터셋 생성
4. **JSON→DWG 변환**: 파인튜닝된 모델의 출력을 DWG로 재변환

## 🏗️ 프로젝트 구조

```
img2dwg/
├── src/
│   └── img2dwg/
│       ├── __init__.py
│       ├── data/              # 데이터 처리 모듈
│       │   ├── __init__.py
│       │   ├── scanner.py     # 데이터 폴더 스캔 및 분류
│       │   ├── dwg_parser.py  # DWG→DXF→JSON 변환
│       │   └── image_processor.py  # 이미지 전처리
│       ├── models/            # 모델 관련
│       │   ├── __init__.py
│       │   ├── schema.py      # 중간 표현 JSON 스키마
│       │   └── converter.py   # JSON→DXF→DWG 변환
│       └── utils/             # 유틸리티
│           ├── __init__.py
│           ├── file_utils.py
│           └── logger.py
├── scripts/                   # 실행 스크립트
│   ├── scan_data.py          # 데이터 스캔
│   ├── convert_dwg.py        # DWG 변환
│   └── generate_dataset.py   # 파인튜닝 데이터셋 생성
├── tests/                     # 테스트
├── .windsurf/                 # Windsurf 설정
│   ├── workflows/            # 워크플로우
│   └── rules/                # 개발 규칙
├── datas/                     # 원본 데이터 (gitignore)
├── output/                    # 변환 결과물 (gitignore)
├── pyproject.toml
└── README.md
```

## 🚀 시작하기

### 필수 요구사항

- Python >= 3.10
- [uv](https://github.com/astral-sh/uv) (패키지 매니저)
- **ODAFileConverter** (DWG↔DXF 변환용) - [설치 가이드](docs/ODAFC_INSTALLATION.md)

### 설치

```bash
# uv를 사용한 의존성 설치
uv sync

# 패키지를 editable 모드로 설치
uv pip install -e .
```

### ODAFileConverter 설정

**중요**: DWG 변환 기능을 사용하려면 ODAFileConverter가 필요합니다.

1. [ODAFileConverter 설치](docs/ODAFC_INSTALLATION.md)
2. 홈 디렉토리에 `.ezdxfrc` 파일 생성:
   ```ini
   [odafc-addon]
   win_exec_path = "C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe"
   ```
3. 설치 확인:
   ```bash
   uv run python examples/test_odafc.py
   ```

### 사용 방법

#### 1. 데이터 스캔 및 분류

```bash
python scripts/scan_data.py
```

원본 데이터 폴더를 스캔하여 다음과 같이 분류합니다:
- **변경 관련**: 파일명에 "변경" 포함 (변경전-모형.jpg, 변경후-모형.jpg, 변경전후.dwg)
- **단면도 관련**: 파일명에 "단면" 포함 (단면도-모형.jpg, 단면도.dwg)

#### 2. DWG→JSON 변환

```bash
# 기본 변환
python scripts/convert_dwg.py --input datas/ --output output/json/

# 최적화 모드 (60~85% 절감)
python scripts/convert_dwg.py --input datas/ --output output/json/ --optimize --rdp-tolerance 1.0 --compact-schema

# 🚀 레이아웃 분석 모드 (95~99% 절감, 권장!)
python scripts/convert_dwg.py --input datas/ --output output/json/ --layout-analysis
```
DWG 파일을 중간 표현 JSON 형태로 변환합니다.

**최적화 옵션**:
- `--layout-analysis`: 🚀 **고수준 레이아웃 분석** (95~99% 절감, 40만 토큰 → 4~20k 토큰)
  - 수천 개의 LINE → 수십 개의 WALL/ROOM 객체로 변환
  - 의미론적 구조 파악 (벽, 방, 문, 창문 등)
  - 반복 패턴 감지 및 템플릿화
- `--optimize`: 기본 최적화 (좌표 반올림, 기본값 제거, DXF R2000)
- `--rdp-tolerance`: 폴리라인 간소화 허용 오차 (0.5=보수적, 1.0=권장, 2.0=공격적)
- `--compact-schema`: Compact 스키마 사용 (키 단축, 배열 평탄화)

⚠️ **중요**: 대부분의 DWG 파일은 40만+ 토큰을 생성하므로, **`--layout-analysis` 옵션 사용을 강력히 권장**합니다.

#### 3. 파인튜닝 데이터셋 생성

```bash
# 기본 방식 (base64 인코딩)
python scripts/generate_dataset.py \
  --input-data datas \
  --input-json output/json \
  --output output \
  --max-tokens 60000 \
  --model gpt-4o

# 🚀 권장: 이미지 URL 사용 (99% 토큰 절감!)
python scripts/generate_dataset.py \
  --use-image-url \
  --image-service github
```
OpenAI GPT-4o 파인튜닝을 위한 JSONL 형식 데이터셋을 생성합니다.

**💡 다중 이미지 지원**:
- DWG 파일 기준으로 레코드 생성 (이미지 기준 아님)
- 변경전/후 이미지를 하나의 레코드로 통합
- 레코드 수 50% 절감, 학습 효율 향상
- 자세한 내용: [다중 이미지 가이드](docs/multi-image-dataset.md)

**기본 옵션**:
- `--max-tokens`: 최대 토큰 수 제한 (기본: 60000)
- `--model`: 토큰 계산에 사용할 모델 (기본: gpt-4o)
- `--split-ratio`: Train/Validation 분할 비율 (기본: 0.8)

**이미지 URL 옵션** (권장):
- `--use-image-url`: 이미지를 공개 URL로 사용 (base64 대신)
  - **효과**: 이미지 토큰 99% 절감 (300k → 15 토큰)
  - **비용**: 파인튜닝 비용 30배 절감
- `--image-service`: 업로드 서비스 선택
  - `imgur`: 간단, 무료 (기본, 권장)
  - `github`: 영구 보관
  - `cloudinary`: 이미지 최적화

**환경변수 설정**:
```bash
# Imgur (권장)
$env:IMGUR_CLIENT_ID="your_client_id"  # Windows
export IMGUR_CLIENT_ID="your_client_id"  # Linux/Mac

# GitHub
$env:GITHUB_TOKEN="ghp_xxx"
$env:GITHUB_REPO_OWNER="username"
$env:GITHUB_REPO_NAME="img2dwg-images"
```

자세한 내용은 [이미지 URL 가이드](docs/image-url-guide.md)를 참조하세요.

**토큰 필터링**: 각 레코드는 tiktoken을 사용하여 토큰 수가 계산되며, 지정된 최대 토큰 수를 초과하는 레코드는 자동으로 필터링됩니다.

## 🌐 Streamlit Publisher 실행/접근/보존 정책

Streamlit 기반 빠른 검증 UI는 아래처럼 실행합니다.

```bash
uv run --extra web streamlit run scripts/web_streamlit_app.py \
  --server.address 127.0.0.1 \
  --server.port 8501 \
  -- --output-root output/web-streamlit
```

운영 가드레일:
- **접근 정책**: 기본 바인딩은 `127.0.0.1`(로컬 전용)으로 유지합니다. 외부 접근이 꼭 필요할 때만 리버스 프록시/방화벽 뒤에서 공개하세요.
- **업로드 정책**: 업로드 파일명은 경로 토큰(`..`, `/`, `\\`)·OS 예약 이름·비허용 특수문자를 거부하며, 확장자는 `.jpg/.jpeg/.png`만 허용됩니다. 저장 시에는 사용자 basename을 버리고 `8hex + 확장자` 랜덤 이름으로 기록해 경로/이름 기반 리스크를 줄입니다.
- **용량 정책**: 단일 업로드는 최대 `10MB`까지만 허용됩니다.
- **개발 검증 스모크**: 업로드 보안 헬퍼 심볼/모듈 로드 확인
  ```bash
  uv run python - <<'PY'
  from scripts.web_streamlit_app import sanitize_upload_filename
  print("smoke:module-load=ok safe_filename=", sanitize_upload_filename("floorplan.png"))
  PY
  ```
- **보존 정책(권장)**: `output/web-streamlit`은 7일 또는 5GB 기준으로 정리 정책을 적용하세요.
  - 예시(7일 초과 파일 정리):
    ```bash
    find output/web-streamlit -type f -mtime +7 -delete
    ```

## 📊 데이터 구조

### 원본 데이터
```
{{ ... }}
└── 2501 (2)/
    ├── 이매촌 진흥 814-405/
    │   ├── 변경전-모형.jpg
    │   ├── 변경후-모형.jpg
    │   ├── 변경전후.dwg
    │   ├── 단면도-모형.jpg
    │   └── 단면도.dwg
    └── ...
```

### 중간 표현 JSON 스키마
```json
{
  "metadata": {
    "filename": "변경전후.dwg",
    "type": "변경",
    "project": "이매촌 진흥 814-405"
  },
  "entities": [
    {
      "type": "line",
      "start": {"x": 0, "y": 0},
      "end": {"x": 100, "y": 0},
      "layer": "Wall"
    },
    {
      "type": "text",
      "position": {"x": 50, "y": 50},
      "content": "거실",
      "height": 3.5
    }
  ]
}
```

## 🔧 기술 스택

### 핵심 라이브러리
- **ezdxf**: DXF 파일 읽기/쓰기 ✅ 구현 완료
- **pandas**: 데이터 처리 및 분석
- **Pillow**: 이미지 처리 ✅ 구현 완료
- **opencv-python**: 이미지 전처리 (왜곡 보정, 노이즈 제거) ✅ 구현 완료
- **pytesseract**: OCR (치수, 텍스트 추출) - 선택사항
- **openai**: GPT-4o API 연동

### 개발 도구
- **pytest**: 테스트 프레임워크
- **ruff**: 린터 및 포매터
- **mypy**: 타입 체킹

### 구현 상태

| 기능 | 상태 |
|------|------|
| 데이터 스캔 및 분류 | ✅ 완료 |
| DWG→DXF→JSON 변환 | ✅ 완료 |
| **토큰 최적화 (RDP, 필터링, 반올림)** | ✅ 완료 |
| 이미지 전처리 | ✅ 완료 |
| JSON→DXF→DWG 역변환 | ✅ 완료 |
| 파인튜닝 데이터셋 생성 | ✅ 완료 |
| 테스트 코드 | ✅ 완료 |

## 🎨 토큰 최적화

DWG 파일의 JSON 변환 시 토큰 수를 줄이기 위한 다양한 최적화 기법이 구현되어 있습니다.

### 빠른 시작

```bash
# 최적화 효과 테스트
python examples/test_optimization.py

# 상세 벤치마크
python scripts/benchmark_compaction.py --input path/to/file.dwg
```

### 주요 최적화 기법 (4단계)

**1단계: 기본 최적화** (30~40% 절감)
- 레이어/타입 필터링
- 좌표 반올림 (소수점 3자리)
- 기본값 제거
- DXF 다운버전 (R2000)

**2단계: RDP + Compact 스키마** (60~85% 절감)
- 폴리라인 간소화 (Ramer-Douglas-Peucker)
- 키 단축 (`"type"` → `"t"`)
- 배열 평탄화 (`[{x,y}]` → `[x,y]`)
- 레이어 테이블화
- 로컬 좌표계

**3단계: 타일링/청크 분할** (100% 활용)
- 공간 타일링 (5000×5000 단위)
- 엔티티 그룹 분할
- 토큰 예산 자동 관리

**4단계: 🚀 레이아웃 분석** (95~99% 절감, **권장!**)
- **고수준 추상화**: LINE/POLYLINE → WALL/ROOM 객체
- **의미론적 그룹화**: 벽, 방, 문, 창문, 주석 자동 감지
- **반복 패턴 감지**: 동일 구조 템플릿화
- **연결선 병합**: 수천 개 선 → 수십 개 폴리라인
- **폐곡선 감지**: 방/공간 자동 인식

### 예상 효과

| 설정 | 토큰 수 (40만 기준) | 절감율 | 용도 |
|------|---------------------|--------|------|
| 기본 | 400,000 | - | 원본 |
| 기본 최적화 | 240,000 | 40% | 일반 |
| RDP + Compact | 60,000 | 85% | 고급 |
| **🚀 레이아웃 분석** | **4,000~20,000** | **95~99%** | ⭐ **권장!** |

자세한 내용은 [최적화 가이드](docs/optimization-guide.md)를 참조하세요.

## 🎯 파인튜닝 워크플로우

1. **데이터 수집**: 이미지-DWG 쌍 수집 (현재 보유)
2. **전처리**: 이미지 정제, DWG→JSON 변환
3. **데이터셋 생성**: GPT-4o 파인튜닝용 JSONL 생성
   ```json
   {
     "messages": [
       {
         "role": "system",
         "content": "당신은 평면도 이미지를 CAD 명령으로 변환하는 전문가입니다."
       },
       {
         "role": "user",
         "content": [
           {"type": "image_url", "image_url": {"url": "..."}}
         ]
       },
       {
         "role": "assistant",
         "content": "{\"entities\": [...]}"
       }
     ]
   }
   ```
4. **파인튜닝**: OpenAI API를 통한 모델 학습
5. **검증**: 생성된 JSON→DWG 변환 및 정확도 평가

## 📝 Windsurf 워크플로우

프로젝트에서 사용 가능한 Windsurf 워크플로우:

- `/scan-data`: 데이터 폴더 스캔 및 분류
- `/convert-dwg`: DWG 파일 변환
- `/test-all`: 전체 테스트 실행
- `/lint-fix`: 코드 린트 및 포맷 자동 수정

자세한 내용은 `.windsurf/workflows/` 참조

## 🔐 Streamlit 업로드 보안 스모크

`web_streamlit_app.py`는 파일명 검증(경로 이탈 차단) 외에도 **유니코드 제어/포맷 문자 + confusable 경로 구분자(NFKC 정규화) 차단**, **저장 시 사용자 basename 제거(랜덤 파일명)**, **확장자-파일시그니처 일치 + 종료 시그니처(IEND/EOI) 검증**을 수행합니다.

빠른 확인 예시:

```bash
uv run python - <<'PY'
import importlib.util
from pathlib import Path

path = Path('scripts/web_streamlit_app.py')
spec = importlib.util.spec_from_file_location('web_streamlit_smoke', path)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)

mod.validate_upload_payload(
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x00IEND\xaeB`\x82',
    filename_suffix='.png',
)

try:
    mod.sanitize_upload_filename('evil\nname.png')
except ValueError:
    print('streamlit upload filename control-char guard: ok')

try:
    mod.sanitize_upload_filename('a／evil.png')
except ValueError:
    print('streamlit upload filename unicode-separator guard: ok')

root = Path('output/_smoke')
upload_dir = root / '_uploads' / '20260305'
upload_dir.mkdir(parents=True, exist_ok=True)
path = mod.build_safe_upload_path(upload_dir, root, 'floorplan.png')
assert path.suffix == '.png' and 'floorplan' not in path.name
print('streamlit upload randomized-save-name guard: ok')

print('streamlit upload signature+footer guard: ok')
PY
```

## 🤝 기여 가이드

1. 이 저장소를 포크합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'feat: Add amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다.

## 🔗 참고 자료

- [OpenAI Fine-tuning Guide](https://platform.openai.com/docs/guides/fine-tuning)
- [ezdxf Documentation](https://ezdxf.readthedocs.io/)
- [AutoCAD DXF Reference](https://help.autodesk.com/view/OARX/2024/ENU/)
