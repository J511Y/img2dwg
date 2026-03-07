# VED Test Strategy (Issue #6)

## Covered branches (current)
- `dataset._load_samples` malformed input guards:
  - non-list `messages`
  - non-dict message entries
  - missing/non-list user `content`
  - non-dict `content` items
  - malformed `image_url` payload (`image_url` non-dict, `url` non-string/empty)
  - assistant `content` non-string/empty/whitespace
- image selection rules:
  - first `image_url` from user content
  - first user/assistant role match, no assistant fallback
- remote loader:
  - cache hit skips network
  - cache write/read path
  - offline cache miss fail / offline cache hit success
  - retry policy for transient errors, 429 retry, 5xx retry exhaustion
  - hard 4xx non-retry behavior

## Remaining priority branches
1. `_load_samples` line-level robustness for mixed very-large JSONL and partial corruption stats/logging policy
2. dataset-level integration smoke for representative mixed corpus (valid + malformed rows)
3. coverage-gate policy split (changed-file gate in CI) to avoid global fail-under instability

## Working rule
- Prefer minimal, isolated regression tests per branch.
- Keep one behavior assertion per test where possible.
- When hardening parser behavior, add test first then minimal guard implementation.
