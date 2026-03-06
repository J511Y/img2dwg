"""Smoke tests to keep scoped coverage gate representative for issue #6."""

from __future__ import annotations

import base64
import importlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import torch
from PIL import Image


class _FakeModelspace:
    """Minimal ezdxf modelspace double for converter smoke coverage."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def add_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        dxfattribs: dict[str, Any],
    ) -> None:
        self.calls.append(("line", (start, end, dxfattribs)))

    def add_lwpolyline(
        self,
        points: list[tuple[float, float]],
        close: bool,
        dxfattribs: dict[str, Any],
    ) -> None:
        self.calls.append(("polyline", (points, close, dxfattribs)))

    def add_circle(
        self,
        center: tuple[float, float],
        radius: float,
        dxfattribs: dict[str, Any],
    ) -> None:
        self.calls.append(("circle", (center, radius, dxfattribs)))

    def add_arc(
        self,
        center: tuple[float, float],
        radius: float,
        start_angle: float,
        end_angle: float,
        dxfattribs: dict[str, Any],
    ) -> None:
        self.calls.append(("arc", (center, radius, start_angle, end_angle, dxfattribs)))

    def add_text(self, content: str, dxfattribs: dict[str, Any]) -> _FakeTextEntity:
        self.calls.append(("text", (content, dxfattribs)))
        return _FakeTextEntity(self.calls)


class _FakeTextEntity:
    def __init__(self, calls: list[tuple[str, Any]]) -> None:
        self._calls = calls

    def set_placement(self, position: tuple[float, float], align: Any) -> _FakeTextEntity:
        self._calls.append(("text-placement", (position, align)))
        return self


class _DummyTokenizer:
    def __call__(
        self,
        text: str,
        max_length: int,
        padding: str,
        truncation: bool,
        return_tensors: str,
    ) -> dict[str, torch.Tensor]:
        del text, padding, truncation, return_tensors
        return {"input_ids": torch.ones((1, max_length), dtype=torch.long)}


class _FakeImageProcessor:
    def __init__(self) -> None:
        self.saved_to: Path | None = None

    def save_pretrained(self, save_directory: Path) -> None:
        self.saved_to = Path(save_directory)


class _FakeDecoder:
    def __init__(self) -> None:
        self.resized_to: int | None = None

    def resize_token_embeddings(self, size: int) -> None:
        self.resized_to = size

    def parameters(self) -> list[torch.nn.Parameter]:
        return [torch.nn.Parameter(torch.ones(1))]


class _FakeEncoder:
    def parameters(self) -> list[torch.nn.Parameter]:
        return [torch.nn.Parameter(torch.ones(1))]


class _FakeVisionModel:
    def __init__(self) -> None:
        self.config = SimpleNamespace(
            decoder_start_token_id=None,
            pad_token_id=None,
            eos_token_id=None,
        )
        self.decoder = _FakeDecoder()
        self.encoder = _FakeEncoder()
        self.saved_to: Path | None = None
        self.forward_calls: list[dict[str, Any]] = []
        self.generate_calls: list[dict[str, Any]] = []
        self.to_device: str | None = None
        self.mode = "eval"

    def parameters(self) -> list[torch.nn.Parameter]:
        return [torch.nn.Parameter(torch.ones(1)), torch.nn.Parameter(torch.ones(1))]

    def __call__(self, **kwargs: Any) -> SimpleNamespace:
        self.forward_calls.append(kwargs)
        return SimpleNamespace(loss=torch.tensor(0.5), logits=torch.zeros(1, 2, 3))

    def generate(self, **kwargs: Any) -> torch.Tensor:
        self.generate_calls.append(kwargs)
        return torch.tensor([[1, 2, 3]])

    def save_pretrained(self, save_directory: Path) -> None:
        self.saved_to = Path(save_directory)

    def to(self, device: str) -> _FakeVisionModel:
        self.to_device = device
        return self

    def train(self) -> None:
        self.mode = "train"

    def eval(self) -> None:
        self.mode = "eval"


class _FakeTokenizer:
    bos_token_id = 11
    pad_token_id = 22
    eos_token_id = 33
    vocab_size = 44

    def __init__(self) -> None:
        self.saved_to: str | None = None

    def save_pretrained(self, save_directory: str) -> None:
        self.saved_to = save_directory


def _write_jsonl(path: Path, image_url: str, content: str = "{}") -> None:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [{"type": "image_url", "image_url": {"url": image_url}}],
            },
            {"role": "assistant", "content": content},
        ]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def _png_bytes() -> bytes:
    image = Image.new("RGB", (4, 4), (255, 255, 255))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_scoped_coverage_smoke_for_core_modules() -> None:
    """Exercise core-module entrypoints so changed-file coverage cannot regress."""
    schema: Any = importlib.import_module("img2dwg.models.schema")
    converter_module: Any = importlib.import_module("img2dwg.models.converter")
    metrics: Any = importlib.import_module("img2dwg.ved.metrics")
    tokenizer: Any = importlib.import_module("img2dwg.ved.tokenizer")
    ved_utils: Any = importlib.import_module("img2dwg.ved.utils")

    point = schema.Point2D.from_dict({"x": 1.0, "y": 2.0})
    doc = schema.CADDocument.from_dict(
        {
            "metadata": {"filename": "demo.png", "type": "plan", "entity_count": 0},
            "entities": [],
        }
    )
    metric_values = metrics.compute_metrics(
        predictions=['{"entities": [{"type": "LINE"}]}'],
        references=['{"entities": [{"type": "LINE"}]}'],
    )

    modelspace = _FakeModelspace()
    converter_instance = converter_module.JSONToDWGConverter()
    converter_instance._add_entity_to_modelspace(
        modelspace,
        {
            "type": "line",
            "start": {"x": 0.0, "y": 0.0},
            "end": {"x": 1.0, "y": 1.0},
            "layer": "0",
            "color": 7,
            "linetype": "BYLAYER",
        },
    )
    converter_instance._add_entity_to_modelspace(
        modelspace,
        {
            "type": "polyline",
            "points": [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 1.0}],
            "closed": True,
        },
    )
    converter_instance._add_entity_to_modelspace(
        modelspace,
        {
            "type": "circle",
            "center": {"x": 1.0, "y": 1.0},
            "radius": 2.0,
        },
    )
    converter_instance._add_entity_to_modelspace(
        modelspace,
        {
            "type": "arc",
            "center": {"x": 1.0, "y": 1.0},
            "radius": 2.0,
            "start_angle": 0.0,
            "end_angle": 90.0,
        },
    )
    converter_instance._add_entity_to_modelspace(
        modelspace,
        {
            "type": "text",
            "position": {"x": 1.0, "y": 1.0},
            "content": "hello",
            "height": 2.5,
            "rotation": 0.0,
        },
    )
    converter_instance._add_entity_to_modelspace(modelspace, {"type": "unknown"})

    assert point.to_dict() == {"x": 1.0, "y": 2.0}
    assert doc.to_dict()["metadata"]["filename"] == "demo.png"
    assert metric_values["parse_success_rate"] == 1.0
    assert metric_values["exact_match"] == 1.0
    assert ved_utils.validate_json('{"ok": true}')
    assert ved_utils.parse_json_safe("{broken") == {}
    assert ved_utils.format_time(65) == "1m 5s"
    assert ved_utils.get_device() in {"cuda", "cpu"}
    assert tokenizer.CADTokenizer.CAD_TOKENS
    assert modelspace.calls and modelspace.calls[0][0] == "line"


def test_scoped_coverage_smoke_for_ved_config_and_dataset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise config/dataset code paths that affect scoped fail-under totals."""
    config_module: Any = importlib.import_module("img2dwg.ved.config")
    dataset_module: Any = importlib.import_module("img2dwg.ved.dataset")

    cfg = config_module.VEDConfig(data_dir="out", output_dir="checkpoints")
    infer_cfg = config_module.InferenceConfig(model_path="saved-model")
    assert isinstance(cfg.data_dir, Path)
    assert isinstance(infer_cfg.model_path, Path)

    local_image = tmp_path / "img.png"
    Image.new("RGB", (2, 2), (0, 0, 0)).save(local_image)

    local_jsonl = tmp_path / "samples-local.jsonl"
    _write_jsonl(local_jsonl, "img.png")

    local_ds = dataset_module.ImageToJSONDataset(
        jsonl_path=local_jsonl,
        tokenizer=_DummyTokenizer(),
        image_size=16,
        max_length=8,
        image_dir=tmp_path,
    )
    local_sample = local_ds[0]
    assert local_sample["pixel_values"].shape == (3, 16, 16)
    assert local_sample["labels"].shape == (8,)

    encoded = base64.b64encode(_png_bytes()).decode("ascii")
    data_jsonl = tmp_path / "samples-data.jsonl"
    _write_jsonl(data_jsonl, f"data:image/png;base64,{encoded}")
    data_ds = dataset_module.ImageToJSONDataset(
        jsonl_path=data_jsonl,
        tokenizer=_DummyTokenizer(),
        image_size=8,
        max_length=4,
    )
    assert data_ds[0]["pixel_values"].shape == (3, 8, 8)

    class _Resp:
        def __init__(self, content: bytes) -> None:
            self.content = content

    http_jsonl = tmp_path / "samples-http.jsonl"
    _write_jsonl(http_jsonl, "https://example.com/image.png")

    monkeypatch.setattr("requests.get", lambda _: _Resp(_png_bytes()))
    http_ds = dataset_module.ImageToJSONDataset(
        jsonl_path=http_jsonl,
        tokenizer=_DummyTokenizer(),
        image_size=8,
        max_length=4,
    )
    assert http_ds[0]["pixel_values"].shape == (3, 8, 8)

    def _raise_timeout(url: str) -> None:
        del url
        raise RuntimeError("timeout")

    monkeypatch.setattr("requests.get", _raise_timeout)
    fallback = http_ds[0]["pixel_values"]
    assert float(fallback.abs().sum().item()) == 0.0

    collated = dataset_module.collate_fn(
        [
            {"pixel_values": torch.zeros(3, 8, 8), "labels": torch.ones(4, dtype=torch.long)},
            {"pixel_values": torch.ones(3, 8, 8), "labels": torch.zeros(4, dtype=torch.long)},
        ]
    )
    assert collated["pixel_values"].shape == (2, 3, 8, 8)
    assert collated["labels"].shape == (2, 4)


def test_scoped_coverage_smoke_for_ved_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Exercise VED model wrapper build/generate/save/load lifecycle."""
    model_module: Any = importlib.import_module("img2dwg.ved.model")
    config_module: Any = importlib.import_module("img2dwg.ved.config")

    fake_image_processor = _FakeImageProcessor()
    fake_model = _FakeVisionModel()

    monkeypatch.setattr(
        "img2dwg.ved.model.AutoImageProcessor.from_pretrained",
        lambda _: fake_image_processor,
    )
    monkeypatch.setattr(
        "img2dwg.ved.model.VisionEncoderDecoderModel.from_encoder_decoder_pretrained",
        lambda *_: fake_model,
    )

    cfg = config_module.VEDConfig(max_length=128)
    tokenizer = _FakeTokenizer()

    model = model_module.VEDModel(config=cfg, tokenizer=tokenizer)

    assert fake_model.config.decoder_start_token_id == tokenizer.bos_token_id
    assert fake_model.config.pad_token_id == tokenizer.pad_token_id
    assert fake_model.config.eos_token_id == tokenizer.eos_token_id
    assert fake_model.decoder.resized_to == tokenizer.vocab_size

    outputs = model.forward(
        pixel_values=torch.zeros(1, 3, 16, 16),
        labels=torch.ones(1, 3, dtype=torch.long),
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

    loaded_tokenizer = _FakeTokenizer()
    loaded_image_processor = _FakeImageProcessor()
    loaded_inner = _FakeVisionModel()

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

    loaded = model_module.VEDModel.from_pretrained(save_dir)
    assert loaded.model is loaded_inner

    loaded.to("cpu")
    assert loaded_inner.to_device == "cpu"

    loaded.train()
    assert loaded_inner.mode == "train"

    loaded.eval()
    assert loaded_inner.mode == "eval"
