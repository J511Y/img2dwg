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


def test_two_stage_v90_midskew_default_pocket_relief_increases_debias(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "two_stage_v90_midskew_default_pocket.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Target pocket: mildly elongated + low/mid complexity where v90 should fire.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=272, height=206, contrast=0.44, edge_density=0.06),
    )
    out_relief = strategy.run(
        ConversionInput(image_path=image_path, metadata={}),
        tmp_path / "out_relief",
    )

    # Control pocket: similar shape but lower complexity where v90 should not fire.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=272, height=206, contrast=0.30, edge_density=0.04),
    )
    out_control = strategy.run(
        ConversionInput(image_path=image_path, metadata={}),
        tmp_path / "out_control",
    )

    assert out_relief.success is True
    assert out_control.success is True
    assert _extract_debias_chords(out_relief.notes) > _extract_debias_chords(out_control.notes)
