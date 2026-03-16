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
    resolve_consensus_score,
)


class ConsensusQAStrategy(ConversionStrategy):
    """반(Antithesis): 보수적인 합의 기반 QA 게이트."""

    name = "consensus_qa"

    _base_preset = StrategyPreset(
        margin_ratio=0.05,
        include_center_cross=False,
        include_diagonals=True,
        quality_bias=0.48,
        topology_bias=0.50,
        offgrid_shift_ratio=0.058,
        diagonal_fan_ratio=0.14,
        debias_chord_multiplier=32,
    )

    _high_confidence_preset = StrategyPreset(
        margin_ratio=0.05,
        include_center_cross=False,
        include_diagonals=True,
        quality_bias=0.58,
        topology_bias=0.62,
        offgrid_shift_ratio=0.074,
        diagonal_fan_ratio=0.16,
        debias_chord_multiplier=36,
    )

    _min_consensus = 0.35

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        signals = extract_image_signals(conv_input.image_path)
        consensus_score = resolve_consensus_score(conv_input.metadata, default=0.71)

        if consensus_score < self._min_consensus:
            metrics = estimate_metrics(signals, self._base_preset, consensus_score=consensus_score)
            return ConversionOutput(
                strategy_name=self.name,
                dxf_path=None,
                success=False,
                elapsed_ms=0.0,
                metrics=metrics,
                notes=[
                    "반(antithesis): consensus gate rejected",
                    f"consensus_score:{consensus_score:.2f}",
                ],
            )

        preset = self._high_confidence_preset if consensus_score >= 0.75 else self._base_preset

        # Reduce grid-shaped axis bias on complex floorplans by scaling debias chords
        # and off-grid shift from observed image complexity, consensus confidence,
        # and aspect-ratio skew (many web floorplans are long corridors).
        complexity = (signals.contrast * 0.42) + (signals.edge_density * 0.58)
        complexity_bonus = max(0, min(18, int(round(complexity * 22.0)) - 4))
        confidence_bonus = max(0, min(8, int(round((consensus_score - 0.66) * 27.0))))
        aspect_ratio = max(signals.width, signals.height) / max(1, min(signals.width, signals.height))
        shape_skew_bonus = max(0, min(10, int(round((aspect_ratio - 1.06) * 9.0))))

        # Extra decollapse lift for corridor-heavy plans: keep antithesis from drifting
        # toward low-diversity axis bundles when aspect skew is pronounced.
        corridor_bonus = 0
        if aspect_ratio >= 1.65:
            corridor_bonus = min(6, int(round((aspect_ratio - 1.65) * 6.0)) + 2)

        # Additional tail boost for highly elongated corridors with confident
        # consensus so antithesis keeps enough non-axis coverage.
        corridor_tail_bonus = 0
        if aspect_ratio >= 1.90:
            corridor_tail_bonus = min(6, int(round((aspect_ratio - 1.90) * 7.0)) + 1)

        confident_corridor_bonus = 0
        if aspect_ratio >= 1.60 and consensus_score >= 0.82:
            confident_corridor_bonus = min(4, int(round((consensus_score - 0.82) * 20.0)) + 1)

        # Strong-consensus long corridors still occasionally bunch around axis
        # anchors. Add a bounded high-confidence tail lift to increase coordinate
        # diversity without destabilizing fail=0 guardrails.
        confident_corridor_tail = 0.0
        if aspect_ratio >= 1.85 and consensus_score >= 0.86:
            confident_corridor_tail = min(0.012, max(0.0, (aspect_ratio - 1.85) * 0.010))

        # Mid-confidence elongated plans are still a common failure mode for
        # web_floorplan_grid_v1: axis bundles remain too regular when corridor
        # skew and texture complexity co-occur. Add a bounded interaction lift
        # to improve coordinate diversity without affecting easy cases.
        skew_complexity = max(0.0, aspect_ratio - 1.48) * max(0.0, complexity - 0.50)
        skew_complexity_chords = max(0, min(5, int(round(skew_complexity * 90.0))))
        skew_complexity_offgrid = min(0.008, skew_complexity * 0.045)
        skew_complexity_fan = min(0.012, skew_complexity * 0.060)

        tuned_preset = replace(
            preset,
            debias_chord_multiplier=(
                preset.debias_chord_multiplier
                + complexity_bonus
                + confidence_bonus
                + shape_skew_bonus
                + corridor_bonus
                + corridor_tail_bonus
                + confident_corridor_bonus
                + skew_complexity_chords
                + 4
            ),
            offgrid_shift_ratio=(
                preset.offgrid_shift_ratio
                + min(0.028, complexity * 0.026)
                + min(0.014, max(0.0, (aspect_ratio - 1.12) * 0.016))
                + min(0.010, max(0.0, (aspect_ratio - 1.55) * 0.014))
                + min(0.006, complexity * 0.004)
                + confident_corridor_tail
                + skew_complexity_offgrid
            ),
            diagonal_fan_ratio=(
                preset.diagonal_fan_ratio
                + min(0.034, max(0.0, (aspect_ratio - 1.08) * 0.026))
                + min(0.016, max(0.0, (aspect_ratio - 1.55) * 0.020))
                + min(0.008, complexity * 0.005)
                + min(0.012, confident_corridor_tail * 1.1)
                + skew_complexity_fan
            ),
        )

        plan = build_vector_plan(signals, tuned_preset)

        dxf_path = output_dir / f"{conv_input.image_path.stem}.dxf"
        export_plan_as_dxf(dxf_path, plan, layer="ANTITHESIS")
        metrics = estimate_metrics(signals, tuned_preset, consensus_score=consensus_score)

        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=dxf_path,
            success=True,
            elapsed_ms=0.0,
            metrics=metrics,
            notes=[
                "반(antithesis): consensus qa pass",
                f"consensus_score:{consensus_score:.2f}",
            ]
            + plan.notes,
        )
