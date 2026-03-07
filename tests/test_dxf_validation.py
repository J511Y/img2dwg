from __future__ import annotations

from pathlib import Path

import ezdxf

from img2dwg.web.dxf_validation import inspect_dxf


def _write_dxf(path: Path, *, with_entity: bool) -> None:
    doc = ezdxf.new("R2018")
    if with_entity:
        doc.modelspace().add_line((0, 0), (100, 50))
    doc.saveas(path)


def test_inspect_dxf_valid_minimal_file(tmp_path: Path) -> None:
    dxf_path = tmp_path / "valid.dxf"
    _write_dxf(dxf_path, with_entity=True)

    inspection = inspect_dxf(dxf_path)

    assert inspection.validation.parse_ok is True
    assert inspection.validation.is_valid is True
    assert inspection.validation.entity_count >= 1
    assert inspection.validation.drawable_entity_count >= 1
    assert inspection.validation.errors == []
    assert inspection.preview.kind == "svg"
    assert "<svg" in inspection.preview.content


def test_inspect_dxf_empty_modelspace_reports_non_drawable(tmp_path: Path) -> None:
    dxf_path = tmp_path / "empty.dxf"
    _write_dxf(dxf_path, with_entity=False)

    inspection = inspect_dxf(dxf_path)

    assert inspection.validation.parse_ok is True
    assert inspection.validation.is_valid is False
    assert inspection.validation.entity_count == 0
    assert inspection.validation.drawable_entity_count == 0
    assert any("모델스페이스가 비어" in item for item in inspection.validation.warnings)
    assert inspection.preview.kind == "text"
    assert "drawable_entities: 0" in inspection.preview.content


def test_inspect_dxf_corrupt_file_reports_parse_failure(tmp_path: Path) -> None:
    dxf_path = tmp_path / "corrupt.dxf"
    dxf_path.write_text("this is not a valid dxf payload", encoding="utf-8")

    inspection = inspect_dxf(dxf_path)

    assert inspection.validation.parse_ok is False
    assert inspection.validation.is_valid is False
    assert any("DXF 파싱 실패" in item for item in inspection.validation.errors)
    assert inspection.preview.kind == "text"
    assert "parse_ok: False" in inspection.preview.content
