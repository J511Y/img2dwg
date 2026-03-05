# ruff: noqa: E402
"""Vision Encoder-Decoder 모델 평가 스크립트."""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import requests
from PIL import Image

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class EvalSample(NamedTuple):
    """평가 샘플 표현."""

    line_no: int
    image_url: str
    reference_json: str


def parse_args() -> argparse.Namespace:
    """명령행 인자를 파싱한다."""
    parser = argparse.ArgumentParser(description="VED 모델 평가")
    parser.add_argument(
        "--model-path",
        type=Path,
        default=project_root / "output" / "ved_checkpoints" / "best",
        help="학습된 모델 경로",
    )
    parser.add_argument(
        "--data-file",
        type=Path,
        required=True,
        help="평가용 JSONL 파일 경로",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "output" / "ved_eval",
        help="평가 산출물 디렉토리",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=None,
        help="상대 이미지 경로 기준 디렉토리",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="평가 샘플 수 제한",
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
        help="최대 생성 길이 (기본: 모델 설정)",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="추론 디바이스",
    )
    return parser.parse_args()


def load_eval_samples(data_file: Path) -> list[EvalSample]:
    """평가용 JSONL에서 샘플을 로드한다."""
    samples: list[EvalSample] = []

    with data_file.open(encoding="utf-8") as file:
        for line_no, raw_line in enumerate(file, start=1):
            if not raw_line.strip():
                continue

            record = json.loads(raw_line)
            image_url, reference_json = extract_sample_fields(record)
            samples.append(
                EvalSample(
                    line_no=line_no,
                    image_url=image_url,
                    reference_json=reference_json,
                )
            )

    return samples


def extract_sample_fields(record: dict[str, Any]) -> tuple[str, str]:
    """레코드에서 image_url과 정답 JSON 문자열을 추출한다."""
    if "image_url" in record and "json_str" in record:
        return str(record["image_url"]), str(record["json_str"])

    messages = record.get("messages")
    if not isinstance(messages, list):
        raise ValueError("messages field is required for finetune-format records")

    user_message = next((item for item in messages if item.get("role") == "user"), None)
    assistant_message = next((item for item in messages if item.get("role") == "assistant"), None)

    if user_message is None or assistant_message is None:
        raise ValueError("record must contain user/assistant messages")

    image_url = extract_image_url_from_user_message(user_message)
    if image_url is None:
        raise ValueError("user message must include image_url content")

    assistant_content = assistant_message.get("content")
    if isinstance(assistant_content, str):
        reference_json = assistant_content
    else:
        reference_json = json.dumps(assistant_content, ensure_ascii=False)

    return image_url, reference_json


def extract_image_url_from_user_message(user_message: dict[str, Any]) -> str | None:
    """user message에서 image_url을 추출한다."""
    content = user_message.get("content")
    if isinstance(content, str):
        return None
    if not isinstance(content, list):
        return None

    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "image_url":
            continue
        image_url_value = item.get("image_url", {}).get("url")
        if image_url_value:
            return str(image_url_value)

    return None


def load_image(image_url: str, image_dir: Path | None = None) -> Image.Image:
    """이미지 URL(또는 경로)에서 PIL 이미지를 로드한다."""
    if image_url.startswith("data:image"):
        _, encoded = image_url.split(",", 1)
        image_data = base64.b64decode(encoded)
        return Image.open(io.BytesIO(image_data)).convert("RGB")

    if image_url.startswith("http://") or image_url.startswith("https://"):
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGB")

    image_path = Path(image_url)
    if not image_path.is_absolute() and image_dir is not None:
        image_path = image_dir / image_path

    return Image.open(image_path).convert("RGB")


def is_valid_json(candidate: str) -> bool:
    """JSON 문자열 유효성을 검증한다."""
    try:
        json.loads(candidate)
    except json.JSONDecodeError:
        return False
    return True


def compute_metrics_for_predictions(
    predictions: list[str], references: list[str]
) -> dict[str, float]:
    """예측/정답 목록에 대한 집계 metric을 계산한다."""
    if len(predictions) != len(references):
        raise ValueError("predictions and references must have the same length")

    if not predictions:
        return {
            "parse_success_rate": 0.0,
            "exact_match": 0.0,
            "entity_count_accuracy": 0.0,
            "entity_type_accuracy": 0.0,
            "avg_entities_pred": 0.0,
            "avg_entities_ref": 0.0,
        }

    parse_success = 0
    exact_match = 0
    entity_count_correct = 0
    entity_type_correct = 0
    total_entities_pred = 0
    total_entities_ref = 0

    for prediction, reference in zip(predictions, references, strict=True):
        if is_valid_json(prediction):
            parse_success += 1

        if not is_valid_json(prediction) or not is_valid_json(reference):
            continue

        prediction_obj = json.loads(prediction)
        reference_obj = json.loads(reference)
        if prediction_obj == reference_obj:
            exact_match += 1

        prediction_entities = prediction_obj.get("entities", [])
        reference_entities = reference_obj.get("entities", [])

        total_entities_pred += len(prediction_entities)
        total_entities_ref += len(reference_entities)

        if len(prediction_entities) == len(reference_entities):
            entity_count_correct += 1

        prediction_types = [
            entity.get("type") for entity in prediction_entities if isinstance(entity, dict)
        ]
        reference_types = [
            entity.get("type") for entity in reference_entities if isinstance(entity, dict)
        ]
        if set(prediction_types) == set(reference_types):
            entity_type_correct += 1

    total = len(predictions)
    return {
        "parse_success_rate": parse_success / total,
        "exact_match": exact_match / total,
        "entity_count_accuracy": entity_count_correct / total,
        "entity_type_accuracy": entity_type_correct / total,
        "avg_entities_pred": total_entities_pred / total,
        "avg_entities_ref": total_entities_ref / total,
    }


def evaluate_predictions(
    samples: list[EvalSample],
    predictions: list[str],
    skip_failure_indices: set[int] | None = None,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    """예측/정답을 비교하여 metric과 실패 로그를 생성한다."""
    references = [sample.reference_json for sample in samples]
    failures: list[dict[str, Any]] = []
    skipped = skip_failure_indices or set()

    if not predictions:
        return compute_metrics_for_predictions([], []), failures

    metrics = compute_metrics_for_predictions(predictions, references)

    for sample, prediction, reference in zip(samples, predictions, references, strict=True):
        if sample.line_no in skipped:
            continue

        if not is_valid_json(prediction):
            failures.append(
                {
                    "line": sample.line_no,
                    "image_url": sample.image_url,
                    "reason": "invalid_prediction_json",
                    "prediction_preview": prediction[:500],
                }
            )
            continue

        if not is_valid_json(reference):
            failures.append(
                {
                    "line": sample.line_no,
                    "image_url": sample.image_url,
                    "reason": "invalid_reference_json",
                    "reference_preview": reference[:500],
                }
            )
            continue

        prediction_obj = json.loads(prediction)
        reference_obj = json.loads(reference)
        if prediction_obj != reference_obj:
            failures.append(
                {
                    "line": sample.line_no,
                    "image_url": sample.image_url,
                    "reason": "exact_mismatch",
                }
            )

    return metrics, failures


def write_evaluation_artifacts(
    output_dir: Path,
    metrics: dict[str, Any],
    failures: list[dict[str, Any]],
) -> tuple[Path, Path]:
    """평가 산출물 파일을 저장한다."""
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = output_dir / "metrics.json"
    failures_path = output_dir / "failures.jsonl"

    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    with failures_path.open("w", encoding="utf-8") as file:
        for failure in failures:
            file.write(json.dumps(failure, ensure_ascii=False) + "\n")

    return metrics_path, failures_path


def main() -> None:
    """메인 평가 함수."""
    args = parse_args()

    import torch
    from torchvision import transforms
    from tqdm import tqdm

    from img2dwg.utils.logger import get_logger, setup_logging
    from img2dwg.ved.config import InferenceConfig
    from img2dwg.ved.model import VEDModel
    from img2dwg.ved.utils import get_device

    setup_logging(log_level="INFO")
    logger = get_logger(__name__)

    logger.info("=" * 80)
    logger.info("Vision Encoder-Decoder 평가")
    logger.info("=" * 80)
    logger.info("Model: %s", args.model_path)
    logger.info("Data file: %s", args.data_file)

    samples = load_eval_samples(args.data_file)
    if args.max_samples is not None:
        if args.max_samples < 1:
            raise ValueError("--max-samples must be >= 1")
        samples = samples[: args.max_samples]

    logger.info("Samples: %s", len(samples))

    config = InferenceConfig(model_path=args.model_path)

    device = get_device() if args.device == "auto" else args.device
    logger.info("Device: %s", device)

    model = VEDModel.from_pretrained(args.model_path, config=config)
    model = model.to(device)
    model.eval()

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

    predictions: list[str] = []
    inference_failures: list[dict[str, Any]] = []
    inference_failed_indices: set[int] = set()

    for sample in tqdm(samples, desc="Evaluating", unit="sample"):
        try:
            image = load_image(sample.image_url, image_dir=args.image_dir)
            pixel_values = transform(image).unsqueeze(0).to(device)

            with torch.no_grad():
                generated_ids = model.generate(
                    pixel_values=pixel_values,
                    max_length=args.max_length or config.max_length,
                    num_beams=args.num_beams,
                    temperature=config.temperature,
                    top_k=config.top_k,
                    top_p=config.top_p,
                    do_sample=config.do_sample,
                )

            prediction = model.tokenizer.decode(generated_ids[0], skip_special_tokens=True)
        except Exception as exc:  # pragma: no cover - runtime/inference fallback
            prediction = ""
            inference_failed_indices.add(sample.line_no)
            inference_failures.append(
                {
                    "line": sample.line_no,
                    "image_url": sample.image_url,
                    "reason": "inference_error",
                    "error": str(exc),
                }
            )

        predictions.append(prediction)

    metric_values, metric_failures = evaluate_predictions(
        samples,
        predictions,
        skip_failure_indices=inference_failed_indices,
    )

    all_failures = inference_failures + metric_failures

    metrics_payload: dict[str, Any] = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "model_path": str(args.model_path),
        "data_file": str(args.data_file),
        "sample_count": len(samples),
        "failure_count": len(all_failures),
        **metric_values,
    }

    metrics_path, failures_path = write_evaluation_artifacts(
        args.output, metrics_payload, all_failures
    )

    logger.info("parse_success_rate=%.4f", metric_values["parse_success_rate"])
    logger.info("exact_match=%.4f", metric_values["exact_match"])
    logger.info("entity_type_accuracy=%.4f", metric_values["entity_type_accuracy"])
    logger.info("metrics.json: %s", metrics_path)
    logger.info("failures.jsonl: %s", failures_path)


if __name__ == "__main__":
    main()
