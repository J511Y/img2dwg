"""Evaluate VED predictions against references and export metric report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from img2dwg.ved.metrics import compute_metrics  # type: ignore[import-untyped]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate VED predictions from JSONL pairs")
    parser.add_argument(
        "--input", type=Path, required=True, help="JSONL path with prediction/reference"
    )
    parser.add_argument("--output", type=Path, required=True, help="output JSON metric report path")
    parser.add_argument(
        "--prediction-key",
        type=str,
        default="prediction",
        help="JSON key for predicted JSON string",
    )
    parser.add_argument(
        "--reference-key",
        type=str,
        default="reference",
        help="JSON key for reference JSON string",
    )
    return parser.parse_args()


def _load_pairs(
    input_path: Path, prediction_key: str, reference_key: str
) -> tuple[list[str], list[str]]:
    predictions: list[str] = []
    references: list[str] = []

    with input_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            payload: Any = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"line {line_no}: expected object JSON")
            if prediction_key not in payload or reference_key not in payload:
                raise ValueError(
                    f"line {line_no}: missing keys ({prediction_key}, {reference_key})"
                )
            pred = payload[prediction_key]
            ref = payload[reference_key]
            if not isinstance(pred, str) or not isinstance(ref, str):
                raise ValueError(f"line {line_no}: prediction/reference must be strings")
            predictions.append(pred)
            references.append(ref)

    return predictions, references


def evaluate(
    input_path: Path, output_path: Path, prediction_key: str, reference_key: str
) -> dict[str, Any]:
    predictions, references = _load_pairs(input_path, prediction_key, reference_key)
    metrics = compute_metrics(predictions, references)
    report = {
        "samples": len(predictions),
        "prediction_key": prediction_key,
        "reference_key": reference_key,
        "metrics": metrics,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    args = parse_args()
    report = evaluate(args.input, args.output, args.prediction_key, args.reference_key)
    print(f"evaluated samples={report['samples']} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
