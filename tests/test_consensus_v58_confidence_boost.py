from pathlib import Path

from img2dwg.strategies import consensus_qa
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy


def _extract_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.split("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_consensus_v58_high_confidence_complexity_lifts_debias(monkeypatch, tmp_path: Path) -> None:
    def _fake_signals(_image_path: Path) -> ImageSignals:
        return ImageSignals(width=180, height=140, contrast=1.0, edge_density=1.0)

    monkeypatch.setattr(consensus_qa, "extract_image_signals", _fake_signals)

    image_path = tmp_path / "stub.png"
    image_path.write_bytes(b"stub")

    out = ConsensusQAStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.95}),
        tmp_path / "out",
    )

    assert out.success is True
    # v59 tuned ceiling includes additional aspect-skew lift.
    assert _extract_chords(out.notes) >= 50


def test_consensus_v59_elongated_floorplan_gets_extra_debias(monkeypatch, tmp_path: Path) -> None:
    calls: list[ImageSignals] = [
        ImageSignals(width=200, height=200, contrast=0.9, edge_density=0.9),
        ImageSignals(width=300, height=120, contrast=0.9, edge_density=0.9),
    ]

    def _fake_signals(_image_path: Path) -> ImageSignals:
        return calls.pop(0)

    monkeypatch.setattr(consensus_qa, "extract_image_signals", _fake_signals)

    image_path = tmp_path / "stub.png"
    image_path.write_bytes(b"stub")

    strategy = ConsensusQAStrategy()
    out_square = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.88}),
        tmp_path / "out_square",
    )
    out_elongated = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.88}),
        tmp_path / "out_elongated",
    )

    assert _extract_chords(out_elongated.notes) > _extract_chords(out_square.notes)


def test_consensus_v62_corridor_skew_gets_extra_decollapse_bonus(monkeypatch, tmp_path: Path) -> None:
    calls: list[ImageSignals] = [
        ImageSignals(width=320, height=200, contrast=0.92, edge_density=0.9),
        ImageSignals(width=420, height=180, contrast=0.92, edge_density=0.9),
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
    out_corridor = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.9}),
        tmp_path / "out_corridor",
    )

    assert _extract_chords(out_corridor.notes) > _extract_chords(out_wide.notes)
