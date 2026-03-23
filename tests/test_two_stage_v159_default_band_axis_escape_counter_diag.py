from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def test_two_stage_v159_default_band_axis_escape_counter_diag_gate() -> None:
    strategy = TwoStageBaselineStrategy()

    plan = type("Plan", (), {})()
    plan.segments = [
        ((0.0, 0.0), (10.0, 0.0)),
        ((10.0, 0.0), (10.0, 6.0)),
        ((10.0, 6.0), (0.0, 6.0)),
        ((0.0, 6.0), (0.0, 0.0)),
    ]

    added = strategy._inject_default_band_axis_escape_counter_diag(
        plan,
        aspect_ratio=1.24,
        complexity=0.33,
        edge_density=0.17,
    )
    assert added == 1

    blocked = strategy._inject_default_band_axis_escape_counter_diag(
        plan,
        aspect_ratio=1.01,
        complexity=0.25,
        edge_density=0.07,
    )
    assert blocked == 0
