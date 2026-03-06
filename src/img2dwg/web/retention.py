"""Retention helpers for web publisher output cleanup."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RetentionStats:
    scanned_files: int
    deleted_files: int
    reclaimed_bytes: int


def cleanup_expired_files(
    root: Path,
    *,
    max_age_seconds: float,
    now_ts: float | None = None,
    dry_run: bool = False,
) -> RetentionStats:
    """Delete files older than max_age_seconds under root.

    Directories are preserved; only files are considered.
    """
    if max_age_seconds < 0:
        raise ValueError("max_age_seconds must be >= 0")

    now = time.time() if now_ts is None else now_ts
    scanned = 0
    deleted = 0
    reclaimed = 0

    if not root.exists():
        return RetentionStats(scanned_files=0, deleted_files=0, reclaimed_bytes=0)

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        scanned += 1
        age = now - path.stat().st_mtime
        if age < max_age_seconds:
            continue

        size = path.stat().st_size
        if not dry_run:
            path.unlink()
        deleted += 1
        reclaimed += size

    return RetentionStats(scanned_files=scanned, deleted_files=deleted, reclaimed_bytes=reclaimed)
