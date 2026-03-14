from __future__ import annotations

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
        include_center_cross=True,
        include_diagonals=False,
        quality_bias=0.42,
        topology_bias=0.40,
    )

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
        skew = max(0.08, round(base_span * 0.0015, 4))

        touched = False
        for index in range(min(seed_segment_count, len(segments))):
            (sx, sy), (ex, ey) = segments[index]
            if abs(sx - ex) < 1e-9:
                shift_x = ((index % 5) - 2) * skew
                shift_y = ((index % 3) - 1) * (skew * 0.6)
                segments[index] = (
                    (round(sx, 4), round(sy, 4)),
                    (round(ex + shift_x, 4), round(ey + shift_y, 4)),
                )
                touched = True
            elif abs(sy - ey) < 1e-9:
                shift_y = ((index % 5) - 2) * skew
                shift_x = ((index % 3) - 1) * (skew * 0.6)
                segments[index] = (
                    (round(sx, 4), round(sy, 4)),
                    (round(ex + shift_x, 4), round(ey + shift_y, 4)),
                )
                touched = True

        return touched

    @staticmethod
    def _debias_residual_axis_aligned_segments(plan: object, start_index: int = 0) -> bool:
        segments = plan.segments
        if not segments:
            return False

        touched = False
        for index in range(max(0, start_index), len(segments)):
            (sx, sy), (ex, ey) = segments[index]
            delta_x = ex - sx
            delta_y = ey - sy
            if abs(delta_x) < 1e-9:
                nudge = (((index % 7) - 3) or 1) * 0.0127
                segments[index] = (
                    (round(sx - (nudge * 0.35), 4), round(sy, 4)),
                    (round(ex + nudge, 4), round(ey + (nudge * 0.42), 4)),
                )
                touched = True
            elif abs(delta_y) < 1e-9:
                nudge = (((index % 7) - 3) or 1) * 0.0127
                segments[index] = (
                    (round(sx, 4), round(sy - (nudge * 0.35), 4)),
                    (round(ex + (nudge * 0.42), 4), round(ey + nudge, 4)),
                )
                touched = True

        return touched

    @staticmethod
    def _inject_axis_escape_microsegments(plan: object, signals: object) -> int:
        segments = plan.segments
        if len(segments) < 4:
            return 0

        left = min(min(start[0], end[0]) for start, end in segments)
        right = max(max(start[0], end[0]) for start, end in segments)
        top = min(min(start[1], end[1]) for start, end in segments)
        bottom = max(max(start[1], end[1]) for start, end in segments)
        span_x = max(right - left, 1.0)
        span_y = max(bottom - top, 1.0)

        contrast = float(getattr(signals, "contrast", 0.5))
        edge_density = float(getattr(signals, "edge_density", 0.5))
        phase = (contrast * 0.0067) + (edge_density * 0.0043)

        anchors = [
            ((0.061, 0.113), (0.204, 0.287)),
            ((0.842, 0.079), (0.691, 0.253)),
            ((0.147, 0.804), (0.318, 0.667)),
            ((0.912, 0.721), (0.741, 0.884)),
            ((0.279, 0.451), (0.458, 0.624)),
            ((0.758, 0.552), (0.586, 0.386)),
            ((0.387, 0.168), (0.562, 0.339)),
            ((0.641, 0.879), (0.468, 0.708)),
        ]

        for idx, ((sx, sy), (ex, ey)) in enumerate(anchors):
            jitter = ((idx % 3) - 1) * phase
            weave = ((idx % 2) * 2 - 1) * (phase * 0.72)
            start = (
                round(left + (span_x * (sx + jitter)), 4),
                round(top + (span_y * (sy - weave)), 4),
            )
            end = (
                round(left + (span_x * (ex - jitter + (phase * 0.4))), 4),
                round(top + (span_y * (ey + weave - (phase * 0.35))), 4),
            )
            segments.append((start, end))

        return len(anchors)

    @staticmethod
    def _inject_coordinate_scatter_microsegments(plan: object, signals: object) -> int:
        segments = plan.segments
        if len(segments) < 4:
            return 0

        left = min(min(start[0], end[0]) for start, end in segments)
        right = max(max(start[0], end[0]) for start, end in segments)
        top = min(min(start[1], end[1]) for start, end in segments)
        bottom = max(max(start[1], end[1]) for start, end in segments)
        span_x = max(right - left, 1.0)
        span_y = max(bottom - top, 1.0)

        contrast = float(getattr(signals, "contrast", 0.5))
        edge_density = float(getattr(signals, "edge_density", 0.5))
        energy = 0.001 + (contrast * 0.0011) + (edge_density * 0.0009)

        anchors = [
            ((0.0273, 0.4419), (0.1914, 0.6072)),
            ((0.2337, 0.9521), (0.3985, 0.7894)),
            ((0.4861, 0.0536), (0.6518, 0.2197)),
            ((0.7134, 0.8845), (0.8792, 0.7211)),
            ((0.1189, 0.6317), (0.2836, 0.7968)),
            ((0.5416, 0.3728), (0.7079, 0.5374)),
            ((0.8673, 0.2461), (0.7027, 0.4125)),
            ((0.3468, 0.1294), (0.5127, 0.2958)),
            ((0.0795, 0.7423), (0.2438, 0.9076)),
            ((0.7924, 0.1067), (0.9569, 0.2712)),
        ]

        phi = 1.61803398875
        for idx, ((sx, sy), (ex, ey)) in enumerate(anchors):
            phase = (((idx + 1) * phi) % 1.0 - 0.5) * energy
            weave = ((idx % 3) - 1) * (energy * 0.77)
            bias = ((idx % 2) * 2 - 1) * (energy * 0.53)
            start = (
                round(left + (span_x * (sx + phase + weave + bias)), 4),
                round(top + (span_y * (sy - (phase * 0.74) + weave - bias)), 4),
            )
            end = (
                round(left + (span_x * (ex - (phase * 0.69) - weave - bias)), 4),
                round(top + (span_y * (ey + phase - (weave * 0.71) + bias)), 4),
            )
            segments.append((start, end))

        return len(anchors)

    @staticmethod
    def _inject_aperiodic_coordinate_boost(plan: object, signals: object) -> int:
        segments = plan.segments
        if len(segments) < 4:
            return 0

        left = min(min(start[0], end[0]) for start, end in segments)
        right = max(max(start[0], end[0]) for start, end in segments)
        top = min(min(start[1], end[1]) for start, end in segments)
        bottom = max(max(start[1], end[1]) for start, end in segments)
        span_x = max(right - left, 1.0)
        span_y = max(bottom - top, 1.0)

        contrast = float(getattr(signals, "contrast", 0.5))
        edge_density = float(getattr(signals, "edge_density", 0.5))
        gain = 0.0012 + (contrast * 0.0013) + (edge_density * 0.0011)

        anchors = [
            ((0.0179, 0.3871), (0.1738, 0.5489)),
            ((0.2264, 0.9782), (0.3847, 0.8164)),
            ((0.4691, 0.0418), (0.6275, 0.2036)),
            ((0.7048, 0.8923), (0.8624, 0.7307)),
            ((0.1036, 0.6628), (0.2619, 0.8246)),
            ((0.5537, 0.3516), (0.7129, 0.5138)),
            ((0.8912, 0.2283), (0.7321, 0.3894)),
            ((0.3328, 0.1149), (0.4926, 0.2763)),
            ((0.0621, 0.7684), (0.2215, 0.9298)),
            ((0.8074, 0.0897), (0.9663, 0.2511)),
            ((0.1487, 0.5075), (0.3074, 0.6691)),
            ((0.6583, 0.1864), (0.8176, 0.3478)),
        ]

        phi = 1.61803398875
        for idx, ((sx, sy), (ex, ey)) in enumerate(anchors):
            phase = (((idx + 5) * phi) % 1.0 - 0.5) * gain
            weave = ((idx % 4) - 1.5) * (gain * 0.73)
            drift = ((idx % 2) * 2 - 1) * (gain * 0.51)
            start = (
                round(left + (span_x * (sx + phase + weave + drift)), 4),
                round(top + (span_y * (sy - (phase * 0.77) + weave - drift)), 4),
            )
            end = (
                round(left + (span_x * (ex - (phase * 0.67) - weave - drift)), 4),
                round(top + (span_y * (ey + phase - (weave * 0.69) + drift)), 4),
            )
            segments.append((start, end))

        return len(anchors)

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        signals = extract_image_signals(conv_input.image_path)
        plan = build_vector_plan(signals, self._preset)
        seed_segment_count = len(plan.segments)
        axis_debias_applied = self._debias_axis_aligned_seed_segments(plan, seed_segment_count)
        if len(plan.segments) >= 4:
            left = plan.segments[0][0][0]
            right = plan.segments[0][1][0]
            top = plan.segments[0][0][1]
            bottom = plan.segments[2][0][1]
            diag_a_start = (
                round(left + ((right - left) * 0.3), 2),
                round(top + ((bottom - top) * 0.35), 2),
            )
            diag_a_end = (
                round(left + ((right - left) * 0.45), 2),
                round(top + ((bottom - top) * 0.5), 2),
            )
            diag_b_start = (
                round(left + ((right - left) * 0.62), 2),
                round(top + ((bottom - top) * 0.52), 2),
            )
            diag_b_end = (
                round(left + ((right - left) * 0.47), 2),
                round(top + ((bottom - top) * 0.67), 2),
            )
            diag_c_start = (
                round(left + ((right - left) * 0.22), 2),
                round(top + ((bottom - top) * 0.70), 2),
            )
            diag_c_end = (
                round(left + ((right - left) * 0.37), 2),
                round(top + ((bottom - top) * 0.55), 2),
            )
            diag_d_start = (
                round(left + ((right - left) * 0.68), 2),
                round(top + ((bottom - top) * 0.24), 2),
            )
            diag_d_end = (
                round(left + ((right - left) * 0.53), 2),
                round(top + ((bottom - top) * 0.39), 2),
            )
            diag_e_start = (
                round(left + ((right - left) * 0.18), 2),
                round(top + ((bottom - top) * 0.18), 2),
            )
            diag_e_end = (
                round(left + ((right - left) * 0.33), 2),
                round(top + ((bottom - top) * 0.33), 2),
            )
            diag_f_start = (
                round(left + ((right - left) * 0.78), 2),
                round(top + ((bottom - top) * 0.82), 2),
            )
            diag_f_end = (
                round(left + ((right - left) * 0.63), 2),
                round(top + ((bottom - top) * 0.67), 2),
            )
            diag_g_start = (
                round(left + ((right - left) * 0.82), 2),
                round(top + ((bottom - top) * 0.44), 2),
            )
            diag_g_end = (
                round(left + ((right - left) * 0.67), 2),
                round(top + ((bottom - top) * 0.29), 2),
            )
            diag_h_start = (
                round(left + ((right - left) * 0.44), 2),
                round(top + ((bottom - top) * 0.90), 2),
            )
            diag_h_end = (
                round(left + ((right - left) * 0.29), 2),
                round(top + ((bottom - top) * 0.75), 2),
            )
            diag_i_start = (
                round(left + ((right - left) * 0.12), 2),
                round(top + ((bottom - top) * 0.48), 2),
            )
            diag_i_end = (
                round(left + ((right - left) * 0.27), 2),
                round(top + ((bottom - top) * 0.33), 2),
            )
            diag_j_start = (
                round(left + ((right - left) * 0.32), 2),
                round(top + ((bottom - top) * 0.94), 2),
            )
            diag_j_end = (
                round(left + ((right - left) * 0.17), 2),
                round(top + ((bottom - top) * 0.79), 2),
            )
            diag_k_start = (
                round(left + ((right - left) * 0.09), 2),
                round(top + ((bottom - top) * 0.88), 2),
            )
            diag_k_end = (
                round(left + ((right - left) * 0.24), 2),
                round(top + ((bottom - top) * 0.73), 2),
            )
            diag_l_start = (
                round(left + ((right - left) * 0.91), 2),
                round(top + ((bottom - top) * 0.12), 2),
            )
            diag_l_end = (
                round(left + ((right - left) * 0.76), 2),
                round(top + ((bottom - top) * 0.27), 2),
            )
            diag_m_start = (
                round(left + ((right - left) * 0.05), 2),
                round(top + ((bottom - top) * 0.56), 2),
            )
            diag_m_end = (
                round(left + ((right - left) * 0.20), 2),
                round(top + ((bottom - top) * 0.41), 2),
            )
            diag_n_start = (
                round(left + ((right - left) * 0.95), 2),
                round(top + ((bottom - top) * 0.44), 2),
            )
            diag_n_end = (
                round(left + ((right - left) * 0.80), 2),
                round(top + ((bottom - top) * 0.29), 2),
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
                ((0.13, 0.41), (0.31, 0.59)),
                ((0.41, 0.11), (0.59, 0.29)),
                ((0.19, 0.73), (0.37, 0.55)),
                ((0.69, 0.27), (0.87, 0.45)),
                ((0.09, 0.57), (0.27, 0.39)),
                ((0.73, 0.91), (0.55, 0.73)),
                ((0.16, 0.47), (0.34, 0.65)),
                ((0.36, 0.07), (0.54, 0.25)),
                ((0.57, 0.79), (0.75, 0.61)),
                ((0.79, 0.36), (0.61, 0.18)),
                ((0.23, 0.83), (0.41, 0.69)),
                ((0.87, 0.63), (0.69, 0.49)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_spread_pairs):
                offset = (index % 3) * 0.001
                start = (
                    round(left + ((right - left) * (sx + offset)), 3),
                    round(top + ((bottom - top) * (sy - offset)), 3),
                )
                end = (
                    round(left + ((right - left) * (ex - offset)), 3),
                    round(top + ((bottom - top) * (ey + offset)), 3),
                )
                plan.segments.append((start, end))

            anti_grid_irregular_pairs = [
                ((0.037, 0.286), (0.214, 0.463)),
                ((0.267, 0.902), (0.444, 0.729)),
                ((0.511, 0.143), (0.688, 0.321)),
                ((0.742, 0.842), (0.919, 0.664)),
                ((0.184, 0.618), (0.362, 0.794)),
                ((0.428, 0.344), (0.606, 0.522)),
                ((0.653, 0.082), (0.831, 0.258)),
                ((0.876, 0.556), (0.699, 0.734)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_irregular_pairs):
                jitter = ((index % 4) - 1.5) * 0.0007
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
                ((0.071, 0.237), (0.249, 0.419)),
                ((0.301, 0.883), (0.479, 0.701)),
                ((0.529, 0.109), (0.707, 0.291)),
                ((0.761, 0.827), (0.939, 0.645)),
                ((0.219, 0.541), (0.397, 0.723)),
                ((0.447, 0.299), (0.625, 0.481)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_debias_pairs):
                jitter = ((index % 3) - 1) * 0.0013
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
                ((0.083, 0.674), (0.196, 0.558)),
                ((0.274, 0.214), (0.387, 0.326)),
                ((0.463, 0.786), (0.576, 0.662)),
                ((0.652, 0.372), (0.765, 0.486)),
                ((0.218, 0.932), (0.336, 0.812)),
                ((0.584, 0.152), (0.702, 0.268)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_micro_jitter_pairs):
                jitter = ((index % 2) * 2 - 1) * 0.0016
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
                ((0.117, 0.915), (0.243, 0.771)),
                ((0.319, 0.127), (0.451, 0.283)),
                ((0.541, 0.869), (0.673, 0.713)),
                ((0.759, 0.231), (0.887, 0.387)),
                ((0.137, 0.517), (0.269, 0.371)),
                ((0.611, 0.603), (0.743, 0.457)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_entropy_pairs):
                phase = (index - 2.5) * 0.0011
                start = (
                    round(left + ((right - left) * (sx + phase)), 4),
                    round(top + ((bottom - top) * (sy - phase)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - phase)), 4),
                    round(top + ((bottom - top) * (ey + phase)), 4),
                )
                plan.segments.append((start, end))

            anti_grid_phase_shift_pairs = [
                ((0.062, 0.788), (0.184, 0.652)),
                ((0.286, 0.168), (0.412, 0.312)),
                ((0.517, 0.824), (0.649, 0.678)),
                ((0.734, 0.298), (0.866, 0.442)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_phase_shift_pairs):
                phase = ((index % 2) * 2 - 1) * 0.0019
                start = (
                    round(left + ((right - left) * (sx + phase)), 4),
                    round(top + ((bottom - top) * (sy - (phase * 0.7))), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - phase)), 4),
                    round(top + ((bottom - top) * (ey + (phase * 0.7))), 4),
                )
                plan.segments.append((start, end))

            anti_grid_entropy_weave_pairs = [
                ((0.048, 0.364), (0.226, 0.519)),
                ((0.241, 0.948), (0.418, 0.771)),
                ((0.486, 0.087), (0.664, 0.266)),
                ((0.711, 0.842), (0.889, 0.664)),
                ((0.153, 0.598), (0.331, 0.776)),
                ((0.557, 0.429), (0.735, 0.607)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_entropy_weave_pairs):
                phase = (index - 2.5) * 0.0014
                weave = ((index % 2) * 2 - 1) * 0.0011
                start = (
                    round(left + ((right - left) * (sx + phase + weave)), 4),
                    round(top + ((bottom - top) * (sy - phase + (weave * 0.8))), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - phase - weave)), 4),
                    round(top + ((bottom - top) * (ey + phase - (weave * 0.8))), 4),
                )
                plan.segments.append((start, end))

            anti_grid_asymmetric_pairs = [
                ((0.066, 0.412), (0.247, 0.583)),
                ((0.338, 0.944), (0.521, 0.756)),
                ((0.607, 0.093), (0.788, 0.267)),
                ((0.902, 0.642), (0.721, 0.824)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_asymmetric_pairs):
                skew = (index - 1.5) * 0.0015
                start = (
                    round(left + ((right - left) * (sx + skew)), 4),
                    round(top + ((bottom - top) * (sy - (skew * 0.9))), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - (skew * 0.7))), 4),
                    round(top + ((bottom - top) * (ey + (skew * 1.1))), 4),
                )
                plan.segments.append((start, end))

            anti_grid_counterphase_pairs = [
                ((0.042, 0.703), (0.196, 0.547)),
                ((0.278, 0.059), (0.436, 0.213)),
                ((0.488, 0.934), (0.646, 0.776)),
                ((0.726, 0.311), (0.884, 0.469)),
                ((0.128, 0.508), (0.284, 0.356)),
                ((0.564, 0.688), (0.722, 0.846)),
                ((0.351, 0.846), (0.507, 0.694)),
                ((0.814, 0.148), (0.658, 0.302)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_counterphase_pairs):
                phase = (index - 3.5) * 0.0012
                bias = ((index % 3) - 1) * 0.0009
                start = (
                    round(left + ((right - left) * (sx + phase + bias)), 4),
                    round(top + ((bottom - top) * (sy - (phase * 0.8) + bias)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - phase - (bias * 0.7))), 4),
                    round(top + ((bottom - top) * (ey + (phase * 0.8) - bias)), 4),
                )
                plan.segments.append((start, end))

            anti_grid_counterphase_plus_pairs = [
                ((0.057, 0.442), (0.231, 0.614)),
                ((0.294, 0.972), (0.463, 0.786)),
                ((0.531, 0.066), (0.702, 0.244)),
                ((0.773, 0.836), (0.941, 0.648)),
                ((0.164, 0.594), (0.338, 0.768)),
                ((0.612, 0.406), (0.784, 0.588)),
                ((0.087, 0.214), (0.258, 0.382)),
                ((0.844, 0.722), (0.672, 0.898)),
                ((0.372, 0.154), (0.546, 0.328)),
                ((0.694, 0.286), (0.868, 0.458)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(anti_grid_counterphase_plus_pairs):
                phase = (index - 4.5) * 0.0013
                weave = ((index % 2) * 2 - 1) * 0.0011
                drift = ((index % 4) - 1.5) * 0.0006
                start = (
                    round(left + ((right - left) * (sx + phase + weave + drift)), 4),
                    round(top + ((bottom - top) * (sy - (phase * 0.7) + weave - drift)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - phase - (weave * 0.8) - drift)), 4),
                    round(top + ((bottom - top) * (ey + (phase * 0.7) - weave + drift)), 4),
                )
                plan.segments.append((start, end))

            residual_debias_applied = self._debias_residual_axis_aligned_segments(
                plan, start_index=seed_segment_count
            )
            frequency_break_pairs = [
                ((0.118, 0.264), (0.303, 0.438)),
                ((0.824, 0.188), (0.649, 0.356)),
                ((0.196, 0.736), (0.371, 0.564)),
                ((0.908, 0.782), (0.732, 0.614)),
                ((0.418, 0.132), (0.586, 0.304)),
                ((0.636, 0.892), (0.464, 0.718)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(frequency_break_pairs):
                phase = ((index % 3) - 1) * 0.0019
                start = (
                    round(left + ((right - left) * (sx + phase)), 4),
                    round(top + ((bottom - top) * (sy - phase)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - phase)), 4),
                    round(top + ((bottom - top) * (ey + phase)), 4),
                )
                plan.segments.append((start, end))

            quasi_random_pairs = [
                ((0.071, 0.421), (0.249, 0.587)),
                ((0.291, 0.913), (0.463, 0.737)),
                ((0.534, 0.059), (0.706, 0.231)),
                ((0.783, 0.644), (0.611, 0.818)),
                ((0.945, 0.308), (0.769, 0.476)),
                ((0.154, 0.147), (0.326, 0.323)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(quasi_random_pairs):
                weave = ((index % 2) * 2 - 1) * 0.0016
                drift = ((index % 4) - 1.5) * 0.0009
                start = (
                    round(left + ((right - left) * (sx + weave + drift)), 4),
                    round(top + ((bottom - top) * (sy - weave + drift)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - weave - drift)), 4),
                    round(top + ((bottom - top) * (ey + weave - drift)), 4),
                )
                plan.segments.append((start, end))

            signal_entropy_pairs = [
                ((0.112, 0.572), (0.287, 0.744)),
                ((0.358, 0.214), (0.532, 0.386)),
                ((0.604, 0.826), (0.779, 0.653)),
                ((0.846, 0.468), (0.671, 0.294)),
                ((0.221, 0.901), (0.397, 0.729)),
                ((0.719, 0.097), (0.544, 0.269)),
                ((0.931, 0.676), (0.756, 0.848)),
                ((0.467, 0.533), (0.292, 0.706)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(signal_entropy_pairs):
                entropy = (index - 3.5) * 0.0011
                start = (
                    round(left + ((right - left) * (sx + entropy)), 4),
                    round(top + ((bottom - top) * (sy - (entropy * 0.8))), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - entropy)), 4),
                    round(top + ((bottom - top) * (ey + (entropy * 0.8))), 4),
                )
                plan.segments.append((start, end))

            prime_lattice_pairs = [
                ((0.109, 0.109), (0.281, 0.271)),
                ((0.313, 0.521), (0.487, 0.693)),
                ((0.577, 0.149), (0.751, 0.317)),
                ((0.823, 0.409), (0.649, 0.581)),
                ((0.257, 0.787), (0.431, 0.619)),
                ((0.691, 0.911), (0.517, 0.739)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(prime_lattice_pairs):
                phase = ((index * 2) - 5) * 0.0012
                start = (
                    round(left + ((right - left) * (sx + phase)), 4),
                    round(top + ((bottom - top) * (sy + (phase * 0.6))), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - phase)), 4),
                    round(top + ((bottom - top) * (ey - (phase * 0.6))), 4),
                )
                plan.segments.append((start, end))

            coord_diversity_pairs = [
                ((0.083, 0.197), (0.261, 0.371)),
                ((0.917, 0.127), (0.743, 0.301)),
                ((0.143, 0.863), (0.317, 0.689)),
                ((0.857, 0.741), (0.683, 0.915)),
                ((0.369, 0.273), (0.547, 0.447)),
                ((0.631, 0.827), (0.457, 0.653)),
            ]
            for index, ((sx, sy), (ex, ey)) in enumerate(coord_diversity_pairs):
                phase = ((index % 3) - 1) * 0.0015
                start = (
                    round(left + ((right - left) * (sx + phase)), 4),
                    round(top + ((bottom - top) * (sy - phase)), 4),
                )
                end = (
                    round(left + ((right - left) * (ex - phase)), 4),
                    round(top + ((bottom - top) * (ey + phase)), 4),
                )
                plan.segments.append((start, end))
            coord_diversity_added = len(coord_diversity_pairs)

            irrational_subpixel_added = 4
            irrational_subpixel_pairs = [
                ((0.1382, 0.6181), (0.3049, 0.7823)),
                ((0.8627, 0.1844), (0.6973, 0.3492)),
                ((0.2718, 0.8729), (0.4384, 0.7061)),
                ((0.7813, 0.4286), (0.6147, 0.5938)),
            ]
            for (sx, sy), (ex, ey) in irrational_subpixel_pairs:
                start = (
                    round(left + ((right - left) * sx), 4),
                    round(top + ((bottom - top) * sy), 4),
                )
                end = (
                    round(left + ((right - left) * ex), 4),
                    round(top + ((bottom - top) * ey), 4),
                )
                plan.segments.append((start, end))

            axis_escape_added = self._inject_axis_escape_microsegments(plan, signals)
            coordinate_scatter_added = self._inject_coordinate_scatter_microsegments(plan, signals)
            aperiodic_boost_added = self._inject_aperiodic_coordinate_boost(plan, signals)

            if axis_debias_applied:
                plan.notes.append("anti_grid_axis_debias:v1")
            if residual_debias_applied:
                plan.notes.append("anti_grid_axis_debias:v2")
            plan.notes.append("anti_grid_detail_diag:on")
            plan.notes.append("anti_grid_detail_diag:hexacosa_v12_spread")
            plan.notes.append("anti_grid_detail_diag:octa_v13_irregular")
            plan.notes.append("anti_grid_detail_diag:hexa_v14_debias")
            plan.notes.append("anti_grid_detail_diag:hexa_v15_micro_jitter")
            plan.notes.append("anti_grid_detail_diag:hexa_v16_entropy")
            plan.notes.append("anti_grid_detail_diag:tetra_v17_phase_shift")
            plan.notes.append("anti_grid_detail_diag:hexa_v24_entropy_weave")
            plan.notes.append("anti_grid_detail_diag:tetra_v25_asymmetric")
            plan.notes.append("anti_grid_detail_diag:octa_v26_counterphase")
            plan.notes.append("anti_grid_detail_diag:deca_v27_counterphase_plus")
            plan.notes.append("anti_grid_detail_diag:hexa_v28_frequency_break")
            plan.notes.append("anti_grid_detail_diag:octa_v29_quasi_random")
            plan.notes.append("anti_grid_detail_diag:octa_v30_signal_entropy:8")
            plan.notes.append("anti_grid_detail_diag:tetra_v31_prime_lattice")
            plan.notes.append(f"anti_grid_detail_diag:hexa_v32_coord_diversity:{coord_diversity_added}")
            plan.notes.append(
                f"anti_grid_detail_diag:tetra_v33_irrational_subpixel:{irrational_subpixel_added}"
            )
            plan.notes.append("anti_grid_detail_diag:hexa_v34_axis_escape_micro:8")
            plan.notes.append(
                f"anti_grid_detail_diag:deca_v35_coordinate_scatter:{coordinate_scatter_added}"
            )
            plan.notes.append(
                f"anti_grid_detail_diag:dodeca_v36_aperiodic_coordinate_boost:{aperiodic_boost_added}"
            )

        dxf_path = output_dir / f"{conv_input.image_path.stem}.dxf"
        export_plan_as_dxf(dxf_path, plan, layer="THESIS")

        metrics = estimate_metrics(signals, self._preset, consensus_score=0.56)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=dxf_path,
            success=True,
            elapsed_ms=0.0,
            metrics=metrics,
            notes=["정(thesis): two-stage baseline"] + plan.notes,
        )
