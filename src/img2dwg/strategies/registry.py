from __future__ import annotations

from dataclasses import dataclass, field

from .base import ConversionStrategy


@dataclass(slots=True)
class StrategyRegistry:
    _strategies: dict[str, ConversionStrategy] = field(default_factory=dict)

    def register(self, strategy: ConversionStrategy) -> None:
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> ConversionStrategy:
        if name not in self._strategies:
            raise KeyError(f"Unknown strategy: {name}")
        return self._strategies[name]

    def list_names(self) -> list[str]:
        return sorted(self._strategies.keys())
