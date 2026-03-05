from __future__ import annotations

import pytest

from img2dwg.utils.tiling import TileGenerator, split_by_token_budget


def _sample_json() -> dict:
    return {
        "metadata": {"filename": "unit"},
        "entities": [
            {"type": "line", "start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 10}},
            {"type": "line", "start": {"x": 100, "y": 0}, "end": {"x": 110, "y": 10}},
            {"type": "text", "position": {"x": 200, "y": 5}},
        ],
    }


def test_generate_tiles_handles_empty_and_bbox() -> None:
    generator = TileGenerator(tile_size=20, overlap=0.0, min_entities_per_tile=1)

    empty = {"metadata": {"filename": "none"}, "entities": []}
    assert generator.generate_tiles(empty) == [empty]

    bbox = generator._calculate_bbox(_sample_json()["entities"])
    assert bbox == (0, 0, 200, 10)


def test_generate_tiles_splits_entities_into_tiles(monkeypatch: pytest.MonkeyPatch) -> None:
    generator = TileGenerator(tile_size=20, overlap=0.0, min_entities_per_tile=1)

    monkeypatch.setattr(
        "img2dwg.utils.tiling.calculate_tiles",
        lambda *_: [(0, 0, 50, 50), (90, -10, 150, 50)],
    )

    tiles = generator.generate_tiles(_sample_json())

    assert len(tiles) == 2
    assert tiles[0]["metadata"]["tile_index"] == 0
    assert tiles[0]["metadata"]["tile_count"] == 2
    assert tiles[0]["metadata"]["entity_count"] == 1
    assert len(tiles[1]["entities"]) == 1


def test_split_by_token_budget_prefers_tiles_and_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    json_data = _sample_json()

    def token_counter(payload: dict) -> int:
        return len(payload.get("entities", [])) * 10

    # already within budget
    assert split_by_token_budget({"entities": [{}]}, max_tokens=20, token_counter=token_counter)

    # tile split success path
    monkeypatch.setattr(
        "img2dwg.utils.tiling.TileGenerator.generate_tiles",
        lambda self, data: [
            {"metadata": {"tile": 0}, "entities": data["entities"][:1]},
            {"metadata": {"tile": 1}, "entities": data["entities"][1:2]},
        ],
    )
    tiles = split_by_token_budget(json_data, max_tokens=20, token_counter=token_counter)
    assert len(tiles) == 2

    # force fallback split by entity groups (tile has oversized chunk)
    monkeypatch.setattr(
        "img2dwg.utils.tiling.TileGenerator.generate_tiles",
        lambda self, data: [{"metadata": {"tile": 0}, "entities": data["entities"]}],
    )
    chunks = split_by_token_budget(json_data, max_tokens=15, token_counter=token_counter)
    assert len(chunks) >= 2
    assert chunks[0]["metadata"]["chunk_index"] == 0
    assert "entity_count" in chunks[0]["metadata"]
