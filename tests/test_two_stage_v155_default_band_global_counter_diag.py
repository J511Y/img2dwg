from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def test_two_stage_v155_default_band_global_counter_diag_gate_and_append() -> None:
    strategy = TwoStageBaselineStrategy()

    plan = type("Plan", (), {})()
    plan.segments = [
        ((0.0, 0.0), (10.0, 0.0)),
        ((10.0, 0.0), (10.0, 6.0)),
        ((10.0, 6.0), (0.0, 6.0)),
        ((0.0, 6.0), (0.0, 0.0)),
    ]

    before = len(plan.segments)
    out_gate = strategy._inject_default_band_global_counter_diag(
        plan,
        aspect_ratio=1.42,
        complexity=0.44,
        edge_density=0.24,
    )
    assert out_gate == 1
    assert len(plan.segments) == before + 1

    no_gate = strategy._inject_default_band_global_counter_diag(
        plan,
        aspect_ratio=2.20,
        complexity=0.44,
        edge_density=0.24,
    )
    assert no_gate == 0
