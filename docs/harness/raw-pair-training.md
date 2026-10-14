# 실제 준공도면 5개·별도 20개 학습/검증 하네스

사용자가 2026-10-14 실행·검증된 모델의 Space 재배포를 승인했다. 실제 실행 정본은
[EXP-045](../experiments/2026-10-14-EXP-045-real-pairs.md)다. 원본/기존 운영 모델을 변경하지 않는다.

**현재 판정:** 아래 primitive 모델은 실패했고 후속 학습을 취소했다. 당시 실행의 재현
계약이며 새 모델 추천 실행기가 아니다. 다음 구현은
[컴포넌트 설계 정정](../research/2026-10-14-component-decoder-correction.md)을 따른다.
`verify_component_factory.py`는 5개 CAD 정답 조립을 검사한다. 이 성공을 모델 성능으로
승격하거나 그 정답을 inference 출력으로 표시하지 않는다.

1. `.venv-train`의 Python 3.12와 `requirements-training.txt`를 사용한다.
2. `scripts/prepare_raw_pairs.py --dataset <v0.2> --output <new-run>/data --size 512`
   는 기존 train 5개/validation 20개를 seed+hash로 고정한다. EXIF/letterbox만 적용한
   실제 input과 native CAD target을 별도로 쓴다. min-length=0으로 치수를 보존한다.
   source/group·CAD near-family 검사는 split 검사이며 특징점 정합을 재개하지 않는다.
3. `tests/test_raw_pairs.py`는 작은 치수 보존, 숫자-only 오류, capacity 누락,
   실제 decoder gradient/입력 의존성, 공유 geometry의 치수 projection을 검사한다.
4. `scripts/package_raw_job.py`는 첫 코드/data archive SHA와 protocol을 작성한다.
   HF bucket의 별도 immutable prefix에 코드/data를 올리고 `job_raw_bootstrap.py`를
   실행한다. token은 `hf jobs run --secrets HF_TOKEN`으로 넘기며 값은 출력하지 않는다.
5. 첫 run은 real 5개만 12,000 steps 학습한다. validation 20개는 종료 후 한 번 평가하며
   전체 SVG/DXF/JSON/metrics를 저장한다. source CAD retrieval이 inference에 없다.
6. 후속 `job_raw_refine.py`는 첫 체크포인트의 SHA를 검사하고 5개 training 실패를
   근거로 joint batch/물리 좌표·측정 길이 loss와 예측 치수 solver를 적용한다.
   첫 학습에서 배운 scale head를 고정하며 20,000 steps, LR 1e-5→1e-6이다.
   같은 20개는 결과 보고에만 사용한다. 평가 결과를 보고 threshold를 바꾸지 않는다.
7. `scripts/build_raw_review.py --root <new-run> --run <attempt>`는 원본/정답 CAD/예측,
   wheel/drag 벡터 검수와 모든 native 치수의 숫자/실제 길이/위치 오차를 보여준다.
   localhost loopback에만 serve하며 원본·고객 도면은 Git에 넣지 않는다.

평가는 `img2dwg/raw_evaluation.py`의 frozen mm protocol로 수행한다. SVG/DXF audit는
구조·치수 성능과 별도다. 모델이 미통과하면 기존 Space의 진단 기준선을 유지한다.
기존 `deploy_vector_space.py`는 진단 기준선만 올리는 실행기다. 모델을 자동으로 다시
배포하지 않으며, 통과한 후보에 한해 모델 서빙/DWG 경로의 실제 재검증을 수행한다.

현재 native geometry 분해·DIMENSION/INSERT 관계 후보는 구현했지만 업무 wall/door/
window/space 의미 catalog와 dimension host solver는 미완성이다. 이 여부와 필요한
치수 coverage, case별 실패, pre/post constraint 결과를 숨기지 않는다.
