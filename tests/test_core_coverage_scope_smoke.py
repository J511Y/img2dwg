"""Smoke tests to keep scoped coverage gate representative for issue #6."""

from __future__ import annotations

from img2dwg.models import converter, schema
from img2dwg.ved import metrics, tokenizer, utils


def test_scoped_coverage_smoke_for_core_modules() -> None:
    """Exercise core-module entrypoints so changed-file coverage cannot regress."""
    point = schema.Point2D.from_dict({"x": 1.0, "y": 2.0})
    doc = schema.CADDocument.from_dict(
        {
            "metadata": {"filename": "demo.png", "type": "plan", "entity_count": 0},
            "entities": [],
        }
    )
    metric_values = metrics.compute_metrics(
        predictions=['{"entities": [{"type": "LINE"}]}'],
        references=['{"entities": [{"type": "LINE"}]}'],
    )

    assert point.to_dict() == {"x": 1.0, "y": 2.0}
    assert doc.to_dict()["metadata"]["filename"] == "demo.png"
    assert metric_values["parse_success_rate"] == 1.0
    assert metric_values["exact_match"] == 1.0
    assert utils.validate_json('{"ok": true}')
    assert utils.format_time(65) == "1m 5s"
    assert tokenizer.CADTokenizer.CAD_TOKENS
    assert hasattr(converter, "JSONToDWGConverter")
