# 벡터 복원 우선: 첫 학습과 제품 완성 계획

작성일: 2026-10-13 KST. 사용자 우선순위 수정에 따른 현재 실행 계획이다. 모델 학습·추론은 이번에 실행하지 않았다. 공식 구현/모델 카드·HF metadata와 사내 CAD 추출 코드를 읽었으며 가중치 다운로드, GPU 작업, 운영 변경은 하지 않았다.

## 1. 결론과 우선순위

**첫 학습은 DINOv3 ViT-B/16 + 전용 벡터/관계 decoder, 첫 비교 학습은 Raster2Seq다.** 치수 판독은 PP-OCRv6 small을 먼저 실행 기준선으로 쓰고 숫자 crop의 오류를 확인한 뒤 필요한 모듈만 fine-tune한다. 이것은 사내 데이터에서 우위를 입증한 결과가 아니라 현재 선택이다.

제품의 첫 성공은 **준공도면 입력 → 전유부의 편집 가능한 벡터 그래프 → 치수에 맞는 DWG**다. 입력의 방향대로 먼저 복원한다. 실제 집의 좌우반전은 완성된 CAD의 MIRROR 또는 후속 UI 기능으로 처리할 수 있으므로 자동 방향 판별을 복원·학습·출력의 선행 조건에서 제거한다. AutoCAD가 제공하는 [MIRROR](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-MEP/files/GUID-D220C504-4BA8-405B-A79C-6AE20F8937D5.htm)를 제품 계획에서 우선 고려했어야 했다.

전유부 범위 선택은 유지하되 초기에 사람이 ROI를 선택할 수 있도록 한다. 자동 전유부 분할 모델을 먼저 완성할 필요는 없다. 작업자 순서는 중심선→전체 치수/구조→디테일로 반영하되 매 선마다 LLM tool call을 하는 구조를 요구하지 않는다. 중간 그래프를 단계별로 출력하는 모델도 이 작업 흐름을 지원할 수 있다.

추가 요구는 핵심 복원/정밀도, 데이터 준비, 후속 편집 기능으로 나눠 개발 순서를 판단한다. 모든 예외를 선행 자동화 과제로 만들어 핵심 모델 개발을 지연시키지 않는다.

## 2. 첫 학습 후보를 선택한 이유

| 순서 | 후보와 초기화 | 첫 실험 | 선택 이유 / 한계 |
| --- | --- | --- | --- |
| 1 · 주력 | `facebook/dinov3-vitb16-pretrain-lvd1689m` + 신규 graph/geometry decoder | encoder freeze, adapter·junction/edge·관계 head 학습; 이후 마지막 encoder blocks fine-tune | 필요한 중심선·연결·폭·개구부·치수 association을 직접 감독할 수 있음. 전용 decoder는 구현해야 하며 DINOv3 자체가 CAD 모델은 아님 |
| 2 · 비교 | `haopt/Raster2Seq`, `raster2graph-512` 초기화 | 공개 sequence decoder를 사내 CAD의 검수 polygon supervision으로 fine-tune | 공개 학습 코드/가중치가 있어 custom graph 모델의 구현 리스크를 견제함. room polygon과 정밀 wall centerline/폭·치수는 같은 출력이 아님 |
| 공통 치수 모듈 | PP-OCRv6 small detection/recognition | 우선 pretrained inference; CAD 치수 숫자 crop + 실제 검수 crop으로 선택적 fine-tune | geometry 학습과 함께 준비. OCR 숫자만 읽는 것으로 끝내지 않고 치수선/측정점/entity 연결을 학습·검증 |
| 재사용 대조군 | 사내 Mask2Former/RF-DETR segmentation + 기존 skeleton/vectorizer | 기존 checkpoint의 inference와 결정론적 vectorization, 첫 단계의 신규 segmentation 학습은 생략 | 이미 가진 자산으로 저렴한 하한선을 확보. 원본 pixel mask와 CAD metric geometry를 혼동하지 않음 |

[DINOv3 공식 구현](https://github.com/facebookresearch/dinov3)과 [모델 카드](https://huggingface.co/facebook/dinov3-vitb16-pretrain-lvd1689m)는 feature backbone을 제공한다. 학습하려는 전용 decoder는 우리 설계다. 완전 scratch encoder 학습보다 pretrained backbone과 작은 출력부부터 시작해 데이터·구현 오류를 분리한다. DINOv2 + 동일 decoder는 DINOv3의 downstream 이득이 불분명하거나 runtime 문제가 있을 때의 통제 실험이다.

[Raster2Seq 공식 구현](https://github.com/Cornell-VAILab/Raster2Seq)은 labeled room polygon sequence와 공개 checkpoint·학습 script를 제공한다. [HF 모델 카드](https://huggingface.co/haopt/Raster2Seq)에 512 checkpoint가 있다. 실제 읽은 config는 input 512, sequence length 512, semantic classes 13이다. 사내 class와 그대로 같다고 가정하지 않는다. 해상도/sequence 제한 때문에 미세 치수·개구부 누락이 생기면 topology 비교 모델로 범위를 좁히고 표현 변경 없이 무한 튜닝하지 않는다. polygon→shared wall/centerline 변환의 오류는 모델 오류와 별도 측정한다.

[PP-OCRv6 small recognition](https://huggingface.co/PaddlePaddle/PP-OCRv6_small_rec_safetensors)과 [공식 PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)을 치수 숫자 기준선으로 사용한다. 새 OCR 전체를 scratch 학습하지 않는다. 치수 exact match·누락·치수 연결 오류를 먼저 보고 필요한 fine-tune을 선택한다.

HAWP/HEAT/RoomFormer, frontier VLM, JEPA/domain SSL, diffusion, 완전 scratch는 백로그에 유지한다. 다만 첫 학습 슬롯을 전부 분산하지 않는다. 전유부·치수·graph 실패 분석에서 각 접근이 해결할 병목이 확인될 때 실행한다.

## 3. 실제 출력 구조와 학습 단위

```text
입력 이미지 + 선택한 전유부 ROI
    ├─ geometry encoder → 연결점/중심선 graph → 벽 폭·문/창/곡선 후보
    └─ 원해상도 치수 OCR → 치수선/보조선 → 측정점/entity association
                    ↓
       전체 치수·간격·연결 제약으로 canonical 좌표 계산
                    ↓
       LINE/POLYLINE/ARC + 문/창 + 실제 DIMENSION 작성
                    ↓
       DXF → DWG → 재열기·편집·저장 검증 → 필요한 항목 HITL 수정
                    ↓
                 선택적 CAD 반전/회전
```

모델은 모든 절대 길이를 이미지 픽셀에서 정확히 추측하는 역할을 맡지 않는다. 구조·연결·측정 대상의 후보를 내고, 확인된 치수가 최종 geometry를 결정한다. 충분한 치수 근거가 없으면 덜 제약된 geometry를 표시하고 부족한 치수만 사람에게 확인받는다. 문 폭 등 관행 값을 사실로 채우지 않는다.

첫 geometry head는 junction 좌표, edge의 endpoint/연결, wall width, opening host·offset·폭과 불확실성을 예측한다. centerline GT가 DWG에 직접 존재하지 않으면 평행한 벽 양면선으로부터 검수 가능한 후보를 만들고 불명인 항목은 loss를 가린다. 모든 LINE을 wall centerline으로 처리하지 않는다. 경사/곡선·문 swing arc는 지원 범위를 명시하며 미지원 누락을 완료로 통과시키지 않는다.

첫 loss는 endpoint/junction coordinate loss, edge/class loss, endpoint association, opening host loss다. 치수 branch에는 text→dimension line→측정 entity/endpoint 관계 감독을 붙인다. global CAD metric 좌표와 관측 이미지 좌표/warp를 분리한다. 단순 mask IoU 최적화로 목표를 대체하지 않는다.

처음에는 종횡비를 유지한 1024 global view + 필요한 detail tile을 사용하고 원해상도 치수 crop은 별도 보존한다. encoder patch보다 작은 얇은 선의 누락을 확인해 adapter/local branch 효과를 대조한다. 512/1024 등 입력 해상도는 CAD 저장 정밀도가 아니며 최종 좌표는 치수 제약으로 계산한다. query 수는 검수 GT entity 분포를 보고 정하며 학습 전에 정답을 잘라 맞추지 않는다.

## 4. 특징점 정합 없이 학습을 시작하는 데이터 경로

이미 추출한 40개 변경전 CAD를 시작 자산으로 쓴다. 원본을 건드리지 않는다. 먼저 5개에서 전유부 선택·단위·dimension override·중심선 표현을 확인하고 CAD-IR/GT writer를 검증한다. 5개는 구현/overfit debug이며 일반화 평가 표본이 아니다.

**합성 경로:** 검수 CAD → 렌더 이미지 + 정확한 graph/치수 관계 → blur/JPEG/색바램/선폭/원근/종이 휨 변형. 이미지와 CAD 정답의 변형 관계가 알려져 있으므로 실패한 전역 특징점 정합을 학습 준비 조건으로 삼지 않는다. 서로 다른 CAD의 train/dev/test 그룹을 먼저 나누고 그 안에서 augmentation을 생성한다. 많은 합성 변형이 독립 도면 수를 늘리지는 않는다.

**실제 경로:** 준공도면은 실제 domain 성능을 측정하고 fine-tune할 핵심 자산이다. 전유부와 주요 graph/치수 관계를 검수한 사례만 hard label로 사용한다. 전체 시트 pixel homography가 없어도 canonical target supervision을 구성할 수 있지만 실제 같은 구조인지 확인은 필요하다. 이미지와 DWG가 반전 관계면 학습 target 좌표를 입력 기준으로 정규화하거나 검수된 동등 변환을 적용한다. 이는 잘못된 학습 정답 방지이며 실제 집의 반전 판별을 제품 선행 gate로 만드는 것이 아니다.

승인되지 않은 실제 40개를 통째로 hard target으로 학습하지 않는다. 대신 합성 학습과 실제 검수/평가를 동시에 진행한다. 기존 segmentation 라벨은 perception 보조에 사용하되 CAD 정답이 있다고 가정하지 않는다. 비내력 분류는 추가 semantic 축이며 벡터 복원 성공을 기다리게 하는 선행 과제가 아니다.

## 5. 첫 run 설계와 계속/중단 기준

아래 step 수는 초기 실행 상한 제안이다. 비용/하드웨어는 첫 job 전 고정하고 이번에는 GPU 작업을 예약하거나 실행하지 않는다.

| 단계 | 실행 범위 | 확인할 결과 | 실패 시 판단 |
| --- | --- | --- | --- |
| T0 · 데이터/writer | 5개 CAD annotation + GT→DXF/DWG | geometry/단위·치수 관계 보존, 지원 엔티티 누락 표 | compiler/GT 오류부터 수정. 모델 크기 증가 금지 |
| T1 · 첫 주력 학습 | DINOv3 freeze, 5개 clean/synthetic debug, 최대 1,000 steps | finite gradient와 파라미터 갱신, tiny graph overfit, predicted CAD-IR로 만든 DWG | 작은 정답도 못 배우면 좌표/표현/matcher/loss 진단. 대규모 job으로 확대 금지 |
| T2 · 합성 일반화 | 검수 CAD 그룹에서 최대 5,000 steps; 같은 split의 Raster2Seq fine-tune 비교 | 보지 않은 CAD 계열의 topology/개구부·치수 연결·E2E DWG | 구조 부족인지 합성 도메인 부족인지 분리. decoder/representation 교체 또는 실패 후보 기록 |
| T3 · 실제 보정 | 실제 검수 표본, 합성 혼합·마지막 blocks 선택적 unfreeze; 최초 최대 2,000 steps | 실제 준공도면에서 누락/잘못된 치수·HITL 수정량·처리시간 | synthetic 성공만으로 계속하지 않음. 실제 GT/augmentation/해상도 원인 확인 후 다음 비교 |
| T4 · 제품 pilot | heldout 입력→단계 preview→수정→새 DWG | 실제 CAD 선택/편집/저장·재열기, 필요한 치수 coverage와 실제 residual | output 파일 존재나 재사용 GT DWG를 이미지→변환 성공으로 취급하지 않음 |

DINOv3가 이미 있는 segmentation/vectorizer 기준선보다 실제 graph/수정시간을 개선하지 못하면 encoder를 키우기 전에 표현과 supervision을 검토한다. Raster2Seq가 동일 CAD 검증에서 더 좋으면 그것을 주력으로 채택한다. 선택은 특정 모델을 지키는 일이 아니라 usable DWG를 만드는 일이다.

초기 release 판정은 필요한 치수 누락 0, 미해결 치수 충돌 0, 실제 길이/간격 residual의 사전 고정 허용 오차 충족, 편집 가능한 핵심 엔티티, CAD open/edit/save/reopen이다. 읽을 수 없는 치수는 HITL 수정 후 판정한다. 소표본 pilot은 대규모 일반화 증명이 아니다. 최종 metric tolerance·수정시간/비용 목표는 GT와 업무 요구를 확인해 sealed 평가 전에 고정한다.

## 6. 제품 단계와 후속 후보

1. **첫 수직 기능:** 사용자가 전유부를 선택하고, 모델이 중심선/벽·개구부 후보와 치수 목록을 만들며, 필요한 값을 수정한 뒤 DWG를 받는다. milestone은 모델 예측으로 생성한 새 DWG와 치수별 근거/오류 표다.
2. **보정 감소:** 실제 fine-tune, 치수 association 개선, 국소 repair로 수동 수정량을 줄인다. 자동 영역 선택은 여기서 개선할 수 있다.
3. **선택적 다음-action controller:** 반복 수정이 주요 병목일 때 VLM batch repair 또는 visual proposal+Jev/Laya selector를 비교한다. 검증된 CAD tools/solver를 재사용한다. 전체 그림을 매 line마다 VLM에 보내는 긴 trajectory fine-tune을 첫 단계에 하지 않는다.
4. **업무 편집:** 좌우반전/회전, 레이어 선택, 부분 재생성, 업무 시스템 연계. CAD 기존 기능으로 해결되는 것은 제품 기본 복원보다 먼저 개발하지 않는다.

## 7. 이번에 확인한 가용성

- DINOv3 HF revision: `5931719e67bbdb9737e363e781fb0c67687896bc`. manual-gated 모델이며 이번 인증 환경에서 weight dry-run은 성공했다. 약 342.7 MB의 다운로드 계획만 확인했고 weight는 내려받지 않았다. 모델 실행·학습 성공을 뜻하지 않는다.
- Raster2Seq HF revision: `c9a9c439ba66594dab701b77b7df52a5f75a5fce`, non-gated, model card MIT. `Raster2Graph-512/config.json`만 비공개 preflight 폴더에 내려받아 설정을 확인했다. weight는 내려받지 않았다.
- DINOv3는 자체 license, Raster2Seq code/model card는 MIT를 각각 기록한다. dependency/data 처리 조건은 실제 run 전에 고정한다.
- Raster2Seq 공식 환경은 Linux/Python 3.10/CUDA extension이다. Windows의 pilot Python 3.14 환경에 그대로 설치하지 않고 별도 학습 runtime을 사용한다.
- 사내 `data-pipeline`의 raw CAD-IR exporter는 DIMENSION과 styles/blocks를 읽는 재사용 후보이며 중심선·치수 관계 학습 GT를 자동 완성하는 도구는 아니다. 다른 저장소의 수집 시점 작업 트리를 수정하거나 기존 실측을 새 성과로 승계하지 않았다.

다음 구현은 이 계획의 T0/T1을 위한 CAD supervision builder, geometry decoder와 공통 writer/metric 연결이다. 전체 40개 사람이 승인할 때까지 아무 모델도 개발하지 않는 방식으로 진행하지 않는다.
