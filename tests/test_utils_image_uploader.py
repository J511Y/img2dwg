from __future__ import annotations

import json
from pathlib import Path

import pytest

from img2dwg.utils.image_uploader import ImageUploader, URLCache


class DummyResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


def test_image_uploader_reads_api_keys_and_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMGUR_CLIENT_ID", "imgur-key")
    monkeypatch.setenv("CLOUDINARY_URL", "cloud-key")
    monkeypatch.setenv("GITHUB_TOKEN", "gh-key")

    assert ImageUploader(service="imgur").api_key == "imgur-key"
    assert ImageUploader(service="cloudinary").api_key == "cloud-key"
    assert ImageUploader(service="github").api_key == "gh-key"

    uploader = ImageUploader(service="github", api_key="token")
    monkeypatch.setattr(uploader, "_upload_github", lambda *_: "ok")
    assert uploader.upload(Path("a.png")) == "ok"

    with pytest.raises(ValueError, match="지원하지 않는 서비스"):
        ImageUploader(service="unknown", api_key="x").upload(Path("a.png"))


def test_imgur_upload_success_and_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = tmp_path / "a.png"
    image.write_bytes(b"png")

    uploader = ImageUploader(service="imgur", api_key="id")

    monkeypatch.setattr(
        "img2dwg.utils.image_uploader.requests.post",
        lambda *_, **__: DummyResponse(200, payload={"data": {"link": "https://imgur.com/a"}}),
    )
    assert uploader._upload_imgur(image) == "https://imgur.com/a"

    monkeypatch.setattr(
        "img2dwg.utils.image_uploader.requests.post",
        lambda *_, **__: DummyResponse(500, text="fail"),
    )
    with pytest.raises(RuntimeError, match="Imgur 업로드 실패"):
        uploader._upload_imgur(image)


def test_upload_cloudinary_requires_package(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    image = tmp_path / "a.png"
    image.write_bytes(b"png")

    uploader = ImageUploader(service="cloudinary", api_key="cloud-url")

    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "cloudinary":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(RuntimeError, match="cloudinary 패키지가 필요합니다"):
        uploader._upload_cloudinary(image)


def test_github_upload_new_and_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    image = tmp_path / "sample.png"
    image.write_bytes(b"png")

    monkeypatch.setenv("GITHUB_REPO_OWNER", "owner")
    monkeypatch.setenv("GITHUB_REPO_NAME", "repo")
    monkeypatch.setenv("GITHUB_BRANCH", "develop")

    uploader = ImageUploader(service="github", api_key="gh-token")

    # first call: file missing => create
    monkeypatch.setattr(
        "img2dwg.utils.image_uploader.requests.get",
        lambda *_, **__: DummyResponse(404),
    )
    captured_put_payloads: list[dict] = []

    def fake_put(*_, **kwargs):
        captured_put_payloads.append(kwargs["json"])
        return DummyResponse(201)

    monkeypatch.setattr("img2dwg.utils.image_uploader.requests.put", fake_put)

    url = uploader._upload_github(image, project_name="my project")
    assert url.startswith("https://raw.githubusercontent.com/owner/repo/develop/images/")
    assert "sha" not in captured_put_payloads[-1]

    # second call: existing file => update with sha
    monkeypatch.setattr(
        "img2dwg.utils.image_uploader.requests.get",
        lambda *_, **__: DummyResponse(200, payload={"sha": "abc123"}),
    )
    uploader._upload_github(image)
    assert captured_put_payloads[-1]["sha"] == "abc123"


def test_url_cache_persists_values(tmp_path: Path) -> None:
    cache_file = tmp_path / "cache.json"
    cache = URLCache(cache_file)

    target = tmp_path / "img.png"
    target.write_bytes(b"img")

    assert cache.get(target) is None
    cache.set(target, "https://example.com/img.png")
    assert cache.get(target) == "https://example.com/img.png"

    reloaded = URLCache(cache_file)
    assert reloaded.get(target) == "https://example.com/img.png"
    # file format sanity
    assert json.loads(cache_file.read_text(encoding="utf-8"))
