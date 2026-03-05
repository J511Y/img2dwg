from __future__ import annotations

import json

import pytest
import torch

from img2dwg.ved.metrics import compute_entity_accuracy, compute_json_accuracy, compute_metrics
from img2dwg.ved.utils import (
    count_parameters,
    format_time,
    get_device,
    parse_json_safe,
    set_seed,
    validate_json,
)


def test_validate_and_parse_json_safe() -> None:
    assert validate_json('{"a": 1}') is True
    assert validate_json("{invalid") is False

    assert parse_json_safe('{"x": 10}') == {"x": 10}
    assert parse_json_safe("{invalid") == {}


def test_set_seed_makes_random_state_reproducible() -> None:
    set_seed(123)
    first = torch.rand(3)

    set_seed(123)
    second = torch.rand(3)

    assert torch.allclose(first, second)


def test_count_parameters_and_format_time() -> None:
    model = torch.nn.Sequential(
        torch.nn.Linear(4, 4),
        torch.nn.Linear(4, 2),
    )
    # freeze one layer to verify requires_grad filtering
    for p in model[1].parameters():
        p.requires_grad = False

    assert count_parameters(model) == sum(p.numel() for p in model[0].parameters())
    assert format_time(5.9) == "5s"
    assert format_time(61.2) == "1m 1s"
    assert format_time(3661.1) == "1h 1m 1s"


def test_get_device_returns_expected_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("torch.cuda.is_available", lambda: True)
    assert get_device() == "cuda"

    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    assert get_device() == "cpu"


def test_metrics_json_and_entity_accuracy() -> None:
    refs = [
        json.dumps({"entities": [{"type": "LINE"}, {"t": "TEXT"}]}),
        json.dumps({"entities": [{"type": "CIRCLE"}]}),
    ]
    preds = [
        json.dumps({"entities": [{"type": "LINE"}, {"t": "TEXT"}]}),
        "{invalid",
    ]

    json_metrics = compute_json_accuracy(preds, refs)
    assert json_metrics["parse_success_rate"] == 0.5
    assert json_metrics["exact_match"] == 0.5

    entity_metrics = compute_entity_accuracy(preds, refs)
    assert entity_metrics["entity_count_accuracy"] == 0.5
    assert entity_metrics["entity_type_accuracy"] == 0.5
    assert entity_metrics["avg_entities_pred"] == 1.0
    assert entity_metrics["avg_entities_ref"] == 1.0

    merged = compute_metrics(preds, refs)
    assert "parse_success_rate" in merged
    assert "entity_type_accuracy" in merged


def test_compute_json_accuracy_raises_on_length_mismatch() -> None:
    with pytest.raises(AssertionError):
        compute_json_accuracy(["{}"], ["{}", "{}"])
