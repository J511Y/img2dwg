from __future__ import annotations

from pathlib import Path
from typing import Any

import torch

from img2dwg.ved.config import VEDConfig  # type: ignore[import-untyped]
from img2dwg.ved.model import VEDModel  # type: ignore[import-untyped]


class _FakeTokenizer:
    bos_token_id = 11
    pad_token_id = 22
    eos_token_id = 33
    vocab_size = 777

    def save_pretrained(self, _path: str) -> None:
        return None


class _FakeEmb:
    def __init__(self) -> None:
        self.last_size: int | None = None

    def resize_token_embeddings(self, size: int) -> None:
        self.last_size = size

    def parameters(self) -> list[torch.Tensor]:
        return [torch.ones(3, 3)]


class _FakeModule:
    def parameters(self) -> list[torch.Tensor]:
        return [torch.ones(2, 2)]


class _FakeModel:
    def __init__(self) -> None:
        self.config = type("Cfg", (), {})()
        self.decoder = _FakeEmb()
        self.encoder = _FakeModule()
        self._params = [torch.ones(2, 2)]
        self.generate_kwargs: dict[str, Any] | None = None

    def parameters(self) -> list[torch.Tensor]:
        return self._params

    def generate(self, **kwargs: Any) -> torch.Tensor:
        self.generate_kwargs = kwargs
        return torch.tensor([[1, 2, 3]])


class _FakeVisionEncoderDecoderModel:
    @staticmethod
    def from_encoder_decoder_pretrained(_enc: str, _dec: str) -> _FakeModel:
        return _FakeModel()

    @staticmethod
    def from_pretrained(_model_path: Path) -> _FakeModel:
        return _FakeModel()


class _FakeImageProcessor:
    @staticmethod
    def from_pretrained(_name: str | Path) -> dict[str, str]:
        return {"ok": "yes"}


def test_generate_uses_config_default_max_length(monkeypatch: Any) -> None:
    monkeypatch.setattr("img2dwg.ved.model.AutoImageProcessor", _FakeImageProcessor)
    monkeypatch.setattr(
        "img2dwg.ved.model.VisionEncoderDecoderModel",
        _FakeVisionEncoderDecoderModel,
    )

    model = VEDModel(VEDConfig(max_length=123), _FakeTokenizer())
    out = model.generate(pixel_values=torch.zeros((1, 3, 4, 4)))

    assert out.shape == (1, 3)
    assert model.model.generate_kwargs is not None
    assert model.model.generate_kwargs["max_length"] == 123
    assert model.model.generate_kwargs["pad_token_id"] == 22
    assert model.model.generate_kwargs["eos_token_id"] == 33


def test_build_model_resizes_decoder_embeddings(monkeypatch: Any) -> None:
    monkeypatch.setattr("img2dwg.ved.model.AutoImageProcessor", _FakeImageProcessor)
    monkeypatch.setattr(
        "img2dwg.ved.model.VisionEncoderDecoderModel",
        _FakeVisionEncoderDecoderModel,
    )

    model = VEDModel(VEDConfig(), _FakeTokenizer())

    assert model.model.decoder.last_size == 777


def test_from_pretrained_wires_components(monkeypatch: Any, tmp_path: Path) -> None:
    fake_tokenizer = _FakeTokenizer()

    class _FakeCADTokenizer:
        @staticmethod
        def from_pretrained(_model_path: str) -> _FakeTokenizer:
            return fake_tokenizer

    monkeypatch.setattr("img2dwg.ved.model.CADTokenizer", _FakeCADTokenizer)
    monkeypatch.setattr("img2dwg.ved.model.AutoImageProcessor", _FakeImageProcessor)
    monkeypatch.setattr(
        "img2dwg.ved.model.VisionEncoderDecoderModel",
        _FakeVisionEncoderDecoderModel,
    )

    loaded = VEDModel.from_pretrained(tmp_path)

    assert loaded.tokenizer is fake_tokenizer
    assert loaded.image_processor == {"ok": "yes"}
    assert isinstance(loaded.model, _FakeModel)
