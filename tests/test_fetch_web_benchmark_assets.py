from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from urllib.parse import quote

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "fetch_web_benchmark_assets.py"


def _load_script_module() -> ModuleType:
    module_name = "fetch_web_benchmark_assets_script_for_tests"
    if module_name in sys.modules:
        loaded = sys.modules[module_name]
        return loaded

    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load fetch_web_benchmark_assets.py module spec")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[module_name] = module
    return module


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_url(path: Path) -> str:
    return f"file://{quote(str(path))}"


def test_validate_row_rejects_case_id_path_traversal() -> None:
    module = _load_script_module()

    with pytest.raises(ValueError, match="case_id"):
        module._validate_row(  # noqa: SLF001
            {
                "case_id": "../../escape",
                "image_filename": "a.png",
                "image_url": "https://example.com/a.png",
                "image_sha256": "0" * 64,
                "dxf_candidate_filename": "a.dxf",
                "dxf_candidate_url": "https://example.com/a.dxf",
                "dxf_candidate_sha256": "0" * 64,
            }
        )


def test_validate_row_rejects_filename_path_traversal() -> None:
    module = _load_script_module()

    with pytest.raises(ValueError, match="image_filename"):
        module._validate_row(  # noqa: SLF001
            {
                "case_id": "safe_case",
                "image_filename": "../escape.png",
                "image_url": "https://example.com/a.png",
                "image_sha256": "0" * 64,
                "dxf_candidate_filename": "a.dxf",
                "dxf_candidate_url": "https://example.com/a.dxf",
                "dxf_candidate_sha256": "0" * 64,
            }
        )

    with pytest.raises(ValueError, match="dxf_candidate_filename"):
        module._validate_row(  # noqa: SLF001
            {
                "case_id": "safe_case",
                "image_filename": "safe.png",
                "image_url": "https://example.com/a.png",
                "image_sha256": "0" * 64,
                "dxf_candidate_filename": "..\\escape.dxf",
                "dxf_candidate_url": "https://example.com/a.dxf",
                "dxf_candidate_sha256": "0" * 64,
            }
        )


def test_download_assets_rejects_manifest_with_traversal_values(tmp_path: Path) -> None:
    module = _load_script_module()

    manifest_path = tmp_path / "manifest.csv"
    manifest_path.write_text(
        "\n".join(
            [
                (
                    "case_id,image_filename,image_url,image_sha256,dxf_candidate_filename,"
                    "dxf_candidate_url,dxf_candidate_sha256"
                ),
                (
                    "../../escape,a.png,https://example.com/a.png," + "0" * 64 + ","
                    "a.dxf,https://example.com/a.dxf," + "0" * 64
                ),
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="case_id"):
        module.download_assets(manifest_path, tmp_path / "out")


def test_download_assets_stores_files_only_under_output_root(tmp_path: Path) -> None:
    module = _load_script_module()

    image_bytes = b"png-bytes"
    dxf_bytes = b"0\nSECTION\n2\nEOF\n"
    image_source = tmp_path / "sample.png"
    dxf_source = tmp_path / "sample.dxf"
    image_source.write_bytes(image_bytes)
    dxf_source.write_bytes(dxf_bytes)

    manifest_path = tmp_path / "manifest.csv"
    manifest_path.write_text(
        "\n".join(
            [
                (
                    "case_id,image_filename,image_url,image_sha256,dxf_candidate_filename,"
                    "dxf_candidate_url,dxf_candidate_sha256"
                ),
                (
                    "safe_case,sample.png,"
                    f"{_file_url(image_source)},"
                    f"{_sha256_bytes(image_bytes)},"
                    "sample.dxf,"
                    f"{_file_url(dxf_source)},"
                    f"{_sha256_bytes(dxf_bytes)}"
                ),
            ]
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "downloaded"
    rows = module.download_assets(manifest_path, output_dir)

    assert len(rows) == 1
    image_target = output_dir / "images" / "safe_case__sample.png"
    dxf_target = output_dir / "dxf_candidates" / "safe_case__sample.dxf"

    assert image_target.exists()
    assert dxf_target.exists()
    assert image_target.read_bytes() == image_bytes
    assert dxf_target.read_bytes() == dxf_bytes

    # Ensure path containment invariant (never escapes output root).
    assert image_target.resolve().is_relative_to(output_dir.resolve())
    assert dxf_target.resolve().is_relative_to(output_dir.resolve())
