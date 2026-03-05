from __future__ import annotations

import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

AGE_REASON = "max-age"
SIZE_REASON = "max-size"


@dataclass(frozen=True, slots=True)
class CleanupEntry:
    path: Path
    size_bytes: int
    modified_at: datetime
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CleanupReport:
    root: Path
    dry_run: bool
    scanned_files: int
    scanned_bytes: int
    deleted_files: int
    deleted_bytes: int
    max_age_days: float | None
    max_size_gb: float | None
    entries: tuple[CleanupEntry, ...]


@dataclass(frozen=True, slots=True)
class _FileEntry:
    path: Path
    size_bytes: int
    modified_at_ts: float


def _resolve_root(root: Path) -> Path:
    return root.resolve()


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def _iter_regular_files(root: Path) -> list[_FileEntry]:
    if not root.exists():
        return []

    root_resolved = _resolve_root(root)
    files: list[_FileEntry] = []
    for path in root.rglob("*"):
        try:
            stat_result = path.lstat()
        except FileNotFoundError:
            continue

        # Skip symlink/special files; only process regular files inside the root.
        if not stat.S_ISREG(stat_result.st_mode):
            continue

        if not _is_within_root(path, root_resolved):
            continue

        files.append(
            _FileEntry(
                path=path,
                size_bytes=stat_result.st_size,
                modified_at_ts=stat_result.st_mtime,
            )
        )
    return files


def _collect_cleanup_targets(
    files: list[_FileEntry],
    *,
    max_age_days: float | None,
    max_size_gb: float | None,
    now: datetime,
) -> list[CleanupEntry]:
    marked: dict[Path, set[str]] = {}

    if max_age_days is not None:
        cutoff_ts = now.timestamp() - (max_age_days * 86400)
        for file_entry in files:
            if file_entry.modified_at_ts <= cutoff_ts:
                marked.setdefault(file_entry.path, set()).add(AGE_REASON)

    remaining = [entry for entry in files if entry.path not in marked]
    if max_size_gb is not None:
        max_size_bytes = int(max_size_gb * (1024**3))
        remaining_total = sum(item.size_bytes for item in remaining)

        if remaining_total > max_size_bytes:
            for file_entry in sorted(remaining, key=lambda item: item.modified_at_ts):
                marked.setdefault(file_entry.path, set()).add(SIZE_REASON)
                remaining_total -= file_entry.size_bytes
                if remaining_total <= max_size_bytes:
                    break

    by_path = {entry.path: entry for entry in files}
    targets: list[CleanupEntry] = []
    for path, reason_set in marked.items():
        source = by_path[path]
        targets.append(
            CleanupEntry(
                path=path,
                size_bytes=source.size_bytes,
                modified_at=datetime.fromtimestamp(source.modified_at_ts, tz=timezone.utc),
                reasons=tuple(sorted(reason_set)),
            )
        )

    targets.sort(key=lambda item: (item.modified_at, str(item.path)))
    return targets


def _remove_empty_dirs(root: Path) -> None:
    if not root.exists():
        return

    root_resolved = _resolve_root(root)
    directories = sorted(
        [path for path in root.rglob("*") if path.is_dir()],
        key=lambda item: len(item.parts),
        reverse=True,
    )
    for directory in directories:
        if not _is_within_root(directory, root_resolved):
            continue
        try:
            directory.rmdir()
        except OSError:
            continue


def cleanup_output_root(
    root: Path,
    *,
    max_age_days: float | None,
    max_size_gb: float | None,
    dry_run: bool,
    now: datetime | None = None,
) -> CleanupReport:
    """Apply retention cleanup to publisher outputs.

    Deletes files by age first, then enforces max-size by removing oldest remaining files.
    """
    if max_age_days is not None and max_age_days <= 0:
        raise ValueError("max_age_days must be greater than 0")
    if max_size_gb is not None and max_size_gb <= 0:
        raise ValueError("max_size_gb must be greater than 0")

    root_resolved = _resolve_root(root)
    files = _iter_regular_files(root_resolved)
    timestamp = now if now is not None else datetime.now(tz=timezone.utc)

    targets = _collect_cleanup_targets(
        files,
        max_age_days=max_age_days,
        max_size_gb=max_size_gb,
        now=timestamp,
    )

    deleted_files = 0
    deleted_bytes = 0
    if not dry_run:
        for entry in targets:
            if not _is_within_root(entry.path, root_resolved):
                continue
            try:
                entry.path.unlink(missing_ok=True)
            except OSError:
                continue
            deleted_files += 1
            deleted_bytes += entry.size_bytes
        _remove_empty_dirs(root_resolved)

    return CleanupReport(
        root=root_resolved,
        dry_run=dry_run,
        scanned_files=len(files),
        scanned_bytes=sum(item.size_bytes for item in files),
        deleted_files=deleted_files if not dry_run else len(targets),
        deleted_bytes=deleted_bytes if not dry_run else sum(item.size_bytes for item in targets),
        max_age_days=max_age_days,
        max_size_gb=max_size_gb,
        entries=tuple(targets),
    )


def _format_entry(entry: CleanupEntry, root: Path) -> str:
    try:
        rel_path = entry.path.relative_to(root)
    except ValueError:
        rel_path = entry.path
    reasons = ", ".join(entry.reasons)
    return f"- {rel_path} ({entry.size_bytes} bytes, reasons: {reasons})"


def format_cleanup_report(report: CleanupReport, *, sample_limit: int = 10) -> str:
    mode = "DRY-RUN" if report.dry_run else "APPLIED"
    lines = [
        f"[cleanup:{mode}] root={report.root}",
        (
            "policy="
            f"max-age-days={report.max_age_days if report.max_age_days is not None else 'off'}, "
            f"max-size-gb={report.max_size_gb if report.max_size_gb is not None else 'off'}"
        ),
        (
            "scan="
            f"{report.scanned_files} files / {report.scanned_bytes} bytes, "
            f"targets={report.deleted_files} files / {report.deleted_bytes} bytes"
        ),
    ]

    if report.entries:
        lines.append("targets(sample):")
        for entry in report.entries[:sample_limit]:
            lines.append(_format_entry(entry, report.root))
        remaining = len(report.entries) - sample_limit
        if remaining > 0:
            lines.append(f"- ... and {remaining} more")
    else:
        lines.append("targets(sample): none")

    return "\n".join(lines)
