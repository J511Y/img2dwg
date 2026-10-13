# 1차 벡터 학습·Space 하네스

**현재 정정:** 첫 coordinate 모델은 실제 스캔 실패로 기본 배포에서 제외됐다.
EXP-044를 따른다. 모델 재배포에는 실제 구조/필수 치수 검증이 필요하며,
단순 upload/download receipt는 통과 근거로 사용할 수 없다. 지금 Space의 선 검출
기준선은 학습 모델이나 완성 CAD 복원으로 표시하지 않는다.

현재 `scripts/deploy_vector_space.py`는 명시적으로 표시된 관측 선 기준선만 배포한다.
`--dry-run`으로 전체 패키지와 source marker를 확인할 수 있다. 새 모델 서빙은 아직
구현하지 않았으며 아래 1차 모델 배포 명령·설명은 당시 기록이다.

최신 사용자는 첫 모델 학습과 별도 HF inference Space 배포를 승인했다.
원본 공유폴더는 이 실행에서 쓰지 않는다. v0.2 릴리스의 로컬 사본을 읽는다.

1. Python 3.12 별도 `.venv-train`을 만들고 `requirements-training.txt`를 설치한다.
2. `scripts/prepare_vector_training.py --dataset <release> --output <new-run>/supervision`으로
   학습/검증 split만 렌더링한다. 합성 이미지는 실제 준공도면 입력과 구분한다.
3. 5개 작성기 smoke, `tests/test_vector.py`, `scripts/smoke_vector_model.py`를 실행한다.
4. `scripts/package_vector_job.py`로 코드/데이터 SHA256을 고정한다. 버킷에 별도
   code prefix와 training archive를 업로드하고 bootstrap을 HF Jobs에서 실행한다.
5. 현재 baseline은 DINOv3 ViT-B/16 frozen + 1/4 해상도 4-slot component center/coordinate/
   layer-role head. 768px, seed 20261013, AdamW 3e-4, tiny 100/full 2,500 steps.
   A100/BF16, 실행별 90분 timeout. 실패 시 새 attempt prefix에 기록한다. 초기
   single-slot/endpoint 미정규화는 attempt-02 비교 baseline으로 보존한다. attempt-03은
   `scripts/compact_vector_supervision.py`로 border 후보 4,620개를 제외하고 등방 compact한
   입력에서 augmentation 후 endpoint 순서를 정규화한다. 자동 전유부 승인과 구분한다.
6. 체크포인트, 로그, manifest, unordered component 평가, receipt를 private bucket와
   private model repo에 보존한다. 직접 dimension 숫자/association 학습은 포함하지 않는다.
7. 당시 `scripts/deploy_vector_space.py`는 새 전용 private Space에 inference 파일만 올렸다.
   model revision/SHA를 고정하며 데이터셋 mount와 정답 CAD 접근은 제공하지 않는다.
8. `scripts/verify_vector_space.py --images <synthetic> <real> --output <private-check>`로
   실제 인증 upload → SVG/DXF download → raster-free SVG/DXF 재열기·SHA를 검사한다.

추론 입력은 EXIF 정규화·종횡비 보존 letterbox다. 출력은 좌표 decoder가 생성한
실제 SVG path/ARC·DXF LINE/ARC/DIMENSION 후보다. 이미지 embedding/contour tracing/
정답 검색을 예측으로 표시하지 않는다. graph edge는 endpoint 근접 후보이며 검증된
wall/opening host association이 아니다.

중요한 한계: center 겹침은 capacity manifest에 별도로 집계한다. native CAD의
parameter writer 검증과 모델 예측 성공은 다르다. layer role은 검수된 의미가 아니다.
전유부는 사용자가 자르기로 선택한다. 숫자를 읽지 못한 치수는 `?`, 축척 미확정은
DXF INSUNITS=0이다. 전체 선택 이미지 폭의 확인된 mm anchor가 있을 때만 단위를 적용한다.
모델 출력의 native symbol envelope는 원래 fixture block 복원으로 간주하지 않는다.

현재 직접 다운로드는 SVG·DXF·좌표 JSON·receipt다. DWG 변환기/실제 CAD UI의
열기·수정·저장/치수 완전성은 별도 완료 조건이며 DXF audit로 대체하지 않는다.

공식 구현 계약: [DINOv3](https://huggingface.co/docs/transformers/model_doc/dinov3),
[HF Jobs](https://huggingface.co/docs/huggingface_hub/guides/jobs),
[Space hardware/sleep](https://huggingface.co/docs/hub/en/spaces-gpus).
