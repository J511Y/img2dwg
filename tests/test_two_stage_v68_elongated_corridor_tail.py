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


def test_two_stage_v68_elongated_corridor_tail_lifts_debias(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "elongated_corridor.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Same complexity, higher aspect ratio should receive extra elongated-tail lift.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=600, height=200, contrast=0.56, edge_density=0.34),
    )
    out_elongated = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_elongated")

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=440, height=220, contrast=0.56, edge_density=0.34),
    )
    out_mid = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_mid")

    assert out_elongated.success is True
    assert out_mid.success is True
    assert _extract_debias_chords(out_elongated.notes) > _extract_debias_chords(out_mid.notes)
    assert _extract_offgrid_shift(out_elongated.notes) > _extract_offgrid_shift(out_mid.notes)
