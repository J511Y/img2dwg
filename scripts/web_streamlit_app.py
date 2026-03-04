"""Streamlit app for quick image -> DXF testing."""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import importlib
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ALLOWED_UPLOAD_SUFFIXES = {".jpg", ".jpeg", ".png"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_UPLOAD_BASENAME_LENGTH = 120
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_IEND_CHUNK = b"\x00\x00\x00\x00IEND\xaeB`\x82"
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"
WINDOWS_RESERVED_BASENAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.strategies.base import ConversionInput  # type: ignore[import-untyped]
from img2dwg.strategies.consensus_qa import ConsensusQAStrategy  # type: ignore[import-untyped]
from img2dwg.strategies.hybrid_mvp import HybridMVPStrategy  # type: ignore[import-untyped]
from img2dwg.strategies.registry import FeatureFlags, StrategyRegistry  # type: ignore[import-untyped]
from img2dwg.strategies.two_stage import TwoStageBaselineStrategy  # type: ignore[import-untyped]


def import_streamlit() -> Any:
    try:
        return importlib.import_module("streamlit")
    except ModuleNotFoundError as exc:
        if exc.name == "streamlit":
            raise SystemExit(
                "Missing optional dependency 'streamlit'.\n"
                "Install web extras with: uv sync --frozen --extra web\n"
                "Run with: uv run --frozen --extra web python scripts/web_streamlit.py"
            ) from exc
        raise


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


def assert_path_within_output_root(target_path: Path, output_root: Path, error_message: str) -> None:
    resolved_root = output_root.resolve()
    resolved_target = target_path.resolve()
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(error_message) from exc


def sanitize_upload_filename(filename: str) -> str:
    raw = filename.strip()
    if not raw:
        raise ValueError("업로드 파일명이 비어 있습니다.")

    if any(ord(char) < 32 or ord(char) == 127 for char in raw):
        raise ValueError("업로드 파일명에 제어 문자가 포함되어 있습니다.")

    normalized = raw.replace("\\", "/")

    if normalized.startswith("/"):
        raise ValueError("절대 경로 업로드 파일명은 허용되지 않습니다.")

    tokens = [token for token in normalized.split("/") if token]
    if len(tokens) != 1:
        raise ValueError("경로 구분자가 포함된 업로드 파일명은 허용되지 않습니다.")

    safe_name = Path(tokens[0]).name.strip()
    if safe_name in {"", ".", ".."} or ".." in safe_name:
        raise ValueError("상대 경로 토큰('..')이 포함된 파일명은 허용되지 않습니다.")

    if safe_name.startswith("."):
        raise ValueError("숨김 파일(dotfile) 형태의 업로드 파일명은 허용되지 않습니다.")

    if len(safe_name) > MAX_UPLOAD_BASENAME_LENGTH:
        raise ValueError(f"업로드 파일명 길이는 {MAX_UPLOAD_BASENAME_LENGTH}자를 초과할 수 없습니다.")

    if any(char in safe_name for char in {":", "*", "?", '"', "<", ">", "|"}):
        raise ValueError("업로드 파일명에 허용되지 않은 특수문자가 포함되어 있습니다.")

    stem = Path(safe_name).stem.rstrip(" .").lower()
    if stem in WINDOWS_RESERVED_BASENAMES:
        raise ValueError("운영체제 예약 이름은 업로드 파일명으로 사용할 수 없습니다.")

    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise ValueError("허용되지 않은 파일 확장자입니다. (.jpg/.jpeg/.png만 허용)")

    return safe_name


def detect_image_signature(payload: bytes) -> str | None:
    if payload.startswith(PNG_SIGNATURE):
        return "png"
    if payload.startswith(JPEG_SOI):
        return "jpeg"
    return None


def validate_upload_signature(payload: bytes, filename_suffix: str) -> None:
    detected = detect_image_signature(payload)

    expected_by_suffix = {
        ".png": "png",
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
    }
    expected = expected_by_suffix.get(filename_suffix.lower())
    if expected is None:
        raise ValueError("허용되지 않은 파일 확장자입니다. (.jpg/.jpeg/.png만 허용)")

    if detected != expected:
        raise ValueError("파일 내용 시그니처가 확장자와 일치하지 않습니다.")

    if detected == "png" and not payload.endswith(PNG_IEND_CHUNK):
        raise ValueError("PNG 파일 종료 시그니처(IEND)가 없어 손상된 파일로 판단됩니다.")

    if detected == "jpeg" and not payload.endswith(JPEG_EOI):
        raise ValueError("JPEG 파일 종료 시그니처(EOI)가 없어 손상된 파일로 판단됩니다.")


def validate_upload_payload(
    payload: bytes,
    *,
    filename_suffix: str,
    max_upload_bytes: int = MAX_UPLOAD_BYTES,
) -> None:
    if not payload:
        raise ValueError("업로드 파일 내용이 비어 있습니다.")

    if len(payload) > max_upload_bytes:
        max_mb = max_upload_bytes // (1024 * 1024)
        raise ValueError(f"업로드 파일 크기는 {max_mb}MB를 초과할 수 없습니다.")

    validate_upload_signature(payload, filename_suffix)


def build_safe_upload_path(upload_dir: Path, output_root: Path, uploaded_filename: str) -> Path:
    safe_filename = sanitize_upload_filename(uploaded_filename)

    assert_path_within_output_root(
        upload_dir,
        output_root,
        "업로드 저장 디렉터리가 output-root를 벗어났습니다.",
    )

    upload_path = upload_dir / f"{uuid4().hex[:8]}-{safe_filename}"
    assert_path_within_output_root(
        upload_path,
        output_root,
        "업로드 저장 경로가 output-root를 벗어났습니다.",
    )
    return upload_path


def write_upload_payload(upload_path: Path, output_root: Path, payload: bytes) -> None:
    validate_upload_payload(payload, filename_suffix=upload_path.suffix)

    assert_path_within_output_root(
        upload_path.parent,
        output_root,
        "업로드 저장 디렉터리가 output-root를 벗어났습니다.",
    )

    if upload_path.exists():
        raise ValueError("업로드 저장 경로가 이미 존재합니다.")

    try:
        with upload_path.open("xb") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise ValueError("업로드 저장 경로가 이미 존재합니다.") from exc

    assert_path_within_output_root(
        upload_path,
        output_root,
        "업로드 저장 경로가 output-root를 벗어났습니다.",
    )


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

        try:
            upload_path = build_safe_upload_path(upload_dir, output_root, uploaded_file.name)
            write_upload_payload(upload_path, output_root, uploaded_file.getvalue())
        except ValueError as exc:
            st.error(f"업로드 파일 검증 실패: {exc}")
            return

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
