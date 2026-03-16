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


def test_two_stage_v92_mild_corridor_midband_relief_lifts_debias_and_shift(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "two_stage_v92_mild_corridor_midband.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Target pocket: mildly elongated + mid-band complexity where v92 should fire.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=244, height=186, contrast=0.52, edge_density=0.12),
    )
    out_relief = strategy.run(
        ConversionInput(image_path=image_path, metadata={}),
        tmp_path / "out_relief",
    )

    # Control: same shape but lower complexity where v92 should stay mostly inactive.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=244, height=186, contrast=0.38, edge_density=0.08),
    )
    out_control = strategy.run(
        ConversionInput(image_path=image_path, metadata={}),
        tmp_path / "out_control",
    )

    assert out_relief.success is True
    assert out_control.success is True
    assert _extract_debias_chords(out_relief.notes) > _extract_debias_chords(out_control.notes)
    assert _extract_offgrid_shift(out_relief.notes) > _extract_offgrid_shift(out_control.notes)
