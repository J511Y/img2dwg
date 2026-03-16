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
        aspect_ratio = max(signals.width, signals.height) / max(
            1, min(signals.width, signals.height)
        )
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

        # v74: bridge-band relief for moderately elongated corridor plans in the
        # mid-confidence pocket (aspect around 1.45~1.70).
        bridge_mid_confidence = (
            max(0.0, aspect_ratio - 1.42)
            * max(0.0, complexity - 0.44)
            * max(0.0, min(0.20, 0.83 - consensus_score))
        )
        bridge_mid_confidence_chords = max(0, min(3, int(round(bridge_mid_confidence * 240.0))))
        bridge_mid_confidence_offgrid = min(0.004, bridge_mid_confidence * 0.090)
        bridge_mid_confidence_fan = min(0.006, bridge_mid_confidence * 0.105)

        # v75: skew-complexity interaction lift. Dense, elongated layouts still
        # show occasional axis rebundling at mid/high confidence; inject a small
        # bounded interaction bonus to bias antithesis away from axis grids.
        skew_complexity_interaction = (
            max(0.0, aspect_ratio - 1.36)
            * max(0.0, complexity - 0.46)
            * max(0.0, min(0.26, consensus_score - 0.68))
        )
        skew_complexity_chords = max(0, min(4, int(round(skew_complexity_interaction * 380.0))))
        skew_complexity_offgrid = min(0.006, skew_complexity_interaction * 0.095)
        skew_complexity_fan = min(0.006, skew_complexity_interaction * 0.110)

        # v78: axis-lock proxy lift. High-consensus elongated layouts with lower
        # texture complexity can still settle into orthogonal bundles; apply a
        # bounded relief signal so consensus_qa keeps coordinate diversity.
        axis_lock_proxy = (
            max(0.0, aspect_ratio - 1.58)
            * max(0.0, 0.60 - complexity)
            * max(0.0, min(0.24, consensus_score - 0.74))
        )
        axis_lock_proxy_chords = max(0, min(3, int(round(axis_lock_proxy * 310.0))))
        axis_lock_proxy_offgrid = min(0.004, axis_lock_proxy * 0.115)
        axis_lock_proxy_fan = min(0.005, axis_lock_proxy * 0.120)

        # v79: most web_floorplan_grid_v1 consensus cases still land near the
        # default 0.71 score, so the higher-confidence relief packs do not fire.
        # Add a bounded moderate-consensus lift for elongated, lower-texture
        # layouts to preserve coordinate diversity without risking fail=0.
        moderate_consensus_corridor_relief = (
            max(0.0, aspect_ratio - 1.38)
            * max(0.0, 0.60 - complexity)
            * max(0.0, min(0.10, consensus_score - 0.68))
        )
        moderate_consensus_corridor_chords = max(
            0,
            min(2, int(round(moderate_consensus_corridor_relief * 950.0))),
        )
        moderate_consensus_corridor_offgrid = min(
            0.004,
            moderate_consensus_corridor_relief * 0.38,
        )
        moderate_consensus_corridor_fan = min(
            0.005,
            moderate_consensus_corridor_relief * 0.46,
        )

        # v83: mid-band square-plan relief. In web_floorplan_grid_v1, consensus
        # around default (≈0.7) with only mild elongation can still re-snap into
        # orthogonal bundles. Add a tiny bounded lift focused on that pocket.
        midband_square_relief = (
            max(0.0, aspect_ratio - 1.14)
            * max(0.0, 1.32 - aspect_ratio)
            * max(0.0, complexity - 0.32)
            * max(0.0, 0.58 - complexity)
            * max(0.0, consensus_score - 0.69)
            * max(0.0, 0.78 - consensus_score)
        )
        midband_square_chords = max(0, min(2, int(round(midband_square_relief * 12000.0))))
        midband_square_offgrid = min(0.003, midband_square_relief * 0.95)
        midband_square_fan = min(0.004, midband_square_relief * 1.20)

        elongated_consensus_floor = max(0.0, aspect_ratio - 1.24) * max(
            0.0, min(0.22, consensus_score - 0.70)
        )
        elongated_floor_chords = max(0, min(2, int(round(elongated_consensus_floor * 90.0))))
        elongated_floor_offgrid = min(0.003, elongated_consensus_floor * 0.060)

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
                + bridge_mid_confidence_chords
                + skew_complexity_chords
                + axis_lock_proxy_chords
                + moderate_consensus_corridor_chords
                + midband_square_chords
                + elongated_floor_chords
                + 4
            ),
            offgrid_shift_ratio=(
                preset.offgrid_shift_ratio
                + min(0.028, complexity * 0.026)
                + min(0.014, max(0.0, (aspect_ratio - 1.12) * 0.016))
                + min(0.010, max(0.0, (aspect_ratio - 1.55) * 0.014))
                + min(0.006, complexity * 0.004)
                + confident_corridor_tail
                + bridge_mid_confidence_offgrid
                + skew_complexity_offgrid
                + axis_lock_proxy_offgrid
                + moderate_consensus_corridor_offgrid
                + midband_square_offgrid
                + elongated_floor_offgrid
            ),
            diagonal_fan_ratio=(
                preset.diagonal_fan_ratio
                + min(0.034, max(0.0, (aspect_ratio - 1.08) * 0.026))
                + min(0.016, max(0.0, (aspect_ratio - 1.55) * 0.020))
                + min(0.008, complexity * 0.005)
                + min(0.012, confident_corridor_tail * 1.1)
                + bridge_mid_confidence_fan
                + skew_complexity_fan
                + axis_lock_proxy_fan
                + moderate_consensus_corridor_fan
                + midband_square_fan
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
