# 인증/시크릿 안전 가이드

시크릿(PAT, API key) 유출은 공급망 공격으로 바로 이어질 수 있습니다. 아래 원칙을 기본 운영 규칙으로 사용합니다.

## 1) 토큰 포함 URL 금지

다음과 같은 형태는 **금지**입니다.

```bash
https://x-access-token:<TOKEN>@github.com/org/repo.git
```

대신 credential helper 또는 `gh auth login`을 사용합니다.

```bash
gh auth login
git config --global credential.helper osxkeychain
```

## 2) 로컬 설정 원칙

- `.env` 파일은 저장소에 커밋하지 않습니다.
- 토큰은 환경변수 또는 OS keychain에서만 읽습니다.
- 샘플 설정은 `.env.example`에 placeholder만 둡니다.

## 3) 로그/출력 마스킹

`img2dwg.utils.logger.setup_logging()`은 기본적으로 시크릿 마스킹 필터를 활성화합니다.

- GitHub PAT (`ghp_`, `github_pat_`)
- OpenAI key (`sk-...`)
- Bearer token / URL credential 구간

민감정보가 포함될 수 있는 문자열을 직접 `print()` 하지 말고 로거를 사용하세요.

## 4) CI 스캔

GitHub Actions `secret-scan` 워크플로에서 gitleaks가 실행됩니다.

- PR/Push에서 시크릿 패턴 탐지 시 실패
- 로컬 사전 점검 권장

```bash
gitleaks detect --source . --config .gitleaks.toml
```

## 5) 예외 처리

테스트 목적으로 synthetic token이 필요한 경우:

1. 실제 토큰 형식을 절대 사용하지 않거나,
2. `.gitleaks.toml` allowlist에 테스트 파일 경로를 명시하고,
3. PR 설명에 예외 사유를 남깁니다.
