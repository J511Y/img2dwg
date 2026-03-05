"""DWGParser POLYLINE/LWPOLYLINE 회귀 테스트."""

from pathlib import Path

import ezdxf

from img2dwg.data.dwg_parser import DWGParser


def test_convert_entity_handles_lwpolyline_and_polyline() -> None:
    parser = DWGParser()
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    lwpolyline = msp.add_lwpolyline([(0, 0), (10, 0), (10, 5)], close=True)
    polyline = msp.add_polyline2d([(1, 1), (3, 1), (3, 4)], close=True)

    converted_lw = parser._convert_entity(lwpolyline)
    converted_poly = parser._convert_entity(polyline)

    assert converted_lw is not None
    assert converted_lw["type"] == "polyline"
    assert converted_lw["closed"] is True
    assert converted_lw["points"] == [
        {"x": 0.0, "y": 0.0},
        {"x": 10.0, "y": 0.0},
        {"x": 10.0, "y": 5.0},
    ]

    assert converted_poly is not None
    assert converted_poly["type"] == "polyline"
    assert converted_poly["closed"] is True
    assert converted_poly["points"] == [
        {"x": 1.0, "y": 1.0},
        {"x": 3.0, "y": 1.0},
        {"x": 3.0, "y": 4.0},
    ]


def test_parse_dxf_preserves_polyline_entities(tmp_path: Path) -> None:
    parser = DWGParser()
    dxf_path = tmp_path / "polyline_mix.dxf"

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (5, 0), (5, 5)], close=False)
    msp.add_polyline2d([(10, 10), (20, 10), (20, 20)], close=True)
    doc.saveas(dxf_path)

    entities = parser._parse_dxf(dxf_path)

    polylines = [entity for entity in entities if entity["type"] == "polyline"]
    assert len(polylines) == 2
    assert polylines[0]["points"] == [
        {"x": 0.0, "y": 0.0},
        {"x": 5.0, "y": 0.0},
        {"x": 5.0, "y": 5.0},
    ]
    assert polylines[0]["closed"] is False
    assert polylines[1]["points"] == [
        {"x": 10.0, "y": 10.0},
        {"x": 20.0, "y": 10.0},
        {"x": 20.0, "y": 20.0},
    ]
    assert polylines[1]["closed"] is True
