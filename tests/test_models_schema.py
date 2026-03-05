from __future__ import annotations

from img2dwg.models.schema import (
    CADDocument,
    CircleEntity,
    LineEntity,
    Metadata,
    Point2D,
    PolylineEntity,
    TextEntity,
)


def test_schema_entities_and_document_roundtrip() -> None:
    p = Point2D(1.5, 2.5)
    assert p.to_dict() == {"x": 1.5, "y": 2.5}
    assert Point2D.from_dict({"x": 3.0, "y": 4.0}) == Point2D(3.0, 4.0)

    line = LineEntity(type="", start=Point2D(0, 0), end=Point2D(10, 10))
    assert line.type == "line"
    assert line.to_dict()["start"] == {"x": 0, "y": 0}

    poly = PolylineEntity(type="", points=[Point2D(0, 0), Point2D(1, 1)], closed=True)
    assert poly.type == "polyline"
    assert poly.to_dict()["closed"] is True

    circle = CircleEntity(type="", center=Point2D(5, 5), radius=3)
    assert circle.type == "circle"
    assert circle.to_dict()["radius"] == 3

    text = TextEntity(type="", position=Point2D(7, 8), content="room", height=2.0)
    assert text.type == "text"
    assert text.to_dict()["content"] == "room"

    metadata = Metadata(filename="a.dwg", type="change", project="p1", source_path="/tmp/a")
    doc = CADDocument(metadata=metadata, entities=[line.to_dict(), text.to_dict()])

    payload = doc.to_dict()
    assert payload["metadata"]["filename"] == "a.dwg"
    assert len(payload["entities"]) == 2

    restored = CADDocument.from_dict(payload)
    assert restored.metadata.filename == "a.dwg"
    assert restored.entities == payload["entities"]
