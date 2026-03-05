"""Run Gradio + Streamlit publisher smoke checks in one command."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
gradio_script_path = project_root / "scripts" / "web_gradio.py"
streamlit_script_path = project_root / "scripts" / "web_streamlit.py"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run smoke tests for all web publishers")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Acknowledge non-loopback host binding for both publisher smoke checks",
    )
    parser.add_argument("--gradio-port", type=int, default=7861, help="Smoke port for Gradio")
    parser.add_argument("--streamlit-port", type=int, default=8502, help="Smoke port for Streamlit")
    parser.add_argument(
        "--smoke-wait-seconds",
        type=float,
        default=0.5,
        help="Seconds to keep each server alive after readiness check",
    )
    parser.add_argument(
        "--gradio-timeout-seconds",
        type=float,
        default=20.0,
        help="Max readiness wait for Gradio",
    )
    parser.add_argument(
        "--streamlit-timeout-seconds",
        type=float,
        default=25.0,
        help="Max readiness wait for Streamlit",
    )
    parser.add_argument(
        "--streamlit-smoke-log-lines",
        type=int,
        default=80,
        help="Tail line count for Streamlit failure logs",
    )
    parser.add_argument(
        "--streamlit-smoke-keep-log",
        action="store_true",
        help="Keep Streamlit temporary log file even on success",
    )
    parser.add_argument(
        "--cleanup-dry-run",
        action="store_true",
        help="Pass through cleanup dry-run to both publishers",
    )
    return parser.parse_args(argv)


def build_gradio_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(gradio_script_path),
        "--host",
        args.host,
        "--port",
        str(args.gradio_port),
        "--smoke-test",
        "--smoke-wait-seconds",
        str(args.smoke_wait_seconds),
        "--smoke-timeout-seconds",
        str(args.gradio_timeout_seconds),
    ]
    if args.allow_remote:
        command.append("--allow-remote")
    if args.cleanup_dry_run:
        command.append("--cleanup-dry-run")
    return command


def build_streamlit_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(streamlit_script_path),
        "--host",
        args.host,
        "--port",
        str(args.streamlit_port),
        "--smoke-test",
        "--smoke-wait-seconds",
        str(args.smoke_wait_seconds),
        "--smoke-timeout-seconds",
        str(args.streamlit_timeout_seconds),
        "--smoke-log-lines",
        str(args.streamlit_smoke_log_lines),
    ]
    if args.streamlit_smoke_keep_log:
        command.append("--smoke-keep-log")
    if args.allow_remote:
        command.append("--allow-remote")
    if args.cleanup_dry_run:
        command.append("--cleanup-dry-run")
    return command


def run_step(label: str, command: list[str]) -> None:
    print(f"[{label}] $ {' '.join(shlex.quote(item) for item in command)}")
    start = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=str(project_root),
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed = time.perf_counter() - start

    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)

    if completed.returncode != 0:
        raise RuntimeError(
            f"{label} smoke failed (exit={completed.returncode}, elapsed={elapsed:.2f}s)."
        )

    print(f"[{label}] PASS ({elapsed:.2f}s)")


def main() -> None:
    if not gradio_script_path.exists():
        raise FileNotFoundError(f"Missing Gradio script: {gradio_script_path}")
    if not streamlit_script_path.exists():
        raise FileNotFoundError(f"Missing Streamlit script: {streamlit_script_path}")

    args = parse_args()
    run_step("gradio", build_gradio_command(args))
    run_step("streamlit", build_streamlit_command(args))
    print("All publisher smoke checks passed.")


if __name__ == "__main__":
    main()
