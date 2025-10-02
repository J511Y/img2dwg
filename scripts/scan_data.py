"""데이터 폴더 스캔 스크립트."""

import sys
from pathlib import Path
import json

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.data.scanner import DataScanner
from img2dwg.utils.logger import setup_logging, get_logger
from img2dwg.utils.file_utils import ensure_dir


def main():
    """메인 함수."""
    # 로깅 설정
    log_dir = project_root / "logs"
    ensure_dir(log_dir)
    setup_logging(log_level="INFO", log_file=log_dir / "scan_data.log")
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("데이터 스캔 시작")
    logger.info("=" * 60)

    # 데이터 경로
    data_path = project_root / "datas"
    
    if not data_path.exists():
        logger.error(f"데이터 폴더를 찾을 수 없습니다: {data_path}")
        return 1

    # 스캐너 생성 및 스캔
    scanner = DataScanner(data_path)
    projects = scanner.scan()

    # 통계 계산
    stats = scanner.get_statistics(projects)

    # 결과 출력
    print("\n" + "=" * 60)
    print("데이터 스캔 결과")
    print("=" * 60)
    print(f"총 프로젝트 수: {stats['total_projects']}")
    print(f"완전한 변경 쌍: {stats['complete_change_pairs']}")
    print(f"완전한 단면도 쌍: {stats['complete_section_pairs']}")
    print(f"불완전한 프로젝트: {stats['incomplete_projects']}")

    if stats['incomplete_projects'] > 0:
        print("\n불완전한 프로젝트 상세:")
        print("-" * 60)
        for detail in stats['incomplete_details'][:10]:  # 최대 10개만 표시
            print(f"- {detail['parent_folder']}/{detail['name']}")
            print(f"  변경: 이미지 {detail['change_images']}개, DWG {detail['change_dwgs']}개")
            print(f"  단면: 이미지 {detail['section_images']}개, DWG {detail['section_dwgs']}개")

    # 결과 저장
    output_dir = project_root / "output"
    ensure_dir(output_dir)

    # JSON 저장
    json_path = output_dir / "scan_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    logger.info(f"결과가 저장되었습니다: {json_path}")
    print(f"\n결과가 저장되었습니다: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
