"""Regression guard for reviewer format failures on issue #21 chain."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_upload_targets_are_ruff_format_clean() -> None:
    """Keep #21 base security targets format-clean for reviewer cycles."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--check",
            "scripts/web_streamlit_app.py",
            "tests/test_web_streamlit_upload_security.py",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, (
        "ruff format gate failed for #21 upload security targets\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
