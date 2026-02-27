from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "export_triad_artifacts.py"
VALID_GIT_REF = "0123456789abcdef0123456789abcdef01234567"
VALID_MANIFEST_REF = "eval/examples/dataset_manifest.guardian-premerge.csv"


def _load_script_module() -> ModuleType:
    module_name = "export_triad_artifacts_script_for_tests"
    if module_name in sys.modules:
        loaded = sys.modules[module_name]
        return loaded

    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load export_triad_artifacts.py module spec")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[module_name] = module
    return module


def _run_main(module: ModuleType, args: list[str]) -> None:
    old_argv = sys.argv[:]
    try:
        sys.argv = [str(SCRIPT_PATH), *args]
        module.main()
    finally:
        sys.argv = old_argv


def _write_benchmark_payloads(
    tmp_path: Path,
    *,
    include_synthesis: bool,
    triad_available: bool,
    triad_missing: list[str],
    summary_passed: bool,
    benchmark_metadata: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    results_path = tmp_path / "benchmark_results.json"
    summary_path = tmp_path / "benchmark_summary.json"

    def _strategy_row(name: str) -> dict[str, Any]:
        return {
            "strategy_name": name,
            "summary": {
                "success_rate": 1.0,
                "cad_loadable_rate": 1.0,
                "cad_loadable_count": 1,
            },
            "cases": [
                {
                    "case_id": "c-1",
                    "image_path": "img/c-1.png",
                    "dxf_path": "out/c-1.dxf",
                    "success": True,
                    "cad_loadable": True,
                    "elapsed_ms": 10.0,
                }
            ],
        }

    strategies = [_strategy_row("two_stage_baseline"), _strategy_row("consensus_qa")]
    if include_synthesis:
        strategies.append(_strategy_row("hybrid_mvp"))

    default_metadata = {
        "git_ref": VALID_GIT_REF,
        "generated_at": "2026-02-27T12:34:56+09:00",
        "dataset_manifest_ref": VALID_MANIFEST_REF,
    }
    if benchmark_metadata is not None:
        default_metadata.update(benchmark_metadata)

    results_payload = {
        "run": {
            "run_id": "run-1",
            "dataset_id": "unit",
            "git_ref": VALID_GIT_REF,
        },
        "strategies": strategies,
        "comparisons": {
            "thesis_antithesis_synthesis": {
                "thesis": "two_stage_baseline",
                "antithesis": "consensus_qa",
                "synthesis": "hybrid_mvp",
                "available": triad_available,
                "missing": triad_missing,
                "cad_loadable_gate": {
                    "passed": summary_passed,
                },
                "deltas": {},
            }
        },
    }
    summary_payload = {
        "triad_gate": {
            "available": triad_available,
            "passed": summary_passed,
            "missing": triad_missing,
        },
        "benchmark_metadata": default_metadata,
    }

    results_path.write_text(json.dumps(results_payload, ensure_ascii=False), encoding="utf-8")
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False), encoding="utf-8")

    return results_path, summary_path


def test_export_triad_artifacts_writes_manifest_and_triad_summary(tmp_path: Path) -> None:
    module = _load_script_module()
    results_path, summary_path = _write_benchmark_payloads(
        tmp_path,
        include_synthesis=True,
        triad_available=True,
        triad_missing=[],
        summary_passed=True,
    )
    out_dir = tmp_path / "triad"

    _run_main(
        module,
        [
            "--results",
            str(results_path),
            "--summary",
            str(summary_path),
            "--out-dir",
            str(out_dir),
        ],
    )

    manifest = json.loads((out_dir / "triad_artifacts_manifest.json").read_text(encoding="utf-8"))
    triad_eval = json.loads(
        (out_dir / "eval" / "eval_summary.triad.json").read_text(encoding="utf-8")
    )

    assert manifest["pred"]["jeong"].endswith("pred/pred_summary.jeong.json")
    assert manifest["eval"]["triad"].endswith("eval/eval_summary.triad.json")
    assert triad_eval["triad"]["thesis"] == "two_stage_baseline"
    assert triad_eval["triad"]["gate"]["summary"]["passed"] is True

    assert manifest["benchmark_metadata"] == {
        "git_ref": VALID_GIT_REF,
        "generated_at": "2026-02-27T03:34:56Z",
        "dataset_manifest_ref": VALID_MANIFEST_REF,
    }
    assert triad_eval["benchmark_metadata"] == manifest["benchmark_metadata"]


def test_export_triad_artifacts_require_triad_fails_fast_on_missing_axes(tmp_path: Path) -> None:
    module = _load_script_module()
    results_path, summary_path = _write_benchmark_payloads(
        tmp_path,
        include_synthesis=False,
        triad_available=False,
        triad_missing=["hybrid_mvp"],
        summary_passed=False,
    )
    out_dir = tmp_path / "triad"

    with pytest.raises(ValueError, match="triad requirement check failed"):
        _run_main(
            module,
            [
                "--results",
                str(results_path),
                "--summary",
                str(summary_path),
                "--out-dir",
                str(out_dir),
                "--require-triad",
            ],
        )


@pytest.mark.parametrize(
    ("metadata_patch", "error_match"),
    [
        ({"git_ref": "abc1234"}, "benchmark_metadata.git_ref must match"),
        ({"generated_at": "2026-02-27 12:34:56"}, "benchmark_metadata.generated_at"),
        (
            {"dataset_manifest_ref": "/abs/path.csv"},
            "dataset_manifest_ref must be a repo-relative path",
        ),
    ],
)
def test_export_triad_artifacts_require_triad_fails_fast_on_invalid_metadata(
    tmp_path: Path,
    metadata_patch: dict[str, Any],
    error_match: str,
) -> None:
    module = _load_script_module()
    results_path, summary_path = _write_benchmark_payloads(
        tmp_path,
        include_synthesis=True,
        triad_available=True,
        triad_missing=[],
        summary_passed=True,
        benchmark_metadata=metadata_patch,
    )

    with pytest.raises(ValueError, match=error_match):
        _run_main(
            module,
            [
                "--results",
                str(results_path),
                "--summary",
                str(summary_path),
                "--out-dir",
                str(tmp_path / "triad"),
                "--require-triad",
            ],
        )


def test_export_triad_artifacts_fails_fast_on_invalid_metadata_during_export(
    tmp_path: Path,
) -> None:
    module = _load_script_module()
    results_path, summary_path = _write_benchmark_payloads(
        tmp_path,
        include_synthesis=True,
        triad_available=True,
        triad_missing=[],
        summary_passed=True,
        benchmark_metadata={"git_ref": "abc1234"},
    )

    with pytest.raises(ValueError, match="benchmark_metadata.git_ref must match"):
        _run_main(
            module,
            [
                "--results",
                str(results_path),
                "--summary",
                str(summary_path),
                "--out-dir",
                str(tmp_path / "triad"),
            ],
        )


def test_export_triad_artifacts_requires_metadata_without_require_triad(tmp_path: Path) -> None:
    module = _load_script_module()
    results_path, summary_path = _write_benchmark_payloads(
        tmp_path,
        include_synthesis=True,
        triad_available=True,
        triad_missing=[],
        summary_passed=True,
    )

    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    summary_payload.pop("benchmark_metadata", None)
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="benchmark_metadata.dataset_manifest_ref is required"):
        _run_main(
            module,
            [
                "--results",
                str(results_path),
                "--summary",
                str(summary_path),
                "--out-dir",
                str(tmp_path / "triad"),
            ],
        )


def test_export_triad_artifacts_fails_fast_on_invalid_comparisons_type(tmp_path: Path) -> None:
    module = _load_script_module()
    results_path, summary_path = _write_benchmark_payloads(
        tmp_path,
        include_synthesis=True,
        triad_available=True,
        triad_missing=[],
        summary_passed=True,
    )

    results_payload = json.loads(results_path.read_text(encoding="utf-8"))
    results_payload["comparisons"] = []
    results_path.write_text(json.dumps(results_payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="results.comparisons must be object"):
        _run_main(
            module,
            [
                "--results",
                str(results_path),
                "--summary",
                str(summary_path),
                "--out-dir",
                str(tmp_path / "triad"),
            ],
        )


def test_export_triad_artifacts_rejects_backslash_parent_manifest_ref(tmp_path: Path) -> None:
    module = _load_script_module()
    results_path, summary_path = _write_benchmark_payloads(
        tmp_path,
        include_synthesis=True,
        triad_available=True,
        triad_missing=[],
        summary_passed=True,
        benchmark_metadata={"dataset_manifest_ref": "eval/..\\dataset_manifest.csv"},
    )

    with pytest.raises(ValueError, match="dataset_manifest_ref must be a repo-relative path"):
        _run_main(
            module,
            [
                "--results",
                str(results_path),
                "--summary",
                str(summary_path),
                "--out-dir",
                str(tmp_path / "triad"),
            ],
        )


def test_export_triad_artifacts_fails_fast_on_non_object_case_entry(tmp_path: Path) -> None:
    module = _load_script_module()
    results_path, summary_path = _write_benchmark_payloads(
        tmp_path,
        include_synthesis=True,
        triad_available=True,
        triad_missing=[],
        summary_passed=True,
    )

    results_payload = json.loads(results_path.read_text(encoding="utf-8"))
    first_strategy_cases = results_payload["strategies"][0]["cases"]
    first_strategy_cases.append("invalid-case")
    results_path.write_text(json.dumps(results_payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match=r"results\.strategies\[two_stage_baseline\]\.cases\[1\]"):
        _run_main(
            module,
            [
                "--results",
                str(results_path),
                "--summary",
                str(summary_path),
                "--out-dir",
                str(tmp_path / "triad"),
            ],
        )
