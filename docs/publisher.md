# Web Publisher Guide (Gradio / Streamlit)

`img2dwg`의 이미지→DXF 변환을 브라우저에서 빠르게 검증하기 위한 실행 가이드입니다.

## 0) 사전 준비

프로젝트 루트(`img2dwg/`)에서 실행합니다.

```bash
# 웹 퍼블리셔 실행 전용 의존성 설치 (lock 파일 기준 재현)
uv sync --frozen --extra web

# (선택) pytest/ruff/mypy까지 함께 쓰려면
uv sync --frozen --extra web --extra dev
```

> `web` extra에는 `gradio`, `streamlit`이 포함됩니다.

---

## 1) Gradio Publisher

### 실행

```bash
uv run --frozen --extra web python scripts/web_gradio.py --host 127.0.0.1 --port 7860
```

### 접속

- http://127.0.0.1:7860

### 주요 옵션

- `--host`: 바인딩 주소 (기본 `127.0.0.1`)
- `--port`: 포트 (기본 `7860`)
- `--allow-remote`: non-loopback host(예: `0.0.0.0`, 사내 IP) 바인딩을 명시적으로 허용
- `--output-root`: 결과 저장 경로 (기본 `output/web`, 상대 경로는 프로젝트 루트 기준으로 고정 해석)
- host 입력 검증: 빈 문자열, 앞뒤 공백, 제어/포맷 문자(`NUL`/개행/탭/`DEL`/bidi 제어 등) 포함 host는 실행 전에 거부
- `--share`: Gradio share URL 사용

> 실행 전 포트 사용 여부를 사전 점검합니다. 이미 점유된 포트면 즉시 에러를 반환합니다.
>
> 또한 loopback이 아닌 host에 바인딩하려면 `--allow-remote`를 함께 지정해야 합니다.

### 스모크 테스트

```bash
uv run --frozen --extra web python scripts/web_gradio.py \
  --smoke-test \
  --smoke-wait-seconds 1 \
  --smoke-timeout-seconds 15 \
  --port 7861
```

---

## 2) Streamlit Publisher

### 실행

```bash
uv run --frozen --extra web python scripts/web_streamlit.py --host 127.0.0.1 --port 8501
```

### 접속

- http://127.0.0.1:8501

### 주요 옵션

- `--host`: 바인딩 주소 (기본 `127.0.0.1`)
- `--port`: 포트 (기본 `8501`)
- `--allow-remote`: non-loopback host(예: `0.0.0.0`, 사내 IP) 바인딩을 명시적으로 허용
- `--output-root`: 결과 저장 경로 (기본 `output/web-streamlit`, 상대 경로는 프로젝트 루트 기준으로 고정 해석)
- host 입력 검증: 빈 문자열, 앞뒤 공백, 제어/포맷 문자(`NUL`/개행/탭/`DEL`/bidi 제어 등) 포함 host는 실행 전에 거부
- `--smoke-log-lines`: 스모크 실패 시 출력할 Streamlit 로그 tail 라인 수 (기본 `80`)
- `--smoke-keep-log`: 스모크 성공 시에도 임시 로그 파일 유지

> 실행 전 포트 사용 여부를 사전 점검합니다. 이미 점유된 포트면 즉시 에러를 반환합니다.
>
> 또한 loopback이 아닌 host에 바인딩하려면 `--allow-remote`를 함께 지정해야 합니다.

### 스모크 테스트

```bash
uv run --frozen --extra web python scripts/web_streamlit.py \
  --smoke-test \
  --smoke-wait-seconds 1 \
  --smoke-timeout-seconds 20 \
  --port 8502
```

---

## 3) 보존 정책 / 정리(cleanup) 운영 가이드

웹 퍼블리셔 출력물은 반복 테스트 시 빠르게 누적될 수 있습니다.

- Gradio: `output/web/<timestamp>/<run-id>/*.dxf`
- Streamlit: `output/web-streamlit/_uploads/<date>/...`, `output/web-streamlit/<timestamp>/<run-id>/*.dxf`

### 기본 정책 (시작 시 자동 실행)

두 퍼블리셔 모두 **시작 시 cleanup**을 수행합니다.

- `--cleanup-max-age-days` 기본값: `7`
- `--cleanup-max-size-gb` 기본값: `5`

정리 순서:
1. max-age 초과 파일 삭제
2. 남은 파일이 max-size 초과면 오래된 파일부터 추가 삭제

### Dry-run (삭제 예정 리포트만 출력)

```bash
# Gradio
uv run --frozen --extra web python scripts/web_gradio.py --cleanup-dry-run

# Streamlit
uv run --frozen --extra web python scripts/web_streamlit.py --cleanup-dry-run
```

출력 예시:

```text
[cleanup:DRY-RUN] root=/.../output/web-streamlit
policy=max-age-days=7.0, max-size-gb=5.0
scan=15 files / 123456 bytes, targets=3 files / 45678 bytes
targets(sample):
- _uploads/20260301/abcd-old.png (12345 bytes, reasons: max-age)
```

### 정책 조정 예시

```bash
# 3일 + 2GB 정책
uv run --frozen --extra web python scripts/web_gradio.py \
  --cleanup-max-age-days 3 \
  --cleanup-max-size-gb 2
```

### cleanup 비활성화 (권장하지 않음)

```bash
uv run --frozen --extra web python scripts/web_streamlit.py --no-cleanup
```

`--no-cleanup` 사용 시 실행 시점에 무제한 누적 경고 로그를 출력합니다.

---

## 4) 통합 스모크 체크 (Gradio + Streamlit)

두 퍼블리셔를 한 번에 점검하려면 아래 명령을 사용하세요.

```bash
uv run --frozen --extra web python scripts/smoke_web_publishers.py
```

cleanup dry-run 포함 예시:

```bash
uv run --frozen --extra web python scripts/smoke_web_publishers.py --cleanup-dry-run
```

---

## 5) 외부 기기에서 접근 (LAN 테스트)

같은 네트워크의 다른 기기에서 접속해야 하면 host를 `0.0.0.0`으로 실행하고,
반드시 `--allow-remote`로 의도적인 노출을 명시해야 합니다.

```bash
# Gradio
uv run --frozen --extra web python scripts/web_gradio.py \
  --host 0.0.0.0 --port 7860 --allow-remote

# Streamlit
uv run --frozen --extra web python scripts/web_streamlit.py \
  --host 0.0.0.0 --port 8501 --allow-remote
```

통합 스모크에서도 동일하게 `--allow-remote`를 전달합니다.

```bash
uv run --frozen --extra web python scripts/smoke_web_publishers.py \
  --host 0.0.0.0 --allow-remote
```

이후 `http://<실행머신-IP>:포트`로 접근하세요.

---

## 6) Troubleshooting

### Q1. `No module named gradio` / `No module named streamlit`

웹 extra 의존성이 빠진 경우입니다.

```bash
uv sync --frozen --extra web
```

### Q2. 포트 충돌 (`Address already in use`)

다른 포트로 실행하세요.

```bash
uv run --frozen --extra web python scripts/web_gradio.py --port 7865
uv run --frozen --extra web python scripts/web_streamlit.py --port 8505
```

### Q3. 스모크 테스트 실패 (`web endpoint not ready ...`)

1. 포트가 이미 점유되어 있는지 확인
2. 의존성 설치 상태 확인 (`uv sync --frozen --extra web`)
3. 로컬 방화벽/보안 도구 점검
4. `--smoke-timeout-seconds` 값을 늘려 재시도
5. Streamlit 실패 시 로그 tail 확인 (`--smoke-log-lines`)

### Q4. `Refusing non-loopback host binding...` 에러가 발생합니다

원격 노출 의도를 명시하지 않은 상태에서 non-loopback host를 지정한 경우입니다.

```bash
# 예: LAN 공개가 필요한 경우
uv run --frozen --extra web python scripts/web_streamlit.py \
  --host 0.0.0.0 --allow-remote
```

로컬에서만 테스트한다면 `--host 127.0.0.1`을 유지하는 것이 안전합니다.

### Q5. DXF 생성 실패

- Strategy 실행 중 오류가 난 경우 Summary의 Notes 확인
- 입력 이미지 업로드 확인
- 필요 시 CLI 파이프라인으로 동일 이미지 재현

### Q6. `Host must not be empty` / `Host contains control or format characters` 에러가 발생합니다

host 인자에 공백만 전달되었거나 앞뒤 공백/개행/탭/NUL/`DEL`/bidi 제어문자 같은 제어·포맷 문자가 포함된 경우입니다.

- `--host 127.0.0.1` 또는 `--host 0.0.0.0 --allow-remote`처럼 **명시적인 host 문자열**을 사용하세요.
- 자동화 스크립트에서 환경변수 치환 시 숨김 제어문자(예: `\u202e`)가 섞이지 않았는지 확인하세요.

### Q7. 리뷰 게이트에서 `ruff format --check` 또는 `mypy (unused-ignore)`가 실패합니다

퍼블리셔 스크립트 변경 후 아래 정적 게이트를 먼저 실행해 CI/리뷰 FAIL을 예방하세요.

```bash
uv run --extra dev ruff format --check scripts/web_gradio.py scripts/web_streamlit.py scripts/web_streamlit_app.py
uv run --extra dev mypy scripts/smoke_web_publishers.py scripts/web_gradio.py scripts/web_streamlit.py scripts/web_streamlit_app.py src/img2dwg/web/__init__.py src/img2dwg/web/retention.py
```

`pyproject.toml`의 `[tool.mypy].mypy_path = "src"`를 기준으로 local package import를 해석하므로,
`PYTHONPATH=src` 환경변수 우회 없이 동일 명령을 재현할 수 있습니다.

추가로 wheel 패키징 단계에서 `src/img2dwg/py.typed`를 강제로 포함하므로,
설치형 실행 환경에서도 `module is installed, but missing py.typed marker` 계열
`import-untyped` 실패가 재발하지 않습니다.

또한 `unused "type: ignore"`가 뜨면 해당 import 라인에서 불필요한
`# type: ignore[import-untyped]` 또는 파일 레벨 `disable-error-code=import-untyped`를 제거합니다.

---

> 참고: Publisher는 DXF 결과 검증용입니다. DWG 변환이 필요하면 ODAFileConverter 설정이 별도로 필요합니다.
