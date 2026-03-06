from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from scripts.fetch_web_benchmark_assets import _safe_output_path, _validate_filename, sync_manifest


def _write_manifest(path: Path, image_sha: str, dxf_sha: str, image_name: str = "a.jpg") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "image_filename",
                "image_url",
                "image_sha256",
                "dxf_candidate_filename",
                "dxf_candidate_url",
                "dxf_candidate_sha256",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "case-1",
                "image_filename": image_name,
                "image_url": "https://example.com/a.jpg",
                "image_sha256": image_sha,
                "dxf_candidate_filename": "a.dxf",
                "dxf_candidate_url": "https://example.com/a.dxf",
                "dxf_candidate_sha256": dxf_sha,
            }
        )


def test_validate_filename_blocks_traversal_tokens() -> None:
    with pytest.raises(ValueError):
        _validate_filename("../evil.jpg", "image_filename")
    with pytest.raises(ValueError):
        _validate_filename("a/b.jpg", "image_filename")
    with pytest.raises(ValueError):
        _validate_filename(".hidden", "image_filename")


def test_safe_output_path_stays_within_bucket(tmp_path: Path) -> None:
    path = _safe_output_path(tmp_path, "images", "sample.jpg")
    assert path.parent == (tmp_path / "images").resolve()


def test_sync_manifest_downloads_and_verifies_hashes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image_bytes = b"img"
    dxf_bytes = b"dxf"
    image_sha = hashlib.sha256(image_bytes).hexdigest()
    dxf_sha = hashlib.sha256(dxf_bytes).hexdigest()
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, image_sha=image_sha, dxf_sha=dxf_sha)

    class _Resp:
        def __init__(self, content: bytes) -> None:
            self.content = content

        def raise_for_status(self) -> None:
            return None

    def _fake_get(url: str, timeout: int) -> _Resp:
        assert timeout == 30
        if url.endswith(".jpg"):
            return _Resp(image_bytes)
        return _Resp(dxf_bytes)

    monkeypatch.setattr("scripts.fetch_web_benchmark_assets.requests.get", _fake_get)

    images, dxfs = sync_manifest(manifest, tmp_path / "out")
    assert images == 1
    assert dxfs == 1
    assert (tmp_path / "out" / "images" / "a.jpg").read_bytes() == image_bytes
    assert (tmp_path / "out" / "dxf_candidates" / "a.dxf").read_bytes() == dxf_bytes


def test_sync_manifest_rejects_hash_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, image_sha="0" * 64, dxf_sha="1" * 64)

    class _Resp:
        content = b"wrong"

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(
        "scripts.fetch_web_benchmark_assets.requests.get", lambda *_args, **_kwargs: _Resp()
    )

    with pytest.raises(ValueError, match="mismatch"):
        sync_manifest(manifest, tmp_path / "out")
