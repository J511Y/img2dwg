from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def test_two_stage_v157_axis_escape_gate_widen_captures_low_edge_band() -> None:
    strategy = TwoStageBaselineStrategy()

    plan = type("Plan", (), {})()
    plan.segments = [
        ((0.0, 0.0), (10.0, 0.0)),
        ((10.0, 0.0), (10.0, 6.0)),
        ((10.0, 6.0), (0.0, 6.0)),
        ((0.0, 6.0), (0.0, 0.0)),
    ]

    widened_gate = strategy._inject_default_band_axis_escape_diag(
        plan,
        aspect_ratio=1.10,
        complexity=0.31,
        edge_density=0.13,
    )
    assert widened_gate == 1

    no_gate = strategy._inject_default_band_axis_escape_diag(
        plan,
        aspect_ratio=1.10,
        complexity=0.28,
        edge_density=0.11,
    )
    assert no_gate == 0
