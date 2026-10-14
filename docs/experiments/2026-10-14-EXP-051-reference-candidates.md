# EXP-051 · 동일 checkpoint의 물리 참조 후보 검사

상태: CPU diagnostic completed / 해결 가설 rejected. 학습·GPU·배포는 하지 않았다.
EXP-049 plain best SHA `190555b8d78db1e9edd3962697da6f50027e0619d122f1fd0271c5ffdcfd7cd8`
가중치를 그대로 사용하고 동일 TRAIN10에서 추론 중 참조 후보 반경30mm만 추가했다.
30mm는 기존 구조 허용오차10mm의3배를 사전 지정했으며 holdout으로 튜닝하지 않았다.

추론은 예측 node/anchor/active와 learned reference score만 읽는다. 원본CAD/정답/의뢰ID는
조회하지 않는다. 후보가 없는 slot은 원 참조를 보존하고 unresolved로 기록한다. 이를
강제로 완성/통과시키지 않는다. 기본 반경은None으로 유지하여 이전 모델 동작은 보존한다.

거리 패널티는 `400*(distance_mm/10000)^2`다.30mm에서 .0036이고100mm에서 .04다.
학습 score가 이 항을 압도할 수 있다는 진단 가설을 세웠다. 이 거리 항만 Gaussian형으로
해석할 때 sigma353.553mm이며 모델 전체를 Gaussian 모델이라고 주장하지 않는다.
신규5에30mm 초과 anchor-reference gap이 각각57/84/57/43/44 slot 있고100mm
초과는49/55/32/32/33이었다. 기존5에는1개만 있었다.

그러나 반경 후보 적용에서 대부분 후보가 없었다. 기존1개·신규각56/70/39/41/41
slot이 unresolved다. 실제 연결 변경은 신규각1/16/19/3/4개에 그쳤다. 신규구조
F1 .956867761→.954309671이고치수112/140은 그대로다. anchor 자체와 참조의 불일치를
작은 반경만으로 해결하지 못했다. 후보 검사까지 요구하면기존4/5·신규0/5다.
이 **추가 안전 조건**의 실패와 원 frozen protocol의기존5/5·신규2/5를 구분한다.
원 결과를 덮어쓰거나 더 엄격해진 pass를 동일 protocol의 성능 악화라고 소개하지 않는다.

같은 TRAIN 감독으로 post-forward audit하여 신규30mm초과 참조 중 matched/defined
slot39/84/48/27/34와 unmatched query18/0/9/16/10을 구분했다. 단순 background false
positive만의 문제도 아니다. 원자료는private run의reference-distance-diagnostic,
reference-label-diagnostic 및CPU-best-plain-reference30 receipt다.
이 방법은 실패로 보존하며 Space/1,028학습에 사용하지 않는다.
