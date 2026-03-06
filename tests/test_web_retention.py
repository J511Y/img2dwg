from __future__ import annotations

# mypy: disable-error-code=import-untyped
import os
from pathlib import Path

import pytest

from img2dwg.web.retention import RetentionStats, cleanup_expired_files


def _touch(path: Path, content: bytes, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(0o644)
    path.touch()
    os.utime(path, (mtime, mtime))


def test_cleanup_expired_files_deletes_only_expired(tmp_path: Path) -> None:
    now = 1_700_000_000.0
    old_file = tmp_path / "runs" / "old.dxf"
    fresh_file = tmp_path / "runs" / "fresh.dxf"

    _touch(old_file, b"old", mtime=now - 3600)
    _touch(fresh_file, b"fresh", mtime=now - 60)

    stats = cleanup_expired_files(tmp_path, max_age_seconds=300, now_ts=now)

    assert isinstance(stats, RetentionStats)
    assert stats.scanned_files == 2
    assert stats.deleted_files == 1
    assert stats.reclaimed_bytes == 3
    assert not old_file.exists()
    assert fresh_file.exists()


def test_cleanup_expired_files_dry_run_keeps_files(tmp_path: Path) -> None:
    now = 1_700_000_000.0
    old_file = tmp_path / "uploads" / "old.png"
    _touch(old_file, b"abcdef", mtime=now - 10_000)

    stats = cleanup_expired_files(tmp_path, max_age_seconds=300, now_ts=now, dry_run=True)

    assert stats.deleted_files == 1
    assert stats.reclaimed_bytes == 6
    assert old_file.exists()


def test_cleanup_expired_files_invalid_age_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_age_seconds"):
        cleanup_expired_files(tmp_path, max_age_seconds=-1)


def test_cleanup_expired_files_missing_root_is_noop(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    stats = cleanup_expired_files(missing, max_age_seconds=300)
    assert stats == RetentionStats(scanned_files=0, deleted_files=0, reclaimed_bytes=0)
