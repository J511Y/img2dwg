# 현재 상태 · 2026-10-14 KST

## 현재 완료: 기존5 유지 + 추가5 동시 재현

[EXP-053](experiments/2026-10-14-EXP-053-ranked-consistent-decoder.md)에서10/10·필수치수
252/252를연속2개의서로다른checkpoint와fresh image CPU추론으로확인했다.
기존F1 .999284692/추가 .998430813이며누락·추가치수0,old function drift0이다.
직접10개시각검수와모델DXF→DWG→DXF 재열기도통과했다. 실제CAD UI edit/save는미확인이다.
원인은이번작은데이터의raw 구조가아니라과잉DIM9개의무검증hard projection이었다.
image count ranked set/치수equation consistency/보정trust region으로수정했다.
단,EXP-047의본학습raw update불안정과구분한다.10개는train 재현이고일반화검증은아니다.
1,028개 본학습/holdout20/Space는새로실행하지않았다.모델SHA `6ca23df9…`,job`6acf8d5b…`.
비교화면`http://127.0.0.1:8780/retention-review.html`,실제DWG/DXF 다운로드포함.

## 지속 목표: 실제10개 동시 재현

사용자가 목표 달성까지 계속 진행하도록 명시 승인하여 active goal을 설정했다.
EXP-048의4조건은 completed지만 신규5는0/140이며10개 동시 재현은 실패다.
guard 단독/결합은 기존5 5/5·112/112를 유지했으나9/256 및12/336 update만 허용했다.
다음 [EXP-049](experiments/2026-10-14-EXP-049-protected-adapter.md)은 실제 입력 특징의
보호 subspace에서 잔차0인 adapter를 사용한다. CPU preflight는 기존5 5/5·112/112,
신규5는0/5·0/140이었다. EXP-049 GPU 두 조건 중 plain이 완료됐으며 최고 점수
checkpoint의 별도 CPU 재검사에서 기존5 5/5·112/112, 신규5 2/5·112/140이다.
plain 최종은 신규0/5·44/140으로 다시 악화했다. balanced도 완료했으며 신규0/5·43/140이다.
좋은 중간 결과와 최종 결과를 구분하며10개 동시 통과를 선언하지 않는다.
관측된 흔들림에 대한 [EXP-050](experiments/2026-10-14-EXP-050-adapter-refinement.md)은
같은 final checkpoint/Adam/assignment를 보존한 학습률 비교를 완료했다.
EXP-050 두 조건 모두기존5/5·112/112,신규2/5이며finalDIM89/140·96/140이다.
EXP-051 물리 참조 후보 검사는anchor 오류까지 있어해결 가설을 기각했다.
EXP-052는같은source best/Adam/assignment에서query 비선형 residual만비교한다.
CPU neutral 초기화는실제10개180개 출력tensor의bit equality와기존5/5·신규2/5를 확인했다.
EXP-052는원인재진단으로cancelled-diagnostic-pivot 상태다. before_constraints를읽으니
현재model의raw 구조는이미재현됐으나3개사례의과잉DIMENSION9개가hard projection을
오염시켜최대3.8m 이동했다. [EXP-053](experiments/2026-10-14-EXP-053-ranked-consistent-decoder.md)은
image-count ranked set/치수기하일치/보정trust region을분리검사했다. 같은.0003 weight는
10/10·252/252 nativeCPU통과다. 다른.0001 weight는fresh9/10·251/252로미채택이다.
연속2checkpoint·fresh/직접검수/DWG 재열기 전최종완료로선언하지않는다.
원본/holdout/Space를 보존한다.

## 현재 실행: 좌표 제한과 loss 균형의 분리 비교

[EXP-048](experiments/2026-10-14-EXP-048-guard-balance.md): 같은 TRAIN10에서
control/좌표 guard/loss group balance/결합4조건을 완료했다. 신규5는 모두0/140으로
실패했으며 guard가 있는 두 조건만 기존5 fixed 진단5/5·112/112를 유지했다.
legacy prefix-count 추론은 두 조건 모두4/5로 fixed 결과와 구분한다.
guard는 node/anchor/숫자 치환 좌표mm의 step2mm·기존5 누적10mm를 검사하며 거부 시
가중치와 Adam 상태를 복구한다. loss는 초기 shared gradient의 큰 그룹만 downweight한다.
10개 실제 구조·치수 동시 통과 전 1,028개 본학습/Space 배포를 하지 않는다.
직전 EXP-047과 원본/holdout/Space를 보존한다.

## 최신 작업: 작은 데이터의 5개 재현 유지 원인 분리

사용자 후속 요청으로 [EXP-047](experiments/2026-10-14-EXP-047-retention-ablation.md)을
구현했다. 원래5+train 추가5, batch/capacity/count/loss와 LR/assignment 단일 요인이다.
CPU 시작 검사 4/5·112/112로 기존 결과를 재현했고 관련18개 검사가 통과했다.
bounded GPU 비교16개와 LR 확인4개가 모두 completed다. 20개 조건은 같은10개의
train 사례만 사용했다. 원래5 단독 Adam1e-6은 두 노출 순서 모두5/5·112/112,
혼합10개는 원래60/112·62/112로 악화하고 추가0/140이다.
첫 update의 물리 좌표 불안정과 지배적인 node loss gradient를 확인했지만 혼합 유지/재현은
미해결이다. 310개 최종 DXF의 실제 audit/단위/DIM count와20개 checkpoint SHA를 대조했다.
1,028개 재학습·Space 재배포와 validation20 사용은 하지 않았다. 다음에도 금지 상태를 유지한다.

## 앞선 본학습 판정: 완료·품질 실패, 실험 회고

사용자 요청으로 새 방법 선정·추가 실험·재배포를 중단하고
[상세 리뷰](research/2026-10-14-experiment-retrospective.md)를 작성했다.
HF job `6acef50cc662881452234b24`는 completed, 종료 이유 quality-plateau,
28 epoch 진입/28,157 updates, trainer elapsed 4,323.4385초다.
checkpoint SHA256 `52cdda59bb3023c7c71f8d9774dcfb59fb28a0a13ee31d0c75e5d3d82ca86138`.

| 본학습 최종 선택 모델, GPU | 통과 | 구조 F1 | 숫자·위치·실제 길이 joint 치수 |
| --- | ---: | ---: | ---: |
| 원래 학습 5개 | 0/5 | 0 | 0/112 |
| 별도 20개 | 0/20 | 0.0002080570 | 0/476 |

전체 20개 입력/GT/실제 예측을 직접 시각 검수했으며 모두 구조 복원 실패다.
native DIMENSION 804개, DXF audit error 0이지만 정확한 도면은 아니다.
검수 기록은 원 receipt와 별도로 보존했다. 직원의 승인을 주장하지 않는다.
선택된 본학습 모델을 Space에 올리지 않았다. 아래 Space는 별도 tiny-v4 pilot다.

완료된 CPU 초기화 대조: 원래 5개 input/컴포넌트 target 불변, 동일 capacity에서
tiny 원본과 full 확장 직후 모두 4/5·112/112였고 full 학습 후 0/5·0/112다.
확장 즉시의 복사 오류만으로 설명되지 않으며 학습 중 악화가 관측됐다.
이 회고 시점에는 개별 원인이 미분리였다. 위 EXP-047이 최초 update 민감도를 좁혔으며,
전체 본학습 실패를 모두 설명하는 단일 원인 규명은 아직 아니다.
모델/데이터 크기만으로 해결된다고 결론 내리지 않는다.

## 현재 배포: 공유 노드 컴포넌트 5개 재현 실험 모델

[EXP-046](experiments/2026-10-14-EXP-046-shared-decoder.md): tiny-v4의 GPU 재현은
5/5 통과·구조 F1 0.999523·치수 112/112다. stable quality pass로 종료했다.
CPU 실제 원본 입력 검사는 4/5·구조 F1 0.983548·치수 112/112이며 1개는
geometry/component/shared-reference 기준 미달이다. 별도 CPU 20개는 0/20·치수 0/476이다.
같은 체크포인트의 GPU/CPU 측정 조건을 구분하며 5개 암기 재현을 일반화로 소개하지 않는다.

사용자가 오차 수용 후 모델 배포·Space 갱신을 명시 요청하여 **5개 재현 실험 모델**로
private Space를 갱신했다. 실제 인증 업로드→vector SVG→native editable DXF 다운로드를
검사했다. 예제 1개에서 INSERT 75/DIMENSION 19, mm, audit 0, raster 0이며 선택
100mm 보정 전후의 치수값·공유 좌표 보존도 확인했다. 실제 다운로드 DXF의 ODA
DWG→DXF 재열기는 통과했다. 실제 업무 CAD UI 수정·저장과 직접 DWG 서빙은 미실행이다.

모델: `youjunhyeok/img2dwg-shared-components-v1`, SHA256
`05a545dd74100f072e56b359fcfa1006eae39e104b076f15ad10df75d0694911`.
Space revision `402d7958db12605f8346b682e64a51f0d1a5c395`, private CPU basic.
학습된 feature/parameter 기반 예측이며 원본/정답 CAD retrieval이나 관측 선 fallback이 없다.

1,028개 본학습은 위의 completed/quality-failed 판정이 정본이다.
16개 development로 checkpoint를 선택하고 별도 20개는 종료 후 한 번 평가했다.
GPU 학습 상한 90분, job 전체 상한 150분은 fit 판정이 아니다.
기존 five-case pilot 배포와 본학습 품질 실패를 구분한다.

## 구현 및 초기 실행 기록

사용자 후속 승인에 따라 `structured.py`/`graph_decoder.py`/`graph_constraints.py`/
`graph_evaluation.py`와 [새 하네스](harness/shared-graph-training.md)를 구현했다.
native path 177개와 TEXT/MTEXT 196개를 첫 5개 정답에 추가 보존했고,
독립 미분류 LINE은 2,542→1,379개다. 작은 native 부분은 train-only local
prototype로 추가 보강한다. semantic wall/window/room의 완성된 라벨을 주장하지 않는다.

5개 GT factory는 구조와 치수 112개를 보존했다. 실제 이미지에서 실행한 초기
node pointer 모델은 연결·정밀도 미달로 중단하고 실패 자료를 보존했다.
node 위치/참조 gradient 분리, 위치 기반 proposal, 숫자 parameter, FP32/joint-batch
보강 버전 tiny-v4는 위의 stable five-pass로 종료했다. 별도 20개는
체크포인트 선택에 사용하지 않았다. 초기 실패·취소 기록은 보존한다.
private 새 비교 화면은 실제 모델 예측이며 GT factory와 구분한다.

## 과거 기록: EXP-045 실제 페어 5개 학습·20개 검증

[EXP-045](experiments/2026-10-14-EXP-045-real-pairs.md): v0.2의 실제 준공도면에서
5개 학습/20개 검증을 고정했고 native 치수 588개를 보존했다. 입력은 합성이 아니다.
첫 실제 학습 12,000 steps에서 학습 5개 치수 숫자 112개는 모두 맞았지만 길이/위치가
틀려 0/5 통과, 별도 20개도 0/20 통과였다. 첫 모델은 Space에 올리지 않았다.
물리 길이 loss/전체 5개 joint batch/예측 치수 constraint projection의 후속 실행은
컴포넌트 출력이 구현되지 않았다는 사용자 지적을 확인한 뒤 canceled다. 8,000-step
체크포인트와 마지막 로그를 보존했고 후속 실행의 20개 평가/모델 배포는 하지 않았다.
25개 비교 화면은 첫 실제 모델의 실패 결과이며 정답으로 바꿔치기하지 않는다.
20개 검증 결과로 학습/threshold/checkpoint를 선택하지 않는다.
노출된 20개는 pilot validation이며 독립 최종 test라고 부르지 않는다. 취소된 후속
실행에서 새로운 20개 평가 결과를 만든 것으로 기록하지 않는다.

당시 [컴포넌트 정정](research/2026-10-14-component-decoder-correction.md): CAD-derived
조립기에서 문짝+원호 34개, 벽 양면 148개, 사각 루프 240개를 parameter로 재조립하고
422개 실제 BLOCK/INSERT를 작성했다. 5개 GT의 형상과 치수 112개를 보존했다.
이는 모델 예측이 아니다. 원래 도형 4,306개 중 2,542개(59.03%)는 아직 미분류다.
완성된 컴포넌트 정답/새 decoder 학습/모델 Space 재배포는 미완료다.

## 과거 기록: EXP-044 실제 스캔 복원 실패 · 모델 기본 사용 중단

사용자가 제공한 실제 입력 결과에서 거대한 원호/흩어진 선이 확인됐다.
첫 모델은 raw 준공도면 페어를 학습하지 않고 CAD 합성 렌더만 학습했다.
이미지상의 중심점과 canonical CAD 좌표를 같은 국소 회귀로 처리한 설계,
독립 endpoint/3점 ARC와 구조 제약 부재, 실제 시각 품질 없이 파일 생성만 검사한
출시 판단이 실패했다. 아래의 학습/서빙 성공은 파일/실행 계약만이며 제품 성공이 아니다.

실패 모델을 Space 기본 출력에서 제외했다. 현재 출력은 명확하게 표시한
관측 선 검출 기준선으로, 학습된 CAD 복원/중심선/치수/컴포넌트 출력이 아니다.
첨부 사례는 원본 해상도가 없는 screenshot crop으로 실패 재현했다.
[EXP-044](experiments/2026-10-13-EXP-044-real-scan-failure.md)를 정본으로 읽는다.

다음: 실제 준공도면→canonical CAD 컴포넌트 감독, 입력 픽셀의 국소 좌표 회귀와
canonical 출력 구분, 관계/제약·ARC parameterization, 실제 5개 train 재현과
20개 별도 validation 구조/치수 평가. 실제 도면 품질을 확인하기 전 모델을 기본 배포하지 않는다.

## 과거 기록: EXP-043 첫 학습·벡터 inference Space

사용자 승인으로 DINOv3 frozen + 4-slot component coordinate head를 학습하고 별도
[private Space](https://huggingface.co/spaces/youjunhyeok/img2dwg)에 배포했다.
CAD 합성 train 1,028/validation 128개, tiny 100/full 2,500 steps, A100/BF16.
합성 validation 64개 선분 F1 0.396, curve 0.102, dimension candidate 0.016.
이 수치는 raw 준공도면/mm/치수 숫자 성능이 아니다. near-family 검수도 미완료다.

첫 FP16 overflow 실패와 single-slot/endpoint 불일치 baseline을 보존하고 endpoint
정규화/4-slot/border 후보 제거·등방 compact로 보완했다. 현재 학습 정답 충돌 누락
3,248개는 별도 제한으로 기록한다. 모델 출력의 구조/치수 정밀도는 완료 기준에 미달한다.

Space는 crop, 벡터 확대/이동, SVG/DXF/좌표/receipt 다운로드를 제공한다. inference에
source CAD 접근이 없으며 SVG에는 raster embed가 없다. 치수 후보 `?`, 축척 미확정은
unitless다. 직접 DWG 다운로드와 실제 CAD UI 편집 검증은 미완료다.
5개 GT factory는 ODA DXF→DWG→DXF에서 DIMENSION 148/INSERT 26과 mm를 보존했다.
이는 모델 복원 정확성과 별도 검사다.

최신 [EXP-043](experiments/2026-10-13-EXP-043-vector-first.md),
[실행 하네스](harness/vector-training.md)를 읽는다. private run/model/deployment/실제
업로드 receipt는 local config에서 찾는다. 다음은 실제 domain fine-tune,
dimension text 위치 감독/OCR·association·solver와 native 업무 컴포넌트/host 관계다.

아래는 단계별 당시 기록이다. 초기 미실행 상태를 현재 학습 금지로 해석하지 않는다.

## 완료한 기본 세팅

- empty GitHub repo를 현 폴더로 clone하고 목표·README·AGENTS·선택/검증 기준을 구성했다.
- 데이터/CAD/평가 계약, 선언적 harness 설정, 실험·run manifest·PR/issue 양식을 추가했다.
- 공식 논문·repo·model card 기반 조사 보고서와 22개 planned 실험 백로그를 작성했다.
- Jev/Laya의 공식 System-1 계약과 HF Laya 모델·demo Space를 확인했다. JEPA/LLaDA와 구분했다.
- 워크 설정의 입력 루트 접근과 로컬 ODA 설치를 확인했다. 실제 설정·비공개 조사 상세는 `local/`에 보관한다.
- 기존 data-pipeline 페어 DWG 10개 header를 소량 읽었으며 모두 `AC1032`였다. 업무 전체 버전 분포나 목표 버전을 확정하는 표본은 아니다.
- 중앙 연구노트 지도에 7번째 프로젝트로 등록하고 기존 주간·월간 예약 prompt를 갱신했다. 정규화 prompt 일치·기존 주기/모델/프로젝트 보존을 확인했다.

## 초기 세팅 시점의 미실행과 불확실성

모델/변환/학습 코드, 실행 하네스/CI, 데이터 전체 스캔·페어 승인·split, dataset 다운로드·GPU/API 호출, DWG 생성·실제 CAD 열기/수정/저장, metric 측정·배포는 미실행이다. 설치 확인은 CAD 호환성 검증이 아니다.

target CAD·DWG version, usable pair 수·정합·권리·외부처리, 예산, metric threshold, 프로젝트 라이선스는 확인 필요다. 과거 data-pipeline 작업 트리는 재현 검증 전 성과로 승계하지 않는다.

## 사용자 추가 맥락 재조사 · 2026-10-13

[사내 자산 기반 보고서](research/2026-10-13-domain-reassessment.md)를 추가했다. Jippin 소비 코드·직원 확정 라벨·가공 manifest·HF endpoint 설정·기존 CAD-IR 보고 JSON을 읽기 전용으로 확인했다. 새 모델 실행·DWG 변환은 하지 않았다. 현재 후보 backlog는 28개이며 초기 22개 목록에 joint gold·dimension solver·dewarp·사내 학습 대조를 추가했다. 공개 후보 목록보다 사내 geometry/semantics 감독과 정밀도 계약을 우선한다.

## 반복 그리기·HITL·페어 조건 추가 · 2026-10-13

[사용자 구상 설계](research/2026-10-13-closed-loop-hitl-design.md)를 작성했다. 원본+현재 CAD render에서 다음 drawing action을 판단하는 세 후보, 준공도면+변경전후.dwg의 변경전 target, final CAD→합성 action trajectory, 중간 사람 수정·잠금·undo/resume을 반영했다. 후보는 34개다. 첨부 thumbnail과 기존 crop 코드를 읽었으며 원본 재추출·모델 실행은 하지 않았다.

## 다음 구현 작업

## 데이터 pilot 실행 완료 · 2026-10-13

[EXP-029](experiments/2026-10-13-EXP-029-pilot.md): 운영 의뢰 인덱스 기반으로 조건에 맞는 후보 60개를 찾고 40개 변경전 DXF/DWG를 추출·ODA 재열기했다. DIMENSION 913개 보존 pass, 원본 80개 hash/size/mtime 보존 확인. 자동 정합은 weak/degenerate 38·신뢰할 match 없음 2로 자동 승인 0이다. 최종 entity duplicate 0, header/loader warning 3을 기록했다. 모델 학습·직원 승인·gold split은 미실행이다.

수집/검수 runner와 비공개 HTML 비교 화면, 실제 실행 report notebook·manifest/receipt를 추가했다. [실행 안내](harness/dataset-pilot.md), private output 위치는 `configs/paths.local.json`을 참조한다. 직원은 비교 화면에서 before 영역·정합·치수·대응점과 메모를 검수하고 JSON으로 내보낼 수 있다.

다음은 입력 ROI/대응점과 변경상태 승인, 종이 휨·도면 차이 분리, 3개 header/loader warning 진단이다. 승인되지 않은 40개를 학습에 투입하지 않는다. 실제 CAD UI의 수정·저장은 별도 확인한다.

## 최신 실행 우선순위 수정

사용자 요청으로 전체 특징점 정합 재시도는 중단했고 기존 결과를 보존했다. 다대일 대응 방지 단위 테스트 9개는 통과했으나 실제 40개 재정합은 하지 않았다.

현재 정본은 [벡터 우선 학습 계획](research/2026-10-13-vector-first-training-plan.md)이다. 입력 방향의 전유부→치수에 맞는 DWG가 핵심이며 실제 좌우반전은 CAD/후속 기능으로 처리한다. 초기 전유부 선택은 수동 ROI를 허용한다.

다음 구현은 5개 CAD로 supervision/GT writer 확인 → DINOv3 freeze+graph decoder tiny 학습 → 합성 학습/Raster2Seq 비교 → 실제 표본 fine-tune → preview/HITL/새 DWG 생성이다. 합성 학습 준비와 실제 검수는 병행하며 전체 40개 승인 완료를 학습 개발 선행 조건으로 두지 않는다.

이번에는 공식 모델 metadata와 Raster2Seq 512 config를 확인했고 DINOv3 weight dry-run만 했다. 모델 weight 다운로드·추론·학습·GPU job·운영 변경은 미실행이다. decoder/치수 association/solver/UI는 계획 상태다. 이전 913개 보존 pass는 입력 치수 완전성/실제 길이 검증이 아니다.

## CAD 컴포넌트 구조 감사 완료

[40개 감사](research/2026-10-13-component-supervision-audit.md): 로컬 source/before/reopened 120개 읽기 전용 검사. 변경전 DIMENSION 913개, INSERT 76개(13개 파일), 명시 GROUP 0개 파일, DIMASSOC object 700개를 확인했다. 보유 block 정의와 현재 사용 인스턴스·분해된 도형을 구분했다. 120개 SHA/size/mtime 무변경, 신규 auditor 테스트 2개 pass. 실제 컴포넌트 의미 승인·DIMASSOC 관계 검증·factory/모델 학습은 미실행이다.

첫 학습 전 component catalog와 5개 factory/GT roundtrip을 수행한다. DINOv3 backbone 선택은 유지하며 출력부를 컴포넌트 type/parameter/관계와 내부 geometry로 구체화한다. 원본/기존 pilot receipt는 보존했다.

## 1,000개 이상 확장·원격 릴리스 완료

[데이터셋 v0.2](research/2026-10-13-dataset-v02-release.md): 1,400개 same-case 페어 수집/ODA/native 전처리 성공. 자동 변경전 조건을 충족한 1,383개를 새 비공개 HF img2dwg 버킷에 저장했다. 17개 영역 불확실은 별도 보존. DIMENSION 32,413개 crop 보존, source 무변경, exact pair/split identity 누수 0. 전체 22 shard 및 5,532 primary artifact 원격 readback 해시 일치. 테스트 15개 pass.

이 사용자 확정 페어 정책이 앞선 구조 정합/사람 페어 승인 수집 gate를 대체한다. 업무 semantic assembly와 DIMASSOC target 보강·near-family grouping은 다음 전처리 상태이며 모델 학습은 미실행이다. 실행 방법은 [릴리스 하네스](harness/dataset-release.md), private URI/run은 local config에서 찾는다.
