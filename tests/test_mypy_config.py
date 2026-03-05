"""Regression tests for static typing gate configuration."""

from __future__ import annotations

from pathlib import Path


def test_mypy_path_includes_src_root() -> None:
    """Ensure mypy resolves local package imports without MYPYPATH env hacks."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")

    assert "[tool.mypy]" in content
    assert 'mypy_path = "src"' in content
