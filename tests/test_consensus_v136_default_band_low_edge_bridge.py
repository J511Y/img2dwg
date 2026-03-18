from pathlib import Path

from PIL import Image

from img2dwg.strategies import consensus_qa
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy


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


def test_consensus_v136_default_band_low_edge_bridge_lifts_moderate_skew_low_edge_pocket(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_default_band_low_edge_bridge.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = ConsensusQAStrategy()

    # control: same skew/complexity/score pocket with edge density just above the new gate
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=178, height=130, contrast=0.503, edge_density=0.25),
    )
    out_no_gate = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.73}),
        tmp_path / "out_no_gate",
    )

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=178, height=130, contrast=0.60, edge_density=0.18),
    )
    out_gate = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.73}),
        tmp_path / "out_gate",
    )

    assert out_gate.success is True
    assert _extract_offgrid_shift(out_gate.notes) > _extract_offgrid_shift(out_no_gate.notes)
    assert _extract_diagonal_fan(out_gate.notes) >= _extract_diagonal_fan(out_no_gate.notes)
