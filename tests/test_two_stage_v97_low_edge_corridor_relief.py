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


def test_two_stage_v97_low_edge_corridor_relief_boosts_mild_elongation_low_edge_pocket(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "low_edge_corridor_relief.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Target pocket: mild elongation + low edge density + mid complexity.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=356, height=270, contrast=0.53, edge_density=0.16),
    )
    out_relief = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_relief")

    # Control: same geometry and near-matched complexity, but edge density above
    # the v97 cap so only the new low-edge term is suppressed.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=356, height=270, contrast=0.365, edge_density=0.27),
    )
    out_control = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_control")

    assert out_relief.success is True
    assert _extract_debias_chords(out_relief.notes) >= _extract_debias_chords(out_control.notes)
