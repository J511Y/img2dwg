from __future__ import annotations

import torch

from img2dwg.ved.dataset import collate_fn  # type: ignore[import-untyped]


def test_collate_fn_stacks_pixel_values_and_labels() -> None:
    batch = [
        {
            "pixel_values": torch.ones(3, 4, 4),
            "labels": torch.tensor([1, 2, 3]),
        },
        {
            "pixel_values": torch.zeros(3, 4, 4),
            "labels": torch.tensor([4, 5, 6]),
        },
    ]

    out = collate_fn(batch)

    assert tuple(out["pixel_values"].shape) == (2, 3, 4, 4)
    assert tuple(out["labels"].shape) == (2, 3)
    assert out["pixel_values"][0].sum().item() == 48
    assert out["labels"].tolist() == [[1, 2, 3], [4, 5, 6]]
