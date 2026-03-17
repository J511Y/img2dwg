from pathlib import Path

from PIL import Image

from img2dwg.strategies import two_stage
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy
from scripts.run_grid_artifact_regression import analyze_dxf


def _extract_offgrid_shift(notes: list[str]) -> float:
    for note in notes:
        if note.startswith("offgrid_shift:"):
            return float(note.split(":", maxsplit=1)[1])
    raise AssertionError("offgrid_shift note missing")


def _extract_diagonal_fan(notes: list[str]) -> float:
    for note in notes:
        if note.startswith("diagonal_fan:"):
            return float(note.split(":", maxsplit=1)[1])
    raise AssertionError("diagonal_fan note missing")


def _extract_debias_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.rsplit("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_two_stage_v117_near_square_default_band_gate_reduces_axis_bias(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "near_square_default_band_gate.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Gate-on sample: near-square + default-band complexity + low-mid edge.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=254, height=250, contrast=0.73, edge_density=0.18),
    )
    out_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_gate")

    # Keep aspect fixed, but move just beyond the edge ceiling while preserving
    # the same complexity band so the new near-square gate turns off.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=254, height=250, contrast=0.64, edge_density=0.24),
    )
    out_no_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_no_gate")

    gate_diag = analyze_dxf(str(out_gate.dxf_path))
    no_gate_diag = analyze_dxf(str(out_no_gate.dxf_path))

    assert out_gate.success is True
    assert out_no_gate.success is True
    assert _extract_debias_chords(out_gate.notes) > _extract_debias_chords(out_no_gate.notes)
    assert _extract_offgrid_shift(out_gate.notes) > _extract_offgrid_shift(out_no_gate.notes)
    assert _extract_diagonal_fan(out_gate.notes) > _extract_diagonal_fan(out_no_gate.notes)
    assert gate_diag.axis_aligned_line_ratio < no_gate_diag.axis_aligned_line_ratio
    assert gate_diag.unique_x_count > no_gate_diag.unique_x_count
    assert gate_diag.unique_y_count > no_gate_diag.unique_y_count
