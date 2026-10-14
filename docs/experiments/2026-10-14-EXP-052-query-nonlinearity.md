# EXP-052 · 같은 입력 함수에서 query 비선형 잔차 용량 비교

상태: implemented / CPU 사전 확인·bounded GPU planned.10개 통과 미확인.
지속 목표의 TRAIN10만 사용하고 원본/holdout20/Space를 보존한다.

EXP-050에서 .0003/.0001은 신규node오차를약1~2mm로 안정화했지만 구조/치수는7/10에
정체됐다. EXP-051의 물리 후보 반경도 신규 치수112/140을 늘리지 못했다.
EXP-050 best 모델/같은 epoch의Adam/assignment를 post-forward audit했다. 실패 사례
중2개는 fresh/cached node 및component 대응 변경이0이고다른1개는node6개만 변했다.
component118개가 바뀐 사례는 이미 재현된 사례였다. 따라서matcher 정지가 주된
해결책이라고 단정하지 않는다. 신규5의phi singular values20.409/9.272/8.274/5.945/4.643으로
입력 특징 rank 붕괴도 관측되지 않았다.

현재 잔차 query는 `query_embedding * image_phi` 뒤 linear head만 적용한다. 입력·query·
output의 쌍선형 표현 제약이 좌표·anchor·숫자·형상 parameters를 함께 맞추는 데 한계일
가능성이 남는다. 이는 **가설**이며 학습을 더 하면 무조건 해결된다고 주장하지 않는다.

같은 EXP-050 .0003 **best** 모델과동일4772 epoch Adam/assignment에서flat control과
query 비선형 잔차 조건을 비교한다. node/component query 각각에bias 없는
128→512→GELU→128 residual을 추가하고 마지막weight를0으로 초기화한다.
추가 직후 기존/신규 모든 함수 출력이 동일하다. 기존 입력 보호 feature가0일 때
모든 새 경로도0이다. 새 conditioner/backbone/데이터·count·loss는 변경하지 않는다.
기존 parameter 이름/순서와Adam moments/step를 그대로 복사하고추가 parameter만
새 Adam state를 시작한다. source best와final optimizer를 섞지 않는다.

양쪽 Adam .0003/clip5/new5 joint/refresh20/orderseed20261014/old step2mm·누적10mm/
new step50mm/query1198·951/default loss를 동일하게 유지한다. 반경 보정은None이다.
조건당25분/suite65분/job80분으로 제한하고geometry/DIM/nativeDXF가10/10·252/252에서
두 checkpoint 연속 통과해야 한다. candidate는fresh image CPU추론/10개 직접 검수와
DXF→DWG→DXF 재열기로 확인한다. 이는10개 train 재현이며 일반화 성능은 아니다.

CPU 실제10개 관측 feature에서flat→zero-output nonlinear migration의18개 출력field,
총180개 tensor가bit-equal임을 확인했다. neutral native 재검사도source와같이기존5/5·
112/112 및신규2/5·106/140이다. 초기화 검사가 신규 학습 성공을 뜻하지 않는다.
source best SHA `f10551c91a0f266831acbe71df0166e7cc69e202a355e17793d556c53cc4824d`,
누적4772 epoch이며새 parameter는추가4개 matrix/262,144개의 scalar다.
