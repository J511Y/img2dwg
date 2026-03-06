"""Download web benchmark assets with path-traversal guards."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]

REQUIRED_COLUMNS = {
    "case_id",
    "image_filename",
    "image_url",
    "image_sha256",
    "dxf_candidate_filename",
    "dxf_candidate_url",
    "dxf_candidate_sha256",
}


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_filename(value: str, field: str) -> str:
    if not value or value.strip() != value:
        raise ValueError(f"{field} must be non-empty and trimmed")
    if "/" in value or "\\" in value or ".." in value:
        raise ValueError(f"{field} must not include path traversal tokens")
    if value.startswith("."):
        raise ValueError(f"{field} must not start with dot")
    return value


def _validate_https_url(url: str, field: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{field} must be a valid https URL")
    return url


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


def _download(url: str) -> bytes:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return bytes(resp.content)


def sync_manifest(manifest: Path, output_dir: Path) -> tuple[int, int]:
    rows = _read_manifest(manifest)
    image_count = 0
    dxf_count = 0

    for row in rows:
        image_name = _validate_filename(row["image_filename"], "image_filename")
        image_url = _validate_https_url(row["image_url"], "image_url")
        image_sha = row["image_sha256"].strip().lower()

        dxf_name = _validate_filename(row["dxf_candidate_filename"], "dxf_candidate_filename")
        dxf_url = _validate_https_url(row["dxf_candidate_url"], "dxf_candidate_url")
        dxf_sha = row["dxf_candidate_sha256"].strip().lower()

        image_bytes = _download(image_url)
        if _sha256_hex(image_bytes) != image_sha:
            raise ValueError(f"image_sha256 mismatch for case_id={row['case_id']}")
        image_path = _safe_output_path(output_dir, "images", image_name)
        image_path.write_bytes(image_bytes)
        image_count += 1

        dxf_bytes = _download(dxf_url)
        if _sha256_hex(dxf_bytes) != dxf_sha:
            raise ValueError(f"dxf_candidate_sha256 mismatch for case_id={row['case_id']}")
        dxf_path = _safe_output_path(output_dir, "dxf_candidates", dxf_name)
        dxf_path.write_bytes(dxf_bytes)
        dxf_count += 1

    return image_count, dxf_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download benchmark assets from manifest safely")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    images, dxfs = sync_manifest(args.manifest, args.output_dir)
    print(f"synced images={images} dxf_candidates={dxfs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
