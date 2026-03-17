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


def _extract_diagonal_fan(notes: list[str]) -> float:
    for note in notes:
        if note.startswith("diagonal_fan:"):
            return float(note.split(":", maxsplit=1)[1])
    raise AssertionError("diagonal_fan note missing")


def test_two_stage_v112_mid_skew_texture_bridge_relief_adds_bounded_lift(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "mid_skew_texture_bridge_relief.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Same mid-skew + mid/high texture pocket, but below edge-density gate.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=242, height=180, contrast=0.84, edge_density=0.09),
    )
    out_no_relief = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_no_relief")

    # Cross the edge gate so v112 activates while preserving the same geometry.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=242, height=180, contrast=0.84, edge_density=0.20),
    )
    out_relief = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_relief")

    assert out_relief.success is True
    assert _extract_offgrid_shift(out_relief.notes) > _extract_offgrid_shift(out_no_relief.notes)
    assert _extract_diagonal_fan(out_relief.notes) > _extract_diagonal_fan(out_no_relief.notes)
