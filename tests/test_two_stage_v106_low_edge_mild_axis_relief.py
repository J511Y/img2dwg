from pathlib import Path

from PIL import Image

from img2dwg.strategies import two_stage
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def _extract_debias_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.rsplit("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_two_stage_v106_low_edge_mild_axis_relief_adds_tiny_bounded_lift(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "low_edge_mild_axis_relief.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=250, height=200, contrast=0.50, edge_density=0.32),
    )
    low_edge = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out-low")

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=250, height=200, contrast=0.38, edge_density=0.40),
    )
    high_edge = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out-high")

    assert low_edge.success is True
    assert high_edge.success is True
    assert _extract_debias_chords(low_edge.notes) == _extract_debias_chords(high_edge.notes) + 1
