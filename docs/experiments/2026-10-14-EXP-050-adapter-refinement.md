# EXP-050 · 동일 adapter 상태에서 학습률만 낮춘 구조·치수 안정화

상태: GPU running.10개 통과 미확인. active goal의 bounded 후속 실험이다.
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
