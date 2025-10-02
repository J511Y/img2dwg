"""DWG 파일 파싱 모듈."""

from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import subprocess
import tempfile
import shutil

import ezdxf
from ezdxf.addons import odafc

from ..utils.logger import get_logger


logger = get_logger(__name__)


class DWGParser:
    """DWG 파일을 파싱하여 JSON 형태로 변환하는 클래스."""

    def __init__(self, oda_converter_path: Optional[Path] = None):
        """
        DWGParser를 초기화한다.

        Args:
            oda_converter_path: ODAFileConverter 실행 파일 경로 (선택사항)
        """
        self.oda_converter_path = oda_converter_path
        logger.info("DWGParser 초기화")

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
                        version="ACAD2018"  # DXF R2018 버전으로 변환
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
            
            entities = []
            
            # 모델스페이스의 모든 엔티티 순회
            for entity in msp:
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
        base_data = {
            "type": entity_type.lower(),
            "layer": entity.dxf.get("layer", "0"),
            "color": entity.dxf.get("color", 256),  # 256 = BYLAYER
            "linetype": entity.dxf.get("linetype", "BYLAYER"),
        }
        
        # 엔티티 타입별 처리
        if entity_type == "LINE":
            base_data.update({
                "start": {"x": entity.dxf.start.x, "y": entity.dxf.start.y},
                "end": {"x": entity.dxf.end.x, "y": entity.dxf.end.y},
            })
            
        elif entity_type == "LWPOLYLINE":
            points = [{"x": p[0], "y": p[1]} for p in entity.get_points("xy")]
            base_data.update({
                "type": "polyline",
                "points": points,
                "closed": entity.closed,
            })
            
        elif entity_type == "CIRCLE":
            base_data.update({
                "center": {"x": entity.dxf.center.x, "y": entity.dxf.center.y},
                "radius": entity.dxf.radius,
            })
            
        elif entity_type == "ARC":
            base_data.update({
                "center": {"x": entity.dxf.center.x, "y": entity.dxf.center.y},
                "radius": entity.dxf.radius,
                "start_angle": entity.dxf.start_angle,
                "end_angle": entity.dxf.end_angle,
            })
            
        elif entity_type == "TEXT":
            base_data.update({
                "position": {"x": entity.dxf.insert.x, "y": entity.dxf.insert.y},
                "content": entity.dxf.text,
                "height": entity.dxf.height,
                "rotation": entity.dxf.get("rotation", 0.0),
            })
            
        elif entity_type == "MTEXT":
            base_data.update({
                "type": "text",  # MTEXT도 text로 통합
                "position": {"x": entity.dxf.insert.x, "y": entity.dxf.insert.y},
                "content": entity.text,
                "height": entity.dxf.char_height,
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

        return {
            "metadata": {
                "filename": dwg_path.name,
                "type": file_type,
                "source_path": str(dwg_path),
                "entity_count": len(entities),
            },
            "entities": entities,
        }

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
