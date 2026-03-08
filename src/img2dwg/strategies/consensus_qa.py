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
            plan.segments.append((diag_a_start, diag_a_end))
            plan.segments.append((diag_b_start, diag_b_end))
            plan.segments.append((diag_c_start, diag_c_end))
            plan.segments.append((diag_d_start, diag_d_end))
            plan.segments.append((diag_e_start, diag_e_end))
            plan.segments.append((diag_f_start, diag_f_end))
            plan.notes.append("anti_grid_detail_diag:on")
            plan.notes.append("anti_grid_detail_diag:sext")

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
