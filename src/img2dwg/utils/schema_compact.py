"""Compact 스키마 변환 유틸리티."""

import math
from typing import Any


class CompactSchemaConverter:
    """
    JSON 스키마를 토큰 최소화를 위한 compact 형태로 변환한다.

    최적화 기법:
    1. 키 단축: "type" → "t", "points" → "p" 등
    2. 배열 평탄화: [{x:0,y:0},{x:1,y:1}] → [0,0,1,1]
    3. 테이블화: 반복되는 문자열을 인덱스로 치환
    4. 로컬 좌표계: 타일 원점 기준으로 좌표 변환
    """

    # 키 매핑 (긴 키 → 짧은 키)
    KEY_MAP = {
        "type": "t",
        "layer": "l",
        "color": "c",
        "linetype": "lt",
        "start": "s",
        "end": "e",
        "points": "p",
        "closed": "cl",
        "center": "ct",
        "radius": "r",
        "start_angle": "sa",
        "end_angle": "ea",
        "position": "ps",
        "content": "tx",
        "height": "h",
        "rotation": "ro",
        "x": "0",
        "y": "1",
    }

    # 역매핑 (복원용)
    REVERSE_KEY_MAP = {v: k for k, v in KEY_MAP.items()}

    def __init__(self, use_local_coords: bool = True):
        """
        CompactSchemaConverter를 초기화한다.

        Args:
            use_local_coords: 로컬 좌표계 사용 여부
        """
        self.use_local_coords = use_local_coords
        self.layer_table: list[str] = []
        self.linetype_table: list[str] = []
        self.origin: tuple[float, float] | None = None

    def compact(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        JSON 데이터를 compact 형태로 변환한다.

        Args:
            data: 원본 JSON 데이터

        Returns:
            Compact 형태의 JSON 데이터
        """
        entities = data.get("entities", [])

        # 1단계: 레이어/리네타입 테이블 생성
        self._build_tables(entities)

        # 2단계: 로컬 좌표계 원점 계산
        self.origin = None
        if self.use_local_coords:
            calculated_origin = self._calculate_origin(entities)
            if calculated_origin is not None and self._is_finite_origin(calculated_origin):
                self.origin = calculated_origin

        # 3단계: 엔티티 변환
        compact_entities = [self._compact_entity(e) for e in entities]

        # 4단계: 메타데이터 변환
        compact_metadata = self._compact_metadata(data.get("metadata", {}))

        result = {
            "m": compact_metadata,
            "e": compact_entities,
        }

        # 테이블 추가 (2개 이상의 항목이 있을 때만)
        if len(self.layer_table) > 1:
            result["lt"] = self.layer_table
        if len(self.linetype_table) > 1:
            result["ltt"] = self.linetype_table

        # 원점 추가
        if self.origin is not None:
            result["o"] = list(self.origin)

        return result

    def expand(self, compact_data: dict[str, Any]) -> dict[str, Any]:
        """
        Compact 형태를 원래 JSON으로 복원한다.

        Args:
            compact_data: Compact 형태의 JSON 데이터

        Returns:
            복원된 JSON 데이터
        """
        # 테이블 복원
        self.layer_table = compact_data.get("lt", [])
        self.linetype_table = compact_data.get("ltt", [])
        self.origin = self._normalize_origin(compact_data.get("o"))

        # 메타데이터 복원
        metadata = self._expand_metadata(compact_data.get("m", {}))

        # 엔티티 복원
        entities = [self._expand_entity(e) for e in compact_data.get("e", [])]

        return {
            "metadata": metadata,
            "entities": entities,
        }

    def _build_tables(self, entities: list[dict[str, Any]]) -> None:
        """레이어 및 리네타입 테이블을 생성한다."""
        layers = set()
        linetypes = set()

        for entity in entities:
            if "layer" in entity:
                layers.add(entity["layer"])
            if "linetype" in entity:
                linetypes.add(entity["linetype"])

        self.layer_table = sorted(layers)
        self.linetype_table = sorted(linetypes)

    def _is_finite_origin(self, origin: tuple[float, float]) -> bool:
        """원점 좌표가 유한 실수인지 검증한다."""
        return math.isfinite(origin[0]) and math.isfinite(origin[1])

    def _normalize_origin(self, raw_origin: Any) -> tuple[float, float] | None:
        """외부 입력 원점을 정규화하고 비정상 값은 제거한다."""
        if not isinstance(raw_origin, (list, tuple)) or len(raw_origin) != 2:
            return None

        try:
            origin = (float(raw_origin[0]), float(raw_origin[1]))
        except (TypeError, ValueError):
            return None

        if not self._is_finite_origin(origin):
            return None

        return origin

    def _calculate_origin(self, entities: list[dict[str, Any]]) -> tuple[float, float] | None:
        """엔티티들의 바운딩박스 최소점을 원점으로 계산한다."""
        min_x = float("inf")
        min_y = float("inf")

        for entity in entities:
            # LINE
            if "start" in entity:
                min_x = min(min_x, entity["start"]["x"])
                min_y = min(min_y, entity["start"]["y"])
            if "end" in entity:
                min_x = min(min_x, entity["end"]["x"])
                min_y = min(min_y, entity["end"]["y"])

            # POLYLINE
            if "points" in entity:
                for pt in entity["points"]:
                    min_x = min(min_x, pt["x"])
                    min_y = min(min_y, pt["y"])

            # CIRCLE, ARC
            if "center" in entity:
                min_x = min(min_x, entity["center"]["x"])
                min_y = min(min_y, entity["center"]["y"])

            # TEXT
            if "position" in entity:
                min_x = min(min_x, entity["position"]["x"])
                min_y = min(min_y, entity["position"]["y"])

        origin = (min_x, min_y)
        if not self._is_finite_origin(origin):
            return None

        return origin

    def _to_local(self, x: float, y: float) -> tuple[float, float]:
        """전역 좌표를 로컬 좌표로 변환한다."""
        if self.origin is not None:
            return (x - self.origin[0], y - self.origin[1])
        return (x, y)

    def _to_global(self, x: float, y: float) -> tuple[float, float]:
        """로컬 좌표를 전역 좌표로 변환한다."""
        if self.origin is not None:
            return (x + self.origin[0], y + self.origin[1])
        return (x, y)

    def _compact_point(self, point: dict[str, float]) -> list[float]:
        """포인트를 배열로 평탄화한다."""
        x, y = self._to_local(point["x"], point["y"])
        return [x, y]

    def _expand_point(self, point: list[float]) -> dict[str, float]:
        """배열을 포인트 객체로 복원한다."""
        x, y = self._to_global(point[0], point[1])
        return {"x": x, "y": y}

    def _compact_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """메타데이터를 compact 형태로 변환한다."""
        result = {}

        if "filename" in metadata:
            result["f"] = metadata["filename"]
        if "type" in metadata:
            result["t"] = metadata["type"]
        if "project" in metadata:
            result["p"] = metadata["project"]
        if "entity_count" in metadata:
            result["n"] = metadata["entity_count"]

        return result

    def _expand_metadata(self, compact: dict[str, Any]) -> dict[str, Any]:
        """Compact 메타데이터를 복원한다."""
        result = {}

        if "f" in compact:
            result["filename"] = compact["f"]
        if "t" in compact:
            result["type"] = compact["t"]
        if "p" in compact:
            result["project"] = compact["p"]
        if "n" in compact:
            result["entity_count"] = compact["n"]

        return result

    def _compact_entity(self, entity: dict[str, Any]) -> dict[str, Any]:
        """엔티티를 compact 형태로 변환한다."""
        result = {}
        entity_type = entity.get("type", "")

        # 타입 (필수)
        result["t"] = entity_type

        # 레이어 (테이블 인덱스)
        if "layer" in entity and self.layer_table:
            try:
                result["l"] = self.layer_table.index(entity["layer"])
            except ValueError:
                result["l"] = entity["layer"]

        # 리네타입 (테이블 인덱스)
        if "linetype" in entity and self.linetype_table:
            try:
                result["lt"] = self.linetype_table.index(entity["linetype"])
            except ValueError:
                result["lt"] = entity["linetype"]

        # 색상
        if "color" in entity:
            result["c"] = entity["color"]

        # 타입별 속성
        if entity_type == "line":
            result["s"] = self._compact_point(entity["start"])
            result["e"] = self._compact_point(entity["end"])

        elif entity_type == "polyline":
            # 포인트 배열 평탄화: [{x:0,y:0},{x:1,y:1}] → [0,0,1,1]
            points_flat = []
            for pt in entity["points"]:
                x, y = self._to_local(pt["x"], pt["y"])
                points_flat.extend([x, y])
            result["p"] = points_flat

            if entity.get("closed"):
                result["cl"] = 1

        elif entity_type == "circle":
            result["ct"] = self._compact_point(entity["center"])
            result["r"] = entity["radius"]

        elif entity_type == "arc":
            result["ct"] = self._compact_point(entity["center"])
            result["r"] = entity["radius"]
            result["sa"] = entity["start_angle"]
            result["ea"] = entity["end_angle"]

        elif entity_type == "text":
            result["ps"] = self._compact_point(entity["position"])
            result["tx"] = entity["content"]
            result["h"] = entity["height"]

            if "rotation" in entity:
                result["ro"] = entity["rotation"]

        return result

    def _expand_entity(self, compact: dict[str, Any]) -> dict[str, Any]:
        """Compact 엔티티를 복원한다."""
        result = {}
        entity_type = compact.get("t", "")

        # 타입
        result["type"] = entity_type

        # 레이어
        if "l" in compact:
            if isinstance(compact["l"], int) and self.layer_table:
                result["layer"] = self.layer_table[compact["l"]]
            else:
                result["layer"] = compact["l"]

        # 리네타입
        if "lt" in compact:
            if isinstance(compact["lt"], int) and self.linetype_table:
                result["linetype"] = self.linetype_table[compact["lt"]]
            else:
                result["linetype"] = compact["lt"]

        # 색상
        if "c" in compact:
            result["color"] = compact["c"]

        # 타입별 속성
        if entity_type == "line":
            result["start"] = self._expand_point(compact["s"])
            result["end"] = self._expand_point(compact["e"])

        elif entity_type == "polyline":
            # 평탄화된 배열을 포인트 리스트로 복원
            points_flat = compact["p"]
            points = []
            for i in range(0, len(points_flat), 2):
                x, y = self._to_global(points_flat[i], points_flat[i + 1])
                points.append({"x": x, "y": y})
            result["points"] = points
            result["closed"] = bool(compact.get("cl", 0))

        elif entity_type == "circle":
            result["center"] = self._expand_point(compact["ct"])
            result["radius"] = compact["r"]

        elif entity_type == "arc":
            result["center"] = self._expand_point(compact["ct"])
            result["radius"] = compact["r"]
            result["start_angle"] = compact["sa"]
            result["end_angle"] = compact["ea"]

        elif entity_type == "text":
            result["position"] = self._expand_point(compact["ps"])
            result["content"] = compact["tx"]
            result["height"] = compact["h"]

            if "ro" in compact:
                result["rotation"] = compact["ro"]

        return result
