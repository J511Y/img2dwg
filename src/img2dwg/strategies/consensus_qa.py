from __future__ import annotations

from pathlib import Path

from .base import ConversionInput, ConversionOutput, ConversionStrategy


class ConsensusQAStrategy(ConversionStrategy):
    name = "consensus_qa"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        # TODO: connect consensus QA + feedback replay gate
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=None,
            success=False,
            elapsed_ms=0.0,
            notes=[f"stub: implement consensus QA for {conv_input.image_path.name}"],
        )
