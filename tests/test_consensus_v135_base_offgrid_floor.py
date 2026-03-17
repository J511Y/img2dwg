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


def test_consensus_v135_base_offgrid_floor_raised_for_mid_consensus(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "consensus_base_floor.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    # Keep bonus terms near zero so the base offgrid floor dominates.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=200, height=200, contrast=0.05, edge_density=0.05),
    )

    out = ConsensusQAStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.70}),
        tmp_path / "out",
    )

    assert out.success is True
    # v135 floor bump: base preset offgrid should now clear 0.060 even in a
    # near-zero bonus setup.
    assert _extract_offgrid_shift(out.notes) > 0.060
