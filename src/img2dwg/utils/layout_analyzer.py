"""레이아웃 분석 및 고수준 추상화 모듈."""

from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import math


class LayoutAnalyzer:
    """
    DXF 엔티티를 분석하여 고수준 레이아웃 객체로 변환한다.
    
    목표:
    - 수천 개의 LINE → 수십 개의 WALL
    - 반복 패턴 → 템플릿 + 인스턴스
    - 의미론적 그룹화 (방, 벽, 문, 창문 등)
    """
    
    def __init__(
        self,
        merge_threshold: float = 0.1,  # 선 병합 임계값
        parallel_threshold: float = 5.0,  # 평행선 각도 임계값 (도)
        min_wall_length: float = 100.0,  # 최소 벽 길이
    ):
        """
        LayoutAnalyzer를 초기화한다.
        
        Args:
            merge_threshold: 연결된 선을 병합할 거리 임계값
            parallel_threshold: 평행선으로 간주할 각도 차이
            min_wall_length: 벽으로 간주할 최소 길이
        """
        self.merge_threshold = merge_threshold
        self.parallel_threshold = parallel_threshold
        self.min_wall_length = min_wall_length
    
    def analyze(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        엔티티 리스트를 분석하여 고수준 레이아웃으로 변환한다.
        
        Args:
            entities: 원본 엔티티 리스트
        
        Returns:
            고수준 레이아웃 딕셔너리
        """
        # 1단계: 엔티티 타입별 분류
        classified = self._classify_entities(entities)
        
        # 2단계: 선 병합 (연결된 선들을 폴리라인으로)
        merged_lines = self._merge_connected_lines(classified.get("lines", []))
        
        # 3단계: 폴리라인 간소화
        simplified_polylines = self._simplify_polylines(
            classified.get("polylines", []) + merged_lines
        )
        
        # 4단계: 벽 감지 (평행한 폴리라인 쌍)
        walls = self._detect_walls(simplified_polylines)
        
        # 5단계: 폐곡선 감지 (방, 공간)
        rooms = self._detect_rooms(simplified_polylines)
        
        # 6단계: 문/창문 감지 (작은 개구부)
        openings = self._detect_openings(classified.get("arcs", []), walls)
        
        # 7단계: 텍스트/치수 그룹화
        annotations = self._group_annotations(
            classified.get("texts", []),
            classified.get("dimensions", [])
        )
        
        # 8단계: 반복 패턴 감지
        patterns = self._detect_patterns(rooms, walls)
        
        return {
            "type": "layout",
            "walls": walls,
            "rooms": rooms,
            "openings": openings,
            "annotations": annotations,
            "patterns": patterns,
            "statistics": {
                "original_entities": len(entities),
                "walls": len(walls),
                "rooms": len(rooms),
                "compression_ratio": self._calculate_compression_ratio(
                    len(entities), walls, rooms, annotations
                )
            }
        }
    
    def _classify_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, List]:
        """엔티티를 타입별로 분류한다."""
        classified = defaultdict(list)
        
        for entity in entities:
            entity_type = entity.get("type", "")
            
            if entity_type == "line":
                classified["lines"].append(entity)
            elif entity_type == "polyline":
                classified["polylines"].append(entity)
            elif entity_type == "arc":
                classified["arcs"].append(entity)
            elif entity_type == "circle":
                classified["circles"].append(entity)
            elif entity_type == "text":
                classified["texts"].append(entity)
            elif "dimension" in entity_type.lower():
                classified["dimensions"].append(entity)
        
        return dict(classified)
    
    def _merge_connected_lines(self, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        연결된 선들을 폴리라인으로 병합한다.
        
        Args:
            lines: LINE 엔티티 리스트
        
        Returns:
            병합된 폴리라인 리스트
        """
        if not lines:
            return []
        
        # 그래프 구조로 변환
        graph = defaultdict(list)
        for line in lines:
            start = self._point_to_key(line["start"])
            end = self._point_to_key(line["end"])
            graph[start].append((end, line))
            graph[end].append((start, line))
        
        # 연결된 체인 찾기
        visited = set()
        polylines = []
        
        for start_key in graph:
            if start_key in visited:
                continue
            
            # DFS로 체인 추적
            chain = self._trace_chain(start_key, graph, visited)
            
            if len(chain) > 1:  # 2개 이상의 선이 연결됨
                polylines.append({
                    "type": "polyline",
                    "points": chain,
                    "closed": self._is_closed_chain(chain),
                    "source": "merged_lines"
                })
        
        return polylines
    
    def _simplify_polylines(self, polylines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        폴리라인을 간소화한다 (Douglas-Peucker 이미 적용됨).
        
        추가로 직선 구간을 하나의 세그먼트로 병합.
        """
        simplified = []
        
        for poly in polylines:
            points = poly.get("points", [])
            if len(points) < 2:
                continue
            
            # 직선 구간 병합
            merged_points = [points[0]]
            
            for i in range(1, len(points) - 1):
                # 이전, 현재, 다음 점이 일직선상에 있는지 확인
                if not self._is_collinear(
                    merged_points[-1],
                    points[i],
                    points[i + 1]
                ):
                    merged_points.append(points[i])
            
            merged_points.append(points[-1])
            
            simplified.append({
                **poly,
                "points": merged_points
            })
        
        return simplified
    
    def _detect_walls(self, polylines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        평행한 폴리라인 쌍을 벽으로 감지한다.
        
        Args:
            polylines: 폴리라인 리스트
        
        Returns:
            벽 객체 리스트
        """
        walls = []
        used = set()
        
        for i, poly1 in enumerate(polylines):
            if i in used:
                continue
            
            points1 = poly1.get("points", [])
            if len(points1) < 2:
                continue
            
            # 평행한 폴리라인 찾기
            for j, poly2 in enumerate(polylines[i + 1:], start=i + 1):
                if j in used:
                    continue
                
                points2 = poly2.get("points", [])
                if len(points2) < 2:
                    continue
                
                # 평행 여부 및 거리 확인
                if self._are_parallel_polylines(points1, points2):
                    thickness = self._calculate_distance_between_polylines(points1, points2)
                    
                    if 50 < thickness < 500:  # 벽 두께 범위 (50mm ~ 500mm)
                        walls.append({
                            "type": "wall",
                            "centerline": self._calculate_centerline(points1, points2),
                            "thickness": round(thickness, 1),
                            "length": self._calculate_polyline_length(points1),
                        })
                        used.add(i)
                        used.add(j)
                        break
        
        # 단일 폴리라인도 벽으로 간주 (두께 추정)
        for i, poly in enumerate(polylines):
            if i not in used:
                points = poly.get("points", [])
                length = self._calculate_polyline_length(points)
                
                if length >= self.min_wall_length:
                    walls.append({
                        "type": "wall",
                        "centerline": points,
                        "thickness": 100,  # 기본 두께
                        "length": round(length, 1),
                    })
        
        return walls
    
    def _detect_rooms(self, polylines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        폐곡선을 방/공간으로 감지한다.
        
        Args:
            polylines: 폴리라인 리스트
        
        Returns:
            방 객체 리스트
        """
        rooms = []
        
        for poly in polylines:
            if poly.get("closed"):
                points = poly.get("points", [])
                area = self._calculate_polygon_area(points)
                
                # 최소 면적 필터 (1m² = 1,000,000mm²)
                if area > 1_000_000:
                    rooms.append({
                        "type": "room",
                        "boundary": self._encode_polygon(points),
                        "area": round(area / 1_000_000, 2),  # m²로 변환
                        "centroid": self._calculate_centroid(points),
                    })
        
        return rooms
    
    def _detect_openings(
        self,
        arcs: List[Dict[str, Any]],
        walls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        호(arc)를 문/창문으로 감지한다.
        
        Args:
            arcs: ARC 엔티티 리스트
            walls: 벽 리스트
        
        Returns:
            개구부 객체 리스트
        """
        openings = []
        
        for arc in arcs:
            # 90도 호는 일반적으로 문
            start_angle = arc.get("start_angle", 0)
            end_angle = arc.get("end_angle", 0)
            angle_diff = abs(end_angle - start_angle)
            
            if 80 < angle_diff < 100:  # 약 90도
                radius = arc.get("radius", 0)
                
                if 400 < radius < 1200:  # 문 크기 범위
                    openings.append({
                        "type": "door",
                        "position": arc.get("center", {}),
                        "width": round(radius * 2, 1),
                        "swing_angle": round(angle_diff, 1),
                    })
        
        return openings
    
    def _group_annotations(
        self,
        texts: List[Dict[str, Any]],
        dimensions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        텍스트와 치수를 그룹화한다.
        
        Args:
            texts: TEXT 엔티티 리스트
            dimensions: DIMENSION 엔티티 리스트
        
        Returns:
            주석 객체 리스트
        """
        annotations = []
        
        # 텍스트 그룹화 (근접한 텍스트 병합)
        text_groups = self._cluster_by_proximity(texts, threshold=500)
        
        for group in text_groups:
            if len(group) == 1:
                text = group[0]
                annotations.append({
                    "type": "label",
                    "text": text.get("content", ""),
                    "position": text.get("position", {}),
                })
            else:
                # 여러 텍스트 병합
                combined_text = " ".join(t.get("content", "") for t in group)
                avg_pos = self._average_position([t.get("position", {}) for t in group])
                annotations.append({
                    "type": "label",
                    "text": combined_text,
                    "position": avg_pos,
                })
        
        # 치수는 값만 추출
        for dim in dimensions:
            annotations.append({
                "type": "dimension",
                "value": dim.get("text", ""),
                "position": dim.get("position", {}),
            })
        
        return annotations
    
    def _detect_patterns(
        self,
        rooms: List[Dict[str, Any]],
        walls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        반복되는 패턴을 감지한다 (예: 동일한 크기의 방).
        
        Args:
            rooms: 방 리스트
            walls: 벽 리스트
        
        Returns:
            패턴 객체 리스트
        """
        patterns = []
        
        # 면적별 방 그룹화
        area_groups = defaultdict(list)
        for room in rooms:
            area = room.get("area", 0)
            # 5% 오차 범위 내에서 그룹화
            area_key = round(area / 0.05) * 0.05
            area_groups[area_key].append(room)
        
        # 3개 이상 반복되는 패턴만 추출
        for area, group in area_groups.items():
            if len(group) >= 3:
                patterns.append({
                    "type": "repeated_room",
                    "area": area,
                    "count": len(group),
                    "template": group[0]["boundary"],  # 첫 번째를 템플릿으로
                    "instances": [r["centroid"] for r in group],  # 위치만 저장
                })
        
        return patterns
    
    # ===== 유틸리티 메서드 =====
    
    def _point_to_key(self, point: Dict[str, float]) -> Tuple[float, float]:
        """포인트를 해시 가능한 키로 변환."""
        return (round(point["x"], 1), round(point["y"], 1))
    
    def _trace_chain(
        self,
        start: Tuple[float, float],
        graph: Dict,
        visited: set
    ) -> List[Dict[str, float]]:
        """그래프에서 연결된 체인을 추적."""
        chain = [{"x": start[0], "y": start[1]}]
        visited.add(start)
        current = start
        
        while True:
            neighbors = [n for n, _ in graph[current] if n not in visited]
            if not neighbors:
                break
            
            next_point = neighbors[0]
            chain.append({"x": next_point[0], "y": next_point[1]})
            visited.add(next_point)
            current = next_point
        
        return chain
    
    def _is_closed_chain(self, chain: List[Dict[str, float]]) -> bool:
        """체인이 폐곡선인지 확인."""
        if len(chain) < 3:
            return False
        
        first = chain[0]
        last = chain[-1]
        dist = math.sqrt((first["x"] - last["x"]) ** 2 + (first["y"] - last["y"]) ** 2)
        
        return dist < self.merge_threshold
    
    def _is_collinear(
        self,
        p1: Dict[str, float],
        p2: Dict[str, float],
        p3: Dict[str, float]
    ) -> bool:
        """세 점이 일직선상에 있는지 확인."""
        # 외적을 이용한 판정
        cross = (p2["x"] - p1["x"]) * (p3["y"] - p1["y"]) - \
                (p2["y"] - p1["y"]) * (p3["x"] - p1["x"])
        
        return abs(cross) < 1.0  # 임계값
    
    def _are_parallel_polylines(
        self,
        points1: List[Dict[str, float]],
        points2: List[Dict[str, float]]
    ) -> bool:
        """두 폴리라인이 평행한지 확인."""
        # 간단히 첫 세그먼트의 각도 비교
        if len(points1) < 2 or len(points2) < 2:
            return False
        
        angle1 = math.atan2(
            points1[1]["y"] - points1[0]["y"],
            points1[1]["x"] - points1[0]["x"]
        )
        angle2 = math.atan2(
            points2[1]["y"] - points2[0]["y"],
            points2[1]["x"] - points2[0]["x"]
        )
        
        angle_diff = abs(math.degrees(angle1 - angle2))
        
        return angle_diff < self.parallel_threshold or \
               abs(angle_diff - 180) < self.parallel_threshold
    
    def _calculate_distance_between_polylines(
        self,
        points1: List[Dict[str, float]],
        points2: List[Dict[str, float]]
    ) -> float:
        """두 폴리라인 사이의 거리 계산."""
        # 간단히 첫 점 간 거리
        p1 = points1[0]
        p2 = points2[0]
        
        return math.sqrt((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2)
    
    def _calculate_centerline(
        self,
        points1: List[Dict[str, float]],
        points2: List[Dict[str, float]]
    ) -> List[Dict[str, float]]:
        """두 폴리라인의 중심선 계산."""
        centerline = []
        
        for p1, p2 in zip(points1, points2):
            centerline.append({
                "x": (p1["x"] + p2["x"]) / 2,
                "y": (p1["y"] + p2["y"]) / 2,
            })
        
        return centerline
    
    def _calculate_polyline_length(self, points: List[Dict[str, float]]) -> float:
        """폴리라인 길이 계산."""
        length = 0.0
        
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            length += math.sqrt((p2["x"] - p1["x"]) ** 2 + (p2["y"] - p1["y"]) ** 2)
        
        return length
    
    def _calculate_polygon_area(self, points: List[Dict[str, float]]) -> float:
        """다각형 면적 계산 (Shoelace formula)."""
        if len(points) < 3:
            return 0.0
        
        area = 0.0
        for i in range(len(points)):
            j = (i + 1) % len(points)
            area += points[i]["x"] * points[j]["y"]
            area -= points[j]["x"] * points[i]["y"]
        
        return abs(area) / 2.0
    
    def _calculate_centroid(self, points: List[Dict[str, float]]) -> Dict[str, float]:
        """다각형 중심점 계산."""
        if not points:
            return {"x": 0, "y": 0}
        
        x_sum = sum(p["x"] for p in points)
        y_sum = sum(p["y"] for p in points)
        
        return {
            "x": round(x_sum / len(points), 1),
            "y": round(y_sum / len(points), 1),
        }
    
    def _encode_polygon(self, points: List[Dict[str, float]]) -> str:
        """다각형을 간결한 문자열로 인코딩."""
        # "[[x1,y1],[x2,y2],...]" 형식
        coords = ",".join(f"[{p['x']:.1f},{p['y']:.1f}]" for p in points)
        return f"[{coords}]"
    
    def _cluster_by_proximity(
        self,
        items: List[Dict[str, Any]],
        threshold: float
    ) -> List[List[Dict[str, Any]]]:
        """근접한 아이템들을 클러스터링."""
        if not items:
            return []
        
        clusters = []
        used = set()
        
        for i, item in enumerate(items):
            if i in used:
                continue
            
            cluster = [item]
            used.add(i)
            pos1 = item.get("position", {})
            
            for j, other in enumerate(items[i + 1:], start=i + 1):
                if j in used:
                    continue
                
                pos2 = other.get("position", {})
                dist = math.sqrt(
                    (pos1.get("x", 0) - pos2.get("x", 0)) ** 2 +
                    (pos1.get("y", 0) - pos2.get("y", 0)) ** 2
                )
                
                if dist < threshold:
                    cluster.append(other)
                    used.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def _average_position(self, positions: List[Dict[str, float]]) -> Dict[str, float]:
        """여러 위치의 평균 계산."""
        if not positions:
            return {"x": 0, "y": 0}
        
        x_sum = sum(p.get("x", 0) for p in positions)
        y_sum = sum(p.get("y", 0) for p in positions)
        
        return {
            "x": round(x_sum / len(positions), 1),
            "y": round(y_sum / len(positions), 1),
        }
    
    def _calculate_compression_ratio(
        self,
        original_count: int,
        walls: List,
        rooms: List,
        annotations: List
    ) -> float:
        """압축률 계산."""
        compressed_count = len(walls) + len(rooms) + len(annotations)
        
        if original_count == 0:
            return 0.0
        
        return round((1 - compressed_count / original_count) * 100, 1)
