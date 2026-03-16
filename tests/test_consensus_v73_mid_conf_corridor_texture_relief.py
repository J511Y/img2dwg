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


def test_consensus_v73_mid_conf_corridor_texture_relief_boosts_elongated_mid_confidence_layouts(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v73_mid_conf.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = ConsensusQAStrategy()

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=420, height=220, contrast=0.64, edge_density=0.48),
    )
    out_relief = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.74}),
        tmp_path / "out_relief",
    )

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=340, height=220, contrast=0.64, edge_density=0.48),
    )
    out_near = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.74}),
        tmp_path / "out_near",
    )

    assert out_relief.success is True
    assert out_near.success is True
    assert _extract_debias_chords(out_relief.notes) > _extract_debias_chords(out_near.notes)
    assert _extract_offgrid_shift(out_relief.notes) > _extract_offgrid_shift(out_near.notes)
