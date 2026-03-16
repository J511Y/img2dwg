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


def _extract_debias_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.split("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_consensus_v75_skew_complexity_interaction_lifts_elongated_dense_layouts(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v75_skew_complexity.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = ConsensusQAStrategy()

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=420, height=220, contrast=0.70, edge_density=0.56),
    )
    out_high = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.84}),
        tmp_path / "out_high",
    )

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=300, height=220, contrast=0.54, edge_density=0.44),
    )
    out_low = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.84}),
        tmp_path / "out_low",
    )

    assert out_high.success is True
    assert out_low.success is True
    assert _extract_debias_chords(out_high.notes) > _extract_debias_chords(out_low.notes)
    assert _extract_offgrid_shift(out_high.notes) > _extract_offgrid_shift(out_low.notes)
