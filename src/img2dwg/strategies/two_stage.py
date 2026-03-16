from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .base import ConversionInput, ConversionOutput, ConversionStrategy
from .prototype_engine import (
    StrategyPreset,
    build_vector_plan,
    estimate_metrics,
    export_plan_as_dxf,
    extract_image_signals,
)


class TwoStageBaselineStrategy(ConversionStrategy):
    """정(Thesis): 빠른 규칙 기반 2단계 베이스라인."""

    name = "two_stage_baseline"

    _preset = StrategyPreset(
        margin_ratio=0.04,
        include_center_cross=False,
        include_diagonals=True,
        quality_bias=0.42,
        topology_bias=0.40,
        offgrid_shift_ratio=0.058,
        diagonal_fan_ratio=0.12,
        debias_chord_multiplier=26,
    )

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        signals = extract_image_signals(conv_input.image_path)

        # Adapt debias controls to image complexity so dense/contrasty floorplans
        # do not collapse into axis-aligned grid artifacts.
        complexity = (signals.contrast * 0.40) + (signals.edge_density * 0.60)
        extra_chords = max(0, min(16, int(round(complexity * 22.0)) - 4))
        offgrid_boost = min(0.024, max(0.0, (complexity - 0.28) * 0.06))
        fan_boost = min(0.04, max(0.0, (complexity - 0.26) * 0.10))

        # Long corridor-like plans in web_floorplan_grid_v1 tend to re-collapse into
        # axis-aligned traces unless we scale debias for aspect skew as well.
        aspect_ratio = max(signals.width, signals.height) / max(1, min(signals.width, signals.height))
        aspect_chords = max(0, min(10, int(round((aspect_ratio - 1.08) * 7.5))))
        aspect_offgrid = min(0.016, max(0.0, (aspect_ratio - 1.14) * 0.012))
        aspect_fan = min(0.028, max(0.0, (aspect_ratio - 1.14) * 0.018))

        # Extra tail lift for highly elongated corridors to avoid axis relapse on
        # long thin plans where the basic aspect boost is not enough.
        corridor_tail = max(0.0, aspect_ratio - 1.58)
        corridor_chords = max(0, min(8, int(round(corridor_tail * 8.0))))
        corridor_offgrid = min(0.01, corridor_tail * 0.011)
        corridor_fan = min(0.02, corridor_tail * 0.021)

        preset = replace(
            self._preset,
            debias_chord_multiplier=(
                self._preset.debias_chord_multiplier
                + extra_chords
                + aspect_chords
                + corridor_chords
            ),
            offgrid_shift_ratio=(
                self._preset.offgrid_shift_ratio
                + offgrid_boost
                + aspect_offgrid
                + corridor_offgrid
            ),
            diagonal_fan_ratio=(
                self._preset.diagonal_fan_ratio
                + fan_boost
                + aspect_fan
                + corridor_fan
            ),
        )

        plan = build_vector_plan(signals, preset)

        dxf_path = output_dir / f"{conv_input.image_path.stem}.dxf"
        export_plan_as_dxf(dxf_path, plan, layer="THESIS")

        metrics = estimate_metrics(signals, preset, consensus_score=0.56)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=dxf_path,
            success=True,
            elapsed_ms=0.0,
            metrics=metrics,
            notes=["정(thesis): two-stage baseline"] + plan.notes,
        )
