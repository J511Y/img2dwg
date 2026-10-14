# 컴포넌트 출력과 학습 판정 정정 · 2026-10-14

## 잘못된 구현 판단

EXP-045의 실제 raster 학습도 `segment/arc/dimension/symbol`의 독립 geometry를
canonical 순서 query에 회귀했다. DIMENSION/active-instance 후보와 shared-point loss를
더해도 업무 wall/door/window/space 컴포넌트 decoder가 되지는 않는다. 변수 개수·계열이
다른 집을 같은 query 위치로 출력하면서 geometry를 섞는 실패가 실제 검증 화면에 드러났다.
이를 under-fit이나 작은 loss의 성공으로 해석하지 않는다. 설계 가설의 실패다.

12,000 steps는 작성자가 고른 실행 상한이다. 학습 재현 metric/수렴 실험으로 정한
학습량이 아니다. 첫 loss는 5개 train의 정규화 좌표/종류/숫자 평균이며 mm·위상·별도
20개 일반화 성능을 나타내지 않는다. 숫자 112개가 맞아도 실제 길이 21~71mm 오류가 남았다.

후속 job `6acecb295ccb47ba0f78eed0`은 같은 primitive 출력에 물리 loss를 보강하는
실행이었다. 사용자 검증 이미지 지적 후 취소했다. 8,000-step checkpoint와 로그를
private bucket에 보존한다. 20,000 steps 완료나 새 20개 평가를 주장하지 않는다.

## 지금 확인한 CAD 구조와 구현

5개 실제 before CAD의 `WIN` layer에는 문 원호·문짝과 다른 사각/가구 geometry가
섞여 있다. layer명만으로 window를 정답 지정할 수 없다. 직원 확정 비내력/내력
semantics와도 다르다. source에서 geometry와 membership/parameter를 먼저 추출한다.

`img2dwg/components.py`와 factory는 다음 CAD-derived 조립을 구현했다.

| 종류 | 주 파라미터 | 5개에서 조립한 수 |
| --- | --- | ---: |
| 문 회전 조립 후보 | hinge, opening radius, swing, leaf style/상대각 | 34 |
| 벽 양면 조립 후보 | 중심축, 두께, 양면의 시작/끝 offset | 148 |
| 사각 native 루프 | 위치, 회전, 폭, 높이; 업무 의미 미확정 | 240 |
| 중심선 CEN guide | shared node/edge | 328 |
| native 치수 | 측정 anchor node, 수치, 종류/방향 | 112 |

문 너비 변경은 문짝과 원호를 함께 변경한다. 벽 두께 변경은 중심축 양쪽 면에
함께 적용된다. 422개의 compound는 실제 DXF BLOCK/INSERT로 작성하고 재사용 가능한
normalized block 정의를 공유한다. 이를 단순 JSON group label로 대신하지 않는다.

5개 GT 재조립에서 기하 최대 오차 <1e-3mm, 치수 112개 보존, DXF audit 0을 확인했다.
실제 BLOCK/INSERT를 재열고 분해한 world geometry도 같은 허용 오차를 통과했다.
ODA DXF→DWG→DXF 5개에서 422개 INSERT/112개 DIMENSION/mm를 보존했다.
이는 파일/정답 factory roundtrip이며 실제 CAD UI에서 편집·저장을 증명한 것은 아니다.
이는 **CAD 정답 파라미터 factory 검증**이다. 이미지 모델이 구조를 맞춘 성과가 아니다.
원래 4,306개 primitive 중 1,764개를 구조화했고 2,542개(59.03%)는 미분류 잔여다.
창·fixture·발코니/공간·TEXT/MTEXT/native INSERT library의 전체 catalog는 미완성이다.
잔여를 모두 false background나 확인된 window/wall로 학습시키지 않는다.

## 다음 모델이 출력할 것

독립 LINE 집합 대신 공유 node 좌표, component 종류/parameter, edge와 host/치수 관계를
출력한다. builder가 문짝+원호, 벽 중심축+폭, 창/기호 prototype와 native DIMENSION을
함께 작성한다. 가변 개수 component의 set matching을 사용하며 source handle/고정 query
순서를 서로 다른 현장의 컴포넌트 identity로 취급하지 않는다.

치수는 문자열만 맞추는 별도 성과가 아니라 동일 node/edge 길이의 제약이다.
관계 미확정은 masked/unknown으로 표시하고 dangling door/상충 치수·비연결 wall을
검증한다. centerline→전체 치수→상세라는 사용자 작업 순서를 출력/학습에 반영한다.
source CAD retrieval을 inference에 넣지 않는다.

## 실행 순서와 판정

1. 부족한 component catalog와 관계를 보강하고 실제 5개 GT factory/단위/native CAD
   재열기를 확인한다. 현재 성공은 이 단계의 일부다.
2. 새 structured decoder에서 5개 tiny-fit을 재현한다. 허용 mm·치수 누락·topology와
   시각 결과를 일정 간격의 checkpoint에서 확인하며 loss만으로 fit을 판정하지 않는다.
   품질 plateau가 지속되면 architecture/감독을 조사하고 횟수만 늘리지 않는다.
3. 5개는 구현 재현 검사다. 5개만 외운 모델을 20개 새 구조의 범용 모델로 취급하지 않는다.
   본학습은 준비한 실제 train 페어로 수행하고 별도 20개는 학습/선택/threshold 조정에
   사용하지 않는다. 기존 노출 validation 20개는 pilot이며 독립 최종 test를 주장하지 않는다.
4. 미통과 모델은 Space에 올리지 않는다. 직접 DWG/실제 CAD 편집·저장/치수 및 구조
   검증을 파일 생성·factory 성공으로 대신하지 않는다.

새 component/node decoder 구현과 학습은 아직 미완료다. 계획을 실행된 모델 성과로
소개하지 않는다. 현재 private 화면은 `review.html`(실패한 실제 모델 25개)와
`component-review.html`(정답 파라미터 조립 검증 5개)을 분리해 보여준다.
