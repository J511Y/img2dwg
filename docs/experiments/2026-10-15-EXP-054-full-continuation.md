# EXP-054 · 수정 decoder와 1,028개 본학습

기록일2026-10-15 KST. 상태: execution completed / quality failed. 기술 가설의 실패 실험이다.
사용자가 본학습/retention10/별도20 직접검수/통과 시 Space 반영을 명시 승인했다.

**결론: 기존10은10/10·252/252를 유지했으나 별도20은0/20·0/479다. 미배포다.**
1,028개 모두를 학습에 사용했고21,928 update/22번째 순회 진입 후 실제 품질 정체로 종료했다.
전체 모델 fine-tuning이 아니라 검증 모델을 동결한 **268만 parameter의 새 pooled residual
adapter 학습**이다. 기존10 보호 성공을 신규 도면 학습 성공으로 해석하지 않는다.
최종30개 직접검수/원본 input pixel audit/native DXF/기존10 DWG 재열기를 완료했다.

| 고정 후보 fresh CPU | pass | 구조F1 | component/refF1 | 필수DIM joint |
| --- | ---: | ---: | ---: | ---: |
| 기존 TRAIN10 | 10/10 | .9987504463 | .9988369656 / .9989518482 | 252/252 |
| 별도 정정20 | 0/20 | .0000526718 | 0 / 0 | 0/479 |
| 같은20의 동결 EXP053 기준선 | 0/20 | .0000460162 | 0 / 0 | 0/479 |

[수치 정본](../research/assets/2026-10-15-full-continuation-summary.json),
[loss와 실제 품질의 분리](../research/assets/2026-10-15-full-continuation-learning.svg).
비교 화면은 `http://127.0.0.1:8781/full-continuation-review.html`이며 실제30개 전체와
치수 누락·숫자/길이 오차·vector DXF, 통과한 기존10의 DWG 다운로드를 제공한다.

## 질문과 고정 조건

EXP-053의10개 train 재현이 새로운 현장에 대한 일반화로 확장되는가?
후처리 전 raw 구조 실패와 과잉DIM/hard projection 실패를 구분한다.
source 모델은 `6ca23df9d4b2e080c84f2b1b600c68976af8de4daab9247336ba74f742f9f375`.
decoder는 image-count-topk, dimension consistency10mm, projection trust region10mm다.
이 조건과 구조/치수 PROTOCOL은 별도20을 보기 전에 동결한다.

실제 준공도면–변경전 CAD train1028, 기존 development16, 기존 train10의 original5+additional5다.
별도20은 기존 pilot을 기반으로 한 정정 검증군이다. 학습 전 metadata 감사에서 기존20의1건이
train과 processed PNG hash가 같아 제외하고 미사용 validation에서 fixed hash rank로1건을
교체했다(기존19+신규1). validation label/예측은 교체 선정에 열지 않았다.
기존19는 과거 full-v1 실패에서 이미 노출된 탐색 사례이므로 완전히 새 sealed test로 주장하지 않는다.
이번 후보 선택/threshold tuning에는 사용하지 않는다. 과거 원래20의 결과는 그대로 보존하며
분모가 같은20이라는 이유로 정정20의 수치를 직접 동등 비교하지 않는다.
나머지 validation92와 test/calibration은 사용하지 않는다. 기존 source-identity group의
교차0을 검증한다. 데이터 릴리스의 건물/layout-family grouping 미완료 한계는 유지하며
새 건물/미노출 평면 계열의 밀봉 일반화 성공으로 주장하지 않는다.
same-request 페어/GT crop/typed component 전처리와 library를 유지한다. library6381의 train 유래
작은 native parts만 사용하고 완성 도면/정답/의뢰ID를 inference로 조회하지 않는다.

## 재현 유지와 확장

검증된 source adapter 전체를 frozen base로 두고 새128 hidden 잔차 분기를 추가한다.
기존 adapter 보호 span을 단순히5→10으로 바꾸면 추가5를 표현하던 기존 residual까지
0이 되므로 그 방법을 쓰지 않는다. 새 분기는 열 개의 CPU DINO 특징 affine span에서
잔차가0이다. CAD geometry와 case ID는 보호 projection에 저장하지 않는다.
이 보호는 정확한 기존 열 개 입력의 함수 유지이며 비슷한 사진/OOD/새 입력의 성공 보장이 아니다.

기존 base/context1198/951을 유지하고 전체 train 최대 nodes/components의1.25배+32를
inactive reserve로 확장한다. 새 pointer 후보의 finite margin12로 기존 argmax를 보존한다.
prefix/GT count로 inference query를 잘라내지 않는다. 모델 log_count로 전체 query 집합을 고른다.
보호 특징 residual이정확히0인eval입력은동결모델전체의출력을바로반환하여불필요한inactive
reserve연산을생략한다. 이는vision subspace로결정하며ID/CAD조회가아니다. 새 입력은확장분기를쓴다.
확장분기의제곱거리는동일한norm/dot 식으로계산해거대한5차원broadcast temporary를피한다.
source optimizer는 동결 모델에 적용하지 않는다. zero-output 새 분기만 새 Adam .0003,
기존 plain loss 비율/clip5/입력별50mm 좌표 update guard를 사용한다.
1-image online batch, seed20261015, FP32/TF32 off. 보호10의 함수/실제 native 검증을 실행한다.

## 실행과 판단

한 A100 작업: training180분, job240분 상한. 현재 CLI 공시 A100 $2.50/hour 기준 job 상한$10은
상한 추정이며 실청구액이 아니다. 코드/data/source SHA와 readback을 확인한 후 실행한다.
CPU frozen DINOv3 vitb16@5931719e…/512 letterbox/16x16 features를 사용해 CPU 서빙과 일치시킨다.
준공도면 원본과 회사 폴더는 수정하지 않는다.

적어도1028개가 모두 노출되기 전 후보를 선택하지 않는다. 임의 step/epoch를 fit 판정으로 쓰지 않는다.
5분 간격 실제 native CAD의 retention10/development16/고정 train probe16 품질을 검사한다.
기존10은10/10·252/252를 유지해야 한다. development의 구조/component/ref/필수DIM 지표로
후보를 선택하며 train probe도 확인한다. 서로 다른checkpoint 두 회의 실제 전체 pass를 stable pass로
판정한다. plateau는 최소3회 전체 자료 노출 뒤 유효 품질5회 정체 때 LR .3배, 세 단계 후 실패 종료다.
cap 종료는 not-quality-pass다. source 코드가 실제 구현한 선택/정지 상태와 raw 결과를 보존한다.
10mm 이진F1만으로 초기 수m→수백mm의 개선을 놓치지 않도록 실제 출력이 참조한 node만의
양방향 Chamfer(mm)를 함께 측정한다. unused query grid는 분모/거리 후보에 넣지 않는다.
선택 score는 F1 세 항+필수DIM joint fraction에최대0.1의 `1/(1+Chamfer/1000)` 항을 더한다.
이는 coarse progress/plateau 보조이며 strict pass tolerance나 필수DIM coverage를 완화하지 않는다.

학습 archive와 분리한 정정20 metadata SHA는
`b7b6041898cb743fda7315e80500da5b1c82ceeb01905891c43ac7eaec245733`다.
exact processed pixel overlap0/source-identity group overlap0이며 건물/평면 계열 분리의
미완료 한계는 별도다. private `data-audit/evaluation-cohort-repair.json`에 기존·교체 ID,
선정 seed/원본 index SHA/판정 시점(본학습 전)을 남겼다.

후보 weight SHA를 고정한 뒤 별도20을 한번 평가한다. 모든20의 원본/GT/실제 모델 vector를
직접 검수하고 수치/구조 누락·치수 숫자/실제 vector 길이·native DXF audit·fresh inference를 확인한다.
통과하면 DWG roundtrip과 실제 Space 업로드/다운로드를 검증한다. 실패하면 배포하지 않는다.
GT factory/파일 export/낮은 loss/old10 보호를 새 현장 성공으로 바꾸지 않는다.
동일 후보 동결 이후에 EXP-053 source6ca23df9…도 동일20/동일decoder에서1회 측정하는
기준선 비교를 사전 등록한다. 두 모델 모두 이미 동결한 뒤이며 이 비교로 재학습하거나
threshold를 바꾸지 않는다. 과거 Space의05a545dd… 모델과 이 기준선을 혼동하지 않는다.

## 산출물과 재현

- private run: `outputs/full-continuation-2026-10-15-v1/`.
- data: `prepare_full_continuation.py`, 원본 train/development만 복사, SHA/CPU features 검증.
- model: `graph_loading.py`의 serializable adapter stack, `train_full_continuation.py`.
- 사전 native10 결과/실행 job/비교 화면/후속 검수 결과는 실행 뒤 추가한다.

## 본학습 작업 제출

job `6ad0277a5ccb47ba0f7a2ced`, A100, training180분/job240분 상한이다.
source`cee3828fcc18ad58e9223f25f79b6eb31dd80a2c`와 code archive
`ffabd6c6d30e90d077f77dee69847c678467df829974d3232dc34a4abd117762`,
training archive`f07df5b783efba2d589d1f660c62ad0f0073dfadcc85865dbd3dde3bc5c30574`,
twenty archive`24ea671885f4fcaaeddf807157e971d1637590e9ba5caa88807d44114c0bc6fe`다.
5개 published file1,071,408,424 bytes를 remote에서 전부 readback하여 SHA를 대조했다.
initial GPU/native quality와 업데이트/완료/최종 품질은 이후 receipt로 확정한다.
기존Space revision402d7958…와 model pin05a545dd…/revision6c51ac29…는 그대로다.

### 실행 명세 감사 정정

running source의 plateau 조건은 `eligible and epoch>=3`다. 즉1028개 전체 노출 후
세 번째 epoch에 진입하면 동작하며, 초기 본문의 "세 번 전체 순회 완료 후"보다 이르다.
manifest의 같은 문구도 이 조건으로 해석해야 한다. 이 감사 정정을 별도 보존하며
실행 중 코드를 바꾸거나 과거 protocol을 덮어쓰지 않는다. strict native pass/두 checkpoint,
본학습 전체 노출 전 후보 선택 금지,20 후보 선택 제외 조건은 유지한다.
실행 결과를 보고 step 자체를 fit 근거로 삼지 않는다.

직접검수에서는 모델의 실제 구조·치수 오류와 단순 CAD 원점/좌우반전을 구분한다.
반전 자동판별을 복원 선행 gate로 추가하지 않는다. fixed-frame 주지표를 유리한 정합으로
바꿔 쓰지 않으며, CAD 후편집만으로 동등해지는 경우는 별도 HITL 관측으로 기록한다.

## 사전 검사

CPU 확장 모델의10개 native 검사에서10/10·252/252를 확인했다.
구조F1 .9987504463/component .9988369656/ref .9989518482다. source 모델을 재직렬화한
SHA도 원본6ca23df9…와 일치했다. nested adapter의 새 입력 학습 후 보호 출력 불변,
비전 입력만 사용하는 저장/재로딩, 거리 식의 값/미분 동등성, ranked selection, guard,
native graph/inference와 교차 split pixel guard/unused reserve 거리 검사 포함44개 단위 검사가 통과했다. 이는 본학습 품질 검증과 별개다.

TRAIN 내 고정 probe16의 input/GT 네 장을 직접 확인했다. 저해상도/사진 왜곡/주변 세대는
입력에 남고 target은 canonical 전유부인 차이가 보였다. 한 사례의 큰 원호는 **예측이 아닌
정답 CAD에도 이미 있는 요소**여서 native annotation 의도 검수 후보로 기록했다.
현재 데이터/threshold를 바꾸거나 해당 사례를 제외하지 않았으며 GT 전체 직원 승인을 주장하지 않는다.
시각 감사와 모든 원자료 SHA는 private run/data-audit/에 있다. 별도20은 열지 않았다.

train1028 의뢰 페어의 processed input PNG는943개 고유 byte hash이며70개 중복군/155건이다.
component 파일 SHA 차이를 곧바로 감독 충돌로 보지 않는다. 처음의 exact float DIM multiset
비교는1e-10 부동소수점 차이까지 세어43군을 표시했으므로 최종 판정으로 쓰지 않는다.
0.1mm 수치 정규화 후에는1군/3건만 다른 치수 집합이다. 해당 사진은 두 세대를 함께 담고 있고
다른 두 구조의 target으로 연결된 것을 직접 확인했다. 그중 두 target은 좌우반전 관계다.
이는 모델 입력에 전유부 ROI/대상 선택이 없을 때 모호한 감독이 존재한다는 관측이다.
사용자 확정의 같은 의뢰 input/output 관계를 부정하거나 임의 삭제하지 않는다.
이번 요청의1028건/기존 frozen 전처리를 유지하고, 1028개 고유 이미지라고 주장하지 않는다.
반전/annotation style/좌표 원점의 비유일성을 이번 decoder 수정이 해결했다고 주장하지 않는다.

첫 CPU 확장 경로 진단은 inactive reserve broadcast로 불필요하게 큰 tensor를 만들었고
한 사례까지 작성한 partial을 보존했다. 새 분기의 거리 식과 보호 span eval bypass로
이를 개선했다. 기존 학습된 inner adapter의 식과 weight는 바꾸지 않았다.
검수용 JSON에는 실제 사용한 prototype만 포함하고 전체 catalog는 모델 library에 보존하여
미사용6381개 catalog를 사례마다 중복 저장하지 않는다. 기하/수치 계산과 판정은 동일하다.

## 실행 중 진단 · 최종 검증과 구분

update1420/epoch2의 중간 best를 별도로 SHA 고정하여 TRAIN4에서 CPU로 추론했다.
네 사례 모두 구조F1=0, 표시 DIM=0이며 실제 벡터를 직접 보니 분산된 객체와 긴 잘못된
연결이 남았다. 원점 이동/좌우반전/100mm 반올림으로 복구할 오차가 아니었다.
이 중간 검사를 별도20 결과나 최종 후보 검사로 사용하지 않는다.

이 snapshot의 post-forward GT 최적 대응에서 node median 오차는138.6~212.9mm이고
node activity recall은 .147~.299였다. pointer slot/DIM digit sequence도 맞지 않았다.
이 대응은 실제 학습 중 cached assignment와 다를 수 있어 순수 OCR 정확도나 실제
학습 assignment 성능으로 해석하지 않는다. 원자료는 private monitor/snapshot-train4다.

고정 source의 active logit 범위가 넓어 새 잔차가 기존 prior를 넘기 어려울 가능성을
조사했다. 같은 TRAIN4/같은 weight/같은 좌표의 CPU control에서 source-active prior와
padding prior만 .05배로 낮췄으나 activity recall/참조 node Chamfer의 일관된 개선이
없고 구조/DIM도 전부0이었다. 원인으로 확정하거나 inference 설정에 채택하지 않았다.
이는 inference-only control이므로 초기화/재학습 효과 전체를 기각하지는 않는다.
GPU 실행·weight·고정 decoder와20 검증 조건은 바꾸지 않았다.

기존10의 이전 릴리스 원본 사본을 primary frame/EXIF 처리한 뒤 actual serving normalize를
적용하니 준비된 입력과10/10 pixel exact였다. fresh CPU 특징 검증과 함께 입력 경로를
확인하는 증거이며 신규 구조 재현 성공은 아니다. native DXF 검수기는 canvas bottom-left
원점/동일 anchor의 서로 다른 치수값을 구분하는 단위 검사1개도 통과했다.


## 최종 실행·검증과 배포 판단

A100 job은 COMPLETED다. 21회 전체 순회와 22번째 340건을 포함해 21,928 update를 모두
허용했고 quality-plateau로 종료했다. Training elapsed 8232.136466초에는 최종 native
export가 포함된다. GPU kernel 실사용 시간이나 실청구액은 아니다. Source 모델
6ca23df9…의 bytes는 유지됐다. Backbone과 base graph decoder는 동결했고, 학습한 새
분기의 parameter는 2,681,728개다. 새 분기는 mean/max pooled 특징을 사용하며 새롭게
학습하는 spatial cross-attention은 없다.

개발 지표로 선택한 후보는 1420 update / epoch2의 best다. SHA는
`aed6d0e89326e761703f18e9726207c95efe542e100c5556484059480818d707`, config SHA는
`b39b36b74a0cc55b70ce24903e714fcea56d4b047e89c565e082bb7be45581bd`다.
21,928 update의 last와 best에 대응하는 model/optimizer/assignment를 각각 보존했다.
별도20을 본 뒤 checkpoint를 바꾸지 않았다. 검증한 후보를 22회 학습된 마지막 weight라고
소개하지 않는다. 후보 선택 시점에는 이미 1,028개를 전부 최소 한 번 노출했다.

Best의 development16은 0/16·0/369, TRAIN probe16은 0/16·0/379다. 마지막 업데이트에서도
각각 0/16·0/369와 0/16·0/379였다. Last의 참조 node Chamfer는 개발687.36mm/학습표본
614.78mm다. 개발638.37mm인 best보다 개발 지표가 나빠졌다. 학습 loss 로그877점은
25 update마다 다른 입력에서 수집한 표본이며 전체 데이터 평균이 아니다. Loss는 하락했지만
CAD pass는 늘지 않았다. 시간 상한이나 loss 감소를 fit 근거로 삼지 않았다.

후보를 고정한 뒤 별도20과 EXP053 기준선을 같은 fresh CPU/image/decoder로 각각 한 번
측정했다. 후보의 참조 node Chamfer는 562.75mm, 기준선은 557.34mm이며 둘 다 0/20·0/479다.
이 작은 차이를 통계적 우열이나 일반화 성과로 주장하지 않는다. 최종20의 제약 전 구조F1도
제약 후와 같았다. EXP053의 과잉DIM hard projection만으로 이번 실패를 설명할 수 없다.
최종20 CAD에 DIMENSION은 총1개뿐이고 그1개도 오답이다. 첫 사례에서 정답6900mm에
대해6510mm를 그렸고 참조점 최대 오차는2258mm다. 100mm 반올림으로 값·공간 관계·누락
치수를 복구할 수 없다.

### 직접 검수와 파일 검증

실제 입력/GT/모델의7개 contact sheet로 기존10과 별도20을 전부 직접 보았다. 기존10의
방·문·벽체, 곡선 발코니와 경사 외벽 배치는 유지됐다. 별도20에서는 방이 닫히지 않고 대각
연결, 가로 띠 군집, 세로 붕괴가 남았다. 단순 원점 이동이나 좌우반전으로 복원할 수 없었다.
사례별 관측은 private `direct-visual-inspection.json`30행에 남겼다. 직원 승인은 아니다.

30개 모두 이전 릴리스 원본 사본의 primary page/EXIF/실제 serving normalize와 준비된
입력 PNG가 pixel exact였다. Linux fresh CPU DINO와 Windows cached 특징의 최대 차이는
1.049041748e-5였고, 기존10의 실제 구조·치수 검사는 통과했다. 특징 bit equality는 아니다.
독립 native verifier로 모델/config/입력/cohort SHA, 모든 update의50mm guard와30개 DXF를
검사했다. Native DIM253개는 기존252개와 신규의 잘못된1개다. 파일 audit·단위·래스터 없음이
통과해도 신규 도면 품질은 실패다. 검수 화면은 모든 필수 치수를 표시하고, 대응 예측이 없는
행을 누락으로 표시한다. 사례 전환 시 서로 다른 사례의 숫자가 섞이지 않도록 함께 갱신한다.

통과한 기존10의 모델DXF→ODA27.1.0→ACAD2018 DWG/AC1032→DXF 재열기에서252DIM과
INSERT/LINE/ARC/CIRCLE을 보존했다. 최대 기하 delta는1.091393642e-11이다. 별도20은
품질 실패로 DWG 검증을 진행하지 않았다. 실제 CAD UI edit/save는 증명하지 않는다.
브라우저에서도 기존1건의27개 치수 행과 DWG 다운로드를 확인하고, 다운로드한 파일과
roundtrip 모델 DWG의 bytes가 같은지 검사했다.

### 해석과 회고

이번에는 본학습으로 기존 재현을 잃는 문제를 막았고, 파일 생성과 실제 공간·치수 복원을
분리해 검사했다. 검증군의 pixel 중복을 학습 전 metadata만으로 수정했고 실패 모델을
배포하지 않았다. 반면 기존 모델을 전부 동결한 pooled residual은 이번 예산과 학습법에서
신규 TRAIN 표본조차 재현하지 못했다. 이를 성공적인 full-model fine-tuning이나 1,000개
데이터의 무효성으로 해석하면 잘못이다.

앞선 추가5는 joint batch로 같은 사례를 많이 반복 학습했다. 이번은 batch1, 큰 고정 query
reserve, 사례당 약21회 노출이다. 작은 실험과 사례당 학습량이 같은 capacity ablation이
아니다. 더 오래 학습하거나 더 큰 모델로 반드시 해결된다는 결론도, 개선 가능성이 없다는
결론도 얻지 못했다. 전역 pooled 분기의 표현력, 동결된 source prior와 연결 관계 학습,
512입력의 작은 치수 문자, ROI/target의 비유일성은 분리할 후속 가설이다. TRAIN에서 같은
사진에 다른 target이 있는3건을 관측했으나 전체 실패를 그3건으로 설명하지 않는다.
같은 의뢰 페어 정책과 1,028건을 유지했다.

다음 판단은 새로운 작은 TRAIN 집합에서 구조와 필수DIM을 먼저 fit시키는 것이다.
Spatial feature를 학습하는 decoder와 현재 pooled adapter를 같은 사례당 노출·기하 감독으로
비교하고, 좌표·연결 관계·치수 숫자 중 먼저 실패하는 출력을 분리할 필요가 있다. 이번20으로
threshold나 학습을 재조정하거나 추가 GPU를 실행하지 않았다. 후속 가설은 실행 성과가 아니다.

### 증거와 운영 상태

Private run의 `GPU/receipt.json`, `CPU-fresh/receipt.json`, `GPU/candidate-freeze.json`,
`artifact-verification.json`, `raw-input-verification/receipt.json`,
`direct-visual-inspection.json`, `retention-DWG-roundtrip/receipt.json`,
`browser-verification.json`, `learning-quality.provenance.json`, `release-decision.json`이 정본이다.
고객 도면·weight·실제 원본 경로는 Git 제외다. 원본과 Jippin 운영 모델은 변경하지 않았다.

Space revision `402d7958db12605f8346b682e64a51f0d1a5c395`, model repo revision
`6c51ac297ce3916f3eaf5f16efde17cdd90895f3`와 pin `05a545dd…`는 실행 전후 동일하다.
이는 기존 five-case pilot이다. 이번 source6ca23df9…나 full후보aed6d0e8…로 교체하지 않았다.
Private `deployment-after.json`과 `release-decision.json`으로 미배포를 확인했다.
