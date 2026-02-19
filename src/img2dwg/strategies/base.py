from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any


@dataclass(slots=True)
class ConversionInput:
    image_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConversionOutput:
    strategy_name: str
    dxf_path: Path | None
    success: bool
    elapsed_ms: float
    metrics: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


class ConversionStrategy(ABC):
    """Abstract strategy for image->DXF conversion experiments."""

    name: str

    @abstractmethod
    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        """Run conversion for a single input sample."""

    def timed_run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        start = perf_counter()
        output = self.run(conv_input, output_dir)
        output.elapsed_ms = round((perf_counter() - start) * 1000, 2)
        return output
