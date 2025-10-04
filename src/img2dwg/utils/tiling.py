"""타일링 유틸리티 모듈."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..data.dwg_parser import DWGParser, ParseOptions
from .geometry import calculate_tiles, intersects_aabb


class TileGenerator:
    """
    DWG 데이터를 타일 단위로 분할하는 클래스.

    큰 DWG 파일을 여러 개의 작은 타일로 나누어
    각 타일이 토큰 제한 내에 들어오도록 합니다.
    """

    def __init__(
        self,
        tile_size: float = 5000.0,
        overlap: float = 0.1,
        min_entities_per_tile: int = 5,
    ):
        """
        TileGenerator를 초기화한다.

        Args:
            tile_size: 타일 크기 (모델 좌표계 단위)
            overlap: 타일 간 겹침 비율 (0.0 ~ 1.0)
            min_entities_per_tile: 타일당 최소 엔티티 수
        """
        self.tile_size = tile_size
        self.overlap = overlap
        self.min_entities_per_tile = min_entities_per_tile

    def generate_tiles(
        self,
        json_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        JSON 데이터를 타일로 분할한다.

        Args:
            json_data: 원본 JSON 데이터

        Returns:
            타일별 JSON 데이터 리스트
        """
        entities = json_data.get("entities", [])

        if not entities:
            return [json_data]

        # 전체 바운딩박스 계산
        bbox = self._calculate_bbox(entities)

        # 타일 생성
        tiles = calculate_tiles(bbox, self.tile_size, self.overlap)

        # 각 타일에 속하는 엔티티 분류
        tile_data_list = []
        for i, tile_bbox in enumerate(tiles):
            tile_entities = self._filter_entities_by_bbox(entities, tile_bbox)

            # 최소 엔티티 수 체크
            if len(tile_entities) < self.min_entities_per_tile:
                continue

            # 타일 메타데이터 생성
            tile_metadata = json_data.get("metadata", {}).copy()
            tile_metadata["tile_index"] = i
            tile_metadata["tile_count"] = len(tiles)
            tile_metadata["tile_bbox"] = tile_bbox
            tile_metadata["entity_count"] = len(tile_entities)

            tile_data = {
                "metadata": tile_metadata,
                "entities": tile_entities,
            }

            tile_data_list.append(tile_data)

        # 타일이 하나도 없으면 원본 반환
        if not tile_data_list:
            return [json_data]

        return tile_data_list

    def _calculate_bbox(self, entities: List[Dict[str, Any]]) -> Tuple[float, float, float, float]:
        """
        엔티티들의 전체 바운딩박스를 계산한다.

        Args:
            entities: 엔티티 리스트

        Returns:
            (xmin, ymin, xmax, ymax) 튜플
        """
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for entity in entities:
            # LINE
            if "start" in entity and "end" in entity:
                min_x = min(min_x, entity["start"]["x"], entity["end"]["x"])
                min_y = min(min_y, entity["start"]["y"], entity["end"]["y"])
                max_x = max(max_x, entity["start"]["x"], entity["end"]["x"])
                max_y = max(max_y, entity["start"]["y"], entity["end"]["y"])

            # POLYLINE
            if "points" in entity:
                for pt in entity["points"]:
                    min_x = min(min_x, pt["x"])
                    min_y = min(min_y, pt["y"])
                    max_x = max(max_x, pt["x"])
                    max_y = max(max_y, pt["y"])

            # CIRCLE, ARC
            if "center" in entity:
                radius = entity.get("radius", 0)
                min_x = min(min_x, entity["center"]["x"] - radius)
                min_y = min(min_y, entity["center"]["y"] - radius)
                max_x = max(max_x, entity["center"]["x"] + radius)
                max_y = max(max_y, entity["center"]["y"] + radius)

            # TEXT
            if "position" in entity:
                min_x = min(min_x, entity["position"]["x"])
                min_y = min(min_y, entity["position"]["y"])
                max_x = max(max_x, entity["position"]["x"])
                max_y = max(max_y, entity["position"]["y"])

        return (min_x, min_y, max_x, max_y)

    def _filter_entities_by_bbox(
        self,
        entities: List[Dict[str, Any]],
        tile_bbox: Tuple[float, float, float, float],
    ) -> List[Dict[str, Any]]:
        """
        타일 바운딩박스와 교차하는 엔티티만 필터링한다.

        Args:
            entities: 엔티티 리스트
            tile_bbox: 타일 바운딩박스

        Returns:
            필터링된 엔티티 리스트
        """
        filtered = []

        for entity in entities:
            entity_bbox = self._get_entity_bbox(entity)
            if entity_bbox and intersects_aabb(entity_bbox, tile_bbox):
                filtered.append(entity)

        return filtered

    def _get_entity_bbox(self, entity: Dict[str, Any]) -> Optional[Tuple[float, float, float, float]]:
        """
        엔티티의 바운딩박스를 계산한다.

        Args:
            entity: 엔티티 딕셔너리

        Returns:
            (xmin, ymin, xmax, ymax) 튜플 또는 None
        """
        # LINE
        if "start" in entity and "end" in entity:
            xs = [entity["start"]["x"], entity["end"]["x"]]
            ys = [entity["start"]["y"], entity["end"]["y"]]
            return (min(xs), min(ys), max(xs), max(ys))

        # POLYLINE
        if "points" in entity:
            xs = [pt["x"] for pt in entity["points"]]
            ys = [pt["y"] for pt in entity["points"]]
            return (min(xs), min(ys), max(xs), max(ys))

        # CIRCLE, ARC
        if "center" in entity:
            radius = entity.get("radius", 0)
            cx, cy = entity["center"]["x"], entity["center"]["y"]
            return (cx - radius, cy - radius, cx + radius, cy + radius)

        # TEXT
        if "position" in entity:
            px, py = entity["position"]["x"], entity["position"]["y"]
            # 텍스트는 포인트로 간주 (높이 고려 가능)
            return (px, py, px, py)

        return None


def split_by_token_budget(
    json_data: Dict[str, Any],
    max_tokens: int,
    token_counter,
) -> List[Dict[str, Any]]:
    """
    토큰 예산에 맞게 JSON 데이터를 분할한다.

    Args:
        json_data: 원본 JSON 데이터
        max_tokens: 최대 토큰 수
        token_counter: 토큰 카운터 함수

    Returns:
        분할된 JSON 데이터 리스트
    """
    # 현재 토큰 수 확인
    current_tokens = token_counter(json_data)

    if current_tokens <= max_tokens:
        return [json_data]

    # 타일 크기를 점진적으로 줄여가며 시도
    tile_sizes = [5000, 3000, 2000, 1000, 500]

    for tile_size in tile_sizes:
        generator = TileGenerator(tile_size=tile_size, overlap=0.1)
        tiles = generator.generate_tiles(json_data)

        # 모든 타일이 토큰 제한 내인지 확인
        all_within_budget = all(
            token_counter(tile) <= max_tokens
            for tile in tiles
        )

        if all_within_budget:
            return tiles

    # 그래도 안 되면 엔티티 단위로 분할
    return _split_by_entity_groups(json_data, max_tokens, token_counter)


def _split_by_entity_groups(
    json_data: Dict[str, Any],
    max_tokens: int,
    token_counter,
) -> List[Dict[str, Any]]:
    """
    엔티티를 그룹으로 나누어 분할한다.

    Args:
        json_data: 원본 JSON 데이터
        max_tokens: 최대 토큰 수
        token_counter: 토큰 카운터 함수

    Returns:
        분할된 JSON 데이터 리스트
    """
    entities = json_data.get("entities", [])
    metadata = json_data.get("metadata", {})

    chunks = []
    current_chunk = []

    for entity in entities:
        # 임시로 엔티티 추가
        test_data = {
            "metadata": metadata.copy(),
            "entities": current_chunk + [entity],
        }

        # 토큰 수 확인
        if token_counter(test_data) > max_tokens and current_chunk:
            # 현재 청크 저장
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = len(chunks)
            chunk_metadata["entity_count"] = len(current_chunk)

            chunks.append({
                "metadata": chunk_metadata,
                "entities": current_chunk,
            })

            current_chunk = [entity]
        else:
            current_chunk.append(entity)

    # 마지막 청크
    if current_chunk:
        chunk_metadata = metadata.copy()
        chunk_metadata["chunk_index"] = len(chunks)
        chunk_metadata["entity_count"] = len(current_chunk)

        chunks.append({
            "metadata": chunk_metadata,
            "entities": current_chunk,
        })

    return chunks if chunks else [json_data]
