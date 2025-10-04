"""DWG 파일 파싱 모듈."""

from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import json
import subprocess
import tempfile
import shutil

import ezdxf
from ezdxf.addons import odafc
from ezdxf import bbox as ezdxf_bbox

from ..utils.logger import get_logger
from ..utils.geometry import (
    rdp_simplify,
    round_coordinate,
    quantize_coordinate,
    intersects_aabb,
)
from ..utils.schema_compact import CompactSchemaConverter
from ..utils.layout_analyzer import LayoutAnalyzer


logger = get_logger(__name__)


@dataclass
class ParseOptions:
    """
    DWG 파싱 옵션.
    
    Attributes:
        include_types: 포함할 엔티티 타입 리스트 (기본: 주요 타입만)
        include_layers: 포함할 레이어 리스트 (None이면 모두 포함)
        exclude_layers: 제외할 레이어 리스트
        window: 공간 클리핑 윈도우 (xmin, ymin, xmax, ymax)
        rdp_tolerance: RDP 간소화 허용 오차 (None이면 간소화 안 함)
        round_ndigits: 좌표 반올림 소수점 자리수 (None이면 반올림 안 함)
        quantize_grid: 그리드 양자화 크기 (None이면 양자화 안 함)
        drop_defaults: 기본값 속성 제거 여부
        compact_schema: 단축 스키마 사용 여부
        dxf_version: DXF 변환 버전 (R12, R2000, R2018 등)
    """
    include_types: List[str] = field(default_factory=lambda: [
        "LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "TEXT", "MTEXT"
    ])
    include_layers: Optional[List[str]] = None
    exclude_layers: List[str] = field(default_factory=list)
    window: Optional[Tuple[float, float, float, float]] = None
    rdp_tolerance: Optional[float] = None
    round_ndigits: Optional[int] = 3
    quantize_grid: Optional[float] = None
    drop_defaults: bool = True
    compact_schema: bool = False
    use_layout_analysis: bool = False  # 고수준 레이아웃 분석 사용
    dxf_version: str = "R2000"


class DWGParser:
    """DWG 파일을 파싱하여 JSON 형태로 변환하는 클래스."""

    def __init__(
        self,
        oda_converter_path: Optional[Path] = None,
        options: Optional[ParseOptions] = None,
    ):
        """
        DWGParser를 초기화한다.

        Args:
            oda_converter_path: ODAFileConverter 실행 파일 경로 (선택사항)
            options: 파싱 옵션 (None이면 기본값 사용)
        """
        self.oda_converter_path = oda_converter_path
        self.options = options or ParseOptions()
        logger.info(f"DWGParser 초기화 (옵션: {self.options})")

    def parse(self, dwg_path: Path) -> Dict[str, Any]:
        """
        DWG 파일을 파싱하여 중간 표현 JSON으로 변환한다.

        Args:
            dwg_path: DWG 파일 경로

        Returns:
            파싱된 데이터 딕셔너리

        Raises:
            FileNotFoundError: DWG 파일이 존재하지 않을 때
            RuntimeError: 파싱 중 오류 발생 시
        """
        if not dwg_path.exists():
            raise FileNotFoundError(f"DWG 파일을 찾을 수 없습니다: {dwg_path}")

        logger.info(f"DWG 파일 파싱 시작: {dwg_path}")

        try:
            # Step 1: DWG → DXF 변환
            dxf_path = self._convert_to_dxf(dwg_path)

            # Step 2: DXF 파싱
            entities = self._parse_dxf(dxf_path)

            # Step 3: JSON 형태로 변환
            result = self._create_json_structure(dwg_path, entities)

            logger.info(f"파싱 완료: {len(entities)}개 엔티티 추출")
            return result

        except Exception as e:
            logger.error(f"DWG 파싱 실패: {e}")
            raise RuntimeError(f"DWG 파싱 중 오류 발생: {e}") from e

    def _convert_to_dxf(self, dwg_path: Path) -> Path:
        """
        DWG 파일을 DXF로 변환한다.

        Args:
            dwg_path: DWG 파일 경로

        Returns:
            변환된 DXF 파일 경로

        Raises:
            RuntimeError: 변환 실패 시
        """
        # DXF 파일 경로
        dxf_path = dwg_path.with_suffix(".dxf")
        
        # DXF 파일이 이미 존재하면 그대로 사용
        if dxf_path.exists():
            logger.info(f"DXF 파일이 이미 존재합니다: {dxf_path}")
            return dxf_path
        
        try:
            # ODAFileConverter가 설치되어 있는지 확인
            if odafc.is_installed():
                logger.info("ODAFileConverter를 사용하여 DWG→DXF 변환 시작")
                
                # 임시 폴더에 변환
                temp_dir = Path(tempfile.mkdtemp())
                try:
                    # ODA File Converter를 사용한 변환
                    odafc.convert(
                        source=str(dwg_path),
                        dest=str(temp_dir / dxf_path.name),
                        version=self.options.dxf_version  # 설정된 DXF 버전으로 변환
                    )
                    
                    # 변환된 파일을 원래 위치로 이동
                    temp_dxf = temp_dir / dxf_path.name
                    if temp_dxf.exists():
                        shutil.move(str(temp_dxf), str(dxf_path))
                        logger.info(f"DXF 변환 완료: {dxf_path}")
                    else:
                        raise RuntimeError("변환된 DXF 파일을 찾을 수 없습니다")
                finally:
                    # 임시 폴더 정리
                    shutil.rmtree(temp_dir, ignore_errors=True)
            else:
                # ODAFileConverter가 없으면 경고 출력
                logger.warning(
                    "ODAFileConverter가 설치되지 않았습니다. "
                    "DWG 파일을 직접 파싱할 수 없습니다. "
                    "https://www.opendesign.com/guestfiles/oda_file_converter 에서 다운로드하세요."
                )
                raise RuntimeError("ODAFileConverter가 설치되지 않았습니다")
                
        except Exception as e:
            logger.error(f"DWG→DXF 변환 실패: {e}")
            raise RuntimeError(f"DWG→DXF 변환 중 오류 발생: {e}") from e
        
        return dxf_path

    def _parse_dxf(self, dxf_path: Path) -> List[Dict[str, Any]]:
        """
        DXF 파일을 파싱하여 엔티티 목록을 추출한다.

        Args:
            dxf_path: DXF 파일 경로

        Returns:
            엔티티 딕셔너리 리스트

        Raises:
            RuntimeError: 파싱 실패 시
        """
        if not dxf_path.exists():
            raise FileNotFoundError(f"DXF 파일을 찾을 수 없습니다: {dxf_path}")
        
        try:
            logger.info(f"DXF 파일 파싱 시작: {dxf_path}")
            
            # DXF 파일 읽기
            doc = ezdxf.readfile(str(dxf_path))
            msp = doc.modelspace()
            
            # 1단계: 타입 필터링
            type_query = " ".join(self.options.include_types)
            filtered_entities = list(msp.query(type_query))
            logger.info(f"타입 필터링 후: {len(filtered_entities)}개 엔티티")
            
            # 2단계: 레이어 필터링
            if self.options.include_layers:
                filtered_entities = [
                    e for e in filtered_entities
                    if e.dxf.get("layer", "0") in self.options.include_layers
                ]
                logger.info(f"레이어 포함 필터링 후: {len(filtered_entities)}개 엔티티")
            
            if self.options.exclude_layers:
                filtered_entities = [
                    e for e in filtered_entities
                    if e.dxf.get("layer", "0") not in self.options.exclude_layers
                ]
                logger.info(f"레이어 제외 필터링 후: {len(filtered_entities)}개 엔티티")
            
            # 3단계: 공간 클리핑 (window가 지정된 경우)
            if self.options.window:
                filtered_entities = self._filter_by_window(filtered_entities)
                logger.info(f"공간 클리핑 후: {len(filtered_entities)}개 엔티티")
            
            # 4단계: 엔티티 변환
            entities = []
            for entity in filtered_entities:
                try:
                    entity_data = self._convert_entity(entity)
                    if entity_data:
                        entities.append(entity_data)
                except Exception as e:
                    logger.warning(f"엔티티 변환 실패 ({entity.dxftype()}): {e}")
                    continue
            
            logger.info(f"파싱 완료: {len(entities)}개 엔티티 추출")
            return entities
            
        except Exception as e:
            logger.error(f"DXF 파싱 실패: {e}")
            raise RuntimeError(f"DXF 파싱 중 오류 발생: {e}") from e
    
    def _filter_by_window(self, entities: List[Any]) -> List[Any]:
        """
        윈도우 영역과 교차하는 엔티티만 필터링한다.
        
        Args:
            entities: 엔티티 리스트
        
        Returns:
            필터링된 엔티티 리스트
        """
        if not self.options.window:
            return entities
        
        filtered = []
        try:
            # 바운딩박스 계산 (fast=True로 빠른 계산)
            bboxes = list(ezdxf_bbox.multi_flat(entities, fast=True))
            
            for entity, entity_bbox in zip(entities, bboxes):
                if entity_bbox.has_data:
                    bbox_tuple = (
                        entity_bbox.extmin.x,
                        entity_bbox.extmin.y,
                        entity_bbox.extmax.x,
                        entity_bbox.extmax.y,
                    )
                    if intersects_aabb(bbox_tuple, self.options.window):
                        filtered.append(entity)
                else:
                    # bbox가 없는 엔티티는 포함 (안전)
                    filtered.append(entity)
        except Exception as e:
            logger.warning(f"바운딩박스 필터링 실패, 모든 엔티티 포함: {e}")
            return entities
        
        return filtered
    
    def _process_coordinate(self, value: float) -> float:
        """
        좌표값을 옵션에 따라 처리한다 (반올림/양자화).
        
        Args:
            value: 원본 좌표값
        
        Returns:
            처리된 좌표값
        """
        if self.options.quantize_grid:
            return quantize_coordinate(value, self.options.quantize_grid)
        elif self.options.round_ndigits is not None:
            return round_coordinate(value, self.options.round_ndigits)
        return value
    
    def _process_point(self, point: Any) -> Dict[str, float]:
        """
        포인트를 처리한다.
        
        Args:
            point: ezdxf 포인트 객체
        
        Returns:
            처리된 포인트 딕셔너리
        """
        return {
            "x": self._process_coordinate(point.x),
            "y": self._process_coordinate(point.y),
        }
    
    def _convert_entity(self, entity: Any) -> Optional[Dict[str, Any]]:
        """
        ezdxf 엔티티를 JSON 형태로 변환한다.

        Args:
            entity: ezdxf 엔티티 객체

        Returns:
            엔티티 딕셔너리 또는 None (지원하지 않는 타입)
        """
        entity_type = entity.dxftype()
        
        # 공통 속성
        layer = entity.dxf.get("layer", "0")
        color = entity.dxf.get("color", 256)  # 256 = BYLAYER
        linetype = entity.dxf.get("linetype", "BYLAYER")
        
        base_data = {
            "type": entity_type.lower(),
        }
        
        # 기본값이 아닌 경우만 추가 (drop_defaults 옵션)
        if not self.options.drop_defaults or layer != "0":
            base_data["layer"] = layer
        if not self.options.drop_defaults or color != 256:
            base_data["color"] = color
        if not self.options.drop_defaults or linetype != "BYLAYER":
            base_data["linetype"] = linetype
        
        # 엔티티 타입별 처리
        if entity_type == "LINE":
            base_data.update({
                "start": self._process_point(entity.dxf.start),
                "end": self._process_point(entity.dxf.end),
            })
            
        elif entity_type == "LWPOLYLINE" or entity_type == "POLYLINE":
            points = [(p[0], p[1]) for p in entity.get_points("xy")]
            
            # RDP 간소화 적용
            if self.options.rdp_tolerance and len(points) > 2:
                points = rdp_simplify(points, self.options.rdp_tolerance)
            
            # 좌표 처리
            processed_points = [
                {"x": self._process_coordinate(p[0]), "y": self._process_coordinate(p[1])}
                for p in points
            ]
            
            base_data.update({
                "type": "polyline",
                "points": processed_points,
                "closed": entity.closed,
            })
            
        elif entity_type == "CIRCLE":
            base_data.update({
                "center": self._process_point(entity.dxf.center),
                "radius": self._process_coordinate(entity.dxf.radius),
            })
            
        elif entity_type == "ARC":
            base_data.update({
                "center": self._process_point(entity.dxf.center),
                "radius": self._process_coordinate(entity.dxf.radius),
                "start_angle": round(entity.dxf.start_angle, 2),
                "end_angle": round(entity.dxf.end_angle, 2),
            })
            
        elif entity_type == "TEXT":
            rotation = entity.dxf.get("rotation", 0.0)
            base_data.update({
                "position": self._process_point(entity.dxf.insert),
                "content": entity.dxf.text,
                "height": self._process_coordinate(entity.dxf.height),
            })
            # rotation이 0이 아닌 경우만 추가
            if not self.options.drop_defaults or rotation != 0.0:
                base_data["rotation"] = round(rotation, 2)
            
        elif entity_type == "MTEXT":
            base_data.update({
                "type": "text",  # MTEXT도 text로 통합
                "position": self._process_point(entity.dxf.insert),
                "content": entity.text,
                "height": self._process_coordinate(entity.dxf.char_height),
            })
            
        elif entity_type in ["DIMENSION", "INSERT", "HATCH", "SPLINE"]:
            # 지원하지만 간단한 정보만 저장
            base_data.update({
                "info": f"{entity_type} entity (simplified)",
            })
            
        else:
            # 지원하지 않는 엔티티 타입
            logger.debug(f"지원하지 않는 엔티티 타입: {entity_type}")
            return None
        
        return base_data

    def _create_json_structure(
        self,
        dwg_path: Path,
        entities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        최종 JSON 구조를 생성한다.

        Args:
            dwg_path: 원본 DWG 파일 경로
            entities: 엔티티 리스트

        Returns:
            JSON 구조 딕셔너리
        """
        # 파일명에서 타입 추출
        filename = dwg_path.name.lower()
        file_type = "변경" if "변경" in filename else "단면" if "단면" in filename else "기타"

        # 레이아웃 분석 적용
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
                }
            }
            logger.info(f"레이아웃 분석 완료: {layout['statistics']['original_entities']}개 엔티티 → "
                       f"{len(layout['walls'])}개 벽, {len(layout['rooms'])}개 방 "
                       f"(압축률: {layout['statistics']['compression_ratio']}%)")
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
        
        # Compact 스키마 적용
        if self.options.compact_schema and not self.options.use_layout_analysis:
            converter = CompactSchemaConverter(use_local_coords=True)
            result = converter.compact(result)
            logger.info("Compact 스키마 적용 완료")
        
        return result

    def save_json(self, data: Dict[str, Any], output_path: Path) -> None:
        """
        JSON 데이터를 파일로 저장한다.

        Args:
            data: 저장할 데이터
            output_path: 출력 파일 경로
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON 저장 완료: {output_path}")
