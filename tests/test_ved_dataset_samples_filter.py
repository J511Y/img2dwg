from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from img2dwg.ved.dataset import ImageToJSONDataset  # type: ignore[import-untyped]


class _DummyTokenizer:
    def __call__(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        import torch

        return {"input_ids": torch.ones((1, 4), dtype=torch.long)}


def _line(messages: Any) -> str:
    return json.dumps({"messages": messages}, ensure_ascii=False)


def test_load_samples_keeps_only_records_with_user_image_and_assistant(tmp_path: Path) -> None:
    jsonl = tmp_path / "samples.jsonl"
    lines = [
        # malformed messages type (non-list)
        _line("bad-messages"),
        # malformed messages entries (non-dict items)
        _line(["not-a-dict", 123, None]),
        # valid
        _line(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}
                    ],
                },
                {"role": "assistant", "content": "{}"},
            ]
        ),
        # missing assistant
        _line(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}
                    ],
                }
            ]
        ),
        # user content contains non-dict item before valid image_url
        _line(
            [
                {
                    "role": "user",
                    "content": [
                        "bad-item",
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AB=="}},
                    ],
                },
                {"role": "assistant", "content": "{}"},
            ]
        ),
        # missing user image_url
        _line(
            [
                {"role": "user", "content": [{"type": "text", "text": "hello"}]},
                {"role": "assistant", "content": "{}"},
            ]
        ),
        # malformed image_url object (non-dict)
        _line(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": "not-a-dict"},
                    ],
                },
                {"role": "assistant", "content": "{}"},
            ]
        ),
        # malformed image_url url (non-string)
        _line(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": 123}},
                    ],
                },
                {"role": "assistant", "content": "{}"},
            ]
        ),
        # missing user content field
        _line(
            [
                {"role": "user"},
                {"role": "assistant", "content": "{}"},
            ]
        ),
        # non-list user content
        _line(
            [
                {"role": "user", "content": None},
                {"role": "assistant", "content": "{}"},
            ]
        ),
        # assistant content is non-string
        _line(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,CC=="}}
                    ],
                },
                {"role": "assistant", "content": None},
            ]
        ),
        # assistant content is empty string
        _line(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,DD=="}}
                    ],
                },
                {"role": "assistant", "content": ""},
            ]
        ),
        # assistant content is whitespace-only
        _line(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,EE=="}}
                    ],
                },
                {"role": "assistant", "content": "   "},
            ]
        ),
        # valid
        _line(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,BB=="}}
                    ],
                },
                {"role": "assistant", "content": "{}"},
            ]
        ),
    ]
    jsonl.write_text("\n".join(lines) + "\n", encoding="utf-8")

    dataset = ImageToJSONDataset(
        jsonl_path=jsonl,
        tokenizer=_DummyTokenizer(),
        image_size=8,
    )

    assert len(dataset) == 3
