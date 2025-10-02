"""JSON→DWG 변환 모듈."""

from pathlib import Path
from typing import Dict, Any
import json
import tempfile
import shutil

import ezdxf
from ezdxf.addons import odafc

from ..utils.logger import get_logger


logger = get_logger(__name__)


class JSONToDWGConverter:
    """JSON 형태의 중간 표현을 DWG 파일로 변환하는 클래스."""

    def __init__(self):
        """JSONToDWGConverter를 초기화한다."""
        logger.info("JSONToDWGConverter 초기화")

    def convert(self, json_path: Path, output_path: Path) -> None:
        """
        JSON 파일을 DWG 파일로 변환한다.

        Args:
            json_path: 입력 JSON 파일 경로
            output_path: 출력 DWG 파일 경로

        Raises:
            FileNotFoundError: JSON 파일이 존재하지 않을 때
            RuntimeError: 변환 중 오류 발생 시

        Note:
            실제 구현 시 ezdxf + ODAFileConverter 사용
            현재는 스텁(stub) 구현
        """
        if not json_path.exists():
            raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_path}")

        logger.info(f"JSON→DWG 변환 시작: {json_path}")

        try:
            # Step 1: JSON 로드
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Step 2: DXF 생성
            dxf_path = output_path.with_suffix(".dxf")
            self._create_dxf(data, dxf_path)

            # Step 3: DXF → DWG 변환
            self._convert_dxf_to_dwg(dxf_path, output_path)

            logger.info(f"변환 완료: {output_path}")

        except Exception as e:
            logger.error(f"JSON→DWG 변환 실패: {e}")
            raise RuntimeError(f"변환 중 오류 발생: {e}") from e

    def _create_dxf(self, data: Dict[str, Any], dxf_path: Path) -> None:
        """
        JSON 데이터로부터 DXF 파일을 생성한다.

        Args:
            data: JSON 데이터
            dxf_path: 출력 DXF 파일 경로

        Raises:
            RuntimeError: DXF 생성 실패 시
        """
        try:
            # 새 DXF 문서 생성 (R2018 버전)
            doc = ezdxf.new("R2018", setup=True)
            msp = doc.modelspace()
            
            # 엔티티 추가
            for entity in data.get("entities", []):
                try:
                    self._add_entity_to_modelspace(msp, entity)
                except Exception as e:
                    logger.warning(f"엔티티 추가 실패 ({entity.get('type', 'unknown')}): {e}")
                    continue
            
            # DXF 파일 저장
            dxf_path.parent.mkdir(parents=True, exist_ok=True)
            doc.saveas(str(dxf_path))
            
            logger.info(f"DXF 생성 완료: {dxf_path}")
            
        except Exception as e:
            logger.error(f"DXF 생성 실패: {e}")
            raise RuntimeError(f"DXF 생성 중 오류 발생: {e}") from e
    
    def _add_entity_to_modelspace(self, msp: Any, entity: Dict[str, Any]) -> None:
        """
        JSON 엔티티를 modelspace에 추가한다.

        Args:
            msp: modelspace 객체
            entity: 엔티티 데이터
        """
        entity_type = entity.get("type", "").lower()
        layer = entity.get("layer", "0")
        color = entity.get("color", 256)
        linetype = entity.get("linetype", "BYLAYER")
        
        # 공통 속성
        dxfattribs = {
            "layer": layer,
            "color": color,
            "linetype": linetype,
        }
        
        if entity_type == "line":
            start = entity["start"]
            end = entity["end"]
            msp.add_line(
                (start["x"], start["y"]),
                (end["x"], end["y"]),
                dxfattribs=dxfattribs
            )
            
        elif entity_type == "polyline":
            points = [(p["x"], p["y"]) for p in entity["points"]]
            closed = entity.get("closed", False)
            msp.add_lwpolyline(points, close=closed, dxfattribs=dxfattribs)
            
        elif entity_type == "circle":
            center = entity["center"]
            radius = entity["radius"]
            msp.add_circle(
                (center["x"], center["y"]),
                radius,
                dxfattribs=dxfattribs
            )
            
        elif entity_type == "arc":
            center = entity["center"]
            radius = entity["radius"]
            start_angle = entity["start_angle"]
            end_angle = entity["end_angle"]
            msp.add_arc(
                (center["x"], center["y"]),
                radius,
                start_angle,
                end_angle,
                dxfattribs=dxfattribs
            )
            
        elif entity_type == "text":
            position = entity["position"]
            content = entity["content"]
            height = entity.get("height", 2.5)
            rotation = entity.get("rotation", 0.0)
            
            dxfattribs.update({
                "height": height,
                "rotation": rotation,
            })
            
            msp.add_text(
                content,
                dxfattribs=dxfattribs
            ).set_placement(
                (position["x"], position["y"]),
                align=ezdxf.enums.TextEntityAlignment.LEFT
            )
            
        else:
            logger.debug(f"지원하지 않는 엔티티 타입: {entity_type}")

    def _convert_dxf_to_dwg(self, dxf_path: Path, dwg_path: Path) -> None:
        """
        DXF 파일을 DWG로 변환한다.

        Args:
            dxf_path: 입력 DXF 파일 경로
            dwg_path: 출력 DWG 파일 경로

        Raises:
            RuntimeError: 변환 실패 시
        """
        try:
            if odafc.is_installed():
                logger.info("ODAFileConverter를 사용하여 DXF→DWG 변환 시작")
                
                # 임시 폴더에 변환
                temp_dir = Path(tempfile.mkdtemp())
                try:
                    # ODA File Converter를 사용한 변환
                    odafc.convert(
                        source=str(dxf_path),
                        dest=str(temp_dir / dwg_path.name),
                        version="ACAD2018"  # DWG R2018 버전으로 변환
                    )
                    
                    # 변환된 파일을 원래 위치로 이동
                    temp_dwg = temp_dir / dwg_path.name
                    if temp_dwg.exists():
                        dwg_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(temp_dwg), str(dwg_path))
                        logger.info(f"DWG 변환 완료: {dwg_path}")
                    else:
                        raise RuntimeError("변환된 DWG 파일을 찾을 수 없습니다")
                finally:
                    # 임시 폴더 정리
                    shutil.rmtree(temp_dir, ignore_errors=True)
            else:
                logger.warning(
                    "ODAFileConverter가 설치되지 않았습니다. "
                    "DXF 파일만 생성됩니다. "
                    "https://www.opendesign.com/guestfiles/oda_file_converter 에서 다운로드하세요."
                )
                raise RuntimeError("ODAFileConverter가 설치되지 않았습니다")
                
        except Exception as e:
            logger.error(f"DXF→DWG 변환 실패: {e}")
            raise RuntimeError(f"DXF→DWG 변환 중 오류 발생: {e}") from e
