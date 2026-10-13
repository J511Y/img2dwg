# 작업 하네스

문서·설정·템플릿에 데이터 pilot 실행기를 추가했다. [pilot 실행 안내](dataset-pilot.md)의 read-only 수집·crop·치수/정합·무결성·화면 검증을 사용할 수 있다. 모델 학습/배포 실행기·CI·canonical schema validator는 아직 없다. 수행되지 않은 명령을 완료로 체크하지 않는다.

## 세션 루프

1. **상태 복원:** AGENTS→STATUS→목표/결정→관련 계약, Git 상태, 로컬 경로 접근을 확인한다.
2. **작업 계약:** 한 기술 질문, 성공/실패 조건, 데이터/예산·변경 범위를 명시한다. 모르는 항목은 null/확인 필요로 남긴다.
3. **근거 확인:** 공식 논문·repo·model card·license와 최신 API 가용성을 확인한다. 다운로드/접근 권한/실측 여부를 따로 기록한다.
4. **실험 등록:** 백로그 ID와 `templates/experiment.md`로 날짜 기록을 만들고 manifest에 Git/모델/데이터/protocol revision을 고정한다.
5. **실행:** 원본은 read-only, 산출물은 private output root의 고유 run ID 아래에 저장한다. 예산/timeout, checkpoint·재시도·실패복구를 기록한다.
6. **검증:** 데이터→IR→기하/위상→DWG→CAD 사용성→render-back→사람 검수 순으로 확인한다. 한 gate 실패가 뒤 단계의 성공에 묻히지 않게 한다.
7. **증거·인계:** run 로그/metric·artifact SHA-256, receipt, 실패·다음 실험을 기록하고 STATUS/결정/백로그를 갱신한다.

## 변경별 검사

| 변경 | 필요한 검사 |
| --- | --- |
| 문서/설정 | JSON 파싱·상대 링크·diff·비밀/원본 경로 제외 확인 |
| 데이터 수집기 (향후) | 원본 무변경·그룹 split·hash·정합 실패 fixture |
| 모델 (향후) | fixed tiny smoke + frozen evaluation, NaN/shape·좌표 역변환 |
| writer (향후) | 공개 synthetic fixture로 entity roundtrip·unit·layer·arc/door 검사 |
| routing (향후) | paired rule/System-1/VLM, calibration과 E2E risk–coverage |
| 배포 (향후) | 실제 업로드→preview→DWG download→CAD open·edit receipt |

## 하네스 구현 시 순서

P1 수집 감사 CLI와 manifest validator → P2 CAD-IR schema/GT writer/roundtrip checker → P3 공통 candidate adapter와 metric runner → P4 System-1 adapter/비용 ledger → CI에는 비식별 synthetic smoke만 추가한다. CI에서 SMB 접근, 사내 도면 upload, 유료 모델 호출을 자동 실행하지 않는다.

첫 학습 후보·run 범위·중단 조건은 [벡터 우선 계획](../research/2026-10-13-vector-first-training-plan.md)과 [선언 설정](../../configs/first-training-plan.json)을 참조한다. 선언 설정은 GPU 작업 runner/예약이 아니며 현재 학습은 미실행이다.
