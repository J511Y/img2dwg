from __future__ import annotations

# mypy: disable-error-code=import-untyped
from pathlib import Path

import pytest

from img2dwg.utils.upload_security import assert_path_within_output_root, sanitize_upload_filename


@pytest.mark.parametrize(
    "name",
    [
        "a.jpg",
        "sample.jpeg",
        "floorplan.png",
    ],
)
def test_sanitize_upload_filename_accepts_safe_inputs(name: str) -> None:
    assert sanitize_upload_filename(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "../evil.jpg",
        "a/b.jpg",
        "C:\\abs\\x.jpg",
        "/abs/x.jpg",
        "..",
        "",
        "nul.jpg",
        "bad.gif",
        ".hidden.jpg",
        "bad\x1fname.png",
        "bad\x7fname.png",
    ],
)
def test_sanitize_upload_filename_blocks_unsafe_inputs(name: str) -> None:
    with pytest.raises(ValueError):
        sanitize_upload_filename(name)


def test_assert_path_within_output_root_accepts_nested_path(tmp_path: Path) -> None:
    root = tmp_path / "out"
    root.mkdir(parents=True)
    target = root / "nested" / "a.jpg"
    target.parent.mkdir(parents=True)
    target.touch()

    assert_path_within_output_root(target, root, "escaped")


def test_assert_path_within_output_root_rejects_escape(tmp_path: Path) -> None:
    root = tmp_path / "out"
    root.mkdir(parents=True)
    outside = tmp_path / "outside.jpg"
    outside.touch()

    with pytest.raises(ValueError, match="escaped"):
        assert_path_within_output_root(outside, root, "escaped")
