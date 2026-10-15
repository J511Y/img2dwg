# 공유 노드·컴포넌트 학습 하네스

## 2026-10-15 · 최신 본학습 승인

사용자가 EXP-053 수정 반영1028학습/기존10 유지/별도20 검수/통과 시 Space를 요청했다.
[EXP-054](../experiments/2026-10-15-EXP-054-full-continuation.md)의새하네스를사용한다.
`prepare_full_continuation.py`→`package_full_continuation.py`→`train_full_continuation.py`→
후보 SHA 동결→`evaluate_full_continuation.py`→직접검수→통과 시 배포다.
20은학습archive에서분리한다. 기존20중1건의processed PNG train중복을학습전에찾아
미사용validation1건으로교체한정정20(19+1)을사용한다. pixel/source-group 교차0이지만
건물/layout family 분리는미완료다. 아래 full-v1은과거실행이며금지가이번승인을덮지않는다.

## 이전 실행 기록

현재 상태: full-v1은 completed/quality-failed, 원래 5개 0/5·0/112와 별도 20개
0/20·0/476이다. 새 실험은 중단하고
[상세 회고](../research/2026-10-14-experiment-retrospective.md)를 먼저 진행한다.
아래 명령은 기존 실행 재현 안내이며 새로운 유료 실행 승인이 아니다.

실행 구현: `structured.py` → `graph_decoder.py` → `graph_constraints.py` →
`graph_evaluation.py`. 원본 준공도면과 canonical CAD의 프레임을 분리한다.
입력은 실제 준공도면의 EXIF 보정/512 letterbox이며 합성 CAD 렌더가 아니다.

## 정답과 compiler

native DIMENSION, 문짝+원호, 벽 양면+폭, 사각 native loop, CEN, native path,
TEXT/MTEXT를 준비한다. 미확정 LINE은 `unresolved_edge`로 남긴다. 2.5m 이하,
256개 이하 도형의 작은 native 묶음은 pose/size+local prototype로 재사용한다.
prototype inference library는 train에서만 만든다. 현장 전체 CAD retrieval이 아니다.
WIN 레이어만으로 창, INSUL 패턴만으로 직원 확정 wall semantics를 만들지 않는다.

위치는 공유 노드에만 저장하며 컴포넌트는 node reference를 사용한다. compiler가
벽·문·native path/symbol의 실제 BLOCK/INSERT와 DIMENSION, MTEXT를 작성한다.
compiler GT 성공은 모델 복원 성공이 아니다. 원본은 읽기 전용이며 모든 결과는
ignored run 폴더와 private HF 버킷의 새로운 prefix에 저장한다.

## decoder와 학습

frozen DINOv3 관측 feature → node/component query sets → Hungarian matching.
컴포넌트는 종류·파라미터·공유 node pointer·host를 출력한다. 동일 x/y 축 관계는
node representative pointer로 감독한다. 이미지 획과 LINE handle의 일대일 대응은 없다.
위치 기반 anchor proposal은 참조 선택을 위한 보조이며 실제 compiler 좌표는 shared
node에서 읽는다. axis/dimension solver는 예측값만 받으며 GT CAD를 조회하지 않는다.

TF32를 끈 FP32, 5개 joint batch, 방향 class+free angle, 길이 수치와 high-confidence
0.1mm node 숫자 head를 사용한다. cardinal class는 source에서 확인된 직교 방향에만
감독하며 free class는 비직교 각을 유지한다. 0.1mm vocabulary는 출력 표현이며 실제
0.1mm 복원 정확성 주장이 아니다. 노드 숫자 confidence도 기하 검사 통과를 대체하지 않는다.

Hungarian assignment를 갱신하다가 실제 train node-set median error <100mm를 관측하면
5개 per-example assignment를 고정해 identity 변경에 따른 pointer 감독 흔들림을 줄인다.
source 저장 순서나 handle identity를 고정하는 방식과 다르다.

## 학습 판정과 배포

직전 검사 완료 후 45초 이상 경과하면 실제 예측으로 구조 F1, component F1, shared-reference F1, 필수 치수 숫자·위치·
실제 길이, invalid references, known geometric host를 확인한다. 구조 >=.90,
component/shared-reference >=.95, 치수 누락·오류 0, 기하 tolerance 10mm/치수 1mm다.
서로 다른 checkpoint 두 번의 전체 pass를 stable pass로 정한다.

quality plateau는 5회 유효 지표 정체 후 LR을 줄이고, 세 번 반복되면 실패 진단으로 종료한다.
별도의 wall-clock cap은 자원 제한이며 convergence/fit 증거가 아니다. loss와 steps만으로
완료하지 않는다. 미측정 host는 분모 0으로 명시하며 recall=1을 host 성공으로 소개하지 않는다.

5개는 구현 재현용이다. 본학습은 실제 train 1,028개, development는 validation에서
미리 정한 16개, 별도 노출 pilot 20개는 선택·threshold 조정에서 제외한다. test/calibration은
사용하지 않는다. 시각 검수와 20개 평가, CAD roundtrip이 끝난 통과 후보만 Space 배포한다.

## 재현 명령

1. `prepare_shared_graphs.py --dataset PRIVATE_RELEASE --output NEW_RUN/full-data --cohort OLD_25/index.json --full`
2. `supplement_shared_catalog.py --source NEW_RUN/full-data --output NEW_RUN/full-data-v2`
3. `package_shared_job.py`로 source/data/initializer SHA를 고정하고 `hf buckets sync/cp`로 새 prefix에 업로드한다.
4. HF Jobs에 private bucket volume과 `--secrets HF_TOKEN`을 전달한다. published protocol을 덮어쓰지 않는다.
5. 완료된 run은 새 로컬 디렉터리에 readback한다. 진행 중 같은 이름의 파일을 sync하면 size/mtime
   비교로 이전 checkpoint가 남을 수 있으므로 initializer는 별도 immutable cp와 SHA readback을 사용한다.
6. `build_shared_review.py`는 실제 input/GT/model 열을 분리한다. prediction 파일이 없으면 대기로 표시한다.

모델 실행, 품질 pass, 본학습, 20개 검증, Space 배포는 별도 상태로 보고한다.

## 현재 실험 미리보기 배포

사용자가 5개 비교를 보고 오차를 수용한 뒤 배포·Space 갱신을 명시 요청했다.
EXP-046 tiny-v4는 GPU 5/5·112/112 치수, CPU 4/5·112/112 치수이며 CPU 20개는
0/20·0/476이다. 이 checkpoint는 승인된 five-case pilot로 제공하고 production
quality pass를 주장하지 않는다. 이전 배포 gate의 예외 범위는 이 실험 미리보기뿐이다.

`deploy_shared_space.py --checkpoint PRIVATE_COMPLETED_RUN --verification MATCHING_RECEIPT
--output NEW_DEPLOYMENT --experimental-authorized`가 private model/Space를 pin한다.
`verify_shared_space.py`는 Space runtime SHA, checkpoint SHA, 인증된 실제 이미지
upload/download, SVG raster 없음, native INSERT/DIMENSION, DXF unit/audit와
보정 전후 dimension 숫자/공유 node 보존을 검사한다. `verify_shared_oda.py`는 실제
Space DXF의 DWG/DXF 재열기를 검사한다. CAD UI 수정/저장 증거로 승격하지 않는다.
