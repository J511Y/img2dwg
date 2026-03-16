from pathlib import Path

import ezdxf
from PIL import Image

from img2dwg.strategies import two_stage
from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.prototype_engine import ImageSignals
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def _extract_debias_chords(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.split("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def _axis_ratio(dxf_path: Path, *, eps: float = 1e-6) -> float:
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    line_count = 0
    non_axis_count = 0
    for entity in msp:
        if entity.dxftype() != "LINE":
            continue
        start = entity.dxf.start
        end = entity.dxf.end
        dx = float(end[0]) - float(start[0])
        dy = float(end[1]) - float(start[1])
        line_count += 1
        if abs(dx) > eps and abs(dy) > eps:
            non_axis_count += 1
    assert line_count > 0
    return (line_count - non_axis_count) / line_count


def test_two_stage_v66_skew_interaction_lift_adds_debias_for_corridor(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "corridor.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)

    monkeypatch.setattr(
        two_stage,
        "extract_image_signals",
        lambda _: ImageSignals(width=420, height=180, contrast=0.52, edge_density=0.34),
    )

    out = TwoStageBaselineStrategy().run(ConversionInput(image_path=image_path), tmp_path / "out")

    assert out.success is True
    assert out.dxf_path is not None
    assert _extract_debias_chords(out.notes) >= 54
    assert _axis_ratio(out.dxf_path) <= 0.04
