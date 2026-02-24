## 요약
- benchmark 전략 선택 경로를 단일화하고, triad(정/반/합) 비교 게이트를 강화했습니다.
- 재귀 이미지 스캔 가드/동기화 케이스를 테스트로 보강했습니다.
- develop 반영 전 품질/회귀/벤치 동기화까지 한 번에 검증하는 guardian pre-merge gate 스크립트를 추가했습니다.

## 변경 범위 (develop 대비 3 commits)
1. `fe67913` fix(benchmark): unify strategy resolution and harden triad comparison
   - `scripts/benchmark_strategies.py`
   - `src/img2dwg/pipeline/benchmark.py`
   - `src/img2dwg/pipeline/schema.py`
   - `tests/test_benchmark_report.py`
2. `6b02d0e` test: cover benchmark sync behavior and recursive scan guards
   - `scripts/benchmark_strategies.py`
   - `src/img2dwg/pipeline/benchmark.py`
   - `tests/test_benchmark_report.py`
   - `tests/test_benchmark_strategies_script.py`
3. `52d257f` chore(ops): add guardian premerge gate script
   - `scripts/guardian_premerge_gate.sh`

## 핵심 포인트
- triad cad_loadable 게이트를 summary/results 양쪽 기준으로 일관 검증 가능
- benchmark run metadata(`run.git_ref`)와 현재 HEAD 동기화 검증 루틴 추가
- 재귀 스캔 시 symlink/중복/최대 이미지 수 제한 가드 강화
- pre-merge 직전 실행용 통합 체크(G1~G5) 자동화

## 로컬 검증
```bash
# 권장: pre-merge 단일 게이트
BENCH_IMAGES=/tmp/img2dwg-bench-images \
  bash scripts/guardian_premerge_gate.sh

# 필요 시 개별 확인
uv run pytest -q tests/test_benchmark_report.py tests/test_benchmark_strategies_script.py
uv run ruff check scripts/benchmark_strategies.py src/img2dwg/pipeline/benchmark.py tests/test_benchmark_report.py tests/test_benchmark_strategies_script.py
uv run mypy scripts/benchmark_strategies.py src/img2dwg/pipeline/benchmark.py src/img2dwg/pipeline/schema.py src/img2dwg/strategies
```

## 벤치 결과(샘플 run)
- 입력 요약 파일: `output/benchmark/benchmark_summary.json`
- 입력 상세 파일: `output/benchmark/benchmark_results.json`
- winner: `hybrid_mvp` (composite `0.7205`)
- triad gate: `passed=true`
- (주의) PR 최종 머지 직전에는 반드시 HEAD 기준으로 재실행한 산출물로 갱신 필요

## 리스크/확인 필요
- guardian gate는 `BENCH_IMAGES` 경로가 필요합니다(기본: `/tmp/img2dwg-bench-images`).
- 결과 JSON의 `run.git_ref`가 PR HEAD와 불일치하면 gate 실패하도록 의도되어 있습니다.

## 머지 후
- develop fast-forward sync 및 benchmark 요약 리포트 갱신
- 최종 보고 시 `scripts/extract_benchmark_highlights.py` 출력 첨부
