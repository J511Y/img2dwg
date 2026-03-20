from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def test_two_stage_v158_default_band_axis_escape_bridge_gate() -> None:
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
        aspect_ratio=1.12,
        complexity=0.29,
        edge_density=0.11,
    )
    assert added == 1

    blocked = strategy._inject_default_band_axis_escape_bridge(
        plan,
        aspect_ratio=1.12,
        complexity=0.24,
        edge_density=0.09,
    )
    assert blocked == 0
