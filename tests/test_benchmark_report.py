from pathlib import Path

from img2dwg.pipeline.benchmark import run_benchmark
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
