from pathlib import Path

from img2dwg.strategies import two_stage
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def _extract_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.split("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def test_two_stage_v60_elongated_floorplan_gets_extra_debias(monkeypatch, tmp_path: Path) -> None:
    calls: list[ImageSignals] = [
        ImageSignals(width=220, height=220, contrast=0.9, edge_density=0.9),
        ImageSignals(width=360, height=120, contrast=0.9, edge_density=0.9),
    ]

    def _fake_signals(_image_path: Path) -> ImageSignals:
        return calls.pop(0)

    monkeypatch.setattr(two_stage, "extract_image_signals", _fake_signals)

    image_path = tmp_path / "stub.png"
    image_path.write_bytes(b"stub")

    strategy = TwoStageBaselineStrategy()
    out_square = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_square")
    out_elongated = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out_elongated")

    assert _extract_chords(out_elongated.notes) > _extract_chords(out_square.notes)
