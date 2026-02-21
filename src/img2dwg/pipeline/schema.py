from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

from img2dwg.strategies.base import ConversionOutput


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))
    return ordered[index]


def _normalize_non_negative(value: Any, *, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(numeric):
        return default
    return max(numeric, 0.0)


def _normalize_ratio(value: Any, *, default: float = 0.0) -> float:
    numeric = _normalize_non_negative(value, default=default)
    return min(numeric, 1.0)


def _normalize_success(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return False
        return bool(value)
    return False


def _normalize_metrics(value: Any) -> dict[str, float]:
    source: Mapping[str, Any] = value if isinstance(value, Mapping) else {}
    return {
        "iou": _normalize_ratio(source.get("iou", 0.0)),
        "topology_f1": _normalize_ratio(source.get("topology_f1", 0.0)),
    }


def _normalize_notes(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(note) for note in value if note is not None]


@dataclass(slots=True)
class BenchmarkRunMeta:
    run_id: str
    git_ref: str
    dataset_id: str
    generated_at: str


@dataclass(slots=True)
class BenchmarkCaseResult:
    case_id: str
    image_path: str
    dxf_path: str | None
    success: bool
    elapsed_ms: float
    metrics: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BenchmarkStrategySummary:
    total_cases: int
    success_count: int
    success_rate: float
    median_elapsed_ms: float
    p95_elapsed_ms: float
    mean_iou: float
    mean_topology_f1: float


@dataclass(slots=True)
class BenchmarkStrategyResult:
    strategy_name: str
    track: str
    status: str
    promoted: bool
    cases: list[BenchmarkCaseResult]
    summary: BenchmarkStrategySummary


@dataclass(slots=True)
class BenchmarkRankingEntry:
    strategy_name: str
    composite_score: float
    rank: int


@dataclass(slots=True)
class BenchmarkReport:
    schema_version: int
    run: BenchmarkRunMeta
    standards: dict[str, Any]
    strategies: list[BenchmarkStrategyResult]
    ranking: list[BenchmarkRankingEntry]
    legacy: dict[str, list[dict[str, Any]]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run": {
                "run_id": self.run.run_id,
                "git_ref": self.run.git_ref,
                "dataset_id": self.run.dataset_id,
                "generated_at": self.run.generated_at,
            },
            "standards": self.standards,
            "strategies": [
                {
                    "strategy_name": s.strategy_name,
                    "track": s.track,
                    "status": s.status,
                    "promoted": s.promoted,
                    "cases": [
                        {
                            "case_id": c.case_id,
                            "image_path": c.image_path,
                            "dxf_path": c.dxf_path,
                            "success": c.success,
                            "elapsed_ms": c.elapsed_ms,
                            "metrics": c.metrics,
                            "notes": c.notes,
                        }
                        for c in s.cases
                    ],
                    "summary": {
                        "total_cases": s.summary.total_cases,
                        "success_count": s.summary.success_count,
                        "success_rate": s.summary.success_rate,
                        "median_elapsed_ms": s.summary.median_elapsed_ms,
                        "p95_elapsed_ms": s.summary.p95_elapsed_ms,
                        "mean_iou": s.summary.mean_iou,
                        "mean_topology_f1": s.summary.mean_topology_f1,
                    },
                }
                for s in self.strategies
            ],
            "ranking": [
                {
                    "strategy_name": r.strategy_name,
                    "composite_score": r.composite_score,
                    "rank": r.rank,
                }
                for r in self.ranking
            ],
            "legacy": self.legacy,
        }


def build_strategy_result(
    strategy_name: str,
    outputs: list[ConversionOutput],
    image_paths: list[Path],
    *,
    track: str,
    status: str,
    promoted: bool,
) -> BenchmarkStrategyResult:
    if len(outputs) != len(image_paths):
        msg = (
            "outputs/image_paths length mismatch: "
            f"strategy={strategy_name}, outputs={len(outputs)}, images={len(image_paths)}"
        )
        raise ValueError(msg)

    cases: list[BenchmarkCaseResult] = []
    for idx, (image_path, out) in enumerate(zip(image_paths, outputs, strict=True), start=1):
        normalized_metrics = _normalize_metrics(out.metrics)
        cases.append(
            BenchmarkCaseResult(
                case_id=f"case_{idx:03d}",
                image_path=str(image_path),
                dxf_path=str(out.dxf_path) if out.dxf_path else None,
                success=_normalize_success(out.success),
                elapsed_ms=round(_normalize_non_negative(out.elapsed_ms), 2),
                metrics=normalized_metrics,
                notes=_normalize_notes(out.notes),
            )
        )

    elapsed = [c.elapsed_ms for c in cases]
    ious = [c.metrics.get("iou", 0.0) for c in cases]
    topologies = [c.metrics.get("topology_f1", 0.0) for c in cases]
    success_count = sum(1 for c in cases if c.success)
    total = len(cases)

    summary = BenchmarkStrategySummary(
        total_cases=total,
        success_count=success_count,
        success_rate=round(success_count / total, 4) if total else 0.0,
        median_elapsed_ms=round(median(elapsed), 2) if elapsed else 0.0,
        p95_elapsed_ms=round(_p95(elapsed), 2) if elapsed else 0.0,
        mean_iou=round(mean(ious), 4) if ious else 0.0,
        mean_topology_f1=round(mean(topologies), 4) if topologies else 0.0,
    )

    return BenchmarkStrategyResult(
        strategy_name=strategy_name,
        track=track,
        status=status,
        promoted=promoted,
        cases=cases,
        summary=summary,
    )


def _composite_score(summary: BenchmarkStrategySummary) -> float:
    return round(
        0.35 * summary.success_rate
        + 0.25 * summary.mean_iou
        + 0.25 * summary.mean_topology_f1
        + 0.15 * (1 / (1 + max(summary.median_elapsed_ms, 0.0))),
        4,
    )


def build_report(
    *,
    strategy_outputs: dict[str, list[ConversionOutput]],
    image_paths: list[Path],
    dataset_id: str,
    git_ref: str,
    legacy: dict[str, list[dict[str, Any]]],
) -> BenchmarkReport:
    strategy_results: list[BenchmarkStrategyResult] = []
    for strategy_name, outputs in strategy_outputs.items():
        strategy_results.append(
            build_strategy_result(
                strategy_name=strategy_name,
                outputs=outputs,
                image_paths=image_paths,
                track="core",
                status="candidate",
                promoted=False,
            )
        )

    scored_results = [
        (strategy, _composite_score(strategy.summary)) for strategy in strategy_results
    ]
    ranked = sorted(
        scored_results,
        key=lambda item: (
            item[1],
            item[0].summary.success_rate,
            item[0].summary.mean_iou,
            item[0].summary.mean_topology_f1,
            -item[0].summary.median_elapsed_ms,
        ),
        reverse=True,
    )

    ranking = [
        BenchmarkRankingEntry(
            strategy_name=strategy.strategy_name,
            composite_score=score,
            rank=i + 1,
        )
        for i, (strategy, score) in enumerate(ranked)
    ]

    return BenchmarkReport(
        schema_version=2,
        run=BenchmarkRunMeta(
            run_id=_utc_now_iso(),
            git_ref=git_ref,
            dataset_id=dataset_id,
            generated_at=_utc_now_iso(),
        ),
        standards={
            "metric_units": {
                "success_rate": "ratio_0_1",
                "median_elapsed_ms": "ms",
                "p95_elapsed_ms": "ms",
                "mean_iou": "ratio_0_1",
                "mean_topology_f1": "ratio_0_1",
            },
            "validation": {
                "elapsed_ms": {"min": 0.0},
                "metrics": {
                    "iou": {"min": 0.0, "max": 1.0},
                    "topology_f1": {"min": 0.0, "max": 1.0},
                },
                "missing_metric_policy": "default_to_0.0",
            },
        },
        strategies=strategy_results,
        ranking=ranking,
        legacy=legacy,
    )
