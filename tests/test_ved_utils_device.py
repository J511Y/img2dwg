from __future__ import annotations

from typing import Any

from img2dwg.ved.utils import (  # type: ignore[import-untyped]
    get_device,
    print_gpu_memory,
)


def test_get_device_returns_cpu_when_cuda_unavailable(monkeypatch: Any) -> None:
    monkeypatch.setattr("img2dwg.ved.utils.torch.cuda.is_available", lambda: False)

    assert get_device() == "cpu"


def test_print_gpu_memory_outputs_expected_message(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr("img2dwg.ved.utils.torch.cuda.is_available", lambda: True)
    monkeypatch.setattr("img2dwg.ved.utils.torch.cuda.memory_allocated", lambda: float(2 * 1024**3))
    monkeypatch.setattr("img2dwg.ved.utils.torch.cuda.memory_reserved", lambda: float(3 * 1024**3))

    print_gpu_memory()
    captured = capsys.readouterr()

    assert "GPU Memory:" in captured.out
    assert "2.00GB allocated" in captured.out
    assert "3.00GB reserved" in captured.out
