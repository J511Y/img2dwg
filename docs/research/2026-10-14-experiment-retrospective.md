# img2dwg 실험 리뷰 · 2026-10-14

작성: Codex. 기록 유형: 2026-10-13~14 실행의 사후 회고. 직원 검토/승인: 미확인.
사용자 요청에 따라 **새 방법 선정·추가 학습·재배포를 중단하고 기존 실행을 검토한다.**
실행 원자료는 보존하며 이전 receipt의 실패/취소/검수 대기 값을 덮어쓰지 않는다.

## 1. 현재 판정

**1,028개 실제 페어 본학습은 실행 완료했지만, 구조·치수 복원은 실패했다.**
5개만 학습한 모델은 그 5개를 상당히 정확하게 재현했다. 그러나 별도 20개에서는
이미 실패했고, 본학습으로 확장한 뒤에는 원래 재현하던 5개도 잃었다.
완성된 것은 데이터 준비, 컴포넌트 감독/작성기, 학습·평가·서빙 연결의 일부다.
새 준공도면을 정확한 편집 가능 DWG로 변환하는 제품 목표는 달성하지 못했다.

본학습 checkpoint는 Space에 반영하지 않았다. 현재 Space는 이전에 사용자가
미리보기 배포를 승인한 **5개 재현 실험 모델**이며, 별도 20개 실패 표시를 유지한다.
이번 리뷰에서 새 GPU 학습, 유료 VLM 호출, 모델 교체는 실행하지 않았다.
리뷰로 방향을 바꾸기 전에 시작한 CPU 초기화 대조 검사는 완료되어 아래에 포함한다.

## 2. 원래 제품 계약과 실제 도달 지점

최종 목표는 준공도면의 입력 방향을 기준으로 전유부를 복원하고, 표시 치수를 누락하지
않으며, 실제 벡터 길이·간격·연결을 그 치수에 맞춘 편집 가능한 DWG를 만드는 것이다.
옆집·엘리베이터·공용부를 모두 옮기는 것이 아니다. 초기 수동 ROI와 사람의 중간
수정은 허용된다. 좌우반전은 CAD의 기존 편집 기능/후속 기능으로 처리한다.

| 요구 | 현재 확인된 것 | 아직 달성하지 못한 것 |
| --- | --- | --- |
| 실제 입력–CAD 페어 | 같은 의뢰 폴더 정책으로 1,383개 릴리스 | 페어 존재만으로 ROI·감독 내용의 완전성이 보장되지는 않음 |
| 전유부 복원 | 변경전 평면 CAD target 추출, 업로드 crop UI | 전유부 의미 승인·자동 분리의 전체 품질 측정 |
| 재사용 컴포넌트 | typed parameter, shared node, BLOCK/INSERT, DIMENSION 작성 | 새로운 이미지에서 종류·위치·연결·치수 관계를 정확하게 예측 |
| 치수 보존 | source→crop의 DIMENSION 보존, 5개 재현 모델의 112개 joint 검사 | 본학습 및 별도 사례에서 숫자·측정점·실제 길이를 함께 복원 |
| 중심선→전체 치수→디테일 | 중심선 타입, 관계 head, 예측 후 제약 solver | 작업자 방식의 단계적 decoder/수정 루프. 현재는 일괄 예측 후 보정 |
| 확대·CAD 편집 | raster 없는 SVG, native 객체를 가진 DXF | Space 직접 DWG 다운로드, 실제 업무 CAD UI에서 열기·수정·저장 검증 |
| HITL | ROI·preview·선택 보정 | 컴포넌트 수정·잠금·undo/resume·부분 재복원과 검수 시간 측정 |

DXF가 열리는 것, DWG로 형식 변환되는 것, 구조가 맞는 것, 업무 CAD에서 수정 가능한
완성 도면인 것은 서로 다른 검증이다. 앞 단계 성공으로 뒤 단계 실패를 덮을 수 없다.

## 3. 데이터 준비에서 실제로 한 일

[v0.2 릴리스 기록](2026-10-13-dataset-v02-release.md)에 따르면 1,400개 실제 의뢰
페어를 수집·전처리했고 1,383개를 릴리스했다. 변경전 영역이 불확실한 17개는 별도로
보존했다. 원본은 읽기 전용으로 처리했고 수집 전후 SHA/size/mtime 검사를 기록했다.
private HF `youjunhyeok/img2dwg` 버킷의 22개 shard와 5,532개 primary artifact를
원격 readback하여 해시를 대조했다. source→crop에서 DIMENSION 32,413개를 보존했다.

split은 train 1,028 / validation 128 / calibration 77 / test 150이다.
source exact identity와 회전·반전 동등 geometry 그룹의 알려진 누수는 0이다.
건물·근접 평면 계열의 완전한 독립성은 아직 입증하지 않았다. 이번 20개는 여러 번
결과가 노출된 pilot validation이며 밀봉 최종 test가 아니다. calibration/test는 이번
shared 학습에 사용하지 않았다. 20개를 checkpoint 선택이나 threshold 조정에 쓰지 않았다.

실제 이미지와 CAD가 같은 현장이라는 사실은 사용자 확정으로 채택했다. 이미지 획마다
CAD LINE을 대응시키거나 전체 특징점 정합을 성공시켜야 수집하는 gate는 폐기했다.
다만 **input/output 페어와 학습 정답의 완전성은 별개**다. CAD를 shared node,
컴포넌트 종류·파라미터·참조·치수 숫자로 바꾸는 자동 감독이 실제로 필요하고 구현됐다.
모델이 라벨 없는 두 파일의 연관성을 알아서 배우도록 둔 방식은 아니다.

## 4. 실험별 실행과 결과

### EXP-043: CAD 렌더 합성 입력의 첫 좌표 모델

사내 CAD 1,028개를 렌더한 **합성 이미지**를 학습했다. 실제 준공도면 원본 1,028장을
입력한 학습은 아니었다. frozen DINOv3 + dense 4-slot coordinate head, 768px,
A100/BF16, full 2,500 steps, 학습/평가 elapsed 1,602.9초였다.
첫 FP16 실행은 gradient overflow로 실패했고 single-slot variant도 충돌 문제가 있었다.
수정이 여러 개 함께 들어갔으므로 각 수정의 효과는 분리하지 못했다.

합성 validation 64개에서 segment F1 0.3964, arc 0.1021, dimension candidate 0.0162,
symbol 0이었다. 이는 pixel tolerance 평가이며 숫자 치수/실제 mm 길이/관계 검사가 아니다.
뒤의 실제 입력 10mm 평가와 숫자를 직접 비교하면 안 된다.

GT factory/ODA 변환과 실제 업로드의 SVG·DXF 형식은 검사했다. 실제 구조 복원 품질을
확인하지 않은 채 첫 모델을 Space에 제공한 판단은 잘못됐다. `?` 치수·단위 미확정
출력은 원래 요청한 치수 완전 DWG가 아니었다.
[당시 기록](../experiments/2026-10-13-EXP-043-vector-first.md).

### EXP-044: 실제 스캔 실패와 배포 정정

사용자 결과에서 도면에 없는 큰 원호와 선 분산을 확인했다. 실제 입력 분포와 CAD 렌더의
차이, 독립 endpoint 출력, 불안정한 3점 원호 표현, 관계·치수 제약 부재가 있었다.
각 요인의 기여를 ablation으로 분리한 것은 아니다. 사용자 crop이나 반전을 실패 원인으로
돌릴 근거는 없다. screenshot-derived input은 원본 해상도의 정량 benchmark도 아니다.

실패 모델 기본 사용을 중단하고 관측 선 검출 기준선을 명시했다. 이는 CAD 복원 모델의
개선 성공이 아니라 실패 정정이었다. 선 829개 검출은 벽/문/치수 복원 성능이 아니다.
[실패 기록](../experiments/2026-10-13-EXP-044-real-scan-failure.md).

### EXP-045: 실제 5개 페어, 여전히 primitive 중심 출력

실제 준공도면 EXIF+512 letterbox, frozen DINOv3, seed 20261014로 5개를 학습했다.
canonical query에 primitive 좌표·치수 숫자 등을 감독했지만 업무 컴포넌트 출력은
충분히 구현되지 않았다. 12,000 steps는 제가 고른 상한이며 관측된 fit 기준이 아니었다.
학습/평가 elapsed는 140.47초였다.

| 평가 | 사례 통과 | 구조 F1 | 숫자·측정점·실제 길이가 함께 맞는 치수 |
| --- | ---: | ---: | ---: |
| 실제 train 5개 | 0/5 | 0.182642 | 0/112 |
| 별도 validation 20개 | 0/20 | 0 | 0/476 |

학습 5개에서는 숫자 112개 자체를 맞혔지만 최대 실제 길이 오류가 사례별 약 21~71mm였다.
숫자 암기와 geometry 복원이 분리돼 있었다. 그 상태에서 같은 primitive 방식의 step을
늘린 후속 job을 시작한 것은 요구사항에 대한 제 판단 실패다. 사용자의 지적 후 취소했고
8,000-step partial checkpoint를 보존했다. 그 취소 실행의 최종 20개 평가는 없다.
[실행 기록](../experiments/2026-10-14-EXP-045-real-pairs.md).

### 컴포넌트 factory 보강: 모델 학습 성공과 분리

5개 GT에서 문짝+원호 34개, 벽 양면 148개, 사각 loop 240개, 중심선 328개,
native DIMENSION 112개를 재조립하고 BLOCK/INSERT 422개를 작성했다.
처음 source primitive 4,306개 중 미분류 2,542개(59.03%)가 남았다.
shared 단계에서 native path 177개, TEXT/MTEXT 196개 등을 추가했고 독립 미분류 LINE은
1,379개로 줄었다. 이 수치들은 전처리 단계별 집계이며 모델 검출 정확도나 확정 의미
라벨 coverage가 아니다.

`component-review.html`의 깔끔한 그림은 **GT 파라미터를 작성기에 넣은 재조립**이다.
`shared-review.html`의 tiny-v4 예측과 구분한다. 학습 5개 source CAD에는 active native
INSERT가 없었다. 생성 BLOCK은 분해된 정답 geometry를 묶은 것이며 원래 사용된 native
블록을 그대로 인식한 것으로 소개하면 안 된다.

### EXP-046 tiny-v4: 공유 노드·컴포넌트 모델의 5개 재현

실제 구현은 frozen DINOv3 ViT-B/16, hidden 192 shared node/component set decoder,
type/parameter/reference/axis/known host/text/template/DIM 숫자 head와 결정론적 compiler다.
source handle/LINE 순서를 이미지 획에 강제 대응시키지 않았다. 이미지 feature로 예측하고
추론에서 정답 CAD를 조회하지 않는다. train-only 작은 native template를 재사용하며
현장 전체 CAD retrieval은 아니다.

초기 v1/v2 pointer 실패는 취소했고 v3의 SHA guard 실패·자원 상한 종료도 보존했다.
first-anchor-only 평가가 같은 시작점의 정확한 엔티티를 잘못 매칭하는 문제를 고쳐
metric v2로 별도 평가했다. axis 100mm tolerance가 80mm 벽 두께를 붕괴시킬 수 있어
1mm guard로 수정했다. 이전 receipt는 다시 쓰지 않았다.

tiny-v4는 5개 joint batch, A100 FP32/TF32 off, 12분 자원 상한 안에서 stable quality
pass로 종료했다. **7,559 updates는 결과로 관측한 수이며 목표 step이 아니다.**
학습/평가 elapsed 627.713초, checkpoint SHA `05a545dd…`다.

| 평가 조건 | 사례 통과 | 구조 F1 | joint 치수 |
| --- | ---: | ---: | ---: |
| 학습 5개 GPU 재현 | 5/5 | 0.9995231283 | 112/112 |
| 같은 checkpoint CPU 실제 서빙 경로 5개 | 4/5 | 0.9835479256 | 112/112 |
| 같은 checkpoint CPU 별도 20개 | 0/20 | 0.0000564557 | 0/476 |

CPU 1개는 component/reference 기준에 미달했다. 그 사례 GPU/CPU node 차이는
median 1.757mm/max 19.588mm였다. GPU와 CPU 모두 5/5라고 표현하면 틀리다.
5개 재현은 실제 학습 모델의 결과였으며 정답으로 바꿔치기한 것은 아니다.
그러나 **일반화를 입증한 결과도 아니다.** 처음부터 별도 20개는 실패했다.

사용자의 시각 수용과 명시 배포 요청에 따라 five-case pilot로 Space를 갱신했다.
일반 도면을 처리하는 production 품질 통과로 해석할 수 없다.
[EXP-046 기록](../experiments/2026-10-14-EXP-046-shared-decoder.md).

### EXP-046 full-v1: 1,028개 실제 페어 본학습

job `6acef50cc662881452234b24`는 completed다. 종료 이유는 **quality-plateau**,
28 epoch 진입/28,157 updates, trainer elapsed 4,323.4385초(약 72.1분)다.
완전한 28회 데이터 순회나 총 청구 GPU 시간을 뜻하지 않는다. queue·설치·업로드·청구액은
이 elapsed로 확정할 수 없다. 학습 90분/job 150분 상한은 비용 제한이다.

train 1,028개, checkpoint 선택 development 16개, 종료 뒤 별도 20개를 평가했다.
선택된 `best`를 최종 model로 내보냈다. `last`나 보기 좋은 사례를 다시 골라 배포하지 않았다.
본학습 checkpoint SHA는 `52cdda59…`다.

| 최종 선택 모델 평가 | 사례 통과 | 구조 F1 | component F1 | shared-reference F1 | joint 치수 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 원래 학습 5개 재현, GPU | 0/5 | 0 | 0 | 0 | 0/112 |
| 별도 20개, GPU | 0/20 | 0.0002080570 | 0.0000827815 | 0 | 0/476 |

여기서 joint 치수는 숫자뿐 아니라 정답 측정점 위치와 실제 벡터 길이를 함께 검사한다.
치수 숫자가 하나도 출력되지 않았다는 뜻은 아니다. 별도 20개 DXF에 **native DIMENSION
804개**가 작성됐지만 필요한 476개 중 joint 검사 통과는 0개였다. 과잉·잘못된 숫자와
참조/측정점 배치가 문제다. 치수 객체를 만드는 능력과 치수를 올바르게 복원하는 능력이 다르다.

최종 20개 DXF의 audit error는 모두 0이고 mm 단위·파일 무결성은 확인했다.
그러나 실제 평면 구조는 틀렸다. 20개 모두 입력/GT/실제 예측 비교를 직접 보았고
개별 메모를 남겼다. 다양한 입력에 비슷한 세로형 선 분산·교차·잘못된 사각/문/치수 배치가
나타난다. strict 10mm 기준만 너무 엄격해서 실패한 상황으로 설명할 수 없다.

제약 적용 **이전**에도 19/20의 구조/component/reference F1은 0이고 한 사례만 매우
작은 일부 일치가 있었다. solver 하나 때문에 원래 좋은 도면이 무너졌다고 보기는 어렵다.
반면 제약 후에도 14/20은 1mm 잔차 기준을 넘고 최대 잔차는 7,350mm였다.
잔차 0인 사례도 잘못된 예측 치수에 맞춘 잘못된 도면일 수 있다.
100mm 반올림은 이런 연결·배치 실패를 고칠 수 없다.

20개 known geometric host는 **정답 1개/맞힌 것 0개**였다. 원 aggregate의 host recall
0.95는 분모 없는 19개를 1로 처리한 평균이다. 95% host 성공으로 소개하지 않는다.
공유 관계 F1도 의미적 방 인접성·문 host·치수 wall association 전체를 평가하는 값은 아니다.

## 5. 왜 처음 5개가 깨끗했는데 본학습은 무너졌는가

두 사실을 구분해야 한다. 첫째, 5개 재현 모델은 별도 20개로 일반화하지 못했다.
둘째, 본학습은 **기존 5개 재현까지 망가뜨렸다.** 첫째만으로 둘째의 원인을 다 설명할 수 없다.

완료된 CPU 대조 검사는 원본 tiny-v4, 본학습 구조로 확장하되 학습하기 전 모델,
본학습 선택 모델을 같은 기존 관측 feature와 고정 조건으로 평가했다.
`train_shared_graph.py`의 initializer 코드를 그대로 재실행했고 새 optimizer update는 없었다.
5개 input PNG bytes와 component target JSON이 tiny/full에서 같음을 확인했다.
20개에는 접근하지 않았다. 검사는 새 후보 선택이나 학습 실험이 아니다.

| 동일 CPU 조건 | 5개 통과 | 구조 F1 | joint 치수 | 실제 5개 추론 query capacity |
| --- | ---: | ---: | ---: | --- |
| 원본 tiny-v4 | 4/5 | 0.9835479256 | 112/112 | node 959 / component 726 |
| 확장 직후, 학습 전 | 4/5 | 0.9835479256 | 112/112 | node 959 / component 726 |
| 본학습 후 선택 모델 | 0/5 | 0 | 0/112 | node 959 / component 726 |

**확장 직후까지 기존 능력은 유지됐고, 이후 학습 과정에서 사라졌다.** 즉시 가중치 복사
오류, 원래 5개 이미지/컴포넌트 target 교체, 해당 5개 추론 capacity 변화만으로 설명하는
가설은 이 대조 결과와 맞지 않는다. 다만 optimizer·assignment·loss·혼합 데이터 감독·
큰 사례 capacity·이미지 조건 사용 중 어느 것이 원인인지는 이 검사로 결정할 수 없다.
이를 모두 검증한 것으로 확대 해석하지 않는다.

tiny→full에서 데이터 수만 바꾼 것도 아니다. joint batch 5→한 이미지씩,
고정 capacity→adaptive capacity, node/component 최대 959/726→5,594/3,585,
prototype 129→6,381, text class 28→250, 좌표/크기 digit 수 확장,
학습 시 GT count 사용→추론 시 count 예측을 함께 도입했다.
full의 optimizer도 새로 생성했다. 이 복합 전환은 원인 분리가 어려운 실험 설계였다.

## 6. 학습 판정과 지표의 회고

full development 16개(필수 치수 369개)를 28회 검사했다. 전 검사에서 사례 통과는 0,
joint 치수도 0이었다. 구조 F1 최대도 약 0.000295였다.
quality-plateau는 **통과가 아니라 실패 종료**다. 학습을 더 하면 반드시 좋아진다는
신호를 얻지 못했다. 반대로 plateau가 이 모델 계열의 이론적 한계를 증명하는 것도 아니다.

선택 점수는 structure F1 + component F1 + reference F1 + joint DIM 비율 +
`1/(1 + node_set_error/100)`이었다. node-set error는 정답 노드에서 가까운 예측
노드까지의 거리다. 올바른 컴포넌트 연결을 맞히지 않아도 노드가 밀집하면 좋아질 수 있다.
best score 약 0.315는 구조·치수 통과가 아니다. 이번에는 중요한 지표가 거의 0인 채
노드 근접도 항으로 checkpoint를 고르는 상태가 됐다.

stable pass/plateau와 자원 제한을 분리한 것은 개선이다. 그러나 **제품 목표에 맞는
checkpoint 선택과 실패 진단은 여전히 부족했다.** 본학습 중 원래 5개 재현을 반복 감시하는
retention guard도 없었다. train 1,028개 전체의 복원 정확도를 최종 측정하지 않았으므로
전체 train도 0/1,028이라고 말할 수는 없다. 5개 재현과 development의 실패가 확인된 것이다.

현재 구조 F1은 canonical frame의 지원 segment/arc geometry matching이며 완전한 방/벽
위상 평가가 아니다. component/reference F1도 현재 자동 정답의 범위를 따른다.
숫자 head가 CAD 숫자를 출력한다고 OCR을 구현·검증한 것은 아니다. 512px letterbox 후
DINOv3 32×32 token을 16×16으로 pooling했고 고해상도 OCR/타일 비교는 실행하지 않았다.
작은 치수/세부선을 잃을 위험은 있지만 이것이 단독 실패 원인이라는 실측은 없다.

## 7. 잘한 점: 남길 수 있는 자산

1. **원본 보존과 데이터 추적.** 실제 의뢰 수로 1,000개 이상 준비하고 native 치수·단위·
   원격 해시를 기록했다. 수집을 불필요한 특징점 정합 gate에 계속 묶어두지는 않았다.
2. **작성기와 모델 출처 구분.** 실제 BLOCK/INSERT/DIMENSION 컴포넌트 작성기를 만들고
   GT 재조립, 관측 선 기준선, 이미지 모델 예측을 별도 화면/receipt로 보존했다.
3. **공유 참조의 실제 구현.** 독립 선 좌표에서 node/type/parameter/reference 출력으로
   전환했고 작은 표본의 실제 구조·치수 재현 가능성은 확인했다.
4. **기하·지표 오류를 수정하고 음성 결과를 보존.** first-anchor matching 오류와
   100mm axis 붕괴를 고쳤다. 실패/취소/이전 metric receipt를 성공으로 덮어쓰지 않았다.
5. **검증과 배포를 분리.** 이번 full 모델의 20개를 직접 보고 native DXF도 모두 검사했다.
   실행 완료·audit 성공을 품질 통과로 취급하지 않고 Space 교체를 막았다.
6. **실제 서빙과 형식 경로의 검증.** 인증 upload/download, raster 없는 SVG, native DXF,
   실제 내려받은 파일의 ODA DWG roundtrip을 확인했다. 이후 모델이 좋아지면 재사용 가능하다.

이 자산의 재사용 가치는 있다. 하지만 인프라 진척을 정확한 도면 변환 성과와 합쳐
프로젝트가 거의 완성됐다는 인상을 주면 안 된다.

## 8. 못한 점: 제 판단과 실행 관리

1. **제품 목표보다 부가 문제를 앞세웠다.** 초기에 전체 특징점 대응·실제 좌우반전을
   모델 선행 과제로 확장했다. CAD 기존 기능과 수동 ROI로 해결할 부분을 판단했어야 했다.
2. **실제 복원 검수 전에 첫 모델을 배포했다.** 합성 F1·파일 생성·벡터 확대를 근거로
   사용자 도면의 구조/치수 품질이 미검증인 모델을 제공했다. 이는 제 출시 판단 오류다.
3. **컴포넌트 요구를 충분히 구현하지 않고 primitive 학습부터 했다.** 데이터에 native
   객체와 재사용 구조가 있다는 설명을 받았는데 출력 설계가 뒤따르지 못했다.
   12,000-step 상한과 후속 step 증가도 기술적 근거가 부족했다.
4. **깔끔한 5개 결과의 의미를 제품 기대와 연결할 때 절제가 부족했다.** 5개는 실제 학습
   재현 성공이지만 별도 20개는 실패였다. 일반화와 관련된 기대를 낮추고 다른 단계로
   명확히 보고했어야 했다. 미리보기 승인 자체를 production 승인으로 넓힐 수 없다.
5. **5→1,028 전환에 변화가 너무 많이 들어갔다.** capacity·vocabulary·batch·count
   방식까지 바꾸면서 기존 능력 유지 검사를 학습 전에 명시적인 통과 조건으로 두지 않았다.
   원인 분리를 위한 중간 대조와 학습 중 retention 관측이 부족했다.
6. **지표 기반 종료를 넣고도 중요한 지표가 0인 상태를 충분히 진단하지 않았다.**
   노드 근접도가 checkpoint 선택을 이끌 수 있는 점과 구조·치수 무진전을 구분했어야 했다.
7. **관계·작업 순서 구현의 범위를 크게 해석할 위험을 남겼다.** 벽 양면의 내부 corner가
   모두 공유 junction인 것은 아니고, DIM→실제 wall host 및 방 의미 관계도 불완전하다.
   중심선 타입과 최종 solver가 있다고 작업자식 단계적 복원까지 구현한 것은 아니다.
8. **현재 상태와 과거 기록을 충분히 정리하지 않았다.** README/STATUS/AGENTS에 당시
   `running`, `미실행`, `최신` 기록이 누적돼 서로 다른 단계가 현재 상태처럼 읽힐 수 있었다.
   상태를 앞에서 확정하고 옛 기록은 당시 기록으로 표시해야 한다. 컨텍스트가 길다는 것은
   이 기록·판단 관리의 책임을 대신하지 않는다.

## 9. 확인한 사실과 아직 모르는 원인

| 판단 | 증거 수준 |
| --- | --- |
| 5개 학습 모델은 학습 사례를 재현했지만 별도 사례는 실패 | 실제 GPU/CPU receipt와 시각 검수로 확인 |
| 확장 직후 유지되던 5개 능력이 본학습 후 사라짐 | 동일 CPU 초기화 대조, 같은 input/target/capacity로 확인 |
| solver를 적용하기 전부터 구조·참조가 틀림 | full의 before-constraints 지표로 확인 |
| native 컴포넌트/치수 객체가 만들어져도 geometry는 틀릴 수 있음 | 20개 DXF audit 0, joint DIM 0/476, 시각 실패로 확인 |
| 단순 100mm 반올림으로 이번 실패를 해결 | 근거 없음. 배치·연결 오류와 meter 규모 충돌이 관측됨 |
| 데이터가 1,028개라 부족해서 실패 | 비교 실험 없음. 감독·학습 문제와 구분하지 못함 |
| hidden 192 또는 DINOv3가 작아서 실패 | 모델 크기/backbone 비교 없음. 확정 불가 |
| Hungarian/cache, count train/inference 차이, loss 간 충돌이 원인 | 코드상 위험 후보. 기여 분리 미실행 |
| frozen 저해상도 feature가 충분히 이미지 정보를 쓰지 못함 | 반복적 왜곡 출력은 관측. image masking/feature 비교로 검증하지 않음 |
| CAD 자동 컴포넌트 정답이 전체 업무 의미를 충분히 제공 | 불완전함은 확인. 전체 데이터의 오류율/실패 기여는 미측정 |
| 컨텍스트 오염이 모델 실패의 원인 | 실행의 input/target/hash 혼동은 이 대조에서 발견되지 않음. 문서·해석 관리 문제는 확인 |

따라서 지금 얻은 결론은 **현재 감독·decoder·학습 조건의 조합으로 일반화를 확보하지
못했고 본학습이 기존 능력도 유지하지 못했다**는 것이다. 데이터 추가, 모델 확대,
backbone 교체 중 무엇이 해법인지 이번 결과만으로 순위를 확정하면 또 근거 없는 선택이 된다.
이번 문서는 다음 실험을 새로 승인하거나 실행하는 계획서가 아니다.

## 10. 미실행 후보와 현재 Space

실제 학습한 vision backbone은 이 계열에서 frozen DINOv3다. Raster2Seq, RoomFormer,
기존 Jippin perception 모델 재사용, frontier VLM, Jev/Laya controller, JEPA,
diffusion/hybrid 등은 조사/후보 등록과 실제 실행을 구분해야 한다. 이번 리뷰에서 대체
가중치 학습이나 두 이미지 기반 action policy를 실행하지 않았다. 후보 목록을 모두
시도해본 것처럼 기록하지 않는다.

현재 private Space revision은 `402d7958db12605f8346b682e64a51f0d1a5c395`,
model repo revision은 `6c51ac297ce3916f3eaf5f16efde17cdd90895f3`이다.
tiny-v4 checkpoint를 쓰며 새 full-v1은 올라가지 않았다.
인증 업로드 1개 학습 사례에서 INSERT 75/DIMENSION 19, mm, audit 0, raster 0을
확인했고 raw/선택 보정의 warm inference는 약 1.32/1.27초였다. 전체 cold latency나
일반 도면 정확도 측정이 아니다. ODA roundtrip에서 19개 치수 차이는 <1e-5mm였지만
실제 CAD UI에서 열기·수정·저장을 검증한 것은 아니다. 직접 DWG 서빙도 미구현이다.

선택 100mm 보정은 1m 이상 벽 span/사각 크기 편집에 한정되고 DIM 숫자·공유 좌표·
벽 두께·문 크기를 유지한다. 실제 치수 host consistency를 자동 보장하지 않는다.

## 11. 재현 근거와 보관

평가: `img2dwg/graph_evaluation.py`의 shared-component-set/v2 및
`raw_evaluation.py`. geometry 10mm, DIM 값·측정점·길이 1mm, structure >=.90,
component/reference >=.95, 필수 치수 완전성, 참조·제약·native DXF 검사.
EXIF+512 letterbox, seed 20261014, threshold .5, frozen backbone revision
`5931719e67bbdb9737e363e781fb0c67687896bc`. GPU/CPU 조건은 위 표에서 분리했다.

| 항목 | 식별자 |
| --- | --- |
| tiny-v4 checkpoint SHA256 | `05a545dd74100f072e56b359fcfa1006eae39e104b076f15ad10df75d0694911` |
| tiny code/data archive SHA256 | `63b83e217fb34d68c133dd454f0a2f9d8555ffad4ac1b0891f7efb36f1076320` / `e77e1bb917328cdc86efa3a5e233f69bc00f03cdc32fed0339a59380e27683f4` |
| full checkpoint SHA256 | `52cdda59bb3023c7c71f8d9774dcfb59fb28a0a13ee31d0c75e5d3d82ca86138` |
| full code/data archive SHA256 | `a33c1072f5f1b1b8d9f19ce9efd92eed1ee5fdd3790566268b7d3868cd1c9d36` / `9013f5470991f6e9a482df6f6cb4d79d9633b64ce830d5e96e77047a1d82a9dc` |

private root `outputs/shared-graph-2026-10-14/`에 terminal receipt, manifest,
quality-history, 전체 25개 metrics/SVG/DXF, `full-review-verification.json`,
`full-review-notes.json`, `transfer-control/receipt.json`을 보관한다.
`full-review.html`은 input/GT/actual prediction을 구분하며 20개 전체를 담은 5장의
contact sheet와 실제 비교 화면 capture를 보관한다. 원본·고객 도면·checkpoint는
공개 Git에 넣지 않는다. 원 receipt의 `visual_inspection_pending:true`는 당시 상태로
보존하고 이후 직접 검수는 별도 receipt에 기록한다. Codex의 직접 시각 검사이며
직원의 승인으로 소개하지 않는다.

본 리뷰 집계는 [비식별 근거 색인](assets/2026-10-14-retrospective-summary.json)에
원자료 hash와 함께 저장한다. 연구노트는 새 private companion에 Markdown, 실행된
notebook, 증거 bundle/manifest/receipt를 작성하며 앞선 pilot의 고정 기록을 덮어쓰지 않는다.
