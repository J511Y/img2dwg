from types import SimpleNamespace

from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def test_two_stage_irrational_coordinate_lift_segments_add_coordinate_diversity() -> None:
    plan = SimpleNamespace(
        segments=[
            ((0.0, 0.0), (100.0, 0.0)),
            ((100.0, 0.0), (100.0, 100.0)),
            ((0.0, 100.0), (100.0, 100.0)),
            ((0.0, 0.0), (0.0, 100.0)),
        ]
    )
    signals = SimpleNamespace(contrast=0.64, edge_density=0.59)

    appended = TwoStageBaselineStrategy._inject_irrational_coordinate_lift_segments(plan, signals)

    assert appended == 6
    injected = plan.segments[-appended:]
    assert all(
        abs(start[0] - end[0]) > 1e-6 and abs(start[1] - end[1]) > 1e-6 for start, end in injected
    )

    rounded_x = {round(coord, 4) for start, end in injected for coord in (start[0], end[0])}
    rounded_y = {round(coord, 4) for start, end in injected for coord in (start[1], end[1])}
    assert len(rounded_x) >= 11
    assert len(rounded_y) >= 11
