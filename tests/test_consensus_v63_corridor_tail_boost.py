from pathlib import Path

from img2dwg.strategies import consensus_qa
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy
from img2dwg.strategies.prototype_engine import ImageSignals


def _extract_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.split("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


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


def test_consensus_v63_corridor_tail_boosts_non_axis_controls(monkeypatch, tmp_path: Path) -> None:
    calls: list[ImageSignals] = [
        ImageSignals(width=320, height=190, contrast=0.92, edge_density=0.9),
        ImageSignals(width=460, height=180, contrast=0.92, edge_density=0.9),
    ]

    def _fake_signals(_image_path: Path) -> ImageSignals:
        return calls.pop(0)

    monkeypatch.setattr(consensus_qa, "extract_image_signals", _fake_signals)

    image_path = tmp_path / "stub.png"
    image_path.write_bytes(b"stub")

    strategy = ConsensusQAStrategy()
    out_wide = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.9}),
        tmp_path / "out_wide",
    )
    out_corridor_tail = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.9}),
        tmp_path / "out_corridor_tail",
    )

    assert _extract_chords(out_corridor_tail.notes) > _extract_chords(out_wide.notes)
    assert _extract_offgrid_shift(out_corridor_tail.notes) > _extract_offgrid_shift(out_wide.notes)
    assert _extract_diagonal_fan(out_corridor_tail.notes) > _extract_diagonal_fan(out_wide.notes)
