from img2dwg.strategies.two_stage import TwoStageBaselineStrategy


def test_two_stage_v154_default_band_global_relay_diag_gate_and_append() -> None:
    strategy = TwoStageBaselineStrategy()

    # Minimal rectangle frame expected by injector.
    plan = type("Plan", (), {})()
    plan.segments = [
        ((0.0, 0.0), (10.0, 0.0)),
        ((10.0, 0.0), (10.0, 6.0)),
        ((10.0, 6.0), (0.0, 6.0)),
        ((0.0, 6.0), (0.0, 0.0)),
    ]

    before = len(plan.segments)
    out_gate = strategy._inject_default_band_global_relay_diag(
        plan,
        aspect_ratio=1.55,
        complexity=0.42,
        edge_density=0.24,
    )
    assert out_gate == 1
    assert len(plan.segments) == before + 1

    no_gate = strategy._inject_default_band_global_relay_diag(
        plan,
        aspect_ratio=2.20,
        complexity=0.42,
        edge_density=0.24,
    )
    assert no_gate == 0
