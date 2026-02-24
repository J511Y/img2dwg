from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

FIELD_PATTERN = re.compile(r"`([^`]+)`")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify docs/logs/pai-73-final-benchmark-summary.md is in sync with "
            "output/benchmark/{benchmark_summary.json,benchmark_results.json} "
            "for git_ref and triad Δmedian_elapsed_ms fields"
        )
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("output/benchmark/benchmark_summary.json"),
        help="path to benchmark_summary.json",
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("output/benchmark/benchmark_results.json"),
        help="path to benchmark_results.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("docs/logs/pai-73-final-benchmark-summary.md"),
        help="path to generated markdown summary",
    )
    return parser.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"json root must be object: {path}")
    return loaded


def _extract_backtick_value(line: str) -> str:
    matched = FIELD_PATTERN.search(line)
    if matched is None:
        raise ValueError(f"expected backtick-delimited value in line: {line}")
    return matched.group(1)


def _parse_markdown(path: Path) -> dict[str, str]:
    summary_git_ref: str | None = None
    results_git_ref: str | None = None
    thesis_delta_ms: str | None = None
    antithesis_delta_ms: str | None = None
    current_block: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip("\n")

        if line.startswith("- summary.git_ref:"):
            summary_git_ref = _extract_backtick_value(line)
            continue
        if line.startswith("- results.git_ref:"):
            results_git_ref = _extract_backtick_value(line)
            continue

        if line.startswith("- vs thesis("):
            current_block = "thesis"
            continue
        if line.startswith("- vs antithesis("):
            current_block = "antithesis"
            continue

        if "Δmedian_elapsed_ms" in line and current_block is not None:
            value = _extract_backtick_value(line)
            if current_block == "thesis":
                thesis_delta_ms = value
            elif current_block == "antithesis":
                antithesis_delta_ms = value

    extracted = {
        "summary_git_ref": summary_git_ref,
        "results_git_ref": results_git_ref,
        "triad_delta_thesis_ms": thesis_delta_ms,
        "triad_delta_antithesis_ms": antithesis_delta_ms,
    }
    missing = [k for k, v in extracted.items() if v is None]
    if missing:
        raise ValueError(
            f"failed to parse required markdown fields from {path}: {', '.join(missing)}"
        )

    return {k: str(v) for k, v in extracted.items()}


def _fmt_delta(value: Any) -> str:
    return f"{float(value):.2f}"


def main() -> int:
    args = parse_args()

    summary = _read_json(args.summary)
    results = _read_json(args.results)
    actual = _parse_markdown(args.markdown)

    triad = (
        results.get("comparisons", {})
        .get("thesis_antithesis_synthesis", {})
        .get("deltas", {})
    )

    expected = {
        "summary_git_ref": str(summary.get("run", {}).get("git_ref")),
        "results_git_ref": str(results.get("run", {}).get("git_ref")),
        "triad_delta_thesis_ms": _fmt_delta(
            triad.get("synthesis_vs_thesis", {}).get("median_elapsed_ms")
        ),
        "triad_delta_antithesis_ms": _fmt_delta(
            triad.get("synthesis_vs_antithesis", {}).get("median_elapsed_ms")
        ),
    }

    failures = [
        key for key, expected_value in expected.items() if actual.get(key) != expected_value
    ]

    if failures:
        print("FAIL: markdown/json drift detected")
        for key in failures:
            print(f"- {key}: expected={expected[key]!r} actual={actual.get(key)!r}")
        return 1

    print("OK: pai-73 final benchmark summary is in sync")
    for key in ("summary_git_ref", "results_git_ref", "triad_delta_thesis_ms", "triad_delta_antithesis_ms"):
        print(f"- {key}={expected[key]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
