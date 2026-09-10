#!/usr/bin/env bash
set -euo pipefail

if command -v python3 >/dev/null 2>&1; then
  python_command=(python3)
elif command -v python >/dev/null 2>&1; then
  python_command=(python)
elif command -v py.exe >/dev/null 2>&1; then
  python_command=(py.exe -3)
elif command -v py >/dev/null 2>&1; then
  python_command=(py -3)
else
  echo "Python 3 is required for eval project cleanup." >&2
  exit 1
fi

mode=${CLEANUP_MODE:-dry-run}
args=(
  --server "${TEAMCITY_URL:?TEAMCITY_URL is required}"
  --parent-project "${EVAL_PARENT_PROJECT:?EVAL_PARENT_PROJECT is required}"
  --mode "$mode"
  --ttl-hours "${CLEANUP_TTL_HOURS:-6}"
  --delete-grace-hours "${CLEANUP_DELETE_GRACE_HOURS:-24}"
  --report cleanup-report.json
)

if [[ $mode != dry-run ]]; then
  [[ ${CLEANUP_APPLY:-false} == true ]] || {
    echo "CLEANUP_APPLY=true is required for archive/delete." >&2
    exit 2
  }
  args+=(--apply --confirm-parent "${CLEANUP_CONFIRM_PARENT:-}")
fi

"${python_command[@]}" evals/cleanup_teamcity_projects.py "${args[@]}"
