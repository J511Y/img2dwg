#!/usr/bin/env bash
set -euo pipefail

BASE_REF="${BASE_REF:-origin/master}"

CHANGED_PY=$(git diff --name-only --diff-filter=ACMRTUXB "$BASE_REF"...HEAD -- '*.py')

if [[ -z "${CHANGED_PY}" ]]; then
  echo "[static-gate] no changed python files"
  exit 0
fi

echo "[static-gate] base_ref=${BASE_REF}"
printf '%s\n' "${CHANGED_PY}"

.venv/bin/ruff check ${CHANGED_PY}
.venv/bin/ruff format --check ${CHANGED_PY}

MYPY_TARGETS=$(printf '%s\n' "${CHANGED_PY}" | grep -v '^tests/' || true)
if [[ -n "${MYPY_TARGETS}" ]]; then
  .venv/bin/mypy ${MYPY_TARGETS}
else
  echo "[static-gate] mypy skipped (no non-test python files)"
fi
