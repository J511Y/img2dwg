"""Vision Encoder-Decoder 추론 스크립트."""

# ruff: noqa: E402

import argparse
import json
import sys
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.utils.logger import get_logger, setup_logging
from img2dwg.ved.config import InferenceConfig, resolve_inference_max_length
from img2dwg.ved.model import VEDModel
from img2dwg.ved.utils import get_device, validate_json


def parse_args() -> argparse.Namespace:
    """명령행 인자를 파싱한다."""
    parser = argparse.ArgumentParser(description="VED 모델로 이미지→JSON 추론")
    parser.add_argument(
        "--model-path",
        type=Path,
        default=project_root / "output" / "ved_checkpoints" / "best",
        help="학습된 모델 경로",
    )
    parser.add_argument(
        "--image",
        type=Path,
        required=True,
        help="입력 이미지 경로",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="출력 JSON 경로 (기본: stdout)",
    )
    parser.add_argument(
        "--num-beams",
        type=int,
        default=4,
        help="Beam search 빔 개수",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=None,
        help=(
            "최대 생성 길이. 미지정 시 체크포인트 학습 메타데이터의 max_length를 사용하고, "
            "메타데이터가 없으면 VEDConfig 기본값(131072)으로 fallback"
        ),
    )
    return parser.parse_args()


def main() -> None:
    """메인 추론 함수."""
    args = parse_args()

    # 로깅 설정
    setup_logging(log_level="INFO")
    logger = get_logger(__name__)

    logger.info("=" * 80)
    logger.info("Vision Encoder-Decoder 추론")
    logger.info("=" * 80)
    logger.info(f"Model: {args.model_path}")
    logger.info(f"Image: {args.image}")

    # 디바이스 설정
    device = get_device()
    logger.info(f"Device: {device}")

    # 모델 로드
    logger.info("모델 로드 중...")
    config = InferenceConfig(model_path=args.model_path)

    try:
        length_resolution = resolve_inference_max_length(
            model_path=args.model_path,
            cli_max_length=args.max_length,
        )
    except ValueError as exc:
        logger.error(f"Invalid --max-length: {exc}")
        raise SystemExit(2) from exc

    config.max_length = length_resolution.value
    logger.info(
        "max_length=%s (source=%s, training=%s)",
        length_resolution.value,
        length_resolution.source,
        length_resolution.training_value,
    )
    for warning in length_resolution.warnings:
        logger.warning(warning)

    model = VEDModel.from_pretrained(args.model_path)
    model = model.to(device)
    model.eval()

    logger.info("✅ 모델 로드 완료")

    # 이미지 로드 및 전처리
    logger.info("이미지 전처리 중...")
    image = Image.open(args.image).convert("RGB")

    transform = transforms.Compose(
        [
            transforms.Resize((config.image_size, config.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )

    pixel_values = transform(image).unsqueeze(0).to(device)

    # 추론
    logger.info("추론 중...")
    with torch.no_grad():
        generated_ids = model.generate(
            pixel_values=pixel_values,
            max_length=config.max_length,
            num_beams=args.num_beams,
            temperature=config.temperature,
            top_k=config.top_k,
            top_p=config.top_p,
            do_sample=config.do_sample,
        )

    # 디코딩
    generated_text = model.tokenizer.decode(
        generated_ids[0],
        skip_special_tokens=True,
    )

    logger.info("✅ 추론 완료")

    generated_tokens = int(generated_ids.shape[-1])
    reached_max_length = generated_tokens >= config.max_length
    logger.info(
        "generated_tokens=%s / max_length=%s (reached_limit=%s)",
        generated_tokens,
        config.max_length,
        reached_max_length,
    )
    if reached_max_length:
        logger.warning(
            "Generation reached max_length boundary; output may be truncated. "
            "Increase --max-length only after memory validation."
        )

    # JSON 검증
    if validate_json(generated_text):
        logger.info("✅ 유효한 JSON 생성")
        json_data = json.loads(generated_text)

        # 통계
        num_entities = len(json_data.get("entities", []))
        logger.info(f"엔티티 수: {num_entities}")
    else:
        logger.warning("⚠️ 유효하지 않은 JSON")

    # 출력
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as output_file:
            if validate_json(generated_text):
                json.dump(
                    json.loads(generated_text),
                    output_file,
                    ensure_ascii=False,
                    indent=2,
                )
            else:
                output_file.write(generated_text)
        logger.info(f"출력 저장: {args.output}")
        return

    print("\n" + "=" * 80)
    print("Generated JSON:")
    print("=" * 80)
    if validate_json(generated_text):
        print(json.dumps(json.loads(generated_text), ensure_ascii=False, indent=2))
    else:
        print(generated_text)


if __name__ == "__main__":
    main()
