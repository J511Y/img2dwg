from __future__ import annotations

from pathlib import Path

from .base import ConversionInput, ConversionOutput, ConversionStrategy


class HybridMVPStrategy(ConversionStrategy):
    name = "hybrid_mvp"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        output_dir.mkdir(parents=True, exist_ok=True)
        # TODO: connect real hybrid pipeline (geometry + OCR + confidence queue)
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=None,
            success=False,
            elapsed_ms=0.0,
            notes=[f"stub: implement hybrid pipeline for {conv_input.image_path.name}"],
        )
