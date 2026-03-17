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


def test_two_stage_v101_moderate_skew_broad_relief_boosts_midband_pocket(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "moderate_skew_broad_relief.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Target pocket: moderate skew + low-mid texture + mild complexity.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=336, height=240, contrast=0.44, edge_density=0.17),
    )
    out_relief = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_relief")

    # Control: near-square geometry with comparable low-mid texture. The v101
    # moderate-skew pocket should not meaningfully activate here.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=246, height=240, contrast=0.44, edge_density=0.17),
    )
    out_control = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_control")

    assert out_relief.success is True
    assert _extract_offgrid_shift(out_relief.notes) > _extract_offgrid_shift(out_control.notes)
