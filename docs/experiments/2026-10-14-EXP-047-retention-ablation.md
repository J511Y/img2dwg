# EXP-047 · 본학습 전환의 5개 재현 상실 원인 분리

상태: implemented / CPU preflight succeeded / bounded GPU comparisons planned.
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

GPU A100 job 하나, suite65분·condition4분의 자원 cap, job 전체90분.
단일 seed/진단 표본의 차이는 관측된 sensitivity다. 실제 전체 학습 실패의 유일 원인으로
확정하려면 다른 요인을 배제하는 일관된 대조가 필요하다. 복합 변경의 효과를 한 요인으로 돌리지 않는다.

실행: prepare_retention_ablation.py → train_retention_ablation.py.
비교 실행기는 10개의 train 입력만 허용하고 full trainer/deployer를 호출하지 않는다.
unit/integration18개 통과: default loss/관계, joint↔accum gradient, count만 제거,
숫자 truncation 거부, 초기 가중치 label-aware expansion, 단일 요인 matrix.

Private run: outputs/retention-ablation-2026-10-14-v1/.
GPU 실행·실제 종료·비교/시각 검수·연구노트는 새 receipt로 후속 기록한다.
