"""기하학 유틸리티 모듈."""

import math


def rdp_simplify(points: list[tuple[float, float]], epsilon: float) -> list[tuple[float, float]]:
    """
    Ramer-Douglas-Peucker 알고리즘으로 폴리라인을 간소화한다.

    Args:
        points: 포인트 리스트 [(x, y), ...]
        epsilon: 허용 오차 (단위: 모델 좌표계)

    Returns:
        간소화된 포인트 리스트
    """
    if len(points) < 3:
        return points

    # 시작점과 끝점 사이의 직선에서 가장 먼 점 찾기
    def perpendicular_distance(
        point: tuple[float, float],
        line_start: tuple[float, float],
        line_end: tuple[float, float],
    ) -> float:
        """점에서 선분까지의 수직 거리를 계산한다."""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end

        dx = x2 - x1
        dy = y2 - y1

        # 선분의 길이가 0이면 점 간 거리 반환
        if dx == 0 and dy == 0:
            return math.hypot(x0 - x1, y0 - y1)

        # 수직 거리 계산
        numerator = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1)
        denominator = math.hypot(dx, dy)

        return numerator / denominator

    # 재귀적으로 간소화
    def rdp_recursive(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if len(pts) < 3:
            return pts

        # 가장 먼 점 찾기
        dmax = 0.0
        index = 0
        for i in range(1, len(pts) - 1):
            d = perpendicular_distance(pts[i], pts[0], pts[-1])
            if d > dmax:
                dmax = d
                index = i

        # 가장 먼 점이 epsilon보다 크면 분할
        if dmax > epsilon:
            # 재귀적으로 두 부분 간소화
            left = rdp_recursive(pts[: index + 1])
            right = rdp_recursive(pts[index:])

            # 중복 제거하고 병합
            return left[:-1] + right

        # epsilon 이하면 시작점과 끝점만 반환
        return [pts[0], pts[-1]]

    return rdp_recursive(points)


def round_coordinate(value: float, ndigits: int) -> float:
    """
    좌표값을 지정된 소수점 자리수로 반올림한다.

    Args:
        value: 좌표값
        ndigits: 소수점 자리수

    Returns:
        반올림된 값
    """
    return round(value, ndigits)


def quantize_coordinate(value: float, grid_size: float) -> float:
    """
    좌표값을 그리드에 스냅한다.

    Args:
        value: 좌표값
        grid_size: 그리드 크기 (예: 1.0, 5.0)

    Returns:
        양자화된 값
    """
    return round(value / grid_size) * grid_size


def intersects_aabb(
    entity_bbox: tuple[float, float, float, float],
    window: tuple[float, float, float, float],
) -> bool:
    """
    엔티티의 바운딩박스가 윈도우와 교차하는지 확인한다.

    Args:
        entity_bbox: (xmin, ymin, xmax, ymax)
        window: (xmin, ymin, xmax, ymax)

    Returns:
        교차 여부
    """
    ex_min, ey_min, ex_max, ey_max = entity_bbox
    wx_min, wy_min, wx_max, wy_max = window

    # AABB 교차 검사
    return not (ex_max < wx_min or ex_min > wx_max or ey_max < wy_min or ey_min > wy_max)


def calculate_tiles(
    bbox: tuple[float, float, float, float],
    tile_size: float,
    overlap: float = 0.0,
) -> list[tuple[float, float, float, float]]:
    """
    전체 바운딩박스를 타일로 분할한다.

    Args:
        bbox: 전체 바운딩박스 (xmin, ymin, xmax, ymax)
        tile_size: 타일 크기 (정사각형)
        overlap: 타일 간 겹침 비율 (0.0 <= overlap < 1.0)

    Returns:
        타일 바운딩박스 리스트

    Raises:
        ValueError: tile_size/overlap/bbox 입력이 유효하지 않을 때
    """
    if tile_size <= 0:
        raise ValueError(f"tile_size must be > 0, got {tile_size}")

    if not (0.0 <= overlap < 1.0):
        raise ValueError(f"overlap must satisfy 0 <= overlap < 1, got {overlap}")

    xmin, ymin, xmax, ymax = bbox
    if xmax < xmin or ymax < ymin:
        raise ValueError(f"bbox must satisfy xmin <= xmax and ymin <= ymax, got {bbox}")

    # 선/점 도면에서도 최소 1개 타일을 반환해 상위 파이프라인이 빈 결과를 받지 않도록 보장한다.
    if xmax == xmin or ymax == ymin:
        return [(xmin, ymin, xmax, ymax)]

    tiles: list[tuple[float, float, float, float]] = []
    step = tile_size * (1.0 - overlap)

    epsilon = 1e-9
    y = ymin
    while True:
        x = xmin
        while True:
            tile_xmax = min(x + tile_size, xmax)
            tile_ymax = min(y + tile_size, ymax)
            tiles.append((x, y, tile_xmax, tile_ymax))

            if x + tile_size >= xmax - epsilon:
                break
            x += step

        if y + tile_size >= ymax - epsilon:
            break
        y += step

    return tiles
