# EXP-046 · 실제 이미지 기반 공유 노드·컴포넌트 decoder

상태: **5개 GPU 재현 succeeded / CPU 20개 failed / 본학습 completed·품질 failed / pilot Space deployed**.
날짜: 2026-10-14 KST. 연구 분류: decoder/감독·참조·제약 실험은 R&D 핵심,
Space 배포는 연구지원/제품 통합이다. 본학습 실행 완료는 범용 도면 변환 성공이 아니다.
사용자의 최신 요청으로 추가 실험을 중단하고
[상세 회고](../research/2026-10-14-experiment-retrospective.md)를 작성했다.

## 질문과 가설

EXP-045의 독립 primitive query는 치수 숫자 암기와 geometry를 연결하지 못했다.
native DIM/도어/벽 양면/사각 컴포넌트, small native template, shared node references와
명시 관계를 감독하면 실제 원본 이미지에서 우선 5개 구조·치수를 재현할 수 있는가?
단계 수보다 실제 구조/치수 지표와 stable pass/plateau로 학습을 판단한다.

## 구현과 데이터

`structured.py`, `graph_decoder.py`, `graph_constraints.py`, `graph_evaluation.py` 및
학습·배포/검증 runner를 추가했다. native path/TEXT를 보존하고 작은 native 묶음을
train-only local template로 추가한다. 현장 전체 CAD retrieval은 없다. source handle과
LINE 저장 순서를 이미지 획에 매칭하지 않는다. Shared coordinates/type/parameters/
reference/axis/host/dimension numeric heads를 사용한다. known host 분모가 없는 사례는
관계 의미의 성공으로 주장하지 않는다. wall corner 전체의 공유 junction·DIM host 관계와
확정 wall/window/room semantics는 여전히 불완전하다.

private v0.2 실제 이미지/변경전 CAD, seed 20261014, EXIF+512 letterbox, threshold .5.
DINOv3 ViT-B/16 frozen @ `5931719e67bbdb9737e363e781fb0c67687896bc`.
geometry 및 DIM 측정점·배치 위치 matching 10mm, DIM 숫자/실제 길이/잔차 1mm, structure >=.90,
component/shared-reference >=.95. 실제 그래프 compile/DXF audit를 매 검사에 포함한다.
같은 시작점을 공유하는 다른 엔티티를 first point만으로 matching하던 평가 오류는
모든 required refs matching으로 수정했다. 이전 metric v1 결과는 보존하며 v2 재평가를 별도로 기록한다.
axis tolerance 100mm는 80mm 벽 두께를 붕괴시킬 수 있어 1mm consistency guard로 고쳤다.

## 실행 및 결과

초기 tiny-v1/v2는 pointer 연결 미달로 canceled. tiny-v3의 첫 시작은 initializer SHA
불일치로 failed이며 복구 실행은 자원 상한으로 종료했다. 실패 상태를 succeeded로 바꾸지 않는다.
tiny-v4는 DIM 관련 참조/노드 우선 loss로 보강했다. job
`6acef07c5ccb47ba0f7900d5`, A100, FP32/TF32 off, 5개 joint batch.
12분 자원 상한보다 먼저 stable quality pass, 7,559 updates/627.713초.
이 step 수는 사후 관측이며 fit 기준이 아니다.

| 측정 | 사례 pass | 구조 F1 | 치수 정확/필수 |
| --- | --- | --- | --- |
| tiny-v4 GPU 5개 학습 재현 | 5/5 | 0.9995231283 | 112/112 |
| 같은 checkpoint CPU 원본 업로드 경로 5개 | 4/5 | 0.9835479256 | 112/112 |
| 같은 checkpoint CPU 별도 20개 pilot | 0/20 | 0.0000564557 | 0/476 |

CPU 1개는 약 0.945 structure, component .941/shared .945로 미달이다.
GPU/CPU node 위치 차이는 해당 사례 median 1.757mm/max 19.588mm였고 치수 26개는
모두 맞았다. 정밀 threshold 결과와 사용자가 수용한 시각 품질을 구분한다.
5개 전체를 직접 시각 검수하여 외곽/방 구획/문호/치수 배치 재현을 확인했다.
별도 20개 실패는 5개 재현이 일반화가 아님을 입증한다. 20개로 checkpoint나 threshold를 바꾸지 않았다.
이 노출 pilot의 결과를 sealed final test로 소개하지 않는다.

tiny-v4 code SHA `63b83e217fb34d68c133dd454f0a2f9d8555ffad4ac1b0891f7efb36f1076320`.
data SHA `e77e1bb917328cdc86efa3a5e233f69bc00f03cdc32fed0339a59380e27683f4`.
checkpoint SHA `05a545dd74100f072e56b359fcfa1006eae39e104b076f15ad10df75d0694911`.
원자료는 ignored `outputs/shared-graph-2026-10-14/`의 protocol/receipt/metric/SVG와
private HF bucket `runs/shared-graph-2026-10-14/tiny-v4`에 보존했다. 원본을 변경하지 않았다.

## 배포 및 다음 실행

사용자가 비교 화면을 수용하고 모델 배포·Space 갱신을 요청하여 **5개 재현 실험 모델**로
배포했다. strict 전체 pass 또는 production 검증 성공을 주장하지 않는다. 모델 repo
`youjunhyeok/img2dwg-shared-components-v1` revision `6c51ac297ce3916f3eaf5f16efde17cdd90895f3`,
Space revision `402d7958db12605f8346b682e64a51f0d1a5c395`, 둘 다 private.
인증 원본 upload 실제 API 결과에서 SVG raster 0, mm DXF audit 0, native INSERT 75,
DIMENSION 19를 확인했다. 100mm 길이 보정은 선택 편집이며 DIM 숫자/벽 두께/문 크기/
공유 좌표를 보존한다. 실제 다운로드 DXF의 ODA ACAD2018 DWG→DXF도 통과했으며
19개 치수 roundtrip max 차이 <1e-5mm다. 원본 대비 치수 정확성이나 업무 CAD UI
open/edit/save 증거로 승격하지 않는다. Space 직접 다운로드는 SVG/DXF다.

본학습은 실제 train 1,028개/선택 development 16개/최종 별도 20개, A100, 학습
90분/job 150분 상한이다. 종료 후 선택된 checkpoint에서 5/20을 다시 평가하며
미통과 본학습 checkpoint를 Space에 자동 교체하지 않는다.
job `6acef50cc662881452234b24`, code SHA
`a33c1072f5f1b1b8d9f19ce9efd92eed1ee5fdd3790566268b7d3868cd1c9d36`,
data SHA `9013f5470991f6e9a482df6f6cb4d79d9633b64ce830d5e96e77047a1d82a9dc`.
Adaptive capacity/count heads와 6,381개 train-only prototypes를 사용한다.
full-data-v3는 coincident native DIM dedup로 누락됐던 26개 annotation을 복구했다.
건물/평면 계열의 완전한 split 독립성, OCR/고해상도 판단, semantic host 연결은 다음
불확실성이다. 아래는 본학습 종료 및 사후 직접 검수 기록이다.

## 본학습 종료와 직접 검수

job은 completed, 종료 이유 quality-plateau, 28 epoch 진입/28,157 updates,
trainer elapsed 4,323.4385초다. 선택된 best model SHA256:
`52cdda59bb3023c7c71f8d9774dcfb59fb28a0a13ee31d0c75e5d3d82ca86138`.
28회 development 검사에서 joint 치수 0/369·사례 0/16이 계속됐다.

| full 선택 모델, GPU | 사례 pass | 구조 F1 | joint 치수 |
| --- | ---: | ---: | ---: |
| 원래 5개 재현 | 0/5 | 0 | 0/112 |
| 종료 후 별도 20개 | 0/20 | 0.0002080570 | 0/476 |

별도 20개 component F1 0.0000827815, shared-reference F1 0이다.
native DIMENSION 804개와 DXF audit error 0은 파일 형식의 성공일 뿐이다.
전체 20개 input/GT/actual model contact sheet를 직접 보았고 구조·배치·치수 실패를
기록했다. known geometric host는 정답 1/맞힌 것 0이며 aggregate .95를 성공으로 쓰지 않는다.
본학습 모델은 Space에 배포하지 않았다. 기존 tiny-v4 미리보기 모델은 유지했다.

사후 CPU 대조에서 원래 5개 input/컴포넌트 target과 capacity 959/726이 같았다.
tiny-v4와 full 구조 확장 직후는 모두 4/5·112/112, full 선택 모델은 0/5·0/112다.
새 optimizer update/20개 접근 없이 initializer를 그대로 재실행한 진단이다.
즉시 expansion corruption만으로 설명할 수 없지만 optimizer/assignment/감독/해상도 등의
기여는 분리하지 않았다. 원 receipt의 visual_inspection_pending은 수정하지 않고
`full-review-notes.json`에 후속 직접 검수를 기록했다. private `full-review.html`에
원래 5개와 별도 20개 실패 결과를 모두 보존한다.
