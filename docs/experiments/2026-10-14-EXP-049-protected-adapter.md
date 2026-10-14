# EXP-049 · 기존 응답을 보호하는 이미지 특징 조건부 잔차 그래프

상태: implemented / CPU preflight 통과 / GPU 준비. 신규5 학습 성공은 아직 미확인.
사용자는 다음 출근 시 확인할 수 있도록 목표 달성까지 계속 진행하도록 명시 승인했다.
목표는 같은 실제 TRAIN10의 구조·치수252개 동시 재현과 직접 검수이며
1,028개 본학습/Space 배포는 수행하지 않는다. 자동 goal은 active다.

## EXP-048에서 확인한 실패

하드 guard는 기존5·치수112개를 보존했지만 accepted9/256 또는12/336 후 더 움직이지
못했고 신규5는0/140이다. 큰 그룹의 loss를 줄이는 것만으로 신규/기존 동시 재현이
회복되지 않았다. 실제 출력의 누적 경계로 모든 parameter update를 줄이거나 거부하면
신규의 타입·숫자·관계 head까지 학습이 멈춘다. 이 한계를 해결하는 별도 방식이다.

## 변경과 source lineage

- 같은 이미지/CAD supervision/컴포넌트/EXIF512 CPU DINO 관측 feature10의 bytes를 유지한다.
- base는 EXP-047 five-safe-lr의 실제 학습 모델 SHA
  ccb4e637837280d547201a8c2a48a6957529edeb18102a33d808f2ea70e39b96이다.
  원래5의 구조5/5·112/112를 확인한 모델이며 GT factory/CAD retrieval이 아니다.
  EXP-048의 initializer와 다르므로 해당4조건과 단일 요인 효과로 직접 비교하지 않는다.
- base 가중치를 고정하고 실제 이미지 특징에 조건화되는128차원 잔차 query/head를 학습한다.
  노드·anchor·종류·파라미터·숫자·template·text·reference·axis·host 등을 수정할 수 있다.
- 원래5 입력의 pooled frozen vision feature를 중심화하고 rank4 affine subspace의
  직교 잔차를 입력으로 쓴다. 이 공간에서는 모든 잔차 head가0이다. CAD/정답/의뢰 ID는
  projection에 넣지 않는다. buffer는 입력 특징 공간의 basis/center이며 CAD 좌표가 아니다.
- 실제 추론은 raster vision feature→frozen base+조건부 잔차 head→동일 graph compiler다.
  ID/hash/원본CAD를 조회하지 않는다. 캐시는 학습 속도를 위한 frozen model의 예측 tensor
  뿐이며 최종 검사는 실제 forward를 새로 실행한다. inference load에는 원래 이미지나
  CAD가 필요하지 않도록 basis/center와 가중치를 저장한다.

## unordered query와 실제 개수

base의959/726 query context를 그대로 두고239/225개의 inactive spare slot을 더한다.
spare 위치는 image/CAD 무관 고정 grid이며 source geometry를 복사하지 않는다.
학습과 추론에서 reserve1198/951를 동일하게 사용한다. 활성/no-object 예측으로 실제
객체를 선택하고 log-count만으로 앞N개 query를 자르지 않는다. Hungarian set matching은
query가 GT 개수 이내의 prefix에 모인다고 보장하지 않기 때문이다.
이는 실제 이미지의 object 선택이며 GT count oracle routing이 아니다.
[DETR 공식 구현](https://github.com/facebookresearch/detr/blob/main/models/detr.py)의 fixed query
set/no-object 설계를 참고했다. 우리 typed CAD decoder의 성능을 DETR 성능으로 주장하지 않는다.

## 사전 실제 검사

CPU actual observation feature에서 새 adapter의 초기화/예비 query를 포함한 실제
forward+SVG/nativeDXF 검사를 했다. 원래5 5/5, 구조F1 .9992846924,
component .9990031130, reference .9996431609,112/112다. 추가5는0/5·0/140이다.
원래5의 projected residual norm은0이며 추가5는2.947~4.400이다.
projection이 신규 입력까지 모두0으로 지워 학습을 막는 상태가 아님을 확인했다.
이 검사에는 optimizer update가 없으며 신규 학습 성공으로 소개하지 않는다.

## GPU 비교·판정

동일한 adapter initializer에서 protected-plain과 protected-balanced 두 조건을 비교한다.
새5만 residual optimizer update를 하며 기존5는 frozen function 보호와 모든 실제 품질
검사에 포함한다. 이를10개 joint gradient 학습과 혼동하지 않는다.
balance는 초기 신규5의 all-trainable adapter gradient로 측정하고 고정한다. 초기 zero
head는 trunk gradient도0이므로 EXP-048의 shared trunk norm을 대신 쓰지 않는다.
숫자/기하/관계 중 어느 그룹도 제거하지 않고 큰 그룹의 weight만 조정한다.
[GradNorm 논문](https://arxiv.org/abs/1711.02257)은 gradient 기준 균형의 참고이며
우리의 일회성 고정 계수를 논문의 adaptive GradNorm 구현이라고 소개하지 않는다.

Adam .003/clip5, 신규5 joint batch, Hungarian refresh20, 같은 순서seed20261014.
guard는 원래 step2mm/누적10mm, 신규 step50mm다. 기존 function 보호 덕분에 신규까지
2mm로 묶지 않아 큰 초기 오차의 학습을 허용한다. measured/accepted/거부율을 보존한다.
1/8/32 초기 검사와 이후90초마다 실제10개 구조·치수/관계·node mm를 검사한다.
두 checkpoint의10/10·치수252/252·nativeDXF 통과를 요구하고 loss만으로 fit을 선언하지 않는다.
실제 검사8회 정체는 plateau, 조건25분/suite65분/job90분은 자원 cap이다.
필요한 후속 실험은 bounded job으로 이어가며 원본/holdout/기존 Space를 보존한다.

이 방법은 작은 표본의 재현/연속 학습 실험이다. 보호 subspace 밖의 신규/OOD 입력,
다른 해상도/전처리/encoder 변경, 공간 안에서 원래와 다른 geometry의 입력은 별도
불확실성이다.10개 재현이 generalization/1,028개 학습/DWG CAD UI 완료를 뜻하지 않는다.
