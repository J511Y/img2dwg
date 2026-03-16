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


def test_two_stage_v96_mild_corridor_midtexture_relief_expands_v95_pocket(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "mild_corridor_midtexture_relief.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Target pocket (mild corridor + low-mid texture): v96 should activate.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=395, height=295, contrast=0.47, edge_density=0.17),
    )
    out_relief = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_relief")

    # Nearby control below the v96 complexity floor: new term should be off.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=395, height=295, contrast=0.30, edge_density=0.05),
    )
    out_control = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_control")

    assert out_relief.success is True
    assert _extract_debias_chords(out_relief.notes) >= _extract_debias_chords(out_control.notes)
    assert _extract_offgrid_shift(out_relief.notes) > _extract_offgrid_shift(out_control.notes)
