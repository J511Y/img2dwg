from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def test_two_stage_v156_default_band_axis_escape_diag_gate_and_append() -> None:
    strategy = TwoStageBaselineStrategy()

    plan = type("Plan", (), {})()
    plan.segments = [
        ((0.0, 0.0), (10.0, 0.0)),
        ((10.0, 0.0), (10.0, 6.0)),
        ((10.0, 6.0), (0.0, 6.0)),
        ((0.0, 6.0), (0.0, 0.0)),
    ]

    before = len(plan.segments)
    out_gate = strategy._inject_default_band_axis_escape_diag(
        plan,
        aspect_ratio=1.44,
        complexity=0.48,
        edge_density=0.24,
    )
    assert out_gate == 1
    assert len(plan.segments) == before + 1

    edge_upper_gate = strategy._inject_default_band_axis_escape_diag(
        plan,
        aspect_ratio=1.62,
        complexity=0.48,
        edge_density=0.38,
    )
    assert edge_upper_gate == 1

    no_gate = strategy._inject_default_band_axis_escape_diag(
        plan,
        aspect_ratio=2.12,
        complexity=0.48,
        edge_density=0.24,
    )
    assert no_gate == 0
