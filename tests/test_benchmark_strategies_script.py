from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "benchmark_strategies.py"


def _load_script_module() -> ModuleType:
    module_name = "benchmark_strategies_script_for_tests"
    if module_name in sys.modules:
        loaded = sys.modules[module_name]
        return loaded

    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load benchmark_strategies.py module spec")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[module_name] = module
    return module


def _ensure_dir_symlink(link_path: Path, target_path: Path) -> None:
    try:
        link_path.symlink_to(target_path, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:  # pragma: no cover - platform dependent
        pytest.skip(f"symlink creation is not supported in this environment: {exc}")


def test_collect_image_paths_recursive_skips_symlink_by_default(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()

    images_root = tmp_path / "images"
    images_root.mkdir()
    (images_root / "local.png").write_bytes(b"img")

    external_dir = tmp_path / "external"
    external_dir.mkdir()
    (external_dir / "linked.png").write_bytes(b"img")

    _ensure_dir_symlink(images_root / "linked_dir", external_dir)

    image_paths = module.collect_image_paths(
        images_root,
        recursive=True,
        follow_symlinks=False,
        max_images=10,
    )

    assert [path.name for path in image_paths] == ["local.png"]
    captured = capsys.readouterr()
    assert "skipped 1 symlink path(s)" in captured.err


def test_collect_image_paths_recursive_can_follow_symlink_dirs(tmp_path: Path) -> None:
    module = _load_script_module()

    images_root = tmp_path / "images"
    images_root.mkdir()
    (images_root / "local.png").write_bytes(b"img")

    external_dir = tmp_path / "external"
    external_dir.mkdir()
    (external_dir / "linked.png").write_bytes(b"img")

    _ensure_dir_symlink(images_root / "linked_dir", external_dir)

    image_paths = module.collect_image_paths(
        images_root,
        recursive=True,
        follow_symlinks=True,
        max_images=10,
    )

    assert sorted(path.name for path in image_paths) == ["linked.png", "local.png"]


def test_collect_image_paths_recursive_raises_when_scan_limit_exceeded(tmp_path: Path) -> None:
    module = _load_script_module()

    images_root = tmp_path / "images"
    images_root.mkdir()
    for idx in range(3):
        (images_root / f"sample-{idx}.png").write_bytes(b"img")

    with pytest.raises(ValueError, match="recursive scan limit exceeded"):
        module.collect_image_paths(
            images_root,
            recursive=True,
            follow_symlinks=False,
            max_images=2,
        )


def test_collect_image_paths_recursive_rejects_invalid_scan_limit(tmp_path: Path) -> None:
    module = _load_script_module()

    images_root = tmp_path / "images"
    images_root.mkdir()
    (images_root / "sample.png").write_bytes(b"img")

    with pytest.raises(ValueError, match="--max-images must be >= 1"):
        module.collect_image_paths(
            images_root,
            recursive=True,
            follow_symlinks=False,
            max_images=0,
        )


def test_build_metadata_key_candidates_includes_root_relative_key(tmp_path: Path) -> None:
    module = _load_script_module()

    images_root = tmp_path / "images"
    nested = images_root / "nested"
    nested.mkdir(parents=True)
    image_path = (nested / "a.png").resolve()
    image_path.write_bytes(b"img")

    key_candidates = module.build_metadata_key_candidates([image_path], images_root)

    assert image_path in key_candidates
    assert ("root_relative", "nested/a.png") in key_candidates[image_path]


def test_load_metadata_manifest_rejects_non_object_values(tmp_path: Path) -> None:
    module = _load_script_module()

    manifest_path = tmp_path / "metadata.json"
    manifest_path.write_text('{"a.png": 1}', encoding="utf-8")

    with pytest.raises(ValueError, match="must be an object"):
        module.load_metadata_manifest(manifest_path)
