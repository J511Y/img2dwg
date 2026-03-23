from pathlib import Path

from PIL import Image

from img2dwg.strategies import consensus_qa
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy


def _extract_v165_count(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("anti_grid_detail_diag:pair_v165_default_band_axis_escape_pairs:"):
            return int(note.rsplit(":", maxsplit=1)[1])
    return 0


def test_consensus_v165_default_band_axis_escape_pairs_adds_two_pairs_in_gate(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v165_axis_escape_pairs.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=168, height=116, contrast=0.56, edge_density=0.22),
    )

    out = ConsensusQAStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.72}),
        tmp_path / "out",
    )

    assert out.success is True
    assert _extract_v165_count(out.notes) == 2


def test_consensus_v165_default_band_axis_escape_pairs_skips_outside_gate(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v165_axis_escape_pairs_skip.png"
    Image.new("RGB", (24, 24), color="white").save(image_path)

    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=96, height=96, contrast=0.56, edge_density=0.22),
    )

    out = ConsensusQAStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.72}),
        tmp_path / "out_skip",
    )

    assert out.success is True
    assert _extract_v165_count(out.notes) == 0
