from __future__ import annotations

from dataclasses import dataclass, field

from .base import ConversionStrategy


@dataclass(slots=True)
class FeatureFlags:
    enable_high_risk: bool = False
    high_risk_allowlist: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Safety default: normalize input and remove empty / duplicated strategy names.
        self.high_risk_allowlist = sorted(
            {
                name.strip()
                for name in self.high_risk_allowlist
                if isinstance(name, str) and name.strip()
            }
        )


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

    def get_enabled_names(self, flags: FeatureFlags) -> list[str]:
        enabled: list[str] = []
        for name in self.list_names():
            strategy = self.get(name)
            if strategy.risk_tier == "high":
                if not flags.enable_high_risk:
                    continue
                # Fail-closed safeguard:
                # even when high-risk mode is enabled, explicit allowlist is mandatory.
                if not flags.high_risk_allowlist:
                    continue
                if name not in flags.high_risk_allowlist:
                    continue
            enabled.append(name)
        return enabled

    def resolve_requested_names(self, requested_names: list[str], flags: FeatureFlags) -> list[str]:
        """Normalize user input and enforce feature-flag risk safeguards."""
        normalized: list[str] = []
        seen: set[str] = set()
        for name in requested_names:
            cleaned = name.strip()
            if not cleaned or cleaned in seen:
                continue
            normalized.append(cleaned)
            seen.add(cleaned)

        if not normalized:
            return self.get_enabled_names(flags)

        known_names = set(self.list_names())
        unknown = [name for name in normalized if name not in known_names]
        if unknown:
            raise ValueError(f"Unknown strategies requested: {', '.join(unknown)}")

        enabled = set(self.get_enabled_names(flags))
        blocked = [name for name in normalized if name not in enabled]
        if blocked:
            blocked_display = ", ".join(blocked)
            raise ValueError(
                "Blocked strategies by feature flags: "
                f"{blocked_display}. "
                "For high-risk strategies, use --enable-high-risk "
                "with --high-risk-allowlist=<strategy_name>."
            )

        return normalized

    def get_safe_default(self) -> ConversionStrategy:
        for name in self.list_names():
            strategy = self.get(name)
            if strategy.risk_tier == "safe":
                return strategy
        raise RuntimeError("No safe strategy registered")
