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


def test_two_stage_v71_skew_texture_tail_lift_targets_extreme_corridors(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "skew_texture.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=520, height=180, contrast=0.58, edge_density=0.42),
    )
    out_extreme = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_extreme")

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=430, height=180, contrast=0.58, edge_density=0.42),
    )
    out_moderate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_moderate")

    assert out_extreme.success is True
    assert out_moderate.success is True
    assert _extract_debias_chords(out_extreme.notes) > _extract_debias_chords(out_moderate.notes)
    assert _extract_offgrid_shift(out_extreme.notes) > _extract_offgrid_shift(out_moderate.notes)
