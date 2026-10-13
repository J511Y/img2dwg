# 실험 백로그 · 2026-10-13

모두 **planned, 미실행**. 준비 순서는 P1/P2를 우선하지만 계열 간 탐색을 제한하지 않는다. 각 ID는 실행 시 `docs/experiments/YYYY-MM-DD-EXP-XXX.md`와 private run manifest를 연결한다. 새 접근법도 계속 추가하며 비적합·실패를 삭제하지 않는다.

| ID | 방법 | 기술 가설·대조군 | 필요한 조건 / 중단·보류 기준 |
| --- | --- | --- | --- |
| EXP-001 | 의뢰 페어·전후상태·정합 감사 | 정합된 DWG가 올바른 supervision인가 | 권리·sample 검수, 틀린 상태/평면이면 학습 보류 |
| EXP-002 | GT CAD-IR→DXF→DWG roundtrip | 모델 없이도 writer가 엔티티를 보존하는가 | 실제 CAD/단위/버전 고정, writer 실패면 모델 성능 판단 보류 |
| EXP-003 | Hough/LSD/skeleton·line/arc fit | learned model 없이 어느 기하까지 가능한가 | clean/scan/photo별 baseline, 강제 직각 보정 on/off |
| EXP-004 | frontier VLM 직접 IR | 큰 VLM이 zero/few-shot으로 구조를 복원하는가 | 승인된 입력·schema·동일 budget, hallucination/invalid IR 실패 |
| EXP-005 | frontier global+tile·render critique | crop/제한적 repair가 작은 구조 오류를 줄이는가 | EXP-004 대비 iteration cap/총비용, test prompt tuning 금지 |
| EXP-006 | SegFormer/Mask2Former/RF-DETR+geometry | mask 인식이 고전 기하보다 noise에 강한가 | 동일 label/split·후처리, 모델 vs solver 효과 분리 |
| EXP-007 | HEAT graph | edge topology 직접 예측이 닫힘/연결을 개선하는가 | 실제 scan용 target·공식 protocol 대비 domain gap |
| EXP-008 | RoomFormer | room queries가 복잡한 polygon을 효율적으로 복원하는가 | shared boundary/문·창, room-only 결과의 CAD 제한 기록 |
| EXP-009 | Raster-to-Graph | autoregressive graph가 위상 일관성을 높이는가 | traversal/복잡도·외부 일반화, 긴 graph 실패 분석 |
| EXP-010 | Raster2Seq 공식 checkpoint/재학습 | polygon sequence가 기하·위상을 함께 개선하는가 | Linux extension·license·공통 writer, room F1과 DWG 분리 |
| EXP-011 | FloorplanVLM SFT→geometry reward | 구조 JSON 학습·reward가 schema/곡선 fidelity를 높이는가 | 공식 자원 확인/재구현 명시, reward hacking·GT leakage 검사 |
| EXP-012 | DINOv2→DINOv3 encoder ablation | dense feature가 적은 라벨로 선/엔티티를 보존하는가 | 동일 decoder/data/해상도, feature 품질 아닌 downstream 평가 |
| EXP-013 | I-JEPA/LeJEPA 도면 SSL | 미라벨 도면 학습이 라벨 효율·OOD를 높이는가 | train group만 SSL, label budget curve·인코더 대조군 |
| EXP-014 | SAM 3 annotation/HITL | proposal이 검수시간을 줄이는가 | human label 품질/시간 비교, masks를 CAD 정답으로 간주 금지 |
| EXP-015 | diffusion/flow vector reconstruction | 여러 geometry 후보가 불확실성을 개선하는가 | image-conditioned, observed fidelity·latency, 설계 생성 환각 분리 |
| EXP-016 | LLaDA/vision diffusion structured output | AR 대비 병렬 decoding이 비용·일관성을 개선하는가 | 실제 image-capable checkpoint 확인, 동일 IR validity 검사 |
| EXP-017 | 제약 최적화/ILP·graph repair | 동일 인식 결과의 topology repair가 개선되는가 | 직교·경사·곡선 별 ablation, 누락 구조 임의 생성 금지 |
| EXP-018 | teacher→소형 entity decoder 증류 | frontier 품질을 낮은 비용에 근사할 수 있는가 | teacher label 수동 검수·권리, holdout·동일 writer |
| EXP-019 | Jev / Laya / rule / 소형 classifier | typed routing·재시도·검수 판단이 E2E 비용을 낮추는가 | 동일 text/JSON 상태, 한국어·순서/후보수, calibration/test 분리 |
| EXP-020 | uncertainty+HITL active learning | 같은 검수예산으로 복원 품질이 더 개선되는가 | random sampling 대조군·시간 기록, test 선택 편향 금지 |
| EXP-021 | CAD render 합성+scan/photo augmentation | train CAD 합성이 실제 noise 일반화를 높이는가 | train-only layout, 합성/실제 gap·정합 유지·외부 holdout |
| EXP-022 | retrieval aided reconstruction | 유사 평면 검색이 입력 근거 복원을 돕는가 | train-only retrieval, 복제/다른 상태 오류·fidelity 검사 |
| EXP-023 | confirmed pixel 라벨↔사내 CAD 교집합/정합 | 두 감독 축을 연결할 joint gold가 실제로 얼마나 있는가 | 동일 도면·전후상태·unit·검수, 단순 파일명 매칭 금지 |
| EXP-024 | canonical geometry·host·dimension 검수 계약 | 기존 editor를 확장하면 정밀 CAD 정답을 일관되게 만들 수 있는가 | 검수자 일치도·변환/단위·unknown, 기존 운영 도구 변경은 별도 구현 |
| EXP-025 | dimension-assisted constraint solver | 명시 치수와 연결 제약이 벽 폭·간격 오차를 줄이는가 | image-only/solver-off 대조, OCR 오독·anchor 충돌·곡선 보존 |
| EXP-026 | homography vs learned dewarp vs canonical decoder | 이미지 평탄화가 실제 metric geometry 개선으로 이어지는가 | 종이 휨/원근별 실물 치수·선/간격 오차, DocRes 기존 보류 사유 |
| EXP-027 | 사내 CAD 합성→실제 aligned gold curriculum | known warp 감독이 실제 사진 복원으로 전이되는가 | group split 먼저, synthetic-only 대조·실제 holdout |
| EXP-028 | pretrained/domain-pretrained/full-scratch 대조 | 사내 감독 규모에서 어떤 초기화가 효율적인가 | 동일 decoder/data/예산, 수렴·라벨 효율·CAD 오차 |
| EXP-029 | 준공도면+변경전 영역 페어 정책 감사 | 사용자 지정 입력/target만으로 usable gold를 만들 수 있는가 | 실제 DWG 영역·unit·before/after·dependencies 검수, thumbnail GT 금지 |
| EXP-030 | VLM sequential/batched CAD actions | tool sequence/history 압축이 품질 유지하며 비용을 낮추는가 | 동일 tools·state·budget, 오차 누적·stop·repair 포함 |
| EXP-031 | visual proposal+Jev/Laya next-action selector | 다음 그리기 판단 위임이 E2E 비용을 낮추는가 | candidate recall/좌표오차와 selector 정확도 분리, none/ask_human |
| EXP-032 | paired-image vision action policy | 빠른 vision controller가 원본/현재 render의 차이에서 다음 동작을 찾는가 | 별도 학습 필요, long-horizon rollout·parameter·도구 검사 |
| EXP-033 | final DWG→partial-state action trajectory | unordered 최종 CAD로 controller 감독을 만들 수 있는가 | 합성 이력임을 명시, multi-valid-order·error-state, GT inference leakage 금지 |
| EXP-034 | 중간 HITL/잠금/국소 재복원 | 적은 개입으로 usable CAD 완료가 가능한가 | 수정시간·intervention·잠금위반·undo/resume·자동/HITL 지표 분리 |

결과 상태는 `planned/running/succeeded/failed/blocked/rejected`. blocked/rejected는 이유·근거·재개 조건을 기록한다. 후보별 반복·예산 상한은 첫 run 전에 확정한다. "가능한 방법을 모두 시도"는 후보와 실행 결과를 추적한다는 뜻이며 비교 근거 없이 무제한 GPU/API 작업을 시작하지 않는다.

## 추가 planned 실험

| ID | 후보 | 검사 |
| --- | --- | --- |
| EXP-035 | 전유부 ROI·출력 범위 검수 | 5개→40개, 옆집/공용부 혼입·경계 불명·직원 승인 |
| EXP-036 | 실제 세대 정방향/반전 확인 | 비대칭 anchor·의뢰 정보·직원 검수, 근거 없으면 unknown |
| EXP-037 | 필요한 표시 치수 전수 원장 | 값·단위·측정점·중심선/마감면·출력 연결·미판독/충돌 |
| EXP-038 | 중심선→치수→세부 요소 기준선 | 승인 GT, solver-off 대조·실제 residual·체인 폐합·roundtrip |
| EXP-039 | 단계별 전유부/치수 검수 UI | 원본 치수↔CAD 측정점·누락/충돌·잠금·수정시간 |

## 첫 실행 선택

현재 [벡터 우선 계획](2026-10-13-vector-first-training-plan.md)에 따라 EXP-012/021/024/025의 DINOv3 graph+합성 감독/치수 공통 경로를 먼저 구현하고, EXP-010 Raster2Seq를 비교한다. EXP-036 실제 반전 판별은 후속 기능으로 내리며 학습 target 방향 정규화와 구분한다. 전체 특징점 정합은 중단했다. GPU/모델 학습은 아직 planned다.

| ID | 추가 후보 | 확인 조건 |
| --- | --- | --- |
| EXP-040 | native CAD→업무 컴포넌트 catalog/factory | [구조 감사](2026-10-13-component-supervision-audit.md), block/분해 도형·style·dimension 관계 보존, 5개 재구성과 검수 |
| EXP-041 | component type/parameter/relation decoder | native representation 차이의 동등성, component AP·parameter/host/치수 오차, common writer |
