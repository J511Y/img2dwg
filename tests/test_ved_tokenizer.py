from __future__ import annotations

from typing import Any

import pytest

from img2dwg.ved.tokenizer import CADTokenizer


class FakeTokenizer:
    def __init__(self) -> None:
        self.pad_token = None
        self.pad_token_id = None
        self.eos_token = "<eos>"
        self.eos_token_id = 9
        self.bos_token_id = 7
        self.added_tokens: list[str] = []
        self.saved_to: str | None = None

    def add_tokens(self, tokens: list[str]) -> int:
        self.added_tokens.extend(tokens)
        return len(tokens)

    def __call__(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"args": args, "kwargs": kwargs}

    def encode(self, text: str, **kwargs: Any) -> list[int]:
        del kwargs
        return [len(text)]

    def decode(self, token_ids: list[int], **kwargs: Any) -> str:
        del kwargs
        return f"decoded:{sum(token_ids)}"

    def batch_decode(self, token_ids_list: list[list[int]], **kwargs: Any) -> list[str]:
        del kwargs
        return [str(sum(ids)) for ids in token_ids_list]

    def save_pretrained(self, save_directory: str) -> None:
        self.saved_to = save_directory

    def __len__(self) -> int:
        return 1234


def test_cad_tokenizer_initialization_and_wrappers(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeTokenizer()
    monkeypatch.setattr("img2dwg.ved.tokenizer.AutoTokenizer.from_pretrained", lambda _: fake)

    tok = CADTokenizer(base_model="dummy", add_special_tokens=True)

    assert fake.pad_token == fake.eos_token
    assert fake.pad_token_id == fake.eos_token_id
    assert len(fake.added_tokens) == len(CADTokenizer.CAD_TOKENS)
    assert tok.encode("abc") == [3]
    assert tok.decode([1, 2, 3]) == "decoded:6"
    assert tok.batch_decode([[1], [2, 3]]) == ["1", "5"]
    assert tok.vocab_size == 1234
    assert tok.pad_token_id == 9
    assert tok.eos_token_id == 9
    assert tok.bos_token_id == 7

    tok.save_pretrained("out-dir")
    assert fake.saved_to == "out-dir"


def test_cad_tokenizer_from_pretrained(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeTokenizer()
    monkeypatch.setattr("img2dwg.ved.tokenizer.AutoTokenizer.from_pretrained", lambda _: fake)

    tok = CADTokenizer.from_pretrained("saved-path")

    assert tok.tokenizer is fake
