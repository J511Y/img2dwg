from types import SimpleNamespace

from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def test_seed_debias_removes_perfect_axis_alignment() -> None:
    plan = SimpleNamespace(
        segments=[
            ((10.0, 10.0), (10.0, 90.0)),
            ((10.0, 10.0), (90.0, 10.0)),
            ((15.0, 15.0), (60.0, 65.0)),
        ]
    )

    touched = TwoStageBaselineStrategy._debias_axis_aligned_seed_segments(plan, seed_segment_count=2)

    assert touched is True
    first, second = plan.segments[0], plan.segments[1]
    assert abs(first[0][0] - first[1][0]) > 1e-6
    assert abs(second[0][1] - second[1][1]) > 1e-6


def test_coordinate_entropy_lift_increases_unique_coordinates() -> None:
    plan = SimpleNamespace(
        segments=[
            ((1.0, 1.0), (3.0, 3.0)),
            ((1.0, 1.0), (3.0, 3.0)),
            ((1.0, 1.0), (3.0, 3.0)),
            ((1.0, 1.0), (3.0, 3.0)),
            ((1.0, 1.0), (3.0, 3.0)),
        ]
    )

    before_x = {coord for seg in plan.segments for coord in (seg[0][0], seg[1][0])}
    before_y = {coord for seg in plan.segments for coord in (seg[0][1], seg[1][1])}
    before_x_rounded = {round(coord, 3) for coord in before_x}
    before_y_rounded = {round(coord, 3) for coord in before_y}

    touched = TwoStageBaselineStrategy._inject_coordinate_entropy(plan)

    after_x = {coord for seg in plan.segments for coord in (seg[0][0], seg[1][0])}
    after_y = {coord for seg in plan.segments for coord in (seg[0][1], seg[1][1])}
    after_x_rounded = {round(coord, 3) for coord in after_x}
    after_y_rounded = {round(coord, 3) for coord in after_y}

    assert touched == 5
    assert len(after_x) > len(before_x)
    assert len(after_y) > len(before_y)
    assert len(after_x_rounded) > len(before_x_rounded)
    assert len(after_y_rounded) > len(before_y_rounded)
