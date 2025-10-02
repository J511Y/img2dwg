"""DWG 파일 파싱 모듈."""

from pathlib import Path
from typing import Dict, List, Any, Optional
import json

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

        Note:
            실제 구현 시 ODAFileConverter 또는 AutoCAD API 사용
            현재는 스텁(stub) 구현
        """
        dxf_path = dwg_path.with_suffix(".dxf")
        
        # TODO: ODAFileConverter를 사용한 실제 변환 구현
        # 예: subprocess.run([self.oda_converter_path, dwg_path, ...])
        
        logger.warning(
            "DWG→DXF 변환은 현재 스텁 구현입니다. "
            "ODAFileConverter 또는 AutoCAD API를 설정하세요."
        )
        
        return dxf_path

    def _parse_dxf(self, dxf_path: Path) -> List[Dict[str, Any]]:
        """
        DXF 파일을 파싱하여 엔티티 목록을 추출한다.

        Args:
            dxf_path: DXF 파일 경로

        Returns:
            엔티티 딕셔너리 리스트

        Note:
            실제 구현 시 ezdxf 라이브러리 사용
            현재는 스텁(stub) 구현
        """
        # TODO: ezdxf를 사용한 실제 파싱 구현
        # import ezdxf
        # doc = ezdxf.readfile(dxf_path)
        # msp = doc.modelspace()
        # entities = []
        # for entity in msp:
        #     entities.append(self._convert_entity(entity))
        
        logger.warning(
            "DXF 파싱은 현재 스텁 구현입니다. "
            "ezdxf 라이브러리를 설치하고 구현하세요."
        )
        
        # 스텁 데이터
        return [
            {
                "type": "line",
                "start": {"x": 0.0, "y": 0.0},
                "end": {"x": 100.0, "y": 0.0},
                "layer": "Wall",
            }
        ]

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
