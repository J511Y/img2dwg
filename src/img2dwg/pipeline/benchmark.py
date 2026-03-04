from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from img2dwg.pipeline.schema import build_report
from img2dwg.strategies import ConversionInput, ConversionOutput, FeatureFlags, StrategyRegistry


def _to_legacy_dict(out: ConversionOutput) -> dict[str, Any]:
    return {
        "strategy_name": out.strategy_name,
        "dxf_path": str(out.dxf_path) if out.dxf_path else None,
        "success": out.success,
        "elapsed_ms": out.elapsed_ms,
        "metrics": out.metrics,
        "notes": out.notes,
    }


def _resolve_strategy_names(
    registry: StrategyRegistry,
    strategy_names: list[str] | None,
    feature_flags: FeatureFlags,
) -> list[str]:
    requested_names = strategy_names or []
    selected = registry.resolve_requested_names(requested_names, feature_flags)
    if selected:
        return selected

    # Keep benchmark runnable even when the enabled set is empty by falling back
    # to one safe strategy (matches CLI behavior).
    safe = registry.get_safe_default()
    return [safe.name]


def _build_final_summary(report: dict[str, Any]) -> dict[str, Any]:
    ranking_raw = report.get("ranking")
    ranking = ranking_raw if isinstance(ranking_raw, list) else []

    ranking_by_name: dict[str, dict[str, Any]] = {}
    for entry in ranking:
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("strategy_name", ""))
        if not name:
            continue
        ranking_by_name[name] = {
            "rank": entry.get("rank"),
            "composite_score": entry.get("composite_score"),
        }

    winner: dict[str, Any] | None = None
    if ranking and isinstance(ranking[0], Mapping):
        top = ranking[0]
        winner_name = str(top.get("strategy_name", ""))
        if winner_name:
            winner = {
                "strategy_name": winner_name,
                "rank": top.get("rank"),
                "composite_score": top.get("composite_score"),
            }

    strategies_raw = report.get("strategies")
    strategies = strategies_raw if isinstance(strategies_raw, list) else []
    rows: list[dict[str, Any]] = []
    for strategy in strategies:
        if not isinstance(strategy, Mapping):
            continue
        strategy_name = str(strategy.get("strategy_name", ""))
        if not strategy_name:
            continue

        summary_raw = strategy.get("summary")
        summary = summary_raw if isinstance(summary_raw, Mapping) else {}
        ranking_info = ranking_by_name.get(strategy_name, {})

        rows.append(
            {
                "strategy_name": strategy_name,
                "rank": ranking_info.get("rank"),
                "composite_score": ranking_info.get("composite_score"),
                "success_rate": summary.get("success_rate", 0.0),
                "cad_loadable_count": summary.get("cad_loadable_count", 0),
                "cad_loadable_rate": summary.get("cad_loadable_rate", 0.0),
                "mean_iou": summary.get("mean_iou", 0.0),
                "mean_topology_f1": summary.get("mean_topology_f1", 0.0),
                "median_elapsed_ms": summary.get("median_elapsed_ms", 0.0),
                "p95_elapsed_ms": summary.get("p95_elapsed_ms", 0.0),
            }
        )

    def _rank_key(item: dict[str, Any]) -> tuple[int, str]:
        rank = item.get("rank")
        if isinstance(rank, int):
            return (rank, item["strategy_name"])
        return (10**9, item["strategy_name"])

    rows.sort(key=_rank_key)

    comparisons_raw = report.get("comparisons")
    comparisons = comparisons_raw if isinstance(comparisons_raw, Mapping) else {}
    triad_raw = comparisons.get("thesis_antithesis_synthesis")
    triad = triad_raw if isinstance(triad_raw, Mapping) else {}

    gate_raw = triad.get("cad_loadable_gate")
    gate = gate_raw if isinstance(gate_raw, Mapping) else {}
    available = bool(triad.get("available", False))

    missing_raw = triad.get("missing")
    missing = [str(name) for name in missing_raw] if isinstance(missing_raw, list) else []

    run_raw = report.get("run")
    run = run_raw if isinstance(run_raw, Mapping) else {}

    return {
        "summary_schema_version": 1,
        "source_schema_version": report.get("schema_version"),
        "run": {
            "run_id": run.get("run_id"),
            "dataset_id": run.get("dataset_id"),
            "git_ref": run.get("git_ref"),
            "generated_at": run.get("generated_at"),
        },
        "winner": winner,
        "triad_gate": {
            "available": available,
            "passed": gate.get("passed") if available else None,
            "missing": missing,
        },
        "strategies": rows,
    }


def _slugify_image_stem(stem: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", stem.strip())
    slug = slug.strip("-._")
    if not slug:
        return "image"
    return slug[:40]


def _build_case_output_dir(base_dir: Path, image_path: Path, case_index: int) -> Path:
    try:
        image_token = str(image_path.resolve())
    except OSError:
        image_token = str(image_path.absolute())
    digest = hashlib.sha1(image_token.encode("utf-8")).hexdigest()[:10]
    slug = _slugify_image_stem(image_path.stem)
    return base_dir / f"case_{case_index:04d}_{slug}_{digest}"


def run_benchmark(
    image_paths: list[Path],
    registry: StrategyRegistry,
    output_dir: Path,
    strategy_names: list[str] | None = None,
    feature_flags: FeatureFlags | None = None,
    dataset_id: str = "default",
    git_ref: str = "local",
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    flags = feature_flags or FeatureFlags()
    target_names = _resolve_strategy_names(registry, strategy_names, flags)

    legacy_results: dict[str, list[dict[str, Any]]] = {name: [] for name in target_names}
    outputs_map: dict[str, list[ConversionOutput]] = {name: [] for name in target_names}

    for case_index, image_path in enumerate(image_paths, start=1):
        conv_input = ConversionInput(image_path=image_path)
        for name in target_names:
            strategy = registry.get(name)
            strategy_output_root = output_dir / name
            case_output_dir = _build_case_output_dir(strategy_output_root, image_path, case_index)
            out = strategy.timed_run(conv_input, case_output_dir)
            outputs_map[name].append(out)
            legacy_results[name].append(_to_legacy_dict(out))

    report = build_report(
        strategy_outputs=outputs_map,
        image_paths=image_paths,
        dataset_id=dataset_id,
        git_ref=git_ref,
        legacy=legacy_results,
    )

    serialized = report.to_dict()
    (output_dir / "benchmark_results.json").write_text(
        json.dumps(serialized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = _build_final_summary(serialized)
    (output_dir / "benchmark_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return serialized
