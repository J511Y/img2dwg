"""Regression smoke test for the PR #52 publisher mypy gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_publisher_mypy_gate_smoke() -> None:
    """Ensure project mypy config keeps publisher scripts type-checkable."""
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        "-m",
        "mypy",
        "scripts/web_gradio.py",
        "scripts/web_streamlit.py",
        "scripts/web_streamlit_app.py",
    ]

    result = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
