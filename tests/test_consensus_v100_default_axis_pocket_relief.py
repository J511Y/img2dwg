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


def test_consensus_v100_default_axis_pocket_relief_lifts_mild_elongation_default_band(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v100_default_axis_pocket.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = ConsensusQAStrategy()

    # Relief-on pocket: mild elongation + low-mid texture + default consensus.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=350, height=250, contrast=0.60, edge_density=0.20),
    )
    out_relief = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.73}),
        tmp_path / "out_relief",
    )

    # Control: near-square geometry should keep v100 pocket lift inactive.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=290, height=260, contrast=0.60, edge_density=0.20),
    )
    out_control = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.73}),
        tmp_path / "out_control",
    )

    assert out_relief.success is True
    assert out_control.success is True
    assert _extract_debias_chords(out_relief.notes) > _extract_debias_chords(out_control.notes)
    assert _extract_offgrid_shift(out_relief.notes) > _extract_offgrid_shift(out_control.notes)
    assert _extract_diagonal_fan(out_relief.notes) > _extract_diagonal_fan(out_control.notes)
