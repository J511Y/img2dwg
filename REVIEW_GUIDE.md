# REVIEW_GUIDE.md

img2dwg 리뷰/확인용 빠른 가이드 (현재 시점)

## 0) 지금 상태
- 최신 반영 브랜치: `develop`
- 최근 머지: PR #3 (`feature/PAI-73-coderabbit-pass2`)
- 핵심 목표: 정/반/합 아이디어 구현 + 벤치마크/요약 파이프라인 확인

---

## 1) 네가 지금 해야 할 것 (요약)
1. PR 변경 내용 빠르게 훑기
2. 정/반/합 구현 코드 확인
3. 최소 검증 명령 실행
4. 벤치마크 결과/요약 파일 확인

---

## 2) 시작 커맨드
```bash
cd /Users/jhyou/.openclaw/workspace/img2dwg
git checkout develop
git pull --ff-only origin develop
```

---

## 3) PR/변경 내역 확인
- 머지된 PR: <https://github.com/J511Y/img2dwg/pull/3>
- 핵심 변경 파일:
  - `src/img2dwg/strategies/two_stage.py`
  - `src/img2dwg/strategies/consensus_qa.py`
  - `src/img2dwg/strategies/hybrid_mvp.py`
  - `src/img2dwg/strategies/prototype_engine.py`
  - `src/img2dwg/pipeline/benchmark.py`
  - `src/img2dwg/pipeline/schema.py`
  - `scripts/benchmark_strategies.py`
  - `scripts/guardian_premerge_gate.sh`
  - `tests/test_strategy_prototypes.py`
  - `tests/test_benchmark_report.py`
  - `tests/test_strategy_registry.py`

---

## 4) 정/반/합 구현부 체크 포인트

### 정 (Thesis)
- 파일: `src/img2dwg/strategies/two_stage.py`
- 확인 포인트:
  - 전략 실행 시 DXF 생성되는지
  - metrics/notes가 `ConversionOutput` 규약대로 채워지는지

### 반 (Antithesis)
- 파일: `src/img2dwg/strategies/consensus_qa.py`
- 확인 포인트:
  - consensus score/votes 기반 차단 로직
  - 임계치 미달 시 실패 처리(dxf 없음) 동작

### 합 (Synthesis)
- 파일: `src/img2dwg/strategies/hybrid_mvp.py`
- 확인 포인트:
  - thesis/antithesis 융합 가중치 로직
  - 합 전략 결과가 벤치마크 랭킹에 반영되는지

### 공통 엔진
- 파일: `src/img2dwg/strategies/prototype_engine.py`
- 확인 포인트:
  - 신호 추출/벡터 플랜/DXF export/메트릭 추정 유틸 일관성

---

## 5) 최소 검증 (복붙 실행)

```bash
uv run pytest -q tests/test_strategy_prototypes.py tests/test_strategy_registry.py tests/test_benchmark_report.py
uv run ruff check src/img2dwg/strategies src/img2dwg/pipeline scripts/benchmark_strategies.py tests/test_strategy_prototypes.py tests/test_strategy_registry.py tests/test_benchmark_report.py
uv run mypy src/img2dwg/strategies src/img2dwg/pipeline
```

기대 결과:
- pytest: 전부 pass
- ruff: all checks passed
- mypy: no issues found

---

## 6) 벤치마크/요약 확인 루트

### 벤치마크 실행
(하위 폴더 포함하려면 `--recursive`)
```bash
PYTHONPATH=src uv run python scripts/benchmark_strategies.py \
  --images /Users/jhyou/.openclaw/workspace/img2dwg-images/images \
  --recursive \
  --output output/benchmark/review \
  --dataset-id review-run \
  --git-ref develop
```

### 산출물 확인
- `output/benchmark/review/benchmark_results.json`
- `output/benchmark/review/benchmark_summary.json` (생성 경로에 따라)
- 최종 요약 문서:
  - `docs/logs/pai-73-final-benchmark-summary.md`

확인 포인트:
- `run.git_ref`가 현재 리뷰 기준 커밋/브랜치와 맞는지
- triad 비교 필드(`comparisons.thesis_antithesis_synthesis`)가 정상 채워졌는지
- ranking에서 `hybrid_mvp` 우세 여부(샘플셋 기준)

---

## 7) 머지 가드 재검증(선택)
```bash
BENCH_IMAGES=/tmp/img2dwg-bench-images \
BENCH_OUTPUT=output/benchmark/premerge \
BENCH_DATASET_ID=guardian-premerge \
bash scripts/guardian_premerge_gate.sh
```

기대 결과:
- `DECISION: PASS`
- G1~G5 PASS

---

## 8) 리뷰 코멘트 남길 때 권장 포맷
```text
[Review]
- Scope:
- Verified commands:
- Findings (must-fix):
- Findings (nice-to-have):
- Verdict: APPROVE / REQUEST_CHANGES
```

---

필요하면 이 가이드 기준으로 내가 체크리스트 방식(체크박스 포함)으로도 바꿔줄게.
