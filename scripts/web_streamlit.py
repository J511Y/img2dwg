"""Streamlit runner entrypoint for img2dwg web testing."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import importlib.util
import ipaddress
import socket
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

project_root = Path(__file__).resolve().parent.parent
streamlit_app_path = project_root / "scripts" / "web_streamlit_app.py"
sys.path.insert(0, str(project_root / "src"))

from img2dwg.web.retention import (
    cleanup_output_root,
    format_cleanup_report,
)


def resolve_output_root(path: Path) -> Path:
    """Resolve output path deterministically from project root when relative."""
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def normalize_host_input(host: str) -> str:
    """Normalize host CLI input and reject ambiguous control/format-character payloads."""
    normalized = host.strip()
    if not normalized:
        raise RuntimeError("Host must not be empty.")
    if host != normalized:
        raise RuntimeError("Host must not include surrounding whitespace.")
    if any(unicodedata.category(char).startswith("C") for char in normalized):
        raise RuntimeError(
            "Host contains control or format characters; provide a plain hostname or IP."
        )
    return normalized


def resolve_probe_host(host: str) -> str:
    """Normalize wildcard hosts to loopback for local smoke probes."""
    normalized = normalize_host_input(host)
    if normalized in {"0.0.0.0", "::", "[::]"}:
        return "127.0.0.1"
    return normalized


def is_port_open(host: str, port: int, timeout_seconds: float = 0.3) -> bool:
    """Return True when TCP port already accepts connections."""
    if port <= 0:
        return False

    probe_host = resolve_probe_host(host)
    try:
        with socket.create_connection((probe_host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def ensure_port_available(host: str, port: int) -> None:
    """Fail fast with a clear hint when target port is already occupied."""
    if is_port_open(host, port):
        raise RuntimeError(
            f"Port {port} is already in use on {resolve_probe_host(host)}. "
            "Use --port to select another one."
        )


def requires_remote_access_ack(host: str) -> bool:
    """Return True when host binding may expose the publisher beyond loopback."""
    normalized = normalize_host_input(host).lower()
    if normalized in {"localhost", "127.0.0.1", "::1", "[::1]"}:
        return False

    candidate = (
        normalized[1:-1] if normalized.startswith("[") and normalized.endswith("]") else normalized
    )
    try:
        return not ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        # Hostnames other than localhost are treated as remotely reachable by default.
        return True


def ensure_access_policy(host: str, allow_remote: bool) -> None:
    """Require explicit opt-in before exposing publisher on non-loopback hosts."""
    if requires_remote_access_ack(host) and not allow_remote:
        raise RuntimeError(
            "Refusing non-loopback host binding without explicit acknowledgement. "
            "Pass --allow-remote when you intentionally expose the web publisher."
        )


def ensure_streamlit_installed() -> None:
    """Validate optional Streamlit dependency with a clear setup hint."""
    if importlib.util.find_spec("streamlit") is not None:
        return
    raise SystemExit(
        "Missing optional dependency 'streamlit'.\n"
        "Install web extras with: uv sync --frozen --extra web\n"
        "Run with: uv run --frozen --extra web python scripts/web_streamlit.py"
    )


def run_startup_cleanup(args: argparse.Namespace) -> None:
    if args.no_cleanup:
        print(
            "[cleanup:DISABLED] Retention cleanup is disabled. "
            "Outputs/uploads may accumulate without limit."
        )
        return

    report = cleanup_output_root(
        args.output_root,
        max_age_days=args.cleanup_max_age_days,
        max_size_gb=args.cleanup_max_size_gb,
        dry_run=args.cleanup_dry_run,
    )
    print(format_cleanup_report(report))


def wait_for_http_ready(
    url: str,
    timeout_seconds: float,
    process: subprocess.Popen[str] | None = None,
    interval_seconds: float = 0.25,
) -> bool:
    """Wait until the given URL responds over HTTP."""
    deadline = time.time() + max(0.0, timeout_seconds)
    while time.time() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(
                f"Smoke test failed: Streamlit process exited early with code {process.returncode}"
            )
        try:
            with urlopen(url, timeout=1.5):
                return True
        except (URLError, OSError):
            time.sleep(max(0.05, interval_seconds))
    return False


def read_log_tail(log_path: Path, max_lines: int) -> str:
    """Read log tail for concise smoke failure context."""
    if max_lines <= 0 or not log_path.exists():
        return ""

    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run img2dwg Streamlit web app")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8501, help="Port to bind")
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Acknowledge non-loopback host binding (required for 0.0.0.0/LAN exposure)",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=project_root / "output" / "web-streamlit",
        help="Directory where generated DXF files are stored",
    )
    parser.add_argument(
        "--cleanup-max-age-days",
        type=float,
        default=7.0,
        help="Retention threshold (days); files older than this are deleted",
    )
    parser.add_argument(
        "--cleanup-max-size-gb",
        type=float,
        default=5.0,
        help="Retention cap (GB); oldest files are removed when exceeded",
    )
    parser.add_argument(
        "--cleanup-dry-run",
        action="store_true",
        help="Report cleanup targets without deleting files",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Disable retention cleanup (not recommended)",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Start app briefly, validate endpoint, then close",
    )
    parser.add_argument(
        "--smoke-timeout-seconds",
        type=float,
        default=20.0,
        help="Max seconds to wait for HTTP readiness",
    )
    parser.add_argument(
        "--smoke-wait-seconds",
        type=float,
        default=2.0,
        help="Seconds to keep server alive after readiness check",
    )
    parser.add_argument(
        "--smoke-log-lines",
        type=int,
        default=80,
        help="How many tail lines to include when smoke test fails",
    )
    parser.add_argument(
        "--smoke-keep-log",
        action="store_true",
        help="Keep Streamlit smoke log file even when test passes",
    )
    return parser.parse_args(argv)


def build_streamlit_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(streamlit_app_path),
        "--server.address",
        args.host,
        "--server.port",
        str(args.port),
        "--server.headless",
        "true",
        "--",
        "--output-root",
        str(args.output_root),
    ]


def run_smoke_test(args: argparse.Namespace) -> None:
    ensure_access_policy(args.host, args.allow_remote)
    ensure_port_available(args.host, args.port)
    args.output_root = resolve_output_root(args.output_root)
    args.output_root.mkdir(parents=True, exist_ok=True)
    run_startup_cleanup(args)

    command = build_streamlit_command(args)
    probe_url = f"http://{resolve_probe_host(args.host)}:{args.port}"

    smoke_error: Exception | None = None
    smoke_log_path: Path

    with tempfile.NamedTemporaryFile(
        mode="w+",
        encoding="utf-8",
        prefix="img2dwg-streamlit-smoke-",
        suffix=".log",
        delete=False,
    ) as log_file:
        smoke_log_path = Path(log_file.name)
        process = subprocess.Popen(
            command,
            cwd=str(project_root),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

        try:
            is_ready = wait_for_http_ready(
                probe_url,
                timeout_seconds=args.smoke_timeout_seconds,
                process=process,
            )
            if not is_ready:
                raise RuntimeError(
                    f"Smoke test failed: web endpoint not ready within {args.smoke_timeout_seconds}s"
                )
            time.sleep(max(0.0, args.smoke_wait_seconds))
            print(f"Smoke test passed: {probe_url}")
        except Exception as exc:  # pragma: no cover - exercised by runtime smoke path
            smoke_error = exc
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            log_file.flush()

    if smoke_error is not None:
        log_tail = read_log_tail(smoke_log_path, args.smoke_log_lines)
        raise RuntimeError(
            f"{smoke_error}\n"
            f"Streamlit smoke log: {smoke_log_path}\n"
            f"--- log tail ---\n{log_tail or '(no output)'}\n--- end log tail ---"
        ) from smoke_error

    if args.smoke_keep_log:
        print(f"Smoke log saved: {smoke_log_path}")
    else:
        smoke_log_path.unlink(missing_ok=True)


def run_server(args: argparse.Namespace) -> None:
    ensure_access_policy(args.host, args.allow_remote)
    ensure_port_available(args.host, args.port)
    args.output_root = resolve_output_root(args.output_root)
    args.output_root.mkdir(parents=True, exist_ok=True)
    run_startup_cleanup(args)
    command = build_streamlit_command(args)
    completed = subprocess.run(command, cwd=str(project_root), check=False)
    raise SystemExit(completed.returncode)


def main() -> None:
    if not streamlit_app_path.exists():
        raise FileNotFoundError(f"Missing Streamlit app file: {streamlit_app_path}")

    ensure_streamlit_installed()
    args = parse_args()
    if args.smoke_test:
        run_smoke_test(args)
        return
    run_server(args)


if __name__ == "__main__":
    main()
