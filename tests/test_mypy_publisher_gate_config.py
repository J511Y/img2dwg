"""Regression guards for publisher mypy gate configuration."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_mypy_path_includes_src_root() -> None:
    """Ensure reviewer gate command resolves local imports without env hacks."""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")

    assert "[tool.mypy]" in content
    assert 'mypy_path = "src"' in content


def test_publisher_scripts_do_not_use_import_untyped_ignores() -> None:
    """Avoid env-dependent mypy behavior from stale import-untyped suppressions."""
    scripts = [
        PROJECT_ROOT / "scripts" / "web_gradio.py",
        PROJECT_ROOT / "scripts" / "web_streamlit.py",
        PROJECT_ROOT / "scripts" / "web_streamlit_app.py",
    ]

    for script in scripts:
        content = script.read_text(encoding="utf-8")
        assert "# type: ignore[import-untyped]" not in content
        assert "disable-error-code=import-untyped" not in content
