"""GitHub 이슈 링크 파싱 유틸리티."""

from __future__ import annotations

import re
from dataclasses import dataclass

_CLOSE_KEYWORD_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b", re.IGNORECASE)
_REF_KEYWORD_RE = re.compile(r"\brefs?\b", re.IGNORECASE)
_ISSUE_REF_RE = re.compile(
    r"(?:https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/|"
    r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#|#)(\d+)"
)


@dataclass(frozen=True)
class IssueLinks:
    """PR 텍스트에서 추출한 이슈 링크 집합."""

    closing_ids: set[int]
    reference_ids: set[int]


def _extract_issue_ids_from_text(text: str) -> set[int]:
    return {int(match.group(1)) for match in _ISSUE_REF_RE.finditer(text)}


def _extract_ids_by_keyword(text: str, keyword_re: re.Pattern[str]) -> set[int]:
    issue_ids: set[int] = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        for keyword_match in keyword_re.finditer(line):
            tail = line[keyword_match.end() :]
            issue_ids.update(_extract_issue_ids_from_text(tail))
    return issue_ids


def extract_issue_links(text: str | None) -> IssueLinks:
    """PR 본문/제목에서 closing/ref 이슈 번호를 분리 추출한다."""

    if text is None:
        return IssueLinks(closing_ids=set(), reference_ids=set())

    closing_ids = _extract_ids_by_keyword(text, _CLOSE_KEYWORD_RE)
    reference_ids = _extract_ids_by_keyword(text, _REF_KEYWORD_RE) - closing_ids
    return IssueLinks(closing_ids=closing_ids, reference_ids=reference_ids)
