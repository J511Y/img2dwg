from __future__ import annotations

import json
from pathlib import Path

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
