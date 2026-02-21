from pathlib import Path

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

    with_high = reg.get_enabled_names(FeatureFlags(enable_high_risk=True))
    assert with_high == ["dummy", "dummy_high"]

    allowlisted = reg.get_enabled_names(
        FeatureFlags(enable_high_risk=True, high_risk_allowlist=["dummy_high"])
    )
    assert allowlisted == ["dummy", "dummy_high"]
