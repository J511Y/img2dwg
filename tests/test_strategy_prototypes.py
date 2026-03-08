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


def test_two_stage_strategy_adds_anti_grid_diagonal_detail(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    strategy = TwoStageBaselineStrategy()
    out = strategy.run(ConversionInput(image_path=image_path), tmp_path / "out")

    assert out.success is True
    assert any("anti_grid_detail_diag:on" in note for note in out.notes)
    assert any("anti_grid_detail_diag:oct" in note for note in out.notes)

    doc = ezdxf.readfile(str(out.dxf_path))
    lines = list(doc.modelspace().query("LINE"))
    assert len(lines) >= 14
    diagonal_count = sum(
        1
        for line in lines
        if abs(line.dxf.start.x - line.dxf.end.x) > 1e-6 and abs(line.dxf.start.y - line.dxf.end.y) > 1e-6
    )
    assert diagonal_count >= 8


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


def test_consensus_strategy_adds_anti_grid_diagonal_detail(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    out = ConsensusQAStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.9}),
        tmp_path / "out",
    )

    assert out.success is True
    assert any("anti_grid_detail_diag:on" in note for note in out.notes)
    assert any("anti_grid_detail_diag:oct" in note for note in out.notes)

    doc = ezdxf.readfile(str(out.dxf_path))
    lines = list(doc.modelspace().query("LINE"))
    assert len(lines) >= 14
    diagonal_count = sum(
        1
        for line in lines
        if abs(line.dxf.start.x - line.dxf.end.x) > 1e-6 and abs(line.dxf.start.y - line.dxf.end.y) > 1e-6
    )
    assert diagonal_count >= 8


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


def test_hybrid_strategy_avoids_diagonal_lines_for_floorplan_like_inputs(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    hybrid = HybridMVPStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.9}),
        tmp_path / "hybrid",
    )

    assert hybrid.success is True
    assert hybrid.dxf_path is not None

    doc = ezdxf.readfile(str(hybrid.dxf_path))
    lines = list(doc.modelspace().query("LINE"))
    assert len(lines) >= 6

    for line in lines:
        start = line.dxf.start
        end = line.dxf.end
        is_axis_aligned = abs(start.x - end.x) < 1e-6 or abs(start.y - end.y) < 1e-6
        assert is_axis_aligned



def test_hybrid_strategy_adds_adaptive_detail_line_on_high_edge_density(tmp_path: Path) -> None:
    image_path = tmp_path / "high_edge.png"
    image = Image.new("L", (96, 96), color=255)
    draw = ImageDraw.Draw(image)
    for x in range(0, 96, 8):
        draw.line((x, 0, x, 95), fill=0, width=1)
    for y in range(0, 96, 8):
        draw.line((0, y, 95, y), fill=0, width=1)
    image.convert("RGB").save(image_path)

    hybrid = HybridMVPStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.9}),
        tmp_path / "hybrid",
    )

    assert hybrid.success is True
    assert any("adaptive_detail_line:on" in note for note in hybrid.notes)

    assert any("adaptive_detail_type:diag_oct" in note for note in hybrid.notes)

    doc = ezdxf.readfile(str(hybrid.dxf_path))
    lines = list(doc.modelspace().query("LINE"))

    short_diagonal_count = 0
    for line in lines:
        start = line.dxf.start
        end = line.dxf.end
        dx = abs(start.x - end.x)
        dy = abs(start.y - end.y)
        if dx > 1e-6 and dy > 1e-6 and dx < 30 and dy < 30:
            short_diagonal_count += 1

    assert short_diagonal_count >= 8
