from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def test_two_stage_v159_axis_escape_bridge_gate_expansion_captures_lower_band() -> None:
    strategy = TwoStageBaselineStrategy()

    plan = type("Plan", (), {})()
    plan.segments = [
        ((0.0, 0.0), (10.0, 0.0)),
        ((10.0, 0.0), (10.0, 6.0)),
        ((10.0, 6.0), (0.0, 6.0)),
        ((0.0, 6.0), (0.0, 0.0)),
    ]

    added = strategy._inject_default_band_axis_escape_bridge(
        plan,
        aspect_ratio=1.00,
        complexity=0.26,
        edge_density=0.08,
    )
    assert added == 1

    blocked = strategy._inject_default_band_axis_escape_bridge(
        plan,
        aspect_ratio=0.99,
        complexity=0.25,
        edge_density=0.07,
    )
    assert blocked == 0
