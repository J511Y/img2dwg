from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import torch

from img2dwg.ved.config import VEDConfig
from img2dwg.ved.model import VEDModel


class FakeImageProcessor:
    def __init__(self) -> None:
        self.saved_to: Path | None = None

    def save_pretrained(self, save_directory: Path) -> None:
        self.saved_to = Path(save_directory)


class FakeDecoder:
    def __init__(self) -> None:
        self.resized_to: int | None = None

    def resize_token_embeddings(self, size: int) -> None:
        self.resized_to = size

    def parameters(self):
        return [torch.nn.Parameter(torch.ones(1))]


class FakeEncoder:
    def parameters(self):
        return [torch.nn.Parameter(torch.ones(1))]


class FakeVisionModel:
    def __init__(self) -> None:
        self.config = SimpleNamespace(
            decoder_start_token_id=None,
            pad_token_id=None,
            eos_token_id=None,
        )
        self.decoder = FakeDecoder()
        self.encoder = FakeEncoder()
        self.saved_to: Path | None = None
        self.forward_calls: list[dict[str, Any]] = []
        self.generate_calls: list[dict[str, Any]] = []
        self.to_device: str | None = None
        self.mode = "eval"

    def parameters(self):
        return [torch.nn.Parameter(torch.ones(1)), torch.nn.Parameter(torch.ones(1))]

    def __call__(self, **kwargs: Any) -> SimpleNamespace:
        self.forward_calls.append(kwargs)
        return SimpleNamespace(loss=torch.tensor(0.5), logits=torch.zeros(1, 2, 3))

    def generate(self, **kwargs: Any) -> torch.Tensor:
        self.generate_calls.append(kwargs)
        return torch.tensor([[1, 2, 3]])

    def save_pretrained(self, save_directory: Path) -> None:
        self.saved_to = Path(save_directory)

    def to(self, device: str):
        self.to_device = device
        return self

    def train(self) -> None:
        self.mode = "train"

    def eval(self) -> None:
        self.mode = "eval"


class FakeTokenizer:
    bos_token_id = 11
    pad_token_id = 22
    eos_token_id = 33
    vocab_size = 44

    def __init__(self) -> None:
        self.saved_to: str | None = None

    def save_pretrained(self, save_directory: str) -> None:
        self.saved_to = save_directory


def test_ved_model_build_forward_generate_save_and_load(monkeypatch, tmp_path: Path) -> None:
    fake_image_processor = FakeImageProcessor()
    fake_model = FakeVisionModel()

    monkeypatch.setattr(
        "img2dwg.ved.model.AutoImageProcessor.from_pretrained",
        lambda _: fake_image_processor,
    )
    monkeypatch.setattr(
        "img2dwg.ved.model.VisionEncoderDecoderModel.from_encoder_decoder_pretrained",
        lambda *_: fake_model,
    )

    cfg = VEDConfig(max_length=128)
    tokenizer = FakeTokenizer()

    model = VEDModel(config=cfg, tokenizer=tokenizer)

    assert fake_model.config.decoder_start_token_id == tokenizer.bos_token_id
    assert fake_model.config.pad_token_id == tokenizer.pad_token_id
    assert fake_model.config.eos_token_id == tokenizer.eos_token_id
    assert fake_model.decoder.resized_to == tokenizer.vocab_size

    outputs = model.forward(
        pixel_values=torch.zeros(1, 3, 16, 16), labels=torch.ones(1, 3, dtype=torch.long)
    )
    assert float(outputs.loss) == 0.5

    generated = model.generate(pixel_values=torch.zeros(1, 3, 16, 16))
    assert generated.shape == (1, 3)
    assert fake_model.generate_calls[-1]["max_length"] == 128

    explicit = model.generate(pixel_values=torch.zeros(1, 3, 16, 16), max_length=16)
    assert explicit.shape == (1, 3)
    assert fake_model.generate_calls[-1]["max_length"] == 16

    save_dir = tmp_path / "saved"
    model.save_pretrained(save_dir)
    assert fake_model.saved_to == save_dir
    assert tokenizer.saved_to == str(save_dir)
    assert fake_image_processor.saved_to == save_dir

    # load from pretrained path
    loaded_tokenizer = FakeTokenizer()
    loaded_image_processor = FakeImageProcessor()
    loaded_inner = FakeVisionModel()

    monkeypatch.setattr(
        "img2dwg.ved.model.CADTokenizer.from_pretrained",
        lambda _: loaded_tokenizer,
    )
    monkeypatch.setattr(
        "img2dwg.ved.model.AutoImageProcessor.from_pretrained",
        lambda _: loaded_image_processor,
    )
    monkeypatch.setattr(
        "img2dwg.ved.model.VisionEncoderDecoderModel.from_pretrained",
        lambda _: loaded_inner,
    )

    loaded = VEDModel.from_pretrained(save_dir)
    assert loaded.model is loaded_inner

    loaded.to("cpu")
    assert loaded_inner.to_device == "cpu"

    loaded.train()
    assert loaded_inner.mode == "train"

    loaded.eval()
    assert loaded_inner.mode == "eval"
