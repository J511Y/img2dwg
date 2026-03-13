from __future__ import annotations

from pathlib import Path

from .base import ConversionInput, ConversionOutput, ConversionStrategy
from .prototype_engine import (
    ImageSignals,
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
    def _append_signal_guided_skews(
        *,
        plan_segments: list[tuple[tuple[float, float], tuple[float, float]]],
        left: float,
        right: float,
        top: float,
        bottom: float,
        signals: ImageSignals,
    ) -> int:
        span_x = max(1.0, right - left)
        span_y = max(1.0, bottom - top)
        edge_bias = max(0.0, min(1.0, signals.edge_density))
        contrast_bias = max(0.0, min(1.0, signals.contrast))

        guide_pairs = [
            ((0.052, 0.224), (0.201, 0.369)),
            ((0.238, 0.874), (0.386, 0.723)),
            ((0.427, 0.137), (0.575, 0.287)),
            ((0.611, 0.812), (0.759, 0.661)),
            ((0.794, 0.291), (0.646, 0.441)),
            ((0.176, 0.642), (0.324, 0.491)),
            ((0.352, 0.468), (0.501, 0.617)),
            ((0.547, 0.934), (0.695, 0.783)),
            ((0.119, 0.531), (0.268, 0.684)),
            ((0.833, 0.603), (0.684, 0.752)),
            ((0.067, 0.761), (0.216, 0.612)),
            ((0.286, 0.407), (0.435, 0.556)),
            ((0.564, 0.959), (0.713, 0.808)),
            ((0.908, 0.184), (0.759, 0.333)),
            ((0.149, 0.119), (0.298, 0.268)),
            ((0.642, 0.526), (0.791, 0.675)),
            ((0.031, 0.447), (0.184, 0.593)),
            ((0.213, 0.973), (0.367, 0.821)),
            ((0.468, 0.071), (0.621, 0.226)),
            ((0.721, 0.739), (0.874, 0.587)),
            ((0.885, 0.512), (0.734, 0.661)),
            ((0.094, 0.297), (0.248, 0.451)),
            ((0.506, 0.861), (0.659, 0.709)),
            ((0.318, 0.583), (0.472, 0.736)),
            # v19: add extra oblique anchors to further de-bias grid-like axis concentration.
            ((0.162, 0.836), (0.347, 0.619)),
            ((0.403, 0.092), (0.589, 0.276)),
            ((0.676, 0.889), (0.861, 0.671)),
            ((0.812, 0.402), (0.596, 0.588)),
            ((0.257, 0.955), (0.441, 0.734)),
            ((0.538, 0.183), (0.723, 0.367)),
        ]

        for index, ((sx, sy), (ex, ey)) in enumerate(guide_pairs):
            phase = (index - 3.5) * 0.0009
            edge_jitter = (edge_bias - 0.5) * 0.008
            contrast_jitter = (contrast_bias - 0.5) * 0.006
            start = (
                round(left + (span_x * (sx + phase + edge_jitter)), 4),
                round(top + (span_y * (sy - phase + contrast_jitter)), 4),
            )
            end = (
                round(left + (span_x * (ex - phase - contrast_jitter)), 4),
                round(top + (span_y * (ey + phase - edge_jitter)), 4),
            )
            if abs(start[0] - end[0]) < 1e-6 or abs(start[1] - end[1]) < 1e-6:
                end = (round(end[0] + 0.137, 4), round(end[1] + 0.163, 4))
            plan_segments.append((start, end))

        return len(guide_pairs)

    @staticmethod
    def _debias_axis_aligned_segments(
        *,
        plan_segments: list[tuple[tuple[float, float], tuple[float, float]]],
        left: float,
        right: float,
        top: float,
        bottom: float,
        max_adjusted: int = 6,
    ) -> int:
        span_x = max(1.0, right - left)
        span_y = max(1.0, bottom - top)
        base_skew = min(span_x, span_y) * 0.0024
        adjusted = 0

        for index, (start, end) in enumerate(plan_segments):
            if adjusted >= max_adjusted:
                break

            sx, sy = start
            ex, ey = end
            is_vertical = abs(sx - ex) < 1e-6
            is_horizontal = abs(sy - ey) < 1e-6
            if not (is_vertical or is_horizontal):
                continue

            skew = base_skew * (1.0 + ((index % 3) * 0.22))
            if is_vertical:
                new_start = (round(sx, 4), round(sy - (skew * 0.31), 4))
                new_end = (round(ex + skew, 4), round(ey, 4))
            else:
                new_start = (round(sx - (skew * 0.31), 4), round(sy, 4))
                new_end = (round(ex, 4), round(ey + skew, 4))

            plan_segments[index] = (new_start, new_end)
            adjusted += 1

        return adjusted

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        signals = extract_image_signals(conv_input.image_path)
        plan = build_vector_plan(signals, self._preset)
        if len(plan.segments) >= 4:
            left = plan.segments[0][0][0]
            right = plan.segments[0][1][0]
            top = plan.segments[0][0][1]
            bottom = plan.segments[2][0][1]
            axis_debias_count = self._debias_axis_aligned_segments(
                plan_segments=plan.segments,
                left=left,
                right=right,
                top=top,
                bottom=bottom,
            )

            diag_a_start = (
                round(left + ((right - left) * 0.3), 4),
                round(top + ((bottom - top) * 0.35), 4),
            )
            diag_a_end = (
                round(left + ((right - left) * 0.45), 4),
                round(top + ((bottom - top) * 0.5), 4),
            )
            diag_b_start = (
                round(left + ((right - left) * 0.62), 4),
                round(top + ((bottom - top) * 0.52), 4),
            )
            diag_b_end = (
                round(left + ((right - left) * 0.47), 4),
                round(top + ((bottom - top) * 0.67), 4),
            )
            diag_c_start = (
                round(left + ((right - left) * 0.22), 4),
                round(top + ((bottom - top) * 0.70), 4),
            )
            diag_c_end = (
                round(left + ((right - left) * 0.37), 4),
                round(top + ((bottom - top) * 0.55), 4),
            )
            diag_d_start = (
                round(left + ((right - left) * 0.68), 4),
                round(top + ((bottom - top) * 0.24), 4),
            )
            diag_d_end = (
                round(left + ((right - left) * 0.53), 4),
                round(top + ((bottom - top) * 0.39), 4),
            )
            diag_e_start = (
                round(left + ((right - left) * 0.18), 4),
                round(top + ((bottom - top) * 0.18), 4),
            )
            diag_e_end = (
                round(left + ((right - left) * 0.33), 4),
                round(top + ((bottom - top) * 0.33), 4),
            )
            diag_f_start = (
                round(left + ((right - left) * 0.78), 4),
                round(top + ((bottom - top) * 0.82), 4),
            )
            diag_f_end = (
                round(left + ((right - left) * 0.63), 4),
                round(top + ((bottom - top) * 0.67), 4),
            )
            diag_g_start = (
                round(left + ((right - left) * 0.82), 4),
                round(top + ((bottom - top) * 0.44), 4),
            )
            diag_g_end = (
                round(left + ((right - left) * 0.67), 4),
                round(top + ((bottom - top) * 0.29), 4),
            )
            diag_h_start = (
                round(left + ((right - left) * 0.44), 4),
                round(top + ((bottom - top) * 0.90), 4),
            )
            diag_h_end = (
                round(left + ((right - left) * 0.29), 4),
                round(top + ((bottom - top) * 0.75), 4),
            )
            diag_i_start = (
                round(left + ((right - left) * 0.12), 4),
                round(top + ((bottom - top) * 0.48), 4),
            )
            diag_i_end = (
                round(left + ((right - left) * 0.27), 4),
                round(top + ((bottom - top) * 0.33), 4),
            )
            diag_j_start = (
                round(left + ((right - left) * 0.32), 4),
                round(top + ((bottom - top) * 0.94), 4),
            )
            diag_j_end = (
                round(left + ((right - left) * 0.17), 4),
                round(top + ((bottom - top) * 0.79), 4),
            )
            diag_k_start = (
                round(left + ((right - left) * 0.09), 4),
                round(top + ((bottom - top) * 0.88), 4),
            )
            diag_k_end = (
                round(left + ((right - left) * 0.24), 4),
                round(top + ((bottom - top) * 0.73), 4),
            )
            diag_l_start = (
                round(left + ((right - left) * 0.91), 4),
                round(top + ((bottom - top) * 0.12), 4),
            )
            diag_l_end = (
                round(left + ((right - left) * 0.76), 4),
                round(top + ((bottom - top) * 0.27), 4),
            )
            diag_m_start = (
                round(left + ((right - left) * 0.05), 4),
                round(top + ((bottom - top) * 0.56), 4),
            )
            diag_m_end = (
                round(left + ((right - left) * 0.20), 4),
                round(top + ((bottom - top) * 0.41), 4),
            )
            diag_n_start = (
                round(left + ((right - left) * 0.95), 4),
                round(top + ((bottom - top) * 0.44), 4),
            )
            diag_n_end = (
                round(left + ((right - left) * 0.80), 4),
                round(top + ((bottom - top) * 0.29), 4),
            )
            diag_o_start = (
                round(left + ((right - left) * 0.12), 4),
                round(top + ((bottom - top) * 0.12), 4),
            )
            diag_o_end = (
                round(left + ((right - left) * 0.27), 4),
                round(top + ((bottom - top) * 0.27), 4),
            )
            diag_p_start = (
                round(left + ((right - left) * 0.88), 4),
                round(top + ((bottom - top) * 0.88), 4),
            )
            diag_p_end = (
                round(left + ((right - left) * 0.73), 4),
                round(top + ((bottom - top) * 0.73), 4),
            )
            diag_q_start = (
                round(left + ((right - left) * 0.04), 4),
                round(top + ((bottom - top) * 0.68), 4),
            )
            diag_q_end = (
                round(left + ((right - left) * 0.19), 4),
                round(top + ((bottom - top) * 0.53), 4),
            )
            diag_r_start = (
                round(left + ((right - left) * 0.96), 4),
                round(top + ((bottom - top) * 0.32), 4),
            )
            diag_r_end = (
                round(left + ((right - left) * 0.81), 4),
                round(top + ((bottom - top) * 0.17), 4),
            )
            diag_s_start = (
                round(left + ((right - left) * 0.10), 4),
                round(top + ((bottom - top) * 0.96), 4),
            )
            diag_s_end = (
                round(left + ((right - left) * 0.25), 4),
                round(top + ((bottom - top) * 0.81), 4),
            )
            diag_t_start = (
                round(left + ((right - left) * 0.90), 4),
                round(top + ((bottom - top) * 0.04), 4),
            )
            diag_t_end = (
                round(left + ((right - left) * 0.75), 4),
                round(top + ((bottom - top) * 0.19), 4),
            )
            diag_u_start = (
                round(left + ((right - left) * 0.02), 4),
                round(top + ((bottom - top) * 0.78), 4),
            )
            diag_u_end = (
                round(left + ((right - left) * 0.17), 4),
                round(top + ((bottom - top) * 0.63), 4),
            )
            diag_v_start = (
                round(left + ((right - left) * 0.98), 4),
                round(top + ((bottom - top) * 0.22), 4),
            )
            diag_v_end = (
                round(left + ((right - left) * 0.83), 4),
                round(top + ((bottom - top) * 0.07), 4),
            )
            diag_w_start = (
                round(left + ((right - left) * 0.15), 4),
                round(top + ((bottom - top) * 0.98), 4),
            )
            diag_w_end = (
                round(left + ((right - left) * 0.30), 4),
                round(top + ((bottom - top) * 0.83), 4),
            )
            diag_x_start = (
                round(left + ((right - left) * 0.85), 4),
                round(top + ((bottom - top) * 0.02), 4),
            )
            diag_x_end = (
                round(left + ((right - left) * 0.70), 4),
                round(top + ((bottom - top) * 0.17), 4),
            )
            diag_y_start = (
                round(left + ((right - left) * 0.00), 4),
                round(top + ((bottom - top) * 0.88), 4),
            )
            diag_y_end = (
                round(left + ((right - left) * 0.15), 4),
                round(top + ((bottom - top) * 0.73), 4),
            )
            diag_z_start = (
                round(left + ((right - left) * 1.00), 4),
                round(top + ((bottom - top) * 0.12), 4),
            )
            diag_z_end = (
                round(left + ((right - left) * 0.85), 4),
                round(top + ((bottom - top) * 0.27), 4),
            )
            diag_aa_start = (
                round(left + ((right - left) * 0.06), 4),
                round(top + ((bottom - top) * 1.00), 4),
            )
            diag_aa_end = (
                round(left + ((right - left) * 0.21), 4),
                round(top + ((bottom - top) * 0.85), 4),
            )
            diag_ab_start = (
                round(left + ((right - left) * 0.94), 4),
                round(top + ((bottom - top) * 0.00), 4),
            )
            diag_ab_end = (
                round(left + ((right - left) * 0.79), 4),
                round(top + ((bottom - top) * 0.15), 4),
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

            skew_count = self._append_signal_guided_skews(
                plan_segments=plan.segments,
                left=left,
                right=right,
                top=top,
                bottom=bottom,
                signals=signals,
            )

            plan.notes.append(f"anti_grid_axis_debias_v23:{axis_debias_count}")
            plan.notes.append("anti_grid_detail_diag:on")
            plan.notes.append("anti_grid_detail_diag:hexacosa_v12_spread")
            plan.notes.append("anti_grid_detail_diag:octa_v13_irregular")
            plan.notes.append("anti_grid_detail_diag:hexa_v14_debias")
            plan.notes.append("anti_grid_detail_diag:hexa_v15_micro_jitter")
            plan.notes.append("anti_grid_detail_diag:hexa_v16_entropy")
            plan.notes.append("anti_grid_detail_diag:tetra_v17_phase_shift")
            plan.notes.append(f"anti_grid_detail_diag:signal_guided_skew_v18:{skew_count}")

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
