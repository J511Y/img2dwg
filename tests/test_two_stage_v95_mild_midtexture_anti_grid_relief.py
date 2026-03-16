from pathlib import Path

from PIL import Image

from img2dwg.strategies import two_stage
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def _extract_debias_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.split("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def _extract_offgrid_shift(notes: list[str]) -> float:
    for note in notes:
        if note.startswith("offgrid_shift:"):
            return float(note.split(":", maxsplit=1)[1])
    raise AssertionError("offgrid_shift note missing")


def test_two_stage_v95_mild_midtexture_anti_grid_relief_targets_narrow_midband_pocket(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "mild_midtexture_anti_grid_relief.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Relief-active pocket: mild elongation + low-mid texture complexity.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=420, height=300, contrast=0.40, edge_density=0.10),
    )
    out_relief = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_relief")

    assert out_relief.success is True
    # Keep this pocket above baseline debias floor so narrow-band anti-grid
    # relief remains active for mild-elongation mid-texture cases.
    assert _extract_debias_chords(out_relief.notes) >= 31
    assert _extract_offgrid_shift(out_relief.notes) > 0.060
