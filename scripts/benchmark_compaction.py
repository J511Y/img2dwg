"""데이터 압축 효과 벤치마크 스크립트."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import time

import tiktoken

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.data.dwg_parser import DWGParser, ParseOptions
from img2dwg.utils.logger import get_logger, setup_logging
from img2dwg.utils.file_utils import ensure_dir


def parse_args():
    """명령행 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="DWG 파싱 옵션별 압축 효과를 벤치마크합니다."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="입력 DWG 파일 경로",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "output" / "benchmark",
        help="출력 폴더 경로",
    )
    return parser.parse_args()


def count_tokens(data: Dict[str, Any], model: str = "gpt-4o") -> int:
    """
    JSON 데이터의 토큰 수를 계산한다.
    
    Args:
        data: JSON 데이터
        model: 토큰 계산 모델
    
    Returns:
        토큰 수
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    json_str = json.dumps(data, ensure_ascii=False)
    return len(encoding.encode(json_str))


def benchmark_configuration(
    dwg_path: Path,
    config_name: str,
    options: ParseOptions,
    logger,
) -> Dict[str, Any]:
    """
    특정 설정으로 파싱하고 결과를 측정한다.
    
    Args:
        dwg_path: DWG 파일 경로
        config_name: 설정 이름
        options: 파싱 옵션
        logger: 로거
    
    Returns:
        벤치마크 결과
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"설정: {config_name}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # 파싱
        parser = DWGParser(options=options)
        result = parser.parse(dwg_path)
        
        # JSON 문자열 생성
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        json_bytes = len(json_str.encode('utf-8'))
        
        # 토큰 수 계산
        token_count = count_tokens(result)
        
        # 엔티티 수
        entity_count = len(result.get("entities", []))
        
        # 폴리라인 포인트 통계
        polyline_points = []
        for entity in result.get("entities", []):
            if entity.get("type") == "polyline":
                polyline_points.append(len(entity.get("points", [])))
        
        avg_polyline_points = (
            sum(polyline_points) / len(polyline_points) if polyline_points else 0
        )
        
        elapsed_time = time.time() - start_time
        
        benchmark_result = {
            "config_name": config_name,
            "success": True,
            "entity_count": entity_count,
            "json_bytes": json_bytes,
            "json_kb": round(json_bytes / 1024, 2),
            "token_count": token_count,
            "polyline_count": len(polyline_points),
            "avg_polyline_points": round(avg_polyline_points, 2),
            "elapsed_seconds": round(elapsed_time, 2),
            "options": {
                "include_types": options.include_types,
                "rdp_tolerance": options.rdp_tolerance,
                "round_ndigits": options.round_ndigits,
                "quantize_grid": options.quantize_grid,
                "drop_defaults": options.drop_defaults,
                "dxf_version": options.dxf_version,
            },
        }
        
        logger.info(f"엔티티 수: {entity_count:,}")
        logger.info(f"JSON 크기: {json_bytes:,} bytes ({benchmark_result['json_kb']} KB)")
        logger.info(f"토큰 수: {token_count:,}")
        logger.info(f"폴리라인 평균 포인트: {avg_polyline_points:.2f}")
        logger.info(f"처리 시간: {elapsed_time:.2f}초")
        
        return benchmark_result
        
    except Exception as e:
        logger.error(f"벤치마크 실패: {e}")
        return {
            "config_name": config_name,
            "success": False,
            "error": str(e),
        }


def main():
    """메인 함수."""
    args = parse_args()
    
    # 로깅 설정
    log_dir = project_root / "logs"
    ensure_dir(log_dir)
    setup_logging(log_level="INFO", log_file=log_dir / "benchmark_compaction.log")
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("데이터 압축 효과 벤치마크 시작")
    logger.info("=" * 60)
    logger.info(f"입력 파일: {args.input}")
    
    if not args.input.exists():
        logger.error(f"입력 파일을 찾을 수 없습니다: {args.input}")
        return 1
    
    # 출력 디렉토리 생성
    ensure_dir(args.output)
    
    # 벤치마크 설정들
    configurations = [
        ("baseline", ParseOptions(
            round_ndigits=None,
            drop_defaults=False,
            dxf_version="R2018",
        )),
        ("basic_optimization", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            dxf_version="R2000",
        )),
        ("with_rdp_light", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            rdp_tolerance=0.5,
            dxf_version="R2000",
        )),
        ("with_rdp_medium", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            rdp_tolerance=1.0,
            dxf_version="R2000",
        )),
        ("with_rdp_aggressive", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            rdp_tolerance=2.0,
            dxf_version="R2000",
        )),
        ("compact_schema", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            rdp_tolerance=1.0,
            compact_schema=True,
            dxf_version="R2000",
        )),
        ("compact_aggressive", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            rdp_tolerance=2.0,
            compact_schema=True,
            dxf_version="R2000",
        )),
        ("quantized", ParseOptions(
            quantize_grid=1.0,
            drop_defaults=True,
            rdp_tolerance=1.0,
            dxf_version="R2000",
        )),
        ("r12_version", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            rdp_tolerance=1.0,
            dxf_version="R12",
        )),
    ]
    
    # 각 설정으로 벤치마크 실행
    results = []
    for config_name, options in configurations:
        result = benchmark_configuration(args.input, config_name, options, logger)
        results.append(result)
    
    # 결과 저장
    output_file = args.output / f"benchmark_{args.input.stem}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n벤치마크 결과 저장: {output_file}")
    
    # 요약 출력
    print("\n" + "=" * 80)
    print("벤치마크 요약")
    print("=" * 80)
    
    baseline = next((r for r in results if r["config_name"] == "baseline"), None)
    
    if baseline and baseline["success"]:
        print(f"\n{'설정':<25} {'엔티티':<10} {'JSON(KB)':<12} {'토큰':<12} {'절감율':<10}")
        print("-" * 80)
        
        for result in results:
            if not result["success"]:
                print(f"{result['config_name']:<25} 실패")
                continue
            
            entity_count = result["entity_count"]
            json_kb = result["json_kb"]
            token_count = result["token_count"]
            
            # 절감율 계산
            if baseline["token_count"] > 0:
                reduction = (1 - token_count / baseline["token_count"]) * 100
            else:
                reduction = 0
            
            print(
                f"{result['config_name']:<25} "
                f"{entity_count:<10,} "
                f"{json_kb:<12.2f} "
                f"{token_count:<12,} "
                f"{reduction:>6.1f}%"
            )
        
        print("\n권장 설정:")
        # 토큰이 60k 이하인 최적 설정 찾기
        valid_results = [r for r in results if r["success"] and r["token_count"] <= 60000]
        if valid_results:
            # 토큰이 적으면서 엔티티가 많은 설정 선택
            best = max(valid_results, key=lambda r: r["entity_count"])
            print(f"  - {best['config_name']}")
            print(f"    엔티티: {best['entity_count']:,}개")
            print(f"    토큰: {best['token_count']:,} (60k 이하)")
            print(f"    절감: {(1 - best['token_count'] / baseline['token_count']) * 100:.1f}%")
        else:
            print("  ⚠️  60k 토큰 이하로 줄이려면 타일링이 필요합니다.")
    
    print("\n" + "=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
