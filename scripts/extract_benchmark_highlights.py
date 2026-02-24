from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract key numbers and paths from benchmark summary/results"
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
        "--format",
        choices=("markdown", "text", "json"),
        default="markdown",
        help="output format",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="optional output file path",
    )
    return parser.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"json root must be object: {path}")
    return cast(dict[str, Any], loaded)


def _find_strategy(summary: dict[str, Any], name: str) -> dict[str, Any] | None:
    for item in summary.get("strategies", []):
        if not isinstance(item, dict):
            continue
        if item.get("strategy_name") == name:
            return cast(dict[str, Any], item)
    return None


def _collect_dxf_dirs(results: dict[str, Any]) -> dict[str, str]:
    output: dict[str, str] = {}
    for strategy in results.get("strategies", []):
        strategy_name = str(strategy.get("strategy_name", ""))
        if not strategy_name:
            continue

        cases = strategy.get("cases", [])
        first_dxf = None
        for case in cases:
            dxf_path = case.get("dxf_path")
            if isinstance(dxf_path, str) and dxf_path:
                first_dxf = Path(dxf_path)
                break

        if first_dxf is None:
            continue

        output[strategy_name] = str(first_dxf.parent)
    return output


def build_payload(summary: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
    run_summary = summary.get("run", {})
    run_results = results.get("run", {})

    winner = summary.get("winner", {})
    winner_name = str(winner.get("strategy_name", ""))

    triad_gate = summary.get("triad_gate", {})
    triad_comparison = (
        results.get("comparisons", {}).get("thesis_antithesis_synthesis", {})
    )

    synthesis_vs_thesis = triad_comparison.get("deltas", {}).get("synthesis_vs_thesis", {})
    synthesis_vs_antithesis = triad_comparison.get("deltas", {}).get(
        "synthesis_vs_antithesis", {}
    )

    payload = {
        "run": {
            "summary_run_id": run_summary.get("run_id"),
            "summary_git_ref": run_summary.get("git_ref"),
            "summary_dataset_id": run_summary.get("dataset_id"),
            "results_git_ref": run_results.get("git_ref"),
            "results_dataset_id": run_results.get("dataset_id"),
        },
        "winner": {
            "strategy_name": winner_name,
            "rank": winner.get("rank"),
            "composite_score": winner.get("composite_score"),
            "summary": _find_strategy(summary, winner_name),
        },
        "triad_gate": {
            "available": triad_gate.get("available"),
            "passed": triad_gate.get("passed"),
            "missing": triad_gate.get("missing", []),
            "synthesis_vs_thesis": synthesis_vs_thesis,
            "synthesis_vs_antithesis": synthesis_vs_antithesis,
        },
        "ranking": summary.get("strategies", []),
        "paths": {
            "benchmark_summary_json": "output/benchmark/benchmark_summary.json",
            "benchmark_results_json": "output/benchmark/benchmark_results.json",
            "strategy_dxf_dirs": _collect_dxf_dirs(results),
        },
    }
    return payload


def _fmt_ratio(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return f"{numeric * 100:.2f}%"


def _fmt_num(value: Any, digits: int = 4) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return f"{numeric:.{digits}f}"


def render_markdown(payload: dict[str, Any], summary_path: Path, results_path: Path) -> str:
    run = payload["run"]
    winner = payload["winner"]
    triad = payload["triad_gate"]
    ranking = payload["ranking"]
    dxf_dirs = payload["paths"]["strategy_dxf_dirs"]

    lines: list[str] = []
    lines.append("# Benchmark Final Highlights")
    lines.append("")
    lines.append("## Source Files")
    lines.append(f"- summary: `{summary_path}`")
    lines.append(f"- results: `{results_path}`")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append(f"- dataset_id: `{run.get('summary_dataset_id')}`")
    lines.append(f"- summary.git_ref: `{run.get('summary_git_ref')}`")
    lines.append(f"- results.git_ref: `{run.get('results_git_ref')}`")
    lines.append("")
    lines.append("## Winner")
    lines.append(
        f"- `{winner.get('strategy_name')}` (rank={winner.get('rank')}, composite={_fmt_num(winner.get('composite_score'))})"
    )

    winner_summary = winner.get("summary") or {}
    lines.append(f"- success_rate: {_fmt_ratio(winner_summary.get('success_rate'))}")
    lines.append(f"- cad_loadable_rate: {_fmt_ratio(winner_summary.get('cad_loadable_rate'))}")
    lines.append(f"- mean_iou: {_fmt_num(winner_summary.get('mean_iou'))}")
    lines.append(f"- mean_topology_f1: {_fmt_num(winner_summary.get('mean_topology_f1'))}")
    lines.append(f"- median_elapsed_ms: {_fmt_num(winner_summary.get('median_elapsed_ms'), 2)}")
    lines.append("")
    lines.append("## Triad Gate")
    lines.append(f"- available: `{triad.get('available')}`")
    lines.append(f"- passed: `{triad.get('passed')}`")
    lines.append("")
    lines.append("### Synthesis Deltas")
    lines.append("- vs thesis(two_stage_baseline)")
    lines.append(
        f"  - Δmean_iou: `{_fmt_num((triad.get('synthesis_vs_thesis') or {}).get('mean_iou'))}`"
    )
    lines.append(
        f"  - Δmean_topology_f1: `{_fmt_num((triad.get('synthesis_vs_thesis') or {}).get('mean_topology_f1'))}`"
    )
    lines.append(
        f"  - Δmedian_elapsed_ms: `{_fmt_num((triad.get('synthesis_vs_thesis') or {}).get('median_elapsed_ms'), 2)}`"
    )
    lines.append("- vs antithesis(consensus_qa)")
    lines.append(
        f"  - Δmean_iou: `{_fmt_num((triad.get('synthesis_vs_antithesis') or {}).get('mean_iou'))}`"
    )
    lines.append(
        f"  - Δmean_topology_f1: `{_fmt_num((triad.get('synthesis_vs_antithesis') or {}).get('mean_topology_f1'))}`"
    )
    lines.append(
        f"  - Δmedian_elapsed_ms: `{_fmt_num((triad.get('synthesis_vs_antithesis') or {}).get('median_elapsed_ms'), 2)}`"
    )
    lines.append("")
    lines.append("## Ranking")
    lines.append("| strategy | rank | composite | success | cad_loadable | mean_iou | topo_f1 | p95_ms |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for row in ranking:
        lines.append(
            "| {strategy} | {rank} | {score} | {success} | {cad} | {iou} | {f1} | {p95} |".format(
                strategy=row.get("strategy_name", "n/a"),
                rank=row.get("rank", "n/a"),
                score=_fmt_num(row.get("composite_score")),
                success=_fmt_ratio(row.get("success_rate")),
                cad=_fmt_ratio(row.get("cad_loadable_rate")),
                iou=_fmt_num(row.get("mean_iou")),
                f1=_fmt_num(row.get("mean_topology_f1")),
                p95=_fmt_num(row.get("p95_elapsed_ms"), 2),
            )
        )

    lines.append("")
    lines.append("## Output DXF Paths")
    for strategy_name, dxf_dir in dxf_dirs.items():
        lines.append(f"- `{strategy_name}`: `{dxf_dir}`")

    return "\n".join(lines) + "\n"


def render_text(payload: dict[str, Any], summary_path: Path, results_path: Path) -> str:
    winner = payload["winner"]
    triad = payload["triad_gate"]
    run = payload["run"]

    lines: list[str] = []
    lines.append(f"summary={summary_path}")
    lines.append(f"results={results_path}")
    lines.append(f"dataset_id={run.get('summary_dataset_id')}")
    lines.append(
        f"git_ref(summary/results)={run.get('summary_git_ref')}/{run.get('results_git_ref')}"
    )
    lines.append(
        "winner={} rank={} composite={}".format(
            winner.get("strategy_name"),
            winner.get("rank"),
            _fmt_num(winner.get("composite_score")),
        )
    )
    lines.append(
        f"triad available={triad.get('available')} passed={triad.get('passed')}"
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    summary = _read_json(args.summary)
    results = _read_json(args.results)
    payload = build_payload(summary, results)

    if args.format == "json":
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    elif args.format == "text":
        rendered = render_text(payload, args.summary, args.results)
    else:
        rendered = render_markdown(payload, args.summary, args.results)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")

    print(rendered)


if __name__ == "__main__":
    main()
