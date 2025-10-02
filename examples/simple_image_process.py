"""간단한 이미지 전처리 예제."""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.data.image_processor import ImageProcessor
from img2dwg.utils.logger import setup_logging


def main():
    """이미지 파일을 전처리하는 간단한 예제."""
    # 로깅 설정
    setup_logging(log_level="INFO")
    
    # 이미지 파일 경로 (실제 파일 경로로 변경하세요)
    image_file = project_root / "datas" / "2501 (2)" / "이매촌 진흥 814-405" / "변경전-모형.jpg"
    
    if not image_file.exists():
        print(f"❌ 이미지 파일을 찾을 수 없습니다: {image_file}")
        print("💡 실제 이미지 파일 경로로 변경하세요.")
        return 1
    
    # 출력 경로
    output_image = project_root / "output" / "examples" / "processed.jpg"
    
    # 이미지 프로세서 생성
    processor = ImageProcessor(target_size=(2048, 2048), quality=85)
    
    try:
        print(f"🔄 이미지 전처리 시작: {image_file.name}")
        
        # 이미지 처리
        result_path = processor.process(image_file, output_image)
        
        print(f"✅ 전처리 완료!")
        print(f"📸 출력 파일: {result_path}")
        
        # Base64 인코딩 예제 (파인튜닝 데이터셋에 사용)
        print("\n🔐 Base64 인코딩 예제:")
        base64_url = processor.to_base64(result_path)
        print(f"   길이: {len(base64_url)} 문자")
        print(f"   시작: {base64_url[:50]}...")
        
        return 0
        
    except Exception as e:
        print(f"❌ 전처리 실패: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
