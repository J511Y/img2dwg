from __future__ import annotations

# mypy: disable-error-code=import-untyped
import json
from pathlib import Path
from typing import Any

import pytest

from img2dwg.pipeline.benchmark import run_benchmark
from img2dwg.strategies.base import ConversionInput, ConversionOutput, ConversionStrategy
from img2dwg.strategies.registry import StrategyRegistry


class MetadataAwareStrategy(ConversionStrategy):
    name = "metadata_aware"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        consensus = conv_input.metadata.get("consensus_score")
        note = f"consensus_score:{consensus}" if consensus is not None else "consensus_score:none"
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=None,
            success=True,
            elapsed_ms=1.0,
            metrics={"iou": 0.5, "topology_f1": 0.5},
            notes=[note],
        )

    def timed_run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        return self.run(conv_input, output_dir)


def _registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register(MetadataAwareStrategy())
    return registry


def test_run_benchmark_matches_root_relative_manifest_key_for_absolute_image_path(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "images" / "nested" / "a.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"fake")

    absolute_image_path = image_path.resolve()
    key_candidates = {
        absolute_image_path: [
            ("absolute", absolute_image_path.as_posix()),
            ("root_relative", "nested/a.png"),
            ("name", "a.png"),
            ("stem", "a"),
        ]
    }

    result = run_benchmark(
        image_paths=[absolute_image_path],
        registry=_registry(),
        output_dir=tmp_path / "out",
        metadata_by_image={"nested/a.png": {"consensus_score": 0.77}},
        metadata_key_candidates_by_image=key_candidates,
    )

    case = result["strategies"][0]["cases"][0]
    assert case["notes"] == ["consensus_score:0.77"]

    stats = result["metadata_manifest"]
    assert stats["total_keys"] == 1
    assert stats["matched_keys"] == 1
    assert stats["unmatched_keys"] == 0
    assert stats["match_mode_counts"]["root_relative"] == 1


def test_run_benchmark_warns_for_unmatched_manifest_keys_and_records_summary_stats(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "images" / "nested" / "a.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"fake")

    absolute_image_path = image_path.resolve()
    key_candidates = {
        absolute_image_path: [
            ("absolute", absolute_image_path.as_posix()),
            ("root_relative", "nested/a.png"),
        ]
    }

    with pytest.warns(UserWarning, match="unmatched key"):
        result = run_benchmark(
            image_paths=[absolute_image_path],
            registry=_registry(),
            output_dir=tmp_path / "out-unmatched",
            metadata_by_image={
                "nested/a.png": {"consensus_score": 0.77},
                "orphan.png": {"consensus_score": 0.11},
            },
            metadata_key_candidates_by_image=key_candidates,
            metadata_warning_sample_size=3,
        )

    stats = result["metadata_manifest"]
    assert stats["total_keys"] == 2
    assert stats["matched_keys"] == 1
    assert stats["unmatched_keys"] == 1
    assert stats["unmatched_key_samples"] == ["orphan.png"]

    summary_payload = json.loads(
        (tmp_path / "out-unmatched" / "benchmark_summary.json").read_text(encoding="utf-8")
    )
    assert summary_payload["metadata_manifest"]["unmatched_keys"] == 1
    assert summary_payload["metadata_manifest"]["unmatched_key_samples"] == ["orphan.png"]


def test_run_benchmark_strict_metadata_manifest_raises_on_unmatched_key(tmp_path: Path) -> None:
    image_path = tmp_path / "images" / "a.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"fake")

    with pytest.raises(ValueError, match="strict-metadata-manifest"):
        run_benchmark(
            image_paths=[image_path.resolve()],
            registry=_registry(),
            output_dir=tmp_path / "out-strict",
            metadata_by_image={"orphan.png": {"consensus_score": 0.11}},
            strict_metadata_manifest=True,
        )


def test_run_benchmark_matches_relative_manifest_key_for_absolute_image_path(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "images" / "nested" / "a.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"fake")

    absolute_image_path = image_path.resolve()
    key_candidates = {
        absolute_image_path: [
            ("absolute", absolute_image_path.as_posix()),
            ("relative", "nested/a.png"),
            ("name", "a.png"),
        ]
    }

    result = run_benchmark(
        image_paths=[absolute_image_path],
        registry=_registry(),
        output_dir=tmp_path / "out-relative",
        metadata_by_image={"nested/a.png": {"consensus_score": 0.66}},
        metadata_key_candidates_by_image=key_candidates,
    )

    case = result["strategies"][0]["cases"][0]
    assert case["notes"] == ["consensus_score:0.66"]

    stats = result["metadata_manifest"]
    assert stats["matched_keys"] == 1
    assert stats["match_mode_counts"]["relative"] == 1


def test_run_benchmark_warns_and_skips_ambiguous_name_fallback_collision(tmp_path: Path) -> None:
    image_a = tmp_path / "images" / "x" / "a.png"
    image_b = tmp_path / "images" / "y" / "a.png"
    image_a.parent.mkdir(parents=True)
    image_b.parent.mkdir(parents=True)
    image_a.write_bytes(b"fake")
    image_b.write_bytes(b"fake")

    abs_a = image_a.resolve()
    abs_b = image_b.resolve()
    key_candidates: dict[Path, list[tuple[str, str]]] = {
        abs_a: [
            ("absolute", abs_a.as_posix()),
            ("root_relative", "x/a.png"),
            ("name", "a.png"),
        ],
        abs_b: [
            ("absolute", abs_b.as_posix()),
            ("root_relative", "y/a.png"),
            ("name", "a.png"),
        ],
    }

    with pytest.warns(UserWarning) as warnings_record:
        result = run_benchmark(
            image_paths=[abs_a, abs_b],
            registry=_registry(),
            output_dir=tmp_path / "out-collision",
            metadata_by_image={"a.png": {"consensus_score": 0.5}},
            metadata_key_candidates_by_image=key_candidates,
        )

    messages = "\n".join(str(item.message) for item in warnings_record)
    assert "ambiguous keys" in messages
    assert "unmatched key" in messages

    notes = [case["notes"] for case in result["strategies"][0]["cases"]]
    assert notes == [["consensus_score:none"], ["consensus_score:none"]]

    stats: dict[str, Any] = result["metadata_manifest"]
    assert stats["matched_keys"] == 0
    assert stats["unmatched_keys"] == 1
    assert stats["ambiguous_fallback_skipped"]["name"] == ["a.png"]
