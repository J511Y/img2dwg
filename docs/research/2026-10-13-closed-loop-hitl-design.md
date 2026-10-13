# 반복 그리기·System-1·HITL 및 변경전 DWG 페어 설계

작성: 2026-10-13 KST. 사용자 추가 설명과 첨부 DWG thumbnail, 기존 crop 코드 및 공식 Jev/Laya 문서를 확인한 설계 보완이다. 구현·데이터 재추출·추론·학습은 미실행이다. [사내 자산 재조사](2026-10-13-domain-reassessment.md)와 함께 현재 적용 계약으로 읽는다.

## 1. 사용자의 System-1 구상을 정확히 반영

사용자는 입력 도면과 현재까지 완성된 CAD의 렌더를 비교해 **다음 line/door/shape를 판단하고 도구로 실행하는 반복 루프**를 구상했다. System-1의 역할을 QC/routing만으로 한정했던 이전 보고서는 이 의도를 충분히 담지 못했다. 이번에는 다음 동작을 선택하는 controller 자체를 연구 대상으로 추가한다.

```text
원본 이미지 + 현재 CAD 렌더 + 현재 엔티티/제약 + 사람 수정
  → 시각 비교·미완성 구조/후보 동작·파라미터 제안
  → 다음 동작 선택 / 보류 / 사람 확인
  → 검증된 CAD tool 실행
  → 새 CAD 상태·렌더·검사 결과
  → 반복, 부분 수정, 완료 검수
```

이미지 비교·위치/치수 파라미터 제안·후보 선택·도구 실행을 각각 구분한다. 어느 모듈의 시간/비용이 큰지 측정하고 병합/분리 여부를 실험한다. 빠른 판단 모델을 썼다는 이유로 이미지 처리 비용까지 낮다고 가정하지 않는다.

## 2. 세 접근법을 공통 상태·도구·평가로 비교

| 접근 | 실제 비교할 구조 | 장점 가설 / 불확실성 |
| --- | --- | --- |
| VLM 전체 controller | 두 이미지·상태를 보고 parameterized CAD action 또는 batch를 제안 | 시작은 단순하지만 긴 action sequence·렌더/토큰·retry 비용과 오류 누적. fine-tuning 필요성/효과는 실측 |
| ML/DL structured model | image encoder→canonical entity/graph·제약/치수 association, solver+writer | 한 번 또는 적은 횟수로 geometry를 내는 속도/비용 가설. 저화질 전처리·data/loss/base model 선택 필요 |
| System-1/hybrid controller | 시각 모듈이 후보 action과 상태를 만들고 빠른 모델이 선택; 또는 별도 vision action policy를 학습 | VLM 호출을 줄일 수 있으나 후보 생성의 누락·좌표 오류와 selector 한계. 두 이미지 처리 자체를 해결할 필요 |

ML/DL 후보가 빠르고 저렴할 것이라는 사용자 기대는 가설로 유지한다. VLM에도 step별 전체 history 대신 현재 state/국소 crop, connected action batch, 큰 구조 일괄 복원 후 국소 repair를 대조한다. 세 후보는 같은 dataset/split·CAD tools·HITL 허용량·품질 기준으로 평가한다.

## 3. Jev/Laya의 현재 기능과 vision controller를 구분

[TypeSafe 공식 Jev 문서](https://docs.typesafe.ai/introduction)는 state에 대한 choice/score/noul을 제공한다. [Laya 공식 model card](https://huggingface.co/convaiinnovations/laya)는 text/JSON 기반 decision 모델을 설명한다. 두 도면 이미지를 직접 입력받아 다음 CAD 좌표를 제안하는 기능을 이번 출처에서 확인하지 못했다. System-1이라는 이름 전체에 이미지 기능이 없다는 뜻은 아니다.

따라서 아래 두 실험을 구분한다.

1. **기존 Jev/Laya를 selector로 사용:** vision encoder/detector/structured decoder가 missing edges·endpoints·door host·후보 좌표/제약을 만들고, 텍스트/JSON 상태로 다음 action을 고르게 한다. 입력 후보에 정답 동작이 포함되는 비율과 selector 조건부 정확도를 분리한다. 후보에 없으면 `none/ask_human`을 선택할 수 있어야 한다.
2. **두 이미지 조건의 빠른 vision action policy:** 원본과 현재 CAD 렌더의 paired visual features 및 entity graph로 action type·target entity·parameter residual·stop/abstain을 예측하는 별도 모델을 사내 데이터로 학습한다. 이는 Jev/Laya checkpoint에 이미지 URL을 넣어 되는 기능이 아니라 새 아키텍처/학습 실험이다.

selector의 finite choice와 임의 연속 좌표 생성은 다르다. 가능한 모든 좌표를 choice 목록으로 펼치지 않는다. geometry proposal/solver가 파라미터를 제안하고 selector는 bounded candidate를 선택한다. choice 수·순서·비슷한 후보·잘못된 state·한국어를 평가하며 confidence가 CAD 검사 실패를 덮지 못하게 한다.

## 4. CAD action과 상태 계약 초안

action 후보: `add_line`, `add_polyline`, `add_arc`, `add_door`, `add_window`, `move_endpoint`, `set_wall_width`, `add_dimension`, `apply_constraint`, `delete_entity`, `finish`, `ask_human`.

모든 action은 고유 ID, target entity/host, CAD 좌표·unit, 의도한 제약, observation evidence, expected state revision, confidence/unknown을 갖는다. `add_door`는 단순 기호 drawing과 opening/host wall 관계를 함께 검사한다. 좌표 없는 "여기에 선을 그린다"는 실행 가능한 action이 아니다.

실행기는 schema·finite coordinates·host/constraint·revision을 검증하고 transaction/undo 기록을 남긴다. 중복 실행은 action ID로 차단한다. 비동기 결과가 사람 수정 이전 state를 기준으로 왔으면 적용하지 않는다. 반복 edit/undo loop·진전 없는 step·최대 iteration·time/cost cap을 두고 보류/사람 검수로 전환한다. 완료 판단도 CAD 상태 검사를 통과해야 한다.

CAD는 매 step 메모리의 CAD-IR/scene graph에서 갱신·렌더하고 필요한 checkpoint/최종 시점에 DWG를 export하는 방식을 후보로 둔다. 매 선마다 DWG 변환기를 호출하는 안과 구분해 tool/export 비용을 측정한다. 아직 이 실행기는 구현하지 않았다.

## 5. 데이터 선택: 준공도면 + 변경전후.dwg만

사용자가 지정한 주력 supervised corpus는 **같은 워크 의뢰 폴더에 `준공도면` 파일과 `변경전후.dwg` 파일이 모두 있는 경우**다. `건축물현황도/단위세대평면도/단위세대도면`만 있는 사례는 이 주력 풀에서 제외한다. 별도 실험 풀로 쓰려면 별도 범위·manifest를 명시한다.

파일 stem `준공도면`의 허용 확장자·멀티페이지 PDF 처리, 실제 파일명 alias, 여러 버전이 있을 때의 선택 기준은 inventory에서 확인하고 명시한다. 숫자 suffix·유사 이름을 임의 승인하지 않는다. 형식이 아직 확정되지 않았다는 이유로 파일을 조용히 누락하지 않고 unsupported 목록을 보고한다. 이미지 page/crop 선택도 검수한다.

기존 `data-pipeline/data_pipeline/dwg_crop/pipeline.py::REQUIRED_REFERENCE_STEMS`는 4종 파일명을 허용하고 `find_required_reference_pair`는 처음 발견한 허용 sibling을 반환한다. 새 계약과 다르므로 기존 전체 manifest를 그대로 사용하지 않는다. 기존 2,286건 manifest의 준공도면 분류 2,148건은 **과거 기록상의 후보량**이며 새 정책을 통과한 gold 수가 아니다. 현재 original folder 존재·파일 버전·pair 정합을 다시 감사한다.

## 6. 정답 영역: 첨부 이미지 왼쪽 빨간 박스의 변경전 평면

첨부 화면은 같은 DWG 안의 좌우 두 도면 패널과 왼쪽 평면 주변 빨간 박스를 보여준다. 사용자 설명에 따라 이 사례의 왼쪽 영역을 변경전 복원 target으로 삼는다. 오른쪽 변경후 geometry를 정답에 섞으면 입력에 없는 변경 설계를 학습하게 된다.

thumbnail은 저해상도 참조이며 정밀 geometry/치수 GT가 아니다. 빨간 박스의 화면 픽셀 좌표를 실제 CAD crop bbox로 그대로 변환하지 않는다. 실제 DWG modelspace/paperspace·도곽·변경전/후 title anchor·entity extents와 고해상도 CAD render에서 대상 패널과 필요한 치수 범위를 확인한다. 다른 양식/방향에서는 변경전이 항상 왼쪽이라는 가정을 강제하지 않는다. 근거가 충돌하면 검수 대상으로 보류한다.

crop은 변경전 평면·문·창·측정 geometry·필요 치수를 유지하고 도곽·회사 title block·개인정보·변경후를 배제한다. 공간 crop과 entity reference 보존을 구분한다. DIMENSION·block/INSERT·xref·text style·dimstyle은 경계 밖 참조가 있을 수 있으므로 dependencies를 확인한다. 경계를 가로지르는 엔티티는 bbox 교차만으로 통째로 포함하지 않고 필요한 portion/association을 검수한다.

기존 `detect_before_crop`는 변경전/후 text anchors, sheet frame, inner frame/dense plan을 이용하며 marker가 없으면 `left_half_fallback`도 쓴다. 현재 exporter는 fixed inner frame 검출을 요구하지만 의미상 올바른 변경전 영역 승인을 보장하지는 않는다. `write_cropped_dxf`는 crop 근처에 bbox가 교차하는 엔티티를 유지하므로 오른쪽/도곽 contamination과 치수 참조 보존을 추가 감사한다. 원본 파일은 수정하지 않는다.

최종 pair manifest에는 source image/DWG hash, 선택 page·before panel, CAD bbox·unit·origin transform, before/after 판별 근거·검수, 포함/제외 layers·entities/dependencies, canonical CAD-IR hash, source→target 정합 승인과 group split을 남긴다.

## 7. 완성 DWG에서 반복 동작 학습 데이터를 만드는 방법

사람이 도면을 보고 완성한 DWG는 유용한 **최종 geometry 정답**이다. 현재 파일만으로 실제 작업자의 stroke/tool 순서를 복원했다고 주장하지 않는다. entity 저장 순서나 handle 순서가 사람이 그린 과정이라는 보장도 없다.

ML/DL의 일괄 entity/graph 감독은 최종 DWG에서 만들 수 있다. 반복 controller 감독은 검수된 target graph의 일부 엔티티를 생략하거나 endpoint/폭/host 오류를 주입해 partial CAD state를 만들고, 원본 입력과 state render에서 가능한 다음 repair/add action을 구성한다. 여러 올바른 순서가 가능하므로 임의 단일 순서를 유일 정답으로 강제하지 않는다. connected wall/opening batch·order permutation·set-valued valid actions·teacher rollout을 비교한다.

이렇게 만든 것은 **최종 DWG에서 파생한 합성 action trajectory**다. 사람 작업 기록과 별도 provenance를 남긴다. GT는 학습 label/reward 생성에만 사용하고 추론 policy/후보 생성 입력에 제공하지 않는다. teacher-forcing의 깨끗한 partial state 외에 실제 모델 오류가 섞인 rollout과 복구 state를 포함해 오차 누적을 평가한다. 단순히 모든 미래 GT 엔티티를 후보로 주면 실환경과 다른 쉬운 selector 문제가 된다.

후속 HITL UI에서 사람이 실제 수행한 수정·고정·undo 이벤트를 수집하면 **실제 correction trajectory**를 추가할 수 있다. 검수 완료·권리·version·split을 확인한 기록만 학습에 반영한다. 같은 평면의 partial states와 합성 distortions는 모두 같은 group split에 둔다.

## 8. HITL은 정상적인 제품 경로

100% 자동 완벽 복원을 전제로 하지 않는다. 중간 preview, 불확실 구간, 치수/축척 anchor, 다음 제안의 accept/reject와 직접 편집을 정상 흐름으로 제공한다. 사람이 수정한 geometry/constraint/semantic을 구분하고 어떤 것을 고정했는지 명시한다.

최소 흐름: 입력/변경전 영역 확인→축척/anchor 확인→초기 구조 생성→중간 수정/다음 action 승인→국소 재복원→최종 CAD 검수/export. 원본·현재 CAD·difference overlay를 함께 보여준다. 차이는 정합된 좌표에서 계산해 perspective 차이를 누락으로 오인하지 않는다.

사용자는 corner/line·벽 폭/간격·door host·치수를 수정하거나 특정 entity/영역을 잠글 수 있다. 재생성은 잠긴 엔티티를 보존하며 constraint 충돌시 설명·보류한다. 부분 수정이 다른 geometry에 전파되는 범위와 변경 내역을 보여주고 되돌리기·checkpoint/resume을 제공한다. uncertain 치수를 실제값처럼 표시하지 않는다.

HITL 성공은 자동 metric 외에 사용자 수정 시간/횟수, 완료까지 intervention 수, 잠금 위반, 자동 재작업률, 재현 가능한 CAD open/edit/save와 총비용으로 판단한다. 전문가 수정이 있었다는 사실을 순수 자동 성능에 숨기지 않는다.

## 9. 우선 비교와 비용 평가

먼저 준공도면+변경전 target의 소량 gold를 확정하고 같은 tools/renderer 위에서 일괄 DL, VLM step/batch, 시각 proposal+Jev/Laya selector, 별도 vision action policy를 비교한다. EXP-029~034에 등록한다.

E2E 비용은 image perception + candidate proposal + 각 decision + tool/solver + render + repair/retry + checkpoint/export + human time을 포함한다. 모델별 warm latency만 비교하지 않는다. step 수와 시각 재분석 주기를 고정/보고하고 긴 history 대신 현재 state만 전달하는 방식의 정보 손실도 평가한다.

controller는 next-action accuracy뿐 아니라 candidate recall, parameter error, per-step progress, duplicate/invalid action, stop/abstain, long-horizon success·비용·HITL 작업량을 평가한다. 일괄 DL도 실패 후 local repair를 허용하는 동일 사용자 흐름에서 비교한다. 문서 세팅 단계에서 어느 방식이 가장 저렴하거나 정확하다고 확정하지 않는다.
