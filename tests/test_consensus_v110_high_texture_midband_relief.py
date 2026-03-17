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
            return int(note.split("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_consensus_v110_high_texture_midband_relief_lifts_high_texture_midband_case(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v110_high_texture_midband.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = ConsensusQAStrategy()

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=278, height=220, contrast=0.62, edge_density=0.42),
    )
    out_relief = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.76}),
        tmp_path / "out_relief",
    )

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=278, height=220, contrast=0.60, edge_density=0.40),
    )
    out_control = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.76}),
        tmp_path / "out_control",
    )

    assert out_relief.success is True
    assert out_control.success is True
    assert _extract_debias_chords(out_relief.notes) > _extract_debias_chords(out_control.notes)
    assert _extract_offgrid_shift(out_relief.notes) > _extract_offgrid_shift(out_control.notes)
    assert _extract_diagonal_fan(out_relief.notes) >= _extract_diagonal_fan(out_control.notes)
