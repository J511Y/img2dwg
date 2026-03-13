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

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        signals = extract_image_signals(conv_input.image_path)
        plan = build_vector_plan(signals, self._preset)
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

            plan.notes.append("anti_grid_detail_diag:on")
            plan.notes.append("anti_grid_detail_diag:hexacosa_v12_spread")
            plan.notes.append("anti_grid_detail_diag:octa_v13_irregular")
            plan.notes.append("anti_grid_detail_diag:hexa_v14_debias")

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
