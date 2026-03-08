from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import ezdxf

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_grid_artifact_regression.py"


def _load_script_module() -> ModuleType:
    module_name = "run_grid_artifact_regression_script_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load run_grid_artifact_regression.py")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_grid_like_dxf(path: Path) -> None:
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()

    # dense axis-aligned grid-like pattern (>=8 lines)
    msp.add_line((0, 0), (100, 0))
    msp.add_line((100, 0), (100, 60))
    msp.add_line((100, 60), (0, 60))
    msp.add_line((0, 60), (0, 0))
    msp.add_line((0, 20), (100, 20))
    msp.add_line((0, 40), (100, 40))
    msp.add_line((33, 0), (33, 60))
    msp.add_line((66, 0), (66, 60))

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)


def _write_sparse_axis_aligned_dxf(path: Path) -> None:
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()

    # 6 axis-aligned lines (below min_line_count_for_grid_pattern=8)
    msp.add_line((0, 0), (100, 0))
    msp.add_line((100, 0), (100, 60))
    msp.add_line((100, 60), (0, 60))
    msp.add_line((0, 60), (0, 0))
    msp.add_line((0, 30), (100, 30))
    msp.add_line((50, 0), (50, 60))

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)


def _write_mixed_entity_dxf(path: Path) -> None:
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()

    for idx in range(12):
        x = idx * 10
        msp.add_line((x, 0), (x + 5, 7))
    msp.add_circle((200, 200), radius=25)
    msp.add_text("ROOM")

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)


def test_evaluate_case_flags_grid_like_low_diversity(tmp_path: Path) -> None:
    module = _load_script_module()

    dxf_path = tmp_path / "grid_like.dxf"
    _write_grid_like_dxf(dxf_path)

    diagnostics = module.analyze_dxf(str(dxf_path))
    thresholds = module.RegressionThresholds(min_entities=10, min_unique_entity_types=2)
    flags = module.evaluate_case(diagnostics, thresholds)

    assert "low_entity_count" in flags
    assert "low_entity_diversity" in flags
    assert "suspicious_grid_pattern" in flags


def test_evaluate_case_does_not_flag_sparse_axis_aligned_as_grid(tmp_path: Path) -> None:
    module = _load_script_module()

    dxf_path = tmp_path / "sparse_axis_aligned.dxf"
    _write_sparse_axis_aligned_dxf(dxf_path)

    diagnostics = module.analyze_dxf(str(dxf_path))
    thresholds = module.RegressionThresholds(min_entities=6, min_unique_entity_types=1)
    flags = module.evaluate_case(diagnostics, thresholds)

    assert "suspicious_grid_pattern" not in flags


def test_evaluate_case_passes_on_mixed_entities(tmp_path: Path) -> None:
    module = _load_script_module()

    dxf_path = tmp_path / "mixed.dxf"
    _write_mixed_entity_dxf(dxf_path)

    diagnostics = module.analyze_dxf(str(dxf_path))
    thresholds = module.RegressionThresholds(min_entities=10, min_unique_entity_types=2)
    flags = module.evaluate_case(diagnostics, thresholds)

    assert flags == []


def test_regression_threshold_defaults_are_tuned_for_grid_baseline() -> None:
    module = _load_script_module()

    thresholds = module.RegressionThresholds()

    assert thresholds.min_entities == 6
    assert thresholds.min_unique_entity_types == 1
    assert thresholds.min_line_count_for_grid_pattern == 8


def test_analyze_benchmark_results_summarizes_failures(tmp_path: Path) -> None:
    module = _load_script_module()

    bad_path = tmp_path / "bad.dxf"
    _write_grid_like_dxf(bad_path)

    good_path = tmp_path / "good.dxf"
    _write_mixed_entity_dxf(good_path)

    benchmark_results = {
        "strategies": [
            {
                "strategy_name": "hybrid_mvp",
                "cases": [
                    {
                        "case_id": "case_001",
                        "image_path": "a.png",
                        "dxf_path": str(bad_path),
                    },
                    {
                        "case_id": "case_002",
                        "image_path": "b.png",
                        "dxf_path": str(good_path),
                    },
                ],
            }
        ]
    }

    report = module.analyze_benchmark_results(
        benchmark_results,
        thresholds=module.RegressionThresholds(min_entities=10, min_unique_entity_types=2),
    )

    previous = {
        "summary": {
            "failed_cases": 2,
            "failures_by_reason": {
                "suspicious_grid_pattern": 1,
                "low_entity_count": 1,
                "low_entity_diversity": 1,
            },
        },
        "strategy_diagnostics": {
            "hybrid_mvp": {
                "avg_axis_margin_score": 10.0,
                "avg_axis_aligned_ratio": 0.8,
                "avg_axis_margin_to_grid_threshold": 0.1,
            }
        },
    }
    report = module._attach_previous_delta(report, previous)

    assert report["summary"]["total_cases"] == 2
    assert report["summary"]["failed_cases"] == 1
    assert report["summary"]["passed_cases"] == 1
    assert "suspicious_grid_pattern" in report["summary"]["failures_by_reason"]
    assert "hybrid_mvp" in report["strategy_failures_by_reason"]
    assert "hybrid_mvp" in report["strategy_diagnostics"]
    assert "avg_axis_margin_to_grid_threshold" in report["strategy_diagnostics"]["hybrid_mvp"]
    assert "avg_axis_margin_score" in report["strategy_diagnostics"]["hybrid_mvp"]
    assert "avg_unique_x_count" in report["strategy_diagnostics"]["hybrid_mvp"]
    assert "avg_unique_y_count" in report["strategy_diagnostics"]["hybrid_mvp"]
    assert "max_axis_aligned_ratio" in report["strategy_diagnostics"]["hybrid_mvp"]
    assert "max_axis_margin_to_grid_threshold" in report["strategy_diagnostics"]["hybrid_mvp"]
    assert "p95_axis_aligned_ratio" in report["strategy_diagnostics"]["hybrid_mvp"]
    assert "p95_axis_margin_to_grid_threshold" in report["strategy_diagnostics"]["hybrid_mvp"]
    assert "min_axis_aligned_ratio" in report["strategy_diagnostics"]["hybrid_mvp"]
    assert "min_axis_margin_to_grid_threshold" in report["strategy_diagnostics"]["hybrid_mvp"]
    assert "std_axis_aligned_ratio" in report["strategy_diagnostics"]["hybrid_mvp"]
    assert "delta_vs_previous" in report
    assert report["delta_vs_previous"]["failed_cases"]["previous"] == 2
    assert report["delta_vs_previous"]["hybrid_avg_axis_margin_score"]["previous"] == 10.0
    assert report["delta_vs_previous"]["hybrid_avg_axis_aligned_ratio"]["previous"] == 0.8
    assert report["delta_vs_previous"]["hybrid_avg_axis_margin_to_grid_threshold"]["previous"] == 0.1
