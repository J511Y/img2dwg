"""간단한 DWG→JSON 변환 예제."""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.data.dwg_parser import DWGParser
from img2dwg.utils.logger import setup_logging


def main():
    """DWG 파일을 JSON으로 변환하는 간단한 예제."""
    # 로깅 설정
    setup_logging(log_level="INFO")
    
    # DWG 파일 경로 (실제 파일 경로로 변경하세요)
    dwg_file = project_root / "datas" / "2501 (2)" / "이매촌 진흥 814-405" / "변경전후.dwg"
    
    if not dwg_file.exists():
        print(f"❌ DWG 파일을 찾을 수 없습니다: {dwg_file}")
        print("💡 실제 DWG 파일 경로로 변경하세요.")
        return 1
    
    # 출력 경로
    output_json = project_root / "output" / "examples" / "converted.json"
    
    # 파서 생성
    parser = DWGParser()
    
    try:
        print(f"🔄 DWG 파일 변환 시작: {dwg_file.name}")
        
        # DWG 파싱
        data = parser.parse(dwg_file)
        
        # JSON 저장
        parser.save_json(data, output_json)
        
        print(f"✅ 변환 완료!")
        print(f"📄 JSON 파일: {output_json}")
        print(f"📊 엔티티 수: {data['metadata']['entity_count']}개")
        
        return 0
        
    except Exception as e:
        print(f"❌ 변환 실패: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
