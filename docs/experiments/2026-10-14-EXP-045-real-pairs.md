# EXP-045 · 실제 준공도면 5개 학습·20개 검증

- 날짜: 2026-10-14 KST. 작성/실행: Codex. 검토자 확인 필요.
- 상태: 첫 실제 모델 평가 failed, 후속 primitive 학습 canceled. 모델 Space 재배포 없음.
- 후속 정본: [컴포넌트 설계 정정](../research/2026-10-14-component-decoder-correction.md).
- 분류: R&D 후보. 실제 입력에서 canonical CAD 구조와 치수 복원이 가능한지 실험한다.

## 고정한 질문과 조건

EXP-044의 합성→스캔 실패 이후 원본 준공도면을 실제 학습 input으로 사용한다.
같은 의뢰의 native 변경전 CAD를 target으로 두며 이미지 획과 LINE handle을 대응시키지 않는다.
입력과 출력은 별도 좌표계다. 전체 특징점 정합/페어 승인 gate를 재개하지 않는다.

v0.2의 기존 train에서 5개, validation에서 20개를 seed 20261014의 sample ID hash 순으로
고정했다. source/group 중복과 CAD render의 회전·반전 64px IoU≥0.85를 검사했다.
후자는 완벽한 건물/평면 계열 분리 증거가 아니다. 성능을 보고 사례를 제외하지 않는다.
calibration/test는 열거나 학습하지 않는다. 기존 모델의 과거 합성 학습에는 이 validation
CAD가 사용되지 않았다. 20개의 결과로 threshold·학습·checkpoint를 선택하지 않는다.

실제 입력은 원본 파일의 hash 검증 뒤 EXIF/letterbox만 적용한 512px다. CAD 합성 입력은
사용하지 않는다. 필요한 native DIMENSION을 길이 필터 없이 보존했고 학습 112개/검증
476개, 총 588개가 포함된다. 도곽 후보 제거는 전유부 의미 승인과 다르다.
학습 5개에는 active INSERT가 없고 검증 20개에는 11개가 있어 블록 학습 coverage가 부족하다.

## 방법

Frozen DINOv3 ViT-B/16, revision `5931719e67bbdb9737e363e781fb0c67687896bc`.
512px 원본 관측 feature를 cross-attention/conditional query decoder가 읽고 canonical
컴포넌트 종류/geometry·레이어 역할 후보, 5자리 native 치수값, 측정 방향과 종류,
active instance membership을 출력한다. 동일 CAD endpoint 관계로 consistency loss를 준다.
수정된 원호는 center/positive radius/start/span parameter이며 3점 circumcircle 회귀가 아니다.

canonical geometry 순서로 감독하고 unordered Hungarian으로 평가한다. 이 실험은 native
parameter와 관계 후보를 포함하지만 업무 wall/door/window/space semantic catalog와
dimension host solver를 완성한 모델은 아니다. 분해된 geometry는 여전히 primitive이다.
이 한계를 숨기거나 컴포넌트 복원 완성으로 표시하지 않는다.

A100 FP32 decoder, 12,000 steps, seed 20261014, 초기 LR 5e-4, 마지막 30% LR 5e-5.
GPU job timeout 90분, 당일 공시 $2.50/h 기준 상한 $3.75; 실제 청구는 확인 필요.
Job: `6acec91fc6628814522330fd`. private 코드/데이터 archive의 SHA를 bootstrap이 검사한다.

## 실행 전 고정한 평가

- 고정된 centered CAD 좌표계에서 구조 endpoint/arc midpoint 최대 오차 10mm 이하
  one-to-one matching. 정답에 맞춘 translation/scale/rotation fit을 하지 않는다.
- 구조 F1≥0.90, 필요한 치수 위치·값·실제 측정 길이 모두 통과, 치수 오류 허용 1mm,
  누락/오류/추가 치수 0개, native symbol coverage와 DXF audit를 사례별 검사한다.
- 5개 재현은 일반화가 아니다. 실패해도 별도 20개 평가를 기록하며 학습/검증 전체 분모를 유지한다.
- 파일 생성·학습 loss를 성공으로 해석하지 않는다. 모델이 미통과하면 Space에 올리지 않는다.
  완전한 DWG/semantic host/실제 CAD 수정·저장 검증은 수치 baseline과 별도다.

## 실행 증거와 결과

Private run: `outputs/raw-pairs-2026-10-14/`. 입력/정답 25개, factory SVG/DXF,
원격 고정 archive, source manifest, train log와 향후 prediction/metrics/비교 화면을 보존한다.
단위 검사와 실제 5개 target capacity/치수 coverage 사전 검사는 통과했다. 이는 성능 검사가 아니다.

첫 12,000 steps의 checkpoint SHA256:
`687f07d594e2d4a248178515dac9a38564ab139f7a88074c7aa48837b0d035f7`.
학습/평가 elapsed 140.47초; 설치·queue·Hub 업로드 시간과 실제 청구액은 별도다.

| 평가 | 사례 | 통과 | 구조 F1 (10mm) | 수치/위치/실제 길이가 모두 맞는 치수 |
| --- | ---: | ---: | ---: | ---: |
| 실제 train 재현 | 5 | 0 | 0.182642 | 0 / 112 |
| 별도 실제 validation | 20 | 0 | 0.000000 | 0 / 476 |

train 5개는 숫자 자체는 112개 모두 맞았지만 사례별 최대 길이 오류가 약 21~71mm였다.
실제 검증 형상은 선들이 흩어진 실패다. 정상 초기 초안/덜 fit한 컴포넌트 모델로 해석하지 않는다.
12,000은 작성자가 고른 상한이며 수렴/시각·기하 판정으로 선정한 step이 아니다.

후속 job `6acecb295ccb47ba0f78eed0`: joint batch 5, physical loss, 예측 dimension
constraint projection, 첫 scale head 고정으로 20,000 steps를 계획했다. 같은 primitive
출력을 보강하는 방법이며 사용자 지적 후 취소했다. 완료 checkpoint는 8,000 steps,
elapsed 369.41초 시점이다. 취소 전 학습은 더 진행됐으나 완료 step/최종 평가를 주장하지 않는다.
partial weights/manifest/log와 cancellation receipt를 보존했다. 후속 20개 평가는 미실행이다.

CAD-derived component factory로 전환한 뒤 5개 GT에서 34 swing opening, 148 wall-face
pair, 240 rectangular loop, 328 CEN guide, 112 DIMENSION을 조립했다. 실제 BLOCK/INSERT
422개를 생성해 컴포넌트 선택/재사용 기반을 확인했다. 4,306개 primitive 중 2,542개는
미분류로 남는다. 이는 정답 조립 검증이며 새 모델 학습/추론 성공이 아니다.

Private `review.html`는 실패한 모델 25개를 그대로 보여준다. `component-review.html`는
정답 CAD의 파라미터 조립을 별도로 표시한다. 실패 모델의 출력을 정답으로 교체하지 않았다.
