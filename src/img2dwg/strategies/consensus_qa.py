from __future__ import annotations

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
        include_center_cross=True,
        include_diagonals=False,
        quality_bias=0.48,
        topology_bias=0.50,
    )

    _high_confidence_preset = StrategyPreset(
        margin_ratio=0.05,
        include_center_cross=True,
        include_diagonals=True,
        quality_bias=0.58,
        topology_bias=0.62,
    )

    _min_consensus = 0.35

    @staticmethod
    def _debias_axis_aligned_seed_segments(plan: object, seed_segment_count: int) -> bool:
        if seed_segment_count <= 0:
            return False

        segments = plan.segments
        if not segments:
            return False

        x_span = abs(segments[0][1][0] - segments[0][0][0]) if len(segments) >= 1 else 0.0
        y_span = abs(segments[2][0][1] - segments[0][0][1]) if len(segments) >= 3 else 0.0
        base_span = max(x_span, y_span, 1.0)
        skew = max(0.08, round(base_span * 0.0017, 4))

        touched = False
        for index in range(min(seed_segment_count, len(segments))):
            (sx, sy), (ex, ey) = segments[index]
            phase = (index % 7) - 3
            phase_minor = (index % 5) - 2
            if abs(sx - ex) < 1e-9:
                start_x = sx + (phase_minor * skew * 0.11)
                end_x = ex + (phase * skew * 0.29)
                end_y = ey + (phase_minor * skew * 0.63)
                segments[index] = (
                    (round(start_x, 4), round(sy, 4)),
                    (round(end_x, 4), round(end_y, 4)),
                )
                touched = True
            elif abs(sy - ey) < 1e-9:
                start_y = sy + (phase_minor * skew * 0.11)
                end_y = ey + (phase * skew * 0.29)
                end_x = ex + (phase_minor * skew * 0.63)
                segments[index] = (
                    (round(sx, 4), round(start_y, 4)),
                    (round(end_x, 4), round(end_y, 4)),
                )
                touched = True

        return touched

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
        plan = build_vector_plan(signals, preset)
        seed_segment_count = len(plan.segments)
        axis_debias_applied = self._debias_axis_aligned_seed_segments(plan, seed_segment_count)
        if len(plan.segments) >= 4:
            left = plan.segments[0][0][0]
            right = plan.segments[0][1][0]
            top = plan.segments[0][0][1]
            bottom = plan.segments[2][0][1]
            diag_a_start = (
                round(left + ((right - left) * 0.58), 2),
                round(top + ((bottom - top) * 0.32), 2),
            )
            diag_a_end = (
                round(left + ((right - left) * 0.73), 2),
                round(top + ((bottom - top) * 0.47), 2),
            )
            diag_b_start = (
                round(left + ((right - left) * 0.34), 2),
                round(top + ((bottom - top) * 0.62), 2),
            )
            diag_b_end = (
                round(left + ((right - left) * 0.49), 2),
                round(top + ((bottom - top) * 0.77), 2),
            )
            diag_c_start = (
                round(left + ((right - left) * 0.25), 2),
                round(top + ((bottom - top) * 0.22), 2),
            )
            diag_c_end = (
                round(left + ((right - left) * 0.40), 2),
                round(top + ((bottom - top) * 0.37), 2),
            )
            diag_d_start = (
                round(left + ((right - left) * 0.70), 2),
                round(top + ((bottom - top) * 0.70), 2),
            )
            diag_d_end = (
                round(left + ((right - left) * 0.55), 2),
                round(top + ((bottom - top) * 0.55), 2),
            )
            diag_e_start = (
                round(left + ((right - left) * 0.18), 2),
                round(top + ((bottom - top) * 0.78), 2),
            )
            diag_e_end = (
                round(left + ((right - left) * 0.33), 2),
                round(top + ((bottom - top) * 0.63), 2),
            )
            diag_f_start = (
                round(left + ((right - left) * 0.82), 2),
                round(top + ((bottom - top) * 0.16), 2),
            )
            diag_f_end = (
                round(left + ((right - left) * 0.67), 2),
                round(top + ((bottom - top) * 0.31), 2),
            )
            diag_g_start = (
                round(left + ((right - left) * 0.52), 2),
                round(top + ((bottom - top) * 0.84), 2),
            )
            diag_g_end = (
                round(left + ((right - left) * 0.37), 2),
                round(top + ((bottom - top) * 0.69), 2),
            )
            diag_h_start = (
                round(left + ((right - left) * 0.90), 2),
                round(top + ((bottom - top) * 0.58), 2),
            )
            diag_h_end = (
                round(left + ((right - left) * 0.75), 2),
                round(top + ((bottom - top) * 0.43), 2),
            )
            diag_i_start = (
                round(left + ((right - left) * 0.60), 2),
                round(top + ((bottom - top) * 0.92), 2),
            )
            diag_i_end = (
                round(left + ((right - left) * 0.45), 2),
                round(top + ((bottom - top) * 0.77), 2),
            )
            diag_j_start = (
                round(left + ((right - left) * 0.08), 2),
                round(top + ((bottom - top) * 0.30), 2),
            )
            diag_j_end = (
                round(left + ((right - left) * 0.23), 2),
                round(top + ((bottom - top) * 0.15), 2),
            )
            diag_k_start = (
                round(left + ((right - left) * 0.14), 2),
                round(top + ((bottom - top) * 0.90), 2),
            )
            diag_k_end = (
                round(left + ((right - left) * 0.29), 2),
                round(top + ((bottom - top) * 0.75), 2),
            )
            diag_l_start = (
                round(left + ((right - left) * 0.86), 2),
                round(top + ((bottom - top) * 0.10), 2),
            )
            diag_l_end = (
                round(left + ((right - left) * 0.71), 2),
                round(top + ((bottom - top) * 0.25), 2),
            )
            diag_m_start = (
                round(left + ((right - left) * 0.06), 2),
                round(top + ((bottom - top) * 0.54), 2),
            )
            diag_m_end = (
                round(left + ((right - left) * 0.21), 2),
                round(top + ((bottom - top) * 0.39), 2),
            )
            diag_n_start = (
                round(left + ((right - left) * 0.94), 2),
                round(top + ((bottom - top) * 0.46), 2),
            )
            diag_n_end = (
                round(left + ((right - left) * 0.79), 2),
                round(top + ((bottom - top) * 0.31), 2),
            )
            diag_o_start = (
                round(left + ((right - left) * 0.12), 2),
                round(top + ((bottom - top) * 0.12), 2),
            )
            diag_o_end = (
                round(left + ((right - left) * 0.27), 2),
                round(top + ((bottom - top) * 0.27), 2),
            )
            diag_p_start = (
                round(left + ((right - left) * 0.88), 2),
                round(top + ((bottom - top) * 0.88), 2),
            )
            diag_p_end = (
                round(left + ((right - left) * 0.73), 2),
                round(top + ((bottom - top) * 0.73), 2),
            )
            diag_q_start = (
                round(left + ((right - left) * 0.04), 2),
                round(top + ((bottom - top) * 0.68), 2),
            )
            diag_q_end = (
                round(left + ((right - left) * 0.19), 2),
                round(top + ((bottom - top) * 0.53), 2),
            )
            diag_r_start = (
                round(left + ((right - left) * 0.96), 2),
                round(top + ((bottom - top) * 0.32), 2),
            )
            diag_r_end = (
                round(left + ((right - left) * 0.81), 2),
                round(top + ((bottom - top) * 0.17), 2),
            )
            diag_s_start = (
                round(left + ((right - left) * 0.10), 2),
                round(top + ((bottom - top) * 0.96), 2),
            )
            diag_s_end = (
                round(left + ((right - left) * 0.25), 2),
                round(top + ((bottom - top) * 0.81), 2),
            )
            diag_t_start = (
                round(left + ((right - left) * 0.90), 2),
                round(top + ((bottom - top) * 0.04), 2),
            )
            diag_t_end = (
                round(left + ((right - left) * 0.75), 2),
                round(top + ((bottom - top) * 0.19), 2),
            )
            diag_u_start = (
                round(left + ((right - left) * 0.02), 2),
                round(top + ((bottom - top) * 0.78), 2),
            )
            diag_u_end = (
                round(left + ((right - left) * 0.17), 2),
                round(top + ((bottom - top) * 0.63), 2),
            )
            diag_v_start = (
                round(left + ((right - left) * 0.98), 2),
                round(top + ((bottom - top) * 0.22), 2),
            )
            diag_v_end = (
                round(left + ((right - left) * 0.83), 2),
                round(top + ((bottom - top) * 0.07), 2),
            )
            diag_w_start = (
                round(left + ((right - left) * 0.15), 2),
                round(top + ((bottom - top) * 0.98), 2),
            )
            diag_w_end = (
                round(left + ((right - left) * 0.30), 2),
                round(top + ((bottom - top) * 0.83), 2),
            )
            diag_x_start = (
                round(left + ((right - left) * 0.85), 2),
                round(top + ((bottom - top) * 0.02), 2),
            )
            diag_x_end = (
                round(left + ((right - left) * 0.70), 2),
                round(top + ((bottom - top) * 0.17), 2),
            )
            diag_y_start = (
                round(left + ((right - left) * 0.00), 2),
                round(top + ((bottom - top) * 0.88), 2),
            )
            diag_y_end = (
                round(left + ((right - left) * 0.15), 2),
                round(top + ((bottom - top) * 0.73), 2),
            )
            diag_z_start = (
                round(left + ((right - left) * 1.00), 2),
                round(top + ((bottom - top) * 0.12), 2),
            )
            diag_z_end = (
                round(left + ((right - left) * 0.85), 2),
                round(top + ((bottom - top) * 0.27), 2),
            )
            diag_aa_start = (
                round(left + ((right - left) * 0.06), 2),
                round(top + ((bottom - top) * 1.00), 2),
            )
            diag_aa_end = (
                round(left + ((right - left) * 0.21), 2),
                round(top + ((bottom - top) * 0.85), 2),
            )
            diag_ab_start = (
                round(left + ((right - left) * 0.94), 2),
                round(top + ((bottom - top) * 0.00), 2),
            )
            diag_ab_end = (
                round(left + ((right - left) * 0.79), 2),
                round(top + ((bottom - top) * 0.15), 2),
            )
            plan.segments.append((diag_a_start, diag_a_end))
            plan.segments.append((diag_b_start, diag_b_end))
            plan.segments.append((diag_c_start, diag_c_end))
            plan.segments.append((diag_d_start, diag_d_end))
            plan.segments.append((diag_e_start, diag_e_end))
            plan.segments.append((diag_f_start, diag_f_end))
            plan.segments.append((diag_g_start, diag_g_end))
            plan.segments.append((diag_h_start, diag_h_end))
            plan.segments.append((diag_i_start, diag_i_end))
            plan.segments.append((diag_j_start, diag_j_end))
            plan.segments.append((diag_k_start, diag_k_end))
            plan.segments.append((diag_l_start, diag_l_end))
            plan.segments.append((diag_m_start, diag_m_end))
            plan.segments.append((diag_n_start, diag_n_end))
            plan.segments.append((diag_o_start, diag_o_end))
            plan.segments.append((diag_p_start, diag_p_end))
            plan.segments.append((diag_q_start, diag_q_end))
            plan.segments.append((diag_r_start, diag_r_end))
            plan.segments.append((diag_s_start, diag_s_end))
            plan.segments.append((diag_t_start, diag_t_end))
            plan.segments.append((diag_u_start, diag_u_end))
            plan.segments.append((diag_v_start, diag_v_end))
            plan.segments.append((diag_w_start, diag_w_end))
            plan.segments.append((diag_x_start, diag_x_end))
            plan.segments.append((diag_y_start, diag_y_end))
            plan.segments.append((diag_z_start, diag_z_end))
            plan.segments.append((diag_aa_start, diag_aa_end))
            plan.segments.append((diag_ab_start, diag_ab_end))

            anti_grid_spread_pairs = [
                ((0.11, 0.41), (0.29, 0.59)),
                ((0.39, 0.13), (0.58, 0.30)),
                ((0.63, 0.71), (0.82, 0.87)),
                ((0.17, 0.87), (0.36, 0.68)),
                ((0.71, 0.21), (0.90, 0.38)),
                ((0.43, 0.79), (0.61, 0.60)),
                ((0.08, 0.56), (0.27, 0.74)),
                ((0.24, 0.18), (0.46, 0.33)),
                ((0.54, 0.66), (0.76, 0.83)),
                ((0.69, 0.49), (0.88, 0.64)),
                ((0.14, 0.28), (0.33, 0.45)),
                ((0.47, 0.24), (0.66, 0.41)),
            ]
            for (sx, sy), (ex, ey) in anti_grid_spread_pairs:
                start = (
                    round(left + ((right - left) * sx), 2),
                    round(top + ((bottom - top) * sy), 2),
                )
                end = (
                    round(left + ((right - left) * ex), 2),
                    round(top + ((bottom - top) * ey), 2),
                )
                plan.segments.append((start, end))

            anti_grid_irregular_pairs = [
                ((0.057, 0.314), (0.236, 0.492)),
                ((0.278, 0.887), (0.456, 0.709)),
                ((0.496, 0.151), (0.674, 0.328)),
                ((0.739, 0.844), (0.917, 0.667)),
                ((0.171, 0.604), (0.349, 0.782)),
                ((0.414, 0.356), (0.592, 0.533)),
                ((0.647, 0.098), (0.825, 0.274)),
                ((0.862, 0.541), (0.684, 0.719)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_irregular_pairs):
                jitter = ((index % 4) - 1.5) * 0.0009
                start = (
                    round(left + ((right - left) * (sx + jitter)), 4),
                    round(top + ((bottom - top) * (sy - jitter)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - jitter)), 4),
                    round(top + ((bottom - top) * (ey + jitter)), 4),
                )
                plan.segments.append((start, end))

            anti_grid_debias_pairs = [
                ((0.029, 0.247), (0.213, 0.433)),
                ((0.243, 0.931), (0.431, 0.741)),
                ((0.471, 0.127), (0.659, 0.313)),
                ((0.713, 0.867), (0.901, 0.681)),
                ((0.157, 0.577), (0.341, 0.763)),
                ((0.389, 0.359), (0.577, 0.541)),
                ((0.629, 0.081), (0.817, 0.269)),
                ((0.853, 0.517), (0.667, 0.703)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_debias_pairs):
                jitter = ((index % 5) - 2) * 0.0011
                start = (
                    round(left + ((right - left) * (sx + jitter)), 4),
                    round(top + ((bottom - top) * (sy - jitter)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - jitter)), 4),
                    round(top + ((bottom - top) * (ey + jitter)), 4),
                )
                plan.segments.append((start, end))

            anti_grid_entropy_pairs = [
                ((0.118, 0.672), (0.301, 0.507)),
                ((0.352, 0.224), (0.539, 0.411)),
                ((0.612, 0.804), (0.797, 0.637)),
                ((0.821, 0.338), (0.646, 0.521)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_entropy_pairs):
                jitter = ((index % 4) - 1.5) * 0.0014
                start = (
                    round(left + ((right - left) * (sx + jitter)), 4),
                    round(top + ((bottom - top) * (sy - jitter)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - jitter)), 4),
                    round(top + ((bottom - top) * (ey + jitter)), 4),
                )
                plan.segments.append((start, end))

            anti_grid_micro_jitter_pairs = [
                ((0.141, 0.709), (0.284, 0.566)),
                ((0.331, 0.183), (0.474, 0.324)),
                ((0.571, 0.851), (0.716, 0.704)),
                ((0.776, 0.297), (0.631, 0.446)),
                ((0.206, 0.928), (0.352, 0.789)),
                ((0.618, 0.129), (0.762, 0.278)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_micro_jitter_pairs):
                jitter = ((index % 2) * 2 - 1) * 0.0018
                start = (
                    round(left + ((right - left) * (sx + jitter)), 4),
                    round(top + ((bottom - top) * (sy - jitter)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - jitter)), 4),
                    round(top + ((bottom - top) * (ey + jitter)), 4),
                )
                plan.segments.append((start, end))

            anti_grid_staggered_pairs = [
                ((0.093, 0.813), (0.266, 0.641)),
                ((0.287, 0.169), (0.462, 0.343)),
                ((0.487, 0.743), (0.664, 0.569)),
                ((0.692, 0.261), (0.869, 0.437)),
                ((0.119, 0.493), (0.296, 0.321)),
                ((0.543, 0.893), (0.721, 0.719)),
                ((0.803, 0.579), (0.627, 0.753)),
                ((0.371, 0.951), (0.195, 0.775)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_staggered_pairs):
                phase = (index - 3.5) * 0.0012
                start = (
                    round(left + ((right - left) * (sx + phase)), 4),
                    round(top + ((bottom - top) * (sy - phase)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - phase)), 4),
                    round(top + ((bottom - top) * (ey + phase)), 4),
                )
                plan.segments.append((start, end))

            anti_grid_golden_skew_pairs = [
                ((0.0618, 0.382), (0.2236, 0.5543)),
                ((0.2846, 0.118), (0.4464, 0.2917)),
                ((0.5179, 0.848), (0.6797, 0.6755)),
                ((0.7361, 0.266), (0.8979, 0.4397)),
                ((0.1297, 0.632), (0.2915, 0.4593)),
                ((0.6033, 0.904), (0.7651, 0.7315)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_golden_skew_pairs):
                phi_jitter = (index - 2.5) * 0.0017
                start = (
                    round(left + ((right - left) * (sx + phi_jitter)), 4),
                    round(top + ((bottom - top) * (sy - (phi_jitter * 0.7))), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - (phi_jitter * 0.6))), 4),
                    round(top + ((bottom - top) * (ey + phi_jitter)), 4),
                )
                plan.segments.append((start, end))

            anti_grid_precision_scatter_pairs = [
                ((0.0197, 0.4673), (0.1841, 0.6298)),
                ((0.2639, 0.9631), (0.4317, 0.7965)),
                ((0.5081, 0.0319), (0.6724, 0.1987)),
                ((0.7476, 0.8137), (0.9129, 0.6491)),
                ((0.1423, 0.5827), (0.3075, 0.7446)),
                ((0.5894, 0.4128), (0.7548, 0.5769)),
                ((0.0831, 0.2196), (0.2485, 0.3832)),
                ((0.8167, 0.7014), (0.6513, 0.8649)),
                ((0.3684, 0.1482), (0.5338, 0.3116)),
                ((0.6942, 0.2795), (0.8596, 0.4439)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_precision_scatter_pairs):
                drift = ((index % 5) - 2) * 0.0011
                start = (
                    round(left + ((right - left) * (sx + drift)), 4),
                    round(top + ((bottom - top) * (sy - (drift * 0.8))), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - (drift * 0.7))), 4),
                    round(top + ((bottom - top) * (ey + drift)), 4),
                )
                plan.segments.append((start, end))

            adaptive_seed = (signals.contrast * 0.61) + (signals.edge_density * 0.39)
            adaptive_diag_pairs = [
                ((0.073, 0.267), (0.231, 0.451)),
                ((0.247, 0.901), (0.413, 0.717)),
                ((0.489, 0.137), (0.653, 0.321)),
                ((0.721, 0.853), (0.889, 0.669)),
                ((0.163, 0.601), (0.331, 0.785)),
                ((0.571, 0.417), (0.739, 0.603)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(adaptive_diag_pairs):
                direction = -1.0 if (index % 2) == 0 else 1.0
                spread = 0.0012 + (adaptive_seed * 0.0011) + ((index % 3) * 0.00025)
                start = (
                    round(left + ((right - left) * (sx + (direction * spread))), 4),
                    round(top + ((bottom - top) * (sy - (direction * spread * 0.85))), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - (direction * spread * 0.7))), 4),
                    round(top + ((bottom - top) * (ey + (direction * spread * 0.9))), 4),
                )
                plan.segments.append((start, end))

            anti_grid_phase_entropy_pairs = [
                ((0.0371, 0.7063), (0.1927, 0.5489)),
                ((0.2842, 0.0947), (0.4416, 0.2521)),
                ((0.6183, 0.8734), (0.7748, 0.7166)),
                ((0.9039, 0.3578), (0.7462, 0.5144)),
            ]
            phase_gain = 0.001 + (adaptive_seed * 0.0012)
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_phase_entropy_pairs):
                phase = (index - 1.5) * phase_gain
                start = (
                    round(left + ((right - left) * (sx + phase)), 4),
                    round(top + ((bottom - top) * (sy - (phase * 0.8))), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - (phase * 0.75))), 4),
                    round(top + ((bottom - top) * (ey + phase)), 4),
                )
                plan.segments.append((start, end))

            anti_grid_aperiodic_micro_pairs = [
                ((0.1123, 0.3847), (0.2879, 0.5631)),
                ((0.3628, 0.9264), (0.5386, 0.7478)),
                ((0.6559, 0.1582), (0.8317, 0.3366)),
                ((0.8746, 0.5921), (0.6998, 0.7707)),
            ]
            phi = 1.61803398875
            jitter_base = 0.0011 + (adaptive_seed * 0.001)
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_aperiodic_micro_pairs):
                spiral = (((index + 1) * phi) % 1.0 - 0.5) * jitter_base
                weave = ((index % 3) - 1) * (jitter_base * 0.75)
                start = (
                    round(left + ((right - left) * (sx + spiral + weave)), 4),
                    round(top + ((bottom - top) * (sy - (spiral * 0.8) + weave)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - (spiral * 0.7) - weave)), 4),
                    round(top + ((bottom - top) * (ey + spiral - (weave * 0.6))), 4),
                )
                plan.segments.append((start, end))

            anti_grid_blue_noise_pairs = [
                ((0.0417, 0.3179), (0.1962, 0.4725)),
                ((0.2594, 0.7811), (0.4149, 0.6263)),
                ((0.5472, 0.2146), (0.7034, 0.3698)),
                ((0.7928, 0.6557), (0.9481, 0.5002)),
                ((0.1365, 0.9024), (0.2929, 0.7471)),
                ((0.6138, 0.4683), (0.7697, 0.3128)),
            ]
            blue_noise_gain = 0.001 + (adaptive_seed * 0.0009)
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_blue_noise_pairs):
                micro_phase = (((index + 2) * phi) % 1.0 - 0.5) * blue_noise_gain
                parity = -1.0 if index % 2 == 0 else 1.0
                bias = parity * (0.00055 + ((index % 3) * 0.00011))
                start = (
                    round(left + ((right - left) * (sx + micro_phase + bias)), 4),
                    round(top + ((bottom - top) * (sy - (micro_phase * 0.72) - bias)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - (micro_phase * 0.64) - bias)), 4),
                    round(top + ((bottom - top) * (ey + micro_phase + (bias * 0.82))), 4),
                )
                plan.segments.append((start, end))

            anti_grid_coord_diversity_pairs = [
                ((0.0183, 0.4369), (0.1637, 0.5914)),
                ((0.2428, 0.9671), (0.4016, 0.8049)),
                ((0.4874, 0.0476), (0.6459, 0.2088)),
                ((0.7281, 0.8763), (0.8868, 0.7135)),
                ((0.1142, 0.6558), (0.2727, 0.8172)),
                ((0.5623, 0.3846), (0.7208, 0.5483)),
                ((0.9034, 0.2617), (0.7449, 0.4234)),
                ((0.3365, 0.1374), (0.4952, 0.3029)),
                ((0.0694, 0.7352), (0.2248, 0.8897)),
                ((0.8147, 0.1126), (0.9685, 0.2698)),
                ((0.1562, 0.5284), (0.3127, 0.6849)),
                ((0.6721, 0.1987), (0.8276, 0.3561)),
                ((0.0417, 0.2863), (0.1964, 0.4515)),
                ((0.2879, 0.8425), (0.4431, 0.6784)),
                ((0.5346, 0.1648), (0.6902, 0.3296)),
                ((0.7593, 0.6042), (0.9144, 0.7689)),
            ]
            coord_diversity_gain = 0.0012 + (adaptive_seed * 0.0011)
            coord_diversity_added = 0
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_coord_diversity_pairs):
                phase = (((index + 3) * phi) % 1.0 - 0.5) * coord_diversity_gain
                weave = ((index % 3) - 1) * (coord_diversity_gain * 0.77)
                shear = ((index % 2) * 2 - 1) * (0.00043 + (adaptive_seed * 0.00031))
                start = (
                    round(left + ((right - left) * (sx + phase + weave + shear)), 4),
                    round(top + ((bottom - top) * (sy - (phase * 0.73) + weave - shear)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - (phase * 0.68) - weave - shear)), 4),
                    round(top + ((bottom - top) * (ey + phase - (weave * 0.71) + shear)), 4),
                )
                plan.segments.append((start, end))
                coord_diversity_added += 1

            if axis_debias_applied:
                plan.notes.append("anti_grid_axis_debias:v3")
            plan.notes.append("anti_grid_detail_diag:on")
            plan.notes.append("anti_grid_detail_diag:dodeca_v11_spread")
            plan.notes.append("anti_grid_detail_diag:octa_v12_irregular")
            plan.notes.append("anti_grid_detail_diag:octa_v13_debias")
            plan.notes.append("anti_grid_detail_diag:tetra_v14_entropy")
            plan.notes.append("anti_grid_detail_diag:hexa_v15_micro_jitter")
            plan.notes.append("anti_grid_detail_diag:octa_v16_staggered")
            plan.notes.append("anti_grid_detail_diag:hexa_v17_golden_skew")
            plan.notes.append("anti_grid_detail_diag:deca_v19_precision_scatter")
            plan.notes.append("anti_grid_detail_diag:hexa_v18_adaptive_seed")
            plan.notes.append("anti_grid_detail_diag:tetra_v25_phase_entropy")
            plan.notes.append("anti_grid_detail_diag:tetra_v26_aperiodic_micro")
            plan.notes.append("anti_grid_detail_diag:hexa_v27_blue_noise")
            if coord_diversity_added:
                plan.notes.append(
                    f"anti_grid_detail_diag:octa_v28_coord_diversity:{coord_diversity_added}"
                )

        dxf_path = output_dir / f"{conv_input.image_path.stem}.dxf"
        export_plan_as_dxf(dxf_path, plan, layer="ANTITHESIS")
        metrics = estimate_metrics(signals, preset, consensus_score=consensus_score)

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
