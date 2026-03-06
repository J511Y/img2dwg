"""시크릿 마스킹 유틸리티 테스트."""

from __future__ import annotations

from img2dwg.utils.logger import get_logger, setup_logging
from img2dwg.utils.secrets import mask_secrets


def test_mask_github_pat_token() -> None:
    token = "github_pat_abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_"
    masked = mask_secrets(f"url token={token}")

    assert token not in masked
    assert "github_pat_" in masked
    assert "***" in masked


def test_mask_openai_key_and_bearer_token() -> None:
    openai_key = "sk-proj-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"
    bearer_value = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abcdef0123456789"

    masked = mask_secrets(f"{openai_key}\n{bearer_value}")

    assert openai_key not in masked
    assert "sk-***" in masked
    assert "Bearer " in masked
    assert bearer_value not in masked


def test_mask_url_embedded_credentials() -> None:
    raw = "https://x-access-token:github_pat_abcdefghijklmnopqrstuvwxyz0123456789ABCDE@github.com/repo.git"
    masked = mask_secrets(raw)

    assert "github_pat_abcdefghijklmnopqrstuvwxyz" not in masked
    assert "x-access-token:" in masked
    assert "***" in masked


def test_setup_logging_masks_secret_output(capsys) -> None:
    setup_logging(log_level="INFO", enable_secret_masking=True)
    logger = get_logger("test.secret")

    token = "ghp_1234567890abcdefghijklmnopqrstuvwxyzAB"
    logger.info("will mask: %s", token)

    captured = capsys.readouterr().out
    assert token not in captured
    assert "***" in captured
