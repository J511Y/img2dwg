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


def test_load_samples_uses_first_user_and_first_assistant_message(tmp_path: Path) -> None:
    payload = {
        "messages": [
            {
                "role": "assistant",
                "content": '{"from": "first-assistant"}',
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}
                ],
            },
            {
                "role": "assistant",
                "content": '{"from": "second-assistant"}',
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,BB=="}}
                ],
            },
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
    assert dataset.samples[0]["image_url"] == "data:image/png;base64,AA=="
    assert dataset.samples[0]["json_str"] == '{"from": "first-assistant"}'


def test_load_samples_does_not_fallback_to_later_assistant_when_first_invalid(
    tmp_path: Path,
) -> None:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}
                ],
            },
            {
                "role": "assistant",
                "content": "   ",
            },
            {
                "role": "assistant",
                "content": '{"from": "later-valid-assistant"}',
            },
        ]
    }

    jsonl = tmp_path / "samples.jsonl"
    jsonl.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")

    dataset = ImageToJSONDataset(
        jsonl_path=jsonl,
        tokenizer=_DummyTokenizer(),
        image_size=8,
    )

    assert len(dataset.samples) == 0
