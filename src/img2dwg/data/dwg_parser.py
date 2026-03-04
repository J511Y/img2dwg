"""DWG 파일 파싱 모듈."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ezdxf
from ezdxf import bbox as ezdxf_bbox
from ezdxf.addons import odafc

from ..utils.geometry import intersects_aabb, quantize_coordinate, rdp_simplify, round_coordinate
from ..utils.layout_analyzer import LayoutAnalyzer
from ..utils.logger import get_logger
from ..utils.schema_compact import CompactSchemaConverter

logger = get_logger(__name__)


@dataclass
class ParseOptions:
    """DWG 파싱 옵션."""

    include_types: list[str] = field(
        default_factory=lambda: ["LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "TEXT", "MTEXT"]
    )
    include_layers: list[str] | None = None
    exclude_layers: list[str] = field(default_factory=list)
    window: tuple[float, float, float, float] | None = None
    rdp_tolerance: float | None = None
    round_ndigits: int | None = 3
    quantize_grid: float | None = None
    drop_defaults: bool = True
    compact_schema: bool = False
    use_layout_analysis: bool = False
    dxf_version: str = "R2000"


class DWGParser:
    """DWG 파일을 파싱하여 JSON 형태로 변환하는 클래스."""

    def __init__(self, oda_converter_path: Path | None = None, options: ParseOptions | None = None):
        self.oda_converter_path = oda_converter_path
        self.options = options or ParseOptions()
        logger.info("DWGParser 초기화 (옵션: %s)", self.options)

    def parse(self, dwg_path: Path) -> dict[str, Any]:
        """DWG 파일을 파싱하여 중간 표현 JSON으로 변환한다."""
        if not dwg_path.exists():
            raise FileNotFoundError(f"DWG 파일을 찾을 수 없습니다: {dwg_path}")

        logger.info("DWG 파일 파싱 시작: %s", dwg_path)

        try:
            dxf_path = self._convert_to_dxf(dwg_path)
            entities = self._parse_dxf(dxf_path)
            result = self._create_json_structure(dwg_path, entities)
            logger.info("파싱 완료: %d개 엔티티 추출", len(entities))
            return result
        except Exception as exc:
            logger.error("DWG 파싱 실패: %s", exc)
            raise RuntimeError(f"DWG 파싱 중 오류 발생: {exc}") from exc

    def _convert_to_dxf(self, dwg_path: Path) -> Path:
        """DWG 파일을 DXF로 변환한다."""
        dxf_path = dwg_path.with_suffix(".dxf")

        if dxf_path.exists():
            logger.info("DXF 파일이 이미 존재합니다: %s", dxf_path)
            return dxf_path

        try:
            checker = getattr(odafc, "is_installed", None)
            if not callable(checker) or not checker():
                logger.warning(
                    "ODAFileConverter가 설치되지 않았습니다. "
                    "DWG 파일을 직접 파싱할 수 없습니다. "
                    "https://www.opendesign.com/guestfiles/oda_file_converter 에서 다운로드하세요."
                )
                raise RuntimeError("ODAFileConverter가 설치되지 않았습니다")

            converter = getattr(odafc, "convert", None)
            if not callable(converter):
                raise RuntimeError("odafc.convert API를 찾을 수 없습니다")

            logger.info("ODAFileConverter를 사용하여 DWG→DXF 변환 시작")
            temp_dir = Path(tempfile.mkdtemp())
            try:
                converter(
                    source=str(dwg_path),
                    dest=str(temp_dir / dxf_path.name),
                    version=self.options.dxf_version,
                )
                temp_dxf = temp_dir / dxf_path.name
                if not temp_dxf.exists():
                    raise RuntimeError("변환된 DXF 파일을 찾을 수 없습니다")
                shutil.move(str(temp_dxf), str(dxf_path))
                logger.info("DXF 변환 완료: %s", dxf_path)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as exc:
            logger.error("DWG→DXF 변환 실패: %s", exc)
            raise RuntimeError(f"DWG→DXF 변환 중 오류 발생: {exc}") from exc

        return dxf_path

    def _parse_dxf(self, dxf_path: Path) -> list[dict[str, Any]]:
        """DXF 파일을 파싱하여 엔티티 목록을 추출한다."""
        if not dxf_path.exists():
            raise FileNotFoundError(f"DXF 파일을 찾을 수 없습니다: {dxf_path}")

        try:
            logger.info("DXF 파일 파싱 시작: %s", dxf_path)
            doc = ezdxf.readfile(str(dxf_path))
            msp = doc.modelspace()

            type_query = " ".join(self.options.include_types)
            filtered_entities = list(msp.query(type_query))
            logger.info("타입 필터링 후: %d개 엔티티", len(filtered_entities))

            if self.options.include_layers:
                filtered_entities = [
                    entity
                    for entity in filtered_entities
                    if entity.dxf.get("layer", "0") in self.options.include_layers
                ]
                logger.info("레이어 포함 필터링 후: %d개 엔티티", len(filtered_entities))

            if self.options.exclude_layers:
                filtered_entities = [
                    entity
                    for entity in filtered_entities
                    if entity.dxf.get("layer", "0") not in self.options.exclude_layers
                ]
                logger.info("레이어 제외 필터링 후: %d개 엔티티", len(filtered_entities))

            if self.options.window:
                filtered_entities = self._filter_by_window(filtered_entities)
                logger.info("공간 클리핑 후: %d개 엔티티", len(filtered_entities))

            entities: list[dict[str, Any]] = []
            for entity in filtered_entities:
                try:
                    entity_data = self._convert_entity(entity)
                    if entity_data:
                        entities.append(entity_data)
                except Exception as exc:  # pragma: no cover - 엔티티 손상 케이스
                    logger.warning("엔티티 변환 실패 (%s): %s", entity.dxftype(), exc)

            logger.info("파싱 완료: %d개 엔티티 추출", len(entities))
            return entities
        except Exception as exc:
            logger.error("DXF 파싱 실패: %s", exc)
            raise RuntimeError(f"DXF 파싱 중 오류 발생: {exc}") from exc

    def _filter_by_window(self, entities: list[Any]) -> list[Any]:
        """윈도우 영역과 교차하는 엔티티만 필터링한다."""
        if not self.options.window:
            return entities

        filtered: list[Any] = []
        try:
            bboxes = list(ezdxf_bbox.multi_flat(entities, fast=True))
            for entity, entity_bbox in zip(entities, bboxes, strict=False):
                if not entity_bbox.has_data:
                    filtered.append(entity)
                    continue

                bbox_tuple = (
                    entity_bbox.extmin.x,
                    entity_bbox.extmin.y,
                    entity_bbox.extmax.x,
                    entity_bbox.extmax.y,
                )
                if intersects_aabb(bbox_tuple, self.options.window):
                    filtered.append(entity)
        except Exception as exc:  # pragma: no cover - 라이브러리 내부 실패 방어
            logger.warning("바운딩박스 필터링 실패, 모든 엔티티 포함: %s", exc)
            return entities

        return filtered

    def _process_coordinate(self, value: float) -> float:
        """좌표값을 옵션에 따라 처리한다 (반올림/양자화)."""
        if self.options.quantize_grid:
            return quantize_coordinate(value, self.options.quantize_grid)
        if self.options.round_ndigits is not None:
            return round_coordinate(value, self.options.round_ndigits)
        return value

    def _process_point(self, point: Any) -> dict[str, float]:
        """포인트를 처리한다."""
        return {
            "x": self._process_coordinate(float(point.x)),
            "y": self._process_coordinate(float(point.y)),
        }

    def _polyline_points(self, entity: Any) -> list[tuple[float, float]]:
        entity_type = entity.dxftype()
        if entity_type == "LWPOLYLINE":
            return [(float(x), float(y)) for x, y, *_ in entity.get_points("xy")]

        vertices = getattr(entity, "vertices", [])
        points: list[tuple[float, float]] = []
        for vertex in vertices:
            location = vertex.dxf.location
            points.append((float(location.x), float(location.y)))
        return points

    def _polyline_closed(self, entity: Any) -> bool:
        entity_type = entity.dxftype()
        if entity_type == "LWPOLYLINE":
            return bool(getattr(entity, "closed", False))

        is_closed = getattr(entity, "is_closed", None)
        if callable(is_closed):
            return bool(is_closed())
        if is_closed is not None:
            return bool(is_closed)

        flags = int(entity.dxf.get("flags", 0))
        return bool(flags & 1)

    def _convert_entity(self, entity: Any) -> dict[str, Any] | None:
        """ezdxf 엔티티를 JSON 형태로 변환한다."""
        entity_type = entity.dxftype()

        layer = entity.dxf.get("layer", "0")
        color = entity.dxf.get("color", 256)
        linetype = entity.dxf.get("linetype", "BYLAYER")

        base_data: dict[str, Any] = {"type": entity_type.lower()}

        if not self.options.drop_defaults or layer != "0":
            base_data["layer"] = layer
        if not self.options.drop_defaults or color != 256:
            base_data["color"] = color
        if not self.options.drop_defaults or linetype != "BYLAYER":
            base_data["linetype"] = linetype

        if entity_type == "LINE":
            base_data.update(
                {
                    "start": self._process_point(entity.dxf.start),
                    "end": self._process_point(entity.dxf.end),
                }
            )
        elif entity_type in {"LWPOLYLINE", "POLYLINE"}:
            points = self._polyline_points(entity)
            if self.options.rdp_tolerance and len(points) > 2:
                points = rdp_simplify(points, self.options.rdp_tolerance)

            base_data.update(
                {
                    "type": "polyline",
                    "points": [
                        {
                            "x": self._process_coordinate(point[0]),
                            "y": self._process_coordinate(point[1]),
                        }
                        for point in points
                    ],
                    "closed": self._polyline_closed(entity),
                }
            )
        elif entity_type == "CIRCLE":
            base_data.update(
                {
                    "center": self._process_point(entity.dxf.center),
                    "radius": self._process_coordinate(float(entity.dxf.radius)),
                }
            )
        elif entity_type == "ARC":
            base_data.update(
                {
                    "center": self._process_point(entity.dxf.center),
                    "radius": self._process_coordinate(float(entity.dxf.radius)),
                    "start_angle": round(float(entity.dxf.start_angle), 2),
                    "end_angle": round(float(entity.dxf.end_angle), 2),
                }
            )
        elif entity_type == "TEXT":
            rotation = float(entity.dxf.get("rotation", 0.0))
            base_data.update(
                {
                    "position": self._process_point(entity.dxf.insert),
                    "content": entity.dxf.text,
                    "height": self._process_coordinate(float(entity.dxf.height)),
                }
            )
            if not self.options.drop_defaults or rotation != 0.0:
                base_data["rotation"] = round(rotation, 2)
        elif entity_type == "MTEXT":
            base_data.update(
                {
                    "type": "text",
                    "position": self._process_point(entity.dxf.insert),
                    "content": entity.text,
                    "height": self._process_coordinate(float(entity.dxf.char_height)),
                }
            )
        elif entity_type in {"DIMENSION", "INSERT", "HATCH", "SPLINE"}:
            base_data.update({"info": f"{entity_type} entity (simplified)"})
        else:
            logger.debug("지원하지 않는 엔티티 타입: %s", entity_type)
            return None

        return base_data

    def _create_json_structure(
        self, dwg_path: Path, entities: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """최종 JSON 구조를 생성한다."""
        filename = dwg_path.name.lower()
        file_type = "변경" if "변경" in filename else "단면" if "단면" in filename else "기타"

        result: dict[str, Any]
        if self.options.use_layout_analysis:
            analyzer = LayoutAnalyzer()
            layout = analyzer.analyze(entities)
            result = {
                "metadata": {
                    "filename": dwg_path.name,
                    "type": file_type,
                    "source_path": str(dwg_path),
                    "representation": "layout",
                    "original_entities": layout["statistics"]["original_entities"],
                    "compression_ratio": layout["statistics"]["compression_ratio"],
                },
                "layout": {
                    "walls": layout["walls"],
                    "rooms": layout["rooms"],
                    "openings": layout["openings"],
                    "annotations": layout["annotations"],
                    "patterns": layout["patterns"],
                },
            }
            logger.info(
                "레이아웃 분석 완료: %s개 엔티티 → %s개 벽, %s개 방 (압축률: %s%%)",
                layout["statistics"]["original_entities"],
                len(layout["walls"]),
                len(layout["rooms"]),
                layout["statistics"]["compression_ratio"],
            )
        else:
            result = {
                "metadata": {
                    "filename": dwg_path.name,
                    "type": file_type,
                    "source_path": str(dwg_path),
                    "entity_count": len(entities),
                },
                "entities": entities,
            }

        if self.options.compact_schema and not self.options.use_layout_analysis:
            converter = CompactSchemaConverter(use_local_coords=True)
            result = converter.compact(result)
            logger.info("Compact 스키마 적용 완료")

        return result

    def save_json(self, data: dict[str, Any], output_path: Path) -> None:
        """JSON 데이터를 파일로 저장한다."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        logger.info("JSON 저장 완료: %s", output_path)
