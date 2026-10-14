# EXP-050 · 동일 adapter 상태에서 학습률만 낮춘 구조·치수 안정화

상태: GPU completed /10개 동시 품질 failed. active goal은 후속 EXP-052로 계속 진행한다.
1,028개 본학습·Space 배포·holdout20 사용은 하지 않는다.

EXP-049 plain은 기존5의 실제 함수를 보존하면서 추가5의 노드 오차를1.9m→수mm로
줄였고 최고 점수 checkpoint의 CPU 재검사에서7/10·치수224/252를 재현했다.
그러나 .003 Adam 업데이트가 계속되는 동안 품질이 흔들렸고 최종 신규 치수는44/140이다.
이 결과가 capacity 부족/추가 데이터 필요를 입증한 것은 아니다.

같은 EXP-049 plain **최종** checkpoint와 대응하는 Adam moments/step/assignment state에서
두 비교를 시작한다. best checkpoint의 optimizer는 당시 저장되지 않았으므로 best 모델에
final Adam을 붙이지 않는다. frozen base/입력 특징 subspace/query1198·951/new5 joint batch/
loss weights/clip5/matcher refresh20/순서seed20261014/old step2mm·누적10mm/new step50mm는
유지하고 학습률만 .0003와 .0001로 낮춘다. 누적source epoch를 이어 순서와 대응 갱신을
재현한다. 두 조건마다 같은 원 Adam을 깊은 복사로 복원한다.

새 trainer는 best 모델과 **같은 시점**의 optimizer/assignment도 함께 저장한다.
이전 final/best/history는 덮어쓰지 않는다. fresh Adam의 첫 업데이트 민감도는
EXP-047에서 확인했으므로 여기서는 초기화하지 않는다. 복원된 Adam의 다음 업데이트가
중단 없는 실행과 정확히 일치하는 검사와 원 state 불변 검사를 추가했다.

조건당20분/suite50분/job65분 상한으로 계획한다. 상한을 수렴으로 해석하지 않는다.
같은 TRAIN10의 구조 F1/component/ref/native symbols/치수값·위치·길이/constraint residual/
DXF audit를90초마다 확인하고10/10·252/252가 두 checkpoint에서 연속 통과해야 한다.
통과 후보는 실제 이미지에서 DINO를 새로 실행한 CPU 추론과10개 직접 시각 검수를 한다.
평균 노드 오차와 loss만으로 성공을 선언하지 않는다. 실패/불안정이 남으면 해당 head와
matcher 변경을 별도 후속 요인으로 기록한다. 임의 step 연장만으로 해결됐다고 주장하지 않는다.

실행 Job `6acf67f15ccb47ba0f799dd9`, source `4c87b38`, code SHA
`b5414a99a3a8482556c536d372e0e7f6b7de13069f96f1dcda967b30006022b1`,
data SHA `460eb6a59951840286726e3cc7538e7a6069696ba9de23ca939853363863180f`.
원 checkpoint `0895fd9bfe4a5cb4e61a781eaaa80ee85914a0fb3961792e128b9b0e59c7723f`의
4740 Adam/assignment 상태를 복원한다. archive 원격 byte readback4개와 CPU preflight의
기존5 5/5·112/112를 확인한 후 실행했다. 기존 Space/model revision을 직전에 read-only
확인하여 무변경을 증명했다. 결과는 아직 최종 판정하지 않았다.
최종 결과는 아래에 별도로 확정한다.

| 최종 실제 이미지 set 추론 | updates | 기존5 pass·DIM | 신규5 pass·DIM | 신규F1 |
| --- | ---: | --- | --- | ---: |
| .0003 | 4312 | 5/5·112/112 | 2/5·89/140 | .938141391 |
| .0001 | 4301 | 5/5·112/112 | 2/5·96/140 | .928978081 |

두 조건 모두accepted=attempted/alpha1/old actual drift0이고 실제 구조·치수·물리 오차
검사8회 정체로 종료했다. loss 수렴이나모든 방법의 한계로 해석하지 않는다.
source의~수십mm 흔들림은 줄었으나 동일3개 신규 사례가 여전히 실패다. 최종40개
DXF 독립 재열기·SHA/guard 검사와20개 실제 예측 직접 검수를 완료했다. 원래5는
두 조건 모두 보존되고 신규2/4번째는 통과,1/3/5번째는 잘못된 연결·문/공간 윤곽이나
치수 위치가 남았다. elapsed2121.927838305초다.1,028학습/holdout/Space는 사용하지 않았다.

EXP-052 source로 선택한 .0003 best dose32/누적4772 checkpoint
`f10551c91a0f266831acbe71df0166e7cc69e202a355e17793d556c53cc4824d`는CPU native
재검사에서기존5/5·112/112,신규2/5·106/140이다. 이것과 final89/140을 구분한다.
best source에 맞는 같은epoch optimizer를 사용한다. source node/component 대응 감사는
`outputs/adapter-refinement-2026-10-14-v1/assignment-consistency-diagnostic.json`에 보존했다.
[최종 aggregate](../research/assets/2026-10-14-adapter-refinement-summary.json).
