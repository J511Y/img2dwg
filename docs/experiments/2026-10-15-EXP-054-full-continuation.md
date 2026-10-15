# EXP-054 · 수정 decoder와 1,028개 본학습

기록일2026-10-15 KST. 상태: preparing. R&D 후보이며 본학습 결과 미측정이다.
사용자가 본학습/retention10/별도20 직접검수/통과 시 Space 반영을 명시 승인했다.

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
