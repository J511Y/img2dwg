from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from img2dwg.web.retention import cleanup_output_root, format_cleanup_report


def _write_file(path: Path, size: int, *, mtime: datetime) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"a" * size)
    timestamp = mtime.timestamp()
    os.utime(path, (timestamp, timestamp))
    return path


def test_cleanup_applies_max_age_first(tmp_path: Path) -> None:
    now = datetime(2026, 3, 5, tzinfo=timezone.utc)
    old_file = _write_file(tmp_path / "runs" / "old.dxf", 10, mtime=now - timedelta(days=10))
    fresh_file = _write_file(tmp_path / "runs" / "fresh.dxf", 20, mtime=now - timedelta(days=1))

    report = cleanup_output_root(
        tmp_path,
        max_age_days=7,
        max_size_gb=None,
        dry_run=False,
        now=now,
    )

    assert old_file.exists() is False
    assert fresh_file.exists() is True
    assert report.deleted_files == 1
    assert report.deleted_bytes == 10
    assert any("max-age" in entry.reasons for entry in report.entries)


def test_cleanup_enforces_max_size_with_oldest_first(tmp_path: Path) -> None:
    now = datetime(2026, 3, 5, tzinfo=timezone.utc)
    oldest = _write_file(tmp_path / "a.dxf", 4, mtime=now - timedelta(days=3))
    middle = _write_file(tmp_path / "b.dxf", 4, mtime=now - timedelta(days=2))
    newest = _write_file(tmp_path / "c.dxf", 4, mtime=now - timedelta(days=1))

    # 12 bytes total -> cap to 8 bytes should delete only oldest file.
    report = cleanup_output_root(
        tmp_path,
        max_age_days=None,
        max_size_gb=8 / (1024**3),
        dry_run=False,
        now=now,
    )

    assert oldest.exists() is False
    assert middle.exists() is True
    assert newest.exists() is True
    assert report.deleted_files == 1
    assert report.deleted_bytes == 4
    assert any("max-size" in entry.reasons for entry in report.entries)


def test_cleanup_dry_run_reports_without_deleting(tmp_path: Path) -> None:
    now = datetime(2026, 3, 5, tzinfo=timezone.utc)
    target = _write_file(tmp_path / "x" / "old.dxf", 5, mtime=now - timedelta(days=8))

    report = cleanup_output_root(
        tmp_path,
        max_age_days=7,
        max_size_gb=None,
        dry_run=True,
        now=now,
    )

    assert target.exists() is True
    assert report.deleted_files == 1
    assert report.deleted_bytes == 5
    assert "DRY-RUN" in format_cleanup_report(report)


def test_cleanup_with_no_limits_is_noop(tmp_path: Path) -> None:
    now = datetime(2026, 3, 5, tzinfo=timezone.utc)
    target = _write_file(tmp_path / "x" / "keep.dxf", 5, mtime=now - timedelta(days=100))

    report = cleanup_output_root(
        tmp_path,
        max_age_days=None,
        max_size_gb=None,
        dry_run=False,
        now=now,
    )

    assert target.exists() is True
    assert report.deleted_files == 0
    assert report.entries == ()


def test_cleanup_validates_thresholds(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_age_days"):
        cleanup_output_root(tmp_path, max_age_days=0, max_size_gb=None, dry_run=True)

    with pytest.raises(ValueError, match="max_size_gb"):
        cleanup_output_root(tmp_path, max_age_days=None, max_size_gb=0, dry_run=True)
