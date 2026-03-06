from __future__ import annotations

import json
from pathlib import Path

from img2dwg.ved.config import (  # type: ignore[import-untyped]
    TRAINING_METADATA_FILENAME,
    VEDConfig,
    load_training_max_length,
    resolve_inference_max_length,
    write_training_metadata,
)


def test_write_and_load_training_metadata_roundtrip(tmp_path: Path) -> None:
    config = VEDConfig(max_length=2048, filter_max_tokens=1024)

    metadata_path = write_training_metadata(config, tmp_path)

    assert metadata_path.name == TRAINING_METADATA_FILENAME
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["max_length"] == 2048
    assert payload["filter_max_tokens"] == 1024
    assert load_training_max_length(tmp_path) == 2048


def test_resolve_inference_max_length_prefers_cli_override(tmp_path: Path) -> None:
    config = VEDConfig(max_length=4096)
    write_training_metadata(config, tmp_path)

    resolved = resolve_inference_max_length(tmp_path, cli_max_length=1024)

    assert resolved.value == 1024
    assert resolved.source == "cli-override"
    assert resolved.training_value == 4096
    assert any("overrides checkpoint" in warning for warning in resolved.warnings)
