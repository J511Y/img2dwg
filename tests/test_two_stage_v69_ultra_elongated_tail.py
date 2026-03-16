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


def test_two_stage_v69_ultra_elongated_tail_boosts_debias(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "ultra_elongated.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Keep complexity equal; only ultra-elongated aspect should trigger extra tail lift.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=720, height=220, contrast=0.56, edge_density=0.34),
    )
    out_ultra = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_ultra")

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=560, height=220, contrast=0.56, edge_density=0.34),
    )
    out_elongated = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_elongated")

    assert out_ultra.success is True
    assert out_elongated.success is True
    assert _extract_debias_chords(out_ultra.notes) > _extract_debias_chords(out_elongated.notes)
    assert _extract_offgrid_shift(out_ultra.notes) > _extract_offgrid_shift(out_elongated.notes)
