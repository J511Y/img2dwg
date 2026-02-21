import math
from pathlib import Path

import pytest

from img2dwg.pipeline.benchmark import run_benchmark
from img2dwg.pipeline.schema import build_strategy_result
from img2dwg.strategies.base import ConversionInput, ConversionOutput, ConversionStrategy
from img2dwg.strategies.registry import StrategyRegistry


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
    assert result["ranking"][0]["strategy_name"] == "success"


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
    assert result.summary.median_elapsed_ms == 0.0
    assert result.summary.p95_elapsed_ms == 0.0
    assert result.summary.mean_iou == 0.0
    assert result.summary.mean_topology_f1 == 0.0


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
