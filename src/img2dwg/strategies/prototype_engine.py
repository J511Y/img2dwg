from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ezdxf
from PIL import Image

Point = tuple[float, float]
Segment = tuple[Point, Point]


@dataclass(slots=True)
class ImageSignals:
    width: int
    height: int
    contrast: float
    edge_density: float


@dataclass(slots=True)
class VectorPlan:
    segments: list[Segment]
    notes: list[str]


@dataclass(slots=True)
class StrategyPreset:
    margin_ratio: float
    include_center_cross: bool
    include_diagonals: bool
    quality_bias: float
    topology_bias: float
    offgrid_shift_ratio: float = 0.0
    diagonal_fan_ratio: float = 0.0


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _to_numeric(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:  # NaN
        return None
    return numeric


def resolve_consensus_score(metadata: dict[str, Any], *, default: float) -> float:
    direct = _to_numeric(metadata.get("consensus_score"))
    if direct is not None:
        return clamp01(direct)

    raw_votes = metadata.get("consensus_votes")
    if isinstance(raw_votes, list):
        votes: list[float] = []
        for item in raw_votes:
            parsed = _to_numeric(item)
            if parsed is None:
                continue
            votes.append(clamp01(parsed))
        if votes:
            return clamp01(sum(votes) / len(votes))

    return clamp01(default)


def extract_image_signals(image_path: Path) -> ImageSignals:
    with Image.open(image_path) as image:
        gray = image.convert("L")
        width, height = gray.size
        if width <= 0 or height <= 0:
            raise ValueError(f"invalid image size: {width}x{height}")

        sample_width = min(width, 128)
        sample_height = min(height, 128)
        sampled = gray.resize((sample_width, sample_height), Image.Resampling.BILINEAR)
        pixels = list(sampled.getdata())

    minimum = min(pixels)
    maximum = max(pixels)
    contrast = (maximum - minimum) / 255.0

    edge_count = 0
    pair_count = 0
    edge_threshold = 24

    for y in range(sample_height):
        row_offset = y * sample_width
        for x in range(sample_width - 1):
            left = pixels[row_offset + x]
            right = pixels[row_offset + x + 1]
            if abs(left - right) >= edge_threshold:
                edge_count += 1
            pair_count += 1

    for y in range(sample_height - 1):
        row_offset = y * sample_width
        next_row_offset = (y + 1) * sample_width
        for x in range(sample_width):
            top = pixels[row_offset + x]
            bottom = pixels[next_row_offset + x]
            if abs(top - bottom) >= edge_threshold:
                edge_count += 1
            pair_count += 1

    edge_density = edge_count / pair_count if pair_count else 0.0
    return ImageSignals(
        width=width,
        height=height,
        contrast=clamp01(contrast),
        edge_density=clamp01(edge_density),
    )


def build_vector_plan(signals: ImageSignals, preset: StrategyPreset) -> VectorPlan:
    width = float(signals.width)
    height = float(signals.height)

    margin_x = max(2.0, width * max(preset.margin_ratio, 0.0))
    margin_y = max(2.0, height * max(preset.margin_ratio, 0.0))

    left = margin_x
    right = max(left + 1.0, width - margin_x)
    top = margin_y
    bottom = max(top + 1.0, height - margin_y)

    segments: list[Segment] = [
        ((left, top), (right, top)),
        ((right, top), (right, bottom)),
        ((right, bottom), (left, bottom)),
        ((left, bottom), (left, top)),
    ]

    notes = [f"bbox:{signals.width}x{signals.height}"]

    if preset.include_center_cross:
        center_x = round((left + right) / 2, 2)
        center_y = round((top + bottom) / 2, 2)
        segments.extend(
            [
                ((left, center_y), (right, center_y)),
                ((center_x, top), (center_x, bottom)),
            ]
        )
        notes.append("center_cross:on")

    if preset.include_diagonals:
        segments.extend(
            [
                ((left, top), (right, bottom)),
                ((right, top), (left, bottom)),
            ]
        )

        if preset.diagonal_fan_ratio > 0:
            fan_x = max(1.0, (right - left) * preset.diagonal_fan_ratio)
            fan_y = max(1.0, (bottom - top) * preset.diagonal_fan_ratio)
            segments.extend(
                [
                    ((left + fan_x, top), (right, bottom - fan_y)),
                    ((right - fan_x, top), (left, bottom - fan_y)),
                ]
            )
            notes.append(f"diagonal_fan:{preset.diagonal_fan_ratio:.3f}")

        notes.append("diagonals:on")

    if preset.offgrid_shift_ratio > 0:
        shift_x = max(1.0, (right - left) * preset.offgrid_shift_ratio)
        shift_y = max(1.0, (bottom - top) * preset.offgrid_shift_ratio)
        inset_x = max(1.0, (right - left) * 0.12)
        inset_y = max(1.0, (bottom - top) * 0.10)

        segments.extend(
            [
                ((left + inset_x, top + inset_y), (right - inset_x, bottom - inset_y - shift_y)),
                ((left + inset_x + shift_x, bottom - inset_y), (right - inset_x - shift_x, top + inset_y + shift_y)),
            ]
        )

        # add asymmetric debias chords to reduce axis-aligned dominance and
        # increase coordinate diversity in grid-heavy floorplans.
        residual_x = max(1.0, shift_x * 0.73)
        residual_y = max(1.0, shift_y * 1.27)
        segments.extend(
            [
                (
                    (left + inset_x * 1.45 + residual_x, top + inset_y * 0.65 + residual_y),
                    (right - inset_x * 0.58 - residual_x, bottom - inset_y * 1.55),
                ),
                (
                    (left + inset_x * 0.55, bottom - inset_y * 1.35 - residual_y),
                    (right - inset_x * 1.62 + residual_x, top + inset_y * 1.10),
                ),
            ]
        )
        notes.append(f"offgrid_shift:{preset.offgrid_shift_ratio:.3f}")
        notes.append("offgrid_debias_chords:on")

    return VectorPlan(segments=segments, notes=notes)


def export_plan_as_dxf(path: Path, plan: VectorPlan, *, layer: str) -> None:
    doc = ezdxf.new("R2018", setup=True)
    msp = doc.modelspace()
    for start, end in plan.segments:
        msp.add_line(start, end, dxfattribs={"layer": layer})
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(path))


def estimate_metrics(signals: ImageSignals, preset: StrategyPreset, *, consensus_score: float) -> dict[str, float]:
    consensus = clamp01(consensus_score)
    iou = clamp01(
        0.22
        + (0.40 * signals.contrast)
        + (0.15 * signals.edge_density)
        + (0.15 * preset.quality_bias)
        + (0.08 * preset.topology_bias)
        + (0.18 * consensus)
    )
    topology_f1 = clamp01(
        0.20
        + (0.22 * signals.contrast)
        + (0.32 * signals.edge_density)
        + (0.10 * preset.quality_bias)
        + (0.20 * preset.topology_bias)
        + (0.16 * consensus)
    )
    return {
        "iou": round(iou, 4),
        "topology_f1": round(topology_f1, 4),
    }
