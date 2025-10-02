"""중간 표현 JSON 스키마 정의."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class Point2D:
    """2D 좌표."""
    x: float
    y: float

    def to_dict(self) -> Dict[str, float]:
        """딕셔너리로 변환."""
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "Point2D":
        """딕셔너리로부터 생성."""
        return cls(x=data["x"], y=data["y"])


@dataclass
class CADEntity:
    """
    CAD 엔티티 기본 클래스.
    
    Attributes:
        type: 엔티티 타입 (line, polyline, circle, arc, text, dimension 등)
        layer: 레이어 이름
        color: 색상 코드
        linetype: 선 종류
    """
    type: str
    layer: str = "0"
    color: int = 7  # AutoCAD 기본 색상 (흰색)
    linetype: str = "Continuous"

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "type": self.type,
            "layer": self.layer,
            "color": self.color,
            "linetype": self.linetype,
        }


@dataclass
class LineEntity(CADEntity):
    """직선 엔티티."""
    start: Point2D = field(default_factory=lambda: Point2D(0, 0))
    end: Point2D = field(default_factory=lambda: Point2D(0, 0))

    def __post_init__(self):
        """초기화 후 처리."""
        self.type = "line"

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환."""
        base = super().to_dict()
        base.update({
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
        })
        return base


@dataclass
class PolylineEntity(CADEntity):
    """폴리라인 엔티티."""
    points: List[Point2D] = field(default_factory=list)
    closed: bool = False

    def __post_init__(self):
        """초기화 후 처리."""
        self.type = "polyline"

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환."""
        base = super().to_dict()
        base.update({
            "points": [p.to_dict() for p in self.points],
            "closed": self.closed,
        })
        return base


@dataclass
class CircleEntity(CADEntity):
    """원 엔티티."""
    center: Point2D = field(default_factory=lambda: Point2D(0, 0))
    radius: float = 1.0

    def __post_init__(self):
        """초기화 후 처리."""
        self.type = "circle"

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환."""
        base = super().to_dict()
        base.update({
            "center": self.center.to_dict(),
            "radius": self.radius,
        })
        return base


@dataclass
class TextEntity(CADEntity):
    """텍스트 엔티티."""
    position: Point2D = field(default_factory=lambda: Point2D(0, 0))
    content: str = ""
    height: float = 2.5

    def __post_init__(self):
        """초기화 후 처리."""
        self.type = "text"

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환."""
        base = super().to_dict()
        base.update({
            "position": self.position.to_dict(),
            "content": self.content,
            "height": self.height,
        })
        return base


@dataclass
class Metadata:
    """
    문서 메타데이터.
    
    Attributes:
        filename: 원본 파일명
        type: 파일 타입 (변경, 단면, 기타)
        project: 프로젝트 이름
        source_path: 원본 파일 경로
        entity_count: 엔티티 개수
    """
    filename: str
    type: str
    project: Optional[str] = None
    source_path: Optional[str] = None
    entity_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "filename": self.filename,
            "type": self.type,
            "project": self.project,
            "source_path": self.source_path,
            "entity_count": self.entity_count,
        }


@dataclass
class CADDocument:
    """
    CAD 문서 전체 구조.
    
    Attributes:
        metadata: 메타데이터
        entities: 엔티티 리스트
    """
    metadata: Metadata
    entities: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "metadata": self.metadata.to_dict(),
            "entities": self.entities,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CADDocument":
        """딕셔너리로부터 생성."""
        metadata = Metadata(**data["metadata"])
        return cls(
            metadata=metadata,
            entities=data.get("entities", []),
        )
