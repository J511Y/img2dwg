"""develop 브랜치 merge 시 linked issue 상태를 동기화한다."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from img2dwg.utils.issue_links import extract_issue_links

STATUS_LABELS_TO_CLEAR = {
    "status:triage",
    "status:in-progress",
    "status:in-review",
    "status:done",
    "in-progress",
    "in-review",
    "done",
}
DONE_LABEL = "status:done"


def _api_request(
    method: str,
    path: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"https://api.github.com{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "img2dwg-issue-lifecycle-sync")
    if data is not None:
        req.add_header("Content-Type", "application/json")

    try:
        with urlopen(req) as response:
            body = response.read().decode("utf-8")
    except HTTPError as error:
        error_body = error.read().decode("utf-8")
        raise RuntimeError(
            f"GitHub API failed ({error.code}) {method} {path}: {error_body}"
        ) from error

    if not body:
        return {}
    parsed: Any = json.loads(body)
    if isinstance(parsed, dict):
        return parsed
    return {}


def _build_done_labels(existing_labels: list[str]) -> list[str]:
    labels = [label for label in existing_labels if label not in STATUS_LABELS_TO_CLEAR]
    labels.append(DONE_LABEL)
    # 순서 고정을 위해 dedupe
    return list(dict.fromkeys(labels))


def _transition_issue_to_done(
    repo: str,
    issue_number: int,
    token: str,
    pr_number: int,
    merge_sha: str,
) -> None:
    issue_path = f"/repos/{repo}/issues/{issue_number}"
    issue_data = _api_request("GET", issue_path, token)
    labels = [item["name"] for item in issue_data.get("labels", []) if "name" in item]
    new_labels = _build_done_labels(labels)

    _api_request(
        "PATCH",
        issue_path,
        token,
        payload={
            "state": "closed",
            "labels": new_labels,
        },
    )

    short_sha = merge_sha[:7]
    comment_body = (
        "✅ develop 머지 감지로 상태를 자동 전환했습니다.\n\n"
        f"- merged PR: #{pr_number}\n"
        f"- commit: `{short_sha}`\n"
        f"- status: `status:done`"
    )
    _api_request(
        "POST",
        f"{issue_path}/comments",
        token,
        payload={"body": comment_body},
    )


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if not event_path or not token:
        raise RuntimeError("GITHUB_EVENT_PATH와 GITHUB_TOKEN 환경변수가 필요합니다.")

    with open(event_path, encoding="utf-8") as handle:
        event = json.load(handle)

    pull_request = event.get("pull_request", {})
    merged = bool(pull_request.get("merged"))
    base_ref = pull_request.get("base", {}).get("ref", "")

    if not merged or base_ref != "develop":
        print("Skip: merged develop PR 조건을 만족하지 않습니다.")
        return 0

    if not repo:
        repo = event.get("repository", {}).get("full_name", "")
    if not repo:
        raise RuntimeError("저장소 이름을 확인할 수 없습니다.")

    pr_number = int(pull_request["number"])
    title = str(pull_request.get("title", ""))
    body = str(pull_request.get("body", ""))
    merge_sha = str(pull_request.get("merge_commit_sha", ""))

    links = extract_issue_links(f"{title}\n{body}")

    if not links.closing_ids:
        print(f"No closing issue references found for PR #{pr_number}.")
        return 0

    for issue_number in sorted(links.closing_ids):
        _transition_issue_to_done(repo, issue_number, token, pr_number, merge_sha)
        print(f"Updated issue #{issue_number} -> status:done")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
