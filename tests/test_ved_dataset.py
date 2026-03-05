from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import pytest
import requests
import torch
from PIL import Image

from img2dwg.ved.dataset import ImageToJSONDataset, collate_fn


class DummyTokenizer:
    def __call__(
        self,
        text: str,
        max_length: int,
        padding: str,
        truncation: bool,
        return_tensors: str,
    ) -> dict[str, torch.Tensor]:
        del text, padding, truncation, return_tensors
        return {"input_ids": torch.ones((1, max_length), dtype=torch.long)}


def _write_jsonl(path: Path, image_url: str, content: str = "{}") -> None:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [{"type": "image_url", "image_url": {"url": image_url}}],
            },
            {"role": "assistant", "content": content},
        ]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def _png_bytes() -> bytes:
    image = Image.new("RGB", (4, 4), (255, 255, 255))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_dataset_loads_local_relative_image(tmp_path: Path) -> None:
    image_path = tmp_path / "img.png"
    Image.new("RGB", (2, 2), (0, 0, 0)).save(image_path)

    jsonl_path = tmp_path / "samples.jsonl"
    _write_jsonl(jsonl_path, "img.png")

    ds = ImageToJSONDataset(
        jsonl_path=jsonl_path,
        tokenizer=DummyTokenizer(),
        image_size=16,
        max_length=8,
        image_dir=tmp_path,
    )

    sample = ds[0]
    assert sample["pixel_values"].shape == (3, 16, 16)
    assert sample["labels"].shape == (8,)


def test_dataset_loads_base64_image(tmp_path: Path) -> None:
    encoded = base64.b64encode(_png_bytes()).decode("ascii")
    image_url = f"data:image/png;base64,{encoded}"

    jsonl_path = tmp_path / "samples.jsonl"
    _write_jsonl(jsonl_path, image_url)

    ds = ImageToJSONDataset(jsonl_path=jsonl_path, tokenizer=DummyTokenizer(), image_size=8, max_length=4)
    sample = ds[0]

    assert sample["pixel_values"].shape == (3, 8, 8)


def test_dataset_http_image_and_error_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jsonl_path = tmp_path / "samples.jsonl"
    image_url = "https://example.com/test.png"
    _write_jsonl(jsonl_path, image_url)

    class Resp:
        def __init__(self, content: bytes) -> None:
            self.content = content

    monkeypatch.setattr("requests.get", lambda _: Resp(_png_bytes()))
    ds = ImageToJSONDataset(jsonl_path=jsonl_path, tokenizer=DummyTokenizer(), image_size=8, max_length=4)
    assert ds[0]["pixel_values"].shape == (3, 8, 8)

    def raise_timeout(url: str):
        del url
        raise requests.Timeout("boom")

    monkeypatch.setattr("requests.get", raise_timeout)
    fallback = ds[0]["pixel_values"]
    assert float(fallback.abs().sum().item()) == 0.0


def test_collate_fn_stacks_batch() -> None:
    batch = [
        {"pixel_values": torch.zeros(3, 8, 8), "labels": torch.ones(4, dtype=torch.long)},
        {"pixel_values": torch.ones(3, 8, 8), "labels": torch.zeros(4, dtype=torch.long)},
    ]
    collated = collate_fn(batch)

    assert collated["pixel_values"].shape == (2, 3, 8, 8)
    assert collated["labels"].shape == (2, 4)
