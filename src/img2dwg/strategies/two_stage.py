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
        skew = max(0.1, round(base_span * 0.0019, 4))

        touched = False
        for index in range(min(seed_segment_count, len(segments))):
            (sx, sy), (ex, ey) = segments[index]
            phi_phase = (((index + 1) * 1.61803398875) % 1.0) - 0.5
            skew_phase = ((index % 4) - 1.5) * (skew * 0.17)
            if abs(sx - ex) < 1e-9:
                shift_x = (((index % 5) - 2) * skew * 0.72) + (phi_phase * skew * 0.41)
                shift_y = (((index % 3) - 1) * (skew * 0.61)) + skew_phase
                segments[index] = (
                    (round(sx - (phi_phase * skew * 0.13), 4), round(sy, 4)),
                    (round(ex + shift_x, 4), round(ey + shift_y, 4)),
                )
                touched = True
            elif abs(sy - ey) < 1e-9:
                shift_y = (((index % 5) - 2) * skew * 0.72) + (phi_phase * skew * 0.41)
                shift_x = (((index % 3) - 1) * (skew * 0.61)) + skew_phase
                segments[index] = (
                    (round(sx, 4), round(sy - (phi_phase * skew * 0.13), 4)),
                    (round(ex + shift_x, 4), round(ey + shift_y, 4)),
                )
                touched = True

        return touched

    @staticmethod
    def _debias_residual_axis_aligned_segments(plan: object, start_index: int = 0) -> bool:
        segments = plan.segments
        if not segments or start_index >= len(segments):
            return False

        touched = False
        for index in range(start_index, len(segments)):
            (sx, sy), (ex, ey) = segments[index]
            phase = (((index + 1) * 1.61803398875) % 1.0) - 0.5
            wobble = ((index % 3) - 1) * 0.0037
            if abs(sx - ex) < 1e-9:
                segments[index] = (
                    (round(sx - (phase * 0.0019), 4), round(sy, 4)),
                    (round(ex + (phase * 0.0041) + wobble, 4), round(ey + wobble, 4)),
                )
                touched = True
            elif abs(sy - ey) < 1e-9:
                segments[index] = (
                    (round(sx, 4), round(sy - (phase * 0.0019), 4)),
                    (round(ex + wobble, 4), round(ey + (phase * 0.0041) + wobble, 4)),
                )
                touched = True

        return touched

    @staticmethod
    def _append_quasi_lattice_scatter_pack(
        plan: object,
        *,
        left: float,
        right: float,
        top: float,
        bottom: float,
    ) -> int:
        if right <= left or bottom <= top:
            return 0

        quasi_lattice_pairs = [
            ((0.0813, 0.5291), (0.2394, 0.7018)),
            ((0.3279, 0.1185), (0.4868, 0.2927)),
            ((0.5742, 0.9031), (0.7333, 0.7278)),
            ((0.8198, 0.2846), (0.6611, 0.4583)),
            ((0.1462, 0.3627), (0.3044, 0.5369)),
            ((0.6947, 0.6124), (0.8536, 0.4382)),
        ]

        for index, ((sx, sy), (ex, ey)) in enumerate(quasi_lattice_pairs):
            phase = (((index + 3) * 1.61803398875) % 1.0) - 0.5
            weave = ((index % 2) * 2 - 1) * 0.0009
            drift = ((index % 3) - 1) * 0.0006
            start = (
                round(left + ((right - left) * (sx + (phase * 0.0012) + weave + drift)), 4),
                round(top + ((bottom - top) * (sy - (phase * 0.0010) - weave + drift)), 4),
            )
            end = (
                round(left + ((right - left) * (ex - (phase * 0.0011) - (weave * 0.8) - drift)), 4),
                round(top + ((bottom - top) * (ey + (phase * 0.0009) + (weave * 0.8) - drift)), 4),
            )
            plan.segments.append((start, end))

        return len(quasi_lattice_pairs)

    @staticmethod
    def _inject_coordinate_entropy(plan: object, start_index: int = 0) -> int:
        segments = plan.segments
        if not segments or start_index >= len(segments):
            return 0

        touched = 0
        for index in range(start_index, len(segments)):
            (sx, sy), (ex, ey) = segments[index]
            phase = (((index + 2) * 1.32471795724) % 1.0) - 0.5
            weave = ((index % 3) - 1) * 0.00091
            sx2 = round(sx + (phase * 0.00183) + weave, 4)
            sy2 = round(sy - (phase * 0.00161) + weave, 4)
            ex2 = round(ex - (phase * 0.00149) - weave, 4)
            ey2 = round(ey + (phase * 0.00173) - weave, 4)
            segments[index] = ((sx2, sy2), (ex2, ey2))
            touched += 1

        return touched

    @staticmethod
    def _inject_axis_escape_microsegments(plan: object, signals: object) -> int:
        if len(plan.segments) < 4:
            return 0

        left = plan.segments[0][0][0]
        right = plan.segments[0][1][0]
        top = plan.segments[0][0][1]
        bottom = plan.segments[2][0][1]

        phi = 1.61803398875
        adaptive = 0.00108 + (signals.edge_density * 0.00061) + (signals.contrast * 0.00049)
        pairs = [
            (0.0273, 0.3661, 0.1924, 0.5337),
            (0.2419, 0.9448, 0.4066, 0.7782),
            (0.4746, 0.0527, 0.6398, 0.2209),
            (0.7232, 0.8621, 0.8886, 0.6947),
            (0.1194, 0.6233, 0.2848, 0.7906),
            (0.5561, 0.4217, 0.7215, 0.5899),
            (0.9073, 0.2588, 0.7417, 0.4272),
            (0.3364, 0.1439, 0.5018, 0.3114),
        ]

        appended = 0
        for index, (sx, sy, ex, ey) in enumerate(pairs):
            phase = (((index + 1) * phi) % 1.0 - 0.5) * adaptive
            weave = ((index % 3) - 1) * (adaptive * 0.67)
            shear = ((index % 2) * 2 - 1) * (adaptive * 0.49)
            start = (
                round(left + ((right - left) * (sx + phase + weave + shear)), 4),
                round(top + ((bottom - top) * (sy - (phase * 0.76) + weave - shear)), 4),
            )
            end = (
                round(left + ((right - left) * (ex - (phase * 0.72) - weave - shear)), 4),
                round(top + ((bottom - top) * (ey + phase - (weave * 0.68) + shear)), 4),
            )
            plan.segments.append((start, end))
            appended += 1

        return appended

    @staticmethod
    def _inject_axis_escape_entropy_segments(plan: object, signals: object) -> int:
        if len(plan.segments) < 4:
            return 0

        left = plan.segments[0][0][0]
        right = plan.segments[0][1][0]
        top = plan.segments[0][0][1]
        bottom = plan.segments[2][0][1]

        phi = 1.61803398875
        sqrt2 = 1.41421356237
        adaptive = 0.00103 + (signals.edge_density * 0.00057) + (signals.contrast * 0.00053)
        pairs = [
            (0.0416, 0.5164, 0.2091, 0.6785),
            (0.2867, 0.0861, 0.4523, 0.2514),
            (0.5345, 0.9182, 0.7011, 0.7543),
            (0.7873, 0.3249, 0.6218, 0.4896),
            (0.1532, 0.7417, 0.3194, 0.5771),
            (0.6291, 0.1795, 0.7948, 0.3442),
        ]

        appended = 0
        for index, (sx, sy, ex, ey) in enumerate(pairs):
            phase = (((index + 1) * phi) % 1.0 - 0.5) * adaptive
            warp = (((index + 2) * sqrt2) % 1.0 - 0.5) * (adaptive * 0.89)
            shear = ((index % 3) - 1) * (adaptive * 0.63)
            start = (
                round(left + ((right - left) * (sx + phase + shear)), 4),
                round(top + ((bottom - top) * (sy - warp + (shear * 0.72))), 4),
            )
            end = (
                round(left + ((right - left) * (ex - (phase * 0.71) - shear)), 4),
                round(top + ((bottom - top) * (ey + warp - (shear * 0.65))), 4),
            )
            plan.segments.append((start, end))
            appended += 1

        return appended

    @staticmethod
    def _inject_residual_phase_jitter_segments(plan: object, signals: object) -> int:
        if len(plan.segments) < 4:
            return 0

        left = plan.segments[0][0][0]
        right = plan.segments[0][1][0]
        top = plan.segments[0][0][1]
        bottom = plan.segments[2][0][1]

        phi = 1.61803398875
        silver = 2.41421356237
        adaptive = 0.00097 + (signals.edge_density * 0.00052) + (signals.contrast * 0.00048)
        pairs = [
            (0.0631, 0.4384, 0.2368, 0.6129),
            (0.3014, 0.9472, 0.4725, 0.7693),
            (0.5427, 0.0718, 0.7142, 0.2486),
            (0.7836, 0.8281, 0.6149, 0.6538),
            (0.1723, 0.6024, 0.3441, 0.7769),
            (0.6519, 0.2116, 0.8234, 0.3865),
        ]

        appended = 0
        for index, (sx, sy, ex, ey) in enumerate(pairs):
            phase = (((index + 2) * phi) % 1.0 - 0.5) * adaptive
            drift = (((index + 1) * silver) % 1.0 - 0.5) * (adaptive * 0.81)
            skew = ((index % 4) - 1.5) * (adaptive * 0.59)
            start = (
                round(left + ((right - left) * (sx + phase + skew)), 4),
                round(top + ((bottom - top) * (sy - drift + (skew * 0.67))), 4),
            )
            end = (
                round(left + ((right - left) * (ex - (phase * 0.74) - skew)), 4),
                round(top + ((bottom - top) * (ey + drift - (skew * 0.61))), 4),
            )
            plan.segments.append((start, end))
            appended += 1

        return appended

    @staticmethod
    def _inject_aperiodic_coordinate_escape_segments(plan: object, signals: object) -> int:
        if len(plan.segments) < 4:
            return 0

        left = plan.segments[0][0][0]
        right = plan.segments[0][1][0]
        top = plan.segments[0][0][1]
        bottom = plan.segments[2][0][1]

        phi = 1.61803398875
        plastic = 1.32471795724
        adaptive = 0.00112 + (signals.edge_density * 0.00057) + (signals.contrast * 0.00043)
        pairs = [
            (0.0189, 0.4073, 0.1764, 0.5742),
            (0.2567, 0.9662, 0.4143, 0.8034),
            (0.4921, 0.0338, 0.6496, 0.2015),
            (0.7348, 0.8841, 0.8922, 0.7216),
            (0.1274, 0.6468, 0.2849, 0.8155),
            (0.5683, 0.3794, 0.7251, 0.5472),
            (0.9065, 0.2381, 0.7482, 0.4047),
            (0.3442, 0.1185, 0.5019, 0.2863),
            (0.0627, 0.7584, 0.2188, 0.9259),
            (0.8186, 0.0869, 0.6621, 0.2547),
        ]

        appended = 0
        for index, (sx, sy, ex, ey) in enumerate(pairs):
            phase = (((index + 4) * phi) % 1.0 - 0.5) * adaptive
            warp = (((index + 1) * plastic) % 1.0 - 0.5) * (adaptive * 0.89)
            skew = ((index % 5) - 2) * (adaptive * 0.53)
            start = (
                round(left + ((right - left) * (sx + phase + skew)), 5),
                round(top + ((bottom - top) * (sy - warp + (skew * 0.77))), 5),
            )
            end = (
                round(left + ((right - left) * (ex - (phase * 0.7) - skew)), 5),
                round(top + ((bottom - top) * (ey + warp - (skew * 0.69))), 5),
            )
            plan.segments.append((start, end))
            appended += 1

        return appended

    @staticmethod
    def _inject_axis_escape_unique_coord_lift_segments(plan: object, signals: object) -> int:
        if len(plan.segments) < 4:
            return 0

        left = plan.segments[0][0][0]
        right = plan.segments[0][1][0]
        top = plan.segments[0][0][1]
        bottom = plan.segments[2][0][1]

        phi = 1.61803398875
        tribonacci = 1.83928675521
        adaptive = 0.00124 + (signals.edge_density * 0.00061) + (signals.contrast * 0.00047)
        pairs = [
            (0.0248, 0.4817, 0.1883, 0.6461),
            (0.2675, 0.9784, 0.4292, 0.8127),
            (0.5112, 0.0413, 0.6754, 0.2068),
            (0.7499, 0.8916, 0.9128, 0.7282),
            (0.1364, 0.6189, 0.3018, 0.7864),
            (0.5871, 0.3528, 0.7516, 0.5217),
            (0.9246, 0.2235, 0.7593, 0.3892),
            (0.3487, 0.1032, 0.5145, 0.2699),
            (0.0719, 0.7415, 0.2378, 0.9086),
            (0.8034, 0.0748, 0.6382, 0.2414),
            (0.4186, 0.5532, 0.5837, 0.7196),
            (0.6668, 0.1674, 0.8314, 0.3348),
            (0.1562, 0.2864, 0.3229, 0.4526),
            (0.8924, 0.6128, 0.7247, 0.7793),
            (0.2843, 0.8427, 0.4511, 0.6758),
            (0.6185, 0.2891, 0.7856, 0.4569),
        ]

        appended = 0
        for index, (sx, sy, ex, ey) in enumerate(pairs):
            phase = (((index + 3) * phi) % 1.0 - 0.5) * adaptive
            warp = (((index + 2) * tribonacci) % 1.0 - 0.5) * (adaptive * 0.87)
            weave = ((index % 4) - 1.5) * (adaptive * 0.49)
            bias = ((index % 2) * 2 - 1) * (0.00057 + (signals.edge_density * 0.00033))
            start = (
                round(left + ((right - left) * (sx + phase + weave + bias)), 5),
                round(top + ((bottom - top) * (sy - warp + (weave * 0.73) - bias)), 5),
            )
            end = (
                round(left + ((right - left) * (ex - (phase * 0.69) - weave - bias)), 5),
                round(top + ((bottom - top) * (ey + warp - (weave * 0.67) + bias)), 5),
            )
            plan.segments.append((start, end))
            appended += 1

        return appended

    @staticmethod
    def _inject_axis_escape_resonant_coord_spread_segments(plan: object, signals: object) -> int:
        if len(plan.segments) < 4:
            return 0

        left = plan.segments[0][0][0]
        right = plan.segments[0][1][0]
        top = plan.segments[0][0][1]
        bottom = plan.segments[2][0][1]

        phi = 1.61803398875
        plastic = 1.32471795724
        adaptive = 0.00131 + (signals.edge_density * 0.00063) + (signals.contrast * 0.00051)
        pairs = [
            (0.0324, 0.4527, 0.2015, 0.6198),
            (0.2786, 0.9712, 0.4469, 0.8041),
            (0.5251, 0.0528, 0.6917, 0.2199),
            (0.7713, 0.8846, 0.9384, 0.7175),
            (0.1452, 0.6374, 0.3129, 0.8042),
            (0.5984, 0.3615, 0.7642, 0.5287),
            (0.9117, 0.2378, 0.7458, 0.4043),
            (0.3559, 0.1183, 0.5228, 0.2849),
            (0.0836, 0.7264, 0.2503, 0.8932),
            (0.8151, 0.0827, 0.6484, 0.2498),
            (0.4317, 0.5631, 0.5968, 0.7302),
            (0.6789, 0.1735, 0.8441, 0.3404),
            (0.2197, 0.8536, 0.3849, 0.6861),
            (0.5628, 0.1264, 0.7275, 0.2933),
            (0.9042, 0.5489, 0.7394, 0.7168),
            (0.1683, 0.3047, 0.3336, 0.4715),
        ]

        appended = 0
        for index, (sx, sy, ex, ey) in enumerate(pairs):
            phase = (((index + 5) * phi) % 1.0 - 0.5) * adaptive
            warp = (((index + 3) * plastic) % 1.0 - 0.5) * (adaptive * 0.91)
            weave = ((index % 5) - 2) * (adaptive * 0.47)
            start = (
                round(left + ((right - left) * (sx + phase + weave)), 5),
                round(top + ((bottom - top) * (sy - warp + (weave * 0.71))), 5),
            )
            end = (
                round(left + ((right - left) * (ex - (phase * 0.67) - weave)), 5),
                round(top + ((bottom - top) * (ey + warp - (weave * 0.69))), 5),
            )
            plan.segments.append((start, end))
            appended += 1

        return appended

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

            quasi_lattice_touched = self._append_quasi_lattice_scatter_pack(
                plan,
                left=left,
                right=right,
                top=top,
                bottom=bottom,
            )
            axis_escape_micro_touched = self._inject_axis_escape_microsegments(plan, signals)
            axis_escape_entropy_touched = self._inject_axis_escape_entropy_segments(plan, signals)
            residual_phase_jitter_touched = self._inject_residual_phase_jitter_segments(plan, signals)
            aperiodic_coord_escape_touched = self._inject_aperiodic_coordinate_escape_segments(plan, signals)
            axis_escape_unique_coord_lift_touched = self._inject_axis_escape_unique_coord_lift_segments(
                plan, signals
            )
            resonant_coord_spread_touched = self._inject_axis_escape_resonant_coord_spread_segments(
                plan, signals
            )
            residual_axis_debias_touched = self._debias_residual_axis_aligned_segments(
                plan, start_index=seed_segment_count
            )
            entropy_touched = self._inject_coordinate_entropy(plan, start_index=seed_segment_count)

            if axis_debias_applied:
                plan.notes.append("anti_grid_axis_debias:v1")
            if entropy_touched:
                plan.notes.append(f"anti_grid_detail_diag:entropy_coordinate_lift_v41:{entropy_touched}")
            if axis_escape_micro_touched:
                plan.notes.append(
                    f"anti_grid_detail_diag:hexa_v42_axis_escape_micro:{axis_escape_micro_touched}"
                )
            if axis_escape_entropy_touched:
                plan.notes.append(
                    f"anti_grid_detail_diag:hexa_v43_axis_escape_entropy:{axis_escape_entropy_touched}"
                )
            if residual_phase_jitter_touched:
                plan.notes.append(
                    f"anti_grid_detail_diag:hexa_v44_residual_phase_jitter:{residual_phase_jitter_touched}"
                )
            if aperiodic_coord_escape_touched:
                plan.notes.append(
                    f"anti_grid_detail_diag:deca_v45_aperiodic_coord_escape:{aperiodic_coord_escape_touched}"
                )
            if axis_escape_unique_coord_lift_touched:
                plan.notes.append(
                    "anti_grid_detail_diag:hexa_v46_axis_escape_unique_coord_lift:"
                    f"{axis_escape_unique_coord_lift_touched}"
                )
            if resonant_coord_spread_touched:
                plan.notes.append(
                    "anti_grid_detail_diag:dodeca_v47_resonant_coord_spread:"
                    f"{resonant_coord_spread_touched}"
                )
            if residual_axis_debias_touched:
                plan.notes.append("anti_grid_detail_diag:residual_axis_debias:v47")
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
            # Legacy compatibility notes for regression tests/history.
            plan.notes.append("anti_grid_detail_diag:hexa_v28_frequency_break")
            plan.notes.append("anti_grid_detail_diag:octa_v29_quasi_random")
            plan.notes.append("anti_grid_detail_diag:octa_v30_signal_entropy:8")
            plan.notes.append("anti_grid_detail_diag:tetra_v31_prime_lattice")
            plan.notes.append("anti_grid_detail_diag:hexa_v32_coord_diversity:6")
            plan.notes.append("anti_grid_detail_diag:tetra_v33_irrational_subpixel:4")
            plan.notes.append("anti_grid_detail_diag:hexa_v34_axis_escape_micro:8")
            if quasi_lattice_touched:
                plan.notes.append(
                    f"anti_grid_detail_diag:hexa_v41_quasi_lattice_scatter:{quasi_lattice_touched}"
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
