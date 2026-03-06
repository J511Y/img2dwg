from __future__ import annotations

# mypy: disable-error-code=import-untyped
from pathlib import Path

from img2dwg.pipeline.benchmark import run_benchmark
from img2dwg.strategies.base import ConversionInput, ConversionOutput, ConversionStrategy
from img2dwg.strategies.registry import StrategyRegistry


class RecordingStrategy(ConversionStrategy):
    name = "recording"

    def __init__(self) -> None:
        self.output_dirs: list[Path] = []

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        self.output_dirs.append(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        dxf_path = output_dir / "result.dxf"
        dxf_path.write_text(conv_input.image_path.name, encoding="utf-8")
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=dxf_path,
            success=True,
            elapsed_ms=0.0,
            metrics={},
            notes=[],
        )


def test_run_benchmark_uses_collision_safe_case_output_dirs(tmp_path: Path) -> None:
    image_a = tmp_path / "images" / "x" / "a.png"
    image_b = tmp_path / "images" / "y" / "a.png"
    image_a.parent.mkdir(parents=True)
    image_b.parent.mkdir(parents=True)
    image_a.write_bytes(b"img")
    image_b.write_bytes(b"img")

    strategy = RecordingStrategy()
    registry = StrategyRegistry()
    registry.register(strategy)

    run_benchmark(
        image_paths=[image_a, image_b],
        registry=registry,
        output_dir=tmp_path / "out",
    )

    assert len(strategy.output_dirs) == 2
    assert strategy.output_dirs[0] != strategy.output_dirs[1]
    assert strategy.output_dirs[0].name.startswith("0000-")
    assert strategy.output_dirs[1].name.startswith("0001-")
