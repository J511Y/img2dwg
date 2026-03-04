"""VED 학습/추론 max_length 정책 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest

from img2dwg.ved.config import (
    MAX_LENGTH_HARD_LIMIT,
    VEDConfig,
    load_training_max_length,
    resolve_inference_max_length,
    write_training_metadata,
)


def test_write_and_load_training_max_length_metadata(tmp_path: Path) -> None:
    config = VEDConfig(max_length=4096, output_dir=tmp_path)

    metadata_path = write_training_metadata(config, tmp_path / "best")

    assert metadata_path.exists()
    assert load_training_max_length(tmp_path / "best") == 4096


def test_resolve_uses_checkpoint_metadata_by_default(tmp_path: Path) -> None:
    config = VEDConfig(max_length=8192, output_dir=tmp_path)
    checkpoint_dir = tmp_path / "best"
    write_training_metadata(config, checkpoint_dir)

    resolved = resolve_inference_max_length(checkpoint_dir, cli_max_length=None)

    assert resolved.value == 8192
    assert resolved.source == "checkpoint-metadata"
    assert resolved.training_value == 8192
    assert resolved.warnings == []


def test_resolve_honors_cli_override_with_warning(tmp_path: Path) -> None:
    config = VEDConfig(max_length=8192, output_dir=tmp_path)
    checkpoint_dir = tmp_path / "best"
    write_training_metadata(config, checkpoint_dir)

    resolved = resolve_inference_max_length(checkpoint_dir, cli_max_length=4096)

    assert resolved.value == 4096
    assert resolved.source == "cli-override"
    assert any("overrides checkpoint" in message for message in resolved.warnings)


def test_resolve_fallbacks_to_default_when_metadata_missing(tmp_path: Path) -> None:
    resolved = resolve_inference_max_length(
        model_path=tmp_path / "missing-checkpoint",
        cli_max_length=None,
        default_training_max_length=2048,
    )

    assert resolved.value == 2048
    assert resolved.source == "ved-default"
    assert any("metadata not found" in message for message in resolved.warnings)


@pytest.mark.parametrize("invalid_value", [0, -1, MAX_LENGTH_HARD_LIMIT + 1])
def test_resolve_rejects_invalid_max_length(tmp_path: Path, invalid_value: int) -> None:
    with pytest.raises(ValueError):
        resolve_inference_max_length(
            model_path=tmp_path,
            cli_max_length=invalid_value,
        )
