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


def test_init_creates_cache_dir_when_configured(tmp_path: Path) -> None:
    jsonl = tmp_path / "samples.jsonl"
    _write_jsonl(jsonl)

    cache_dir = tmp_path / "nested" / "cache"
    assert not cache_dir.exists()

    _ = ImageToJSONDataset(
        jsonl_path=jsonl,
        tokenizer=_DummyTokenizer(),
        cache_dir=cache_dir,
    )

    assert cache_dir.exists() and cache_dir.is_dir()
