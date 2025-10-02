"""파인튜닝 데이터셋 생성 스크립트."""

import sys
from pathlib import Path
import argparse
import json
from typing import List, Dict, Any

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.data.scanner import DataScanner
from img2dwg.data.image_processor import ImageProcessor
from img2dwg.utils.logger import setup_logging, get_logger
from img2dwg.utils.file_utils import ensure_dir


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
    return parser.parse_args()


def create_finetune_record(
    image_path: Path,
    json_data: Dict[str, Any],
    image_processor: ImageProcessor,
) -> Dict[str, Any]:
    """
    파인튜닝 레코드를 생성한다.

    Args:
        image_path: 이미지 파일 경로
        json_data: 변환된 JSON 데이터
        image_processor: 이미지 프로세서

    Returns:
        파인튜닝 레코드 (OpenAI 형식)
    """
    # 이미지를 base64로 인코딩
    image_url = image_processor.to_base64(image_path)

    # JSON 데이터를 문자열로 변환
    json_str = json.dumps(json_data, ensure_ascii=False)

    # OpenAI 파인튜닝 형식
    record = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "당신은 2D 건축 평면도 이미지를 분석하여 AutoCAD 호환 JSON 형태로 변환하는 전문가입니다. "
                    "선, 곡선, 점선, 텍스트, 치수를 정확하게 추출해야 합니다."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "다음 평면도 이미지를 분석하여 CAD 엔티티를 추출해주세요.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    },
                ],
            },
            {
                "role": "assistant",
                "content": json_str,
            },
        ]
    }

    return record


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

    # 출력 디렉토리 생성
    ensure_dir(args.output)

    # 데이터 스캔
    scanner = DataScanner(args.input_data)
    projects = scanner.scan()

    logger.info(f"총 {len(projects)}개 프로젝트 발견")

    # 이미지 프로세서 초기화
    image_processor = ImageProcessor()

    # 데이터셋 레코드
    records: List[Dict[str, Any]] = []

    # 각 프로젝트 처리
    for project in projects:
        # 변경 관련 파일
        if project.has_change_files:
            for image_path in project.change_group.images:
                # 대응하는 JSON 파일 찾기
                json_path = args.input_json / f"{project.name}_변경.json"
                
                if json_path.exists():
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            json_data = json.load(f)
                        
                        record = create_finetune_record(
                            image_path, json_data, image_processor
                        )
                        records.append(record)
                        logger.info(f"레코드 생성: {project.name} (변경)")
                    except Exception as e:
                        logger.error(f"레코드 생성 실패: {project.name} - {e}")

        # 단면도 관련 파일
        if project.has_section_files:
            for image_path in project.section_group.images:
                # 대응하는 JSON 파일 찾기
                json_path = args.input_json / f"{project.name}_단면.json"
                
                if json_path.exists():
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            json_data = json.load(f)
                        
                        record = create_finetune_record(
                            image_path, json_data, image_processor
                        )
                        records.append(record)
                        logger.info(f"레코드 생성: {project.name} (단면)")
                    except Exception as e:
                        logger.error(f"레코드 생성 실패: {project.name} - {e}")

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
        "split_ratio": args.split_ratio,
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
    print(f"\n파일 저장:")
    print(f"- {train_path}")
    print(f"- {val_path}")
    print(f"- {stats_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
