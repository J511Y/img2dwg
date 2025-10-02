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
python scripts/convert_dwg.py --input datas/ --output output/json/
```
DWG 파일을 중간 표현 JSON 형태로 변환합니다.

#### 3. 파인튜닝 데이터셋 생성

```bash
python scripts/generate_dataset.py \
  --input-data datas \
  --input-json output/json \
  --output output \
  --max-tokens 60000 \
  --model gpt-4o
```
OpenAI GPT-4o 파인튜닝을 위한 JSONL 형식 데이터셋을 생성합니다.

**옵션**:
- `--max-tokens`: 최대 토큰 수 제한 (기본: 60000)
- `--model`: 토큰 계산에 사용할 모델 (기본: gpt-4o)
- `--split-ratio`: Train/Validation 분할 비율 (기본: 0.8)

**토큰 필터링**: 각 레코드는 tiktoken을 사용하여 토큰 수가 계산되며, 지정된 최대 토큰 수를 초과하는 레코드는 자동으로 필터링됩니다.

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
| 이미지 전처리 | ✅ 완료 |
| JSON→DXF→DWG 역변환 | ✅ 완료 |
| 파인튜닝 데이터셋 생성 | ✅ 완료 |
| 테스트 코드 | ✅ 완료 |

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
