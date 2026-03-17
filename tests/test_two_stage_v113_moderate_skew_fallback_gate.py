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


def test_two_stage_v113_moderate_skew_fallback_gate_adds_tiny_lift(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "moderate_skew_fallback_gate.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = TwoStageBaselineStrategy()

    # Keep complexity in the fallback band, just below aspect gate.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=198, height=180, contrast=0.84, edge_density=0.22),
    )
    out_no_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_no_gate")

    # Cross aspect gate while preserving complexity band so v113 activates.
    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=216, height=180, contrast=0.84, edge_density=0.22),
    )
    out_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_gate")

    assert out_gate.success is True
    assert _extract_offgrid_shift(out_gate.notes) > _extract_offgrid_shift(out_no_gate.notes)
    assert _extract_diagonal_fan(out_gate.notes) > _extract_diagonal_fan(out_no_gate.notes)
