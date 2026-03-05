from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from img2dwg.models.converter import JSONToDWGConverter


class FakeTextEntity:
    def __init__(self) -> None:
        self.placements: list[tuple[tuple[float, float], object]] = []

    def set_placement(self, position: tuple[float, float], align: object) -> FakeTextEntity:
        self.placements.append((position, align))
        return self


class FakeModelspace:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def add_line(self, *args, **kwargs):
        self.calls.append(("line", args, kwargs))

    def add_lwpolyline(self, *args, **kwargs):
        self.calls.append(("lwpolyline", args, kwargs))

    def add_circle(self, *args, **kwargs):
        self.calls.append(("circle", args, kwargs))

    def add_arc(self, *args, **kwargs):
        self.calls.append(("arc", args, kwargs))

    def add_text(self, *args, **kwargs):
        self.calls.append(("text", args, kwargs))
        return FakeTextEntity()


def test_add_entity_to_modelspace_supports_core_types() -> None:
    converter = JSONToDWGConverter()
    msp = FakeModelspace()

    converter._add_entity_to_modelspace(
        msp,
        {"type": "line", "start": {"x": 0, "y": 0}, "end": {"x": 1, "y": 1}},
    )
    converter._add_entity_to_modelspace(
        msp,
        {
            "type": "polyline",
            "points": [{"x": 0, "y": 0}, {"x": 1, "y": 1}],
            "closed": True,
        },
    )
    converter._add_entity_to_modelspace(
        msp,
        {"type": "circle", "center": {"x": 5, "y": 6}, "radius": 2},
    )
    converter._add_entity_to_modelspace(
        msp,
        {
            "type": "arc",
            "center": {"x": 5, "y": 6},
            "radius": 2,
            "start_angle": 0,
            "end_angle": 180,
        },
    )
    converter._add_entity_to_modelspace(
        msp,
        {
            "type": "text",
            "position": {"x": 2, "y": 3},
            "content": "A",
            "height": 1.0,
            "rotation": 45.0,
        },
    )
    converter._add_entity_to_modelspace(msp, {"type": "unsupported"})

    called = [name for name, _, _ in msp.calls]
    assert called.count("line") == 1
    assert called.count("lwpolyline") == 1
    assert called.count("circle") == 1
    assert called.count("arc") == 1
    assert called.count("text") == 1


def test_convert_success_and_error_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    converter = JSONToDWGConverter()
    json_path = tmp_path / "in.json"
    output_path = tmp_path / "out.dwg"
    json_path.write_text(json.dumps({"entities": []}), encoding="utf-8")

    called = SimpleNamespace(create=None, convert=None)

    def fake_create(data, dxf_path):
        called.create = (data, dxf_path)

    def fake_convert(dxf_path, dwg_path):
        called.convert = (dxf_path, dwg_path)

    monkeypatch.setattr(converter, "_create_dxf", fake_create)
    monkeypatch.setattr(converter, "_convert_dxf_to_dwg", fake_convert)

    converter.convert(json_path, output_path)

    assert called.create is not None
    assert called.convert == (output_path.with_suffix(".dxf"), output_path)

    with pytest.raises(FileNotFoundError):
        converter.convert(tmp_path / "missing.json", output_path)

    def always_fail(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("boom")

    monkeypatch.setattr(converter, "_create_dxf", always_fail)
    with pytest.raises(RuntimeError, match="변환 중 오류 발생"):
        converter.convert(json_path, output_path)


def test_convert_dxf_to_dwg_requires_odafc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    converter = JSONToDWGConverter()
    dxf = tmp_path / "in.dxf"
    dwg = tmp_path / "out.dwg"
    dxf.write_text("0", encoding="utf-8")

    monkeypatch.setattr("img2dwg.models.converter.odafc.is_installed", lambda: False)

    with pytest.raises(RuntimeError, match="ODAFileConverter"):
        converter._convert_dxf_to_dwg(dxf, dwg)
