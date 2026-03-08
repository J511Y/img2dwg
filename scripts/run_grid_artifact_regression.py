"""Run floorplan regression and flag suspicious grid-like DXF outputs."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import ezdxf

from img2dwg.pipeline.benchmark import run_benchmark
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy
from img2dwg.strategies.hybrid_mvp import HybridMVPStrategy
from img2dwg.strategies.registry import FeatureFlags, StrategyRegistry
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _load_sync_manifest() -> Callable[[Path, Path], list[Path]]:
    candidate_paths = [
        Path(__file__).resolve().parent / "fetch_web_floorplan_assets.py",
        Path.cwd() / "scripts" / "fetch_web_floorplan_assets.py",
    ]

    for candidate in candidate_paths:
        if not candidate.exists() or not candidate.is_file():
            continue

        spec = importlib.util.spec_from_file_location(
            "fetch_web_floorplan_assets_runtime", candidate
        )
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        function = getattr(module, "sync_manifest", None)
        if callable(function):
            return cast(Callable[[Path, Path], list[Path]], function)

    raise ModuleNotFoundError("failed to load sync_manifest from fetch_web_floorplan_assets.py")


sync_manifest = _load_sync_manifest()


@dataclass(slots=True)
class RegressionThresholds:
    min_entities: int = 6
    min_unique_entity_types: int = 1
    min_axis_aligned_ratio_for_grid: float = 0.9
    min_line_count_for_grid_pattern: int = 8
    max_unique_x_for_grid: int = 4
    max_unique_y_for_grid: int = 4
    coord_round_digits: int = 3


@dataclass(slots=True)
class DxfDiagnostics:
    cad_loadable: bool
    total_entities: int
    entity_type_counts: dict[str, int]
    unique_entity_types: int
    line_count: int
    axis_aligned_line_ratio: float
    unique_x_count: int
    unique_y_count: int


@dataclass(slots=True)
class CaseFinding:
    strategy_name: str
    case_id: str
    image_path: str
    dxf_path: str | None
    flags: list[str]
    diagnostics: DxfDiagnostics


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _collect_image_paths(images_dir: Path) -> list[Path]:
    if not images_dir.exists() or not images_dir.is_dir():
        raise ValueError(f"images directory does not exist: {images_dir}")
    return sorted(
        path
        for path in images_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def _to_cwd_relative_paths(paths: list[Path]) -> list[Path]:
    cwd = Path.cwd().resolve()
    normalized: list[Path] = []

    for path in paths:
        resolved = path.resolve()
        try:
            normalized.append(resolved.relative_to(cwd))
        except ValueError:
            normalized.append(path)

    return normalized


def analyze_dxf(path_value: str | None, *, coord_round_digits: int = 3) -> DxfDiagnostics:
    if not path_value:
        return DxfDiagnostics(
            cad_loadable=False,
            total_entities=0,
            entity_type_counts={},
            unique_entity_types=0,
            line_count=0,
            axis_aligned_line_ratio=0.0,
            unique_x_count=0,
            unique_y_count=0,
        )

    path = Path(path_value)
    if not path.exists() or not path.is_file():
        return DxfDiagnostics(
            cad_loadable=False,
            total_entities=0,
            entity_type_counts={},
            unique_entity_types=0,
            line_count=0,
            axis_aligned_line_ratio=0.0,
            unique_x_count=0,
            unique_y_count=0,
        )

    try:
        doc = ezdxf.readfile(str(path))
    except Exception:
        return DxfDiagnostics(
            cad_loadable=False,
            total_entities=0,
            entity_type_counts={},
            unique_entity_types=0,
            line_count=0,
            axis_aligned_line_ratio=0.0,
            unique_x_count=0,
            unique_y_count=0,
        )

    type_counts: Counter[str] = Counter()
    line_count = 0
    axis_aligned_line_count = 0
    x_coords: set[float] = set()
    y_coords: set[float] = set()

    modelspace = doc.modelspace()
    for entity in modelspace:
        entity_type = entity.dxftype().upper()
        type_counts[entity_type] += 1

        if entity_type == "LINE":
            line_count += 1
            start = entity.dxf.start
            end = entity.dxf.end
            dx = float(end.x - start.x)
            dy = float(end.y - start.y)

            x_coords.add(round(float(start.x), coord_round_digits))
            x_coords.add(round(float(end.x), coord_round_digits))
            y_coords.add(round(float(start.y), coord_round_digits))
            y_coords.add(round(float(end.y), coord_round_digits))

            if math.isclose(dx, 0.0, abs_tol=1e-9) or math.isclose(dy, 0.0, abs_tol=1e-9):
                axis_aligned_line_count += 1

    axis_ratio = (axis_aligned_line_count / line_count) if line_count else 0.0

    return DxfDiagnostics(
        cad_loadable=True,
        total_entities=sum(type_counts.values()),
        entity_type_counts=dict(sorted(type_counts.items())),
        unique_entity_types=len(type_counts),
        line_count=line_count,
        axis_aligned_line_ratio=round(axis_ratio, 4),
        unique_x_count=len(x_coords),
        unique_y_count=len(y_coords),
    )


def evaluate_case(diagnostics: DxfDiagnostics, thresholds: RegressionThresholds) -> list[str]:
    flags: list[str] = []

    if not diagnostics.cad_loadable:
        flags.append("dxf_not_loadable")
        return flags

    if diagnostics.total_entities <= 0:
        flags.append("empty_drawable")

    if diagnostics.total_entities < thresholds.min_entities:
        flags.append("low_entity_count")

    if diagnostics.unique_entity_types < thresholds.min_unique_entity_types:
        flags.append("low_entity_diversity")

    suspicious_grid_pattern = (
        diagnostics.line_count >= thresholds.min_line_count_for_grid_pattern
        and diagnostics.axis_aligned_line_ratio >= thresholds.min_axis_aligned_ratio_for_grid
        and diagnostics.unique_x_count <= thresholds.max_unique_x_for_grid
        and diagnostics.unique_y_count <= thresholds.max_unique_y_for_grid
    )
    if suspicious_grid_pattern:
        flags.append("suspicious_grid_pattern")

    return flags


def analyze_benchmark_results(
    benchmark_results: dict[str, Any],
    *,
    thresholds: RegressionThresholds,
) -> dict[str, Any]:
    findings: list[CaseFinding] = []
    failures_by_reason: Counter[str] = Counter()
    strategy_failures: dict[str, Counter[str]] = {}

    for strategy in benchmark_results.get("strategies", []):
        strategy_name = str(strategy.get("strategy_name", ""))
        strategy_counter = strategy_failures.setdefault(strategy_name, Counter())
        for case in strategy.get("cases", []):
            dxf_path = case.get("dxf_path")
            diagnostics = analyze_dxf(
                dxf_path,
                coord_round_digits=thresholds.coord_round_digits,
            )
            flags = evaluate_case(diagnostics, thresholds)
            failures_by_reason.update(flags)
            strategy_counter.update(flags)
            findings.append(
                CaseFinding(
                    strategy_name=strategy_name,
                    case_id=str(case.get("case_id", "")),
                    image_path=str(case.get("image_path", "")),
                    dxf_path=str(dxf_path) if dxf_path else None,
                    flags=flags,
                    diagnostics=diagnostics,
                )
            )

    total_cases = len(findings)
    failed_cases = sum(1 for item in findings if item.flags)
    passed_cases = total_cases - failed_cases

    top_problematic = sorted(
        (item for item in findings if item.flags),
        key=lambda item: (len(item.flags), item.strategy_name, item.case_id),
        reverse=True,
    )[:10]

    strategy_breakdown = {
        name: dict(sorted(counter.items())) for name, counter in sorted(strategy_failures.items())
    }

    strategy_diagnostics: dict[str, dict[str, float]] = {}
    for strategy_name in sorted({item.strategy_name for item in findings}):
        strategy_cases = [item for item in findings if item.strategy_name == strategy_name]
        if not strategy_cases:
            continue
        axis_values = [item.diagnostics.axis_aligned_line_ratio for item in strategy_cases]
        line_values = [item.diagnostics.line_count for item in strategy_cases]
        avg_axis_ratio = sum(axis_values) / len(axis_values)
        avg_axis_margin = thresholds.min_axis_aligned_ratio_for_grid - avg_axis_ratio
        unique_x_values = [item.diagnostics.unique_x_count for item in strategy_cases]
        unique_y_values = [item.diagnostics.unique_y_count for item in strategy_cases]
        max_axis_ratio = max(axis_values)
        min_axis_ratio = min(axis_values)
        sorted_axis_values = sorted(axis_values)
        p95_index = max(0, math.ceil(len(sorted_axis_values) * 0.95) - 1)
        p95_axis_ratio = sorted_axis_values[p95_index]
        max_axis_margin = thresholds.min_axis_aligned_ratio_for_grid - max_axis_ratio
        min_axis_margin = thresholds.min_axis_aligned_ratio_for_grid - min_axis_ratio
        p95_axis_margin = thresholds.min_axis_aligned_ratio_for_grid - p95_axis_ratio
        if len(axis_values) > 1:
            variance = sum((value - avg_axis_ratio) ** 2 for value in axis_values) / len(axis_values)
            std_axis_ratio = math.sqrt(variance)
        else:
            std_axis_ratio = 0.0
        strategy_diagnostics[strategy_name] = {
            "avg_line_count": round(sum(line_values) / len(line_values), 4),
            "avg_axis_aligned_ratio": round(avg_axis_ratio, 4),
            "std_axis_aligned_ratio": round(std_axis_ratio, 4),
            "avg_axis_margin_to_grid_threshold": round(avg_axis_margin, 4),
            "avg_axis_margin_score": round(avg_axis_margin * 100.0, 2),
            "max_axis_aligned_ratio": round(max_axis_ratio, 4),
            "max_axis_margin_to_grid_threshold": round(max_axis_margin, 4),
            "p95_axis_aligned_ratio": round(p95_axis_ratio, 4),
            "p95_axis_margin_to_grid_threshold": round(p95_axis_margin, 4),
            "min_axis_aligned_ratio": round(min_axis_ratio, 4),
            "min_axis_margin_to_grid_threshold": round(min_axis_margin, 4),
            "avg_unique_x_count": round(sum(unique_x_values) / len(unique_x_values), 4),
            "avg_unique_y_count": round(sum(unique_y_values) / len(unique_y_values), 4),
        }

    payload = {
        "report_schema_version": 1,
        "generated_at": _utc_now_iso(),
        "summary": {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "pass_rate": round((passed_cases / total_cases), 4) if total_cases else 0.0,
            "failures_by_reason": dict(sorted(failures_by_reason.items())),
        },
        "thresholds": asdict(thresholds),
        "strategy_failures_by_reason": strategy_breakdown,
        "strategy_diagnostics": strategy_diagnostics,
        "top_problematic": [
            {
                "strategy_name": item.strategy_name,
                "case_id": item.case_id,
                "image_path": item.image_path,
                "flags": item.flags,
                "diagnostics": asdict(item.diagnostics),
            }
            for item in top_problematic
        ],
        "cases": [
            {
                "strategy_name": item.strategy_name,
                "case_id": item.case_id,
                "image_path": item.image_path,
                "dxf_path": item.dxf_path,
                "flags": item.flags,
                "diagnostics": asdict(item.diagnostics),
            }
            for item in findings
        ],
    }
    return payload


def _resolve_previous_report_path(
    *,
    requested: Path | None,
    report_json_path: Path,
) -> Path | None:
    if requested is not None:
        return requested if requested.exists() else None
    return report_json_path if report_json_path.exists() else None


def _attach_previous_delta(report: dict[str, Any], previous_report: dict[str, Any]) -> dict[str, Any]:
    current_summary = report.get("summary", {})
    previous_summary = previous_report.get("summary", {})

    current_failures = current_summary.get("failures_by_reason", {}) or {}
    previous_failures = previous_summary.get("failures_by_reason", {}) or {}

    def _failure_count(payload: dict[str, Any], key: str) -> int:
        value = payload.get(key, 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    current_hybrid = (report.get("strategy_diagnostics", {}) or {}).get("hybrid_mvp", {}) or {}
    previous_hybrid = (previous_report.get("strategy_diagnostics", {}) or {}).get("hybrid_mvp", {}) or {}

    def _to_float(payload: dict[str, Any], key: str) -> float | None:
        value = payload.get(key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    current_margin_score = _to_float(current_hybrid, "avg_axis_margin_score")
    previous_margin_score = _to_float(previous_hybrid, "avg_axis_margin_score")
    margin_score_delta = None
    if current_margin_score is not None and previous_margin_score is not None:
        margin_score_delta = round(current_margin_score - previous_margin_score, 4)

    current_avg_axis_ratio = _to_float(current_hybrid, "avg_axis_aligned_ratio")
    previous_avg_axis_ratio = _to_float(previous_hybrid, "avg_axis_aligned_ratio")
    avg_axis_ratio_delta = None
    if current_avg_axis_ratio is not None and previous_avg_axis_ratio is not None:
        avg_axis_ratio_delta = round(current_avg_axis_ratio - previous_avg_axis_ratio, 4)

    current_avg_axis_margin = _to_float(current_hybrid, "avg_axis_margin_to_grid_threshold")
    previous_avg_axis_margin = _to_float(previous_hybrid, "avg_axis_margin_to_grid_threshold")
    avg_axis_margin_delta = None
    if current_avg_axis_margin is not None and previous_avg_axis_margin is not None:
        avg_axis_margin_delta = round(current_avg_axis_margin - previous_avg_axis_margin, 4)

    current_avg_unique_x = _to_float(current_hybrid, "avg_unique_x_count")
    previous_avg_unique_x = _to_float(previous_hybrid, "avg_unique_x_count")
    avg_unique_x_delta = None
    if current_avg_unique_x is not None and previous_avg_unique_x is not None:
        avg_unique_x_delta = round(current_avg_unique_x - previous_avg_unique_x, 4)

    current_avg_unique_y = _to_float(current_hybrid, "avg_unique_y_count")
    previous_avg_unique_y = _to_float(previous_hybrid, "avg_unique_y_count")
    avg_unique_y_delta = None
    if current_avg_unique_y is not None and previous_avg_unique_y is not None:
        avg_unique_y_delta = round(current_avg_unique_y - previous_avg_unique_y, 4)

    current_avg_line_count = _to_float(current_hybrid, "avg_line_count")
    previous_avg_line_count = _to_float(previous_hybrid, "avg_line_count")
    avg_line_count_delta = None
    if current_avg_line_count is not None and previous_avg_line_count is not None:
        avg_line_count_delta = round(current_avg_line_count - previous_avg_line_count, 4)

    current_std_axis_ratio = _to_float(current_hybrid, "std_axis_aligned_ratio")
    previous_std_axis_ratio = _to_float(previous_hybrid, "std_axis_aligned_ratio")
    std_axis_ratio_delta = None
    if current_std_axis_ratio is not None and previous_std_axis_ratio is not None:
        std_axis_ratio_delta = round(current_std_axis_ratio - previous_std_axis_ratio, 4)

    current_max_axis_margin = _to_float(current_hybrid, "max_axis_margin_to_grid_threshold")
    previous_max_axis_margin = _to_float(previous_hybrid, "max_axis_margin_to_grid_threshold")
    max_axis_margin_delta = None
    if current_max_axis_margin is not None and previous_max_axis_margin is not None:
        max_axis_margin_delta = round(current_max_axis_margin - previous_max_axis_margin, 4)

    current_max_axis_ratio = _to_float(current_hybrid, "max_axis_aligned_ratio")
    previous_max_axis_ratio = _to_float(previous_hybrid, "max_axis_aligned_ratio")
    max_axis_ratio_delta = None
    if current_max_axis_ratio is not None and previous_max_axis_ratio is not None:
        max_axis_ratio_delta = round(current_max_axis_ratio - previous_max_axis_ratio, 4)

    current_p95_axis_margin = _to_float(current_hybrid, "p95_axis_margin_to_grid_threshold")
    previous_p95_axis_margin = _to_float(previous_hybrid, "p95_axis_margin_to_grid_threshold")
    p95_axis_margin_delta = None
    if current_p95_axis_margin is not None and previous_p95_axis_margin is not None:
        p95_axis_margin_delta = round(current_p95_axis_margin - previous_p95_axis_margin, 4)

    current_p95_axis_ratio = _to_float(current_hybrid, "p95_axis_aligned_ratio")
    previous_p95_axis_ratio = _to_float(previous_hybrid, "p95_axis_aligned_ratio")
    p95_axis_ratio_delta = None
    if current_p95_axis_ratio is not None and previous_p95_axis_ratio is not None:
        p95_axis_ratio_delta = round(current_p95_axis_ratio - previous_p95_axis_ratio, 4)

    current_min_axis_margin = _to_float(current_hybrid, "min_axis_margin_to_grid_threshold")
    previous_min_axis_margin = _to_float(previous_hybrid, "min_axis_margin_to_grid_threshold")
    min_axis_margin_delta = None
    if current_min_axis_margin is not None and previous_min_axis_margin is not None:
        min_axis_margin_delta = round(current_min_axis_margin - previous_min_axis_margin, 4)

    current_min_axis_ratio = _to_float(current_hybrid, "min_axis_aligned_ratio")
    previous_min_axis_ratio = _to_float(previous_hybrid, "min_axis_aligned_ratio")
    min_axis_ratio_delta = None
    if current_min_axis_ratio is not None and previous_min_axis_ratio is not None:
        min_axis_ratio_delta = round(current_min_axis_ratio - previous_min_axis_ratio, 4)

    previous_pass_rate = previous_summary.get("pass_rate")
    current_pass_rate = current_summary.get("pass_rate")
    pass_rate_delta = None
    try:
        if previous_pass_rate is not None and current_pass_rate is not None:
            pass_rate_delta = round(float(current_pass_rate) - float(previous_pass_rate), 4)
    except (TypeError, ValueError):
        pass_rate_delta = None

    report["delta_vs_previous"] = {
        "failed_cases": {
            "previous": int(previous_summary.get("failed_cases", 0)),
            "current": int(current_summary.get("failed_cases", 0)),
            "delta": int(current_summary.get("failed_cases", 0)) - int(previous_summary.get("failed_cases", 0)),
        },
        "pass_rate": {
            "previous": previous_pass_rate,
            "current": current_pass_rate,
            "delta": pass_rate_delta,
        },
        "suspicious_grid_pattern": {
            "previous": _failure_count(previous_failures, "suspicious_grid_pattern"),
            "current": _failure_count(current_failures, "suspicious_grid_pattern"),
            "delta": _failure_count(current_failures, "suspicious_grid_pattern")
            - _failure_count(previous_failures, "suspicious_grid_pattern"),
        },
        "low_entity_count": {
            "previous": _failure_count(previous_failures, "low_entity_count"),
            "current": _failure_count(current_failures, "low_entity_count"),
            "delta": _failure_count(current_failures, "low_entity_count")
            - _failure_count(previous_failures, "low_entity_count"),
        },
        "low_entity_diversity": {
            "previous": _failure_count(previous_failures, "low_entity_diversity"),
            "current": _failure_count(current_failures, "low_entity_diversity"),
            "delta": _failure_count(current_failures, "low_entity_diversity")
            - _failure_count(previous_failures, "low_entity_diversity"),
        },
        "hybrid_avg_axis_margin_score": {
            "previous": previous_margin_score,
            "current": current_margin_score,
            "delta": margin_score_delta,
        },
        "hybrid_avg_axis_aligned_ratio": {
            "previous": previous_avg_axis_ratio,
            "current": current_avg_axis_ratio,
            "delta": avg_axis_ratio_delta,
        },
        "hybrid_avg_axis_margin_to_grid_threshold": {
            "previous": previous_avg_axis_margin,
            "current": current_avg_axis_margin,
            "delta": avg_axis_margin_delta,
        },
        "hybrid_avg_unique_x_count": {
            "previous": previous_avg_unique_x,
            "current": current_avg_unique_x,
            "delta": avg_unique_x_delta,
        },
        "hybrid_avg_unique_y_count": {
            "previous": previous_avg_unique_y,
            "current": current_avg_unique_y,
            "delta": avg_unique_y_delta,
        },
        "hybrid_avg_line_count": {
            "previous": previous_avg_line_count,
            "current": current_avg_line_count,
            "delta": avg_line_count_delta,
        },
        "hybrid_std_axis_aligned_ratio": {
            "previous": previous_std_axis_ratio,
            "current": current_std_axis_ratio,
            "delta": std_axis_ratio_delta,
        },
        "hybrid_max_axis_margin_to_grid_threshold": {
            "previous": previous_max_axis_margin,
            "current": current_max_axis_margin,
            "delta": max_axis_margin_delta,
        },
        "hybrid_max_axis_aligned_ratio": {
            "previous": previous_max_axis_ratio,
            "current": current_max_axis_ratio,
            "delta": max_axis_ratio_delta,
        },
        "hybrid_p95_axis_margin_to_grid_threshold": {
            "previous": previous_p95_axis_margin,
            "current": current_p95_axis_margin,
            "delta": p95_axis_margin_delta,
        },
        "hybrid_p95_axis_aligned_ratio": {
            "previous": previous_p95_axis_ratio,
            "current": current_p95_axis_ratio,
            "delta": p95_axis_ratio_delta,
        },
        "hybrid_min_axis_margin_to_grid_threshold": {
            "previous": previous_min_axis_margin,
            "current": current_min_axis_margin,
            "delta": min_axis_margin_delta,
        },
        "hybrid_min_axis_aligned_ratio": {
            "previous": previous_min_axis_ratio,
            "current": current_min_axis_ratio,
            "delta": min_axis_ratio_delta,
        },
    }
    return report


def _render_markdown_report(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Grid Artifact Regression Report",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- total_cases: `{summary.get('total_cases')}`",
        f"- passed_cases: `{summary.get('passed_cases')}`",
        f"- failed_cases: `{summary.get('failed_cases')}`",
        f"- pass_rate: `{summary.get('pass_rate')}`",
        "",
        "## Failure reasons",
        "",
    ]

    failures = summary.get("failures_by_reason", {})
    if failures:
        for reason, count in failures.items():
            lines.append(f"- `{reason}`: {count}")
    else:
        lines.append("- none")

    delta_vs_previous = report.get("delta_vs_previous")
    if delta_vs_previous:
        lines.extend(["", "## Delta vs previous", ""])
        for key, payload in delta_vs_previous.items():
            lines.append(
                f"- `{key}`: previous={payload.get('previous')}, current={payload.get('current')}, delta={payload.get('delta')}"
            )

    strategy_diagnostics = report.get("strategy_diagnostics", {})
    lines.extend(["", "## Strategy diagnostics", ""])
    if strategy_diagnostics:
        for strategy, diag in strategy_diagnostics.items():
            lines.append(
                f"- `{strategy}`: avg_line_count={diag.get('avg_line_count')}, "
                f"avg_axis_aligned_ratio={diag.get('avg_axis_aligned_ratio')}, "
                f"std_axis_aligned_ratio={diag.get('std_axis_aligned_ratio')}, "
                f"avg_axis_margin_to_grid_threshold={diag.get('avg_axis_margin_to_grid_threshold')}, "
                f"avg_axis_margin_score={diag.get('avg_axis_margin_score')}, "
                f"max_axis_aligned_ratio={diag.get('max_axis_aligned_ratio')}, "
                f"max_axis_margin_to_grid_threshold={diag.get('max_axis_margin_to_grid_threshold')}, "
                f"p95_axis_aligned_ratio={diag.get('p95_axis_aligned_ratio')}, "
                f"p95_axis_margin_to_grid_threshold={diag.get('p95_axis_margin_to_grid_threshold')}, "
                f"min_axis_aligned_ratio={diag.get('min_axis_aligned_ratio')}, "
                f"min_axis_margin_to_grid_threshold={diag.get('min_axis_margin_to_grid_threshold')}, "
                f"avg_unique_x_count={diag.get('avg_unique_x_count')}, "
                f"avg_unique_y_count={diag.get('avg_unique_y_count')}"
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Top problematic samples",
            "",
            "| strategy | case_id | image | flags | entities | unique_types | axis_ratio | unique_x | unique_y |",
            "|---|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )

    for item in report.get("top_problematic", []):
        diagnostics = item.get("diagnostics", {})
        image_path = Path(str(item.get("image_path", ""))).name
        flags = ", ".join(item.get("flags", []))
        lines.append(
            "| {strategy} | {case_id} | {image} | {flags} | {entities} | {types} | {axis} | {ux} | {uy} |".format(
                strategy=item.get("strategy_name"),
                case_id=item.get("case_id"),
                image=image_path,
                flags=flags,
                entities=diagnostics.get("total_entities", 0),
                types=diagnostics.get("unique_entity_types", 0),
                axis=diagnostics.get("axis_aligned_line_ratio", 0.0),
                ux=diagnostics.get("unique_x_count", 0),
                uy=diagnostics.get("unique_y_count", 0),
            )
        )

    return "\n".join(lines) + "\n"


def _build_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register(HybridMVPStrategy())
    registry.register(TwoStageBaselineStrategy())
    registry.register(ConsensusQAStrategy())
    return registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run floorplan benchmark and detect suspicious grid-like DXF outputs"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("eval/datasets/web_floorplan_grid_v1/manifest.csv"),
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=Path("output/web_floorplan_grid_v1"),
        help="manifest sync output root (images stored under <assets-dir>/images)",
    )
    parser.add_argument(
        "--benchmark-output",
        type=Path,
        default=Path("output/benchmark/web_floorplan_grid_v1"),
    )
    parser.add_argument("--dataset-id", type=str, default="web_floorplan_grid_v1")
    parser.add_argument("--git-ref", type=str, default="local")
    parser.add_argument(
        "--strategies",
        type=str,
        default="hybrid_mvp,two_stage_baseline,consensus_qa",
        help="comma-separated strategy names",
    )
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument(
        "--report-json",
        type=Path,
        default=Path("eval/reports/web_floorplan_grid_v1/grid_artifact_regression.json"),
    )
    parser.add_argument(
        "--report-md",
        type=Path,
        default=Path("eval/reports/web_floorplan_grid_v1/grid_artifact_regression.md"),
    )
    parser.add_argument("--fail-on-findings", action="store_true")
    parser.add_argument(
        "--previous-report-json",
        type=Path,
        default=None,
        help="optional previous report JSON path for delta comparison",
    )
    parser.add_argument("--min-entities", type=int, default=6)
    parser.add_argument("--min-unique-entity-types", type=int, default=1)
    parser.add_argument("--min-axis-aligned-ratio-for-grid", type=float, default=0.9)
    parser.add_argument("--min-line-count-for-grid-pattern", type=int, default=8)
    parser.add_argument("--max-unique-x-for-grid", type=int, default=4)
    parser.add_argument("--max-unique-y-for-grid", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.skip_sync:
        image_paths = _collect_image_paths(args.assets_dir / "images")
    else:
        image_paths = sync_manifest(args.manifest, args.assets_dir)

    image_paths = _to_cwd_relative_paths(image_paths)

    if not image_paths:
        raise ValueError("no images available for regression run")

    registry = _build_registry()
    args.benchmark_output.mkdir(parents=True, exist_ok=True)

    run_benchmark(
        image_paths=image_paths,
        registry=registry,
        output_dir=args.benchmark_output,
        strategy_names=_parse_csv(args.strategies),
        feature_flags=FeatureFlags(),
        dataset_id=args.dataset_id,
        git_ref=args.git_ref,
    )

    benchmark_results_path = args.benchmark_output / "benchmark_results.json"
    benchmark_results = json.loads(benchmark_results_path.read_text(encoding="utf-8"))

    thresholds = RegressionThresholds(
        min_entities=args.min_entities,
        min_unique_entity_types=args.min_unique_entity_types,
        min_axis_aligned_ratio_for_grid=args.min_axis_aligned_ratio_for_grid,
        min_line_count_for_grid_pattern=args.min_line_count_for_grid_pattern,
        max_unique_x_for_grid=args.max_unique_x_for_grid,
        max_unique_y_for_grid=args.max_unique_y_for_grid,
    )

    report = analyze_benchmark_results(benchmark_results, thresholds=thresholds)
    report["dataset_id"] = args.dataset_id
    report["manifest"] = str(args.manifest)
    report["benchmark_results_path"] = str(benchmark_results_path)

    previous_report_path = _resolve_previous_report_path(
        requested=args.previous_report_json,
        report_json_path=args.report_json,
    )
    if previous_report_path is not None:
        previous_report = json.loads(previous_report_path.read_text(encoding="utf-8"))
        report = _attach_previous_delta(report, previous_report)

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.write_text(_render_markdown_report(report), encoding="utf-8")

    failed_cases = int(report.get("summary", {}).get("failed_cases", 0))
    print(
        "grid artifact regression: "
        f"total={report['summary']['total_cases']} "
        f"failed={failed_cases} "
        f"report={args.report_json}"
    )

    if args.fail_on_findings and failed_cases > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
