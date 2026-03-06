from pathlib import Path

import pytest

from img2dwg.strategies.base import ConversionInput, ConversionOutput, ConversionStrategy
from img2dwg.strategies.registry import FeatureFlags, StrategyRegistry


class DummyStrategy(ConversionStrategy):
    name = "dummy"

    def run(self, conv_input: ConversionInput, output_dir: Path) -> ConversionOutput:
        return ConversionOutput(
            strategy_name=self.name,
            dxf_path=None,
            success=True,
            elapsed_ms=0.0,
            notes=[conv_input.image_path.name],
        )


class HighRiskDummyStrategy(DummyStrategy):
    name = "dummy_high"
    risk_tier = "high"


def test_registry_register_and_get() -> None:
    reg = StrategyRegistry()
    reg.register(DummyStrategy())

    strategy = reg.get("dummy")
    out = strategy.timed_run(ConversionInput(image_path=Path("sample.png")), Path("."))

    assert out.success is True
    assert out.strategy_name == "dummy"
    assert "sample.png" in out.notes[0]


def test_registry_feature_flags() -> None:
    reg = StrategyRegistry()
    reg.register(DummyStrategy())
    reg.register(HighRiskDummyStrategy())

    safe_only = reg.get_enabled_names(FeatureFlags())
    assert safe_only == ["dummy"]

    # safeguard: high-risk mode only is not enough, allowlist is required
    with_high_no_allowlist = reg.get_enabled_names(FeatureFlags(enable_high_risk=True))
    assert with_high_no_allowlist == ["dummy"]

    allowlisted = reg.get_enabled_names(
        FeatureFlags(enable_high_risk=True, high_risk_allowlist=["dummy_high"])
    )
    assert allowlisted == ["dummy", "dummy_high"]


def test_feature_flags_allowlist_normalization() -> None:
    flags = FeatureFlags(enable_high_risk=True, high_risk_allowlist=[" dummy_high ", "", "dummy_high"])

    assert flags.high_risk_allowlist == ["dummy_high"]


def test_resolve_requested_names_blocks_high_risk_without_allowlist() -> None:
    reg = StrategyRegistry()
    reg.register(DummyStrategy())
    reg.register(HighRiskDummyStrategy())

    with pytest.raises(ValueError, match="Blocked strategies by feature flags: dummy_high"):
        reg.resolve_requested_names(["dummy_high"], FeatureFlags(enable_high_risk=True))


def test_resolve_requested_names_accepts_allowlisted_high_risk() -> None:
    reg = StrategyRegistry()
    reg.register(DummyStrategy())
    reg.register(HighRiskDummyStrategy())

    selected = reg.resolve_requested_names(
        ["dummy", "dummy_high"],
        FeatureFlags(enable_high_risk=True, high_risk_allowlist=["dummy_high"]),
    )

    assert selected == ["dummy", "dummy_high"]


def test_resolve_requested_names_rejects_unknown_strategy() -> None:
    reg = StrategyRegistry()
    reg.register(DummyStrategy())

    with pytest.raises(ValueError, match="Unknown strategies requested: missing"):
        reg.resolve_requested_names(["dummy", "missing"], FeatureFlags())


def test_registry_get_unknown_strategy_raises_keyerror() -> None:
    reg = StrategyRegistry()

    with pytest.raises(KeyError, match="Unknown strategy: missing"):
        reg.get("missing")
