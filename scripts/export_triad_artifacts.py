from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Export triad(정/반/합) pred/eval summary artifacts from benchmark results")
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("output/benchmark/benchmark_results.json"),
        help="path to benchmark_results.json",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("output/benchmark/benchmark_summary.json"),
        help="path to benchmark_summary.json",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("output/triad"),
        help="output root for triad artifacts",
    )
    parser.add_argument(
        "--dataset-manifest-ref",
        default=None,
        help="optional repo-relative dataset manifest path for benchmark_metadata",
    )
    parser.add_argument(
        "--require-triad",
        action="store_true",
        help="fail fast when thesis/antithesis/synthesis triad is incomplete",
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing input file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json root must be object: {path}")
    return payload


def _dump_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _to_rel(path: Path) -> str:
    return path.as_posix()


def _utc_iso_z(value: str | None = None) -> str:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("benchmark_metadata.generated_at must be parseable ISO-8601") from exc

    if parsed.tzinfo is None:
        raise ValueError("benchmark_metadata.generated_at must include timezone offset or Z")

    return parsed.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_repo_relative_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    if not normalized:
        return False
    if normalized.startswith("/"):
        return False
    if re.match(r"^[A-Za-z]:", normalized):
        return False

    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    return all(part != ".." for part in parts)


def _extract_benchmark_metadata(
    results: Mapping[str, Any],
    summary: Mapping[str, Any],
    dataset_manifest_override: str | None,
) -> dict[str, str]:
    run_raw = results.get("run", {})
    run = run_raw if isinstance(run_raw, Mapping) else {}

    summary_meta_raw = summary.get("benchmark_metadata", {})
    summary_meta = summary_meta_raw if isinstance(summary_meta_raw, Mapping) else {}
    results_meta_raw = results.get("benchmark_metadata", {})
    results_meta = results_meta_raw if isinstance(results_meta_raw, Mapping) else {}

    git_ref_raw = summary_meta.get("git_ref") or results_meta.get("git_ref") or run.get("git_ref")
    generated_at_raw = (
        summary_meta.get("generated_at")
        or results_meta.get("generated_at")
        or run.get("generated_at")
    )
    dataset_manifest_ref_raw = (
        dataset_manifest_override
        or summary_meta.get("dataset_manifest_ref")
        or results_meta.get("dataset_manifest_ref")
    )

    git_ref = str(git_ref_raw).strip() if git_ref_raw is not None else ""
    dataset_manifest_ref = (
        str(dataset_manifest_ref_raw).strip() if dataset_manifest_ref_raw is not None else ""
    )

    if not git_ref:
        raise ValueError("benchmark_metadata.git_ref is required")
    if SHA_RE.fullmatch(git_ref) is None:
        raise ValueError("benchmark_metadata.git_ref must match ^[0-9a-f]{40}$")

    if not dataset_manifest_ref:
        raise ValueError("benchmark_metadata.dataset_manifest_ref is required")
    if not _is_repo_relative_path(dataset_manifest_ref):
        raise ValueError("benchmark_metadata.dataset_manifest_ref must be a repo-relative path")

    generated_at = (
        _utc_iso_z(str(generated_at_raw)) if generated_at_raw is not None else _utc_iso_z()
    )

    return {
        "git_ref": git_ref,
        "generated_at": generated_at,
        "dataset_manifest_ref": dataset_manifest_ref,
    }


def _require_triad_or_raise(
    *,
    triad: Mapping[str, Any],
    axis_map: Mapping[str, str],
    by_name: Mapping[str, dict[str, Any]],
) -> None:
    available = bool(triad.get("available", False))
    missing_raw = triad.get("missing", [])
    missing = missing_raw if isinstance(missing_raw, list) else []
    unresolved_axes = [
        axis for axis, strategy_name in axis_map.items() if strategy_name not in by_name
    ]

    failures: list[str] = []
    if not available:
        failures.append("triad.available=false")
    if missing:
        failures.append(f"triad.missing={missing}")
    if unresolved_axes:
        failures.append(f"unresolved_axes={unresolved_axes}")

    if failures:
        raise ValueError(f"triad requirement check failed: {'; '.join(failures)}")


def main() -> None:
    args = parse_args()

    results = _load_json(args.results)
    summary = _load_json(args.summary)
    benchmark_metadata = _extract_benchmark_metadata(
        results=results,
        summary=summary,
        dataset_manifest_override=args.dataset_manifest_ref,
    )

    strategies_raw = results.get("strategies", [])
    if not isinstance(strategies_raw, list):
        raise ValueError("results.strategies must be list")

    by_name: dict[str, dict[str, Any]] = {}
    for item in strategies_raw:
        if not isinstance(item, dict):
            continue
        name = item.get("strategy_name")
        if isinstance(name, str) and name:
            by_name[name] = item

    comparisons_raw = results.get("comparisons", {})
    if not isinstance(comparisons_raw, Mapping):
        raise ValueError("results.comparisons must be object")

    triad_raw = comparisons_raw.get("thesis_antithesis_synthesis", {})
    if triad_raw is None:
        triad_raw = {}
    if not isinstance(triad_raw, Mapping):
        raise ValueError("results.comparisons.thesis_antithesis_synthesis must be object")
    triad = dict(triad_raw)

    thesis = triad.get("thesis")
    antithesis = triad.get("antithesis")
    synthesis = triad.get("synthesis")

    thesis_name: str = thesis if isinstance(thesis, str) else "two_stage_baseline"
    antithesis_name: str = antithesis if isinstance(antithesis, str) else "consensus_qa"
    synthesis_name: str = synthesis if isinstance(synthesis, str) else "hybrid_mvp"

    axis_map: dict[str, str] = {
        "jeong": thesis_name,
        "ban": antithesis_name,
        "hap": synthesis_name,
    }

    if args.require_triad:
        _require_triad_or_raise(triad=triad, axis_map=axis_map, by_name=by_name)

    run = results.get("run", {})
    if not isinstance(run, dict):
        run = {}

    triad_gate = summary.get("triad_gate", {})
    if not isinstance(triad_gate, dict):
        triad_gate = {}

    pred_dir = args.out_dir / "pred"
    eval_dir = args.out_dir / "eval"

    pred_paths: dict[str, str] = {}
    eval_paths: dict[str, str] = {}

    for axis, strategy_name in axis_map.items():
        strategy = by_name.get(strategy_name, {})

        cases_raw = strategy.get("cases", []) if isinstance(strategy, dict) else []
        if not isinstance(cases_raw, list):
            raise ValueError(f"results.strategies[{strategy_name}].cases must be list")

        serialized_cases: list[dict[str, Any]] = []
        for idx, case in enumerate(cases_raw):
            if not isinstance(case, Mapping):
                raise ValueError(
                    f"results.strategies[{strategy_name}].cases[{idx}] must be object"
                )
            serialized_cases.append(
                {
                    "case_id": case.get("case_id"),
                    "image_path": case.get("image_path"),
                    "dxf_path": case.get("dxf_path"),
                    "success": case.get("success"),
                    "cad_loadable": case.get("cad_loadable"),
                    "elapsed_ms": case.get("elapsed_ms"),
                }
            )

        pred_payload: dict[str, Any] = {
            "schema_version": 1,
            "axis": axis,
            "role": {
                "jeong": "thesis",
                "ban": "antithesis",
                "hap": "synthesis",
            }[axis],
            "strategy_name": strategy_name,
            "run": run,
            "case_count": len(serialized_cases),
            "cases": serialized_cases,
        }
        pred_payload["benchmark_metadata"] = benchmark_metadata

        eval_payload: dict[str, Any] = {
            "schema_version": 1,
            "axis": axis,
            "role": pred_payload["role"],
            "strategy_name": strategy_name,
            "run": run,
            "summary": strategy.get("summary", {}) if isinstance(strategy, dict) else {},
        }
        eval_payload["benchmark_metadata"] = benchmark_metadata

        pred_path = pred_dir / f"pred_summary.{axis}.json"
        eval_path = eval_dir / f"eval_summary.{axis}.json"
        _dump_json(pred_path, pred_payload)
        _dump_json(eval_path, eval_payload)

        pred_paths[axis] = _to_rel(pred_path)
        eval_paths[axis] = _to_rel(eval_path)

    triad_eval_payload: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": _utc_iso_z(),
        "run": run,
        "triad": {
            "thesis": thesis_name,
            "antithesis": antithesis_name,
            "synthesis": synthesis_name,
            "available": bool(triad.get("available", False)),
            "missing": triad.get("missing", []),
            "gate": {
                "summary": triad_gate,
                "results": triad.get("cad_loadable_gate", {}),
            },
            "deltas": triad.get("deltas", {}),
        },
        "eval_summaries": eval_paths,
    }
    triad_eval_payload["benchmark_metadata"] = benchmark_metadata

    triad_eval_path = eval_dir / "eval_summary.triad.json"
    _dump_json(triad_eval_path, triad_eval_payload)

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "source": {
            "results": _to_rel(args.results),
            "summary": _to_rel(args.summary),
        },
        "pred": pred_paths,
        "eval": {
            **eval_paths,
            "triad": _to_rel(triad_eval_path),
        },
    }
    manifest["benchmark_metadata"] = benchmark_metadata

    manifest_path = args.out_dir / "triad_artifacts_manifest.json"
    _dump_json(manifest_path, manifest)

    print("written triad artifacts:")
    for axis in ("jeong", "ban", "hap"):
        print(f"- pred[{axis}]: {pred_paths[axis]}")
        print(f"- eval[{axis}]: {eval_paths[axis]}")
    print(f"- eval[triad]: {_to_rel(triad_eval_path)}")
    print(f"- manifest: {_to_rel(manifest_path)}")


if __name__ == "__main__":
    main()
