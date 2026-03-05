# Issue Status Lifecycle (develop PR 기준)

## 목적
`develop` 대상 PR merge 이후에도 이슈 상태가 `in-review`에서 멈추지 않도록, 저장소 내 상태 전환 규칙을 고정합니다.

## 라벨 전환 규칙
- `status:triage` → 작업 우선순위/범위 확정 전
- `status:in-progress` → 구현/테스트 착수 후
- `status:in-review` → PR 생성 후 리뷰 중
- `status:done` → develop merge 완료 + 검증 완료

## PR 링크 규칙
- 자동 완료 전환 대상: `Closes #<issue-number>`
- 참고 링크: `Refs #<issue-number>`

`Closes` 키워드는 PR 본문 또는 제목에 포함되어야 하며, merge 시 워크플로우가 해당 이슈를 `closed` + `status:done`으로 동기화합니다.

## 자동화 워크플로우
- 파일: `.github/workflows/sync-issue-status-on-develop-merge.yml`
- 트리거: `pull_request_target.closed`
- 실행 조건: `merged == true` and `base.ref == "develop"`
- 동작:
  1. PR 본문/제목에서 `Closes` 이슈 추출
  2. 해당 이슈 라벨에서 triage/in-progress/in-review 제거
  3. `status:done` 추가 및 이슈 `closed`
  4. PR 번호/commit sha를 이슈 코멘트로 기록

## 운영 체크리스트
1. 착수 시: `status:in-progress`로 이동 + 작업 계획 코멘트
2. PR 생성 시: `status:in-review`로 이동 + PR 링크 코멘트
3. merge 후: 워크플로우 코멘트로 `status:done` 전환 여부 확인
4. 예외 발생 시: `scripts/sync_issue_status.py` 로그 확인 후 수동 보정
