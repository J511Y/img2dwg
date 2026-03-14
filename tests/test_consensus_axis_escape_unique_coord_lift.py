from types import SimpleNamespace

from img2dwg.strategies.consensus_qa import ConsensusQAStrategy


def test_axis_escape_unique_coord_lift_appends_non_axis_segments() -> None:
    plan = SimpleNamespace(
        segments=[
            ((0.0, 0.0), (100.0, 0.0)),
            ((100.0, 0.0), (100.0, 100.0)),
            ((100.0, 100.0), (0.0, 100.0)),
            ((0.0, 100.0), (0.0, 0.0)),
        ],
        notes=[],
    )
    signals = SimpleNamespace(edge_density=0.4, contrast=0.6)

    appended = ConsensusQAStrategy._inject_axis_escape_unique_coord_lift(plan, signals)

    assert appended == 6
    assert len(plan.segments) == 10
    for segment in plan.segments[-appended:]:
        (sx, sy), (ex, ey) = segment
        assert sx != ex
        assert sy != ey


def test_axis_escape_unique_coord_lift_requires_seed_geometry() -> None:
    plan = SimpleNamespace(segments=[((0.0, 0.0), (1.0, 0.0))], notes=[])
    signals = SimpleNamespace(edge_density=0.5, contrast=0.5)

    appended = ConsensusQAStrategy._inject_axis_escape_unique_coord_lift(plan, signals)

    assert appended == 0
    assert len(plan.segments) == 1
