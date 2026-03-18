from pathlib import Path

from PIL import Image

from img2dwg.strategies import two_stage
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


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


def test_two_stage_v151_midskew_default_band_coord_bridge_boosts_debias(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "two_stage_v151_midskew_default_band_coord_bridge.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # out-of-gate: keep aspect/complexity in-range, but edge density just
    # below the v151 lower bound so the bridge should stay off.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=136, height=100, contrast=0.61, edge_density=0.17),
    )
    out_no_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_no_gate")

    # in-gate: mild mid-skew + default-band complexity + slightly higher edge.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=136, height=100, contrast=0.57, edge_density=0.21),
    )
    out_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_gate")

    assert out_gate.success is True
    assert _extract_offgrid_shift(out_gate.notes) > _extract_offgrid_shift(out_no_gate.notes)
    assert _extract_diagonal_fan(out_gate.notes) > _extract_diagonal_fan(out_no_gate.notes)
    assert _extract_debias_chords(out_gate.notes) >= _extract_debias_chords(out_no_gate.notes)
