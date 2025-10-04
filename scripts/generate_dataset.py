"""파인튜닝 데이터셋 생성 스크립트."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import tiktoken

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.data.dwg_parser import DWGParser, ParseOptions
from img2dwg.data.image_processor import ImageProcessor
from img2dwg.data.scanner import DataScanner
from img2dwg.utils.file_utils import ensure_dir
from img2dwg.utils.image_uploader import ImageUploader, URLCache
from img2dwg.utils.logger import get_logger, setup_logging
from img2dwg.utils.schema_compact import CompactSchemaConverter
from img2dwg.utils.tiling import split_by_token_budget


def parse_args():
    """명령행 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="OpenAI 파인튜닝용 JSONL 데이터셋을 생성합니다."
    )
    parser.add_argument(
        "--input-data",
        type=Path,
        default=project_root / "datas",
        help="입력 데이터 폴더 경로",
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        default=project_root / "output" / "json",
        help="변환된 JSON 폴더 경로",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "output",
        help="출력 폴더 경로",
    )
    parser.add_argument(
        "--split-ratio",
        type=float,
        default=0.8,
        help="Train/Validation 분할 비율 (기본: 0.8)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=60000,
        help="최대 토큰 수 (기본: 60000)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="cl100k_base",
        help="토큰 계산에 사용할 모델 (기본: cl100k_base)",
    )
    parser.add_argument(
        "--enable-tiling",
        action="store_true",
        default=True,
        help="토큰 초과 시 자동 타일링 활성화",
    )
    parser.add_argument(
        "--compact-schema",
        action="store_true",
        help="Compact 스키마 사용 (추가 20~30%% 토큰 절감)",
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        default=True,
        help="최적화 옵션 사용 (RDP, 반올림 등)",
    )
    parser.add_argument(
        "--use-image-url",
        action="store_true",
        default=True,
        help="이미지를 base64 대신 공개 URL로 사용 (토큰 절감)",
    )
    parser.add_argument(
        "--image-service",
        type=str,
        default="github",
        choices=["imgur", "cloudinary", "github"],
        help="이미지 업로드 서비스 (기본: github)",
    )
    return parser.parse_args()


def create_finetune_record(
    image_data: List[Dict[str, str]],
    json_data: Dict[str, Any],
    dwg_type: str,
) -> Dict[str, Any]:
    """
    파인튜닝 레코드를 생성한다 (여러 이미지 지원).

    Args:
        image_data: 이미지 정보 리스트 [{"url": "...", "description": "변경전"}, ...]
        json_data: 변환된 JSON 데이터
        dwg_type: DWG 타입 ("변경" 또는 "단면")

    Returns:
        파인튜닝 레코드 (OpenAI 형식)
    """
    # JSON 데이터를 문자열로 변환
    json_str = json.dumps(json_data, ensure_ascii=False)

    # 이미지 설명 생성
    if dwg_type == "변경":
        image_desc = "다음은 건축 평면도의 변경 전/후 이미지입니다. 이 이미지들을 분석하여 CAD 엔티티를 추출해주세요."
    else:
        image_desc = "다음은 건축 평면도의 단면도 이미지입니다. 이 이미지들을 분석하여 CAD 엔티티를 추출해주세요."

    # user content 구성 (텍스트 + 여러 이미지)
    user_content = [
        {
            "type": "text",
            "text": image_desc,
        }
    ]

    # 모든 이미지 추가
    for img in image_data:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": img["url"]},
        })

    # OpenAI 파인튜닝 형식
    record = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "당신은 2D 건축 평면도 이미지를 분석하여 AutoCAD 호환 JSON 형태로 변환하는 전문가입니다. "
                    "여러 이미지(변경 전/후, 단면도 등)를 종합적으로 분석하여 정확한 CAD 엔티티를 추출해야 합니다."
                ),
            },
            {
                "role": "user",
                "content": user_content,
            },
            {
                "role": "assistant",
                "content": json_str,
            },
        ]
    }

    return record


def count_tokens(record: Dict[str, Any], model: str = "gpt-4o") -> int:
    """
    레코드의 토큰 수를 계산한다.

    Args:
        record: 파인튜닝 레코드
        model: 토큰 계산에 사용할 모델명

    Returns:
        토큰 수
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # 모델을 찾을 수 없으면 기본 인코딩 사용
        encoding = tiktoken.get_encoding("cl100k_base")

    # 레코드 전체를 JSON 문자열로 변환하여 토큰 수 계산
    record_str = json.dumps(record, ensure_ascii=False)
    num_tokens = len(encoding.encode(record_str))

    return num_tokens


def main():
    """메인 함수."""
    args = parse_args()

    # 로깅 설정
    log_dir = project_root / "logs"
    ensure_dir(log_dir)
    setup_logging(log_level="INFO", log_file=log_dir / "generate_dataset.log")
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("파인튜닝 데이터셋 생성 시작")
    logger.info("=" * 60)
    logger.info(f"타일링: {'활성화' if args.enable_tiling else '비활성화'}")
    logger.info(f"Compact 스키마: {'활성화' if args.compact_schema else '비활성화'}")
    logger.info(f"최적화: {'활성화' if args.optimize else '비활성화'}")
    logger.info(f"이미지 URL 사용: {'활성화' if args.use_image_url else '비활성화 (base64)'}")
    if args.use_image_url:
        logger.info(f"이미지 서비스: {args.image_service}")

    # 출력 디렉토리 생성
    ensure_dir(args.output)

    # 데이터 스캔
    scanner = DataScanner(args.input_data)
    projects = scanner.scan()

    logger.info(f"총 {len(projects)}개 프로젝트 발견")

    # 이미지 프로세서 초기화
    image_processor = ImageProcessor()

    # 이미지 업로더 초기화 (URL 모드인 경우)
    uploader = None
    url_cache = None
    if args.use_image_url:
        uploader = ImageUploader(service=args.image_service)
        cache_file = args.output / "image_url_cache.json"
        url_cache = URLCache(cache_file)
        logger.info(f"이미지 업로더 초기화 완료 (서비스: {args.image_service})")

    # 데이터셋 레코드
    records: List[Dict[str, Any]] = []
    filtered_count = 0  # 필터링된 레코드 수
    tiled_count = 0  # 타일링된 레코드 수

    # 각 프로젝트 처리
    for project in projects:
        # 변경 관련 파일 (DWG 파일 기준으로 하나의 레코드 생성)
        if project.has_change_files:
            # 대응하는 JSON 파일 찾기
            json_path = args.input_json / f"{project.name}_변경.json"

            if json_path.exists() and len(project.change_group.images) > 0:
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        json_data = json.load(f)

                    # Compact 스키마 적용
                    if args.compact_schema:
                        converter = CompactSchemaConverter(use_local_coords=True)
                        json_data = converter.compact(json_data)

                    # 모든 이미지 URL 수집
                    image_data = []
                    for image_path in project.change_group.images:
                        image_url = None
                        if args.use_image_url:
                            # 캐시 확인
                            image_url = url_cache.get(image_path)
                            if image_url is None:
                                # 업로드 및 캐시 저장 (프로젝트명 포함)
                                image_url = uploader.upload(image_path, project_name=project.name)
                                url_cache.set(image_path, image_url)
                        else:
                            # base64 인코딩
                            image_url = image_processor.to_base64(image_path)

                        # 이미지 설명 추출 (파일명에서)
                        filename = image_path.stem  # 확장자 제외
                        description = "변경전" if "변경전" in filename else "변경후" if "변경후" in filename else "평면도"
                        
                        image_data.append({
                            "url": image_url,
                            "description": description
                        })

                    logger.info(f"{project.name} (변경): {len(image_data)}개 이미지 수집 완료")

                    # 타일링 처리
                    json_chunks = [json_data]
                    if args.enable_tiling:
                        json_chunks = split_by_token_budget(
                            json_data,
                            args.max_tokens,
                            lambda d: count_tokens(
                                create_finetune_record(image_data, d, "변경"),
                                args.model
                            )
                        )
                        if len(json_chunks) > 1:
                            tiled_count += len(json_chunks) - 1
                            logger.info(f"{project.name} (변경): {len(json_chunks)}개 타일로 분할")

                    # 각 청크별 레코드 생성
                    for chunk_idx, chunk_data in enumerate(json_chunks):
                        record = create_finetune_record(
                            image_data, chunk_data, "변경"
                        )

                        # 토큰 수 확인
                        token_count = count_tokens(record, args.model)

                        if token_count <= args.max_tokens:
                            records.append(record)
                            chunk_info = f" (타일 {chunk_idx + 1}/{len(json_chunks)})" if len(json_chunks) > 1 else ""
                            logger.info(
                                f"레코드 생성: {project.name} (변경){chunk_info} - "
                                f"{len(image_data)}개 이미지, {token_count:,} 토큰"
                            )
                        else:
                            filtered_count += 1
                            logger.warning(
                                f"레코드 필터링: {project.name} (변경) - "
                                f"{token_count:,} 토큰 > {args.max_tokens:,} 토큰 제한"
                            )
                except Exception as e:
                    logger.error(f"레코드 생성 실패: {project.name} (변경) - {e}")

        # 단면도 관련 파일 (DWG 파일 기준으로 하나의 레코드 생성)
        if project.has_section_files:
            # 대응하는 JSON 파일 찾기
            json_path = args.input_json / f"{project.name}_단면.json"

            if json_path.exists() and len(project.section_group.images) > 0:
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        json_data = json.load(f)

                    # Compact 스키마 적용
                    if args.compact_schema:
                        converter = CompactSchemaConverter(use_local_coords=True)
                        json_data = converter.compact(json_data)

                    # 모든 이미지 URL 수집
                    image_data = []
                    for image_path in project.section_group.images:
                        image_url = None
                        if args.use_image_url:
                            # 캐시 확인
                            image_url = url_cache.get(image_path)
                            if image_url is None:
                                # 업로드 및 캐시 저장 (프로젝트명 포함)
                                image_url = uploader.upload(image_path, project_name=project.name)
                                url_cache.set(image_path, image_url)
                        else:
                            # base64 인코딩
                            image_url = image_processor.to_base64(image_path)

                        # 이미지 설명 추출 (파일명에서)
                        filename = image_path.stem  # 확장자 제외
                        description = "단면도"
                        if "단면도" in filename:
                            description = "단면도"
                        
                        image_data.append({
                            "url": image_url,
                            "description": description
                        })

                    logger.info(f"{project.name} (단면): {len(image_data)}개 이미지 수집 완료")

                    # 타일링 처리
                    json_chunks = [json_data]
                    if args.enable_tiling:
                        json_chunks = split_by_token_budget(
                            json_data,
                            args.max_tokens,
                            lambda d: count_tokens(
                                create_finetune_record(image_data, d, "단면"),
                                args.model
                            )
                        )
                        if len(json_chunks) > 1:
                            tiled_count += len(json_chunks) - 1
                            logger.info(f"{project.name} (단면): {len(json_chunks)}개 타일로 분할")

                    # 각 청크별 레코드 생성
                    for chunk_idx, chunk_data in enumerate(json_chunks):
                        record = create_finetune_record(
                            image_data, chunk_data, "단면"
                        )

                        # 토큰 수 확인
                        token_count = count_tokens(record, args.model)

                        if token_count <= args.max_tokens:
                            records.append(record)
                            chunk_info = f" (타일 {chunk_idx + 1}/{len(json_chunks)})" if len(json_chunks) > 1 else ""
                            logger.info(
                                f"레코드 생성: {project.name} (단면){chunk_info} - "
                                f"{len(image_data)}개 이미지, {token_count:,} 토큰"
                            )
                        else:
                            filtered_count += 1
                            logger.warning(
                                f"레코드 필터링: {project.name} (단면) - "
                                f"{token_count:,} 토큰 > {args.max_tokens:,} 토큰 제한"
                            )
                except Exception as e:
                    logger.error(f"레코드 생성 실패: {project.name} (단면) - {e}")

    # Train/Val 분할
    split_idx = int(len(records) * args.split_ratio)
    train_records = records[:split_idx]
    val_records = records[split_idx:]

    logger.info(f"Train: {len(train_records)}개, Val: {len(val_records)}개")

    # JSONL 저장
    train_path = args.output / "finetune_train.jsonl"
    val_path = args.output / "finetune_val.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        for record in train_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for record in val_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 통계 저장
    stats = {
        "total_samples": len(records),
        "train_samples": len(train_records),
        "val_samples": len(val_records),
        "filtered_samples": filtered_count,
        "tiled_samples": tiled_count,
        "split_ratio": args.split_ratio,
        "max_tokens": args.max_tokens,
        "model": args.model,
        "tiling_enabled": args.enable_tiling,
        "compact_schema": args.compact_schema,
        "optimize": args.optimize,
    }

    stats_path = args.output / "dataset_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # 결과 출력
    print("\n" + "=" * 60)
    print("데이터셋 생성 결과")
    print("=" * 60)
    print(f"총 샘플: {stats['total_samples']}개")
    print(f"Train: {stats['train_samples']}개")
    print(f"Validation: {stats['val_samples']}개")
    print(f"필터링됨: {stats['filtered_samples']}개 (토큰 수 초과)")
    if args.enable_tiling:
        print(f"타일링됨: {stats['tiled_samples']}개 추가 타일")
    print(f"\n최적화 옵션:")
    print(f"- 타일링: {'✅' if args.enable_tiling else '❌'}")
    print(f"- Compact 스키마: {'✅' if args.compact_schema else '❌'}")
    print(f"- 기본 최적화: {'✅' if args.optimize else '❌'}")
    print(f"\n토큰 제한: {args.max_tokens:,} 토큰 ({args.model})")
    print(f"\n파일 저장:")
    print(f"- {train_path}")
    print(f"- {val_path}")
    print(f"- {stats_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
