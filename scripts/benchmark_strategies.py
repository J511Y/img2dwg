from __future__ import annotations

import argparse
import sys
from pathlib import Path

from img2dwg.pipeline.benchmark import run_benchmark
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy
from img2dwg.strategies.hybrid_mvp import HybridMVPStrategy
from img2dwg.strategies.registry import FeatureFlags, StrategyRegistry
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
DEFAULT_RECURSIVE_SCAN_LIMIT = 2_000


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
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="follow symlinked files/directories during --recursive scan (off by default)",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=DEFAULT_RECURSIVE_SCAN_LIMIT,
        help=(
            "max image count allowed during --recursive scan before aborting "
            f"(default: {DEFAULT_RECURSIVE_SCAN_LIMIT})"
        ),
    )
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


def _safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def _collect_recursive_image_paths(
    root: Path,
    *,
    follow_symlinks: bool,
    max_images: int,
) -> tuple[list[Path], int]:
    if max_images < 1:
        raise ValueError("--max-images must be >= 1")

    stack = [root]
    visited_dirs: set[Path] = set()
    seen_images: set[Path] = set()
    image_paths: list[Path] = []
    skipped_symlink_paths = 0

    while stack:
        directory = stack.pop()
        resolved_dir = _safe_resolve(directory)
        if resolved_dir in visited_dirs:
            continue
        visited_dirs.add(resolved_dir)

        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            print(f"warning: failed to read directory {directory}: {exc}", file=sys.stderr)
            continue

        for entry in entries:
            if entry.is_symlink() and not follow_symlinks:
                skipped_symlink_paths += 1
                continue

            try:
                if entry.is_dir():
                    stack.append(entry)
                    continue

                if not entry.is_file() or entry.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
            except OSError as exc:
                print(f"warning: failed to inspect path {entry}: {exc}", file=sys.stderr)
                continue

            resolved_image = _safe_resolve(entry)
            if resolved_image in seen_images:
                continue

            seen_images.add(resolved_image)
            image_paths.append(entry)

            if len(image_paths) > max_images:
                raise ValueError(
                    "recursive scan limit exceeded: "
                    f"found more than {max_images} images under {root}. "
                    "Use --max-images to raise the limit or narrow --images."
                )

    return sorted(image_paths), skipped_symlink_paths


def collect_image_paths(
    root: Path,
    *,
    recursive: bool,
    follow_symlinks: bool,
    max_images: int,
) -> list[Path]:
    if not root.exists():
        raise ValueError(f"images path does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"images path must be a directory: {root}")

    if recursive:
        image_paths, skipped_symlink_paths = _collect_recursive_image_paths(
            root,
            follow_symlinks=follow_symlinks,
            max_images=max_images,
        )
        if skipped_symlink_paths:
            print(
                "warning: skipped "
                f"{skipped_symlink_paths} symlink path(s) during recursive scan. "
                "Use --follow-symlinks to include them.",
                file=sys.stderr,
            )
        return image_paths

    return sorted(
        [p for p in root.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    )


def main() -> None:
    args = parse_args()
    image_paths = collect_image_paths(
        args.images,
        recursive=args.recursive,
        follow_symlinks=args.follow_symlinks,
        max_images=args.max_images,
    )
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
