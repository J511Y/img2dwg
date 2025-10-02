"""JSON→DWG 변환 모듈."""

from pathlib import Path
from typing import Dict, Any
import json

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

        Note:
            실제 구현 시 ezdxf 사용
        """
        # TODO: ezdxf를 사용한 실제 DXF 생성 구현
        # import ezdxf
        # 
        # doc = ezdxf.new('R2010')
        # msp = doc.modelspace()
        # 
        # for entity in data['entities']:
        #     if entity['type'] == 'line':
        #         msp.add_line(
        #             (entity['start']['x'], entity['start']['y']),
        #             (entity['end']['x'], entity['end']['y']),
        #             dxfattribs={'layer': entity['layer']}
        #         )
        #     elif entity['type'] == 'text':
        #         msp.add_text(
        #             entity['content'],
        #             dxfattribs={
        #                 'insert': (entity['position']['x'], entity['position']['y']),
        #                 'height': entity['height'],
        #                 'layer': entity['layer']
        #             }
        #         )
        #     # ... 다른 엔티티 타입들
        # 
        # doc.saveas(dxf_path)

        logger.warning(
            "DXF 생성은 현재 스텁 구현입니다. "
            "ezdxf 라이브러리를 설치하고 구현하세요."
        )

    def _convert_dxf_to_dwg(self, dxf_path: Path, dwg_path: Path) -> None:
        """
        DXF 파일을 DWG로 변환한다.

        Args:
            dxf_path: 입력 DXF 파일 경로
            dwg_path: 출력 DWG 파일 경로

        Note:
            실제 구현 시 ODAFileConverter 사용
        """
        # TODO: ODAFileConverter를 사용한 실제 변환 구현
        # import subprocess
        # subprocess.run([
        #     oda_converter_path,
        #     str(dxf_path.parent),
        #     str(dwg_path.parent),
        #     'ACAD2018',
        #     'DWG',
        #     '0',
        #     '1',
        #     dxf_path.name
        # ])

        logger.warning(
            "DXF→DWG 변환은 현재 스텁 구현입니다. "
            "ODAFileConverter를 설정하세요."
        )
