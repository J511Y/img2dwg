from pathlib import Path
from types import SimpleNamespace

import ezdxf
from PIL import Image, ImageDraw

from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def _make_sample_plan_image(path: Path) -> None:
    image = Image.new("L", (96, 96), color=245)
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 84, 84), outline=20, width=4)
    draw.line((12, 48, 84, 48), fill=50, width=2)
    draw.line((48, 12, 48, 84), fill=50, width=2)
    image.convert("RGB").save(path)


def test_append_quasi_lattice_scatter_pack_adds_six_non_axis_segments() -> None:
    plan = SimpleNamespace(segments=[])

    appended = TwoStageBaselineStrategy._append_quasi_lattice_scatter_pack(
        plan,
        left=0.0,
        right=100.0,
        top=0.0,
        bottom=100.0,
    )

    assert appended == 6
    injected = plan.segments[-appended:]
    assert all(
        abs(start[0] - end[0]) > 1e-6 and abs(start[1] - end[1]) > 1e-6 for start, end in injected
    )


def test_two_stage_v41_quasi_lattice_pack_is_emitted(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    strategy = TwoStageBaselineStrategy()
    out = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out")

    assert out.success is True
    assert any("anti_grid_detail_diag:hexa_v41_quasi_lattice_scatter:6" in note for note in out.notes)

    doc = ezdxf.readfile(str(out.dxf_path))
    lines = list(doc.modelspace().query("LINE"))
    assert len(lines) >= 110
