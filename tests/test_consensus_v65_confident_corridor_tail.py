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


def test_consensus_v65_confident_corridor_tail_boosts_debias(monkeypatch, tmp_path: Path) -> None:
    def _fake_signals(_image_path: Path) -> ImageSignals:
        return ImageSignals(width=500, height=200, contrast=0.92, edge_density=0.9)

    monkeypatch.setattr(consensus_qa, "extract_image_signals", _fake_signals)

    image_path = tmp_path / "stub.png"
    image_path.write_bytes(b"stub")

    strategy = ConsensusQAStrategy()
    out_mid_conf = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.84}),
        tmp_path / "out_mid_conf",
    )
    out_high_conf = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.9}),
        tmp_path / "out_high_conf",
    )

    assert _extract_offgrid_shift(out_high_conf.notes) > _extract_offgrid_shift(out_mid_conf.notes)
    assert _extract_diagonal_fan(out_high_conf.notes) > _extract_diagonal_fan(out_mid_conf.notes)
