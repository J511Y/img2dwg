"""Smoke tests to keep scoped coverage gate representative for issue #6."""

from __future__ import annotations

import importlib
from typing import Any


class _FakeText:
    """Minimal text entity double supporting set_placement chaining."""

    def __init__(self, calls: list[tuple[str, Any]]) -> None:
        self._calls = calls

    def set_placement(self, position: tuple[float, float], align: Any) -> _FakeText:
        self._calls.append(("text_placement", (position, align)))
        return self


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

    def add_lwpolyline(
        self,
        points: list[tuple[float, float]],
        close: bool,
        dxfattribs: dict[str, Any],
    ) -> None:
        self.calls.append(("polyline", (points, close, dxfattribs)))

    def add_circle(
        self,
        center: tuple[float, float],
        radius: float,
        dxfattribs: dict[str, Any],
    ) -> None:
        self.calls.append(("circle", (center, radius, dxfattribs)))

    def add_arc(
        self,
        center: tuple[float, float],
        radius: float,
        start_angle: float,
        end_angle: float,
        dxfattribs: dict[str, Any],
    ) -> None:
        self.calls.append(("arc", (center, radius, start_angle, end_angle, dxfattribs)))

    def add_text(self, content: str, dxfattribs: dict[str, Any]) -> _FakeText:
        self.calls.append(("text", (content, dxfattribs)))
        return _FakeText(self.calls)


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
    entities: list[dict[str, Any]] = [
        {
            "type": "line",
            "start": {"x": 0.0, "y": 0.0},
            "end": {"x": 1.0, "y": 1.0},
            "layer": "0",
            "color": 7,
            "linetype": "BYLAYER",
        },
        {
            "type": "polyline",
            "points": [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 1.0}],
            "closed": True,
            "layer": "0",
            "color": 7,
            "linetype": "BYLAYER",
        },
        {
            "type": "circle",
            "center": {"x": 2.0, "y": 2.0},
            "radius": 2.5,
            "layer": "0",
            "color": 7,
            "linetype": "BYLAYER",
        },
        {
            "type": "arc",
            "center": {"x": 2.0, "y": 2.0},
            "radius": 1.5,
            "start_angle": 0.0,
            "end_angle": 90.0,
            "layer": "0",
            "color": 7,
            "linetype": "BYLAYER",
        },
        {
            "type": "text",
            "position": {"x": 3.0, "y": 3.0},
            "content": "smoke",
            "height": 2.5,
            "rotation": 10.0,
            "layer": "0",
            "color": 7,
            "linetype": "BYLAYER",
        },
        {"type": "unknown"},
    ]
    for entity in entities:
        converter_instance._add_entity_to_modelspace(modelspace, entity)

    assert point.to_dict() == {"x": 1.0, "y": 2.0}
    assert doc.to_dict()["metadata"]["filename"] == "demo.png"
    assert metric_values["parse_success_rate"] == 1.0
    assert metric_values["exact_match"] == 1.0
    assert ved_utils.validate_json('{"ok": true}')
    assert ved_utils.format_time(65) == "1m 5s"
    assert tokenizer.CADTokenizer.CAD_TOKENS
    called_kinds = {name for name, _ in modelspace.calls}
    assert {"line", "polyline", "circle", "arc", "text", "text_placement"}.issubset(called_kinds)
