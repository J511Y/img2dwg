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
| ADR-010 · 2026-10-13 | canonical geometry·metric 치수/간격과 pixel semantics를 별도 감독 후 연결한다 | Jippin overlay 라벨만으로 CAD 정밀도 supervision 불충분. joint gold 검수 필요 |
| ADR-011 · 2026-10-13 | 사내 데이터 중심 structured decoder 학습을 주력 후보로 둔다 | 공개 generic wall이 confirmed NB를 대신하지 않음. pretrained/domain-pretrained/scratch는 비교로 결정 |
| ADR-012 · 2026-10-13 | 준공도면+변경전후.dwg의 변경전 평면을 주력 페어로 제한한다 | 사용자 파일/영역 지정. 기존 4종 reference 허용과 thumbnail crop은 그대로 채택 불가 |
| ADR-013 · 2026-10-13 | 다음 CAD action controller와 중간 HITL을 정식 연구·제품 경로로 둔다 | 사용자 System-1 구상. 현재 Jev/Laya 모달리티와 별도 vision action policy 구분 |

확인 필요: target CAD/DWG version, 정량 acceptance 목표, 승인된 데이터 범위·외부처리·compute budget, 자체 코드 라이선스.

## 추가 결정

- ADR-014 · 전유부만 복원한다. 실제 방향을 복원 선행 gate로 두었던 결정은 ADR-017로 수정한다.
- ADR-015 · 중심선→치수 제약→디테일과 치수 원장 누락/geometry 검사를 필수로 둔다. text 보존만으로 완료할 수 없다.
- ADR-016 · 사용자 요청으로 전체 특징점 정합 재시도를 중단하고 기존 40개에서 5개 검수 기준선부터 진행한다. 기존 실험 증거는 보존한다.

- ADR-017 · 입력 방향의 DWG 벡터 복원을 우선한다. 실제 좌우반전은 CAD 기존 기능/후속 편집으로 처리하며 복원을 막지 않는다. 학습 image/GT 방향 정규화는 별도 데이터 정확성 검사다.
- ADR-018 · 첫 학습은 DINOv3 ViT-B/16+graph decoder, 첫 비교는 Raster2Seq다. 치수 OCR/association+solver는 공통 경로다. 실제 정합 실패를 합성 CAD 학습의 중단 사유로 두지 않는다.
