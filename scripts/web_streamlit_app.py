"""Streamlit app for quick image -> DXF testing."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

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


def import_streamlit() -> Any:
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        if exc.name == "streamlit":
            raise SystemExit(
                "Missing optional dependency 'streamlit'.\n"
                "Install web extras with: uv sync --frozen --extra web\n"
                "Run with: uv run --frozen --extra web python scripts/web_streamlit.py"
            ) from exc
        raise
    return st


def parse_runtime_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=project_root / "output" / "web-streamlit",
    )
    args, _ = parser.parse_known_args()
    return args


def resolve_output_root(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def build_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register(HybridMVPStrategy())
    registry.register(TwoStageBaselineStrategy())
    registry.register(ConsensusQAStrategy())
    return registry


def format_result_markdown(
    strategy_name: str,
    dxf_path: Path | None,
    success: bool,
    elapsed_ms: float,
    metrics: dict[str, float],
    notes: list[str],
) -> str:
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


def sanitize_upload_filename(filename: str) -> str:
    normalized = filename.replace("\\", "/")
    sanitized = Path(normalized).name.strip().replace("\x00", "")
    if sanitized in {"", ".", ".."}:
        return "uploaded-image"
    return sanitized


def main() -> None:
    st = import_streamlit()

    args = parse_runtime_args()
    output_root = resolve_output_root(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    registry = build_registry()
    enabled_names = registry.get_enabled_names(FeatureFlags())
    if not enabled_names:
        st.set_page_config(page_title="img2dwg Streamlit Publisher", page_icon="📐", layout="wide")
        st.title("img2dwg Streamlit Publisher")
        st.error("활성화된 변환 전략이 없습니다. strategy registry/feature flags를 확인해 주세요.")
        st.stop()

    st.set_page_config(page_title="img2dwg Streamlit Publisher", page_icon="📐", layout="wide")
    st.title("img2dwg Streamlit Publisher")
    st.caption("평면도 이미지를 업로드하고 전략 기반으로 DXF 결과를 빠르게 확인합니다.")

    col1, col2 = st.columns(2)

    with col1:
        uploaded_file = st.file_uploader("Input Image (JPG/PNG)", type=["jpg", "jpeg", "png"])
        strategy_name = st.selectbox(
            "Strategy",
            enabled_names,
            index=0,
        )
        consensus_score = st.slider(
            "Consensus Score (consensus_qa/hybrid 참고)",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=0.74,
        )
        run_clicked = st.button("Convert to DXF", type="primary", use_container_width=True)

    with col2:
        st.markdown("### Summary")
        summary_placeholder = st.empty()
        download_placeholder = st.empty()

    if run_clicked:
        if uploaded_file is None:
            st.warning("이미지를 먼저 업로드해 주세요.")
            return

        upload_dir = output_root / "_uploads" / datetime.now().strftime("%Y%m%d")
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = sanitize_upload_filename(uploaded_file.name)
        upload_path = upload_dir / f"{uuid4().hex[:8]}-{safe_filename}"
        upload_path.write_bytes(uploaded_file.getvalue())

        run_dir = output_root / datetime.now().strftime("%Y%m%d-%H%M%S") / uuid4().hex[:8]
        conv_input = ConversionInput(
            image_path=upload_path,
            metadata={"consensus_score": float(consensus_score)},
        )

        start = time.perf_counter()
        try:
            strategy = registry.get(strategy_name)
            output = strategy.timed_run(conv_input, run_dir)
            summary = format_result_markdown(
                strategy_name=output.strategy_name,
                dxf_path=output.dxf_path,
                success=output.success,
                elapsed_ms=output.elapsed_ms,
                metrics=output.metrics,
                notes=output.notes,
            )
            summary_placeholder.markdown(summary)

            if output.success and output.dxf_path and output.dxf_path.exists():
                dxf_bytes = output.dxf_path.read_bytes()
                download_placeholder.download_button(
                    label="Download Generated DXF",
                    data=dxf_bytes,
                    file_name=output.dxf_path.name,
                    mime="application/dxf",
                    use_container_width=True,
                )
            else:
                download_placeholder.info("DXF 생성에 실패했거나 출력 파일이 없습니다.")
        except Exception as exc:  # pragma: no cover - UI runtime safety fallback
            elapsed_ms = (time.perf_counter() - start) * 1000
            summary = format_result_markdown(
                strategy_name=strategy_name,
                dxf_path=None,
                success=False,
                elapsed_ms=elapsed_ms,
                metrics={},
                notes=[f"Conversion failed with unexpected error: {exc!r}"],
            )
            summary_placeholder.markdown(summary)
            download_placeholder.info("변환 중 오류가 발생했습니다. Summary를 확인해 주세요.")


if __name__ == "__main__":
    main()
