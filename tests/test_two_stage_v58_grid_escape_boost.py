from pathlib import Path

from img2dwg.strategies import two_stage
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def _extract_note_value(notes: list[str], prefix: str) -> float:
    for note in notes:
        if note.startswith(prefix):
            return float(note.split(":", maxsplit=1)[1])
    raise AssertionError(f"missing note: {prefix}")


def _extract_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.split("x", maxsplit=1)[1])
    raise AssertionError("missing offgrid_debias_chords note")


def test_two_stage_v58_high_complexity_raises_chord_budget(monkeypatch, tmp_path: Path) -> None:
    def _fake_signals(_image_path: Path) -> ImageSignals:
        return ImageSignals(width=160, height=120, contrast=1.0, edge_density=1.0)

    monkeypatch.setattr(two_stage, "extract_image_signals", _fake_signals)

    image_path = tmp_path / "stub.png"
    image_path.write_bytes(b"stub")

    out = TwoStageBaselineStrategy().run(ConversionInput(image_path=image_path), tmp_path / "out")

    assert out.success is True
    assert out.dxf_path is not None
    assert out.dxf_path.exists()

    # v58 ceiling: base(26) + max extra(28) => 54
    assert _extract_chords(out.notes) >= 54
    assert _extract_note_value(out.notes, "offgrid_shift:") >= 0.089
    assert _extract_note_value(out.notes, "diagonal_fan:") >= 0.175
