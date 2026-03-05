from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePath
from typing import Any
from urllib.request import urlopen

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_DXF_EXTENSIONS = {".dxf"}
SAFE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
REQUIRED_COLUMNS = {
    "case_id",
    "image_filename",
    "image_url",
    "image_sha256",
    "dxf_candidate_filename",
    "dxf_candidate_url",
    "dxf_candidate_sha256",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download benchmark image/DXF candidates from a web manifest into a fixed output root"
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="CSV manifest path",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="directory to store downloaded benchmark assets",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout seconds (default: 30)",
    )
    return parser.parse_args()


def _is_hex_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", value.lower()))


def _validate_safe_token(value: str, *, field: str) -> str:
    token = value.strip()
    if not token:
        raise ValueError(f"{field} must not be empty")

    token_path = PurePath(token)
    if token_path.name != token:
        raise ValueError(f"{field} must be a plain file/token name: {value!r}")

    if token in {".", ".."} or ".." in token:
        raise ValueError(f"{field} must not contain parent path segments: {value!r}")

    if "/" in token or "\\" in token:
        raise ValueError(f"{field} must not contain path separators: {value!r}")

    if not SAFE_TOKEN_PATTERN.fullmatch(token):
        raise ValueError(
            f"{field} contains unsupported characters; allowed: letters, numbers, dot, dash, underscore"
        )

    return token


def _validate_filename(value: str, *, field: str, allowed_extensions: set[str]) -> str:
    filename = _validate_safe_token(value, field=field)
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ValueError(f"{field} must use one of extensions: {allowed}")
    return filename


def _safe_target_path(base_dir: Path, filename: str) -> Path:
    base_resolved = base_dir.resolve()
    target = (base_dir / filename).resolve()
    try:
        target.relative_to(base_resolved)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"resolved target escaped output directory: {target}") from exc
    return target


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, target: Path, *, timeout: float) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=timeout) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)


def _validate_row(row: Mapping[str, str]) -> dict[str, str]:
    missing = [name for name in REQUIRED_COLUMNS if not str(row.get(name, "")).strip()]
    if missing:
        raise ValueError(f"manifest row missing required fields: {', '.join(sorted(missing))}")

    case_id = _validate_safe_token(str(row["case_id"]), field="case_id")
    image_filename = _validate_filename(
        str(row["image_filename"]),
        field="image_filename",
        allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
    )
    dxf_filename = _validate_filename(
        str(row["dxf_candidate_filename"]),
        field="dxf_candidate_filename",
        allowed_extensions=ALLOWED_DXF_EXTENSIONS,
    )

    image_sha256 = str(row["image_sha256"]).strip().lower()
    dxf_sha256 = str(row["dxf_candidate_sha256"]).strip().lower()
    if not _is_hex_sha256(image_sha256):
        raise ValueError("image_sha256 must be a 64-char hex string")
    if not _is_hex_sha256(dxf_sha256):
        raise ValueError("dxf_candidate_sha256 must be a 64-char hex string")

    image_url = str(row["image_url"]).strip()
    dxf_url = str(row["dxf_candidate_url"]).strip()
    if not image_url or not dxf_url:
        raise ValueError("image_url and dxf_candidate_url must not be empty")

    return {
        "case_id": case_id,
        "image_filename": image_filename,
        "image_url": image_url,
        "image_sha256": image_sha256,
        "dxf_candidate_filename": dxf_filename,
        "dxf_candidate_url": dxf_url,
        "dxf_candidate_sha256": dxf_sha256,
    }


def _iter_manifest_rows(manifest_path: Path) -> Iterable[dict[str, str]]:
    if not manifest_path.exists() or not manifest_path.is_file():
        raise ValueError(f"manifest path does not exist: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"manifest is missing a CSV header: {manifest_path}")
        for row in reader:
            if row is None:
                continue
            normalized = {key: (value or "") for key, value in row.items()}
            if not any(value.strip() for value in normalized.values()):
                continue
            yield _validate_row(normalized)


def download_assets(
    manifest_path: Path,
    output_dir: Path,
    *,
    timeout: float = 30.0,
) -> list[dict[str, Any]]:
    rows = list(_iter_manifest_rows(manifest_path))
    images_dir = output_dir / "images"
    dxf_dir = output_dir / "dxf_candidates"
    images_dir.mkdir(parents=True, exist_ok=True)
    dxf_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[dict[str, Any]] = []

    for row in rows:
        image_target_name = f"{row['case_id']}__{row['image_filename']}"
        dxf_target_name = f"{row['case_id']}__{row['dxf_candidate_filename']}"

        image_target = _safe_target_path(images_dir, image_target_name)
        dxf_target = _safe_target_path(dxf_dir, dxf_target_name)

        _download(row["image_url"], image_target, timeout=timeout)
        _download(row["dxf_candidate_url"], dxf_target, timeout=timeout)

        image_hash = _sha256_file(image_target)
        dxf_hash = _sha256_file(dxf_target)

        if image_hash != row["image_sha256"]:
            image_target.unlink(missing_ok=True)
            raise ValueError(
                f"image sha256 mismatch for case_id={row['case_id']}: "
                f"expected {row['image_sha256']}, got {image_hash}"
            )

        if dxf_hash != row["dxf_candidate_sha256"]:
            dxf_target.unlink(missing_ok=True)
            raise ValueError(
                f"dxf sha256 mismatch for case_id={row['case_id']}: "
                f"expected {row['dxf_candidate_sha256']}, got {dxf_hash}"
            )

        downloaded.append(
            {
                "case_id": row["case_id"],
                "image_path": image_target,
                "dxf_candidate_path": dxf_target,
                "image_sha256": image_hash,
                "dxf_candidate_sha256": dxf_hash,
            }
        )

    return downloaded


def main() -> None:
    args = parse_args()
    rows = download_assets(args.manifest, args.output_dir, timeout=args.timeout)
    print(f"downloaded {len(rows)} benchmark case(s) into {args.output_dir}")


if __name__ == "__main__":
    main()
