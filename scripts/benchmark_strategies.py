from __future__ import annotations

import argparse
from pathlib import Path

from img2dwg.pipeline.benchmark import run_benchmark
from img2dwg.strategies.registry import StrategyRegistry
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy
from img2dwg.strategies.hybrid_mvp import HybridMVPStrategy
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare conversion strategies on same samples")
    parser.add_argument("--images", type=Path, required=True, help="directory containing input images")
    parser.add_argument("--output", type=Path, default=Path("output/benchmark"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    image_paths = sorted([p for p in args.images.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])

    registry = StrategyRegistry()
    registry.register(HybridMVPStrategy())
    registry.register(TwoStageBaselineStrategy())
    registry.register(ConsensusQAStrategy())

    run_benchmark(image_paths=image_paths, registry=registry, output_dir=args.output)
    print(f"done: benchmark results -> {args.output / 'benchmark_results.json'}")


if __name__ == "__main__":
    main()
