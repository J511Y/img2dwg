from pathlib import Path
from types import SimpleNamespace

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
    assert any("anti_grid_axis_debias:v1" in note for note in out.notes)
    assert any("anti_grid_detail_diag:on" in note for note in out.notes)
    assert any("anti_grid_detail_diag:hexacosa_v12_spread" in note for note in out.notes)
    assert any("anti_grid_detail_diag:octa_v13_irregular" in note for note in out.notes)
    assert any("anti_grid_detail_diag:hexa_v14_debias" in note for note in out.notes)
    assert any("anti_grid_detail_diag:hexa_v15_micro_jitter" in note for note in out.notes)
    assert any("anti_grid_detail_diag:hexa_v16_entropy" in note for note in out.notes)
    assert any("anti_grid_detail_diag:tetra_v17_phase_shift" in note for note in out.notes)
    assert any("anti_grid_detail_diag:hexa_v24_entropy_weave" in note for note in out.notes)
    assert any("anti_grid_detail_diag:tetra_v25_asymmetric" in note for note in out.notes)
    assert any("anti_grid_detail_diag:octa_v26_counterphase" in note for note in out.notes)
    assert any("anti_grid_detail_diag:deca_v27_counterphase_plus" in note for note in out.notes)
    assert any("anti_grid_detail_diag:hexa_v28_frequency_break" in note for note in out.notes)
    assert any("anti_grid_detail_diag:octa_v29_quasi_random" in note for note in out.notes)
    assert any("anti_grid_detail_diag:tetra_v31_prime_lattice" in note for note in out.notes)
    assert any("anti_grid_detail_diag:octa_v30_signal_entropy:8" in note for note in out.notes)
    assert any("anti_grid_detail_diag:hexa_v32_coord_diversity:6" in note for note in out.notes)
    assert any(
        "anti_grid_detail_diag:tetra_v33_irrational_subpixel:4" in note for note in out.notes
    )
    assert any("anti_grid_detail_diag:hexa_v34_axis_escape_micro:8" in note for note in out.notes)
    assert any("anti_grid_detail_diag:deca_v35_coordinate_scatter:10" in note for note in out.notes)
    assert any(
        "anti_grid_detail_diag:dodeca_v36_aperiodic_coordinate_boost:14" in note
        for note in out.notes
    )

    doc = ezdxf.readfile(str(out.dxf_path))
    lines = list(doc.modelspace().query("LINE"))
    assert len(lines) >= 90
    diagonal_count = sum(
        1
        for line in lines
        if abs(line.dxf.start.x - line.dxf.end.x) > 1e-6
        and abs(line.dxf.start.y - line.dxf.end.y) > 1e-6
    )
    assert diagonal_count >= 40

    seed_non_axis_count = sum(
        1
        for line in lines[:6]
        if abs(line.dxf.start.x - line.dxf.end.x) > 1e-6
        and abs(line.dxf.start.y - line.dxf.end.y) > 1e-6
    )
    assert seed_non_axis_count >= 2


def test_two_stage_residual_axis_debias_nudges_perfectly_aligned_segments() -> None:
    plan = SimpleNamespace(
        segments=[
            ((10.0, 10.0), (10.0, 22.0)),
            ((30.0, 40.0), (48.0, 40.0)),
            ((1.0, 1.0), (5.0, 7.0)),
        ]
    )

    touched = TwoStageBaselineStrategy._debias_residual_axis_aligned_segments(plan, start_index=0)

    assert touched is True
    first = plan.segments[0]
    second = plan.segments[1]
    assert abs(first[0][0] - first[1][0]) > 1e-6
    assert abs(second[0][1] - second[1][1]) > 1e-6


def test_two_stage_residual_axis_debias_respects_start_index() -> None:
    plan = SimpleNamespace(
        segments=[
            ((10.0, 10.0), (10.0, 22.0)),
            ((30.0, 40.0), (48.0, 40.0)),
            ((1.0, 1.0), (5.0, 7.0)),
        ]
    )

    touched = TwoStageBaselineStrategy._debias_residual_axis_aligned_segments(plan, start_index=2)

    assert touched is False
    assert plan.segments[0] == ((10.0, 10.0), (10.0, 22.0))
    assert plan.segments[1] == ((30.0, 40.0), (48.0, 40.0))


def test_two_stage_axis_escape_microsegments_add_eight_non_axis_segments() -> None:
    plan = SimpleNamespace(
        segments=[
            ((0.0, 0.0), (100.0, 0.0)),
            ((100.0, 0.0), (100.0, 100.0)),
            ((0.0, 100.0), (100.0, 100.0)),
            ((0.0, 0.0), (0.0, 100.0)),
        ]
    )
    signals = SimpleNamespace(contrast=0.67, edge_density=0.54)

    appended = TwoStageBaselineStrategy._inject_axis_escape_microsegments(plan, signals)

    assert appended == 8
    injected = plan.segments[-appended:]
    assert all(
        abs(start[0] - end[0]) > 1e-6 and abs(start[1] - end[1]) > 1e-6 for start, end in injected
    )

    rounded_x = {round(coord, 3) for start, end in injected for coord in (start[0], end[0])}
    rounded_y = {round(coord, 3) for start, end in injected for coord in (start[1], end[1])}
    assert len(rounded_x) >= 14
    assert len(rounded_y) >= 14


def test_two_stage_coordinate_scatter_microsegments_expand_coordinate_diversity() -> None:
    plan = SimpleNamespace(
        segments=[
            ((0.0, 0.0), (100.0, 0.0)),
            ((100.0, 0.0), (100.0, 100.0)),
            ((0.0, 100.0), (100.0, 100.0)),
            ((0.0, 0.0), (0.0, 100.0)),
        ]
    )
    signals = SimpleNamespace(contrast=0.71, edge_density=0.63)

    appended = TwoStageBaselineStrategy._inject_coordinate_scatter_microsegments(plan, signals)

    assert appended == 10
    injected = plan.segments[-appended:]
    assert all(
        abs(start[0] - end[0]) > 1e-6 and abs(start[1] - end[1]) > 1e-6 for start, end in injected
    )

    rounded_x = {round(coord, 3) for start, end in injected for coord in (start[0], end[0])}
    rounded_y = {round(coord, 3) for start, end in injected for coord in (start[1], end[1])}
    assert len(rounded_x) >= 18
    assert len(rounded_y) >= 18


def test_two_stage_aperiodic_coordinate_boost_adds_non_axis_segments() -> None:
    plan = SimpleNamespace(
        segments=[
            ((0.0, 0.0), (100.0, 0.0)),
            ((100.0, 0.0), (100.0, 100.0)),
            ((0.0, 100.0), (100.0, 100.0)),
            ((0.0, 0.0), (0.0, 100.0)),
        ]
    )
    signals = SimpleNamespace(contrast=0.73, edge_density=0.66)

    appended = TwoStageBaselineStrategy._inject_aperiodic_coordinate_boost(plan, signals)

    assert appended == 14
    injected = plan.segments[-appended:]
    assert all(
        abs(start[0] - end[0]) > 1e-6 and abs(start[1] - end[1]) > 1e-6 for start, end in injected
    )

    rounded_x = {round(coord, 3) for start, end in injected for coord in (start[0], end[0])}
    rounded_y = {round(coord, 3) for start, end in injected for coord in (start[1], end[1])}
    assert len(rounded_x) >= 20
    assert len(rounded_y) >= 20


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
    assert any("anti_grid_detail_diag:dodeca_v11_spread" in note for note in out.notes)
    assert any("anti_grid_detail_diag:octa_v12_irregular" in note for note in out.notes)
    assert any("anti_grid_detail_diag:octa_v13_debias" in note for note in out.notes)
    assert any("anti_grid_detail_diag:tetra_v14_entropy" in note for note in out.notes)
    assert any("anti_grid_detail_diag:hexa_v15_micro_jitter" in note for note in out.notes)
    assert any("anti_grid_detail_diag:octa_v16_staggered" in note for note in out.notes)
    assert any("anti_grid_detail_diag:hexa_v17_golden_skew" in note for note in out.notes)
    assert any("anti_grid_detail_diag:deca_v19_precision_scatter" in note for note in out.notes)
    assert any("anti_grid_detail_diag:hexa_v18_adaptive_seed" in note for note in out.notes)
    assert any("anti_grid_detail_diag:tetra_v25_phase_entropy" in note for note in out.notes)
    assert any("anti_grid_detail_diag:tetra_v26_aperiodic_micro" in note for note in out.notes)
    assert any("anti_grid_detail_diag:hexa_v27_blue_noise" in note for note in out.notes)
    coord_diversity_notes = [
        note for note in out.notes if "anti_grid_detail_diag:octa_v28_coord_diversity:" in note
    ]
    assert coord_diversity_notes
    added_count = int(coord_diversity_notes[0].rsplit(":", 1)[-1])
    assert added_count >= 12

    doc = ezdxf.readfile(str(out.dxf_path))
    lines = list(doc.modelspace().query("LINE"))
    assert len(lines) >= 118
    diagonal_count = sum(
        1
        for line in lines
        if abs(line.dxf.start.x - line.dxf.end.x) > 1e-6
        and abs(line.dxf.start.y - line.dxf.end.y) > 1e-6
    )
    assert diagonal_count >= 70

    rounded_x = {round(coord, 3) for line in lines for coord in (line.dxf.start.x, line.dxf.end.x)}
    rounded_y = {round(coord, 3) for line in lines for coord in (line.dxf.start.y, line.dxf.end.y)}
    assert len(rounded_x) >= 214
    assert len(rounded_y) >= 220


def test_consensus_strategy_seed_debias_diversifies_seed_coordinates(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    out = ConsensusQAStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.9}),
        tmp_path / "out",
    )

    assert out.success is True
    assert out.dxf_path is not None

    doc = ezdxf.readfile(str(out.dxf_path))
    lines = list(doc.modelspace().query("LINE"))
    seed_lines = lines[:6]
    assert len(seed_lines) == 6

    start_x_values = {round(line.dxf.start.x, 4) for line in seed_lines}
    start_y_values = {round(line.dxf.start.y, 4) for line in seed_lines}

    assert len(start_x_values) >= 4
    assert len(start_y_values) >= 4


def test_hybrid_strategy_improves_over_two_stage_at_high_consensus(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    baseline = TwoStageBaselineStrategy().run(
        ConversionInput(image_path=image_path), tmp_path / "base"
    )
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
