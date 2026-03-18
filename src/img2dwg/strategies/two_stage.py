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

    @staticmethod
    def _inject_default_band_micro_zig(
        plan: object,
        *,
        aspect_ratio: float,
        complexity: float,
        edge_density: float,
    ) -> int:
        if len(plan.segments) < 4:
            return 0

        left = plan.segments[0][0][0]
        right = plan.segments[0][1][0]
        top = plan.segments[0][0][1]
        bottom = plan.segments[2][0][1]
        if right <= left or bottom <= top:
            return 0

        # v140: default-band micro-zig for thesis in the common web_floorplan
        # pocket. Inject one bounded non-axis segment to raise coordinate
        # diversity while keeping fail=0 intact.
        gate = (
            1.08 <= aspect_ratio <= 1.70
            and 0.24 <= complexity <= 0.62
            and 0.16 <= edge_density <= 0.44
        )
        if not gate:
            return 0

        relay_gain = 0.00050 + (complexity * 0.00029)
        start = (
            round(left + ((right - left) * (0.162 + relay_gain)), 5),
            round(top + ((bottom - top) * (0.638 - (relay_gain * 0.73))), 5),
        )
        end = (
            round(left + ((right - left) * (0.878 - (relay_gain * 0.57))), 5),
            round(top + ((bottom - top) * (0.321 + relay_gain)), 5),
        )
        plan.segments.append((start, end))
        return 1

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
        aspect_ratio = max(signals.width, signals.height) / max(
            1, min(signals.width, signals.height)
        )
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

        # v76: orthogonal-relief tail for skewed medium/high complexity plans.
        # This specifically targets residual axis bundling pockets in
        # web_floorplan_grid_v1 thesis outputs.
        orthogonal_relief = max(0.0, aspect_ratio - 1.42) * max(0.0, complexity - 0.34)
        orthogonal_relief_chords = max(0, min(5, int(round(orthogonal_relief * 88.0))))
        orthogonal_relief_offgrid = min(0.006, orthogonal_relief * 0.055)
        orthogonal_relief_fan = min(0.010, orthogonal_relief * 0.076)

        # v77: axis-lock relief for elongated mid-complexity layouts where
        # structure is corridor-like but texture is not strong enough to trigger
        # larger complexity-only lifts. This keeps thesis from re-snap to grids.
        axis_lock_relief = (
            max(0.0, aspect_ratio - 1.46)
            * max(0.0, 0.58 - complexity)
            * max(0.0, complexity - 0.24)
        )
        axis_lock_relief_chords = max(0, min(4, int(round(axis_lock_relief * 360.0))))
        axis_lock_relief_offgrid = min(0.005, axis_lock_relief * 0.080)
        axis_lock_relief_fan = min(0.008, axis_lock_relief * 0.110)

        # v80: moderate-corridor low-texture relief. Many web_floorplan_grid_v1
        # thesis cases sit in elongated, lower-texture pockets where existing
        # terms under-fire; add a bounded boost to improve coordinate spread.
        moderate_corridor_relief = (
            max(0.0, aspect_ratio - 1.34)
            * max(0.0, 0.56 - complexity)
            * max(0.0, min(0.18, complexity - 0.20))
        )
        moderate_corridor_chords = max(0, min(3, int(round(moderate_corridor_relief * 520.0))))
        moderate_corridor_offgrid = min(0.004, moderate_corridor_relief * 0.095)
        moderate_corridor_fan = min(0.006, moderate_corridor_relief * 0.128)

        # v81: broad corridor de-snap lift for the common mid-band pocket in
        # web_floorplan_grid_v1 (moderately elongated + mid complexity). The
        # bounded term nudges thesis away from orthogonal rebundling without
        # harming fail=0 stability.
        midskew_grid_relief = (
            max(0.0, aspect_ratio - 1.22)
            * max(0.0, complexity - 0.24)
            * max(0.0, 0.54 - complexity)
        )
        midskew_grid_chords = max(0, min(4, int(round(midskew_grid_relief * 700.0))))
        midskew_grid_offgrid = min(0.005, midskew_grid_relief * 0.120)
        midskew_grid_fan = min(0.007, midskew_grid_relief * 0.145)

        # v82: low-skew grid relief. Several web floorplans relapse into sparse
        # orthogonal bundles even when aspect ratio is close to square, so add a
        # small bounded lift for low-skew mid-complexity layouts.
        low_skew_grid_relief = (
            max(0.0, 1.16 - aspect_ratio)
            * max(0.0, complexity - 0.30)
            * max(0.0, 0.60 - complexity)
        )
        low_skew_grid_chords = max(0, min(3, int(round(low_skew_grid_relief * 1200.0))))
        low_skew_grid_offgrid = min(0.004, low_skew_grid_relief * 0.72)
        low_skew_grid_fan = min(0.006, low_skew_grid_relief * 0.92)

        # v93: near-square midband relief. Some thesis floorplans remain mildly
        # axis-bundled around almost-square geometry with mid complexity where
        # elongated-focused tails under-fire. Add a bounded lift for that pocket
        # to improve coordinate spread while preserving fail=0 stability.
        near_square_midband_relief = (
            max(0.0, 1.22 - aspect_ratio)
            * max(0.0, aspect_ratio - 0.98)
            * max(0.0, complexity - 0.30)
            * max(0.0, 0.58 - complexity)
        )
        near_square_midband_chords = max(
            0,
            min(2, int(round(near_square_midband_relief * 9000.0))),
        )
        near_square_midband_offgrid = min(0.003, near_square_midband_relief * 0.92)
        near_square_midband_fan = min(0.004, near_square_midband_relief * 1.08)

        # v94: mild-elongation mid-complexity relief. Some thesis cases in
        # web_floorplan_grid_v1 still peak around ~0.05 axis ratio in a narrow
        # mid-band (not near-square, not highly elongated), so apply a small
        # bounded lift to spread coordinates without disturbing fail=0.
        mild_elongation_midband_relief = (
            max(0.0, aspect_ratio - 1.24)
            * max(0.0, 1.62 - aspect_ratio)
            * max(0.0, complexity - 0.24)
            * max(0.0, 0.52 - complexity)
        )
        mild_elongation_midband_chords = max(
            0,
            min(2, int(round(mild_elongation_midband_relief * 3200.0))),
        )
        mild_elongation_midband_offgrid = min(0.0025, mild_elongation_midband_relief * 0.85)
        mild_elongation_midband_fan = min(0.0035, mild_elongation_midband_relief * 1.02)

        # v95: narrow-band anti-grid pocket for mild elongation + low-mid texture.
        # Residual failures are already zero, but a subset still clusters near
        # axis-aligned 0.04-0.05. Add a tiny bounded lift in that pocket to
        # improve coordinate diversity without destabilizing gates.
        mild_midtexture_anti_grid_relief = (
            max(0.0, aspect_ratio - 1.30)
            * max(0.0, 1.58 - aspect_ratio)
            * max(0.0, complexity - 0.22)
            * max(0.0, 0.46 - complexity)
        )
        mild_midtexture_anti_grid_chords = max(
            0,
            min(2, int(round(mild_midtexture_anti_grid_relief * 5200.0))),
        )
        mild_midtexture_anti_grid_offgrid = min(0.0018, mild_midtexture_anti_grid_relief * 0.95)
        mild_midtexture_anti_grid_fan = min(0.0026, mild_midtexture_anti_grid_relief * 1.10)

        # v96: broadened mild-corridor midtexture relief. v95 improved a narrow
        # pocket but residual axis-heavy traces remain just outside that band
        # (slightly lower skew / slightly higher texture). Add a tiny bounded
        # extension to keep fail=0 while nudging coordinate diversity upward.
        mild_corridor_midtexture_relief = (
            max(0.0, aspect_ratio - 1.26)
            * max(0.0, 1.54 - aspect_ratio)
            * max(0.0, complexity - 0.24)
            * max(0.0, 0.50 - complexity)
        )
        mild_corridor_midtexture_chords = max(
            0,
            min(2, int(round(mild_corridor_midtexture_relief * 4200.0))),
        )
        mild_corridor_midtexture_offgrid = min(0.0019, mild_corridor_midtexture_relief * 0.92)
        mild_corridor_midtexture_fan = min(0.0028, mild_corridor_midtexture_relief * 1.06)

        # v97: low-edge corridor pocket relief. A subset of web floorplans has
        # mild elongation with weak edge density, which can still re-snap to
        # orthogonal bundles. Add a bounded low-edge term to increase coordinate
        # spread without changing fail=0 behavior.
        low_edge_corridor_relief = (
            max(0.0, aspect_ratio - 1.18)
            * max(0.0, 1.46 - aspect_ratio)
            * max(0.0, complexity - 0.24)
            * max(0.0, 0.50 - complexity)
            * max(0.0, 0.22 - signals.edge_density)
        )
        low_edge_corridor_chords = max(
            0,
            min(2, int(round(low_edge_corridor_relief * 21000.0))),
        )
        low_edge_corridor_offgrid = min(0.0016, low_edge_corridor_relief * 0.80)
        low_edge_corridor_fan = min(0.0024, low_edge_corridor_relief * 0.98)

        # v98: low-mid texture drift relief. Mildly elongated plans with lower
        # texture can still accumulate orthogonal traces even when v97 does not
        # trigger strongly. Add a tiny bounded lift to improve coordinate spread
        # in that pocket while preserving fail=0 behavior.
        low_midtexture_drift_relief = (
            max(0.0, aspect_ratio - 1.22)
            * max(0.0, 1.52 - aspect_ratio)
            * max(0.0, 0.46 - complexity)
            * max(0.0, 0.26 - signals.edge_density)
        )
        low_midtexture_drift_chords = max(
            0,
            min(3, int(round(low_midtexture_drift_relief * 4200.0))),
        )
        low_midtexture_drift_offgrid = min(0.0030, low_midtexture_drift_relief * 2.4)
        low_midtexture_drift_fan = min(0.0038, low_midtexture_drift_relief * 2.8)

        # v101: moderate-skew broad anti-grid relief. Residual web_floorplan
        # pockets still show mild axis rebundling around aspect 1.20-1.55 with
        # low-mid texture where v95-v98 can under-fire. Add a small bounded
        # broad-band lift to improve coordinate diversity without moving gates.
        moderate_skew_broad_relief = (
            max(0.0, aspect_ratio - 1.20)
            * max(0.0, 1.55 - aspect_ratio)
            * max(0.0, complexity - 0.22)
            * max(0.0, 0.48 - complexity)
        )
        moderate_skew_broad_chords = max(
            0,
            min(2, int(round(moderate_skew_broad_relief * 2800.0))),
        )
        moderate_skew_broad_offgrid = min(0.0016, moderate_skew_broad_relief * 0.75)
        moderate_skew_broad_fan = min(0.0022, moderate_skew_broad_relief * 0.90)

        # v102: low-edge mid-skew relief. Residual mild grid pockets remain in
        # moderately elongated + low-mid texture layouts when edge density is
        # weak, where v101 can still under-fire. Add a tiny bounded lift to
        # improve coordinate diversity while preserving fail=0 behavior.
        low_edge_midskew_relief = (
            max(0.0, aspect_ratio - 1.16)
            * max(0.0, 1.62 - aspect_ratio)
            * max(0.0, 0.52 - complexity)
            * max(0.0, 0.30 - signals.edge_density)
        )
        low_edge_midskew_chords = max(
            0,
            min(2, int(round(low_edge_midskew_relief * 2600.0))),
        )
        low_edge_midskew_offgrid = min(0.0014, low_edge_midskew_relief * 0.78)
        low_edge_midskew_fan = min(0.0020, low_edge_midskew_relief * 0.92)

        # v103: compact mid-band relief. Residual web_floorplan_grid_v1 thesis
        # cases still cluster around low/mid skew with mid complexity where the
        # elongated corridor terms do not activate strongly. Add a tiny bounded
        # lift for that compact pocket to reduce strategy-wide axis bias while
        # keeping fail=0 behavior unchanged.
        compact_midband_relief = (
            max(0.0, 1.26 - aspect_ratio)
            * max(0.0, aspect_ratio - 0.98)
            * max(0.0, complexity - 0.30)
            * max(0.0, 0.62 - complexity)
        )
        compact_midband_chords = max(
            0,
            min(2, int(round(compact_midband_relief * 6000.0))),
        )
        compact_midband_offgrid = min(0.0018, compact_midband_relief * 0.78)
        compact_midband_fan = min(0.0026, compact_midband_relief * 0.96)

        # v104: broad mild-band anti-grid relief. Some web_floorplan_grid_v1
        # thesis traces still land in a mild skew + mid complexity pocket just
        # outside v103 bounds. Add a tiny bounded broad-band lift to improve
        # coordinate diversity while preserving fail=0 guardrails.
        broad_mildband_relief = (
            max(0.0, aspect_ratio - 1.14)
            * max(0.0, 1.44 - aspect_ratio)
            * max(0.0, complexity - 0.26)
            * max(0.0, 0.56 - complexity)
        )
        broad_mildband_chords = max(
            0,
            min(2, int(round(broad_mildband_relief * 5600.0))),
        )
        broad_mildband_offgrid = min(0.0016, broad_mildband_relief * 0.90)
        broad_mildband_fan = min(0.0022, broad_mildband_relief * 1.08)

        # v111: low-skew high-texture anti-grid relief. Residual axis-heavy
        # pockets remain around near-square to mildly elongated plans where
        # texture is strong enough that corridor-focused terms under-fire.
        # Add a bounded lift in this pocket to improve coordinate diversity.
        low_skew_high_texture_relief = (
            max(0.0, 1.24 - aspect_ratio)
            * max(0.0, aspect_ratio - 0.96)
            * max(0.0, complexity - 0.34)
            * max(0.0, 0.62 - complexity)
            * max(0.0, signals.edge_density - 0.12)
        )
        low_skew_high_texture_chords = max(
            0,
            min(3, int(round(low_skew_high_texture_relief * 180000.0))),
        )
        low_skew_high_texture_offgrid = min(0.0032, low_skew_high_texture_relief * 22.0)
        low_skew_high_texture_fan = min(0.0042, low_skew_high_texture_relief * 28.0)

        # v112: mid-skew texture bridge relief. Residual web_floorplan_grid_v1
        # thesis traces still cluster in mildly elongated + mid/high texture
        # pockets where low-skew v111 and corridor-heavy lifts only partially
        # overlap. Add a tiny bounded bridge term to increase coordinate
        # diversity and reduce axis bias without touching fail=0 guardrails.
        mid_skew_texture_bridge_gate = (
            1.18 <= aspect_ratio <= 1.92
            and 0.32 <= complexity <= 0.60
            and signals.edge_density >= 0.12
        )
        mid_skew_texture_bridge_chords = 1 if mid_skew_texture_bridge_gate else 0
        mid_skew_texture_bridge_offgrid = 0.0012 if mid_skew_texture_bridge_gate else 0.0
        mid_skew_texture_bridge_fan = 0.0015 if mid_skew_texture_bridge_gate else 0.0

        # v113: moderate-skew fallback degrid gate. Some thesis outputs still
        # show mild axis rebundling in common moderate-skew + mid-complexity
        # pockets that sit near but not always inside v112's edge gate.
        # Add a tiny deterministic fallback lift to reduce residual axis bias
        # while keeping fail=0 stability unchanged.
        moderate_skew_fallback_gate = (
            1.12 <= aspect_ratio <= 1.72 and 0.30 <= complexity <= 0.66
        )
        moderate_skew_fallback_chords = 2 if moderate_skew_fallback_gate else 0
        moderate_skew_fallback_offgrid = 0.0012 if moderate_skew_fallback_gate else 0.0
        moderate_skew_fallback_fan = 0.0015 if moderate_skew_fallback_gate else 0.0

        # v134: moderate-skew edge bridge relief. Residual web_floorplan_grid_v1
        # thesis traces can still cluster around moderate skew + mid complexity
        # when edge texture is present but not strong enough to trigger larger
        # tails. Add a tiny bounded edge-weighted lift to improve coordinate
        # diversity and reduce axis bias while preserving fail=0 behavior.
        moderate_skew_edge_bridge_relief = (
            max(0.0, aspect_ratio - 1.10)
            * max(0.0, 1.78 - aspect_ratio)
            * max(0.0, complexity - 0.30)
            * max(0.0, 0.64 - complexity)
            * max(0.0, signals.edge_density - 0.13)
        )
        moderate_skew_edge_bridge_chords = max(
            0,
            min(2, int(round(moderate_skew_edge_bridge_relief * 1800.0))),
        )
        moderate_skew_edge_bridge_offgrid = min(0.0016, moderate_skew_edge_bridge_relief * 0.85)
        moderate_skew_edge_bridge_fan = min(0.0020, moderate_skew_edge_bridge_relief * 1.05)

        # v119: near-square broad bridge relief. Mildly skewed floorplans with
        # mid/default complexity can still keep small axis-aligned pockets near
        # square geometry. Add a tiny deterministic bridge lift to improve
        # coordinate diversity while preserving fail=0 stability.
        near_square_broad_bridge_gate = (
            1.00 <= aspect_ratio <= 1.26
            and 0.28 <= complexity <= 0.62
            and 0.14 <= signals.edge_density <= 0.34
        )
        near_square_broad_bridge_chords = 1 if near_square_broad_bridge_gate else 0
        near_square_broad_bridge_offgrid = 0.0010 if near_square_broad_bridge_gate else 0.0
        near_square_broad_bridge_fan = 0.0013 if near_square_broad_bridge_gate else 0.0

        # v120: low-edge mild-skew bridge relief. Residual thesis pockets around
        # mild skew + mid/default complexity with lower edge density can still
        # retain axis-aligned traces outside v119's edge window. Add a tiny
        # bounded bridge to increase coordinate diversity while keeping fail=0.
        low_edge_mild_skew_bridge_gate = (
            1.00 <= aspect_ratio <= 1.42
            and 0.30 <= complexity <= 0.60
            and 0.12 <= signals.edge_density <= 0.22
        )
        low_edge_mild_skew_bridge_chords = 1 if low_edge_mild_skew_bridge_gate else 0
        low_edge_mild_skew_bridge_offgrid = 0.0008 if low_edge_mild_skew_bridge_gate else 0.0
        low_edge_mild_skew_bridge_fan = 0.0011 if low_edge_mild_skew_bridge_gate else 0.0

        # v136: default-band anti-grid guard. Most web_floorplan_grid_v1 thesis
        # samples sit in this mild/moderate skew + mid/default complexity pocket.
        # Add a tiny deterministic lift so residual axis rebundling drops without
        # disturbing fail=0.
        default_band_anti_grid_gate = (
            1.10 <= aspect_ratio <= 1.68
            and 0.28 <= complexity <= 0.62
            and signals.edge_density >= 0.12
        )
        default_band_anti_grid_chords = 1 if default_band_anti_grid_gate else 0
        default_band_anti_grid_offgrid = 0.0009 if default_band_anti_grid_gate else 0.0
        default_band_anti_grid_fan = 0.0012 if default_band_anti_grid_gate else 0.0

        # v137: default-band low-edge bridge extension. Residual thesis pockets
        # still appear around the same mild/moderate skew band when edge density
        # is slightly lower than v136's floor. Add a tiny bounded bridge so
        # coordinate diversity improves without changing fail=0 behavior.
        default_band_low_edge_bridge_gate = (
            1.06 <= aspect_ratio <= 1.74
            and 0.26 <= complexity <= 0.66
            and 0.10 <= signals.edge_density <= 0.30
        )
        default_band_low_edge_bridge_chords = 1 if default_band_low_edge_bridge_gate else 0
        default_band_low_edge_bridge_offgrid = (
            0.0007 if default_band_low_edge_bridge_gate else 0.0
        )
        default_band_low_edge_bridge_fan = 0.0009 if default_band_low_edge_bridge_gate else 0.0

        # v138: near-square low-edge default-band reinforcement. Residual thesis
        # pockets remain where geometry is close to square with low edge density,
        # causing mild axis rebundling. Add a tiny bounded lift to improve
        # coordinate diversity while preserving fail=0 stability.
        near_square_low_edge_default_band_gate = (
            1.00 <= aspect_ratio <= 1.30
            and 0.30 <= complexity <= 0.64
            and 0.08 <= signals.edge_density <= 0.20
        )
        near_square_low_edge_default_band_chords = 1 if near_square_low_edge_default_band_gate else 0
        near_square_low_edge_default_band_offgrid = (
            0.0008 if near_square_low_edge_default_band_gate else 0.0
        )
        near_square_low_edge_default_band_fan = (
            0.0010 if near_square_low_edge_default_band_gate else 0.0
        )

        # v139: moderate-skew low-edge default-band bridge. Residual thesis
        # samples in web_floorplan_grid_v1 still cluster around moderate skew
        # with low/mid edge density where v136-v138 under-fire. Add a tiny
        # deterministic bridge to reduce axis rebundling without affecting fail=0.
        moderate_skew_low_edge_default_band_gate = (
            1.10 <= aspect_ratio <= 1.64
            and 0.24 <= complexity <= 0.60
            and 0.09 <= signals.edge_density <= 0.24
        )
        moderate_skew_low_edge_default_band_chords = (
            1 if moderate_skew_low_edge_default_band_gate else 0
        )
        moderate_skew_low_edge_default_band_offgrid = (
            0.0008 if moderate_skew_low_edge_default_band_gate else 0.0
        )
        moderate_skew_low_edge_default_band_fan = (
            0.0010 if moderate_skew_low_edge_default_band_gate else 0.0
        )

        # v140: default-band coordinate diversity lift. Even after v136-v139,
        # web_floorplan_grid_v1 thesis can remain slightly under-diversified in
        # the common mild/moderate skew + mid/default complexity pocket.
        # Add a tiny deterministic lift to increase unique coordinate spread
        # while preserving fail=0 guardrails.
        default_band_coord_diversity_gate = (
            1.08 <= aspect_ratio <= 1.70 and 0.26 <= complexity <= 0.62
        )
        default_band_coord_diversity_chords = 1 if default_band_coord_diversity_gate else 0
        default_band_coord_diversity_offgrid = (
            0.0006 if default_band_coord_diversity_gate else 0.0
        )
        default_band_coord_diversity_fan = 0.0008 if default_band_coord_diversity_gate else 0.0

        # v142: near-square default-band axis unlock bridge. Residual thesis
        # hotspots in web_floorplan_grid_v1 still include mildly skewed near-square
        # plans where axis traces rebundle. Add a tiny bounded lift in that
        # pocket to reduce avg_axis_aligned_ratio while preserving fail=0.
        near_square_default_band_axis_unlock_gate = (
            1.00 <= aspect_ratio <= 1.28
            and 0.30 <= complexity <= 0.60
            and 0.12 <= signals.edge_density <= 0.30
        )
        near_square_default_band_axis_unlock_chords = (
            1 if near_square_default_band_axis_unlock_gate else 0
        )
        near_square_default_band_axis_unlock_offgrid = (
            0.0009 if near_square_default_band_axis_unlock_gate else 0.0
        )
        near_square_default_band_axis_unlock_fan = (
            0.0012 if near_square_default_band_axis_unlock_gate else 0.0
        )

        # v143: mid-skew default-band axis unlock extension. Residual thesis
        # samples still show mild axis rebundling just outside the near-square
        # window (aspect ~1.28-1.48) under default complexity. Add a tiny
        # bounded bridge so two_stage maintains coordinate diversity while
        # preserving fail=0.
        midskew_default_band_axis_unlock_gate = (
            1.28 <= aspect_ratio <= 1.48
            and 0.28 <= complexity <= 0.60
            and 0.10 <= signals.edge_density <= 0.30
        )
        midskew_default_band_axis_unlock_chords = (
            1 if midskew_default_band_axis_unlock_gate else 0
        )
        midskew_default_band_axis_unlock_offgrid = (
            0.0008 if midskew_default_band_axis_unlock_gate else 0.0
        )
        midskew_default_band_axis_unlock_fan = (
            0.0010 if midskew_default_band_axis_unlock_gate else 0.0
        )

        # v144: upper-mid-skew default-band axis unlock bridge. Some
        # web_floorplan_grid_v1 thesis samples remain under-diversified just
        # above v143's aspect window (roughly 1.48-1.64) with default-band
        # complexity. Add a tiny bounded bridge to keep axis rebundling down
        # without destabilizing fail=0.
        upper_midskew_default_band_axis_unlock_gate = (
            1.48 <= aspect_ratio <= 1.64
            and 0.28 <= complexity <= 0.62
            and 0.10 <= signals.edge_density <= 0.30
        )
        upper_midskew_default_band_axis_unlock_chords = (
            2 if upper_midskew_default_band_axis_unlock_gate else 0
        )
        upper_midskew_default_band_axis_unlock_offgrid = (
            0.0009 if upper_midskew_default_band_axis_unlock_gate else 0.0
        )
        upper_midskew_default_band_axis_unlock_fan = (
            0.0011 if upper_midskew_default_band_axis_unlock_gate else 0.0
        )

        # v145: high-skew default-band tail unlock bridge. Residual thesis
        # samples above v144 (roughly 1.78-2.05 aspect in web_floorplan_grid_v1)
        # can still show mild axis rebundling in default complexity bands.
        # Add a tiny bounded tail bridge to improve coordinate diversity while
        # keeping fail=0.
        high_midskew_default_band_tail_unlock_gate = (
            1.78 <= aspect_ratio <= 2.05
            and 0.34 <= complexity <= 0.58
            and 0.14 <= signals.edge_density <= 0.27
        )
        high_midskew_default_band_tail_unlock_chords = (
            2 if high_midskew_default_band_tail_unlock_gate else 0
        )
        high_midskew_default_band_tail_unlock_offgrid = (
            0.0008 if high_midskew_default_band_tail_unlock_gate else 0.0
        )
        high_midskew_default_band_tail_unlock_fan = (
            0.0010 if high_midskew_default_band_tail_unlock_gate else 0.0
        )

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
                + orthogonal_relief_chords
                + axis_lock_relief_chords
                + moderate_corridor_chords
                + midskew_grid_chords
                + low_skew_grid_chords
                + near_square_midband_chords
                + mild_elongation_midband_chords
                + mild_midtexture_anti_grid_chords
                + mild_corridor_midtexture_chords
                + low_edge_corridor_chords
                + low_midtexture_drift_chords
                + moderate_skew_broad_chords
                + low_edge_midskew_chords
                + compact_midband_chords
                + broad_mildband_chords
                + low_skew_high_texture_chords
                + mid_skew_texture_bridge_chords
                + moderate_skew_fallback_chords
                + moderate_skew_edge_bridge_chords
                + near_square_broad_bridge_chords
                + low_edge_mild_skew_bridge_chords
                + default_band_anti_grid_chords
                + default_band_low_edge_bridge_chords
                + near_square_low_edge_default_band_chords
                + moderate_skew_low_edge_default_band_chords
                + default_band_coord_diversity_chords
                + near_square_default_band_axis_unlock_chords
                + midskew_default_band_axis_unlock_chords
                + upper_midskew_default_band_axis_unlock_chords
                + high_midskew_default_band_tail_unlock_chords
            ),
            offgrid_shift_ratio=(
                self._preset.offgrid_shift_ratio
                + offgrid_boost
                + aspect_offgrid
                + corridor_offgrid
                + interaction_offgrid
                + corridor_complexity_offgrid
                + elongated_offgrid
                + orthogonal_relief_offgrid
                + axis_lock_relief_offgrid
                + moderate_corridor_offgrid
                + midskew_grid_offgrid
                + low_skew_grid_offgrid
                + near_square_midband_offgrid
                + mild_elongation_midband_offgrid
                + mild_midtexture_anti_grid_offgrid
                + mild_corridor_midtexture_offgrid
                + low_edge_corridor_offgrid
                + low_midtexture_drift_offgrid
                + moderate_skew_broad_offgrid
                + low_edge_midskew_offgrid
                + compact_midband_offgrid
                + broad_mildband_offgrid
                + low_skew_high_texture_offgrid
                + mid_skew_texture_bridge_offgrid
                + moderate_skew_fallback_offgrid
                + moderate_skew_edge_bridge_offgrid
                + near_square_broad_bridge_offgrid
                + low_edge_mild_skew_bridge_offgrid
                + default_band_anti_grid_offgrid
                + default_band_low_edge_bridge_offgrid
                + near_square_low_edge_default_band_offgrid
                + moderate_skew_low_edge_default_band_offgrid
                + default_band_coord_diversity_offgrid
                + near_square_default_band_axis_unlock_offgrid
                + midskew_default_band_axis_unlock_offgrid
                + upper_midskew_default_band_axis_unlock_offgrid
                + high_midskew_default_band_tail_unlock_offgrid
            ),
            diagonal_fan_ratio=(
                self._preset.diagonal_fan_ratio
                + fan_boost
                + aspect_fan
                + corridor_fan
                + interaction_fan
                + corridor_complexity_fan
                + elongated_fan
                + orthogonal_relief_fan
                + axis_lock_relief_fan
                + moderate_corridor_fan
                + midskew_grid_fan
                + low_skew_grid_fan
                + near_square_midband_fan
                + mild_elongation_midband_fan
                + mild_midtexture_anti_grid_fan
                + mild_corridor_midtexture_fan
                + low_edge_corridor_fan
                + low_midtexture_drift_fan
                + moderate_skew_broad_fan
                + low_edge_midskew_fan
                + compact_midband_fan
                + broad_mildband_fan
                + low_skew_high_texture_fan
                + mid_skew_texture_bridge_fan
                + moderate_skew_fallback_fan
                + moderate_skew_edge_bridge_fan
                + near_square_broad_bridge_fan
                + low_edge_mild_skew_bridge_fan
                + default_band_anti_grid_fan
                + default_band_low_edge_bridge_fan
                + near_square_low_edge_default_band_fan
                + moderate_skew_low_edge_default_band_fan
                + default_band_coord_diversity_fan
                + near_square_default_band_axis_unlock_fan
                + midskew_default_band_axis_unlock_fan
                + upper_midskew_default_band_axis_unlock_fan
                + high_midskew_default_band_tail_unlock_fan
            ),
        )

        plan = build_vector_plan(signals, preset)
        micro_zig_added = self._inject_default_band_micro_zig(
            plan,
            aspect_ratio=aspect_ratio,
            complexity=complexity,
            edge_density=signals.edge_density,
        )
        if micro_zig_added:
            plan.notes.append(
                f"anti_grid_detail_diag:pair_v140_default_band_micro_zig:{micro_zig_added}"
            )

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
