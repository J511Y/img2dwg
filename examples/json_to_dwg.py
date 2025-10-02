"""JSON→DWG 역변환 예제."""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.models.converter import JSONToDWGConverter
from img2dwg.utils.logger import setup_logging


def main():
    """JSON 파일을 DWG로 역변환하는 예제."""
    # 로깅 설정
    setup_logging(log_level="INFO")
    
    # JSON 파일 경로
    json_file = project_root / "output" / "examples" / "converted.json"
    
    if not json_file.exists():
        print(f"❌ JSON 파일을 찾을 수 없습니다: {json_file}")
        print("💡 먼저 simple_convert.py를 실행하여 JSON 파일을 생성하세요.")
        return 1
    
    # 출력 경로
    output_dwg = project_root / "output" / "examples" / "reconstructed.dwg"
    
    # 컨버터 생성
    converter = JSONToDWGConverter()
    
    try:
        print(f"🔄 JSON→DWG 변환 시작: {json_file.name}")
        
        # JSON을 DWG로 변환
        converter.convert(json_file, output_dwg)
        
        print(f"✅ 변환 완료!")
        print(f"📄 DWG 파일: {output_dwg}")
        print(f"💡 AutoCAD 또는 DWG 뷰어로 열어보세요.")
        
        return 0
        
    except Exception as e:
        print(f"❌ 변환 실패: {e}")
        if "ODAFileConverter" in str(e):
            print("\n⚠️  ODAFileConverter가 설치되지 않았습니다.")
            print("📖 설치 가이드: docs/ODAFC_INSTALLATION.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
