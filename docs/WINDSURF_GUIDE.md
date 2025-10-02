# Windsurf 사용 가이드

img2dwg 프로젝트를 Windsurf에서 효율적으로 개발하기 위한 가이드입니다.

## 🌊 Windsurf 소개

Windsurf는 AI 기반 코드 에디터로, Cascade AI 어시스턴트가 코딩, 디버깅, 테스트를 도와줍니다.

## 🚀 시작하기

### 1. 프로젝트 열기

```bash
# Windsurf로 프로젝트 열기
windsurf .
```

### 2. 첫 실행 체크리스트

- [ ] Python 3.10+ 설치 확인
- [ ] uv 패키지 매니저 설치
- [ ] `uv sync` 실행하여 의존성 설치
- [ ] `.venv` 가상환경 자동 활성화 확인

## 📋 Workflows 사용법

Windsurf는 `.windsurf/workflows/` 폴더의 마크다운 파일을 자동으로 인식합니다.

### 사용 가능한 Workflows

#### `/scan-data` - 데이터 스캔
```
데이터 폴더를 스캔하고 이미지-DWG 쌍을 분류합니다.

사용법:
1. Cascade 패널 열기 (Ctrl+L / Cmd+L)
2. "/scan-data" 입력
3. Cascade가 자동으로 스크립트 실행 및 결과 분석
```

#### `/convert-dwg` - DWG 변환
```
DWG 파일을 중간 표현 JSON으로 변환합니다.

사용법:
1. "/convert-dwg" 입력
2. Cascade가 변환 프로세스 안내
3. 오류 발생 시 자동으로 문제 진단
```

#### `/test-all` - 전체 테스트
```
모든 테스트를 실행하고 커버리지를 확인합니다.

사용법:
1. "/test-all" 입력
2. 테스트 결과 자동 분석
3. 실패한 테스트 디버깅 제안
```

#### `/lint-fix` - 린트 자동 수정
```
코드 스타일 문제를 자동으로 수정합니다.

사용법:
1. "/lint-fix" 입력
2. Ruff가 자동으로 코드 수정
3. 변경사항 리뷰 및 커밋
```

#### `/generate-dataset` - 데이터셋 생성
```
파인튜닝용 JSONL 데이터셋을 생성합니다.

사용법:
1. "/generate-dataset" 입력
2. 데이터셋 생성 프로세스 실행
3. 통계 및 검증 결과 확인
```

### Workflow 체이닝

Workflows는 서로 호출할 수 있습니다:

```markdown
1. /scan-data 실행
2. 결과 확인 후 /convert-dwg 호출
3. /test-all로 검증
```

## 🎯 Cascade 활용 팁

### 1. 파일 컨텍스트 제공

Cascade에게 파일을 직접 참조시키려면 `@` 멘션을 사용하세요:

```
@src/img2dwg/data/scanner.py 이 파일의 scan 메서드를 리팩토링해줘
```

### 2. 터미널 연동

터미널에서 실행된 명령어 결과를 Cascade가 자동으로 읽습니다:

```bash
pytest tests/test_scanner.py -v
# Cascade가 테스트 결과를 분석하고 실패 원인 진단
```

### 3. 에러 자동 해결

코드에서 에러가 발생하면:
1. 에러 메시지가 Cascade에 자동 전달됨
2. Cascade가 문제 분석 및 해결 방법 제시
3. 코드 수정 제안 또는 직접 수정

### 4. 코드 생성

```
이미지 전처리를 위한 OpenCV 함수를 작성해줘:
- 왜곡 보정
- 노이즈 제거
- 명암 정규화
포함해서
```

### 5. 테스트 작성

```
@src/img2dwg/data/dwg_parser.py 이 파일에 대한 pytest 테스트를 작성해줘
```

## 🔧 설정 최적화

### Windsurf 설정 (.vscode/settings.json)

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true,
      "source.fixAll": true
    }
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".venv": true
  }
}
```

### 권장 확장 프로그램

1. **Ruff** - 린터 및 포매터
2. **Python** - Python 언어 지원
3. **Pylance** - 고급 타입 체킹
4. **Python Test Explorer** - 테스트 시각화

## 💡 실전 예제

### 예제 1: 새 기능 개발

```
USER: scanner.py에 단면도와 변경 파일을 구분하는 기능을 추가해줘

Cascade:
1. @src/img2dwg/data/scanner.py 파일 분석
2. classify_file_type() 메서드 생성
3. 테스트 코드 자동 생성 (tests/test_scanner.py)
4. docstring 추가
```

### 예제 2: 버그 수정

```
USER: DWG 변환 시 한글 텍스트가 깨지는 문제를 해결해줘

Cascade:
1. 에러 로그 분석
2. 인코딩 문제 진단 (CP949 vs UTF-8)
3. dwg_parser.py 수정 제안
4. 테스트 케이스 추가
```

### 예제 3: 리팩토링

```
USER: /lint-fix 실행 후 타입 힌트가 없는 함수들에 추가해줘

Cascade:
1. mypy로 타입 체크
2. 타입 힌트 누락 함수 찾기
3. 자동으로 타입 힌트 추가
4. 검증 테스트 실행
```

## 🎨 Cascade 프롬프트 패턴

### 패턴 1: 단계적 작업

```
다음 순서로 작업해줘:
1. datas/ 폴더 구조 분석
2. 각 프로젝트별 파일 분류
3. 통계를 JSON으로 저장
4. 결과를 터미널에 출력
```

### 패턴 2: 컨텍스트 제공

```
@README.md @docs/DEVELOPMENT_GUIDE.md 를 참고해서
새로운 모듈 image_processor.py를 작성해줘.
프로젝트 컨벤션을 따라야 해.
```

### 패턴 3: 오류 해결

```
방금 실행한 pytest에서 실패한 테스트들을 분석하고
각 실패 원인과 해결 방법을 설명해줘.
필요하면 코드도 수정해줘.
```

## 📊 생산성 팁

### 1. 단축키 활용

- `Ctrl+L` (Cmd+L): Cascade 열기/닫기
- `Ctrl+K`: 빠른 명령어 실행
- `Ctrl+Shift+P`: 명령 팔레트

### 2. 멀티 태스킹

여러 작업을 동시에 요청:
```
동시에 다음 작업 수행:
1. /scan-data 실행
2. README.md 업데이트
3. requirements를 pyproject.toml로 마이그레이션
```

### 3. 코드 리뷰

```
@src/img2dwg/data/ 폴더의 모든 파일을 리뷰하고
개선 사항을 제안해줘:
- 코드 스타일
- 성능 최적화
- 에러 처리
```

## 🔍 문제 해결

### Cascade가 응답하지 않을 때

1. Windsurf 재시작
2. 캐시 클리어: `Ctrl+Shift+P` → "Reload Window"
3. 로그 확인: `Help` → `Toggle Developer Tools`

### 가상환경 인식 문제

```bash
# Python 인터프리터 수동 선택
Ctrl+Shift+P → "Python: Select Interpreter" → .venv 선택
```

### 워크플로우가 실행되지 않을 때

1. `.windsurf/workflows/` 폴더 존재 확인
2. 마크다운 파일 형식 검증
3. Windsurf 재시작

## 📚 추가 학습 자료

- [Windsurf 공식 문서](https://docs.windsurf.com)
- [Cascade 활용 가이드](https://docs.windsurf.com/windsurf/cascade)
- [Workflows 문서](https://docs.windsurf.com/windsurf/cascade/workflows)

## 💬 커뮤니티

- [Windsurf Discord](https://discord.gg/windsurf)
- [GitHub Discussions](https://github.com/codeium/windsurf/discussions)
