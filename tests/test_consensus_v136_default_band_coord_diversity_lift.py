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


def _extract_debias_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.rsplit("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_consensus_v136_default_band_coord_diversity_lift_boosts_debias(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_default_band_coord_diversity.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = ConsensusQAStrategy()

    # out-of-gate: same geometry/consensus but complexity below v136 lower bound.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=176, height=128, contrast=0.26, edge_density=0.08),
    )
    out_no_gate = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.71}),
        tmp_path / "out_no_gate",
    )

    # in-gate: default consensus + mild/moderate skew + mid complexity.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=176, height=128, contrast=0.56, edge_density=0.14),
    )
    out_gate = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.71}),
        tmp_path / "out_gate",
    )

    assert out_gate.success is True
    assert _extract_debias_chords(out_gate.notes) > _extract_debias_chords(out_no_gate.notes)
    assert _extract_offgrid_shift(out_gate.notes) > _extract_offgrid_shift(out_no_gate.notes)
    assert _extract_diagonal_fan(out_gate.notes) > _extract_diagonal_fan(out_no_gate.notes)
