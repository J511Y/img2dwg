from pathlib import Path

from PIL import Image

from img2dwg.strategies import consensus_qa
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy
from img2dwg.strategies.prototype_engine import ImageSignals
from scripts.run_grid_artifact_regression import analyze_dxf


def _extract_debias_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.split("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_consensus_v129_near_square_midedge_default_fallback_increases_debias(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v129_near_square_midedge_default_fallback.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = ConsensusQAStrategy()

    # Gate-on pocket: near-square + mid-edge + default-band consensus.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=252, height=236, contrast=0.68, edge_density=0.24),
    )
    out_gate_on = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.74}),
        tmp_path / "out_gate_on",
    )

    # Gate-off control: edge density above upper bound.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=252, height=236, contrast=0.68, edge_density=0.34),
    )
    out_gate_off = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.74}),
        tmp_path / "out_gate_off",
    )

    gate_on_diag = analyze_dxf(str(out_gate_on.dxf_path))
    gate_off_diag = analyze_dxf(str(out_gate_off.dxf_path))

    assert out_gate_on.success is True
    assert out_gate_off.success is True
    assert _extract_debias_chords(out_gate_on.notes) > _extract_debias_chords(out_gate_off.notes)
    assert gate_on_diag.axis_aligned_line_ratio < gate_off_diag.axis_aligned_line_ratio
    assert gate_on_diag.unique_x_count > gate_off_diag.unique_x_count
    assert gate_on_diag.unique_y_count > gate_off_diag.unique_y_count
