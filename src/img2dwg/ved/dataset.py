"""Vision Encoder-Decoder 학습용 데이터셋."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]
import torch
from PIL import Image, UnidentifiedImageError
from torch.utils.data import Dataset
from torchvision import transforms

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RemoteImagePolicy:
    """원격 이미지 로딩 정책."""

    timeout_seconds: float = 10.0
    max_retries: int = 2
    backoff_seconds: float = 0.5
    cache_dir: Path | None = None
    offline: bool = False


class ImageToJSONDataset(Dataset):
    """
    이미지→JSON 변환을 위한 데이터셋.

    JSONL 파일에서 이미지 URL과 JSON 데이터를 로드하여
    Vision Encoder-Decoder 학습에 사용할 수 있는 형태로 변환한다.
    """

    _VALID_IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".gif",
        ".tif",
        ".tiff",
    }
    _CONTENT_TYPE_TO_EXT = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/gif": ".gif",
        "image/tiff": ".tiff",
    }

    def __init__(
        self,
        jsonl_path: Path,
        tokenizer: Any,
        image_size: int = 384,
        max_length: int = 2048,
        image_dir: Path | None = None,
        remote_policy: RemoteImagePolicy | None = None,
    ):
        """
        ImageToJSONDataset을 초기화한다.

        Args:
            jsonl_path: JSONL 파일 경로
            tokenizer: CAD 토크나이저
            image_size: 이미지 리사이즈 크기
            max_length: 최대 토큰 길이
            image_dir: 이미지 디렉토리 (URL이 아닌 로컬 경로인 경우)
            remote_policy: 원격 이미지 로딩 정책
        """
        self.jsonl_path = jsonl_path
        self.tokenizer = tokenizer
        self.image_size = image_size
        self.max_length = max_length
        self.image_dir = image_dir
        self.remote_policy = remote_policy or RemoteImagePolicy()
        self.remote_cache_dir = self._resolve_remote_cache_dir()

        # 데이터 로드
        self.samples = self._load_samples()

        # 이미지 전처리 변환
        self.transform = transforms.Compose(
            [
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],  # ImageNet 평균
                    std=[0.229, 0.224, 0.225],  # ImageNet 표준편차
                ),
            ]
        )

    def _resolve_remote_cache_dir(self) -> Path:
        if self.remote_policy.cache_dir is not None:
            return Path(self.remote_policy.cache_dir)
        return self.jsonl_path.parent / ".ved_image_cache"

    def _load_samples(self) -> list[dict[str, Any]]:
        """
        JSONL 파일에서 샘플을 로드한다.

        Returns:
            샘플 리스트
        """
        samples = []

        with open(self.jsonl_path, encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)

                # OpenAI 파인튜닝 형식에서 추출
                messages = record.get("messages", [])

                # User 메시지에서 이미지 URL 추출
                user_msg = next((m for m in messages if m["role"] == "user"), None)
                if not user_msg:
                    continue

                # Assistant 메시지에서 JSON 추출
                assistant_msg = next((m for m in messages if m["role"] == "assistant"), None)
                if not assistant_msg:
                    continue

                # 이미지 URL 추출 (첫 번째 이미지만 사용)
                content = user_msg.get("content", [])
                image_url = None
                for item in content:
                    if item.get("type") == "image_url":
                        image_url = item["image_url"]["url"]
                        break

                if not image_url:
                    continue

                # JSON 데이터
                json_str = assistant_msg["content"]

                samples.append(
                    {
                        "image_url": image_url,
                        "json_str": json_str,
                    }
                )

        return samples

    def _load_image(self, image_url: str) -> Image.Image:
        """
        이미지를 로드한다.

        Args:
            image_url: 이미지 URL 또는 경로

        Returns:
            PIL Image
        """
        # URL인 경우 (base64 또는 http)
        if image_url.startswith("data:image"):
            header, encoded = image_url.split(",", 1)
            del header
            image_data = base64.b64decode(encoded)
            return Image.open(io.BytesIO(image_data)).convert("RGB")

        if image_url.startswith("http://") or image_url.startswith("https://"):
            return self._load_remote_image(image_url)

        # 로컬 파일 경로
        if self.image_dir:
            image_path = self.image_dir / image_url
        else:
            image_path = Path(image_url)

        return Image.open(image_path).convert("RGB")

    def _load_remote_image(self, image_url: str) -> Image.Image:
        self.remote_cache_dir.mkdir(parents=True, exist_ok=True)

        cache_key = hashlib.sha256(image_url.encode("utf-8")).hexdigest()
        cached_file = self._find_cached_file(cache_key)
        if cached_file is not None:
            try:
                return Image.open(cached_file).convert("RGB")
            except UnidentifiedImageError:
                logger.warning("Corrupt cached image detected. Re-downloading: %s", cached_file)
                cached_file.unlink(missing_ok=True)

        if self.remote_policy.offline:
            raise FileNotFoundError(
                f"Offline mode enabled and cache missing for remote image: {image_url}"
            )

        last_error: Exception | None = None
        max_attempts = self.remote_policy.max_retries + 1

        for attempt_idx in range(max_attempts):
            try:
                response = requests.get(image_url, timeout=self.remote_policy.timeout_seconds)
                response.raise_for_status()
                content_type = (
                    response.headers.get("Content-Type", "").split(";")[0].strip().lower()
                )
                if content_type and not content_type.startswith("image/"):
                    raise ValueError(
                        f"Expected image content type for {image_url}, got: {content_type}"
                    )

                ext = self._guess_extension(image_url, response)
                cache_path = self.remote_cache_dir / f"{cache_key}{ext}"
                self._write_cache_file(cache_path, response.content)
                return Image.open(io.BytesIO(response.content)).convert("RGB")

            except (
                requests.exceptions.RequestException,
                UnidentifiedImageError,
                ValueError,
            ) as exc:
                last_error = exc
                should_stop_retry = self._is_non_retryable_http_error(exc)
                if should_stop_retry or attempt_idx == max_attempts - 1:
                    break

                backoff = self.remote_policy.backoff_seconds * (2**attempt_idx)
                logger.warning(
                    "Remote image download failed (attempt %s/%s): %s",
                    attempt_idx + 1,
                    max_attempts,
                    image_url,
                )
                if backoff > 0:
                    time.sleep(backoff)

        raise RuntimeError(
            f"Failed to load remote image after retries: {image_url}"
        ) from last_error

    @staticmethod
    def _is_non_retryable_http_error(exc: Exception) -> bool:
        if not isinstance(exc, requests.exceptions.HTTPError):
            return False

        response = exc.response
        if response is None:
            return False

        status_code = getattr(response, "status_code", None)
        if not isinstance(status_code, int):
            return False

        if status_code in {408, 429}:
            return False

        return 400 <= status_code < 500

    def _write_cache_file(self, cache_path: Path, payload: bytes) -> None:
        tmp_path = cache_path.with_suffix(f"{cache_path.suffix}.tmp")
        tmp_path.write_bytes(payload)
        tmp_path.replace(cache_path)

    def _find_cached_file(self, cache_key: str) -> Path | None:
        matches = sorted(self.remote_cache_dir.glob(f"{cache_key}.*"))
        if not matches:
            return None
        return matches[0]

    def _guess_extension(self, image_url: str, response: Any) -> str:
        parsed = urlparse(image_url)
        suffix = Path(parsed.path).suffix.lower()
        if suffix in self._VALID_IMAGE_EXTENSIONS:
            return suffix

        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type in self._CONTENT_TYPE_TO_EXT:
            return self._CONTENT_TYPE_TO_EXT[content_type]

        return ".img"

    def __len__(self) -> int:
        """데이터셋 크기를 반환한다."""
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        """
        샘플을 반환한다.

        Args:
            idx: 샘플 인덱스

        Returns:
            {
                "pixel_values": 이미지 텐서 (C, H, W),
                "labels": 타겟 토큰 ID (max_length,)
            }
        """
        sample = self.samples[idx]

        # 이미지 로드 및 전처리
        try:
            image = self._load_image(sample["image_url"])
            pixel_values = self.transform(image)
        except Exception as e:
            if self.remote_policy.offline:
                raise RuntimeError(
                    f"Offline dataset cannot resolve image from cache: {sample['image_url']}"
                ) from e
            logger.warning("Error loading image %s: %s", sample["image_url"], e)
            # 에러 시 검은색 이미지 반환
            pixel_values = torch.zeros(3, self.image_size, self.image_size)

        # JSON 토큰화
        json_str = sample["json_str"]
        encoding = self.tokenizer(
            json_str,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        labels = encoding["input_ids"].squeeze(0)

        return {
            "pixel_values": pixel_values,
            "labels": labels,
        }


def collate_fn(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    """
    배치 collate 함수.

    Args:
        batch: 샘플 리스트

    Returns:
        배치 딕셔너리
    """
    pixel_values = torch.stack([item["pixel_values"] for item in batch])
    labels = torch.stack([item["labels"] for item in batch])

    return {
        "pixel_values": pixel_values,
        "labels": labels,
    }
