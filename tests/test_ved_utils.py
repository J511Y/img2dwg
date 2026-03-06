from __future__ import annotations

import torch

from img2dwg.ved.utils import (  # type: ignore[import-untyped]
    count_parameters,
    format_time,
    parse_json_safe,
    validate_json,
)


def test_validate_and_parse_json_helpers() -> None:
    assert validate_json('{"ok": true}') is True
    assert validate_json("{bad json}") is False

    assert parse_json_safe('{"x": 1}') == {"x": 1}
    assert parse_json_safe("not-json") == {}


def test_format_time_and_count_parameters() -> None:
    assert format_time(59) == "59s"
    assert format_time(61) == "1m 1s"
    assert format_time(3661) == "1h 1m 1s"

    model = torch.nn.Linear(3, 2, bias=True)
    assert count_parameters(model) == 8
