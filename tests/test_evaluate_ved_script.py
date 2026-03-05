from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "evaluate_ved.py"


def _load_script_module() -> ModuleType:
    module_name = "evaluate_ved_script_for_tests"
    if module_name in sys.modules:
        loaded = sys.modules[module_name]
        return loaded

    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load evaluate_ved.py module spec")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[module_name] = module
    return module


def test_extract_sample_fields_supports_finetune_format() -> None:
    module = _load_script_module()
    record = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "draw it"},
                    {"type": "image_url", "image_url": {"url": "images/sample.png"}},
                ],
            },
            {"role": "assistant", "content": '{"entities": []}'},
        ]
    }

    image_url, reference_json = module.extract_sample_fields(record)

    assert image_url == "images/sample.png"
    assert reference_json == '{"entities": []}'


def test_extract_sample_fields_rejects_missing_messages() -> None:
    module = _load_script_module()

    with pytest.raises(ValueError, match="messages field is required"):
        module.extract_sample_fields({"foo": "bar"})


def test_load_eval_samples_supports_compact_record_format(tmp_path: Path) -> None:
    module = _load_script_module()
    data_file = tmp_path / "eval.jsonl"
    payload = {"image_url": "images/local.png", "json_str": '{"entities": [{"type": "line"}]}'}
    data_file.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")

    samples = module.load_eval_samples(data_file)

    assert len(samples) == 1
    assert samples[0].line_no == 1
    assert samples[0].image_url == "images/local.png"
    assert samples[0].reference_json == '{"entities": [{"type": "line"}]}'


def test_evaluate_predictions_collects_failures() -> None:
    module = _load_script_module()
    samples = [
        module.EvalSample(
            line_no=1, image_url="img1.png", reference_json='{"entities": [{"type": "line"}]}'
        ),
        module.EvalSample(
            line_no=2, image_url="img2.png", reference_json='{"entities": [{"type": "arc"}]}'
        ),
        module.EvalSample(
            line_no=3, image_url="img3.png", reference_json='{"entities": [{"type": "line"}]}'
        ),
    ]
    predictions = [
        '{"entities": [{"type": "line"}]}',
        '{"entities": [{"type": "circle"}]}',
        "not-json",
    ]

    metrics, failures = module.evaluate_predictions(samples, predictions)

    assert metrics["parse_success_rate"] == pytest.approx(2 / 3)
    assert metrics["exact_match"] == pytest.approx(1 / 3)

    reasons = [failure["reason"] for failure in failures]
    assert "exact_mismatch" in reasons
    assert "invalid_prediction_json" in reasons


def test_write_evaluation_artifacts_writes_files(tmp_path: Path) -> None:
    module = _load_script_module()
    metrics = {
        "parse_success_rate": 0.5,
        "exact_match": 0.25,
        "entity_type_accuracy": 0.25,
    }
    failures = [{"line": 1, "reason": "invalid_prediction_json"}]

    metrics_path, failures_path = module.write_evaluation_artifacts(tmp_path, metrics, failures)

    stored_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    stored_failures = failures_path.read_text(encoding="utf-8").strip().splitlines()

    assert stored_metrics == metrics
    assert len(stored_failures) == 1
    assert json.loads(stored_failures[0])["reason"] == "invalid_prediction_json"
