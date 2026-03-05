# 시크릿 유출 대응 Runbook

시크릿(PAT/API key/Access token) 노출이 의심되면 아래 순서로 대응합니다.

## 0. 트리거

- CI(gitleaks) 실패
- PR/로그/스크린샷에서 토큰 노출 발견
- 외부 제보

## 1. 즉시 차단 (T+0)

- 노출된 토큰을 **즉시 폐기(revoke)**
- 동일 권한 토큰 재발급
- 필요한 경우 계정/봇 비밀번호/세션 회전

체크리스트:
- [ ] GitHub PAT revoke 완료
- [ ] OpenAI/API key revoke 완료
- [ ] 새 토큰 발급 및 서비스 반영 완료

## 2. 노출 범위 파악 (T+15m)

- 유출 위치: 커밋, PR 코멘트, 로그, 아티팩트
- 노출 시간: 최초 업로드 시각
- 권한 범위: read/write/admin 등

증거 수집:
- [ ] 관련 PR/커밋 URL
- [ ] 로그/아티팩트 링크
- [ ] 영향받은 저장소/서비스 목록

## 3. 저장소 정리 (T+30m)

- 평문 시크릿 제거 커밋
- 필요 시 히스토리 정리(`git filter-repo`/BFG)
- force-push 후 팀 공지 및 로컬 재동기화 안내

> 주의: 히스토리 정리는 협업 중단/재동기화 비용이 커서 오너 승인 후 수행.

## 4. 검증 (T+45m)

- `secret-scan` CI green 확인
- 재발급 토큰 정상 동작 확인
- 노출 문자열 재검색

```bash
git grep -nE "gh[pousr]_ | github_pat_ | sk-" || true
```

## 5. 사후 조치 (T+1h)

- Incident 코멘트/문서화
- 재발 방지 액션 등록
  - 최소권한 토큰
  - 만료기한 단축
  - 로거 사용 강제
  - PR 템플릿 체크리스트에 보안 항목 추가

## Incident 기록 템플릿

```markdown
### Secret Leak Incident
- 발견 시각:
- 발견 경로:
- 유출 시크릿 종류:
- 노출 범위:
- 회수/교체 완료 시각:
- 후속 작업:
```
