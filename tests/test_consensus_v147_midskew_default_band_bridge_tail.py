from pathlib import Path

from PIL import Image

from img2dwg.strategies import consensus_qa
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy
from img2dwg.strategies.prototype_engine import ImageSignals


def _extract_v147_count(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("anti_grid_detail_diag:pair_v147_midskew_default_band_bridge_tail:"):
            return int(note.rsplit(":", maxsplit=1)[1])
    return 0


def test_consensus_v147_midskew_default_band_bridge_tail_adds_single_segment_in_gate(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v147_gate.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=210, height=120, contrast=0.54, edge_density=0.24),
    )

    out = ConsensusQAStrategy().run(
        ConversionInput(image_path=image_path, metadata={}),
        tmp_path / "out",
    )

    assert out.success is True
    assert _extract_v147_count(out.notes) == 1


def test_consensus_v147_midskew_default_band_bridge_tail_skips_outside_gate(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v147_off.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=126, height=120, contrast=0.54, edge_density=0.24),
    )

    out = ConsensusQAStrategy().run(
        ConversionInput(image_path=image_path, metadata={}),
        tmp_path / "out_off",
    )

    assert out.success is True
    assert _extract_v147_count(out.notes) == 0
