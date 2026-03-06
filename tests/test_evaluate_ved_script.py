from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.evaluate_ved import evaluate


def _write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8"
    )


def test_evaluate_writes_metric_report(tmp_path: Path) -> None:
    input_path = tmp_path / "pairs.jsonl"
    output_path = tmp_path / "report.json"

    rows = [
        {
            "prediction": '{"entities": [{"type": "LINE"}]}',
            "reference": '{"entities": [{"type": "LINE"}]}',
        },
        {
            "prediction": '{"entities": [{"type": "TEXT"}]}',
            "reference": '{"entities": [{"type": "LINE"}]}',
        },
    ]
    _write_jsonl(input_path, rows)

    report = evaluate(input_path, output_path, "prediction", "reference")
    assert report["samples"] == 2
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["samples"] == 2
    assert "metrics" in payload
    assert payload["metrics"]["parse_success_rate"] == pytest.approx(1.0)


def test_evaluate_raises_on_missing_keys(tmp_path: Path) -> None:
    input_path = tmp_path / "bad.jsonl"
    output_path = tmp_path / "report.json"
    _write_jsonl(input_path, [{"prediction": "{}"}])

    with pytest.raises(ValueError, match="missing keys"):
        evaluate(input_path, output_path, "prediction", "reference")


def test_evaluate_handles_empty_input_as_zero_metrics(tmp_path: Path) -> None:
    input_path = tmp_path / "empty.jsonl"
    output_path = tmp_path / "report.json"
    input_path.write_text("", encoding="utf-8")

    report = evaluate(input_path, output_path, "prediction", "reference")
    assert report["samples"] == 0
    assert report["metrics"]["parse_success_rate"] == 0.0
    assert report["metrics"]["exact_match"] == 0.0


def test_evaluate_raises_on_non_string_prediction_or_reference(tmp_path: Path) -> None:
    input_path = tmp_path / "bad_type.jsonl"
    output_path = tmp_path / "report.json"
    bad_row: dict[str, Any] = {"prediction": {}, "reference": "{}"}
    _write_jsonl(input_path, [bad_row])

    with pytest.raises(ValueError, match="must be strings"):
        evaluate(input_path, output_path, "prediction", "reference")


def test_evaluate_supports_custom_prediction_and_reference_keys(tmp_path: Path) -> None:
    input_path = tmp_path / "custom.jsonl"
    output_path = tmp_path / "report.json"
    _write_jsonl(
        input_path,
        [{"pred_json": '{"entities": []}', "ref_json": '{"entities": []}'}],
    )

    report = evaluate(input_path, output_path, "pred_json", "ref_json")
    assert report["samples"] == 1
    assert report["prediction_key"] == "pred_json"
    assert report["reference_key"] == "ref_json"
    assert report["metrics"]["exact_match"] == pytest.approx(1.0)
