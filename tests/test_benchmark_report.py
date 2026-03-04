import json
import math
from pathlib import Path
from typing import Any, cast

import ezdxf
import pytest

from img2dwg.pipeline.benchmark import _build_final_summary, run_benchmark
from img2dwg.pipeline.schema import build_strategy_result
from img2dwg.strategies.base import ConversionInput, ConversionOutput, ConversionStrategy
from img2dwg.strategies.registry import FeatureFlags, StrategyRegistry


def _load_summary_payload(output_dir: Path) -> dict[str, Any]:
    summary_file = output_dir / "benchmark_summary.json"
    return cast(dict[str, Any], json.loads(summary_file.read_text(encoding="utf-8")))


class SuccessStrategy(ConversionStrategy):
    name = "success"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=output_dir / f"{conv_input.image_path.stem}.dxf",
            success=True,
            elapsed_ms=0.0,
            metrics={"iou": 0.9, "topology_f1": 0.8},
            notes=[],
        )


class HighRiskSuccessStrategy(SuccessStrategy):
    name = "high_risk_success"
    risk_tier = "high"


class FastLowQualityStrategy(ConversionStrategy):
    name = "fast_low_quality"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=output_dir / f"{conv_input.image_path.stem}.dxf",
            success=True,
            elapsed_ms=1.0,
            metrics={"iou": 0.4, "topology_f1": 0.4},
            notes=["quality below threshold"],
        )


class SlowHighQualityStrategy(ConversionStrategy):
    name = "slow_high_quality"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=output_dir / f"{conv_input.image_path.stem}.dxf",
            success=True,
            elapsed_ms=50.0,
            metrics={"iou": 0.95, "topology_f1": 0.93},
            notes=[],
        )


class TriadThesisStrategy(ConversionStrategy):
    name = "two_stage_baseline"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=output_dir / f"{conv_input.image_path.stem}.dxf",
            success=True,
            elapsed_ms=10.0,
            metrics={"iou": 0.55, "topology_f1": 0.50},
            notes=[],
        )

    def timed_run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        return self.run(conv_input, output_dir)


class TriadAntithesisStrategy(ConversionStrategy):
    name = "consensus_qa"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=output_dir / f"{conv_input.image_path.stem}.dxf",
            success=True,
            elapsed_ms=12.0,
            metrics={"iou": 0.60, "topology_f1": 0.65},
            notes=[],
        )

    def timed_run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        return self.run(conv_input, output_dir)


class TriadSynthesisStrategy(ConversionStrategy):
    name = "hybrid_mvp"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=output_dir / f"{conv_input.image_path.stem}.dxf",
            success=True,
            elapsed_ms=11.0,
            metrics={"iou": 0.70, "topology_f1": 0.72},
            notes=[],
        )

    def timed_run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        return self.run(conv_input, output_dir)


class PartialMetricStrategy(ConversionStrategy):
    name = "partial_metric"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=output_dir / f"{conv_input.image_path.stem}.dxf",
            success=True,
            elapsed_ms=3.0,
            metrics={"iou": 0.7},
            notes=[],
        )


class InvalidMetricStrategy(ConversionStrategy):
    name = "invalid_metric"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=output_dir / f"{conv_input.image_path.stem}.dxf",
            success=True,
            elapsed_ms=-10.0,
            metrics={"iou": 2.5, "topology_f1": -0.2},
            notes=["raw metric out of range"],
        )

    def timed_run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        # schema validation 테스트를 위해 음수/이상치 값을 그대로 전달
        return self.run(conv_input, output_dir)


class NonNumericMetricStrategy(ConversionStrategy):
    name = "non_numeric_metric"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=output_dir / f"{conv_input.image_path.stem}.dxf",
            success=True,
            elapsed_ms="nan",  # type: ignore[arg-type]
            metrics={"iou": "oops", "topology_f1": None},  # type: ignore[dict-item]
            notes=["invalid numeric payload"],
        )

    def timed_run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        return self.run(conv_input, output_dir)


class InvalidPayloadStrategy(ConversionStrategy):
    name = "invalid_payload"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=output_dir / f"{conv_input.image_path.stem}.dxf",
            success="yes",  # type: ignore[arg-type]
            elapsed_ms=5.0,
            metrics=None,  # type: ignore[arg-type]
            notes=None,  # type: ignore[arg-type]
        )

    def timed_run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        return self.run(conv_input, output_dir)


class NonFiniteSuccessStrategy(ConversionStrategy):
    name = "non_finite_success"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=output_dir / f"{conv_input.image_path.stem}.dxf",
            success=math.nan,  # type: ignore[arg-type]
            elapsed_ms=1.0,
            metrics={"iou": 0.4, "topology_f1": 0.4},
            notes=[],
        )

    def timed_run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        return self.run(conv_input, output_dir)


def test_run_benchmark_returns_v2_schema(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(SuccessStrategy())

    result = run_benchmark(
        image_paths=[img],
        registry=reg,
        output_dir=tmp_path / "out",
        dataset_id="unit",
        git_ref="test",
    )

    assert result["schema_version"] == 2
    assert result["run"]["dataset_id"] == "unit"
    assert result["strategies"][0]["summary"]["success_rate"] == 1.0
    assert result["strategies"][0]["summary"]["cad_loadable_rate"] == 0.0
    assert result["ranking"][0]["strategy_name"] == "success"

    summary_file = tmp_path / "out" / "benchmark_summary.json"
    assert summary_file.exists()

    summary_payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary_payload["summary_schema_version"] == 1
    assert summary_payload["source_schema_version"] == 2
    assert summary_payload["run"]["dataset_id"] == "unit"
    assert summary_payload["winner"] == {
        "strategy_name": "success",
        "rank": 1,
        "composite_score": result["ranking"][0]["composite_score"],
    }
    assert summary_payload["triad_gate"] == {
        "available": False,
        "passed": None,
        "missing": [
            "two_stage_baseline",
            "consensus_qa",
            "hybrid_mvp",
        ],
    }
    assert len(summary_payload["strategies"]) == 1
    strategy_row = summary_payload["strategies"][0]
    assert strategy_row["strategy_name"] == "success"
    assert strategy_row["rank"] == 1
    assert strategy_row["composite_score"] == result["ranking"][0]["composite_score"]
    assert strategy_row["success_rate"] == 1.0
    assert strategy_row["cad_loadable_count"] == 0
    assert strategy_row["cad_loadable_rate"] == 0.0
    assert strategy_row["mean_iou"] == 0.9
    assert strategy_row["mean_topology_f1"] == 0.8
    assert strategy_row["median_elapsed_ms"] >= 0.0
    assert strategy_row["p95_elapsed_ms"] >= 0.0


def test_run_benchmark_summary_fields_match_results_payload(tmp_path: Path) -> None:
    img1 = tmp_path / "a.png"
    img2 = tmp_path / "b.png"
    img1.write_bytes(b"fake")
    img2.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(FastLowQualityStrategy())
    reg.register(SlowHighQualityStrategy())

    out_dir = tmp_path / "out-summary-consistency"
    result = run_benchmark(
        image_paths=[img1, img2],
        registry=reg,
        output_dir=out_dir,
        dataset_id="summary-consistency",
        git_ref="test",
    )

    summary_payload = _load_summary_payload(out_dir)

    ranking_by_name = {
        entry["strategy_name"]: entry
        for entry in result["ranking"]
    }
    results_summary_by_name = {
        strategy["strategy_name"]: strategy["summary"]
        for strategy in result["strategies"]
    }

    run_info = summary_payload["run"]
    assert isinstance(run_info, dict)
    assert run_info == result["run"]

    winner = summary_payload["winner"]
    assert winner == {
        "strategy_name": result["ranking"][0]["strategy_name"],
        "rank": result["ranking"][0]["rank"],
        "composite_score": result["ranking"][0]["composite_score"],
    }

    summary_rows = summary_payload["strategies"]
    assert isinstance(summary_rows, list)
    assert [row["rank"] for row in summary_rows] == sorted(
        entry["rank"] for entry in result["ranking"]
    )

    for row in summary_rows:
        strategy_name = row["strategy_name"]
        rank_entry = ranking_by_name[strategy_name]
        source_summary = results_summary_by_name[strategy_name]

        assert row["rank"] == rank_entry["rank"]
        assert row["composite_score"] == rank_entry["composite_score"]
        assert row["success_rate"] == source_summary["success_rate"]
        assert row["cad_loadable_count"] == source_summary["cad_loadable_count"]
        assert row["cad_loadable_rate"] == source_summary["cad_loadable_rate"]
        assert row["mean_iou"] == source_summary["mean_iou"]
        assert row["mean_topology_f1"] == source_summary["mean_topology_f1"]
        assert row["median_elapsed_ms"] == source_summary["median_elapsed_ms"]
        assert row["p95_elapsed_ms"] == source_summary["p95_elapsed_ms"]


def test_build_final_summary_allows_nullable_winner_and_sorts_unranked_rows() -> None:
    report = {
        "schema_version": 2,
        "run": {
            "run_id": "r1",
            "dataset_id": "unit",
            "git_ref": "test",
            "generated_at": "2026-02-24T00:00:00Z",
        },
        "ranking": [
            {
                "strategy_name": "",
                "rank": 1,
                "composite_score": 0.99,
            },
            {
                "strategy_name": "gamma",
                "rank": 1,
                "composite_score": 0.95,
            },
        ],
        "strategies": [
            {
                "strategy_name": "beta",
                "summary": {"success_rate": 0.3},
            },
            {
                "strategy_name": "alpha",
                "summary": {"success_rate": 0.2},
            },
            {
                "strategy_name": "gamma",
                "summary": {"success_rate": 0.4},
            },
        ],
        "comparisons": {
            "thesis_antithesis_synthesis": {
                "available": False,
                "missing": ["two_stage_baseline"],
            }
        },
    }

    summary = _build_final_summary(report)

    assert summary["winner"] is None
    assert [row["strategy_name"] for row in summary["strategies"]] == [
        "gamma",
        "alpha",
        "beta",
    ]


def test_run_benchmark_ranking_prefers_quality_when_success_equal(tmp_path: Path) -> None:
    img1 = tmp_path / "a.png"
    img2 = tmp_path / "b.png"
    img1.write_bytes(b"fake")
    img2.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(FastLowQualityStrategy())
    reg.register(SlowHighQualityStrategy())

    result = run_benchmark(
        image_paths=[img1, img2],
        registry=reg,
        output_dir=tmp_path / "out",
        dataset_id="ranking-check",
        git_ref="test",
    )

    assert len(result["strategies"]) == 2
    assert (tmp_path / "out" / "benchmark_results.json").exists()

    # success_rate가 동일하면 iou/topology가 더 높은 전략이 상위여야 한다.
    assert result["ranking"][0]["strategy_name"] == "slow_high_quality"
    assert result["ranking"][1]["strategy_name"] == "fast_low_quality"


def test_run_benchmark_ranking_sorted_by_composite_score(tmp_path: Path) -> None:
    img1 = tmp_path / "a.png"
    img2 = tmp_path / "b.png"
    img1.write_bytes(b"fake")
    img2.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(FastLowQualityStrategy())
    reg.register(SlowHighQualityStrategy())

    result = run_benchmark(
        image_paths=[img1, img2],
        registry=reg,
        output_dir=tmp_path / "out-score",
        dataset_id="ranking-composite-check",
        git_ref="test",
    )

    scores = [entry["composite_score"] for entry in result["ranking"]]
    assert scores == sorted(scores, reverse=True)
    assert [entry["rank"] for entry in result["ranking"]] == [1, 2]


def test_run_benchmark_defaults_missing_metric_to_zero(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(PartialMetricStrategy())

    result = run_benchmark(
        image_paths=[img],
        registry=reg,
        output_dir=tmp_path / "out",
        dataset_id="missing-metric",
        git_ref="test",
    )

    summary = result["strategies"][0]["summary"]
    case_metrics = result["strategies"][0]["cases"][0]["metrics"]

    assert case_metrics["iou"] == 0.7
    assert case_metrics["topology_f1"] == 0.0
    assert summary["mean_iou"] == 0.7
    assert summary["mean_topology_f1"] == 0.0


def test_run_benchmark_clamps_out_of_range_metrics_and_elapsed(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(InvalidMetricStrategy())

    result = run_benchmark(
        image_paths=[img],
        registry=reg,
        output_dir=tmp_path / "out",
        dataset_id="invalid-metric",
        git_ref="test",
    )

    case = result["strategies"][0]["cases"][0]
    standards = result["standards"]

    assert case["elapsed_ms"] == 0.0
    assert case["metrics"] == {"iou": 1.0, "topology_f1": 0.0}
    assert standards["validation"]["missing_metric_policy"] == "default_to_0.0"


def test_run_benchmark_defaults_non_numeric_values_to_zero(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(NonNumericMetricStrategy())

    result = run_benchmark(
        image_paths=[img],
        registry=reg,
        output_dir=tmp_path / "out",
        dataset_id="non-numeric-metric",
        git_ref="test",
    )

    case = result["strategies"][0]["cases"][0]

    assert case["elapsed_ms"] == 0.0
    assert case["metrics"] == {"iou": 0.0, "topology_f1": 0.0}


def test_run_benchmark_normalizes_invalid_payload_containers(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(InvalidPayloadStrategy())

    result = run_benchmark(
        image_paths=[img],
        registry=reg,
        output_dir=tmp_path / "out",
        dataset_id="invalid-payload",
        git_ref="test",
    )

    case = result["strategies"][0]["cases"][0]
    assert case["success"] is False
    assert case["metrics"] == {"iou": 0.0, "topology_f1": 0.0}
    assert case["notes"] == []


def test_build_strategy_result_handles_empty_cases() -> None:
    result = build_strategy_result(
        strategy_name="empty_case",
        outputs=[],
        image_paths=[],
        track="core",
        status="candidate",
        promoted=False,
    )

    assert result.summary.total_cases == 0
    assert result.summary.success_count == 0
    assert result.summary.success_rate == 0.0
    assert result.summary.cad_loadable_count == 0
    assert result.summary.cad_loadable_rate == 0.0
    assert result.summary.median_elapsed_ms == 0.0
    assert result.summary.p95_elapsed_ms == 0.0
    assert result.summary.mean_iou == 0.0
    assert result.summary.mean_topology_f1 == 0.0


def test_build_strategy_result_tracks_cad_loadable_rate(tmp_path: Path) -> None:
    img1 = tmp_path / "a.png"
    img2 = tmp_path / "b.png"
    img1.write_bytes(b"fake")
    img2.write_bytes(b"fake")

    loadable_dxf = tmp_path / "a.dxf"
    ezdxf.new("R2018", setup=True).saveas(str(loadable_dxf))

    broken_dxf = tmp_path / "b.dxf"
    broken_dxf.write_text("not-a-valid-dxf", encoding="utf-8")

    outputs = [
        ConversionOutput(
            strategy_name="cad_loadable_check",
            dxf_path=loadable_dxf,
            success=True,
            elapsed_ms=1.0,
            metrics={"iou": 0.7, "topology_f1": 0.6},
            notes=[],
        ),
        ConversionOutput(
            strategy_name="cad_loadable_check",
            dxf_path=broken_dxf,
            success=True,
            elapsed_ms=1.2,
            metrics={"iou": 0.6, "topology_f1": 0.5},
            notes=[],
        ),
    ]

    result = build_strategy_result(
        strategy_name="cad_loadable_check",
        outputs=outputs,
        image_paths=[img1, img2],
        track="core",
        status="candidate",
        promoted=False,
    )

    assert result.cases[0].cad_loadable is True
    assert result.cases[1].cad_loadable is False
    assert result.summary.cad_loadable_count == 1
    assert result.summary.cad_loadable_rate == 0.5


def test_build_strategy_result_normalizes_numeric_success(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    output = ConversionOutput(
        strategy_name="numeric_success",
        dxf_path=tmp_path / "a.dxf",
        success=1,  # type: ignore[arg-type]
        elapsed_ms=2.0,
        metrics={"iou": 0.5, "topology_f1": 0.5},
        notes=[],
    )

    result = build_strategy_result(
        strategy_name="numeric_success",
        outputs=[output],
        image_paths=[img],
        track="core",
        status="candidate",
        promoted=False,
    )

    assert result.cases[0].success is True
    assert result.summary.success_rate == 1.0


def test_build_strategy_result_defaults_non_finite_success_to_false(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    output = ConversionOutput(
        strategy_name="non_finite_success",
        dxf_path=tmp_path / "a.dxf",
        success=math.inf,  # type: ignore[arg-type]
        elapsed_ms=2.0,
        metrics={"iou": 0.5, "topology_f1": 0.5},
        notes=[],
    )

    result = build_strategy_result(
        strategy_name="non_finite_success",
        outputs=[output],
        image_paths=[img],
        track="core",
        status="candidate",
        promoted=False,
    )

    assert result.cases[0].success is False
    assert result.summary.success_rate == 0.0


def test_run_benchmark_rejects_nan_success_payload(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(NonFiniteSuccessStrategy())

    result = run_benchmark(
        image_paths=[img],
        registry=reg,
        output_dir=tmp_path / "out",
        dataset_id="non-finite-success",
        git_ref="test",
    )

    case = result["strategies"][0]["cases"][0]
    assert case["success"] is False


def test_run_benchmark_rejects_unknown_strategy_name(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(SuccessStrategy())

    with pytest.raises(ValueError, match="Unknown strategies requested: missing"):
        run_benchmark(
            image_paths=[img],
            registry=reg,
            output_dir=tmp_path / "out-unknown",
            strategy_names=["missing"],
            dataset_id="unknown-strategy",
            git_ref="test",
        )


def test_run_benchmark_normalizes_strategy_names(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(SuccessStrategy())
    reg.register(FastLowQualityStrategy())

    result = run_benchmark(
        image_paths=[img],
        registry=reg,
        output_dir=tmp_path / "out-normalized",
        strategy_names=[" success ", "success", ""],
        dataset_id="normalized-strategy-names",
        git_ref="test",
    )

    assert [strategy["strategy_name"] for strategy in result["strategies"]] == ["success"]


def test_run_benchmark_blocks_high_risk_strategy_without_allowlist(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(HighRiskSuccessStrategy())

    with pytest.raises(ValueError, match="Blocked strategies by feature flags: high_risk_success"):
        run_benchmark(
            image_paths=[img],
            registry=reg,
            output_dir=tmp_path / "out-high-risk-blocked",
            strategy_names=["high_risk_success"],
            dataset_id="high-risk-blocked",
            git_ref="test",
        )


def test_run_benchmark_allows_allowlisted_high_risk_strategy(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(HighRiskSuccessStrategy())

    result = run_benchmark(
        image_paths=[img],
        registry=reg,
        output_dir=tmp_path / "out-high-risk-allowlisted",
        strategy_names=["high_risk_success"],
        feature_flags=FeatureFlags(enable_high_risk=True, high_risk_allowlist=["high_risk_success"]),
        dataset_id="high-risk-allowlisted",
        git_ref="test",
    )

    assert [strategy["strategy_name"] for strategy in result["strategies"]] == ["high_risk_success"]


def test_build_strategy_result_raises_on_length_mismatch(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"fake")

    with pytest.raises(ValueError, match="length mismatch"):
        build_strategy_result(
            strategy_name="mismatch_case",
            outputs=[],
            image_paths=[img],
            track="core",
            status="candidate",
            promoted=False,
        )


def test_run_benchmark_adds_triad_comparison_when_all_present(tmp_path: Path) -> None:
    img = tmp_path / "triad.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(TriadThesisStrategy())
    reg.register(TriadAntithesisStrategy())
    reg.register(TriadSynthesisStrategy())

    result = run_benchmark(
        image_paths=[img],
        registry=reg,
        output_dir=tmp_path / "out-triad",
        dataset_id="triad-compare",
        git_ref="test",
    )

    triad = result["comparisons"]["thesis_antithesis_synthesis"]

    assert triad["available"] is True
    assert triad["cad_loadable_snapshot"] == {
        "thesis": {"count": 0, "rate": 0.0},
        "antithesis": {"count": 0, "rate": 0.0},
        "synthesis": {"count": 0, "rate": 0.0},
    }
    assert triad["cad_loadable_gate"] == {
        "synthesis_ge_thesis": True,
        "synthesis_ge_antithesis": True,
        "synthesis_ge_best_baseline_rate": True,
        "synthesis_ge_best_baseline_count": True,
        "passed": True,
    }
    assert triad["casewise_cad_loadable"] == {
        "aligned_case_count": 1,
        "all_three_loadable_count": 0,
        "all_three_unloadable_count": 1,
        "synthesis_rescue": {
            "vs_thesis_count": 0,
            "vs_antithesis_count": 0,
            "vs_both_baselines_count": 0,
        },
        "synthesis_regression": {
            "vs_thesis_count": 0,
            "vs_antithesis_count": 0,
            "vs_either_baseline_count": 0,
        },
    }
    assert triad["deltas"]["synthesis_vs_thesis"] == {
        "success_rate": 0.0,
        "cad_loadable_count": 0,
        "cad_loadable_rate": 0.0,
        "mean_iou": 0.15,
        "mean_topology_f1": 0.22,
        "median_elapsed_ms": 1.0,
    }
    assert triad["deltas"]["synthesis_vs_antithesis"] == {
        "success_rate": 0.0,
        "cad_loadable_count": 0,
        "cad_loadable_rate": 0.0,
        "mean_iou": 0.1,
        "mean_topology_f1": 0.07,
        "median_elapsed_ms": -1.0,
    }

    summary_payload = _load_summary_payload(tmp_path / "out-triad")
    assert summary_payload["triad_gate"] == {
        "available": True,
        "passed": True,
        "missing": [],
    }


def test_run_benchmark_triad_comparison_tracks_cad_loadable_gate(tmp_path: Path) -> None:
    class LoadableThesisStrategy(ConversionStrategy):
        name = "two_stage_baseline"

        def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
            output_dir.mkdir(parents=True, exist_ok=True)
            dxf_path = output_dir / f"{conv_input.image_path.stem}.dxf"
            ezdxf.new("R2018", setup=True).saveas(str(dxf_path))
            return ConversionOutput(
                strategy_name=self.name,
                dxf_path=dxf_path,
                success=True,
                elapsed_ms=10.0,
                metrics={"iou": 0.6, "topology_f1": 0.6},
                notes=[],
            )

    class LoadableAntithesisStrategy(ConversionStrategy):
        name = "consensus_qa"

        def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
            output_dir.mkdir(parents=True, exist_ok=True)
            dxf_path = output_dir / f"{conv_input.image_path.stem}.dxf"
            ezdxf.new("R2018", setup=True).saveas(str(dxf_path))
            return ConversionOutput(
                strategy_name=self.name,
                dxf_path=dxf_path,
                success=True,
                elapsed_ms=12.0,
                metrics={"iou": 0.6, "topology_f1": 0.6},
                notes=[],
            )

    class BrokenSynthesisStrategy(ConversionStrategy):
        name = "hybrid_mvp"

        def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
            output_dir.mkdir(parents=True, exist_ok=True)
            dxf_path = output_dir / f"{conv_input.image_path.stem}.dxf"
            dxf_path.write_text("broken", encoding="utf-8")
            return ConversionOutput(
                strategy_name=self.name,
                dxf_path=dxf_path,
                success=True,
                elapsed_ms=11.0,
                metrics={"iou": 0.6, "topology_f1": 0.6},
                notes=[],
            )

    img = tmp_path / "triad-loadability.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(LoadableThesisStrategy())
    reg.register(LoadableAntithesisStrategy())
    reg.register(BrokenSynthesisStrategy())

    result = run_benchmark(
        image_paths=[img],
        registry=reg,
        output_dir=tmp_path / "out-triad-loadability",
        dataset_id="triad-loadability",
        git_ref="test",
    )

    triad = result["comparisons"]["thesis_antithesis_synthesis"]

    assert triad["cad_loadable_snapshot"] == {
        "thesis": {"count": 1, "rate": 1.0},
        "antithesis": {"count": 1, "rate": 1.0},
        "synthesis": {"count": 0, "rate": 0.0},
    }
    assert triad["cad_loadable_gate"] == {
        "synthesis_ge_thesis": False,
        "synthesis_ge_antithesis": False,
        "synthesis_ge_best_baseline_rate": False,
        "synthesis_ge_best_baseline_count": False,
        "passed": False,
    }
    assert triad["casewise_cad_loadable"] == {
        "aligned_case_count": 1,
        "all_three_loadable_count": 0,
        "all_three_unloadable_count": 0,
        "synthesis_rescue": {
            "vs_thesis_count": 0,
            "vs_antithesis_count": 0,
            "vs_both_baselines_count": 0,
        },
        "synthesis_regression": {
            "vs_thesis_count": 1,
            "vs_antithesis_count": 1,
            "vs_either_baseline_count": 1,
        },
    }
    assert triad["deltas"]["synthesis_vs_thesis"]["cad_loadable_count"] == -1
    assert triad["deltas"]["synthesis_vs_antithesis"]["cad_loadable_count"] == -1

    summary_payload = _load_summary_payload(tmp_path / "out-triad-loadability")
    assert summary_payload["triad_gate"] == {
        "available": True,
        "passed": False,
        "missing": [],
    }


def test_run_benchmark_triad_casewise_reports_rescue_and_regression(tmp_path: Path) -> None:
    def write_dxf(path: Path, *, loadable: bool) -> None:
        if loadable:
            ezdxf.new("R2018", setup=True).saveas(str(path))
            return
        path.write_text("broken", encoding="utf-8")

    class SplitLoadableThesisStrategy(ConversionStrategy):
        name = "two_stage_baseline"

        def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
            output_dir.mkdir(parents=True, exist_ok=True)
            dxf_path = output_dir / f"{conv_input.image_path.stem}.dxf"
            write_dxf(dxf_path, loadable=conv_input.image_path.stem == "a")
            return ConversionOutput(
                strategy_name=self.name,
                dxf_path=dxf_path,
                success=True,
                elapsed_ms=10.0,
                metrics={"iou": 0.6, "topology_f1": 0.6},
                notes=[],
            )

    class SplitLoadableAntithesisStrategy(ConversionStrategy):
        name = "consensus_qa"

        def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
            output_dir.mkdir(parents=True, exist_ok=True)
            dxf_path = output_dir / f"{conv_input.image_path.stem}.dxf"
            write_dxf(dxf_path, loadable=conv_input.image_path.stem == "b")
            return ConversionOutput(
                strategy_name=self.name,
                dxf_path=dxf_path,
                success=True,
                elapsed_ms=12.0,
                metrics={"iou": 0.6, "topology_f1": 0.6},
                notes=[],
            )

    class SplitLoadableSynthesisStrategy(ConversionStrategy):
        name = "hybrid_mvp"

        def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
            output_dir.mkdir(parents=True, exist_ok=True)
            dxf_path = output_dir / f"{conv_input.image_path.stem}.dxf"
            write_dxf(dxf_path, loadable=conv_input.image_path.stem == "c")
            return ConversionOutput(
                strategy_name=self.name,
                dxf_path=dxf_path,
                success=True,
                elapsed_ms=11.0,
                metrics={"iou": 0.6, "topology_f1": 0.6},
                notes=[],
            )

    image_paths = [tmp_path / "a.png", tmp_path / "b.png", tmp_path / "c.png"]
    for image in image_paths:
        image.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(SplitLoadableThesisStrategy())
    reg.register(SplitLoadableAntithesisStrategy())
    reg.register(SplitLoadableSynthesisStrategy())

    result = run_benchmark(
        image_paths=image_paths,
        registry=reg,
        output_dir=tmp_path / "out-triad-casewise",
        dataset_id="triad-casewise",
        git_ref="test",
    )

    triad = result["comparisons"]["thesis_antithesis_synthesis"]

    assert triad["cad_loadable_gate"]["passed"] is True
    assert triad["casewise_cad_loadable"] == {
        "aligned_case_count": 3,
        "all_three_loadable_count": 0,
        "all_three_unloadable_count": 0,
        "synthesis_rescue": {
            "vs_thesis_count": 1,
            "vs_antithesis_count": 1,
            "vs_both_baselines_count": 1,
        },
        "synthesis_regression": {
            "vs_thesis_count": 1,
            "vs_antithesis_count": 1,
            "vs_either_baseline_count": 2,
        },
    }


def test_run_benchmark_marks_triad_comparison_unavailable_when_missing(tmp_path: Path) -> None:
    img = tmp_path / "triad-missing.png"
    img.write_bytes(b"fake")

    reg = StrategyRegistry()
    reg.register(SuccessStrategy())

    result = run_benchmark(
        image_paths=[img],
        registry=reg,
        output_dir=tmp_path / "out-triad-missing",
        dataset_id="triad-missing",
        git_ref="test",
    )

    triad = result["comparisons"]["thesis_antithesis_synthesis"]

    assert triad["available"] is False
    assert triad["missing"] == [
        "two_stage_baseline",
        "consensus_qa",
        "hybrid_mvp",
    ]


def test_run_benchmark_isolates_case_outputs_for_same_stem_images(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir(parents=True, exist_ok=True)
    right.mkdir(parents=True, exist_ok=True)

    image_a = left / "same.png"
    image_b = right / "same.png"
    image_a.write_bytes(b"image-a")
    image_b.write_bytes(b"image-b")

    class SameStemLoadabilityStrategy(ConversionStrategy):
        name = "same_stem_loadability"

        def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
            output_dir.mkdir(parents=True, exist_ok=True)
            dxf_path = output_dir / f"{conv_input.image_path.stem}.dxf"
            if conv_input.image_path.parent.name == "left":
                ezdxf.new("R2018", setup=True).saveas(str(dxf_path))
            else:
                dxf_path.write_text("broken", encoding="utf-8")

            return ConversionOutput(
                strategy_name=self.name,
                dxf_path=dxf_path,
                success=True,
                elapsed_ms=1.0,
                metrics={"iou": 0.5, "topology_f1": 0.5},
                notes=[],
            )

    reg = StrategyRegistry()
    reg.register(SameStemLoadabilityStrategy())

    result = run_benchmark(
        image_paths=[image_a, image_b],
        registry=reg,
        output_dir=tmp_path / "out-same-stem",
        dataset_id="same-stem",
        git_ref="test",
    )

    strategy_row = result["strategies"][0]
    cases = strategy_row["cases"]

    assert len(cases) == 2
    assert cases[0]["dxf_path"] != cases[1]["dxf_path"]
    assert cases[0]["cad_loadable"] is True
    assert cases[1]["cad_loadable"] is False
    assert strategy_row["summary"]["cad_loadable_count"] == 1
    assert strategy_row["summary"]["cad_loadable_rate"] == 0.5
