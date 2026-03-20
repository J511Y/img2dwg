from pathlib import Path

from PIL import Image

from img2dwg.strategies import two_stage
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def test_two_stage_v163_high_contrast_midskew_axis_escape_relay_injects_note(
    monkeypatch,
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "two_stage_v163_high_contrast_midskew_axis_escape_relay.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Out-of-gate: contrast below the expanded relay lower bound.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=160, height=100, contrast=0.64, edge_density=0.18),
    )
    out_no_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_no_gate")

    # In-gate: midskew + high contrast + default-band complexity should trigger v163.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=160, height=100, contrast=0.74, edge_density=0.18),
    )
    out_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_gate")

    assert out_gate.success is True
    assert not any("pair_v163_high_contrast_midskew_axis_escape_relay" in n for n in out_no_gate.notes)
    assert any("pair_v163_high_contrast_midskew_axis_escape_relay" in n for n in out_gate.notes)
