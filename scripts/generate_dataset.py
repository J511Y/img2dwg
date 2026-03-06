"""파인튜닝 데이터셋 생성 스크립트."""

from __future__ import annotations

# mypy: disable-error-code=import-untyped
import argparse
import json
import sys
from pathlib import Path
from typing import Any

import tiktoken

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _bootstrap_src_path() -> None:
    """로컬 실행 시 src 경로를 Python import path에 주입한다."""
    src_path = PROJECT_ROOT / "src"
    src_str = str(src_path)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """명령행 인자를 파싱한다."""
    parser = argparse.ArgumentParser(description="OpenAI 파인튜닝용 JSONL 데이터셋을 생성합니다.")
    parser.add_argument(
        "--input-data",
        type=Path,
        default=PROJECT_ROOT / "datas",
        help="입력 데이터 폴더 경로",
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "json",
        help="변환된 JSON 폴더 경로",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output",
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
        action=argparse.BooleanOptionalAction,
        default=True,
        help="토큰 초과 시 자동 타일링 활성화",
    )
    parser.add_argument(
        "--compact-schema",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Compact 스키마 사용 (추가 20~30%% 토큰 절감)",
    )
    parser.add_argument(
        "--optimize",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="최적화 옵션 사용 (RDP, 반올림 등)",
    )
    parser.add_argument(
        "--use-image-url",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="이미지를 base64 대신 공개 URL로 사용 (토큰 절감)",
    )
    parser.add_argument(
        "--image-service",
        type=str,
        default="github",
        choices=["imgur", "cloudinary", "github"],
        help="이미지 업로드 서비스 (기본: github)",
    )
    return parser.parse_args(argv)


def create_finetune_record(
    image_data: list[dict[str, str]],
    json_data: dict[str, Any],
    dwg_type: str,
) -> dict[str, Any]:
    """파인튜닝 레코드를 생성한다 (여러 이미지 지원)."""
    json_str = json.dumps(json_data, ensure_ascii=False)

    if dwg_type == "변경":
        image_desc = (
            "다음은 건축 평면도의 변경 전/후 이미지입니다. "
            "이 이미지들을 분석하여 CAD 엔티티를 추출해주세요."
        )
    else:
        image_desc = (
            "다음은 건축 평면도의 단면도 이미지입니다. "
            "이 이미지들을 분석하여 CAD 엔티티를 추출해주세요."
        )

    user_content: list[dict[str, Any]] = [{"type": "text", "text": image_desc}]
    for image in image_data:
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": image["url"]},
            }
        )

    return {
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


def count_tokens(record: dict[str, Any], model: str = "gpt-4o") -> int:
    """레코드의 토큰 수를 계산한다."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    record_str = json.dumps(record, ensure_ascii=False)
    return len(encoding.encode(record_str))


def _description_from_filename(filename: str, dwg_type: str) -> str:
    if dwg_type == "단면":
        return "단면도"
    if "변경전" in filename:
        return "변경전"
    if "변경후" in filename:
        return "변경후"
    return "평면도"


def main(argv: list[str] | None = None) -> int:
    """메인 함수."""
    args = parse_args(argv)

    _bootstrap_src_path()
    from img2dwg.data.image_processor import ImageProcessor
    from img2dwg.data.scanner import DataScanner
    from img2dwg.utils.file_utils import ensure_dir
    from img2dwg.utils.image_uploader import ImageUploader, URLCache
    from img2dwg.utils.logger import get_logger, setup_logging
    from img2dwg.utils.schema_compact import CompactSchemaConverter
    from img2dwg.utils.tiling import split_by_token_budget

    log_dir = PROJECT_ROOT / "logs"
    ensure_dir(log_dir)
    setup_logging(log_level="INFO", log_file=log_dir / "generate_dataset.log")
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("파인튜닝 데이터셋 생성 시작")
    logger.info("=" * 60)
    logger.info("타일링: %s", "활성화" if args.enable_tiling else "비활성화")
    logger.info("Compact 스키마: %s", "활성화" if args.compact_schema else "비활성화")
    logger.info("최적화: %s", "활성화" if args.optimize else "비활성화")
    logger.info("이미지 URL 사용: %s", "활성화" if args.use_image_url else "비활성화 (base64)")
    if args.use_image_url:
        logger.info("이미지 서비스: %s", args.image_service)

    ensure_dir(args.output)

    scanner = DataScanner(args.input_data)
    projects = scanner.scan()
    logger.info("총 %d개 프로젝트 발견", len(projects))

    image_processor = ImageProcessor()

    uploader: Any | None = None
    url_cache: Any | None = None
    if args.use_image_url:
        uploader = ImageUploader(service=args.image_service)
        cache_file = args.output / "image_url_cache.json"
        url_cache = URLCache(cache_file)
        logger.info("이미지 업로더 초기화 완료 (서비스: %s)", args.image_service)

    records: list[dict[str, Any]] = []
    filtered_count = 0
    tiled_count = 0

    work_items = [
        (
            "변경",
            lambda project: project.has_change_files,
            lambda project: project.change_group.images,
        ),
        (
            "단면",
            lambda project: project.has_section_files,
            lambda project: project.section_group.images,
        ),
    ]

    for project in projects:
        for dwg_type, exists_predicate, images_selector in work_items:
            if not exists_predicate(project):
                continue

            json_path = args.input_json / f"{project.name}_{dwg_type}.json"
            project_images = images_selector(project)
            if not (json_path.exists() and project_images):
                continue

            try:
                with open(json_path, encoding="utf-8") as file:
                    json_data: dict[str, Any] = json.load(file)

                if args.compact_schema:
                    converter = CompactSchemaConverter(use_local_coords=True)
                    json_data = converter.compact(json_data)

                image_data: list[dict[str, str]] = []
                for image_path in project_images:
                    if args.use_image_url:
                        assert uploader is not None
                        assert url_cache is not None
                        image_url = url_cache.get(image_path)
                        if image_url is None:
                            image_url = uploader.upload(image_path, project_name=project.name)
                            url_cache.set(image_path, image_url)
                    else:
                        image_url = image_processor.to_base64(image_path)

                    image_data.append(
                        {
                            "url": image_url,
                            "description": _description_from_filename(image_path.stem, dwg_type),
                        }
                    )

                logger.info(
                    "%s (%s): %d개 이미지 수집 완료", project.name, dwg_type, len(image_data)
                )

                json_chunks = [json_data]
                if args.enable_tiling:

                    def token_counter(
                        data: dict[str, Any],
                        image_snapshot: list[dict[str, str]] = image_data,
                        current_type: str = dwg_type,
                    ) -> int:
                        return count_tokens(
                            create_finetune_record(image_snapshot, data, current_type),
                            args.model,
                        )

                    json_chunks = split_by_token_budget(json_data, args.max_tokens, token_counter)
                    if len(json_chunks) > 1:
                        tiled_count += len(json_chunks) - 1
                        logger.info(
                            "%s (%s): %d개 타일로 분할",
                            project.name,
                            dwg_type,
                            len(json_chunks),
                        )

                for chunk_idx, chunk_data in enumerate(json_chunks):
                    record = create_finetune_record(image_data, chunk_data, dwg_type)
                    token_count = count_tokens(record, args.model)

                    if token_count <= args.max_tokens:
                        records.append(record)
                        chunk_info = (
                            f" (타일 {chunk_idx + 1}/{len(json_chunks)})"
                            if len(json_chunks) > 1
                            else ""
                        )
                        logger.info(
                            "레코드 생성: %s (%s)%s - %d개 이미지, %s 토큰",
                            project.name,
                            dwg_type,
                            chunk_info,
                            len(image_data),
                            f"{token_count:,}",
                        )
                    else:
                        filtered_count += 1
                        logger.warning(
                            "레코드 필터링: %s (%s) - %s 토큰 > %s 토큰 제한",
                            project.name,
                            dwg_type,
                            f"{token_count:,}",
                            f"{args.max_tokens:,}",
                        )
            except Exception as exc:  # pragma: no cover - 로그 경로
                logger.error("레코드 생성 실패: %s (%s) - %s", project.name, dwg_type, exc)

    split_idx = int(len(records) * args.split_ratio)
    train_records = records[:split_idx]
    val_records = records[split_idx:]

    logger.info("Train: %d개, Val: %d개", len(train_records), len(val_records))

    train_path = args.output / "finetune_train.jsonl"
    val_path = args.output / "finetune_val.jsonl"

    with open(train_path, "w", encoding="utf-8") as file:
        for record in train_records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    with open(val_path, "w", encoding="utf-8") as file:
        for record in val_records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

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
        "use_image_url": args.use_image_url,
        "image_service": args.image_service if args.use_image_url else None,
    }

    stats_path = args.output / "dataset_stats.json"
    with open(stats_path, "w", encoding="utf-8") as file:
        json.dump(stats, file, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("데이터셋 생성 결과")
    print("=" * 60)
    print(f"총 샘플: {stats['total_samples']}개")
    print(f"Train: {stats['train_samples']}개")
    print(f"Validation: {stats['val_samples']}개")
    print(f"필터링됨: {stats['filtered_samples']}개 (토큰 수 초과)")
    if args.enable_tiling:
        print(f"타일링됨: {stats['tiled_samples']}개 추가 타일")
    print("\n최적화 옵션:")
    print(f"- 타일링: {'✅' if args.enable_tiling else '❌'}")
    print(f"- Compact 스키마: {'✅' if args.compact_schema else '❌'}")
    print(f"- 기본 최적화: {'✅' if args.optimize else '❌'}")
    print(f"- 이미지 URL: {'✅' if args.use_image_url else '❌'}")
    print(f"\n토큰 제한: {args.max_tokens:,} 토큰 ({args.model})")
    print("\n파일 저장:")
    print(f"- {train_path}")
    print(f"- {val_path}")
    print(f"- {stats_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
