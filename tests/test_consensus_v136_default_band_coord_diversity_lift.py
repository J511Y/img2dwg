from pathlib import Path

from PIL import Image

from img2dwg.strategies import consensus_qa
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy


def _has_v136_note(notes: list[str]) -> bool:
    return any(note.startswith("anti_grid_detail_diag:tetra_v136_default_band_coord_diversity:") for note in notes)


def _extract_v136_count(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("anti_grid_detail_diag:tetra_v136_default_band_coord_diversity:"):
            return int(note.rsplit(":", maxsplit=1)[1])
    raise AssertionError("v136 detail note missing")


def test_consensus_v136_default_band_coord_diversity_lift_adds_micro_segments(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_default_band_coord_diversity.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    strategy = ConsensusQAStrategy()

    # out-of-gate: edge_density below v136 floor.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=176, height=128, contrast=0.56, edge_density=0.08),
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
    assert _has_v136_note(out_no_gate.notes) is False
    assert _has_v136_note(out_gate.notes) is True
    assert _extract_v136_count(out_gate.notes) == 4
