"""Vision Encoder-Decoder 학습용 데이터셋."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import requests  # type: ignore[import-untyped]
import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

from .tokenizer import CADTokenizer


class _NonRetryableHTTPError(RuntimeError):
    """Raised when retry should be skipped for deterministic client-side failures."""


class ImageToJSONDataset(Dataset):
    """이미지→JSON 변환 학습 데이터셋."""

    def __init__(
        self,
        jsonl_path: Path,
        tokenizer: CADTokenizer,
        image_size: int = 384,
        max_length: int = 2048,
        image_dir: Path | None = None,
        remote_timeout_seconds: float = 10.0,
        remote_max_retries: int = 2,
        remote_backoff_seconds: float = 0.5,
        cache_dir: Path | None = None,
        offline: bool = False,
    ) -> None:
        self.jsonl_path = jsonl_path
        self.tokenizer = tokenizer
        self.image_size = image_size
        self.max_length = max_length
        self.image_dir = image_dir
        self.remote_timeout_seconds = max(0.1, remote_timeout_seconds)
        self.remote_max_retries = max(0, remote_max_retries)
        self.remote_backoff_seconds = max(0.0, remote_backoff_seconds)
        self.cache_dir = cache_dir
        self.offline = offline

        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.samples = self._load_samples()

        self.transform = transforms.Compose(
            [
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )

    def _load_samples(self) -> list[dict[str, Any]]:
        samples: list[dict[str, Any]] = []

        with self.jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                messages = record.get("messages", [])

                user_msg = next((m for m in messages if m["role"] == "user"), None)
                if not user_msg:
                    continue

                assistant_msg = next((m for m in messages if m["role"] == "assistant"), None)
                if not assistant_msg:
                    continue

                content = user_msg.get("content", [])
                if not isinstance(content, list):
                    continue

                image_url: str | None = None
                for item in content:
                    if item.get("type") == "image_url":
                        image_url = item["image_url"]["url"]
                        break

                if not image_url:
                    continue

                json_str = assistant_msg["content"]
                samples.append({"image_url": image_url, "json_str": json_str})

        return samples

    def _cache_path_for_url(self, image_url: str) -> Path | None:
        if self.cache_dir is None:
            return None
        suffix = Path(image_url).suffix.lower() or ".img"
        digest = hashlib.sha256(image_url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}{suffix}"

    def _download_remote_image(self, image_url: str) -> Image.Image:
        cache_path = self._cache_path_for_url(image_url)
        if cache_path is not None and cache_path.exists():
            return Image.open(cache_path).convert("RGB")

        if self.offline:
            raise RuntimeError(f"offline mode enabled and cache miss for URL: {image_url}")

        attempts = self.remote_max_retries + 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                response = requests.get(image_url, timeout=self.remote_timeout_seconds)
                status = int(response.status_code)
                if 400 <= status < 500 and status != 429:
                    raise _NonRetryableHTTPError(f"client error status={status}")
                if status >= 500:
                    raise RuntimeError(f"server error status={status}")

                response.raise_for_status()
                content = bytes(response.content)

                if cache_path is not None:
                    cache_path.write_bytes(content)

                return Image.open(BytesIO(content)).convert("RGB")
            except _NonRetryableHTTPError as exc:
                last_error = exc
                break
            except Exception as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    break
                time.sleep(self.remote_backoff_seconds * (2**attempt))

        assert last_error is not None
        raise RuntimeError(f"failed to load remote image: {image_url}") from last_error

    def _load_image(self, image_url: str) -> Image.Image:
        if image_url.startswith("data:image"):
            _, encoded = image_url.split(",", 1)
            image_data = base64.b64decode(encoded)
            return Image.open(BytesIO(image_data)).convert("RGB")

        if image_url.startswith("http"):
            return self._download_remote_image(image_url)

        if self.image_dir:
            image_path = self.image_dir / image_url
        else:
            image_path = Path(image_url)

        return Image.open(image_path).convert("RGB")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        sample = self.samples[idx]

        try:
            image = self._load_image(sample["image_url"])
            pixel_values = self.transform(image)
        except Exception as e:  # pragma: no cover - fallback protection path
            print(f"Error loading image {sample['image_url']}: {e}")
            pixel_values = torch.zeros(3, self.image_size, self.image_size)

        json_str = sample["json_str"]
        encoding = self.tokenizer(
            json_str,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        labels = encoding["input_ids"].squeeze(0)
        return {"pixel_values": pixel_values, "labels": labels}


def collate_fn(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    pixel_values = torch.stack([item["pixel_values"] for item in batch])
    labels = torch.stack([item["labels"] for item in batch])
    return {"pixel_values": pixel_values, "labels": labels}
