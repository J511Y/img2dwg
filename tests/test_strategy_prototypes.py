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


def _extract_debias_chord_multiplier(notes: list[str]) -> int:
    for note in notes:
        if note.startswith("offgrid_debias_chords:x"):
            return int(note.split("x", maxsplit=1)[1])
    raise AssertionError("offgrid_debias_chords note missing")


def _extract_offgrid_shift(notes: list[str]) -> float:
    for note in notes:
        if note.startswith("offgrid_shift:"):
            return float(note.split(":", maxsplit=1)[1])
    raise AssertionError("offgrid_shift note missing")


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
    assert any("diagonal_fan:" in note for note in out.notes)
    assert not any("center_cross:on" in note for note in out.notes)
    assert out.dxf_path is not None
    non_axis_count, line_count, unique_x_count, unique_y_count = _line_diagnostics(out.dxf_path)
    assert non_axis_count >= 6
    assert line_count >= 10
    assert (line_count - non_axis_count) / line_count <= 0.40
    assert unique_x_count >= 10
    assert unique_y_count >= 10


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
    assert any("diagonal_fan:" in note for note in out.notes)
    assert not any("center_cross:on" in note for note in out.notes)
    non_axis_count, line_count, unique_x_count, unique_y_count = _line_diagnostics(out.dxf_path)
    assert non_axis_count >= 6
    assert line_count >= 10
    assert (line_count - non_axis_count) / line_count <= 0.40
    assert unique_x_count >= 10
    assert unique_y_count >= 10


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


def test_two_stage_strategy_has_grid_debias_guardrail(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    baseline = TwoStageBaselineStrategy().run(
        ConversionInput(image_path=image_path), tmp_path / "base"
    )

    assert baseline.success is True
    assert baseline.dxf_path is not None
    assert _extract_debias_chord_multiplier(baseline.notes) >= 24

    non_axis_count, line_count, unique_x_count, unique_y_count = _line_diagnostics(
        baseline.dxf_path
    )
    axis_ratio = (line_count - non_axis_count) / line_count

    assert axis_ratio <= 0.11
    assert unique_x_count >= 20
    assert unique_y_count >= 20


def test_consensus_strategy_debiases_more_than_two_stage_by_default(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    baseline = TwoStageBaselineStrategy().run(
        ConversionInput(image_path=image_path), tmp_path / "base"
    )
    consensus = ConsensusQAStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.71}),
        tmp_path / "consensus",
    )

    assert baseline.success is True
    assert baseline.dxf_path is not None
    assert consensus.success is True
    assert consensus.dxf_path is not None
    assert _extract_debias_chord_multiplier(consensus.notes) >= 30

    base_non_axis, base_lines, base_unique_x, base_unique_y = _line_diagnostics(baseline.dxf_path)
    con_non_axis, con_lines, con_unique_x, con_unique_y = _line_diagnostics(consensus.dxf_path)

    base_axis_ratio = (base_lines - base_non_axis) / base_lines
    con_axis_ratio = (con_lines - con_non_axis) / con_lines

    assert base_axis_ratio <= 0.10
    assert con_axis_ratio <= 0.11
    assert con_unique_x >= 64
    assert con_unique_y >= 64


def test_consensus_strategy_default_adds_coordinate_diversity_vs_two_stage(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    baseline = TwoStageBaselineStrategy().run(
        ConversionInput(image_path=image_path), tmp_path / "base"
    )
    consensus = ConsensusQAStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.71}),
        tmp_path / "consensus",
    )

    assert baseline.success is True
    assert baseline.dxf_path is not None
    assert consensus.success is True
    assert consensus.dxf_path is not None

    _, _, base_unique_x, base_unique_y = _line_diagnostics(baseline.dxf_path)
    _, _, con_unique_x, con_unique_y = _line_diagnostics(consensus.dxf_path)

    assert base_unique_x >= 70
    assert base_unique_y >= 70
    assert con_unique_x >= 64
    assert con_unique_y >= 64


def test_consensus_strategy_high_confidence_uses_extra_debias_chords(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    consensus = ConsensusQAStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.9}),
        tmp_path / "consensus_hi",
    )

    assert consensus.success is True
    assert consensus.dxf_path is not None
    assert _extract_debias_chord_multiplier(consensus.notes) >= 34

    non_axis_count, line_count, unique_x_count, unique_y_count = _line_diagnostics(
        consensus.dxf_path
    )
    axis_ratio = (line_count - non_axis_count) / line_count

    assert axis_ratio <= 0.11
    assert unique_x_count >= 16
    assert unique_y_count >= 16


def test_two_stage_strategy_chord_boost_improves_coordinate_diversity(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    baseline = TwoStageBaselineStrategy().run(
        ConversionInput(image_path=image_path), tmp_path / "base"
    )

    assert baseline.success is True
    assert baseline.dxf_path is not None

    non_axis_count, line_count, unique_x_count, unique_y_count = _line_diagnostics(
        baseline.dxf_path
    )
    axis_ratio = (line_count - non_axis_count) / line_count

    assert _extract_debias_chord_multiplier(baseline.notes) >= 24
    assert axis_ratio <= 0.10
    assert line_count >= 54
    assert unique_x_count >= 22
    assert unique_y_count >= 22


def test_two_stage_strategy_adapts_debias_chords_to_image_complexity(tmp_path: Path) -> None:
    low_path = tmp_path / "low.png"
    high_path = tmp_path / "high.png"

    low = Image.new("L", (96, 96), color=230)
    ImageDraw.Draw(low).rectangle((18, 18, 78, 78), outline=50, width=2)
    low.convert("RGB").save(low_path)

    high = Image.new("L", (96, 96), color=250)
    draw_high = ImageDraw.Draw(high)
    for step in range(6, 90, 8):
        draw_high.line((step, 4, 95 - step // 2, 92), fill=10 + (step % 60), width=2)
        draw_high.line((4, step, 92, 95 - step // 2), fill=20 + (step % 70), width=2)
    high.convert("RGB").save(high_path)

    strategy = TwoStageBaselineStrategy()
    out_low = strategy.run(ConversionInput(image_path=low_path), tmp_path / "low_out")
    out_high = strategy.run(ConversionInput(image_path=high_path), tmp_path / "high_out")

    assert out_low.success is True
    assert out_high.success is True

    low_chords = _extract_debias_chord_multiplier(out_low.notes)
    high_chords = _extract_debias_chord_multiplier(out_high.notes)
    low_shift = _extract_offgrid_shift(out_low.notes)
    high_shift = _extract_offgrid_shift(out_high.notes)

    assert high_chords >= low_chords
    assert high_shift >= low_shift


def test_consensus_strategy_v2_debias_chords_raise_line_budget(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    consensus = ConsensusQAStrategy().run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.71}),
        tmp_path / "consensus",
    )

    assert consensus.success is True
    assert consensus.dxf_path is not None
    assert _extract_debias_chord_multiplier(consensus.notes) >= 32

    non_axis_count, line_count, unique_x_count, unique_y_count = _line_diagnostics(
        consensus.dxf_path
    )
    axis_ratio = (line_count - non_axis_count) / line_count

    assert axis_ratio <= 0.08
    assert line_count >= 74
    assert unique_x_count >= 30
    assert unique_y_count >= 30


def test_consensus_strategy_increases_debias_with_confidence(tmp_path: Path) -> None:
    image_path = tmp_path / "plan.png"
    _make_sample_plan_image(image_path)

    strategy = ConsensusQAStrategy()
    out_mid = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.71}),
        tmp_path / "consensus_mid",
    )
    out_high = strategy.run(
        ConversionInput(image_path=image_path, metadata={"consensus_score": 0.92}),
        tmp_path / "consensus_high",
    )

    assert out_mid.success is True
    assert out_high.success is True

    mid_chords = _extract_debias_chord_multiplier(out_mid.notes)
    high_chords = _extract_debias_chord_multiplier(out_high.notes)
    mid_shift = _extract_offgrid_shift(out_mid.notes)
    high_shift = _extract_offgrid_shift(out_high.notes)

    assert high_chords >= mid_chords
    assert high_shift >= mid_shift


def test_consensus_strategy_residual_axis_jitter_gate_lifts_moderate_band(tmp_path: Path) -> None:
    mild_path = tmp_path / "mild.png"
    gated_path = tmp_path / "gated.png"

    mild = Image.new("L", (96, 96), color=238)
    ImageDraw.Draw(mild).rectangle((16, 16, 80, 80), outline=55, width=2)
    mild.convert("RGB").save(mild_path)

    gated = Image.new("L", (168, 96), color=250)
    draw_gated = ImageDraw.Draw(gated)
    for step in range(8, 160, 10):
        draw_gated.line((step, 6, max(4, step - 34), 90), fill=12 + (step % 80), width=2)
        draw_gated.line((max(4, step - 28), 8, step, 88), fill=22 + (step % 90), width=2)
    gated.convert("RGB").save(gated_path)

    strategy = ConsensusQAStrategy()
    out_mild = strategy.run(
        ConversionInput(image_path=mild_path, metadata={"consensus_score": 0.72}),
        tmp_path / "mild_out",
    )
    out_gated = strategy.run(
        ConversionInput(image_path=gated_path, metadata={"consensus_score": 0.72}),
        tmp_path / "gated_out",
    )

    assert out_mild.success is True
    assert out_gated.success is True

    mild_chords = _extract_debias_chord_multiplier(out_mild.notes)
    gated_chords = _extract_debias_chord_multiplier(out_gated.notes)
    mild_shift = _extract_offgrid_shift(out_mild.notes)
    gated_shift = _extract_offgrid_shift(out_gated.notes)

    assert gated_chords >= mild_chords + 2
    assert gated_shift > mild_shift
