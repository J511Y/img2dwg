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
    # v58 tuned ceiling should push above the previous 42-ish range.
    assert _extract_chords(out.notes) >= 48
