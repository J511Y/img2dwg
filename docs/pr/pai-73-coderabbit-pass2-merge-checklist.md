# PAI-73 coderabbit pass2 머지 체크리스트

## 0) 기준 확인
- [ ] 작업 브랜치: `feature/PAI-73-coderabbit-pass2`
- [ ] `origin/develop` 대비 ahead 3 / behind 0 확인
  ```bash
  git fetch origin
  git rev-list --left-right --count HEAD...origin/develop
  # 기대값: 3 0
  ```
- [ ] `origin/feature/PAI-73-coderabbit-pass2` 대비 ahead 2 / behind 0 확인
  ```bash
  git rev-list --left-right --count HEAD...origin/feature/PAI-73-coderabbit-pass2
  # 기대값: 2 0
  ```

## 1) 게이트 실행
- [ ] pre-merge guardian gate 실행
  ```bash
  BENCH_IMAGES=/tmp/img2dwg-bench-images \
    bash scripts/guardian_premerge_gate.sh
  ```
- [ ] 결과 `DECISION: PASS` 확인
- [ ] 필요 시 로그 보존
  ```bash
  ts=$(date +%Y%m%d-%H%M%S)
  BENCH_IMAGES=/tmp/img2dwg-bench-images \
    bash scripts/guardian_premerge_gate.sh | tee docs/logs/pai-74-gate-${ts}.log
  ```

## 2) Push & PR 생성
- [ ] 원격 push
  ```bash
  git push origin feature/PAI-73-coderabbit-pass2
  ```
- [ ] PR 생성 (base: `develop`, head: `feature/PAI-73-coderabbit-pass2`)
  - compare 링크: `https://github.com/J511Y/img2dwg/compare/develop...feature/PAI-73-coderabbit-pass2`
- [ ] PR 본문은 아래 파일 사용
  - `docs/pr/pai-73-coderabbit-pass2-pr-body.md`

## 3) 리뷰/머지 전 최종 확인
- [ ] CI green (tests/lint/type/gate)
- [ ] benchmark 산출물 최신성 확인 (`run.git_ref == PR HEAD`)
- [ ] triad gate `passed=true` 확인
- [ ] 머지 전략 선택
  - 권장: **Create a merge commit** (3개 커밋 단위 보존)

## 4) 머지 후 develop 반영
- [ ] 로컬 develop 업데이트
  ```bash
  git checkout develop
  git pull --ff-only origin develop
  ```
- [ ] 작업 브랜치 정리(선택)
  ```bash
  git branch -d feature/PAI-73-coderabbit-pass2
  git push origin --delete feature/PAI-73-coderabbit-pass2
  ```

## 5) 최종 벤치 요약 보고 생성
- [ ] 핵심 수치/경로 추출
  ```bash
  uv run python scripts/extract_benchmark_highlights.py \
    --summary output/benchmark/benchmark_summary.json \
    --results output/benchmark/benchmark_results.json \
    --format markdown
  ```
- [ ] 보고서 파일로 저장(선택)
  ```bash
  uv run python scripts/extract_benchmark_highlights.py \
    --format markdown \
    --output docs/logs/pai-73-final-benchmark-summary.md
  ```
