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


def test_cache_path_uses_url_suffix_or_default_img(tmp_path: Path) -> None:
    jsonl = tmp_path / "samples.jsonl"
    _write_jsonl(jsonl)

    dataset = ImageToJSONDataset(
        jsonl_path=jsonl,
        tokenizer=_DummyTokenizer(),
        cache_dir=tmp_path / "cache",
    )

    with_suffix = dataset._cache_path_for_url("https://example.com/file.jpeg")
    without_suffix = dataset._cache_path_for_url("https://example.com/noext")

    assert with_suffix is not None and with_suffix.suffix == ".jpeg"
    assert without_suffix is not None and without_suffix.suffix == ".img"
