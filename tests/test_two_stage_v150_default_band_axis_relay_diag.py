from pathlib import Path

from PIL import Image

from img2dwg.strategies import two_stage
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def _extract_v150_count(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("anti_grid_detail_diag:pair_v150_default_band_axis_relay_diag:"):
            return int(note.rsplit(":", maxsplit=1)[1])
    return 0


def test_two_stage_v150_default_band_axis_relay_diag_adds_single_segment_in_gate(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "two_stage_v150_gate.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=182, height=120, contrast=0.54, edge_density=0.22),
    )

    out = TwoStageBaselineStrategy().run(
        ConversionInput(image_path=image_path, metadata={}),
        tmp_path / "out",
    )

    assert out.success is True
    assert _extract_v150_count(out.notes) == 1


def test_two_stage_v150_default_band_axis_relay_diag_skips_outside_gate(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "two_stage_v150_off.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=136, height=120, contrast=0.44, edge_density=0.36),
    )

    out = TwoStageBaselineStrategy().run(
        ConversionInput(image_path=image_path, metadata={}),
        tmp_path / "out_off",
    )

    assert out.success is True
    assert _extract_v150_count(out.notes) == 0
