"""DWG 파일 변환 스크립트."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _bootstrap_src_path() -> None:
    """로컬 실행 시 src 경로를 Python import path에 주입한다."""
    src_path = PROJECT_ROOT / "src"
    src_str = str(src_path)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """명령행 인자를 파싱한다."""
    parser = argparse.ArgumentParser(description="DWG 파일을 JSON으로 변환합니다.")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "datas",
        help="입력 데이터 폴더 경로",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output" / "json",
        help="출력 JSON 폴더 경로",
    )
    parser.add_argument(
        "--oda-converter",
        type=Path,
        help="ODAFileConverter 실행 파일 경로 (선택사항)",
    )
    parser.add_argument(
        "--optimize",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="최적화 옵션 사용 (RDP 간소화, 좌표 반올림, 기본값 제거)",
    )
    parser.add_argument(
        "--rdp-tolerance",
        type=float,
        default=1.0,
        help="RDP 간소화 허용 오차 (기본: 1.0)",
    )
    parser.add_argument(
        "--compact-schema",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Compact 스키마 사용 (추가 20~30%% 토큰 절감)",
    )
    parser.add_argument(
        "--layout-analysis",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="고수준 레이아웃 분석 사용 (95~99%% 토큰 절감)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """메인 함수."""
    args = parse_args(argv)

    _bootstrap_src_path()
    from img2dwg.data.dwg_parser import DWGParser, ParseOptions
    from img2dwg.data.scanner import DataScanner
    from img2dwg.utils.file_utils import ensure_dir
    from img2dwg.utils.logger import get_logger, setup_logging

    log_dir = PROJECT_ROOT / "logs"
    ensure_dir(log_dir)
    setup_logging(log_level="INFO", log_file=log_dir / "convert_dwg.log")
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("DWG→JSON 변환 시작")
    logger.info("=" * 60)

    ensure_dir(args.output)

    scanner = DataScanner(args.input)
    projects = scanner.scan()
    logger.info("총 %d개 프로젝트 발견", len(projects))

    options = ParseOptions(
        compact_schema=args.compact_schema,
        use_layout_analysis=args.layout_analysis,
    )
    if args.layout_analysis:
        options.rdp_tolerance = args.rdp_tolerance if args.optimize else 1.0
        options.round_ndigits = 3
        options.drop_defaults = True
        options.dxf_version = "R2000"
        logger.info("🚀 레이아웃 분석 모드 활성화 (고수준 추상화)")
    elif args.optimize:
        options.rdp_tolerance = args.rdp_tolerance
        options.round_ndigits = 3
        options.drop_defaults = True
        options.dxf_version = "R2000"
        logger.info("최적화 모드 활성화 (RDP tolerance: %s)", args.rdp_tolerance)
        if args.compact_schema:
            logger.info("Compact 스키마 활성화")
    else:
        logger.info("기본 모드")
        if args.compact_schema:
            logger.info("Compact 스키마 활성화")

    parser = DWGParser(oda_converter_path=args.oda_converter, options=options)

    converted_count = 0
    failed_count = 0
    failed_files: list[str] = []

    for project in projects:
        work_items = [
            *[(dwg_file, "변경") for dwg_file in project.change_group.dwg_files],
            *[(dwg_file, "단면") for dwg_file in project.section_group.dwg_files],
        ]
        for dwg_file, suffix in work_items:
            try:
                logger.info("변환 중: %s", dwg_file.name)
                data = parser.parse(dwg_file)
                data["metadata"]["project"] = project.name

                output_file = args.output / f"{project.name}_{suffix}.json"
                parser.save_json(data, output_file)
                converted_count += 1
            except Exception as exc:  # pragma: no cover - 로그 경로
                logger.error("변환 실패: %s - %s", dwg_file.name, exc)
                failed_count += 1
                failed_files.append(str(dwg_file))

    print("\n" + "=" * 60)
    print("DWG→JSON 변환 결과")
    print("=" * 60)
    print(f"성공: {converted_count}개")
    print(f"실패: {failed_count}개")

    if failed_files:
        print("\n실패한 파일:")
        for failed_file in failed_files[:10]:
            print(f"- {failed_file}")

    log_data = {
        "converted": converted_count,
        "failed": failed_count,
        "failed_files": failed_files,
    }

    log_file = args.output / "conversion_log.json"
    with open(log_file, "w", encoding="utf-8") as file:
        json.dump(log_data, file, ensure_ascii=False, indent=2)

    logger.info("변환 로그 저장: %s", log_file)
    print(f"\n변환 로그 저장: {log_file}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
