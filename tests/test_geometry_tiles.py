"""calculate_tiles 경계 조건 테스트."""

import pytest

from img2dwg.utils.geometry import calculate_tiles


@pytest.mark.parametrize("tile_size", [0, -1.0])
def test_calculate_tiles_rejects_non_positive_tile_size(tile_size):
    with pytest.raises(ValueError, match="tile_size"):
        calculate_tiles((0.0, 0.0, 10.0, 10.0), tile_size=tile_size)


@pytest.mark.parametrize("overlap", [-0.1, 1.0, 1.2])
def test_calculate_tiles_rejects_invalid_overlap(overlap):
    with pytest.raises(ValueError, match="overlap"):
        calculate_tiles((0.0, 0.0, 10.0, 10.0), tile_size=10.0, overlap=overlap)


@pytest.mark.parametrize(
    "bbox",
    [
        (0.0, 0.0, 20.0, 0.0),  # horizontal line domain
        (10.0, 0.0, 10.0, 20.0),  # vertical line domain
        (5.0, 5.0, 5.0, 5.0),  # point domain
    ],
)
def test_calculate_tiles_returns_single_fallback_tile_for_degenerate_bbox(bbox):
    tiles = calculate_tiles(bbox, tile_size=10.0, overlap=0.5)

    assert len(tiles) == 1
    assert tiles[0] == bbox


def test_calculate_tiles_generates_expected_grid_count_with_overlap():
    tiles = calculate_tiles((0.0, 0.0, 20.0, 20.0), tile_size=10.0, overlap=0.5)

    assert len(tiles) == 9
    assert tiles[0] == (0.0, 0.0, 10.0, 10.0)
    assert tiles[-1] == (10.0, 10.0, 20.0, 20.0)
