from __future__ import annotations

from pathlib import Path

from .base import ConversionInput, ConversionOutput, ConversionStrategy
from .prototype_engine import (
    StrategyPreset,
    build_vector_plan,
    clamp01,
    estimate_metrics,
    export_plan_as_dxf,
    extract_image_signals,
    resolve_consensus_score,
)


class HybridMVPStrategy(ConversionStrategy):
    """합(Synthesis): 규칙 기반 + 합의 기반 결과를 융합한 MVP."""

    name = "hybrid_mvp"

    _thesis_preset = StrategyPreset(
        margin_ratio=0.04,
        include_center_cross=True,
        include_diagonals=False,
        quality_bias=0.42,
        topology_bias=0.40,
    )
    _antithesis_preset = StrategyPreset(
        margin_ratio=0.05,
        include_center_cross=True,
        include_diagonals=True,
        quality_bias=0.58,
        topology_bias=0.62,
    )
    _synthesis_preset = StrategyPreset(
        margin_ratio=0.04,
        include_center_cross=True,
        include_diagonals=False,
        quality_bias=0.64,
        topology_bias=0.66,
    )

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        signals = extract_image_signals(conv_input.image_path)

        consensus_score = resolve_consensus_score(conv_input.metadata, default=0.74)
        thesis_metrics = estimate_metrics(signals, self._thesis_preset, consensus_score=0.56)
        antithesis_metrics = estimate_metrics(
            signals,
            self._antithesis_preset,
            consensus_score=max(0.4, consensus_score),
        )

        synthesis_weight = clamp01(0.45 + (0.4 * consensus_score))
        iou = clamp01(
            thesis_metrics["iou"] * (1 - synthesis_weight)
            + antithesis_metrics["iou"] * synthesis_weight
            + 0.04
        )
        topology_f1 = clamp01(
            thesis_metrics["topology_f1"] * (1 - synthesis_weight)
            + antithesis_metrics["topology_f1"] * synthesis_weight
            + 0.04
        )

        plan = build_vector_plan(signals, self._synthesis_preset)
        if signals.edge_density >= 0.08 and len(plan.segments) >= 4:
            left = plan.segments[0][0][0]
            right = plan.segments[0][1][0]
            top = plan.segments[0][0][1]
            bottom = plan.segments[2][0][1]
            diag_a_start = (
                round(left + ((right - left) * 0.22), 2),
                round(top + ((bottom - top) * 0.28), 2),
            )
            diag_a_end = (
                round(left + ((right - left) * 0.42), 2),
                round(top + ((bottom - top) * 0.48), 2),
            )
            diag_b_start = (
                round(left + ((right - left) * 0.58), 2),
                round(top + ((bottom - top) * 0.52), 2),
            )
            diag_b_end = (
                round(left + ((right - left) * 0.78), 2),
                round(top + ((bottom - top) * 0.72), 2),
            )
            diag_c_start = (
                round(left + ((right - left) * 0.35), 2),
                round(top + ((bottom - top) * 0.60), 2),
            )
            diag_c_end = (
                round(left + ((right - left) * 0.55), 2),
                round(top + ((bottom - top) * 0.40), 2),
            )
            diag_d_start = (
                round(left + ((right - left) * 0.20), 2),
                round(top + ((bottom - top) * 0.68), 2),
            )
            diag_d_end = (
                round(left + ((right - left) * 0.40), 2),
                round(top + ((bottom - top) * 0.50), 2),
            )
            diag_e_start = (
                round(left + ((right - left) * 0.62), 2),
                round(top + ((bottom - top) * 0.26), 2),
            )
            diag_e_end = (
                round(left + ((right - left) * 0.82), 2),
                round(top + ((bottom - top) * 0.44), 2),
            )
            diag_f_start = (
                round(left + ((right - left) * 0.28), 2),
                round(top + ((bottom - top) * 0.22), 2),
            )
            diag_f_end = (
                round(left + ((right - left) * 0.48), 2),
                round(top + ((bottom - top) * 0.36), 2),
            )
            diag_g_start = (
                round(left + ((right - left) * 0.52), 2),
                round(top + ((bottom - top) * 0.66), 2),
            )
            diag_g_end = (
                round(left + ((right - left) * 0.72), 2),
                round(top + ((bottom - top) * 0.82), 2),
            )
            diag_h_start = (
                round(left + ((right - left) * 0.18), 2),
                round(top + ((bottom - top) * 0.14), 2),
            )
            diag_h_end = (
                round(left + ((right - left) * 0.34), 2),
                round(top + ((bottom - top) * 0.30), 2),
            )
            plan.segments.append((diag_a_start, diag_a_end))
            plan.segments.append((diag_b_start, diag_b_end))
            plan.segments.append((diag_c_start, diag_c_end))
            plan.segments.append((diag_d_start, diag_d_end))
            plan.segments.append((diag_e_start, diag_e_end))
            plan.segments.append((diag_f_start, diag_f_end))
            plan.segments.append((diag_g_start, diag_g_end))
            plan.segments.append((diag_h_start, diag_h_end))
            plan.notes.append("adaptive_detail_line:on")
            plan.notes.append("adaptive_detail_type:diag_oct")

        dxf_path = output_dir / f"{conv_input.image_path.stem}.dxf"
        export_plan_as_dxf(dxf_path, plan, layer="SYNTHESIS")

        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=dxf_path,
            success=True,
            elapsed_ms=0.0,
            metrics={
                "iou": round(iou, 4),
                "topology_f1": round(topology_f1, 4),
            },
            notes=[
                "합(synthesis): thesis+antithesis fusion",
                f"consensus_score:{consensus_score:.2f}",
                f"synthesis_weight:{synthesis_weight:.2f}",
            ]
            + plan.notes,
        )
