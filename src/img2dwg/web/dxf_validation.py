from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
from typing import Any

import ezdxf
from ezdxf import bbox
from ezdxf.addons.drawing import Frontend, RenderContext, layout
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.document import Drawing
from ezdxf.entities.dxfgfx import DXFGraphic

MAX_AUDIT_MESSAGES = 10


@dataclass(slots=True)
class DxfValidationResult:
    path: Path
    parse_ok: bool
    is_valid: bool
    entity_count: int = 0
    drawable_entity_count: int = 0
    entity_types: dict[str, int] = field(default_factory=dict)
    bbox_available: bool = False
    bbox_min: tuple[float, float, float] | None = None
    bbox_max: tuple[float, float, float] | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DxfPreviewResult:
    kind: str
    content: str
    message: str | None = None


@dataclass(slots=True)
class DxfInspectionResult:
    validation: DxfValidationResult
    preview: DxfPreviewResult


def inspect_dxf(path: Path) -> DxfInspectionResult:
    """Read, audit, and preview a DXF file in a single pass."""
    try:
        document = ezdxf.readfile(path)
    except Exception as exc:
        validation = DxfValidationResult(
            path=path,
            parse_ok=False,
            is_valid=False,
            errors=[f"DXF 파싱 실패: {exc}"],
            warnings=[
                "생성된 DXF가 손상되었거나 형식이 잘못되었습니다. "
                "다른 전략으로 재시도하거나 입력 이미지를 확인해 주세요."
            ],
        )
        return DxfInspectionResult(
            validation=validation,
            preview=DxfPreviewResult(
                kind="text",
                content=build_text_preview(validation),
                message="유효한 DXF 문서를 읽지 못해 시각 미리보기를 만들 수 없습니다.",
            ),
        )

    validation = validate_loaded_dxf(path, document)

    if validation.drawable_entity_count <= 0:
        preview = DxfPreviewResult(
            kind="text",
            content=build_text_preview(validation),
            message="렌더링 가능한 엔티티가 없어 시각 미리보기를 생성할 수 없습니다.",
        )
        return DxfInspectionResult(validation=validation, preview=preview)

    try:
        svg = render_dxf_to_svg(document)
    except Exception as exc:
        validation.warnings.append(
            "SVG 미리보기를 생성하지 못했습니다. "
            "아래 텍스트 요약으로 엔티티/감사 상태를 확인해 주세요."
        )
        preview = DxfPreviewResult(
            kind="text",
            content=build_text_preview(validation),
            message=f"SVG 렌더링 실패: {exc}",
        )
        return DxfInspectionResult(validation=validation, preview=preview)

    return DxfInspectionResult(
        validation=validation,
        preview=DxfPreviewResult(kind="svg", content=svg),
    )


def validate_loaded_dxf(path: Path, document: Drawing) -> DxfValidationResult:
    modelspace = document.modelspace()

    entities = list(modelspace)
    entity_types = Counter(entity.dxftype() for entity in entities)
    drawable_entities = [entity for entity in entities if _is_drawable_entity(entity)]

    errors: list[str] = []
    warnings: list[str] = []

    if not entities:
        warnings.append(
            "모델스페이스가 비어 있습니다. 변환 결과가 비어 있을 수 있으니 입력 이미지/전략을 확인해 주세요."
        )

    if entities and not drawable_entities:
        warnings.append(
            "모델스페이스에 도형으로 렌더링 가능한 엔티티가 없습니다. "
            "TEXT/LINE/LWPOLYLINE 등 도면 엔티티가 생성되었는지 확인해 주세요."
        )

    audit_errors, audit_fixes = _run_audit(document)
    if audit_errors:
        errors.extend(audit_errors)
    if audit_fixes:
        warnings.extend(audit_fixes)

    box = bbox.extents(modelspace)
    bbox_available = bool(box.has_data)
    if not bbox_available and drawable_entities:
        warnings.append(
            "도면 경계 상자를 계산하지 못했습니다. 일부 엔티티가 비정상 좌표를 가질 수 있습니다."
        )

    is_valid = not errors and len(drawable_entities) > 0

    return DxfValidationResult(
        path=path,
        parse_ok=True,
        is_valid=is_valid,
        entity_count=len(entities),
        drawable_entity_count=len(drawable_entities),
        entity_types=dict(sorted(entity_types.items())),
        bbox_available=bbox_available,
        bbox_min=tuple(box.extmin) if bbox_available else None,
        bbox_max=tuple(box.extmax) if bbox_available else None,
        errors=errors,
        warnings=warnings,
    )


def _run_audit(document: Drawing) -> tuple[list[str], list[str]]:
    auditor = document.audit()
    raw_errors = list(getattr(auditor, "errors", []))
    raw_fixes = list(getattr(auditor, "fixed_errors", []) or [])

    errors = _format_audit_entries(raw_errors, label="AUDIT 오류")
    fixes = _format_audit_entries(raw_fixes, label="AUDIT 자동수정")
    return errors, fixes


def _format_audit_entries(entries: list[object], *, label: str) -> list[str]:
    if not entries:
        return []

    messages: list[str] = []
    for entry in entries[:MAX_AUDIT_MESSAGES]:
        text = _audit_entry_to_text(entry)
        messages.append(f"{label}: {text}")

    hidden_count = len(entries) - len(messages)
    if hidden_count > 0:
        messages.append(f"{label}: 추가 {hidden_count}건은 생략되었습니다.")

    return messages


def _audit_entry_to_text(entry: object) -> str:
    message = getattr(entry, "message", None)
    if isinstance(message, str) and message.strip():
        return message.strip()
    return str(entry)


def _is_drawable_entity(entity: object) -> bool:
    if not isinstance(entity, DXFGraphic):
        return False
    invisible = int(getattr(entity.dxf, "invisible", 0))
    return invisible == 0


def render_dxf_to_svg(document: Drawing) -> str:
    modelspace = document.modelspace()
    page = _build_svg_page(modelspace)
    backend = SVGBackend()
    frontend = Frontend(RenderContext(document), backend)
    frontend.draw_layout(modelspace, finalize=True)
    svg_text = backend.get_string(page)
    return _strip_xml_declaration(svg_text)


def _build_svg_page(modelspace: Any) -> layout.Page:
    extents = bbox.extents(modelspace)

    if not extents.has_data:
        return layout.Page(width=200.0, height=200.0, units=layout.Units.mm)

    width_raw, height_raw, _ = extents.size
    width = _safe_extent(width_raw, fallback=120.0)
    height = _safe_extent(height_raw, fallback=120.0)

    target_max_mm = 240.0
    longest = max(width, height)
    scale = target_max_mm / longest if longest > 0 else 1.0

    page_width = max(80.0, width * scale)
    page_height = max(80.0, height * scale)
    return layout.Page(width=page_width, height=page_height, units=layout.Units.mm)


def _safe_extent(value: float, *, fallback: float) -> float:
    if not isfinite(value) or value <= 0:
        return fallback
    return value


def _strip_xml_declaration(svg_text: str) -> str:
    if not svg_text.startswith("<?xml"):
        return svg_text

    lines = svg_text.splitlines()
    if len(lines) <= 1:
        return svg_text
    return "\n".join(lines[1:])


def build_text_preview(result: DxfValidationResult) -> str:
    lines = [
        f"file: {result.path}",
        f"parse_ok: {result.parse_ok}",
        f"is_valid: {result.is_valid}",
        f"entities: {result.entity_count}",
        f"drawable_entities: {result.drawable_entity_count}",
    ]

    if result.entity_types:
        lines.append("entity_types:")
        for entity_name, count in result.entity_types.items():
            lines.append(f"  - {entity_name}: {count}")

    if result.bbox_available and result.bbox_min and result.bbox_max:
        lines.append(f"bbox_min: {result.bbox_min}")
        lines.append(f"bbox_max: {result.bbox_max}")

    if result.errors:
        lines.append("errors:")
        for error in result.errors:
            lines.append(f"  - {error}")

    if result.warnings:
        lines.append("warnings:")
        for warning in result.warnings:
            lines.append(f"  - {warning}")

    return "\n".join(lines)
