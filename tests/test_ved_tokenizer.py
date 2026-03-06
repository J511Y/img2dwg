from __future__ import annotations

from typing import Any

from img2dwg.ved.tokenizer import CADTokenizer  # type: ignore[import-untyped]


class _FakeTokenizer:
    def __init__(
        self,
        pad_token: str | None = None,
        pad_token_id: int | None = None,
        eos_token: str = "<eos>",
        eos_token_id: int = 99,
    ) -> None:
        self.pad_token = pad_token
        self.pad_token_id = pad_token_id
        self.eos_token = eos_token
        self.eos_token_id = eos_token_id
        self.bos_token_id = 1
        self.added_tokens: list[str] = []
        self.saved_to: str | None = None

    def add_tokens(self, tokens: list[str]) -> int:
        self.added_tokens.extend(tokens)
        return len(tokens)

    def encode(self, text: str, **kwargs: Any) -> list[int]:
        return [len(text)]

    def decode(self, token_ids: list[int], **kwargs: Any) -> str:
        return f"decoded:{token_ids}"

    def __call__(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"args": args, "kwargs": kwargs}

    def batch_decode(self, token_ids_list: list[list[int]], **kwargs: Any) -> list[str]:
        return [str(x) for x in token_ids_list]

    def save_pretrained(self, save_directory: str) -> str:
        self.saved_to = save_directory
        return save_directory

    def __len__(self) -> int:
        return 1000 + len(self.added_tokens)


class _FakeAutoTokenizer:
    @staticmethod
    def from_pretrained(_model_name: str) -> _FakeTokenizer:
        return _FakeTokenizer()


def test_cad_tokenizer_sets_pad_token_and_adds_cad_tokens(monkeypatch: Any) -> None:
    monkeypatch.setattr("img2dwg.ved.tokenizer.AutoTokenizer", _FakeAutoTokenizer)

    tokenizer = CADTokenizer(base_model="fake", add_special_tokens=True)

    assert tokenizer.pad_token_id == tokenizer.eos_token_id == 99
    assert tokenizer.vocab_size == 1000 + len(CADTokenizer.CAD_TOKENS)


def test_cad_tokenizer_wrapper_methods(monkeypatch: Any) -> None:
    monkeypatch.setattr("img2dwg.ved.tokenizer.AutoTokenizer", _FakeAutoTokenizer)

    tokenizer = CADTokenizer(base_model="fake", add_special_tokens=False)

    assert tokenizer.encode("abc") == [3]
    assert tokenizer.decode([1, 2]) == "decoded:[1, 2]"
    assert tokenizer.batch_encode(["a", "b"], truncation=True)["kwargs"]["truncation"] is True
    assert tokenizer.batch_decode([[1], [2]]) == ["[1]", "[2]"]


def test_cad_tokenizer_save_and_from_pretrained(monkeypatch: Any, tmp_path: Any) -> None:
    fake = _FakeTokenizer()

    class _LocalAutoTokenizer:
        @staticmethod
        def from_pretrained(_model_name: str) -> _FakeTokenizer:
            return fake

    monkeypatch.setattr("img2dwg.ved.tokenizer.AutoTokenizer", _LocalAutoTokenizer)

    tokenizer = CADTokenizer(base_model="fake", add_special_tokens=False)
    tokenizer.save_pretrained(str(tmp_path))

    reloaded = CADTokenizer.from_pretrained(str(tmp_path))

    assert fake.saved_to == str(tmp_path)
    assert reloaded.tokenizer is fake
