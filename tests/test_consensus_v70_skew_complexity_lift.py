from pathlib import Path

from img2dwg.strategies import consensus_qa
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy
from img2dwg.strategies.prototype_engine import ImageSignals


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


def test_consensus_v70_skew_complexity_interaction_boost(monkeypatch, tmp_path: Path) -> None:
    # Same consensus, same complexity; only elongated geometry should receive
    # additional skew×complexity interaction lift.
    def _high_skew(_image_path: Path) -> ImageSignals:
        return ImageSignals(width=520, height=240, contrast=0.88, edge_density=0.86)

    def _low_skew(_image_path: Path) -> ImageSignals:
        return ImageSignals(width=320, height=260, contrast=0.88, edge_density=0.86)

    image_path = tmp_path / "stub.png"
    image_path.write_bytes(b"stub")

    strategy = ConsensusQAStrategy()

    monkeypatch.setattr(consensus_qa, "extract_image_signals", _low_skew)
    out_low_skew = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.80}),
        tmp_path / "out_low_skew",
    )

    monkeypatch.setattr(consensus_qa, "extract_image_signals", _high_skew)
    out_high_skew = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.80}),
        tmp_path / "out_high_skew",
    )

    assert _extract_offgrid_shift(out_high_skew.notes) > _extract_offgrid_shift(out_low_skew.notes)
    assert _extract_diagonal_fan(out_high_skew.notes) > _extract_diagonal_fan(out_low_skew.notes)
