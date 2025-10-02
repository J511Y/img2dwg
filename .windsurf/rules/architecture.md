---
trigger: always_on
---

# 프로젝트 아키텍처

img2dwg 프로젝트의 구조와 설계 원칙을 설명합니다.

## 📐 전체 구조

```
img2dwg/
├── src/img2dwg/          # 메인 소스 코드
│   ├── data/             # 데이터 처리 계층
│   ├── models/           # 데이터 모델 및 변환
│   └── utils/            # 공통 유틸리티
├── scripts/              # 실행 스크립트
├── tests/                # 테스트 코드
└── docs/                 # 문서
```

## 🏛️ 레이어 구조

### 1. Data Layer (데이터 계층)

**목적**: 원본 데이터 처리 및 분류

#### 모듈

- **`scanner.py`**: 데이터 폴더 스캔 및 파일 분류
  - `DataScanner`: 폴더 구조 탐색
  - `ProjectData`: 프로젝트 데이터 모델
  - `FileGroup`: 파일 그룹 (변경/단면)

- **`dwg_parser.py`**: DWG 파일 파싱
  - DWG → DXF 변환
  - DXF → JSON 중간 표현

- **`image_processor.py`**: 이미지 전처리
  - 해상도 정규화
  - 왜곡 보정
  - 노이즈 제거

### 2. Model Layer (모델 계층)

**목적**: 데이터 구조 정의 및 변환

#### 모듈

- **`schema.py`**: 중간 표현 JSON 스키마
  - `CADEntity`: 엔티티 기본 클래스
  - `LineEntity`, `PolylineEntity`, etc.
  - `CADDocument`: 문서 전체 구조

- **`converter.py`**: JSON → DWG 역변환
  - JSON → DXF 생성
  - DXF → DWG 변환

### 3. Utils Layer (유틸리티 계층)

**목적**: 공통 기능 제공

#### 모듈

- **`logger.py`**: 로깅 설정
- **`file_utils.py`**: 파일 유틸리티

## 🔄 데이터 플로우

### 파인튜닝 데이터셋 생성 플로우

```
[원본 데이터]
    │
    ├─→ [DataScanner] ──→ 프로젝트 목록
    │
    ├─→ [DWGParser]
    │       ├─→ DWG → DXF 변환
    │       ├─→ DXF 파싱
    │       └─→ JSON 생성
    │
    ├─→ [ImageProcessor]
    │       ├─→ 전처리
    │       └─→ Base64 인코딩
    │
    └─→ [DatasetGenerator]
            ├─→ Image + JSON 쌍 생성
            ├─→ OpenAI 형식 변환
            └─→ JSONL 저장
```

### 역변환 플로우 (추론 후)

```
[LLM 출력 JSON]
    │
    └─→ [JSONToDWGConverter]
            ├─→ JSON → DXF 생성
            └─→ DXF → DWG 변환
                    │
                    └─→ [최종 DWG 파일]
```

## 🎯 설계 원칙

### 1. 관심사의 분리 (Separation of Concerns)

각 모듈은 단일 책임을 가집니다:
- **Data Layer**: 데이터 입출력
- **Model Layer**: 데이터 변환
- **Utils Layer**: 공통 기능

### 2. 의존성 역전 (Dependency Inversion)

상위 모듈은 하위 모듈의 구현에 의존하지 않습니다:
```python
# ❌ 나쁜 예
class DWGParser:
    def __init__(self):
        self.converter = ODAConverter()  # 구체적 구현에 의존

# ✅ 좋은 예
class DWGParser:
    def __init__(self, converter_path: Optional[Path] = None):
        self.converter_path = converter_path  # 추상화에 의존
```

### 3. 명시적 에러 처리

모든 외부 의존성은 명시적으로 검증:
```python
if not dwg_path.exists():
    raise FileNotFoundError(f"DWG 파일을 찾을 수 없습니다: {dwg_path}")
```

### 4. 타입 안전성

모든 함수에 타입 힌트 사용:
```python
def parse(self, dwg_path: Path) -> Dict[str, Any]:
    """타입 힌트로 인터페이스 명확화."""
    ...
```

## 📦 데이터 모델

### ProjectData 계층 구조

```
ProjectData
├── name: str
├── path: Path
├── parent_folder: str
├── change_group: FileGroup
│   ├── type: "변경"
│   ├── images: List[Path]
│   └── dwg_files: List[Path]
└── section_group: FileGroup
    ├── type: "단면"
    ├── images: List[Path]
    └── dwg_files: List[Path]
```

### CADDocument 계층 구조

```
CADDocument
├── metadata: Metadata
│   ├── filename: str
│   ├── type: str
│   ├── project: Optional[str]
│   └── source_path: Optional[str]
└── entities: List[CADEntity]
    ├── LineEntity
    │   ├── start: Point2D
    │   └── end: Point2D
    ├── PolylineEntity
    │   ├── points: List[Point2D]
    │   └── closed: bool
    ├── TextEntity
    │   ├── position: Point2D
    │   ├── content: str
    │   └── height: float
    └── ...
```

## 🔌 외부 의존성

### 핵심 라이브러리

1. **ezdxf**: DXF 파일 읽기/쓰기
   - 용도: DWG ↔ DXF 변환 후 처리
   - 대안: Direct DWG reader (라이선스 이슈)

2. **Pillow**: 이미지 처리
   - 용도: 리사이징, 포맷 변환
   - 대안: OpenCV (더 많은 기능)

3. **OpenCV**: 고급 이미지 처리
   - 용도: 왜곡 보정, 노이즈 제거
   - 대안: scikit-image

4. **OpenAI SDK**: LLM API
   - 용도: 파인튜닝 및 추론
   - 대안: 다른 LLM provider

### 외부 도구

- **ODAFileConverter**: DWG ↔ DXF 변환
  - 필수: DWG 파일 처리
  - 설치: [Open Design Alliance](https://www.opendesign.com/guestfiles/oda_file_converter)

## 🧪 테스트 전략

### 테스트 피라미드

```
        /\
       /  \  E2E Tests (적음)
      /____\
     /      \  Integration Tests (중간)
    /________\
   /          \  Unit Tests (많음)
  /__________\
```

### 테스트 범위

1. **Unit Tests** (80%)
   - 각 모듈의 개별 함수
   - 엣지 케이스 처리
   - 에러 조건

2. **Integration Tests** (15%)
   - 데이터 스캔 → JSON 변환
   - JSON → DWG 변환

3. **E2E Tests** (5%)
   - 전체 파이프라인
   - 샘플 데이터셋 생성

## 🚀 확장 가능성

### 향후 추가 가능한 기능

1. **다양한 CAD 형식 지원**
   ```python
   class CADParser(ABC):
       @abstractmethod
       def parse(self, file_path: Path) -> CADDocument:
           pass

   class DWGParser(CADParser):
       ...

   class DXFParser(CADParser):
       ...
   ```

2. **다양한 LLM Provider 지원**
   ```python
   class LLMProvider(ABC):
       @abstractmethod
       def finetune(self, dataset: Path) -> str:
           pass

   class OpenAIProvider(LLMProvider):
       ...

   class AnthropicProvider(LLMProvider):
       ...
   ```

3. **웹 애플리케이션 통합**
   ```
   FastAPI Backend
   ├── /api/scan
   ├── /api/convert
   ├── /api/generate
   └── /api/inference
   ```

## 📊 성능 고려사항

### 병렬 처리

대량의 파일 처리 시 병렬화:
```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor() as executor:
    results = executor.map(parser.parse, dwg_files)
```

### 메모리 관리

큰 이미지 처리 시 스트리밍:
```python
def process_large_image(path: Path) -> None:
    """청크 단위로 이미지 처리."""
    with Image.open(path) as img:
        # 필요한 작업만 수행
        img.thumbnail((2048, 2048))
        img.save(output_path)
```

### 캐싱

중복 처리 방지:
```python
@lru_cache(maxsize=128)
def parse_dwg_cached(dwg_path: str) -> Dict[str, Any]:
    """파싱 결과 캐싱."""
    return parse_dwg(Path(dwg_path))
```

## 🔒 보안 고려사항

1. **파일 경로 검증**
   ```python
   def validate_path(path: Path, base: Path) -> None:
       """Path traversal 공격 방지."""
       if not path.resolve().is_relative_to(base.resolve()):
           raise ValueError("Invalid path")
   ```

2. **API 키 관리**
   ```python
   import os
   from pathlib import Path

   # 환경변수 우선
   api_key = os.getenv("OPENAI_API_KEY")

   # .env 파일 (gitignore)
   if not api_key:
       env_file = Path(".env")
       if env_file.exists():
           # python-dotenv 사용
           load_dotenv(env_file)
   ```

3. **입력 검증**
   ```python
   def validate_json(data: Dict[str, Any]) -> None:
       """JSON 스키마 검증."""
       required_fields = ["metadata", "entities"]
       for field in required_fields:
           if field not in data:
               raise ValueError(f"Missing field: {field}")
   ```
