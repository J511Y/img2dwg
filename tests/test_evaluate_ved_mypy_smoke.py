"""Regression smoke test for PR #47 mypy gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_evaluate_ved_script_passes_mypy_gate() -> None:
    """Keep evaluate_ved.py aligned with reviewer mypy invocation."""
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "scripts/evaluate_ved.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
