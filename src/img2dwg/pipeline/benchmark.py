from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from img2dwg.pipeline.schema import build_report
from img2dwg.strategies import ConversionInput, ConversionOutput, StrategyRegistry


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
) -> list[str]:
    if strategy_names is None:
        return registry.list_names()

    normalized: list[str] = []
    seen: set[str] = set()
    for name in strategy_names:
        cleaned = name.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    # Backward compatibility: empty/blank-only input behaves like default-all.
    if not normalized:
        return registry.list_names()

    known_names = set(registry.list_names())
    unknown = [name for name in normalized if name not in known_names]
    if unknown:
        unknown_display = ", ".join(unknown)
        raise ValueError(f"Unknown strategies requested: {unknown_display}")

    return normalized


def run_benchmark(
    image_paths: list[Path],
    registry: StrategyRegistry,
    output_dir: Path,
    strategy_names: list[str] | None = None,
    dataset_id: str = "default",
    git_ref: str = "local",
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    target_names = _resolve_strategy_names(registry, strategy_names)

    legacy_results: dict[str, list[dict[str, Any]]] = {name: [] for name in target_names}
    outputs_map: dict[str, list[ConversionOutput]] = {name: [] for name in target_names}

    for image_path in image_paths:
        conv_input = ConversionInput(image_path=image_path)
        for name in target_names:
            strategy = registry.get(name)
            out = strategy.timed_run(conv_input, output_dir / name)
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
    return serialized
