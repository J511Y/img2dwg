"""TileGenerator 테스트."""

import logging

from img2dwg.utils.tiling import TileGenerator


def test_tile_generator_fallbacks_to_original_json_on_invalid_tiling_config(caplog):
    json_data = {
        "metadata": {"filename": "line.json"},
        "entities": [
            {
                "type": "LINE",
                "start": {"x": 0.0, "y": 0.0},
                "end": {"x": 100.0, "y": 0.0},
            }
        ],
    }
    generator = TileGenerator(tile_size=100.0, overlap=1.0, min_entities_per_tile=1)

    with caplog.at_level(logging.WARNING):
        result = generator.generate_tiles(json_data)

    assert result == [json_data]
    assert "Invalid tiling configuration" in caplog.text
