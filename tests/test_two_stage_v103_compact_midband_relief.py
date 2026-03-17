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


def _extract_debias_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.rsplit("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_two_stage_v103_compact_midband_relief_boosts_low_skew_midband_pocket(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "compact_midband_relief.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Target pocket: compact geometry with mid complexity where corridor-heavy
    # relief terms under-fire but residual axis bundling still appears.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=252, height=240, contrast=0.70, edge_density=0.13),
    )
    out_relief = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_relief")

    assert out_relief.success is True
    assert _extract_offgrid_shift(out_relief.notes) == 0.065
    assert _extract_debias_chords(out_relief.notes) == 37
