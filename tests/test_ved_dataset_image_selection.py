from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from img2dwg.ved.dataset import ImageToJSONDataset  # type: ignore[import-untyped]


class _DummyTokenizer:
    def __call__(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        import torch

        return {"input_ids": torch.ones((1, 4), dtype=torch.long)}


def test_load_samples_selects_first_image_url_from_user_content(tmp_path: Path) -> None:
    first_url = "data:image/png;base64,AA=="
    second_url = "data:image/png;base64,BB=="
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "preface"},
                    {"type": "image_url", "image_url": {"url": first_url}},
                    {"type": "image_url", "image_url": {"url": second_url}},
                ],
            },
            {"role": "assistant", "content": "{}"},
        ]
    }

    jsonl = tmp_path / "samples.jsonl"
    jsonl.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")

    dataset = ImageToJSONDataset(
        jsonl_path=jsonl,
        tokenizer=_DummyTokenizer(),
        image_size=8,
    )

    assert len(dataset.samples) == 1
    assert dataset.samples[0]["image_url"] == first_url
