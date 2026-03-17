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
            return int(note.split("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_two_stage_v136_default_band_anti_grid_gate(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "two_stage_default_band_anti_grid.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=136, height=100, contrast=0.30, edge_density=0.20),
    )

    out = TwoStageBaselineStrategy().run(
        ConversionInput(image_path=image_path, metadata={}),
        tmp_path / "out",
    )

    assert out.success is True
    # v136 default-band anti-grid guard should keep this pocket above the
    # previous floor and preserve enough debias chords.
    assert _extract_offgrid_shift(out.notes) >= 0.063
    assert _extract_debias_chords(out.notes) >= 34
