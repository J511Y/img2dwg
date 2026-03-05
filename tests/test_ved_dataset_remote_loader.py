from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
import requests
import torch
from PIL import Image

from img2dwg.ved.dataset import ImageToJSONDataset, RemoteImagePolicy


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
        return {"input_ids": torch.zeros((1, max_length), dtype=torch.long)}


class DummyResponse:
    def __init__(
        self, content: bytes, status_code: int = 200, headers: dict[str, str] | None = None
    ):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "image/png"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.HTTPError(f"status={self.status_code}")
            error.response = self  # type: ignore[assignment]
            raise error


def _png_bytes() -> bytes:
    image = Image.new("RGB", (2, 2), (255, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _write_dataset_jsonl(path: Path, image_url: str) -> None:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    }
                ],
            },
            {"role": "assistant", "content": "{}"},
        ]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def _make_dataset(tmp_path: Path, image_url: str, policy: RemoteImagePolicy) -> ImageToJSONDataset:
    jsonl_path = tmp_path / "dataset.jsonl"
    _write_dataset_jsonl(jsonl_path, image_url)
    return ImageToJSONDataset(
        jsonl_path=jsonl_path,
        tokenizer=DummyTokenizer(),
        image_size=32,
        max_length=16,
        remote_policy=policy,
    )


def test_remote_image_cache_hit_skips_second_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_url = "https://example.com/floorplan.png"
    calls: list[float] = []

    def fake_get(url: str, timeout: float) -> DummyResponse:
        assert url == image_url
        calls.append(timeout)
        return DummyResponse(_png_bytes())

    monkeypatch.setattr("img2dwg.ved.dataset.requests.get", fake_get)

    dataset = _make_dataset(
        tmp_path,
        image_url,
        policy=RemoteImagePolicy(cache_dir=tmp_path / "cache", timeout_seconds=7.0),
    )

    first = dataset._load_image(image_url)
    second = dataset._load_image(image_url)

    assert first.size == (2, 2)
    assert second.size == (2, 2)
    assert calls == [7.0]
    assert len(list((tmp_path / "cache").iterdir())) == 1


def test_remote_image_loader_retries_with_backoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_url = "https://example.com/retry.png"
    attempts = {"count": 0}
    sleeps: list[float] = []

    def fake_get(url: str, timeout: float) -> DummyResponse:
        assert url == image_url
        assert timeout == 3.0
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise requests.Timeout("simulated timeout")
        return DummyResponse(_png_bytes())

    monkeypatch.setattr("img2dwg.ved.dataset.requests.get", fake_get)
    monkeypatch.setattr("img2dwg.ved.dataset.time.sleep", lambda value: sleeps.append(value))

    dataset = _make_dataset(
        tmp_path,
        image_url,
        policy=RemoteImagePolicy(
            cache_dir=tmp_path / "cache",
            timeout_seconds=3.0,
            max_retries=2,
            backoff_seconds=0.25,
        ),
    )

    image = dataset._load_image(image_url)

    assert image.size == (2, 2)
    assert attempts["count"] == 3
    assert sleeps == [0.25, 0.5]


def test_remote_image_loader_does_not_retry_on_http_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_url = "https://example.com/missing.png"
    attempts = {"count": 0}
    sleeps: list[float] = []

    def always_404(url: str, timeout: float) -> DummyResponse:
        assert url == image_url
        assert timeout == 2.5
        attempts["count"] += 1
        return DummyResponse(b"", status_code=404)

    monkeypatch.setattr("img2dwg.ved.dataset.requests.get", always_404)
    monkeypatch.setattr("img2dwg.ved.dataset.time.sleep", lambda value: sleeps.append(value))

    dataset = _make_dataset(
        tmp_path,
        image_url,
        policy=RemoteImagePolicy(
            cache_dir=tmp_path / "cache",
            timeout_seconds=2.5,
            max_retries=3,
            backoff_seconds=1.0,
        ),
    )

    with pytest.raises(RuntimeError, match="Failed to load remote image after retries"):
        dataset._load_image(image_url)

    assert attempts["count"] == 1
    assert sleeps == []


def test_remote_image_loader_retries_on_http_429(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_url = "https://example.com/rate-limit.png"
    attempts = {"count": 0}
    sleeps: list[float] = []

    def flaky_429(url: str, timeout: float) -> DummyResponse:
        assert url == image_url
        assert timeout == 1.5
        attempts["count"] += 1
        if attempts["count"] < 3:
            return DummyResponse(b"", status_code=429)
        return DummyResponse(_png_bytes())

    monkeypatch.setattr("img2dwg.ved.dataset.requests.get", flaky_429)
    monkeypatch.setattr("img2dwg.ved.dataset.time.sleep", lambda value: sleeps.append(value))

    dataset = _make_dataset(
        tmp_path,
        image_url,
        policy=RemoteImagePolicy(
            cache_dir=tmp_path / "cache",
            timeout_seconds=1.5,
            max_retries=3,
            backoff_seconds=0.2,
        ),
    )

    image = dataset._load_image(image_url)

    assert image.size == (2, 2)
    assert attempts["count"] == 3
    assert sleeps == [0.2, 0.4]


def test_offline_mode_requires_cached_remote_image(tmp_path: Path) -> None:
    image_url = "https://example.com/offline.png"
    dataset = _make_dataset(
        tmp_path,
        image_url,
        policy=RemoteImagePolicy(cache_dir=tmp_path / "cache", offline=True),
    )

    with pytest.raises(FileNotFoundError, match="Offline mode enabled"):
        dataset._load_image(image_url)


def test_offline_mode_uses_existing_cache_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_url = "https://example.com/cached.png"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_key = hashlib.sha256(image_url.encode("utf-8")).hexdigest()
    (cache_dir / f"{cache_key}.png").write_bytes(_png_bytes())

    def should_not_be_called(url: str, timeout: float) -> DummyResponse:  # pragma: no cover
        del url, timeout
        raise AssertionError("requests.get should not be called in offline cache hit")

    monkeypatch.setattr("img2dwg.ved.dataset.requests.get", should_not_be_called)

    dataset = _make_dataset(
        tmp_path,
        image_url,
        policy=RemoteImagePolicy(cache_dir=cache_dir, offline=True),
    )

    image = dataset._load_image(image_url)

    assert image.size == (2, 2)


def test_getitem_falls_back_to_black_image_on_remote_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_url = "https://example.com/network-fail.png"

    def always_fail(url: str, timeout: float) -> DummyResponse:
        del url, timeout
        raise requests.Timeout("network down")

    monkeypatch.setattr("img2dwg.ved.dataset.requests.get", always_fail)

    dataset = _make_dataset(
        tmp_path,
        image_url,
        policy=RemoteImagePolicy(cache_dir=tmp_path / "cache", max_retries=0),
    )

    sample = dataset[0]

    assert sample["pixel_values"].shape == (3, 32, 32)
    assert float(sample["pixel_values"].abs().sum().item()) == 0.0


def test_getitem_raises_clear_error_in_offline_mode(tmp_path: Path) -> None:
    image_url = "https://example.com/missing-cache.png"
    dataset = _make_dataset(
        tmp_path,
        image_url,
        policy=RemoteImagePolicy(cache_dir=tmp_path / "cache", offline=True),
    )

    with pytest.raises(RuntimeError, match="Offline dataset cannot resolve image from cache"):
        _ = dataset[0]
