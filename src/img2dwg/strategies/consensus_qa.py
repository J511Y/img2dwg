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
        # and off-grid shift from observed image complexity and consensus confidence.
        complexity = (signals.contrast * 0.42) + (signals.edge_density * 0.58)
        complexity_bonus = max(0, min(16, int(round(complexity * 20.0)) - 4))
        confidence_bonus = max(0, min(7, int(round((consensus_score - 0.68) * 26.0))))

        tuned_preset = replace(
            preset,
            debias_chord_multiplier=preset.debias_chord_multiplier + complexity_bonus + confidence_bonus,
            offgrid_shift_ratio=preset.offgrid_shift_ratio + min(0.024, complexity * 0.024),
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
