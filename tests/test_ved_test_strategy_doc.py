from __future__ import annotations

from pathlib import Path


def test_ved_test_strategy_doc_contains_core_sections() -> None:
    content = Path("docs/ved-test-strategy.md").read_text(encoding="utf-8")

    assert "# VED Test Strategy" in content
    assert "Covered branches" in content
    assert "Remaining priority branches" in content
