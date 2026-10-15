# 에이전트 작업 지침

## 2026-10-15 최신 완료 · EXP-054

실제 1,028개 본학습을 완료했으나 신규 도면 품질은 실패했다. job6ad0277a…는 COMPLETED,
21,928 update/quality-plateau 종료다. 선택 후보는1420 update의 best aed6d0e8…이며
기존 verified 모델6ca23df9… 전체를 동결한 새 pooled residual268만 parameter 학습이다.
전체 decoder/backbone fine-tuning으로 소개하지 않는다. fresh CPU 기존10은10/10·252/252,
별도 정정20은0/20·0/479다. 30개 직접 검수도 기존10 유지/신규20 실패를 확인했다.
모든30개 원본→serving 입력 pixel exact/native DXF 검사와 기존10 DWG 재열기를 마쳤다.
Space revision402d7958…/기존 five-case pilot pin05a545dd…는 그대로다. 실패 모델은 미배포다.
실행 연구노트·manifest/receipt/readback은 private run에 보존한다. 추가 GPU/20 재튜닝/Space
교체를 자동 재개하지 않는다. 후속은 새 사용자 요청 범위에서 진행한다.
아래 running/active goal/금지/승인 문구는 각각의 과거 요청 당시 기록이다.

## 2026-10-15 승인된 실행 범위 · EXP-054

사용자가 EXP-053 수정을 반영한 실제 TRAIN 1,028개 본학습, 기존10 유지 검사,
후보 고정 뒤 별도20 구조·치수 직접 검수와 비교 화면을 명시 승인했다.
통과한 모델만 private Space에 반영한다. 아래 1,028/20/Space 금지는 이전 요청의
이력이며 이번 범위에는 이 승인이 우선한다. 원본과 기존 배포는 보존한다.
EXP-054는 verified10 전체 모델을 동결하고 열 개 입력 특징 subspace에서 잔차0인
새 분기를 학습한다. 기존 adapter의 보호 span을 바꿔 추가5를 지우지 않는다.
CPU native10 preflight, 전체 train 노출, development16 품질 선택, 후보 SHA 고정,
별도20/fresh/직접검수/CAD roundtrip, 통과 시 배포 순서다. 유료 실행은 A100 단일
본학습180분/job240분 상한이며 cap을 수렴·성공으로 표현하지 않는다.
별도20은 학습 archive에서 제외하고 threshold/후보 선택에 쓰지 않는다.
학습 전 processed PNG hash 감사에서 기존20 중1건의train 중복을 찾아 미사용validation
1건으로 사전 교체했다. 정정20(기존19+신규1)의 index SHA는b7b6041898cb743fda7315e80500da5b1c82ceeb01905891c43ac7eaec245733다.
`data-audit/evaluation-index.json`을 사용하며 옛20을 묵시적으로 재사용하지 않는다.
원래20의과거결과는보존하고신규20과동일cohort로주장하지않는다.

## 2026-10-14 실행 권한

**최신 완료:** EXP-053에서현재사용자요청의TRAIN10 동시재현을완료했다. 연속9053/9060
checkpoint와fresh image CPU추론에서10/10·필수DIM252/252,직접10개검수와모델DXF→DWG→
DXF 재열기까지통과했다. 모델SHA6ca23df9…/decoder image-count-topk·dim consistency10mm·
project trust region10mm가한쌍이다. 원인/회고와실행연구노트·manifest/receipt/private readback을
보존했다. EXP-052는취소/partial이다. 아래active/running기록은이전실행권한·경과이며
현재추가GPU요청으로읽지않는다.1,028재학습/holdout20/Space는이번작업에서실행하지않았다.
10개train 재현을일반화성공으로확대하지않는다. 후속은새사용자요청범위로진행한다.

**지속 목표:** 사용자가 다음 출근 때 확인할 수 있도록 목표 달성까지 계속 진행하도록
명시 승인했다. 같은 실제 TRAIN10의 동시 구조/치수 재현을 active goal로 추구한다.
EXP-048 하드 guard의 신규학습 정지 결과를 보존하고 EXP-049의 조건부 잔차 adapter를
bounded job으로 비교한다. EXP-050은 같은 plain final 모델/Adam/assignment를 보존하고
학습률만 .0003/.0001로 낮춘다(각20분/suite50분/job65분). 필요한 작은 후속 실험을 이어가되 각 실행의 scope/cap/hash를
기록한다. EXP-050도신규2/5에정체됐다. EXP-051 반경 참조 후보는CPU diagnostic/rejected이며
기본 inference는None이다. EXP-052는동일4772 best 모델/Adam에서zero-output query
비선형 residual을 비교한다(각25분/suite65분/job80분). 실제 neutral function/Adam 상태 보존을
기록한다.1,028개 본학습/Space 배포와 holdout20 사용은 계속 금지다. 실패를 완료로 바꾸지 않는다.

**현재 요청:** EXP-048의 같은 TRAIN10에 좌표 업데이트 guard와 loss group balance를
각각/결합 비교한다. bounded A100 4조건만이며 구조·치수 직접 검수와 비교 화면을 남긴다.
10개 동시 통과 전 1,028개 본학습/Space 배포를 하지 않는다. 이전 20개/test는 튜닝에 쓰지 않는다.

**최신 사용자 요청은 작은 데이터의 원인 분리 실험이다.**
EXP-047-retention-ablation.md를 따른다. 원래5+train 추가5,
batch/capacity/count/loss 단일 요인과 관측된 LR/assignment 차이를 bounded GPU job으로
비교한다. **원인 확인 전 1,028개 재학습·Space 재배포 금지**다. validation20을 튜닝에 쓰지 않는다.
아래 회고 중단 상태는 이번 명시 요청의 작은 진단 범위에서만 대체된다.
EXP-047의 bounded 20조건 진단은 완료됐다. 원래5 첫 update 실패는 unexpanded에서도
재현됐고 Adam1e-6 원래5 단독은5/5·112/112로 유지됐지만 혼합10개는 실패했다.
다음 혼합 재현 통과 전 본학습/재배포를 재개하지 않는다. 32회 노출을 수렴 판정으로
쓰지 않으며 새 후속 GPU 실험은 이번 완료 상태에 자동 승계하지 않는다.

**직전 요청은 실험 회고였다.** 새 방법 선정·추가 GPU/API 실험·재배포를 중단하고
`docs/research/2026-10-14-experiment-retrospective.md`를 먼저 읽는다. full-v1은 실행
completed / 품질 failed이며 GPU 5개 0/5·0/112, 별도 20개 0/20·0/476이다.
직접 시각 검수도 실패다. full checkpoint SHA는 `52cdda59…`, 기존 Space의 승인된
five-case pilot SHA는 `05a545dd…`로 서로 다르다. 본학습으로 자동 교체하지 않았다.
아래의 이전 실행 승인은 새 유료 후속 실험의 승인이 아니다.

**최신 실행 정본:** `docs/experiments/2026-10-14-EXP-046-shared-decoder.md`와
`docs/harness/shared-graph-training.md`. shared node/component decoder를 실제 구현·학습했다.
사용자가 비교 화면의 오차를 수용하고 모델 배포·Space 갱신을 명시 요청하여 **5개 재현
실험 모델**의 private 배포를 승인했다. 이는 이전의 20개 전체 pass gate에 대한 실험
미리보기 예외이며, 검증 성공으로 재작성하지 않는다. GPU 5/5·112/112 치수, CPU 4/5·
112/112 치수, 별도 CPU 20개 0/20·0/476이다. 1,028개 본학습 bounded job은
quality-plateau로 종료했고 품질 실패다. 미통과 본학습 모델을 자동 교체하지 않는다.
`deploy_shared_space.py`가 최신 deployer이고 관측 선 기준선 deployer는 폐기했다.

사용자가 실제 준공도면–CAD 페어의 5개 재현 학습, 별도 20개 검증, 비교 화면과
검증된 모델의 Space 재배포를 명시적으로 요청했다. EXP-045와
`docs/harness/raw-pair-training.md`를 따른다. 실패한 모델은 재배포하지 않는다.
EXP-045 당시 두 실행은 각각 A100/90분으로 제한했다. 현재 실행 중인 작업으로
해석하지 않는다. 원본과 기존 운영 모델은 보존한다.

**후속 정정:** EXP-045의 primitive canonical-query 모델도 실패했고, 컴포넌트 구현 없이
step만 늘린 후속 GPU job은 사용자 지적 후 취소했다. `docs/research/2026-10-14-component-decoder-correction.md`
를 다음 실행 정본으로 사용한다. CAD-derived parameter factory의 재조립 성공과
학습 모델 예측을 엄격히 구분한다. WIN layer를 window 정답으로 쓰지 않는다.

## 시작 순서

**먼저 EXP-054 최종 보고서를 읽는다.** 기존10 보존과 신규 학습/검증 실패를 구분한다.
비교 화면은8781/full-continuation-review.html이며30개 전체와 필수 치수 누락을 표시한다.
EXP-053의10개 train 성공, 과거 full-v1 실패, 현재 EXP-054 실패는 별도 모델/프로토콜이다.
이번20은 기존19+학습 전 중복교체1로, 과거20의476DIM과 다른479DIM이다.

1. 이 파일, `README.md`, `docs/STATUS.md`, `docs/PROJECT.md`, `docs/DECISIONS.md`, `docs/harness/workflow.md`를 읽는다.
2. `git status --short --branch`, 원격, 관련 변경을 확인하고 기존 작업을 보존한다.
3. 작업에 따라 `docs/DATA.md`, `docs/CAD.md`, `docs/EVALUATION.md`, 조사·백로그를 읽는다.
4. 목표·완료 조건·미확인 사항을 짧게 알리고 현재 요청 범위에서 수행한다.

## 현재 권한과 범위

- 사용자는 원본 보존 데이터셋 pilot·최소 1,000개 페어·private HF 버킷에 이어 첫 모델 학습과 새 private inference Space 배포를 승인했었다. 원본·기존 Jippin 운영 모델을 변경하지 않는다. 최신 모델 실행 기록은 EXP-046/shared-graph-training, 현재 판단은 위의 실험 회고다. EXP-043/vector-training은 첫 합성 모델의 과거 기록이다. 유료 VLM/API 호출이나 무제한 후속 GPU 실험까지 승계하지 않는다.
- 후속 사용자가 구현·실험을 요청하면 해당 범위로 진행한다. 이 초기 상태를 영구적인 구현 금지로 해석하지 않는다.
- 데이터 수집·변경전 crop·ODA roundtrip·치수/정합 검증 실행기가 추가됐다. 학습/배포 하네스·CI·canonical CAD-IR schema validator와 구분한다.
- 사내 워크의 의뢰 연결 경로가 데이터 위치의 정본이다. 원본 폴더를 읽기 전용으로 사용하고 결과는 별도 run 폴더에 작성한다. 원본 DWG를 덮어쓰지 않는다.
- 실제 경로는 `configs/paths.local.json`, 로컬 조사 결과는 `local/`에 둔다. 둘 다 Git 제외다. 비밀은 환경 변수 또는 비밀 저장소에서 읽고 출력하지 않는다.
- 다른 저장소는 기본적으로 조사만 한다. 기존 `data-pipeline`·모델 저장소의 dirty 변경을 가져오거나 수정·커밋하지 않는다. 재사용할 때 출처 revision/hash와 라이선스를 기록한다.

## 연구·검증 규칙

- 목표는 편집 가능한 실제 DWG다. CAD-IR→DXF→DWG→실제 CAD 열기/수정/저장→render-back까지 구분해 증명한다.
- 현재 적용 전략은 `docs/research/2026-10-13-domain-reassessment.md`다. Jippin 원본 픽셀 오버레이와 canonical CAD 좌표·치수·간격 복원을 구분한다. 사내 CAD geometry와 직원 확정 wall semantics를 연결하고, generic wall/기타벽을 비내력 정답으로 승격하지 않는다. 사내 데이터 학습 필요성과 모든 weight의 scratch 학습 필요성을 구분한다.
- 사용자 추가 설계 계약은 `docs/research/2026-10-13-closed-loop-hitl-design.md`다. 주력 데이터는 같은 의뢰 폴더의 준공도면+변경전후.dwg이고 target은 검수된 변경전 평면 영역이다. thumbnail/왼쪽 위치만으로 CAD crop 정답을 확정하지 않는다. System-1은 두 이미지 기반 다음 CAD action controller 구상까지 포함하며 현재 Jev/Laya의 text/JSON 기능과 별도 vision policy를 구분한다. HITL 중간 수정·잠금·undo/resume을 정상 성공 경로로 설계한다.
- 좌표 변환·원점·y축·단위·축척·문 방향·레이어를 명시한다. 비직교 벽과 곡선을 무조건 직각화하지 않는다.
- 프론티어, Jev/Laya System-1, 고전 기하, segmentation, graph, sequence, JEPA, diffusion, hybrid 후보를 배제하지 않고 백로그에 등록한다. 명칭·입력 모달리티·실제 가용성을 출처로 확인한다.
- 동일 의뢰/건물/동일 평면 계열과 augmentation은 split 간 섞지 않는다. 테스트 자료로 프롬프트·threshold·routing을 튜닝하지 않는다.
- 성능 주장에는 데이터/split/hash, 표본수, metric 구현, 모델 revision, seed, 해상도, CAD 엔진, 비용·재시도 포함 조건과 원자료를 붙인다. 학습 loss·커밋·문헌 수치를 우리 성능으로 쓰지 않는다.
- schema 및 기하 검사 실패는 모델 confidence로 통과시킬 수 없다. System-1은 결정론적 검증을 보조한다.
- planned/running/succeeded/failed/blocked/rejected 상태를 구분하고 실패 로그와 다음 실험을 남긴다. 실패 실행을 succeeded로 재작성하지 않는다.
- 모델 카드의 zero-shot·보정·속도 주장은 해당 출처의 측정으로 표시하고 사내 데이터에서 재검증한다.
- 연구노트는 `$koita-research-notebook`, 증거 번들은 `$research-note-evidence-assets`를 적용한다. 중앙 `projects.json`과 주간·월간 프롬프트가 수집 정본이다. 셋업·문헌조사를 실험 성공으로 승격하지 않는다.

## 완료와 인계

변경 범위에 맞는 검증만 수행하고 실제 결과를 보고한다. 구현 시 meaningful unit/integration/CAD roundtrip 체크를 추가한다. 원본·고객정보·비밀이 Git에 포함되지 않았는지 확인한다. `docs/STATUS.md`, 필요시 결정/백로그/실험 기록을 갱신한다. 수정 파일, 검증, 남은 불확실성·다음 재현 방법을 짧게 전달한다.

## 최신 전유부·치수 요구사항

`docs/research/2026-10-13-vector-first-training-plan.md`가 현재 실행 정본이다. 핵심 목표는 입력 방향의 전유부 이미지→치수에 맞는 편집 가능한 DWG 벡터 그래프다. 실제 집의 좌우반전은 CAD 기존 기능/후속 편집으로 처리하며 복원 선행 gate로 두지 않는다. 전유부는 초기 수동 ROI를 허용한다. 중심선→전체 치수 제약→세부 요소와 치수 누락/geometry 검사는 필수다. 전체 특징점 정합 재시도는 중단했다. 5개 CAD로 감독/decoder smoke를 준비하고 CAD 합성 학습과 실제 표본 검수는 병행한다. 첫 주력은 DINOv3+graph decoder, 비교는 Raster2Seq다. 후보별 실제 실행 권한/비용과 planned 상태를 구분한다.

## 제품 판단 원칙

추가 요구의 목적과 우선순위를 판단하고 CAD 기존 기능·간단한 HITL로 해결할 부분을 제안한다. 사용자의 설명을 모두 선행 모델/자동화 gate로 승격하지 않는다. 후보를 나열하는 대신 첫 선택·근거·실패 시 전환 조건을 정하고 최종 DWG까지 이어지는 작은 수직 기능을 우선한다. 성과 근거 규칙은 유지하되 검수 자동화 완성이 모든 모델 개발의 선행 조건은 아니다.

## 컴포넌트 감독 보완

`docs/research/2026-10-13-component-supervision-audit.md`를 첫 학습 계획에 함께 적용한다. native BLOCK/INSERT·DIMENSION·style·관계를 먼저 보존하고 분해된 geometry는 검수 업무 컴포넌트로 묶는다. block 정의 존재를 active instance/semantic label로 승격하지 않는다. 매 LINE/handle/저장 순서를 이미지 획과 강제로 대응시키지 않는다. component catalog와 5개 factory/GT roundtrip을 확인한 뒤 component type/parameter/relation head를 학습한다. backbone 후보는 유지한다.

## 확장 데이터셋의 사용자 확정 정책

같은 의뢰 폴더의 준공도면과 변경전후.dwg는 동일 현장의 input/output이다. 별도 구조/특징점 정합·사람 페어 승인으로 수집을 막지 않는다. 파일 무결성, 변경전 crop, 컴포넌트 전처리 상태와 페어 관계를 구분한다. 최소 1,000개 실제 페어를 준비하며 augmentation/entity 수를 의뢰 수로 세지 않는다. 비공개 Hugging Face img2dwg 버킷 사용이 명시적으로 승인됐다. 실행은 `docs/harness/dataset-release.md`를 따른다.

## 첫 학습·서빙의 해석

**실제 실패 정정:** EXP-044가 EXP-043의 제품 해석을 대체한다. 첫 coordinate 모델은
raw 준공도면에서 실패하여 기본 사용을 중단했다. 관측 선 기준선을 학습 모델 복원이나
완성 CAD로 소개하지 않는다. 파일/동작 검증을 실제 구조 복원 품질로 승격하지 않는다.
원본 RAW 입력–canonical CAD 감독과 typed component/관계·치수 제약을 우선하고,
실제 입력의 train 재현/별도 validation의 시각·기하/치수 검사 전에 기본 배포하지 않는다.

**아래 문단은 EXP-043 당시의 상태다. 현재 구현/학습 상태는 EXP-046과 회고를 따른다.**
DINOv3 frozen + 4-slot component coordinate baseline이 구현됐다. source-identity group의
train 1,028개/validation 128개 CAD 합성으로 학습하며 raw 준공도면 coordinate fine-tune과
숫자 치수/OCR·host association은 아직 미실행이다. 세부 성능은 EXP-043과 private receipts로
확인한다. Space의 `?` 치수/단위 미확정 출력은 완성 DWG가 아니다. geometric role 후보를
confirmed wall semantics로 승격하지 않는다. native block GT factory와 모델 symbol envelope도
구분한다. HF app는 SVG path/편집 가능한 DXF를 반환하며 source CAD를 조회하지 않는다.
Space revision·checkpoint SHA·실제 인증 upload/download를 검사한다. 원본/정답 retrieval,
mask contour, embedded raster를 모델의 좌표 예측으로 표시하지 않는다.
