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


def test_consensus_v115_near_square_default_band_expansion_raises_debias_floor(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "consensus_v115_near_square_default_band.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    strategy = ConsensusQAStrategy()

    # Chrysler-like default-band near-square pocket.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=256, height=252, contrast=0.68, edge_density=0.14),
    )
    out_relief = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.71}),
        tmp_path / "out_relief",
    )

    # Move just beyond the near-square gate while preserving the rest.
    monkeypatch.setattr(
        consensus_qa,
        "extract_image_signals",
        lambda _: ImageSignals(width=280, height=252, contrast=0.68, edge_density=0.14),
    )
    out_control = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.71}),
        tmp_path / "out_control",
    )

    relief_diag = analyze_dxf(str(out_relief.dxf_path))
    control_diag = analyze_dxf(str(out_control.dxf_path))

    assert out_relief.success is True
    assert out_control.success is True
    assert _extract_debias_chords(out_relief.notes) >= 45
    assert _extract_debias_chords(out_relief.notes) > _extract_debias_chords(out_control.notes)
    assert relief_diag.axis_aligned_line_ratio < control_diag.axis_aligned_line_ratio
    assert relief_diag.unique_x_count > control_diag.unique_x_count
    assert relief_diag.unique_y_count > control_diag.unique_y_count
