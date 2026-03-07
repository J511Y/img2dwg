from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from scripts.fetch_web_floorplan_assets import _validate_filename, sync_manifest


def _write_manifest(path: Path, image_sha: str, image_name: str = "a.png") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "image_filename",
                "image_url",
                "image_sha256",
                "source_page_url",
                "license_name",
                "license_spdx",
                "license_proof_url",
                "retrieved_at",
                "source_family",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "wfpgv1_001",
                "image_filename": image_name,
                "image_url": "https://example.com/a.png",
                "image_sha256": image_sha,
                "source_page_url": "https://example.com/source",
                "license_name": "Public domain",
                "license_spdx": "LicenseRef-Public-Domain",
                "license_proof_url": "https://example.com/source?oldid=1",
                "retrieved_at": "2026-03-07",
                "source_family": "example",
                "notes": "note",
            }
        )


def test_validate_filename_rejects_path_traversal() -> None:
    with pytest.raises(ValueError):
        _validate_filename("../evil.png", "image_filename")
    with pytest.raises(ValueError):
        _validate_filename("sub/evil.png", "image_filename")
    with pytest.raises(ValueError):
        _validate_filename(".hidden.png", "image_filename")


def test_sync_manifest_downloads_and_verifies_hashes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    image_bytes = b"img"
    image_sha = hashlib.sha256(image_bytes).hexdigest()

    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, image_sha=image_sha)

    class _Resp:
        def __init__(self, content: bytes) -> None:
            self.content = content
            self.status_code = 200

        def raise_for_status(self) -> None:
            return None

    def _fake_get(url: str, timeout: int, headers: dict[str, str]) -> _Resp:
        assert timeout == 60
        assert "User-Agent" in headers
        assert url == "https://example.com/a.png"
        return _Resp(image_bytes)

    monkeypatch.setattr("scripts.fetch_web_floorplan_assets.requests.get", _fake_get)

    image_paths = sync_manifest(manifest, tmp_path / "out")
    assert len(image_paths) == 1
    assert image_paths[0].name == "a.png"
    assert image_paths[0].read_bytes() == image_bytes


def test_sync_manifest_rejects_hash_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, image_sha="0" * 64)

    class _Resp:
        content = b"wrong"
        status_code = 200

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(
        "scripts.fetch_web_floorplan_assets.requests.get",
        lambda *_args, **_kwargs: _Resp(),
    )

    with pytest.raises(ValueError, match="mismatch"):
        sync_manifest(manifest, tmp_path / "out")
