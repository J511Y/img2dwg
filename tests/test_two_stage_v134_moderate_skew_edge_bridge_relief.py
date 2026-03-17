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


def test_two_stage_v134_moderate_skew_edge_bridge_relief_lifts_midband_edge_case(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "moderate_skew_edge_bridge.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Keep aspect/contrast fixed in the moderate-skew midband pocket, then
    # cross the edge-density gate so v134 adds a tiny relief lift.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=236, height=180, contrast=0.60, edge_density=0.12),
    )
    out_low_edge = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_low_edge")

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=236, height=180, contrast=0.60, edge_density=0.26),
    )
    out_high_edge = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_high_edge")

    assert out_high_edge.success is True
    assert _extract_offgrid_shift(out_high_edge.notes) > _extract_offgrid_shift(out_low_edge.notes)
    assert _extract_diagonal_fan(out_high_edge.notes) > _extract_diagonal_fan(out_low_edge.notes)
