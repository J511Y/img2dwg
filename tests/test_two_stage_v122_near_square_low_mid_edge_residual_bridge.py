from pathlib import Path

from PIL import Image

from img2dwg.strategies import two_stage
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy
from scripts.run_grid_artifact_regression import analyze_dxf


def _extract_debias_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.rsplit("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_two_stage_v122_near_square_low_mid_edge_residual_bridge_improves_degrid(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "near_square_low_mid_edge_residual_bridge.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Gate-on: near-square, low/mid edge, mid complexity pocket.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=308, height=276, contrast=0.66, edge_density=0.24),
    )
    out_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_gate")

    # Gate-off: keep geometry/complexity similar but edge above fallback band.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=308, height=276, contrast=0.66, edge_density=0.32),
    )
    out_no_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_no_gate")

    gate_diag = analyze_dxf(str(out_gate.dxf_path))
    no_gate_diag = analyze_dxf(str(out_no_gate.dxf_path))

    assert out_gate.success is True
    assert out_no_gate.success is True
    assert _extract_debias_chords(out_gate.notes) > _extract_debias_chords(out_no_gate.notes)
    assert gate_diag.axis_aligned_line_ratio < no_gate_diag.axis_aligned_line_ratio
    assert gate_diag.unique_x_count > no_gate_diag.unique_x_count
    assert gate_diag.unique_y_count > no_gate_diag.unique_y_count
