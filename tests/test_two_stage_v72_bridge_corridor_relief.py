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


def test_two_stage_v72_bridge_corridor_relief_boosts_moderate_elongated_dense_layouts(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "bridge_corridor.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=430, height=220, contrast=0.61, edge_density=0.44),
    )
    out_bridge = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_bridge")

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=360, height=220, contrast=0.61, edge_density=0.44),
    )
    out_near = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_near")

    assert out_bridge.success is True
    assert out_near.success is True
    assert _extract_debias_chords(out_bridge.notes) > _extract_debias_chords(out_near.notes)
    assert _extract_offgrid_shift(out_bridge.notes) > _extract_offgrid_shift(out_near.notes)
