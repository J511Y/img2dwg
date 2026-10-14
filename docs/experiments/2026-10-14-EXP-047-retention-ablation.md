# EXP-047 · 본학습 전환의 5개 재현 상실 원인 분리

상태: completed diagnostics / 원래5 단독 작은-update 재현 유지 / 10개 혼합 실패 / 배포 없음.
날짜: 2026-10-14 KST. 사용자 승인 범위: 작은 데이터의 단일 요인 비교·재현/유지 검사.
**1,028개 재학습과 Space 재배포는 금지한다.** 원본/이전 실행과 validation20을 보존한다.

## 질문·원자료 대조

EXP-046의 tiny-v4를 full 구조로 확장한 직후까지 CPU 4/5·치수112/112가 유지됐으나,
1,028개 본학습 후 원래 5개도 0/5·0/112가 됐다. batch, capacity/count 경로,
실질 loss 감독과 optimizer 재시작 중 어느 변화가 작은 표본에서도 이 악화를 유발하는가?

tiny-v4/full-v1 원본 archive의 graph_decoder.py와 structured.py는 byte-identical이다.
decoder/loss SHA256 c795095bf48bb6f1f44c2d816bd05997187c3ae7b8722504bc154ff0896e7c8a.
loss 가중치 공식을 변경했다는 근거는 없다. 숫자 digit/클래스 확장으로 감독의 효과는
달라질 수 있어 sensitivity control을 둔다. tiny-v4는 quality-history에서 한 번 LR*.3 후
통과했고 full은 새 Adam/LR1e-4로 시작했다. optimizer 상태는 checkpoint에 없었다.

## 고정 데이터·초기 상태

- v0.2 train의 원래 5개와 추가 train 5개. 추가 표본은 SHA 순서, group 중복 제외,
  node 959 초과~1,200 이하/component 726 초과~950 이하라는 사전 규칙으로 선택한다.
  이는 capacity를 자극하는 진단 표본이며 대표성/일반화 평가가 아니다.
- 원래 치수112개 + 추가 치수140개. 기존 development/validation20/calibration/test 미사용.
- 원본 input PNG/target/components/관측 feature의 hash를 고정한다. 실제 EXIF512
  DINOv3 CPU 관측 feature를 동일하게 캐시하며 CAD render/target은 encoder에 넣지 않는다.
- 모든 비교는 동일 expanded initializer에서 다시 시작한다. source tiny SHA는 05a545dd…
  full의 vocabulary/8-coordinate-digit/6-size-digit 및 최대 query reserve는 공통으로 유지한다.
- 새 Adam, FP32/TF32 off, gradient clip5, 기본 LR1e-4, 동일 이미지 노출 순서.
  CPU 시작 검사: 원래5 4/5·구조F1 .983548·치수112/112, 추가5 0/5·0/140.
  실제 SVG/native DXF 재열기 검사도 실행했다. GPU 시작 조건은 따로 기록한다.

## 단일 요인 비교

| 비교 | 통제 |
| --- | --- |
| 5개 joint / 한 장씩 update / 5장 gradient accumulate | 같은 image exposure. online은 Adam update 수가 5배임을 기록. joint↔accumulate로 update 빈도 분리 |
| mixed joint / online / accumulate | 10개 모두 동일 fixed train capacity N1198/C951 |
| mixed accumulate fixed / variable | virtual batch5·update 빈도 동일. variable은 GT count+32, min N959/C726. capacity 이외 동일 |
| 같은 checkpoint의 fixed / image-predicted count 추론 | 가중치 동일. 부족한 capacity 사례 수를 기록. count oracle/fixed 진단을 실제 일반화 성공으로 소개하지 않음 |
| variable baseline / count loss0 | 단일 count gradient 제거. global clipping 영향 포함 |
| variable baseline / 기존 digit loss | leading zero 숫자 감독만 제외. nonzero prefix는 실행 거부 |
| variable baseline / template loss0 | 단일 auxiliary template 감독 제거. 실제 기존 loss 공식 변경 주장이 아님 |
| 동일 조건 LR1e-4 / 3e-5 | 실제 마지막 tiny LR와 full restart LR 차이 |
| 동일 조건 assignment refresh20 / refresh1 | 캐시 갱신의 단일 요인 진단 |
| 5개 online/accumulate 순서 seed 반복 | 초기 weight는 동일, 노출 순서를 20261015로 재검사 |

예측 개수와 query capacity는 별도다. fixed 진단 평가에서 원래5는 N959/C726,
추가5는 N1198/C951로 유지하고, 실제 image-predicted count 평가를 별도로 실행한다.
매 학습 사례의 정답 수가 capacity를 넘으면 학습을 거부하며 정답을 잘라내지 않는다.

## 판정·자원·해석

공통 exposure dose 0/1/2/4/8/16/32회에서 원래5 유지와 추가5 재현을 검사한다.
이는 **동일 학습량의 원인 진단 창**이며 32회를 fit/convergence로 선언하지 않는다.
joint/accumulate/online update 수와 실제 노출 수를 함께 기록한다. 시간 cap 때문에
중단되면 공통으로 완료된 dose까지만 비교하고 partial을 completed fit으로 바꾸지 않는다.

geometry/치수 위치 matching10mm, DIM 숫자/실제 길이/잔차1mm, structure .90,
component/reference .95, 필수 치수 coverage와 잘못된 참조·제약 충돌을 확인한다.
중간 검사는 geometry-only candidate로 표시하고 DXF audit 성공을 만들어 넣지 않는다.
초기/최종에는 실제 native DXF를 작성·재열어 audit하고 완전한 passed와 구분한다.
원래5의 DIM112/112 또는 구조가 떨어진 최초 dose를 기록하며 숫자만 맞는 결과를 통과시키지 않는다.

첫 GPU A100 job은 suite65분·condition4분의 자원 cap, job 전체90분이다.
원래 모델의 첫 update CPU 대조에서 원인 후보를 좁힌 뒤 같은 10개·같은 initializer에
LR1e-6만 바꾼 4개 조건을 두 번째 bounded A100 job으로 확인한다. 추가 suite15분,
job25분이며 새로운 데이터/1,028개 재학습/Space 배포는 없다.
단일 seed/진단 표본의 차이는 관측된 sensitivity다. 실제 전체 학습 실패의 유일 원인으로
확정하려면 다른 요인을 배제하는 일관된 대조가 필요하다. 복합 변경의 효과를 한 요인으로 돌리지 않는다.

실행: prepare_retention_ablation.py → train_retention_ablation.py.
비교 실행기는 10개의 train 입력만 허용하고 full trainer/deployer를 호출하지 않는다.
unit/integration18개 통과: default loss/관계, joint↔accum gradient, count만 제거,
숫자 truncation 거부, 초기 가중치 label-aware expansion, 단일 요인 matrix.

Private run: outputs/retention-ablation-2026-10-14-v1/.
GPU 실행·종료 및 독립 artifact 검사를 새 receipt에 기록했다.

실행 job: 6acf22715ccb47ba0f792733. code archive SHA256
8f347937ca17be801898902ca21713d97362c165261445fdad61bf152160291a,
data archive SHA256 ac654cf5bf2923dba897465312d9c6f0ea30216ffa7d7675fb3f4fef32d9ee28.
원격 byte readback을 대조한 뒤 시작했다. Space revision 402d7958…와 model repo
6c51ac29…는 시작 전 읽기 전용으로 기록했다. 비교 시작을 성공 결과로 소개하지 않는다.

두 번째 package의 code archive SHA256은
fe5ccfb6f388ba48aeacfd855305dc968e2ca6e151304033dcad1235ffc1a3c1,
data archive SHA256은 257ad2f011abc8f75952a5b4031efbae9da2bd398d0add49f5de1582c9984d2f다.
관측 encoder는 DINOv3 ViT-B/16 frozen, revision
5931719e67bbdb9737e363e781fb0c67687896bc다. metric 구현은 graph_evaluation.py,
실행기는 train_retention_ablation.py이며 최종 Git revision의 코드를 증거 번들로 연결한다.
v1/v2는 input/GT/feature/initializer byte를 대조했고 v2의 LR-only 조건은 같은 모델로 시작했다.

## 종료 결과 · 2026-10-14

첫 job은 16/16 조건 completed, trainer elapsed 3,170.2267초다.
두 번째 job 6acf28bf5ccb47ba0f7937b5는 LR-only 4/4 조건 completed,
elapsed 710.6705초다. 종료 상태는 진단 실행 완료이며 모델 일반화/수렴 성공이 아니다.
모든 조건은 동일 expanded initializer SHA256
6832b79afda3470ae49c4b80f56287fdec2ebb5f853e90e779b55ea6216aa57e에서 시작했다.
원래5의 시작점은 이번 고정 CPU 관측 feature→GPU decoder 조건에서 4/5·112/112다.
앞선 GPU encoder 실험의 5/5를 이번 시작 결과로 대신 쓰지 않는다.

| 조건 · 모두 32회 동일 데이터 노출 | 원래5 pass | 구조 F1 | joint 치수 |
| --- | ---: | ---: | ---: |
| 원래5 joint, Adam1e-4 | 0/5 | 0.322127 | 22/112 |
| 원래5 online, Adam1e-4 | 0/5 | 0.008107 | 0/112 |
| 원래5 accumulate, Adam1e-4 | 0/5 | 0.315212 | 16/112 |
| 원래5 accumulate, 기존 digit loss | 0/5 | 0.349547 | 25/112 |
| 원래5 accumulate, Adam3e-5 | 4/5 | 0.991416 | 111/112 |
| 원래5 accumulate, Adam1e-6 | 5/5 | 0.999285 | 112/112 |
| 같은 Adam1e-6, 노출 순서2 | 5/5 | 0.999285 | 112/112 |

online은 160 optimizer updates, joint/accumulate는 32 updates다.
joint와 accumulate의 gradient 동등성은 fixture에서 검사했지만 실수 연산/Adam 누적으로
실제 최종 수치는 약간 다르다. 같은 노출량에서 online이 더 나쁘며, batch1 하나만이
첫 실패의 필요조건은 아니다. joint에서도 첫 update가 실패했다.

| 10개 혼합, 32회 노출·64 updates | 원래5 구조 F1 | 원래 joint 치수 | 추가 joint 치수 |
| --- | ---: | ---: | ---: |
| fixed capacity, accumulate, Adam1e-4 | 0 | 0/112 | 0/140 |
| variable capacity, accumulate, Adam1e-4 | 0.002705 | 0/112 | 0/140 |
| 같은 variable, count loss0 | 0.000226 | 0/112 | 0/140 |
| 같은 variable, 기존 digit loss | 0.000678 | 0/112 | 0/140 |
| 같은 variable, template loss0 | 0.000906 | 0/112 | 0/140 |
| 같은 variable, assignment 매회 갱신 | 0.001133 | 0/112 | 0/140 |
| 같은 variable, Adam3e-5 | 0.002033 | 0/112 | 0/140 |
| 같은 variable, Adam1e-6 | 0.391750 | 60/112 | 0/140 |
| 같은 Adam1e-6, 노출 순서2 | 0.389604 | 62/112 | 0/140 |

고정 capacity 진단이다. image-predicted count로 같은 checkpoint를 평가하면
mixed-safe 조건의 원래 치수는 57/112 및 59/112로 더 떨어졌다.
추가5는 image count에서 5/5 사례의 capacity가 필요한 node/컴포넌트 수보다 부족했다.
그러나 충분한 fixed capacity에서도 추가5는 0/140이므로 count만의 문제는 아니다.
32회는 동일 노출 진단 창이며 신규5가 최종 수렴해도 불가능하다고 증명한 결과는 아니다.

## 첫 업데이트와 loss gradient 추가 대조

원래 unexpanded tiny-v4와 expanded 모델을 CPU에서 독립적으로 한 번씩 업데이트했다.
같은 원래5/GT/features, joint batch5, 새 Adam, clip5, LR1e-4에서 둘 다
구조 F1 0.000238·joint DIM0/112로 즉시 악화했다. 새로운 사례/확장/variable count가
없어도 첫 악화가 발생함을 확인했다. optimizer state는 원 checkpoint에 없으므로
원래 momentum을 그대로 이어간 대조라고 주장하지 않는다.

**첫 단계에서는 숫자112개와 실제 측정 길이112개 자체는 유지됐다.** 측정점/컴포넌트
위치가 바뀌어 joint 검사가 실패했다. 원점 이동을 빼도 internal query 위치의 90분위
상대 이동은 사례별 약110~137mm였다. 동일 종류2614 query 중 reference 변경은3개였다.
이 시점의 shared-reference F1=0은 geometry matching 실패에도 영향을 받는다.
이를 모든 관계/치수 숫자가 한 번에 지워진 것으로 설명하면 안 된다.

expanded Adam1e-6만 바꾼 첫 update에서는 5/5·112/112·구조F1 .994754가 유지됐다.
relative query 이동90분위는 약1.3~1.5mm다. SGD1e-4는 구조F1 .030758·0/112로 실패했다.
optimizer 이름만 바꾸는 해결을 확인한 것이 아니다.

기존 tiny loss의 weighted gradient 분해, optimizer update0, 동일5 CPU:

| 항 | 원래 weight | loss 원값 | weighted gradient L2 |
| --- | ---: | ---: | ---: |
| node 좌표 | 100 | 0.0000487273 | 162.449814 |
| anchor proposal | 40 | 0.0000661590 | 27.415237 |
| parameter | 20 | 0.0001145276 | 19.398233 |
| dimension geometry | 4 | 0.0001183355 | 15.509731 |
| pointer | 1 | 0.0116517436 | 0.115582 |
| count | 1 | 0.0000000493 | 0.001152 |
| template | 1 | 0.0000000912 | 0.000002977 |

전체 gradient L2는170.8463이고 node 항과 전체 방향 cosine은 .9764다.
gradient norm들은 서로 더해지는 기여율/백분율이 아니다.
작은 normalized loss 값은 작은 물리 좌표 update를 보장하지 않았다.
clip5도 Adam/SGD의 실제 CAD 좌표 이동을 보장하는 장치가 아니었다.

## 해석과 현재 결정

확인된 최초 파괴 지점은 **fitted checkpoint의 좌표 함수가 재시작 update에 지나치게
민감한 것**이다. 새로운 데이터나 count/capacity 확장이 최초 악화에 필요하지 않았다.
batch1 update는 악화를 키웠고 count/auxiliary loss 제거만으로 혼합 재현은 회복되지 않았다.
작은 update로 원래5 단독은 유지할 수 있지만 신·구 혼합에서는 여전히 간섭이 관측됐다.

본학습 전체 실패의 유일 원인을 규명했다고 확대 해석하지 않는다.
새 optimizer의 momentum 재시작, raw continuous loss와 숫자/solver를 거친 평가 경로,
물리 단위 민감도, 신·구 gradient 간섭의 추가 기여가 남아 있다.
backbone/데이터 수 부족을 원인으로 확정하지 않는다. 추가5의32회 노출 실패를
충분한 fit 후의 불가능성으로 소개하지 않는다.

다음 통과 조건은 작은 혼합 데이터에서 추가 사례의 실제 구조·치수를 배우면서 원래
재현을 함께 유지하는 것이다. optimizer/scheduler/assignment 상태 보존, 물리 출력
변화와 기존 재현을 확인하는 update guard, loss/gradient 균형을 우선 검토한다.
이는 다음 구현/실험 제안이며 이번에 이 guard를 실제 구현했다고 주장하지 않는다.
**1,028개 재학습·Space 재배포는 하지 않는다.**

310개 최종 fixed/image-count DXF를 모두 독립 재열어 audit0·mm·native DIM count를
확인하고 20개 checkpoint SHA를 대조했다. 파일 성공은 위의 geometry 실패를 대신하지 않는다.
전체조건/개별치수/실제SVG·DXF·loss·history·archive/checkpoint hashes는 private run에 보존한다.
[비식별 결과](../research/assets/2026-10-14-retention-ablation-summary.json).
비교 화면은 localhost8776의 retention-review.html이다. Codex 시각 검사와 직원 승인을 구분한다.

## 직접 시각 검수와 제한

LR1e-6 원래5 단독과 같은 LR의 혼합 조건에서 원래5·추가5의 실제 입력/감독/예측을
각각 5행 비교 그림으로 직접 확인했다. 단독 조건은 방 구조·벽 간격·문 곡선·치수 배치가
유지됐다. 혼합 조건의 원래5는 평면의 큰 형태는 남았지만 내부 위치와 연결에 어긋남이
있었고, 추가5는 구조가 재현되지 않았다. 지표 실패를 보고 모든 관계/형태가 지워졌다고
설명하지 않는다. 이 검수는 Codex 검수이며 직원의 최종 CAD 검수와 구분한다.

가운데 열은 before CAD에서 추출한 감독 그래프를 동일 SVG 함수로 그린 것으로,
실제 CAD 프로그램의 원본 렌더가 아니다. 추가 사례 P20285b076736236e의 감독에는
경사진 외곽 획들이 보인다. 원자료 symbol envelope는 작은 2개뿐이어서 이 큰 획들을
단순히 envelope 때문이라고 확정하지 않는다. 원 CAD 객체/추출 표현의 후속 확인 사항으로
남긴다. 같은 의뢰 페어 관계를 부정하는 근거가 아니며, 원래5 첫 update 실패를 설명하는
요인도 아니다. 기존 정답/원본을 수정하지 않았다.

두 A100 job의 trainer elapsed 합계는 3,880.8972초다. 대기·설치·과금 시간을 포함한
정확한 비용은 미확인이다. DWG 변환과 실제 CAD 열기/수정/저장 검증은 이번 진단의
실행 범위가 아니며 native DXF 검사로 대체 성공을 주장하지 않는다.
