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


def test_two_stage_v119_near_square_broad_bridge_gate_reduces_axis_bias(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "near_square_broad_bridge_gate.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Gate-on sample: near-square + default/mid complexity + edge inside v119
    # broad bridge band. Keep edge above v118 ceiling so this test validates
    # the new bridge term.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=288, height=240, contrast=0.52, edge_density=0.33),
    )
    out_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_gate")

    # Keep geometry/complexity in a similar pocket but move edge below v119's
    # floor so the new broad bridge gate turns off.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=288, height=240, contrast=0.82, edge_density=0.13),
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
