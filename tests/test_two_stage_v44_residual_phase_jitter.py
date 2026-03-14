from pathlib import Path
from types import SimpleNamespace

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


def test_two_stage_v44_residual_phase_jitter_appends_non_axis_segments() -> None:
    plan = SimpleNamespace(
        segments=[
            ((0.0, 0.0), (100.0, 0.0)),
            ((100.0, 0.0), (100.0, 100.0)),
            ((0.0, 100.0), (100.0, 100.0)),
            ((0.0, 0.0), (0.0, 100.0)),
        ]
    )
    signals = SimpleNamespace(contrast=0.61, edge_density=0.64)

    appended = TwoStageBaselineStrategy._inject_residual_phase_jitter_segments(plan, signals)

    assert appended == 6
    injected = plan.segments[-appended:]
    assert all(
        abs(start[0] - end[0]) > 1e-6 and abs(start[1] - end[1]) > 1e-6 for start, end in injected
    )

    rounded_x = {round(coord, 4) for start, end in injected for coord in (start[0], end[0])}
    rounded_y = {round(coord, 4) for start, end in injected for coord in (start[1], end[1])}
    assert len(rounded_x) >= 11
    assert len(rounded_y) >= 11


def test_two_stage_v44_residual_phase_jitter_note_present(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    out = TwoStageBaselineStrategy().run(ConversionInput(image_path=image_path), tmp_path / "out")

    assert out.success is True
    assert any("anti_grid_detail_diag:hexa_v44_residual_phase_jitter:6" in note for note in out.notes)


def test_two_stage_v45_aperiodic_coord_escape_appends_high_precision_non_axis_segments() -> None:
    plan = SimpleNamespace(
        segments=[
            ((0.0, 0.0), (100.0, 0.0)),
            ((100.0, 0.0), (100.0, 100.0)),
            ((0.0, 100.0), (100.0, 100.0)),
            ((0.0, 0.0), (0.0, 100.0)),
        ]
    )
    signals = SimpleNamespace(contrast=0.59, edge_density=0.67)

    appended = TwoStageBaselineStrategy._inject_aperiodic_coordinate_escape_segments(plan, signals)

    assert appended == 10
    injected = plan.segments[-appended:]
    assert all(
        abs(start[0] - end[0]) > 1e-6 and abs(start[1] - end[1]) > 1e-6 for start, end in injected
    )

    rounded_x = {round(coord, 5) for start, end in injected for coord in (start[0], end[0])}
    rounded_y = {round(coord, 5) for start, end in injected for coord in (start[1], end[1])}
    assert len(rounded_x) >= 16
    assert len(rounded_y) >= 16


def test_two_stage_v45_aperiodic_coord_escape_note_present(tmp_path: Path) -> None:
    image_path = tmp_path / "plan-v45.png"
    _make_sample_plan_image(image_path)

    out = TwoStageBaselineStrategy().run(ConversionInput(image_path=image_path), tmp_path / "out-v45")

    assert out.success is True
    assert any("anti_grid_detail_diag:deca_v45_aperiodic_coord_escape:10" in note for note in out.notes)
