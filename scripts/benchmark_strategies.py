from __future__ import annotations

import argparse
from pathlib import Path

from img2dwg.pipeline.benchmark import run_benchmark
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy
from img2dwg.strategies.hybrid_mvp import HybridMVPStrategy
from img2dwg.strategies.registry import FeatureFlags, StrategyRegistry
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare conversion strategies on same samples")
    parser.add_argument("--images", type=Path, required=True, help="directory containing input images")
    parser.add_argument("--output", type=Path, default=Path("output/benchmark"))
    parser.add_argument("--dataset-id", type=str, default="default")
    parser.add_argument("--git-ref", type=str, default="local")
    parser.add_argument(
        "--strategies",
        type=str,
        default="",
        help="comma-separated strategy names; empty means auto-enabled set",
    )
    parser.add_argument("--recursive", action="store_true", help="recursively scan image files")
    parser.add_argument("--enable-high-risk", action="store_true")
    parser.add_argument(
        "--high-risk-allowlist",
        type=str,
        default="",
        help="comma-separated allowlist for high-risk strategies",
    )
    return parser.parse_args()


def _parse_csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def main() -> None:
    args = parse_args()
    iterator = args.images.rglob("*") if args.recursive else args.images.iterdir()
    image_paths = sorted([p for p in iterator if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
    if not image_paths:
        raise ValueError(f"no image files found in: {args.images}")

    registry = StrategyRegistry()
    registry.register(HybridMVPStrategy())
    registry.register(TwoStageBaselineStrategy())
    registry.register(ConsensusQAStrategy())

    flags = FeatureFlags(
        enable_high_risk=args.enable_high_risk,
        high_risk_allowlist=_parse_csv(args.high_risk_allowlist),
    )
    run_benchmark(
        image_paths=image_paths,
        registry=registry,
        output_dir=args.output,
        strategy_names=_parse_csv(args.strategies),
        feature_flags=flags,
        dataset_id=args.dataset_id,
        git_ref=args.git_ref,
    )
    print(f"done: benchmark results -> {args.output / 'benchmark_results.json'}")


if __name__ == "__main__":
    main()
