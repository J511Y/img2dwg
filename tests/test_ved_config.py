from __future__ import annotations

from pathlib import Path

from img2dwg.ved.config import InferenceConfig, VEDConfig


def test_ved_config_converts_paths() -> None:
    cfg = VEDConfig(data_dir="out", output_dir="checkpoints")
    assert isinstance(cfg.data_dir, Path)
    assert isinstance(cfg.output_dir, Path)
    assert str(cfg.data_dir) == "out"


def test_inference_config_converts_model_path() -> None:
    cfg = InferenceConfig(model_path="saved-model")
    assert isinstance(cfg.model_path, Path)
    assert str(cfg.model_path) == "saved-model"
