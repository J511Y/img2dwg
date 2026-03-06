from __future__ import annotations

import json
import warnings
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from img2dwg.pipeline.schema import build_report  # type: ignore[import-untyped]
from img2dwg.strategies import (  # type: ignore[import-untyped]
    ConversionInput,
    ConversionOutput,
    FeatureFlags,
    StrategyRegistry,
)

MetadataCandidate = tuple[str, str]
DEFAULT_METADATA_WARNING_SAMPLE_SIZE = 5
METADATA_MATCH_MODES = ("absolute", "root_relative", "relative", "name", "stem")
FALLBACK_METADATA_MATCH_MODES = {"name", "stem"}


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
        return [str(name) for name in selected]

    # Keep benchmark runnable even when the enabled set is empty by falling back
    # to one safe strategy (matches CLI behavior).
    safe = registry.get_safe_default()
    return [safe.name]


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


def _normalize_metadata_manifest(
    metadata_by_image: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    if metadata_by_image is None:
        return {}

    normalized: dict[str, dict[str, Any]] = {}
    for raw_key, raw_metadata in metadata_by_image.items():
        if not isinstance(raw_metadata, Mapping):
            raise ValueError(f"metadata manifest value must be an object for key: {raw_key}")

        canonical_key = _canonicalize_manifest_key(raw_key)
        if not canonical_key:
            raise ValueError("metadata manifest key must not be empty")

        if canonical_key in normalized:
            raise ValueError(
                "metadata manifest key collision after canonicalization: "
                f"{raw_key!r} -> {canonical_key!r}"
            )

        normalized[canonical_key] = {str(k): v for k, v in raw_metadata.items()}

    return normalized


def _normalize_metadata_candidates(
    candidates: Sequence[MetadataCandidate],
) -> list[MetadataCandidate]:
    normalized: list[MetadataCandidate] = []
    seen_keys: set[str] = set()

    for kind, raw_key in candidates:
        if not kind:
            continue
        canonical_key = _canonicalize_manifest_key(raw_key)
        if not canonical_key or canonical_key in seen_keys:
            continue

        seen_keys.add(canonical_key)
        normalized.append((kind, canonical_key))

    return normalized


def _build_default_metadata_candidates(image_path: Path) -> list[MetadataCandidate]:
    resolved = _safe_resolve(image_path)
    resolved_key = _canonicalize_manifest_key(resolved.as_posix())
    as_given_key = _canonicalize_manifest_key(image_path.as_posix())

    candidates: list[MetadataCandidate] = [("absolute", resolved_key)]
    if as_given_key and as_given_key != resolved_key:
        candidates.append(("relative", as_given_key))

    if image_path.name:
        candidates.append(("name", image_path.name))
    if image_path.stem and image_path.stem != image_path.name:
        candidates.append(("stem", image_path.stem))

    return _normalize_metadata_candidates(candidates)


def _collect_ambiguous_fallback_keys(
    image_paths: list[Path],
    metadata_key_candidates_by_image: Mapping[Path, list[MetadataCandidate]],
) -> dict[str, set[str]]:
    name_counter: Counter[str] = Counter()
    stem_counter: Counter[str] = Counter()

    for image_path in image_paths:
        candidates = metadata_key_candidates_by_image.get(image_path)
        if candidates is None:
            candidates = _build_default_metadata_candidates(image_path)

        for kind, key in candidates:
            if kind == "name":
                name_counter[key] += 1
            elif kind == "stem":
                stem_counter[key] += 1

    return {
        "name": {key for key, count in name_counter.items() if count > 1},
        "stem": {key for key, count in stem_counter.items() if count > 1},
    }


def _resolve_input_metadata(
    *,
    metadata_by_image: Mapping[str, dict[str, Any]],
    key_candidates: Sequence[MetadataCandidate],
    ambiguous_fallback_keys_by_kind: Mapping[str, set[str]],
    ambiguous_fallback_skipped_by_kind: dict[str, set[str]],
) -> tuple[dict[str, Any], str | None, str | None]:
    for kind, key in key_candidates:
        if kind in FALLBACK_METADATA_MATCH_MODES:
            ambiguous_keys = ambiguous_fallback_keys_by_kind.get(kind, set())
            if key in ambiguous_keys and key in metadata_by_image:
                ambiguous_fallback_skipped_by_kind.setdefault(kind, set()).add(key)
                continue

        metadata = metadata_by_image.get(key)
        if metadata is None:
            continue
        return dict(metadata), kind, key

    return {}, None, None


def _build_metadata_manifest_stats(
    *,
    metadata_by_image: Mapping[str, dict[str, Any]],
    matched_keys: set[str],
    match_mode_counts: Mapping[str, int],
    ambiguous_fallback_skipped_by_kind: Mapping[str, set[str]],
    warning_sample_size: int,
) -> dict[str, Any]:
    unmatched_keys = sorted(set(metadata_by_image) - matched_keys)
    mode_counts: dict[str, int] = {
        mode: int(match_mode_counts.get(mode, 0)) for mode in METADATA_MATCH_MODES
    }
    for mode, count in match_mode_counts.items():
        if mode not in mode_counts:
            mode_counts[mode] = int(count)

    return {
        "enabled": True,
        "total_keys": len(metadata_by_image),
        "matched_keys": len(matched_keys),
        "unmatched_keys": len(unmatched_keys),
        "match_mode_counts": mode_counts,
        "fallback_match_count": sum(
            int(match_mode_counts.get(mode, 0)) for mode in FALLBACK_METADATA_MATCH_MODES
        ),
        "unmatched_key_samples": unmatched_keys[:warning_sample_size],
        "ambiguous_fallback_skipped": {
            "name": sorted(ambiguous_fallback_skipped_by_kind.get("name", set())),
            "stem": sorted(ambiguous_fallback_skipped_by_kind.get("stem", set())),
        },
    }


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

    payload: dict[str, Any] = {
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

    metadata_manifest_raw = report.get("metadata_manifest")
    if isinstance(metadata_manifest_raw, Mapping):
        payload["metadata_manifest"] = {
            "enabled": bool(metadata_manifest_raw.get("enabled", False)),
            "total_keys": metadata_manifest_raw.get("total_keys", 0),
            "matched_keys": metadata_manifest_raw.get("matched_keys", 0),
            "unmatched_keys": metadata_manifest_raw.get("unmatched_keys", 0),
            "match_mode_counts": metadata_manifest_raw.get("match_mode_counts", {}),
            "fallback_match_count": metadata_manifest_raw.get("fallback_match_count", 0),
            "unmatched_key_samples": metadata_manifest_raw.get("unmatched_key_samples", []),
            "ambiguous_fallback_skipped": metadata_manifest_raw.get(
                "ambiguous_fallback_skipped",
                {"name": [], "stem": []},
            ),
        }

    return payload


def _benchmark_case_output_dir(base_dir: Path, image_path: Path, index: int) -> Path:
    """Return collision-safe per-case output directory.

    Prevent same-stem images from writing into the same location within one strategy run.
    """
    token = _canonicalize_manifest_key(image_path.as_posix()).replace("/", "__")
    if not token:
        token = image_path.name or "image"
    return base_dir / f"{index:04d}-{token}"


def run_benchmark(
    image_paths: list[Path],
    registry: StrategyRegistry,
    output_dir: Path,
    strategy_names: list[str] | None = None,
    feature_flags: FeatureFlags | None = None,
    dataset_id: str = "default",
    git_ref: str = "local",
    metadata_by_image: Mapping[str, Mapping[str, Any]] | None = None,
    metadata_key_candidates_by_image: Mapping[Path, Sequence[MetadataCandidate]] | None = None,
    strict_metadata_manifest: bool = False,
    metadata_warning_sample_size: int = DEFAULT_METADATA_WARNING_SAMPLE_SIZE,
) -> dict[str, Any]:
    if metadata_warning_sample_size < 1:
        raise ValueError("metadata_warning_sample_size must be >= 1")

    output_dir.mkdir(parents=True, exist_ok=True)
    flags = feature_flags or FeatureFlags()
    target_names = _resolve_strategy_names(registry, strategy_names, flags)

    normalized_metadata_by_image = _normalize_metadata_manifest(metadata_by_image)

    normalized_key_candidates_by_image: dict[Path, list[MetadataCandidate]] = {}
    if metadata_key_candidates_by_image is not None:
        for image_path, raw_candidates in metadata_key_candidates_by_image.items():
            normalized_key_candidates_by_image[image_path] = _normalize_metadata_candidates(
                list(raw_candidates)
            )

    ambiguous_fallback_keys_by_kind = _collect_ambiguous_fallback_keys(
        image_paths,
        normalized_key_candidates_by_image,
    )
    ambiguous_fallback_skipped_by_kind: dict[str, set[str]] = {"name": set(), "stem": set()}
    matched_keys: set[str] = set()
    match_mode_counts: Counter[str] = Counter()
    resolved_metadata_by_image: dict[Path, dict[str, Any]] = {}

    for image_path in image_paths:
        candidates = normalized_key_candidates_by_image.get(image_path)
        if candidates is None:
            candidates = _build_default_metadata_candidates(image_path)

        metadata, match_mode, matched_key = _resolve_input_metadata(
            metadata_by_image=normalized_metadata_by_image,
            key_candidates=candidates,
            ambiguous_fallback_keys_by_kind=ambiguous_fallback_keys_by_kind,
            ambiguous_fallback_skipped_by_kind=ambiguous_fallback_skipped_by_kind,
        )
        resolved_metadata_by_image[image_path] = metadata

        if match_mode is not None and matched_key is not None:
            matched_keys.add(matched_key)
            match_mode_counts[match_mode] += 1

    metadata_manifest_stats: dict[str, Any] | None = None
    if normalized_metadata_by_image:
        metadata_manifest_stats = _build_metadata_manifest_stats(
            metadata_by_image=normalized_metadata_by_image,
            matched_keys=matched_keys,
            match_mode_counts=match_mode_counts,
            ambiguous_fallback_skipped_by_kind=ambiguous_fallback_skipped_by_kind,
            warning_sample_size=metadata_warning_sample_size,
        )

        ambiguous_name = metadata_manifest_stats["ambiguous_fallback_skipped"]["name"]
        ambiguous_stem = metadata_manifest_stats["ambiguous_fallback_skipped"]["stem"]
        if ambiguous_name or ambiguous_stem:
            parts: list[str] = []
            if ambiguous_name:
                parts.append(f"name={ambiguous_name}")
            if ambiguous_stem:
                parts.append(f"stem={ambiguous_stem}")
            warnings.warn(
                "metadata manifest fallback disabled for ambiguous keys: " + ", ".join(parts),
                stacklevel=2,
            )

        unmatched_count = int(metadata_manifest_stats["unmatched_keys"])
        if unmatched_count > 0:
            unmatched_samples = metadata_manifest_stats["unmatched_key_samples"]
            unmatched_msg = (
                f"metadata manifest has {unmatched_count} unmatched key(s): {unmatched_samples}"
            )
            if strict_metadata_manifest:
                raise ValueError(f"strict-metadata-manifest: {unmatched_msg}")
            warnings.warn(unmatched_msg, stacklevel=2)

    legacy_results: dict[str, list[dict[str, Any]]] = {name: [] for name in target_names}
    outputs_map: dict[str, list[ConversionOutput]] = {name: [] for name in target_names}

    for index, image_path in enumerate(image_paths):
        conv_input = ConversionInput(
            image_path=image_path,
            metadata=resolved_metadata_by_image.get(image_path, {}),
        )
        for name in target_names:
            strategy = registry.get(name)
            case_output_dir = _benchmark_case_output_dir(output_dir / name, image_path, index)
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

    serialized: dict[str, Any] = dict(report.to_dict())
    if metadata_manifest_stats is not None:
        serialized["metadata_manifest"] = metadata_manifest_stats

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
