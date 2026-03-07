from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from img2dwg.ved.dataset import ImageToJSONDataset  # type: ignore[import-untyped]


class _DummyTokenizer:
    def __call__(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        import torch

        return {"input_ids": torch.ones((1, 4), dtype=torch.long)}


def test_load_samples_skips_malformed_jsonl_lines(tmp_path: Path) -> None:
    jsonl = tmp_path / "samples.jsonl"
    valid = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}
                ],
            },
            {"role": "assistant", "content": "{}"},
        ]
    }
    jsonl.write_text(
        "{not-json}\n" + json.dumps(valid, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    dataset = ImageToJSONDataset(
        jsonl_path=jsonl,
        tokenizer=_DummyTokenizer(),
        image_size=8,
    )

    assert len(dataset) == 1
