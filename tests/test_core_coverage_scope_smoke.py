"""Smoke tests to keep scoped coverage gate representative for issue #6."""

from __future__ import annotations

import importlib
from typing import Any


class _FakeModelspace:
    """Minimal ezdxf modelspace double for converter smoke coverage."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def add_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        dxfattribs: dict[str, Any],
    ) -> None:
        self.calls.append(("line", (start, end, dxfattribs)))


def test_scoped_coverage_smoke_for_core_modules() -> None:
    """Exercise core-module entrypoints so changed-file coverage cannot regress."""
    schema: Any = importlib.import_module("img2dwg.models.schema")
    converter_module: Any = importlib.import_module("img2dwg.models.converter")
    metrics: Any = importlib.import_module("img2dwg.ved.metrics")
    tokenizer: Any = importlib.import_module("img2dwg.ved.tokenizer")
    ved_utils: Any = importlib.import_module("img2dwg.ved.utils")

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

    modelspace = _FakeModelspace()
    converter_instance = converter_module.JSONToDWGConverter()
    converter_instance._add_entity_to_modelspace(
        modelspace,
        {
            "type": "line",
            "start": {"x": 0.0, "y": 0.0},
            "end": {"x": 1.0, "y": 1.0},
            "layer": "0",
            "color": 7,
            "linetype": "BYLAYER",
        },
    )

    assert point.to_dict() == {"x": 1.0, "y": 2.0}
    assert doc.to_dict()["metadata"]["filename"] == "demo.png"
    assert metric_values["parse_success_rate"] == 1.0
    assert metric_values["exact_match"] == 1.0
    assert ved_utils.validate_json('{"ok": true}')
    assert ved_utils.format_time(65) == "1m 5s"
    assert tokenizer.CADTokenizer.CAD_TOKENS
    assert modelspace.calls and modelspace.calls[0][0] == "line"
