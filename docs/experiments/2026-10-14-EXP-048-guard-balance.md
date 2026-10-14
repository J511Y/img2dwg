# EXP-048 · 실제 좌표 이동 제한과 loss 균형의 분리 비교

상태: completed diagnostics / 기존5 유지 성공·신규5 학습 실패 / 목표 지속 중.
최신 사용자 승인: 기존5 유지＋추가5의 구조·치수 재현을 위한 작은 비교.
**10개가 함께 통과하기 전 1,028개 본학습/Space 배포 금지.** 이번 실행은 10개만이다.

## 질문·고정 조건

EXP-047의 같은 v0.2 TRAIN10, 동일 PNG/CAD감독/components/EXIF512 CPU DINO feature,
같은 expanded initializer SHA6832b79afda3470ae49c4b80f56287fdec2ebb5f853e90e779b55ea6216aa57e.
원래5 치수112개, 추가5 치수140개. development/validation20/calibration/test 미사용.
기존 checkpoint/로그/원본은 보존한다. 새로운 정답 조회/보정으로 예측을 대체하지 않는다.

모든4조건은 Adam restart LR3e-5, FP32/TF32off, virtual batch5 accumulate,
clip5, 동일 순서 seed20261014, assignment refresh20이다. 원래 사례의 train/eval capacity는
959/726, 추가는1198/951로 충분하고 고정한다. 이 capacity 정책은4조건 모두 같지만
EXP-047의 mixed variable 정책과 다르므로 **이번 control과 비교**한다.
추론 시 실제 image-predicted count는 같은 weights로 별도 검사한다.

## 좌표 제한 · guard 단독 요인

`graph_update.guarded_step`은 현재 output을 모든10개 관측에서 측정한 뒤 Adam step을
제안하고 parameter delta의1,1/2,…,1/256을 실제 forward로 확인한다.
검사 대상은 공유 노드 연속 좌표, component reference anchor, 실제 decoder의 숫자
치환 후 노드 좌표다. 모두mm이며 query identity만 비교하고 GT 좌표를 guard에 넣지 않는다.
전체10개의 각 update 이동 최대2mm, 원래5의 초기 output 대비 누적 이동 최대10mm다.
노드/anchor의 가장 큰 Euclidean 이동을 검사하며 평균/원점 보정으로 오차를 감추지 않는다.
허용 step은 proposed Adam moment를 유지하며, 모든 backtrack 실패는 가중치와 optimizer
상태를 모두 복구한다. attempted와accepted update를 나누고 alpha/거부율을 기록한다.

이 guard는 참조·종류·크기·solver가 바꾸는 최종 geometry 전체를 통과 인증하는 장치가
아니다. 기하/치수 검사는 그대로 필요하다. 누적 제한 때문에 신규 학습이 막히는지도
추가 사례의 실제 구조/치수와 노드mm 오차로 확인한다. 원래의4/5 초기 통과를5/5로
가정하지 않는다. 초기화의 semantic 정답이나 CAD를 복사하는 장치는 아니다.

## loss 균형 · balance 단독 요인

같은10개 TRAIN의 초기화 상태에서 update0으로 shared image/MLP trunk의 평균 gradient를
두 그룹으로 측정한다. 연속 기하=node/proposal/parameter/dimension, 나머지는
숫자·sign·종류·참조·host·axis·objectness·count 등 categorical 감독이다.
측정상 큰 그룹의 scale을clip(작은 그룹 norm/큰 그룹 norm,.01,1)로 정하고 이후 고정한다.
작은 그룹은1이며 두 그룹 각각 내부 weight 비율은 유지한다. 숫자/관계/종류 항도
0으로 제거하지 않고 scale을 공유한다.
scale과 실제 norm·parameter 목록을receipt에 보존한다. 전 조건의 initializer는 같다.
이는 shared gradient 균형의 한 후보이며 최적 weight나 각각의 항 중요도를 확정하는 방법은 아니다.

초기 CPU preflight의10개 평균 shared gradient는 continuous9.5265121 / categorical81.2079315였다.
geometry만 낮추려던 초기 후보는 scale1로 no-op이어서 GPU에 실행하지 않고 보완했다.
실제 양방향 balance는 categorical scale 약.11731, geometry1로 설정한다. 첫 후보의
preflight receipt는 보존하며 이 값은 GPU calibration에서 별도로 측정·기록한다.

| 조건 | 좌표 guard | loss balance | 비교 |
| --- | --- | --- | --- |
| control | off | off | 이번 고정조건 기준선 |
| coordinate-guard | on | off | control 대비 guard만 변경 |
| loss-balance | off | on | control 대비 balance만 변경 |
| guard-and-balance | on | on | 단독 대비 두 요인의 결합·상호작용 |

## 실행·판정·한도

1/2/4/8/16 및32회 노출마다 모든10개 실제 예측을 검사한다. 구조F1 .90,
component/reference .95, 치수 숫자·측정점/배치·길이 joint 누락/오류0, constraint,
invalid reference 및 실제 nativeDXF를 확인한다. 위치10mm, 숫자/길이/잔차1mm다.
fixed와 image-count 모두 연속2개 checkpoint의10/10 통과를 stable pass로 둔다.
같은 노출 회수의 결과를 비교하며 조건별 종료 최종값도 별도 기록한다.

학습 loss만으로 fit을 선언하지 않는다. 128회 이후 5개 유효 검사에서 실제 구조/치수
지표와 신규 노드 물리 오차의 개선이 모두 없으면 plateau 진단으로 종료한다.
원래/추가 두 그룹 중 낮은 joint 품질을 우선하는 score와 신규 node 평균mm 오차를 기록한다.
matched node/type 정확도는 학습 진단이며 최종 기하/치수 통과를 대신하지 않는다.
best와final weights를 모두 보존하고 최종값을 best로 바꿔 표시하지 않는다.

A100 4조건, 각 trainer10분·suite50분, job75분의 자원 상한이다. exposure2048은
비용/오류 안전 상한이며 수렴 판정이 아니다. 시간상한/plateau/stablepass를 구분한다.
이번10개가 통과해도 실제 일반화나 DWG/CAD UI 검증 완료가 아니며 자동 배포하지 않는다.
실행은 `train_guard_balance.py`, package는 허용된10개 trainer만 선택한다.
직접 시각 검수, 비교 화면, final DXF 재열기 및 실행·연구노트 receipt로 마무리한다.

## 실제 종료 결과

job6acf434cc66288145223c97d는 COMPLETED,4/4조건 종료, trainer2838.7882초다.
원격 code/data byte readback과 최종4개 model hash를 대조했다. GPU 초기 shared gradient는
continuous9.4719448 / categorical82.9569855로 scale1.0/.1141789899를 고정했다.
EXP-047의 원래5/all-parameter gradient norm과 이번10/shared-trunk norm은 직접 비교하지 않는다.

| 조건 | 실제 노출 dose | accepted/attempted | 기존5 pass | 구조 F1 | 기존 joint DIM | 신규 joint DIM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| control |224|448/448|0/5|.0002293|2/112|0/140|
| coordinate-guard |128|9/256|5/5|.9868860|112/112|0/140|
| loss-balance |224|448/448|0/5|.0168757|35/112|0/140|
| guard-and-balance |168|12/336|5/5|.9933238|112/112|0/140|

서로 다른 최종 노출량이므로128회 공통 history도 별도 비교한다. guard는 실제 기하·치수
재현을 보호했지만 신규 학습을 멈췄다. 누적 경계에 가까워지면1/256까지 줄인 proposal도
초기 대비10mm를 넘어 모든 가중치/Adam 상태가 rollback됐다. max accepted drift는
guard9.9856873mm / 결합9.8677311mm다. 모든parameter delta를 함께 줄였기 때문에
신규 숫자/종류/관계 head의 학습까지 제한했다. 이를10개 재현 성공으로 소개하지 않는다.

최종 fixed/image-count native DXF80개를 독립 재열어 audit0/mm/DIM 수/raster 없음과
checkpoint hash를 확인했다. 파일 audit 성공은 신규 구조 실패를 대신하지 않는다.
네 조건×기존5/신규5의 실제 입력/GT/예측 비교 그림을 생성해 직접 검수한다.
[비식별 결과](../research/assets/2026-10-14-guard-balance-summary.json),
localhost8777의 retention-review.html이 비교 화면이다. 직원 승인과 Codex 검수를 구분한다.
사용자 지속 승인에 따라 [EXP-049](2026-10-14-EXP-049-protected-adapter.md)의 기능 보호
잔차 adapter로 이어가며1,028개 본학습/Space 배포/holdout20은 사용하지 않는다.
