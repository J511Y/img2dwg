"""schema_compact 모듈 회귀 테스트."""

import json
from typing import Any

from img2dwg.utils.schema_compact import CompactSchemaConverter


def test_compact_empty_entities_omits_non_finite_origin() -> None:
    converter = CompactSchemaConverter(use_local_coords=True)
    data: dict[str, Any] = {
        "metadata": {"filename": "empty.dwg", "type": "기타", "entity_count": 0},
        "entities": [],
    }

    compacted = converter.compact(data)

    assert compacted["e"] == []
    assert "o" not in compacted

    payload = json.dumps(compacted, allow_nan=False)
    assert "Infinity" not in payload
    assert "NaN" not in payload


def test_expand_empty_entities_keeps_structure_consistent() -> None:
    converter = CompactSchemaConverter(use_local_coords=True)
    compacted: dict[str, Any] = {"m": {"f": "empty.dwg", "t": "기타", "n": 0}, "e": []}

    expanded = converter.expand(compacted)

    assert expanded == {
        "metadata": {"filename": "empty.dwg", "type": "기타", "entity_count": 0},
        "entities": [],
    }


def test_expand_ignores_non_finite_origin_from_input() -> None:
    converter = CompactSchemaConverter(use_local_coords=True)
    compacted: dict[str, Any] = {
        "m": {"f": "x.dwg", "t": "기타", "n": 1},
        "o": [float("inf"), 0.0],
        "e": [{"t": "line", "s": [1.0, 2.0], "e": [3.0, 4.0]}],
    }

    expanded = converter.expand(compacted)

    assert expanded["entities"] == [
        {
            "type": "line",
            "start": {"x": 1.0, "y": 2.0},
            "end": {"x": 3.0, "y": 4.0},
        }
    ]
