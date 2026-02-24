#!/usr/bin/env bash
# img2dwg guardian pre-merge gate (develop 반영 전)
set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BENCH_IMAGES="${BENCH_IMAGES:-/tmp/img2dwg-bench-images}"
BENCH_OUTPUT="${BENCH_OUTPUT:-output/benchmark}"
BENCH_DATASET_ID="${BENCH_DATASET_ID:-guardian-premerge}"

FAILURES=()

print_header() {
  printf '\n[%s] %s\n' "$1" "$2"
}

run_check() {
  local id="$1"
  local title="$2"
  local fn="$3"

  print_header "$id" "$title"
  if "$fn"; then
    echo "PASS"
  else
    echo "FAIL"
    FAILURES+=("$id:$title")
  fi
}

check_worktree_clean() {
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "working tree is dirty"
    git status --short
    return 1
  fi
  return 0
}

check_sync_with_develop() {
  git fetch origin develop --quiet || return 1

  local ahead behind
  read -r ahead behind < <(git rev-list --left-right --count HEAD...origin/develop)

  echo "ahead_of_origin_develop=$ahead"
  echo "behind_origin_develop=$behind"

  if [[ "$behind" -gt 0 ]]; then
    echo "branch is behind origin/develop; rebase or merge develop first"
    return 1
  fi

  return 0
}

check_scope_gate() {
  local -a scope_tests=()
  for t in \
    tests/test_benchmark_report.py \
    tests/test_strategy_registry.py \
    tests/test_strategy_prototypes.py \
    tests/test_benchmark_strategies_script.py; do
    [[ -f "$t" ]] && scope_tests+=("$t")
  done

  if [[ "${#scope_tests[@]}" -eq 0 ]]; then
    echo "no scope tests found"
    return 1
  fi

  uv run pytest -q "${scope_tests[@]}" || return 1

  local -a ruff_targets=()
  for p in \
    scripts/benchmark_strategies.py \
    src/img2dwg/pipeline/benchmark.py \
    tests/test_benchmark_report.py \
    tests/test_strategy_registry.py \
    tests/test_strategy_prototypes.py \
    tests/test_benchmark_strategies_script.py; do
    [[ -f "$p" ]] && ruff_targets+=("$p")
  done

  uv run ruff check "${ruff_targets[@]}" || return 1

  local -a mypy_targets=()
  for p in \
    scripts/benchmark_strategies.py \
    src/img2dwg/pipeline/benchmark.py \
    src/img2dwg/pipeline/schema.py \
    src/img2dwg/strategies; do
    [[ -e "$p" ]] && mypy_targets+=("$p")
  done

  uv run mypy "${mypy_targets[@]}" || return 1

  return 0
}

check_full_regression() {
  uv run pytest -q
}

check_benchmark_git_ref_sync() {
  if [[ ! -d "$BENCH_IMAGES" ]]; then
    echo "benchmark images dir missing: $BENCH_IMAGES"
    echo "set BENCH_IMAGES=/path/to/images"
    return 1
  fi

  local head_ref
  head_ref="$(git rev-parse --short HEAD)"

  uv run python scripts/benchmark_strategies.py \
    --images "$BENCH_IMAGES" \
    --recursive \
    --dataset-id "$BENCH_DATASET_ID" \
    --git-ref "$head_ref" \
    --output "$BENCH_OUTPUT" || return 1

  GUARDIAN_BENCH_OUTPUT="$BENCH_OUTPUT" uv run python - <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path

output_dir = Path(os.environ.get("GUARDIAN_BENCH_OUTPUT", "output/benchmark"))
results = output_dir / "benchmark_results.json"
summary = output_dir / "benchmark_summary.json"

if not results.exists() or not summary.exists():
    print("required benchmark outputs missing")
    sys.exit(1)

results_json = json.loads(results.read_text(encoding="utf-8"))
summary_json = json.loads(summary.read_text(encoding="utf-8"))
head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()

checks = {
    "results_git_ref_eq_head": results_json.get("run", {}).get("git_ref") == head,
    "summary_git_ref_eq_head": summary_json.get("run", {}).get("git_ref") == head,
    "summary_git_ref_eq_results": (
        summary_json.get("run", {}).get("git_ref")
        == results_json.get("run", {}).get("git_ref")
    ),
    "triad_available": summary_json.get("triad_gate", {}).get("available") is True,
    "triad_passed": summary_json.get("triad_gate", {}).get("passed") is True,
}

failed = [name for name, passed in checks.items() if not passed]
print("benchmark_sync_checks=", checks)
if failed:
    print("failed_checks=", failed)
    sys.exit(1)
PY
}

run_check "G1" "Working tree clean" check_worktree_clean
run_check "G2" "Sync with origin/develop" check_sync_with_develop
run_check "G3" "Scope quality gate (pytest+ruff+mypy)" check_scope_gate
run_check "G4" "Full regression gate (pytest -q)" check_full_regression
run_check "G5" "Benchmark run.git_ref sync + triad gate" check_benchmark_git_ref_sync

printf '\n==== Guardian Gate Result ====\n'
if [[ "${#FAILURES[@]}" -eq 0 ]]; then
  echo "DECISION: PASS"
  exit 0
fi

echo "DECISION: FAIL"
printf 'failed_gates(%d):\n' "${#FAILURES[@]}"
printf ' - %s\n' "${FAILURES[@]}"
exit 1
