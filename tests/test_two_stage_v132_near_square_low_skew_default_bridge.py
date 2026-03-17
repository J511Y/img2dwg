from pathlib import Path

from PIL import Image

from img2dwg.strategies import two_stage
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy
from scripts.run_grid_artifact_regression import analyze_dxf


def test_two_stage_v132_near_square_low_skew_default_bridge_reduces_axis_bias(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "near_square_low_skew_default_bridge.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Gate-on pocket: near-square + default complexity + mid edge density.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=312, height=298, contrast=0.70, edge_density=0.22),
    )
    out_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_gate")

    # Move only edge density just below gate floor to disable v132 lift.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=312, height=298, contrast=0.70, edge_density=0.15),
    )
    out_no_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_no_gate")

    gate_diag = analyze_dxf(str(out_gate.dxf_path))
    no_gate_diag = analyze_dxf(str(out_no_gate.dxf_path))

    assert out_gate.success is True
    assert out_no_gate.success is True
    assert gate_diag.axis_aligned_line_ratio < no_gate_diag.axis_aligned_line_ratio
    assert gate_diag.unique_x_count > no_gate_diag.unique_x_count
    assert gate_diag.unique_y_count > no_gate_diag.unique_y_count
