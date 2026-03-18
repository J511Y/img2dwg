from pathlib import Path

from PIL import Image

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


def _extract_debias_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.rsplit("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_consensus_v139_high_midskew_default_band_tail_unlock_boosts_debias(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v139_high_midskew_default_band_tail_unlock.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = ConsensusQAStrategy()

    # out-of-gate: aspect ratio just below v139 lower bound while preserving
    # default-band complexity (0.42*contrast + 0.58*edge = 0.35).
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=177, height=100, contrast=0.58, edge_density=0.18),
    )
    out_no_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_no_gate")

    # in-gate: high mid-skew + default-band complexity should trigger v139.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=188, height=100, contrast=0.58, edge_density=0.18),
    )
    out_gate = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_gate")

    assert out_gate.success is True
    assert _extract_debias_chords(out_gate.notes) > _extract_debias_chords(out_no_gate.notes)
    assert _extract_offgrid_shift(out_gate.notes) > _extract_offgrid_shift(out_no_gate.notes)
    assert _extract_diagonal_fan(out_gate.notes) > _extract_diagonal_fan(out_no_gate.notes)
