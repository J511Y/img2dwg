"""Upload-path security helpers for publisher entrypoints."""

from __future__ import annotations

from pathlib import Path

ALLOWED_UPLOAD_SUFFIXES = {".jpg", ".jpeg", ".png"}
MAX_UPLOAD_BASENAME_LENGTH = 120
WINDOWS_RESERVED_BASENAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def assert_path_within_output_root(
    target_path: Path, output_root: Path, error_message: str
) -> None:
    resolved_root = output_root.resolve()
    resolved_target = target_path.resolve()
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(error_message) from exc


def sanitize_upload_filename(filename: str) -> str:
    raw = filename.strip().replace("\x00", "")
    if not raw:
        raise ValueError("업로드 파일명이 비어 있습니다.")

    normalized = raw.replace("\\", "/")

    if normalized.startswith("/"):
        raise ValueError("절대 경로 업로드 파일명은 허용되지 않습니다.")

    tokens = [token for token in normalized.split("/") if token]
    if len(tokens) != 1:
        raise ValueError("경로 구분자가 포함된 업로드 파일명은 허용되지 않습니다.")

    safe_name = Path(tokens[0]).name.strip()
    if safe_name in {"", ".", ".."} or ".." in safe_name:
        raise ValueError("상대 경로 토큰('..')이 포함된 파일명은 허용되지 않습니다.")

    if len(safe_name) > MAX_UPLOAD_BASENAME_LENGTH:
        raise ValueError(
            f"업로드 파일명 길이는 {MAX_UPLOAD_BASENAME_LENGTH}자를 초과할 수 없습니다."
        )

    if any(char in safe_name for char in {":", "*", "?", '"', "<", ">", "|"}):
        raise ValueError("업로드 파일명에 허용되지 않은 특수문자가 포함되어 있습니다.")

    stem = Path(safe_name).stem.rstrip(" .").lower()
    if stem in WINDOWS_RESERVED_BASENAMES:
        raise ValueError("운영체제 예약 이름은 업로드 파일명으로 사용할 수 없습니다.")

    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise ValueError("허용되지 않은 파일 확장자입니다. (.jpg/.jpeg/.png만 허용)")

    return safe_name
