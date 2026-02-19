"""Strategy implementations for comparing image->CAD approaches."""

from .base import ConversionInput, ConversionOutput, ConversionStrategy
from .registry import StrategyRegistry

__all__ = [
    "ConversionInput",
    "ConversionOutput",
    "ConversionStrategy",
    "StrategyRegistry",
]
