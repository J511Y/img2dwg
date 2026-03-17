from pathlib import Path

from PIL import Image

from img2dwg.strategies import consensus_qa
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy
from img2dwg.strategies.prototype_engine import ImageSignals


def _extract(notes: list[str], key: str) -> float:
    for note in notes:
        if note.startswith(f"{key}:"):
            return float(note.split(":", maxsplit=1)[1])
    raise AssertionError(f"{key} note missing")


def _extract_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.split("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_consensus_v134_near_square_midedge_bridge_gate_lifts_debias(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v134_near_square_midedge_bridge.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = ConsensusQAStrategy()

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=236, height=220, contrast=0.74, edge_density=0.28),
    )
    gate_on = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.72}),
        tmp_path / "gate_on",
    )

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=236, height=220, contrast=0.74, edge_density=0.18),
    )
    gate_off = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.72}),
        tmp_path / "gate_off",
    )

    assert gate_on.success is True
    assert gate_off.success is True
    assert _extract_chords(gate_on.notes) > _extract_chords(gate_off.notes)
    assert _extract(gate_on.notes, "offgrid_shift") > _extract(gate_off.notes, "offgrid_shift")
    assert _extract(gate_on.notes, "diagonal_fan") > _extract(gate_off.notes, "diagonal_fan")
