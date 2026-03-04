"""시크릿 문자열 마스킹 유틸리티."""

from __future__ import annotations

import re

_MASK = "***"

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    # GitHub classic token (ghp_...)
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    # GitHub fine-grained PAT (github_pat_...)
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    # OpenAI API key (sk-..., sk-proj-...)
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    # Generic Bearer/JWT-like access token
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}\b", re.IGNORECASE),
)

# URL credential 구간: scheme://user:password@host
_URL_CREDENTIAL_PATTERN = re.compile(r"(?P<prefix>https?://[^\s/@:]+:)(?P<secret>[^\s/@]+)(?P<suffix>@)")


def _mask_value(value: str, keep_prefix: int = 4, keep_suffix: int = 3) -> str:
    """토큰 문자열 일부를 보존하고 나머지를 마스킹한다."""
    if len(value) <= keep_prefix + keep_suffix:
        return _MASK
    return f"{value[:keep_prefix]}{_MASK}{value[-keep_suffix:]}"


def _mask_token(token: str) -> str:
    """토큰 타입별로 식별 가능한 접두어를 남기고 마스킹한다."""
    if token.startswith("github_pat_"):
        return "github_pat_***"
    if token.startswith("sk-"):
        return f"sk-{_MASK}{token[-3:]}"
    return _mask_value(token)


def mask_secrets(text: str) -> str:
    """문자열 내 민감정보 패턴을 마스킹한다."""
    masked = text

    def _mask_url_credential(match: re.Match[str]) -> str:
        secret = match.group("secret")
        return f"{match.group('prefix')}{_mask_token(secret)}{match.group('suffix')}"

    masked = _URL_CREDENTIAL_PATTERN.sub(_mask_url_credential, masked)

    for pattern in _SECRET_PATTERNS:
        if "Bearer" in pattern.pattern:
            masked = pattern.sub(lambda m: f"Bearer {_mask_token(m.group(0).split(maxsplit=1)[1])}", masked)
        else:
            masked = pattern.sub(lambda m: _mask_token(m.group(0)), masked)

    return masked
