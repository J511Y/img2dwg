from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLISHER_SCRIPT_TARGETS = [
    "scripts/web_gradio.py",
    "scripts/web_streamlit.py",
    "scripts/web_streamlit_app.py",
]
PUBLISHER_MYPY_TARGETS = [
    "scripts/smoke_web_publishers.py",
    *PUBLISHER_SCRIPT_TARGETS,
    "src/img2dwg/web/__init__.py",
    "src/img2dwg/web/retention.py",
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


def test_publisher_scripts_do_not_use_import_untyped_ignore() -> None:
    marker = "type: ignore[import-untyped]"
    offenders: dict[str, list[int]] = {}

    for relative_path in PUBLISHER_SCRIPT_TARGETS:
        file_path = REPO_ROOT / relative_path
        line_numbers = [
            line_number
            for line_number, line in enumerate(
                file_path.read_text(encoding="utf-8").splitlines(), 1
            )
            if marker in line
        ]
        if line_numbers:
            offenders[relative_path] = line_numbers

    assert not offenders, f"Remove stale import-untyped ignores in publisher scripts: {offenders}"


def test_publisher_ruff_format_gate_passes() -> None:
    ruff = _require_tool("ruff")

    result = _run_tool([ruff, "format", "--check", *PUBLISHER_SCRIPT_TARGETS])

    assert result.returncode == 0, (
        f"Publisher ruff format gate failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_publisher_mypy_gate_passes() -> None:
    mypy = _require_tool("mypy")

    result = _run_tool([mypy, *PUBLISHER_MYPY_TARGETS])

    assert result.returncode == 0, (
        f"Publisher mypy gate failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
