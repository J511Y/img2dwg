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

- ADR-019 · native CAD 구조 감사 후 업무 컴포넌트/parameter/관계를 주된 감독 단위로 정한다. LINE handle·entity 순서·block 정의 존재를 의미 정답으로 쓰지 않는다. catalog/factory 검증은 첫 학습 정답을 확정하는 최소 단계다.

- ADR-020 · 사용자 확정으로 같은 의뢰 폴더의 준공도면+변경전후.dwg를 현장의 input/output 페어로 인정한다. 별도 구조 정합 승인을 수집 gate로 두지 않는다. 변경전 추출·컴포넌트 전처리·파일 무결성은 계속 검사한다.
- ADR-021 · 최소 1,000개 실제 페어를 새 비공개 img2dwg HF 버킷의 별도 version prefix에 준비한다. source paths는 local provenance에만 두고 클라우드 metadata는 비식별 ID로 연결한다. 업로드 후 전체 shard byte readback을 검증한다.

- ADR-022 · 사용자 첫 학습/Space 요청에 따라 DINOv3 frozen dense component coordinate
  baseline을 768px/A100, job별 90분으로 실행한다. 최초 FP16 실패는 BF16으로 수정하고
  4-slot·endpoint 정규화 variant를 선택한다. Geometry candidate를 먼저 실시간 벡터로
  제공하되 숫자 치수 미학습·미확정 축척을 `?`/unitless로 표시한다. 현 Space는 SVG·DXF이며
  DWG/치수 완전 목표의 완료로 승격하지 않는다. source CAD retrieval은 inference에서 금지한다.

- ADR-023 · 실제 스캔에서 실패한 coordinate 모델은 기본 배포에서 제외한다. 파일 생성/학습
  loss/합성 F1로 서비스 복원 품질을 대신하지 않는다. 실제 raw input–canonical output을
  배우는 component/parameter/관계 경로를 우선하고, 실제 구조 및 필수 치수 검증 receipt
  없이 학습 모델을 다시 기본 배포하지 않는다. 관측 선 기준선과 학습 모델의 출처를 구분한다.

- ADR-024 · 공유 노드·컴포넌트 set decoder와 learned reference/host/axis 관계를 실제 구현한다.
  GT factory와 모델을 구분하고 source handle/고정 LINE 순서를 query identity로 감독하지 않는다.
  필요한 모든 치수의 숫자·측정점·실제 길이를 검사하며 geometry confidence로 실패를 덮지 않는다.
  학습 판정은 실제 구조·치수 지표의 stable pass/plateau다. 시간 상한은 비용 제약이다.
  본학습/development/별도 20개를 분리하며 통과 모델만 private Space에 올린다.

- ADR-025 · 2026-10-14 · 사용자의 현재 시각 수용 및 명시 배포 요청에 따라 5개 재현
  실험 checkpoint를 private Space에서 미리 제공한다. 원래 production quality gate를
  성공으로 바꾸지 않으며 별도 20개 실패와 CPU/GPU 차이를 공개한다. 본학습의 미통과
  checkpoint를 자동 배포하지 않는다. 실제 인증 upload/download와 checkpoint/revision을 검증한다.
- ADR-026 · 100mm 보정은 사용자가 선택하는 편집이다. 1m 이상 벽 face span/사각 폭·높이만
  보정하고 치수 숫자, shared node 좌표, 벽 두께, 문 크기는 유지한다. 독립 절대좌표
  rounding으로 두꺼운 벽을 하나의 선으로 붕괴시키지 않는다. dimension-host 일치는 별도 검수다.

- ADR-027 · 2026-10-14 · full-v1 실행은 completed지만 원래 5개와 별도 20개 구조·치수
  실패로 Space 교체를 거부한다. native DXF audit 성공을 품질 통과로 쓰지 않는다.
  사용자의 최신 요청에 따라 추가 실험/방법 선정을 중단하고 상세 실험 회고를 먼저 한다.
  초기화 확장 직후 5개 능력이 유지됐다는 대조 결과는 보존하되 실패 원인을 단정하지 않는다.

- ADR-028 · 2026-10-14 · 사용자 승인으로 EXP-047의 10개 train 단일 요인 진단을 실행했다.
  unexpanded 원래5도 새 Adam1e-4 첫 update에서 실패하므로 새 데이터/count 확장을
  최초 실패의 필요조건으로 보지 않는다. LR1e-6은 원래5 단독 유지에 성공했지만 같은
  초기화의 10개 혼합에서는 실패했다. 32회 동일 노출은 진단 창이며 수렴 판정이 아니다.
  작은 혼합에서 신규 재현과 기존 유지가 함께 확인되기 전 1,028개 재학습/Space 재배포를
  하지 않는다. optimizer 상태 부재와 물리 좌표 민감도·gradient 간섭을 후속 검증 대상으로 둔다.


- ADR-029 · 2026-10-15 · EXP-054는1,028개 실행 completed / 신규 품질 failed다.
  동결 base+새 pooled residual로 기존10은 유지했으나 별도 정정20은0/20·0/479다.
  candidate freeze 후의 같은20 기준선과 직접30개 검수까지 확인했으므로 배포를 거부한다.
  file audit/기존10 DWG 성공을 신규 복원 성공으로 승격하지 않는다. 사례당 반복 노출과
  학습 가능한 spatial decoder가 다른 작은5/큰1028 실험으로 capacity 한계를 단정하지 않는다.
  본 실험의20을 재튜닝에 쓰거나 추가 GPU를 자동 실행하지 않는다.
