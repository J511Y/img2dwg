from __future__ import annotations

import importlib.util
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GRADIO_SCRIPT_PATH = REPO_ROOT / "scripts" / "web_gradio.py"
STREAMLIT_SCRIPT_PATH = REPO_ROOT / "scripts" / "web_streamlit.py"
SMOKE_RUNNER_SCRIPT_PATH = REPO_ROOT / "scripts" / "smoke_web_publishers.py"


class _ReadyHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def _start_http_server() -> tuple[HTTPServer, threading.Thread, str]:
    server = HTTPServer(("127.0.0.1", 0), _ReadyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    host_text = host.decode("utf-8") if isinstance(host, bytes) else str(host)
    return server, thread, f"http://{host_text}:{int(port)}"


def _load_script_module(module_name: str, script_path: Path) -> ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module spec: {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_gradio_cli_defaults() -> None:
    module = _load_script_module("web_gradio_script_for_tests", GRADIO_SCRIPT_PATH)

    args = module.parse_args([])

    assert args.host == "127.0.0.1"
    assert args.port == 7860
    assert args.allow_remote is False
    assert args.smoke_test is False
    assert args.smoke_timeout_seconds == 15.0
    assert args.cleanup_max_age_days == 7.0
    assert args.cleanup_max_size_gb == 5.0
    assert args.cleanup_dry_run is False
    assert args.no_cleanup is False


def test_streamlit_cli_defaults() -> None:
    module = _load_script_module("web_streamlit_script_for_tests", STREAMLIT_SCRIPT_PATH)

    args = module.parse_args([])

    assert args.host == "127.0.0.1"
    assert args.port == 8501
    assert args.allow_remote is False
    assert args.smoke_test is False
    assert args.smoke_timeout_seconds == 20.0
    assert args.smoke_log_lines == 80
    assert args.smoke_keep_log is False
    assert args.cleanup_max_age_days == 7.0
    assert args.cleanup_max_size_gb == 5.0
    assert args.cleanup_dry_run is False
    assert args.no_cleanup is False


def test_output_root_resolution_is_project_relative() -> None:
    gradio_module = _load_script_module("web_gradio_script_for_tests", GRADIO_SCRIPT_PATH)
    streamlit_module = _load_script_module("web_streamlit_script_for_tests", STREAMLIT_SCRIPT_PATH)

    gradio_resolved = gradio_module.resolve_output_root(Path("output/custom"))
    streamlit_resolved = streamlit_module.resolve_output_root(Path("output/custom"))

    assert gradio_resolved == REPO_ROOT / "output" / "custom"
    assert streamlit_resolved == REPO_ROOT / "output" / "custom"


def test_smoke_runner_cli_defaults() -> None:
    module = _load_script_module("smoke_web_publishers_script_for_tests", SMOKE_RUNNER_SCRIPT_PATH)

    args = module.parse_args([])

    assert args.host == "127.0.0.1"
    assert args.allow_remote is False
    assert args.gradio_port == 7861
    assert args.streamlit_port == 8502
    assert args.smoke_wait_seconds == 0.5
    assert args.gradio_timeout_seconds == 20.0
    assert args.streamlit_timeout_seconds == 25.0
    assert args.streamlit_smoke_log_lines == 80
    assert args.streamlit_smoke_keep_log is False
    assert args.cleanup_dry_run is False


def test_smoke_runner_build_commands_include_overrides() -> None:
    module = _load_script_module("smoke_web_publishers_script_for_tests", SMOKE_RUNNER_SCRIPT_PATH)

    args = module.parse_args(
        [
            "--host",
            "0.0.0.0",
            "--allow-remote",
            "--gradio-port",
            "7900",
            "--streamlit-port",
            "8600",
            "--smoke-wait-seconds",
            "1.2",
            "--streamlit-smoke-log-lines",
            "120",
            "--streamlit-smoke-keep-log",
            "--cleanup-dry-run",
        ]
    )

    gradio_command = module.build_gradio_command(args)
    streamlit_command = module.build_streamlit_command(args)

    assert "--host" in gradio_command and "0.0.0.0" in gradio_command
    assert "--port" in gradio_command and "7900" in gradio_command
    assert "--smoke-test" in gradio_command
    assert "--allow-remote" in gradio_command
    assert "--cleanup-dry-run" in gradio_command

    assert "--host" in streamlit_command and "0.0.0.0" in streamlit_command
    assert "--port" in streamlit_command and "8600" in streamlit_command
    assert "--smoke-log-lines" in streamlit_command and "120" in streamlit_command
    assert "--smoke-keep-log" in streamlit_command
    assert "--allow-remote" in streamlit_command
    assert "--cleanup-dry-run" in streamlit_command


def test_resolve_probe_host_handles_wildcards() -> None:
    gradio_module = _load_script_module("web_gradio_script_for_tests", GRADIO_SCRIPT_PATH)
    streamlit_module = _load_script_module("web_streamlit_script_for_tests", STREAMLIT_SCRIPT_PATH)

    for host in ["0.0.0.0", "::", "[::]", ""]:
        assert gradio_module.resolve_probe_host(host) == "127.0.0.1"
        assert streamlit_module.resolve_probe_host(host) == "127.0.0.1"


def test_requires_remote_access_ack_detects_loopback_and_remote_hosts() -> None:
    gradio_module = _load_script_module("web_gradio_script_for_tests", GRADIO_SCRIPT_PATH)
    streamlit_module = _load_script_module("web_streamlit_script_for_tests", STREAMLIT_SCRIPT_PATH)

    for module in (gradio_module, streamlit_module):
        assert module.requires_remote_access_ack("127.0.0.1") is False
        assert module.requires_remote_access_ack("localhost") is False
        assert module.requires_remote_access_ack("::1") is False
        assert module.requires_remote_access_ack("0.0.0.0") is True
        assert module.requires_remote_access_ack("192.168.0.12") is True


def test_ensure_access_policy_requires_allow_remote_for_non_loopback() -> None:
    gradio_module = _load_script_module("web_gradio_script_for_tests", GRADIO_SCRIPT_PATH)
    streamlit_module = _load_script_module("web_streamlit_script_for_tests", STREAMLIT_SCRIPT_PATH)

    for module in (gradio_module, streamlit_module):
        module.ensure_access_policy("127.0.0.1", allow_remote=False)
        module.ensure_access_policy("0.0.0.0", allow_remote=True)

        with pytest.raises(RuntimeError, match="--allow-remote"):
            module.ensure_access_policy("0.0.0.0", allow_remote=False)


def test_port_probe_detects_open_socket() -> None:
    gradio_module = _load_script_module("web_gradio_script_for_tests", GRADIO_SCRIPT_PATH)
    streamlit_module = _load_script_module("web_streamlit_script_for_tests", STREAMLIT_SCRIPT_PATH)

    for module in (gradio_module, streamlit_module):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        try:
            host, port = listener.getsockname()
            assert host == "127.0.0.1"
            assert module.is_port_open("127.0.0.1", port) is True
        finally:
            listener.close()


def test_streamlit_build_command_includes_runtime_flags() -> None:
    module = _load_script_module("web_streamlit_script_for_tests", STREAMLIT_SCRIPT_PATH)

    args = module.parse_args(
        ["--host", "0.0.0.0", "--port", "8600", "--output-root", "output/custom"]
    )
    command = module.build_streamlit_command(args)

    assert command[0] == sys.executable
    assert command[1:4] == ["-m", "streamlit", "run"]
    assert "--server.address" in command and "0.0.0.0" in command
    assert "--server.port" in command and "8600" in command
    assert "--output-root" in command and "output/custom" in command


def test_streamlit_read_log_tail_returns_latest_lines(tmp_path: Path) -> None:
    module = _load_script_module("web_streamlit_script_for_tests", STREAMLIT_SCRIPT_PATH)

    log_path = tmp_path / "smoke.log"
    log_path.write_text("line1\nline2\nline3\n", encoding="utf-8")

    assert module.read_log_tail(log_path, 2) == "line2\nline3"
    assert module.read_log_tail(log_path, 0) == ""


def test_ensure_port_available_raises_for_open_port() -> None:
    gradio_module = _load_script_module("web_gradio_script_for_tests", GRADIO_SCRIPT_PATH)
    streamlit_module = _load_script_module("web_streamlit_script_for_tests", STREAMLIT_SCRIPT_PATH)

    for module in (gradio_module, streamlit_module):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        try:
            _, port = listener.getsockname()
            with pytest.raises(RuntimeError, match="already in use"):
                module.ensure_port_available("127.0.0.1", port)
        finally:
            listener.close()


def test_wait_for_http_ready_detects_live_endpoint() -> None:
    gradio_module = _load_script_module("web_gradio_script_for_tests", GRADIO_SCRIPT_PATH)
    streamlit_module = _load_script_module("web_streamlit_script_for_tests", STREAMLIT_SCRIPT_PATH)

    server, thread, url = _start_http_server()
    try:
        assert gradio_module.wait_for_http_ready(url, timeout_seconds=1.0, interval_seconds=0.05)
        assert streamlit_module.wait_for_http_ready(url, timeout_seconds=1.0, interval_seconds=0.05)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def test_streamlit_wait_for_http_ready_fails_fast_on_early_process_exit() -> None:
    module = _load_script_module("web_streamlit_script_for_tests", STREAMLIT_SCRIPT_PATH)
    process = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(7)"])

    try:
        with pytest.raises(RuntimeError, match="exited early"):
            module.wait_for_http_ready(
                "http://127.0.0.1:9",
                timeout_seconds=0.8,
                process=process,
                interval_seconds=0.05,
            )
    finally:
        process.wait(timeout=1)
