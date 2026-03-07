from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from img2dwg.ved.dataset import ImageToJSONDataset  # type: ignore[import-untyped]


class _DummyTokenizer:
    def __call__(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        import torch

        return {"input_ids": torch.ones((1, 4), dtype=torch.long)}


def _write_jsonl(path: Path) -> None:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}}
                ],
            },
            {"role": "assistant", "content": "{}"},
        ]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def test_cache_path_for_url_is_deterministic_for_same_input(tmp_path: Path) -> None:
    jsonl = tmp_path / "samples.jsonl"
    _write_jsonl(jsonl)

    dataset = ImageToJSONDataset(
        jsonl_path=jsonl,
        tokenizer=_DummyTokenizer(),
        cache_dir=tmp_path / "cache",
    )

    url = "https://example.com/assets/image.png"
    path_a = dataset._cache_path_for_url(url)
    path_b = dataset._cache_path_for_url(url)

    assert path_a is not None and path_b is not None
    assert path_a == path_b
    assert path_a.suffix == ".png"
