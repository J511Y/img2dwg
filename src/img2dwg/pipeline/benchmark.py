from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from img2dwg.strategies import ConversionInput, StrategyRegistry


def run_benchmark(
    image_paths: list[Path],
    registry: StrategyRegistry,
    output_dir: Path,
    strategy_names: list[str] | None = None,
) -> dict[str, list[dict]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    target_names = strategy_names or registry.list_names()
    results: dict[str, list[dict]] = {name: [] for name in target_names}

    for image_path in image_paths:
        conv_input = ConversionInput(image_path=image_path)
        for name in target_names:
            strategy = registry.get(name)
            out = strategy.timed_run(conv_input, output_dir / name)
            results[name].append(asdict(out))

    (output_dir / "benchmark_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results
