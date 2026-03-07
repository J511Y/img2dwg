"""Download floorplan regression assets from a manifest with integrity checks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]

DEFAULT_USER_AGENT = "img2dwg-floorplan-regression-fetcher/1.0"

REQUIRED_COLUMNS = {
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
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_filename(value: str, field: str) -> str:
    if not value or value.strip() != value:
        raise ValueError(f"{field} must be non-empty and trimmed")
    if "/" in value or "\\" in value or ".." in value:
        raise ValueError(f"{field} must not include path traversal tokens")
    if value.startswith("."):
        raise ValueError(f"{field} must not start with dot")
    suffix = Path(value).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        raise ValueError(f"{field} must end with one of {sorted(IMAGE_EXTENSIONS)}")
    return value


def _validate_https_url(url: str, field: str) -> str:
    if not url or url.strip() != url:
        raise ValueError(f"{field} must be non-empty and trimmed")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{field} must be a valid https URL")
    return url


def _validate_sha256(value: str, field: str) -> str:
    normalized = value.strip().lower()
    if not HEX64_RE.fullmatch(normalized):
        raise ValueError(f"{field} must be a 64-char lowercase hex SHA256 digest")
    return normalized


def _safe_output_path(output_dir: Path, bucket: str, filename: str) -> Path:
    bucket_dir = (output_dir / bucket).resolve()
    bucket_dir.mkdir(parents=True, exist_ok=True)
    candidate = (bucket_dir / filename).resolve()
    try:
        candidate.relative_to(bucket_dir)
    except ValueError as exc:
        raise ValueError("resolved output path escaped output root") from exc
    return candidate


def _read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
            raise ValueError("manifest missing required columns")
        rows = [dict(row) for row in reader]

    if not rows:
        raise ValueError("manifest is empty")
    return rows


def _download(
    url: str,
    *,
    user_agent: str,
    max_retries: int = 4,
    base_delay_seconds: float = 1.5,
) -> bytes:
    if max_retries < 1:
        raise ValueError("max_retries must be >= 1")

    for attempt in range(max_retries):
        resp = requests.get(url, timeout=60, headers={"User-Agent": user_agent})

        retryable_status = resp.status_code in {429, 500, 502, 503, 504}
        if retryable_status and attempt < max_retries - 1:
            delay = base_delay_seconds * (2**attempt)
            time.sleep(delay)
            continue

        resp.raise_for_status()
        return bytes(resp.content)

    raise RuntimeError("unreachable: download retry loop exhausted")


def sync_manifest(
    manifest: Path,
    output_dir: Path,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
) -> list[Path]:
    rows = _read_manifest(manifest)
    image_paths: list[Path] = []

    for row in rows:
        case_id = str(row["case_id"])
        image_name = _validate_filename(row["image_filename"], "image_filename")
        image_url = _validate_https_url(row["image_url"], "image_url")
        image_sha = _validate_sha256(row["image_sha256"], "image_sha256")

        _validate_https_url(row["source_page_url"], "source_page_url")
        _validate_https_url(row["license_proof_url"], "license_proof_url")
        if not row["license_name"].strip():
            raise ValueError(f"license_name must be non-empty for case_id={case_id}")
        if not row["license_spdx"].strip():
            raise ValueError(f"license_spdx must be non-empty for case_id={case_id}")
        if not row["retrieved_at"].strip():
            raise ValueError(f"retrieved_at must be non-empty for case_id={case_id}")

        image_bytes = _download(image_url, user_agent=user_agent)
        if _sha256_hex(image_bytes) != image_sha:
            raise ValueError(f"image_sha256 mismatch for case_id={case_id}")

        image_path = _safe_output_path(output_dir, "images", image_name)
        image_path.write_bytes(image_bytes)
        image_paths.append(image_path)

    return sorted(image_paths)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download floorplan regression assets from manifest safely"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--user-agent", type=str, default=DEFAULT_USER_AGENT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image_paths = sync_manifest(args.manifest, args.output_dir, user_agent=args.user_agent)
    print(f"synced images={len(image_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
