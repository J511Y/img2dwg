from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


@pytest.fixture(scope="module")
def module() -> ModuleType:
    path = Path(__file__).resolve().parent.parent / "scripts" / "web_streamlit_app.py"
    spec = importlib.util.spec_from_file_location("web_streamlit_app_upload_security", path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


@pytest.mark.parametrize(
    "filename",
    [
        "a/../../evil.png",
        "..\\evil.png",
        "../evil.jpg",
        "/tmp/evil.png",
        "C:\\temp\\evil.png",
        "evil.gif",
        "evil",
        "",
        "con.png",
        "evil?.png",
        f"{'a' * 121}.png",
    ],
)
def test_sanitize_upload_filename_rejects_malicious_inputs(module: ModuleType, filename: str) -> None:
    with pytest.raises(ValueError):
        module.sanitize_upload_filename(filename)


def test_sanitize_upload_filename_accepts_valid_name(module: ModuleType) -> None:
    assert module.sanitize_upload_filename("FloorPlan.PNG") == "FloorPlan.PNG"


def test_build_safe_upload_path_rejects_output_root_escape_via_symlink(
    module: ModuleType,
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output-root"
    output_root.mkdir(parents=True, exist_ok=True)

    outside = tmp_path / "outside"
    outside.mkdir(parents=True, exist_ok=True)

    upload_dir = output_root / "_uploads" / "20260305"
    upload_dir.parent.mkdir(parents=True, exist_ok=True)
    upload_dir.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError):
        module.build_safe_upload_path(upload_dir, output_root, "ok.png")


def test_build_safe_upload_path_returns_internal_path(module: ModuleType, tmp_path: Path) -> None:
    output_root = tmp_path / "output-root"
    upload_dir = output_root / "_uploads" / "20260305"
    upload_dir.mkdir(parents=True, exist_ok=True)

    path = module.build_safe_upload_path(upload_dir, output_root, "ok.png")

    assert path.parent == upload_dir
    assert path.name.endswith("-ok.png")
    assert path.resolve().is_relative_to(output_root.resolve())


def test_validate_upload_payload_rejects_empty_and_oversized(module: ModuleType) -> None:
    with pytest.raises(ValueError):
        module.validate_upload_payload(b"")

    with pytest.raises(ValueError):
        module.validate_upload_payload(b"x" * (module.MAX_UPLOAD_BYTES + 1))


def test_write_upload_payload_writes_once_and_rejects_overwrite(
    module: ModuleType,
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output-root"
    upload_dir = output_root / "_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    upload_path = upload_dir / "sample.png"
    module.write_upload_payload(upload_path, output_root, b"png-bytes")

    assert upload_path.read_bytes() == b"png-bytes"

    with pytest.raises(ValueError):
        module.write_upload_payload(upload_path, output_root, b"second")
