from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image

from img2dwg.ved.dataset import ImageToJSONDataset  # type: ignore[import-untyped]


class _DummyTokenizer:
    def __call__(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        import torch

        return {"input_ids": torch.ones((1, 4), dtype=torch.long)}


def _write_jsonl(path: Path, image_url: str) -> None:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [{"type": "image_url", "image_url": {"url": image_url}}],
            },
            {"role": "assistant", "content": "{}"},
        ]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def test_load_image_resolves_relative_path_with_image_dir(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir(parents=True)
    image_name = "sample.png"
    image_path = image_dir / image_name
    Image.new("RGB", (8, 8), (12, 34, 56)).save(image_path)

    jsonl = tmp_path / "samples.jsonl"
    _write_jsonl(jsonl, image_name)

    dataset = ImageToJSONDataset(
        jsonl_path=jsonl,
        tokenizer=_DummyTokenizer(),
        image_dir=image_dir,
        image_size=8,
    )

    sample = dataset[0]
    assert tuple(sample["pixel_values"].shape) == (3, 8, 8)
    assert tuple(sample["labels"].shape) == (4,)
