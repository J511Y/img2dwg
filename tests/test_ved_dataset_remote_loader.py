from __future__ import annotations

# mypy: disable-error-code=import-untyped
import io
import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from img2dwg.ved.dataset import ImageToJSONDataset


class _DummyTokenizer:
    def __call__(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        import torch

        return {"input_ids": torch.ones((1, 4), dtype=torch.long)}


def _png_bytes() -> bytes:
    image = Image.new("RGB", (4, 4), (255, 255, 255))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


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


class _Resp:
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status={self.status_code}")


def test_remote_loader_uses_cache_after_first_download(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    jsonl = tmp_path / "samples.jsonl"
    url = "https://example.com/a.png"
    _write_jsonl(jsonl, url)

    calls: list[str] = []

    def _fake_get(target: str, timeout: float) -> _Resp:
        assert timeout == 10.0
        calls.append(target)
        return _Resp(_png_bytes())

    monkeypatch.setattr("img2dwg.ved.dataset.requests.get", _fake_get)

    dataset = ImageToJSONDataset(
        jsonl_path=jsonl,
        tokenizer=_DummyTokenizer(),
        cache_dir=tmp_path / "cache",
    )

    dataset._load_image(url)
    dataset._load_image(url)
    assert len(calls) == 1


def test_remote_loader_offline_requires_cache(tmp_path: Path) -> None:
    jsonl = tmp_path / "samples.jsonl"
    url = "https://example.com/a.png"
    _write_jsonl(jsonl, url)

    dataset = ImageToJSONDataset(
        jsonl_path=jsonl,
        tokenizer=_DummyTokenizer(),
        cache_dir=tmp_path / "cache",
        offline=True,
    )

    with pytest.raises(RuntimeError, match="offline mode"):
        dataset._load_image(url)


def test_remote_loader_retries_then_succeeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    jsonl = tmp_path / "samples.jsonl"
    url = "https://example.com/a.png"
    _write_jsonl(jsonl, url)

    attempts = {"n": 0}

    def _fake_get(_target: str, timeout: float) -> _Resp:
        assert timeout == 10.0
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("temporary network error")
        return _Resp(_png_bytes())

    monkeypatch.setattr("img2dwg.ved.dataset.requests.get", _fake_get)
    monkeypatch.setattr("img2dwg.ved.dataset.time.sleep", lambda _s: None)

    dataset = ImageToJSONDataset(
        jsonl_path=jsonl,
        tokenizer=_DummyTokenizer(),
        cache_dir=tmp_path / "cache",
        remote_max_retries=2,
        remote_backoff_seconds=0.01,
    )

    image = dataset._load_image(url)
    assert image.mode == "RGB"
    assert attempts["n"] == 2


def test_remote_loader_does_not_retry_hard_4xx(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    jsonl = tmp_path / "samples.jsonl"
    url = "https://example.com/missing.png"
    _write_jsonl(jsonl, url)

    attempts = {"n": 0}

    def _fake_get(_target: str, timeout: float) -> _Resp:
        assert timeout == 10.0
        attempts["n"] += 1
        return _Resp(b"", status_code=404)

    monkeypatch.setattr("img2dwg.ved.dataset.requests.get", _fake_get)
    monkeypatch.setattr("img2dwg.ved.dataset.time.sleep", lambda _s: None)

    dataset = ImageToJSONDataset(
        jsonl_path=jsonl,
        tokenizer=_DummyTokenizer(),
        remote_max_retries=3,
    )

    with pytest.raises(RuntimeError, match="failed to load remote image"):
        dataset._load_image(url)
    assert attempts["n"] == 1
