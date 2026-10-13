# 결정 기록

| ID / 날짜 | 결정 | 근거 / 재검토 조건 |
| --- | --- | --- |
| ADR-001 · 2026-10-13 | CAD-IR→결정론적 DXF→DWG를 기본 출력 경로로 둔다 | 엔티티·좌표·기하 오류를 분리 검증. 직접 다른 출력 후보도 공통 평가로 비교 가능 |
| ADR-002 · 2026-10-13 | 워크 의뢰 연결 폴더를 데이터 위치 정본으로 삼는다 | 원본 read-only, 실제 설정은 로컬 전용. 다른 인벤토리는 lineage를 기록해 연계 |
| ADR-003 · 2026-10-13 | 모델·방법을 넓게 탐색하고 동일 protocol로 선택한다 | frontier/System-1/graph/sequence/SSL/diffusion/hybrid 실험 목록 유지 |
| ADR-004 · 2026-10-13 | Jev/Laya는 typed decision 보조 후보로 둔다 | 공식 text/JSON 계약 확인. 이미지/geometry 기능이 공식 추가되면 재검토 |
| ADR-005 · 2026-10-13 | 건물·평면 계열 그룹 split 및 calibration/test 분리 | duplicate·합성·routing 누수 방지 |
| ADR-006 · 2026-10-13 | 공개 repo에 원본·민감 경로·가중치를 넣지 않는다 | 현재 GitHub repo 공개. 비식별 예외는 실제 파일 검토 후 추가 |
| ADR-007 · 2026-10-13 | 현재 실행 코드·CI·유료 실험은 만들지 않는다 | 사용자 기본 세팅 요청 범위. 후속 구현 요청으로 전환 |
| ADR-008 · 2026-10-13 | 중앙 연구노트의 기존 주간·월간 예약에 통합한다 | 신규 중복 예약 없이 projects.json·AGENTS·저장/실행 prompt 동기화 |
| ADR-009 · 2026-10-13 | 기존 data-pipeline 자료는 재사용 후보로 조사한다 | dirty 자료/과거 집계는 이관 성과가 아님. snapshot·license·재현 검증 후 채택 |

확인 필요: target CAD/DWG version, 정량 acceptance 목표, 승인된 데이터 범위·외부처리·compute budget, 자체 코드 라이선스.
