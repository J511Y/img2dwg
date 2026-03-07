from __future__ import annotations

from typing import Any

from img2dwg.ved.utils import set_seed  # type: ignore[import-untyped]


def test_set_seed_configures_rng_and_cudnn(monkeypatch: Any) -> None:
    calls: dict[str, int | bool | None] = {
        "random": None,
        "numpy": None,
        "torch": None,
        "cuda": None,
        "deterministic": None,
        "benchmark": None,
    }

    monkeypatch.setattr("img2dwg.ved.utils.random.seed", lambda v: calls.__setitem__("random", v))
    monkeypatch.setattr("img2dwg.ved.utils.np.random.seed", lambda v: calls.__setitem__("numpy", v))
    monkeypatch.setattr(
        "img2dwg.ved.utils.torch.manual_seed", lambda v: calls.__setitem__("torch", v)
    )
    monkeypatch.setattr(
        "img2dwg.ved.utils.torch.cuda.manual_seed_all",
        lambda v: calls.__setitem__("cuda", v),
    )

    class _FakeCuDNN:
        deterministic = False
        benchmark = True

    monkeypatch.setattr("img2dwg.ved.utils.torch.backends.cudnn", _FakeCuDNN)

    set_seed(42)

    assert calls["random"] == 42
    assert calls["numpy"] == 42
    assert calls["torch"] == 42
    assert calls["cuda"] == 42
    assert _FakeCuDNN.deterministic is True
    assert _FakeCuDNN.benchmark is False
