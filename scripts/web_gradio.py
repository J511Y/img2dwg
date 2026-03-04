"""Gradio web entrypoint for quick image -> DXF testing."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import socket
import sys
import time
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.strategies.base import ConversionInput  # type: ignore[import-untyped]
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy  # type: ignore[import-untyped]
from img2dwg.strategies.hybrid_mvp import HybridMVPStrategy  # type: ignore[import-untyped]
from img2dwg.strategies.registry import (  # type: ignore[import-untyped]
    FeatureFlags,
    StrategyRegistry,
)
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy  # type: ignore[import-untyped]
from img2dwg.web.retention import cleanup_output_root, format_cleanup_report


def import_gradio() -> Any:
    """Import Gradio with a friendly setup hint when missing."""
    try:
        import gradio as gr
    except ModuleNotFoundError as exc:
        if exc.name == "gradio":
            raise SystemExit(
                "Missing optional dependency 'gradio'.\n"
                "Install web extras with: uv sync --frozen --extra web\n"
                "Run with: uv run --frozen --extra web python scripts/web_gradio.py"
            ) from exc
        raise
    return gr


def resolve_probe_host(host: str) -> str:
    """Normalize wildcard hosts to loopback for local smoke probes."""
    normalized = host.strip()
    if normalized in {"0.0.0.0", "::", "[::]", ""}:
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


def build_registry() -> StrategyRegistry:
    """Create and populate strategy registry."""
    registry = StrategyRegistry()
    registry.register(HybridMVPStrategy())
    registry.register(TwoStageBaselineStrategy())
    registry.register(ConsensusQAStrategy())
    return registry


def resolve_output_root(path: Path) -> Path:
    """Resolve output path deterministically from project root when relative."""
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


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


def format_result_markdown(
    strategy_name: str,
    dxf_path: Path | None,
    success: bool,
    elapsed_ms: float,
    metrics: dict[str, float],
    notes: list[str],
) -> str:
    """Build markdown summary shown in UI."""
    lines = [
        "## Conversion Result",
        f"- Strategy: `{strategy_name}`",
        f"- Success: `{success}`",
        f"- Elapsed: `{elapsed_ms:.2f} ms`",
        f"- DXF Path: `{dxf_path}`" if dxf_path else "- DXF Path: `N/A`",
    ]

    if metrics:
        lines.append("\n### Metrics")
        for key, value in metrics.items():
            lines.append(f"- {key}: `{value}`")

    if notes:
        lines.append("\n### Notes")
        for note in notes:
            lines.append(f"- {note}")

    return "\n".join(lines)


def wait_for_http_ready(url: str, timeout_seconds: float, interval_seconds: float = 0.25) -> bool:
    """Wait until a HTTP endpoint starts responding."""
    deadline = time.time() + max(0.0, timeout_seconds)
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1.5):
                return True
        except (URLError, OSError):
            time.sleep(max(0.05, interval_seconds))
    return False


def build_app(output_root: Path, gr: Any) -> Any:
    """Build Gradio Blocks app."""
    registry = build_registry()
    enabled_names = registry.get_enabled_names(FeatureFlags())
    if not enabled_names:
        raise RuntimeError(
            "No enabled conversion strategies found. "
            "Check strategy registry/feature flags before launching web publisher."
        )

    def convert_image(
        uploaded_image_path: str,
        strategy_name: str,
        consensus_score: float,
    ) -> tuple[str | None, str]:
        """Run conversion strategy and return generated DXF path + markdown summary."""
        if not uploaded_image_path:
            return None, "이미지를 업로드해 주세요."

        image_path = Path(uploaded_image_path)
        if not image_path.exists():
            return None, f"업로드된 이미지 파일을 찾을 수 없습니다: {image_path}"

        if strategy_name not in enabled_names:
            return None, f"유효하지 않은 전략입니다: {strategy_name}"

        run_dir = output_root / datetime.now().strftime("%Y%m%d-%H%M%S") / uuid4().hex[:8]
        conv_input = ConversionInput(
            image_path=image_path,
            metadata={"consensus_score": float(consensus_score)},
        )

        start = time.perf_counter()
        try:
            strategy = registry.get(strategy_name)
            output = strategy.timed_run(conv_input, run_dir)
        except Exception as exc:  # pragma: no cover - runtime safety fallback
            elapsed_ms = (time.perf_counter() - start) * 1000
            summary = format_result_markdown(
                strategy_name=strategy_name,
                dxf_path=None,
                success=False,
                elapsed_ms=elapsed_ms,
                metrics={},
                notes=[f"Conversion failed with unexpected error: {exc!r}"],
            )
            return None, summary

        summary = format_result_markdown(
            strategy_name=output.strategy_name,
            dxf_path=output.dxf_path,
            success=output.success,
            elapsed_ms=output.elapsed_ms,
            metrics=output.metrics,
            notes=output.notes,
        )

        if not output.success or output.dxf_path is None:
            return None, summary

        return str(output.dxf_path), summary

    with gr.Blocks(title="img2dwg Web Publisher") as app:
        gr.Markdown(
            """
# img2dwg Web Publisher

평면도 이미지를 업로드하고 전략 기반으로 **DXF 출력**을 빠르게 테스트합니다.
- 기본 출력: DXF (`.dxf`)
- 전략: `hybrid_mvp`, `two_stage_baseline`, `consensus_qa`
            """.strip()
        )

        with gr.Row():
            with gr.Column(scale=1):
                image_input = gr.Image(
                    type="filepath",
                    label="Input Image (JPG/PNG)",
                )
                strategy_input = gr.Dropdown(
                    choices=enabled_names,
                    value=enabled_names[0] if enabled_names else None,
                    label="Strategy",
                )
                consensus_input = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    step=0.01,
                    value=0.74,
                    label="Consensus Score (consensus_qa/hybrid 참고)",
                )
                run_button = gr.Button("Convert to DXF", variant="primary")

            with gr.Column(scale=1):
                dxf_output = gr.File(label="Generated DXF")
                summary_output = gr.Markdown(label="Summary")

        run_button.click(
            fn=convert_image,
            inputs=[image_input, strategy_input, consensus_input],
            outputs=[dxf_output, summary_output],
        )

    return app


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run img2dwg Gradio web app")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=7860, help="Port to bind")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=project_root / "output" / "web",
        help="Directory where generated DXF files are stored",
    )
    parser.add_argument("--share", action="store_true", help="Enable Gradio share URL")
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
        help="Start app briefly and close automatically",
    )
    parser.add_argument(
        "--smoke-wait-seconds",
        type=float,
        default=2.0,
        help="Seconds to keep server alive in smoke test mode after readiness check",
    )
    parser.add_argument(
        "--smoke-timeout-seconds",
        type=float,
        default=15.0,
        help="Max seconds to wait for HTTP readiness in smoke test mode",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    args.output_root = resolve_output_root(args.output_root)
    args.output_root.mkdir(parents=True, exist_ok=True)
    run_startup_cleanup(args)
    ensure_port_available(args.host, args.port)

    gr = import_gradio()
    app = build_app(args.output_root, gr)

    if args.smoke_test:
        launched = False
        probe_url = f"http://{resolve_probe_host(args.host)}:{args.port}"
        try:
            app.launch(
                server_name=args.host,
                server_port=args.port,
                share=args.share,
                inbrowser=False,
                show_error=True,
                prevent_thread_lock=True,
            )
            launched = True
            is_ready = wait_for_http_ready(
                probe_url,
                timeout_seconds=args.smoke_timeout_seconds,
            )
            if not is_ready:
                raise RuntimeError(
                    f"Smoke test failed: web endpoint not ready within {args.smoke_timeout_seconds}s"
                )
            time.sleep(max(0.0, args.smoke_wait_seconds))
            print(f"Smoke test passed: {probe_url}")
        finally:
            if launched:
                app.close()
        return

    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        inbrowser=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
