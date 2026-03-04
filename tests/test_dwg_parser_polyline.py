"""DWGParser polyline 변환 테스트."""

import ezdxf

from img2dwg.data.dwg_parser import DWGParser


def test_convert_entity_lwpolyline_points_and_closed_flag() -> None:
    parser = DWGParser()
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    entity = msp.add_lwpolyline([(0, 0), (10, 0), (10, 5)], close=True)

    converted = parser._convert_entity(entity)

    assert converted is not None
    assert converted["type"] == "polyline"
    assert converted["closed"] is True
    assert converted["points"] == [
        {"x": 0.0, "y": 0.0},
        {"x": 10.0, "y": 0.0},
        {"x": 10.0, "y": 5.0},
    ]


def test_convert_entity_polyline_points_and_closed_flag() -> None:
    parser = DWGParser()
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    entity = msp.add_polyline2d([(1, 1), (3, 1), (3, 4)], close=True)

    converted = parser._convert_entity(entity)

    assert converted is not None
    assert converted["type"] == "polyline"
    assert converted["closed"] is True
    assert converted["points"] == [
        {"x": 1.0, "y": 1.0},
        {"x": 3.0, "y": 1.0},
        {"x": 3.0, "y": 4.0},
    ]
