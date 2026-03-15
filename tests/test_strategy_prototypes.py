from pathlib import Path

import ezdxf
from PIL import Image, ImageDraw

from img2dwg.strategies.base import ConversionInput
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy
from img2dwg.strategies.hybrid_mvp import HybridMVPStrategy
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def _make_sample_plan_image(path: Path) -> None:
    image = Image.new("L", (96, 96), color=245)
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 84, 84), outline=20, width=4)
    draw.line((12, 48, 84, 48), fill=50, width=2)
    draw.line((48, 12, 48, 84), fill=50, width=2)
    image.convert("RGB").save(path)


def _line_diagnostics(dxf_path: Path, *, eps: float = 1e-6) -> tuple[int, int, int, int]:
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    non_axis_count = 0
    line_count = 0
    x_coords: set[float] = set()
    y_coords: set[float] = set()
    for entity in msp:
        if entity.dxftype() != "LINE":
            continue
        start = entity.dxf.start
        end = entity.dxf.end
        dx = float(end[0]) - float(start[0])
        dy = float(end[1]) - float(start[1])
        line_count += 1
        x_coords.add(round(float(start[0]), 3))
        x_coords.add(round(float(end[0]), 3))
        y_coords.add(round(float(start[1]), 3))
        y_coords.add(round(float(end[1]), 3))
        if abs(dx) > eps and abs(dy) > eps:
            non_axis_count += 1
    return non_axis_count, line_count, len(x_coords), len(y_coords)


def test_two_stage_strategy_exports_dxf(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    strategy = TwoStageBaselineStrategy()
    out = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out")

    assert out.success is True
    assert out.dxf_path is not None
    assert out.dxf_path.exists()
    assert out.metrics["iou"] > 0.0
    assert any("정(thesis)" in note for note in out.notes)
    assert any("offgrid_shift:" in note for note in out.notes)
    assert out.dxf_path is not None
    non_axis_count, line_count, unique_x_count, unique_y_count = _line_diagnostics(out.dxf_path)
    assert non_axis_count >= 4
    assert line_count >= 10
    assert (line_count - non_axis_count) / line_count <= 0.6
    assert unique_x_count >= 8
    assert unique_y_count >= 8


def test_consensus_strategy_rejects_low_confidence(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    strategy = ConsensusQAStrategy()
    out = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.1}),
        tmp_path / "out",
    )

    assert out.success is False
    assert out.dxf_path is None
    assert any("rejected" in note for note in out.notes)


def test_consensus_strategy_accepts_vote_list(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    strategy = ConsensusQAStrategy()
    out = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_votes": [0.9, 0.8, 0.7]}),
        tmp_path / "out",
    )

    assert out.success is True
    assert out.dxf_path is not None
    assert out.dxf_path.exists()
    assert any("offgrid_shift:" in note for note in out.notes)
    non_axis_count, line_count, unique_x_count, unique_y_count = _line_diagnostics(out.dxf_path)
    assert non_axis_count >= 4
    assert line_count >= 10
    assert (line_count - non_axis_count) / line_count <= 0.6
    assert unique_x_count >= 8
    assert unique_y_count >= 8


def test_hybrid_strategy_improves_over_two_stage_at_high_consensus(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    baseline = TwoStageBaselineStrategy().run(ConversionInput(image_path=image_path), tmp_path / "base")
    hybrid = HybridMVPStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.9}),
        tmp_path / "hybrid",
    )

    assert hybrid.success is True
    assert hybrid.dxf_path is not None
    assert hybrid.dxf_path.exists()
    assert hybrid.metrics["iou"] >= baseline.metrics["iou"]
    assert hybrid.metrics["topology_f1"] >= baseline.metrics["topology_f1"]
