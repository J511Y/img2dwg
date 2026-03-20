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


def test_two_stage_v154_high_edge_moderate_complexity_axis_unlock_lifts_offgrid_shift(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "two_stage_v154_high_edge_moderate_complexity_axis_unlock.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Out-of-gate: edge density just below v154 lower bound.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=132, height=100, contrast=0.50, edge_density=0.27),
    )
    out_no_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_no_gate")

    # In-gate: mild-to-mid skew + moderate complexity + high-edge pocket.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=132, height=100, contrast=0.50, edge_density=0.30),
    )
    out_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_gate")

    assert out_gate.success is True
    assert out_no_gate.success is True
    assert _extract_offgrid_shift(out_gate.notes) > _extract_offgrid_shift(out_no_gate.notes)
