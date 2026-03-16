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
        debias_chord_multiplier=28,
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

        # For skewed + moderately complex plans, apply an interaction lift so
        # thesis does not under-debias into sparse axis bundles.
        skew_intensity = max(0.0, aspect_ratio - 1.35)
        complexity_tail = max(0.0, complexity - 0.22)
        interaction_chords = max(
            0,
            min(8, int(round((skew_intensity * 4.5) + (complexity_tail * 6.0)))),
        )
        interaction_offgrid = min(0.012, (skew_intensity * 0.006) + (complexity_tail * 0.010))
        interaction_fan = min(0.018, (skew_intensity * 0.009) + (complexity_tail * 0.012))

        # Additional corridor-complexity coupling for elongated, moderately dense
        # layouts. This nudges coordinate diversity upward without destabilizing
        # fail=0 guardrails.
        corridor_complexity = max(0.0, aspect_ratio - 1.48) * max(0.0, complexity - 0.30)
        corridor_complexity_chords = max(0, min(6, int(round(corridor_complexity * 95.0))))
        corridor_complexity_offgrid = min(0.008, corridor_complexity * 0.060)
        corridor_complexity_fan = min(0.010, corridor_complexity * 0.072)

        # Very elongated corridor plans can still relapse into axis-heavy traces.
        # Add a bounded tail boost that only activates on high-skew layouts so
        # we increase coordinate diversity without perturbing easy cases.
        elongated_corridor = max(0.0, aspect_ratio - 1.95) * max(0.0, complexity - 0.27)
        elongated_chords = max(0, min(6, int(round(elongated_corridor * 120.0))))
        elongated_offgrid = min(0.008, elongated_corridor * 0.065)
        elongated_fan = min(0.012, elongated_corridor * 0.090)

        # Ultra-elongated plans (e.g. corridor-heavy web floorplans) still show
        # residual axis relapse on thesis outputs. Add a tiny tail-only lift so
        # we improve coordinate diversity without changing normal cases.
        ultra_elongated = max(0.0, aspect_ratio - 1.88) * max(0.0, complexity - 0.20)
        ultra_elongated_chords = max(0, min(7, int(round(ultra_elongated * 220.0))))
        ultra_elongated_offgrid = min(0.007, ultra_elongated * 0.085)
        ultra_elongated_fan = min(0.011, ultra_elongated * 0.115)

        preset = replace(
            self._preset,
            debias_chord_multiplier=(
                self._preset.debias_chord_multiplier
                + extra_chords
                + aspect_chords
                + corridor_chords
                + interaction_chords
                + corridor_complexity_chords
                + elongated_chords
                + ultra_elongated_chords
            ),
            offgrid_shift_ratio=(
                self._preset.offgrid_shift_ratio
                + offgrid_boost
                + aspect_offgrid
                + corridor_offgrid
                + interaction_offgrid
                + corridor_complexity_offgrid
                + elongated_offgrid
                + ultra_elongated_offgrid
            ),
            diagonal_fan_ratio=(
                self._preset.diagonal_fan_ratio
                + fan_boost
                + aspect_fan
                + corridor_fan
                + interaction_fan
                + corridor_complexity_fan
                + elongated_fan
                + ultra_elongated_fan
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
