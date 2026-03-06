from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from img2dwg.pipeline.benchmark import run_benchmark  # type: ignore[import-untyped]
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy  # type: ignore[import-untyped]
from img2dwg.strategies.hybrid_mvp import HybridMVPStrategy  # type: ignore[import-untyped]
from img2dwg.strategies.registry import (  # type: ignore[import-untyped]
    FeatureFlags,
    StrategyRegistry,
)
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy  # type: ignore[import-untyped]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
DEFAULT_RECURSIVE_SCAN_LIMIT = 2_000
DEFAULT_METADATA_WARNING_SAMPLE_SIZE = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare conversion strategies on same samples")
    parser.add_argument(
        "--images", type=Path, required=True, help="directory containing input images"
    )
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
    parser.add_argument(
        "--metadata-manifest",
        type=Path,
        default=None,
        help="optional JSON map: {<image-key>: <metadata-object>} for per-image metadata",
    )
    parser.add_argument(
        "--strict-metadata-manifest",
        action="store_true",
        help="fail benchmark if metadata manifest has unmatched keys",
    )
    parser.add_argument(
        "--metadata-warning-sample-size",
        type=int,
        default=DEFAULT_METADATA_WARNING_SAMPLE_SIZE,
        help=(
            "max unmatched manifest keys shown in warning messages "
            f"(default: {DEFAULT_METADATA_WARNING_SAMPLE_SIZE})"
        ),
    )
    return parser.parse_args()


def _parse_csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def _safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def _canonicalize_manifest_key(key: str) -> str:
    normalized = key.strip().replace("\\", "/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


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


def load_metadata_manifest(manifest_path: Path) -> dict[str, dict[str, Any]]:
    if not manifest_path.exists() or not manifest_path.is_file():
        raise ValueError(f"metadata manifest path does not exist: {manifest_path}")

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"metadata manifest must be valid JSON: {manifest_path}") from exc

    if not isinstance(payload, Mapping):
        raise ValueError("metadata manifest root must be an object")

    metadata_by_image: dict[str, dict[str, Any]] = {}
    for raw_key, raw_value in payload.items():
        key = _canonicalize_manifest_key(str(raw_key))
        if not key:
            raise ValueError("metadata manifest key must not be empty")

        if not isinstance(raw_value, Mapping):
            raise ValueError(f"metadata manifest value must be an object for key: {raw_key}")

        metadata_by_image[key] = {str(k): v for k, v in raw_value.items()}

    return metadata_by_image


def build_metadata_key_candidates(
    image_paths: list[Path],
    images_root: Path,
) -> dict[Path, list[tuple[str, str]]]:
    root_resolved = _safe_resolve(images_root)
    by_image: dict[Path, list[tuple[str, str]]] = {}

    for image_path in image_paths:
        resolved_image = _safe_resolve(image_path)
        candidates: list[tuple[str, str]] = [
            ("absolute", _canonicalize_manifest_key(resolved_image.as_posix()))
        ]

        try:
            root_relative = resolved_image.relative_to(root_resolved).as_posix()
        except ValueError:
            root_relative = ""
        if root_relative:
            candidates.append(("root_relative", _canonicalize_manifest_key(root_relative)))

        as_given = _canonicalize_manifest_key(image_path.as_posix())
        resolved_key = _canonicalize_manifest_key(resolved_image.as_posix())
        if as_given and as_given != resolved_key:
            candidates.append(("relative", as_given))

        if image_path.name:
            candidates.append(("name", image_path.name))
        if image_path.stem and image_path.stem != image_path.name:
            candidates.append(("stem", image_path.stem))

        by_image[image_path] = candidates

    return by_image


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

    metadata_by_image: dict[str, dict[str, Any]] | None = None
    metadata_key_candidates_by_image: dict[Path, list[tuple[str, str]]] | None = None
    if args.metadata_manifest is not None:
        metadata_by_image = load_metadata_manifest(args.metadata_manifest)
        metadata_key_candidates_by_image = build_metadata_key_candidates(image_paths, args.images)

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
        metadata_by_image=metadata_by_image,
        metadata_key_candidates_by_image=metadata_key_candidates_by_image,
        strict_metadata_manifest=args.strict_metadata_manifest,
        metadata_warning_sample_size=args.metadata_warning_sample_size,
    )
    print(f"done: benchmark results -> {args.output / 'benchmark_results.json'}")


if __name__ == "__main__":
    main()
