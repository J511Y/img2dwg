"""Strategy implementations for comparing image->CAD approaches."""

from .base import ConversionInput, ConversionOutput, ConversionStrategy
from .registry import FeatureFlags, StrategyRegistry

__all__ = [
    "ConversionInput",
    "ConversionOutput",
    "ConversionStrategy",
    "StrategyRegistry",
    "FeatureFlags",
]
