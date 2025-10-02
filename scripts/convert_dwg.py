"""DWG 파일 변환 스크립트."""

import sys
from pathlib import Path
import argparse
import json

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.data.scanner import DataScanner
from img2dwg.data.dwg_parser import DWGParser
from img2dwg.utils.logger import setup_logging, get_logger
from img2dwg.utils.file_utils import ensure_dir


def parse_args():
    """명령행 인자를 파싱한다."""
    parser = argparse.ArgumentParser(description="DWG 파일을 JSON으로 변환합니다.")
    parser.add_argument(
        "--input",
        type=Path,
        default=project_root / "datas",
        help="입력 데이터 폴더 경로",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "output" / "json",
        help="출력 JSON 폴더 경로",
    )
    parser.add_argument(
        "--oda-converter",
        type=Path,
        help="ODAFileConverter 실행 파일 경로 (선택사항)",
    )
    return parser.parse_args()


def main():
    """메인 함수."""
    args = parse_args()

    # 로깅 설정
    log_dir = project_root / "logs"
    ensure_dir(log_dir)
    setup_logging(log_level="INFO", log_file=log_dir / "convert_dwg.log")
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("DWG→JSON 변환 시작")
    logger.info("=" * 60)

    # 출력 디렉토리 생성
    ensure_dir(args.output)

    # 데이터 스캔
    scanner = DataScanner(args.input)
    projects = scanner.scan()

    logger.info(f"총 {len(projects)}개 프로젝트 발견")

    # DWG 파서 초기화
    parser = DWGParser(oda_converter_path=args.oda_converter)

    # 변환 통계
    converted_count = 0
    failed_count = 0
    failed_files = []

    # 각 프로젝트의 DWG 파일 변환
    for project in projects:
        # 변경 DWG 파일
        for dwg_file in project.change_group.dwg_files:
            try:
                logger.info(f"변환 중: {dwg_file.name}")
                data = parser.parse(dwg_file)
                
                # 프로젝트 정보 추가
                data["metadata"]["project"] = project.name
                
                # JSON 저장
                output_file = args.output / f"{project.name}_변경.json"
                parser.save_json(data, output_file)
                
                converted_count += 1
            except Exception as e:
                logger.error(f"변환 실패: {dwg_file.name} - {e}")
                failed_count += 1
                failed_files.append(str(dwg_file))

        # 단면도 DWG 파일
        for dwg_file in project.section_group.dwg_files:
            try:
                logger.info(f"변환 중: {dwg_file.name}")
                data = parser.parse(dwg_file)
                
                # 프로젝트 정보 추가
                data["metadata"]["project"] = project.name
                
                # JSON 저장
                output_file = args.output / f"{project.name}_단면.json"
                parser.save_json(data, output_file)
                
                converted_count += 1
            except Exception as e:
                logger.error(f"변환 실패: {dwg_file.name} - {e}")
                failed_count += 1
                failed_files.append(str(dwg_file))

    # 결과 출력
    print("\n" + "=" * 60)
    print("DWG→JSON 변환 결과")
    print("=" * 60)
    print(f"성공: {converted_count}개")
    print(f"실패: {failed_count}개")
    
    if failed_files:
        print("\n실패한 파일:")
        for file in failed_files[:10]:  # 최대 10개만 표시
            print(f"- {file}")

    # 변환 로그 저장
    log_data = {
        "converted": converted_count,
        "failed": failed_count,
        "failed_files": failed_files,
    }
    
    log_file = args.output / "conversion_log.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"변환 로그 저장: {log_file}")
    print(f"\n변환 로그 저장: {log_file}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
