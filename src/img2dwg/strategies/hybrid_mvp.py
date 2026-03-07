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
