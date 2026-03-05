from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
STREAMLIT_TARGETS = [
    "scripts/web_streamlit_app.py",
    "tests/test_web_streamlit_upload_security.py",
]


def _require_tool(tool_name: str) -> str:
    tool_path = shutil.which(tool_name)
    if tool_path is None:
        pytest.skip(f"{tool_name} is not installed in this environment")
    return tool_path


def _run_tool(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_streamlit_script_has_no_import_untyped_ignore() -> None:
    marker = "type: ignore[import-untyped]"
    script_path = REPO_ROOT / "scripts" / "web_streamlit_app.py"
    offending_lines = [
        line_number
        for line_number, line in enumerate(script_path.read_text(encoding="utf-8").splitlines(), 1)
        if marker in line
    ]

    assert not offending_lines, (
        "Remove stale type: ignore[import-untyped] comments in web_streamlit_app.py: "
        f"{offending_lines}"
    )


def test_streamlit_upload_ruff_format_gate_passes() -> None:
    ruff = _require_tool("ruff")
    result = _run_tool([ruff, "format", "--check", *STREAMLIT_TARGETS])

    assert result.returncode == 0, (
        "Streamlit upload ruff format gate failed.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_streamlit_upload_ruff_check_gate_passes() -> None:
    ruff = _require_tool("ruff")
    result = _run_tool([ruff, "check", *STREAMLIT_TARGETS])

    assert result.returncode == 0, (
        "Streamlit upload ruff check gate failed.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_streamlit_upload_mypy_gate_passes() -> None:
    mypy = _require_tool("mypy")
    result = _run_tool([mypy, "scripts/web_streamlit_app.py"])

    assert result.returncode == 0, (
        f"Streamlit upload mypy gate failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_streamlit_upload_pytest_gate_passes() -> None:
    result = _run_tool(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_web_streamlit_upload_security.py",
        ]
    )

    assert result.returncode == 0, (
        f"Streamlit upload pytest gate failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
