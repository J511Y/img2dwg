# 1,028개 본학습과 기존10 유지 · EXP-054

이 문서는 `train_full_continuation.py`의 실행 계약이다. 실제 결과는
[EXP-054](../experiments/2026-10-15-EXP-054-full-continuation.md)와 immutable receipt를 따른다.
현재 모델이 일반화에 통과했다는 뜻이 아니다. 새 유료 실행의 포괄 승인이 아니다.

## 입력과 분리

`prepare_full_continuation.py`는 기존 full-data-v3에서 train1028/development16만 새 폴더로
복사하고 CPU DINO 특징을 저장한다. 기존10은 EXP-053의 같은 특징 bytes를 재사용한다.
원본/이전 run을 덮지 않는다. input/target/components/features의SHA를 index에 묶는다.

실제 의뢰1028개와 고유 processed PNG943개를 구분한다. 같은 입력에 두 세대/반전 target이
연결된 모호성은 자동 삭제하지 않으며 데이터 감사에 남긴다.

source-identity group과 **processed PNG hash**를 둘 다 검사한다. 기존 pilot20 중1건의
pixel train 중복은 label/예측을 보기 전에 미사용validation의 fixed hash rank1건으로 교체했다.
정정20(19+1)은 별도 `evaluation-index.json`과 SHA로 고정한다. 기존 결과를 덮어쓰지 않는다.
건물/layout family grouping 완료나 완전히 새 sealed test로 주장하지 않는다.

`verify_full_input_pixels.py`는 회사 원본이 아닌 이전 릴리스의 원본 사본에서 primary page와
EXIF 방향을 읽고 실제 serving `normalize`의512 입력 픽셀을 비교한다. `--retention-only`는
기존10만 검사한다. 최종30 검사는 candidate freeze/CPU 평가 receipt 이후에만 실행하여
20개 원본을 사전에 열지 않는다. 이 검사는 모델 재추론이나 품질 통과를 대신하지 않는다.

## 모델과 실행

source6ca23df9… 전체를 동결하고 새128 hidden 잔차 분기만 학습한다. source Adam은
재시작하지 않는다. 새 분기만 새 Adam .0003을 사용한다. 원래 adapter의 보호 span을
바꿔 추가5 학습 함수를 없애지 않는다. 새 보호 span은 CAD가 아닌 열 개 비전 특징이다.
저장/재로딩은 `graph_loading.build_graph_model`의 adapter stack을 사용한다.

고정 query reserve는 train 최대의1.25배+32다. image count top-k는 전체 reserve에서 고른다.
GT count/prefix crop은 forward에 주지 않는다. 보호 특징 residual0인 eval 입력은
기존 모델 함수를 그대로 사용한다. 이는 비슷한 새로운 사진의 성공 보장이 아니다.

`package_full_continuation.py --data NEW_DATA --holdout-source SOURCE_DATA
--evaluation-index FROZEN_EVAL_INDEX --release NEW_RELEASE --remote-prefix runs/NEW_RUN`로
code/train/twenty archive를 분리한다. 모든 published file을 private bucket에서 전부 readback하고
SHA를 확인한 뒤 bootstrap을 실행한다. job image/timeout/source SHA/데이터 SHA를 기록한다.
EXP-054의 실행 상한은 training180분/job240분 A100 한 작업이다.

## 품질과 종료

기존10은 GPU native10/10·252/252를 선행 검사한다. 새 분기의 현재 이미지 좌표 업데이트를
50mm 이하로 제한한다. 이 guard는 다른1017개 신규 입력의 변화를 동시에 검사하지 않는다.
기존10 보존은 동결된 base bytes, 보호 특징, 주기적 native10/fresh CPU로 따로 확인한다.

5분 간격으로 retention10/development16/고정 TRAIN probe16의 실제 native CAD를 검사한다.
schema/단위/audit/참조/치수 숫자와 실제 길이를 포함한다. 모델 confidence로 실패를 덮지 않는다.
적어도1028개 전체 노출 전에는 best 후보를 선택하지 않는다. step 수나 loss 자체로 fit을 선언하지 않는다.

선택 score는 구조/component/ref F1+필수DIM joint fraction+최대0.1의참조 node Chamfer 항이다.
거리 보조는 actual referenced nodes만 사용하며 unused grid로 개선시킬 수 없다.
strict pass는 원래10mm 구조/1mm 치수·누락0 기준을 유지한다. stable pass는 두 checkpoint다.

published source의 plateau 판정은 전체 자료 노출 뒤 `epoch>=3`부터다(세 번째 순회 진입).
manifest 초기 문구의 "3회 순회 완료"와 차이가 있어 EXP-054에 감사 정정을 보존했다.
5회 지표 정체에서 LR .3배, 세 단계에서 quality-plateau로 끝낸다. 시간 cap은 품질 통과가 아니다.

## 고정 후보와 최종 검수

학습이 끝나면 weight/config SHA를 `candidate-freeze.json`으로 고정한 뒤 처음으로
twenty archive를 추출한다. CPU fresh 이미지로 기존10/정정20을 평가하고 source EXP-053도
같은20에서 사전 등록 기준선으로 한 번 측정한다. 이후20으로 재학습/threshold 조정을 하지 않는다.

job 종료 후 새 로컬 폴더로 readback한다. running snapshot과 final receipt를 섞지 않는다.
`verify_full_continuation.py`는 모델/동결 base/입력/cohort/guard와30개 실제 native DXF를
독립 검사한다. native CAD 원점은 `x=px*scale, y=(height-py)*scale`이며 metric의 centered
좌표와 구분한다. 숫자·측정점으로 DIM을 대응시키며 coincident annotation을 삭제하지 않는다.

`build_full_continuation_review.py`는 실제 input/GT/model을 분리하고30개 SVG/DXF와7개
contact sheet·SHA provenance를 만든다. agent가 모든 결과를 직접 본 다음 별도 검수 receipt를 쓴다.
단순 원점/반전과 실제 구조 실패를 구분하고 CAD 기존 편집을 새 자동판별 gate로 만들지 않는다.

실제 model DXF→DWG→DXF 재열기와 CAD UI edit/save는 별도 증거다. 파일 audit 성공을
새 현장의 구조/치수 성공으로 부르지 않는다. 미통과 모델을 Space에 반영하지 않는다.
기존 `deploy_shared_space.py`는5개 pilot 전용이며 stack 모델 배포기로 사용하지 않는다.
통과 시에는 stack/decoder contract를 읽는 serving 경로와 실제 인증 upload/download를 먼저 검증한다.
