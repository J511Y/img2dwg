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


def test_consensus_v140_midskew_dense_consensus_bridge_lifts_offgrid_shift(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v140_midskew_dense_consensus_bridge.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = ConsensusQAStrategy()

    # Out-of-gate: edge density just below v140 lower bound.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=146, height=100, contrast=0.60, edge_density=0.17),
    )
    out_no_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_no_gate")

    # In-gate: midskew + moderate complexity + moderate edge density.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=146, height=100, contrast=0.60, edge_density=0.23),
    )
    out_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_gate")

    assert out_gate.success is True
    assert out_no_gate.success is True
    assert _extract_offgrid_shift(out_gate.notes) > _extract_offgrid_shift(out_no_gate.notes)
