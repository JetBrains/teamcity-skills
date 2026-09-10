#!/usr/bin/env bash
# Build the safe TeamCity eval dashboard.  The output directory is intended
# only for a build artifact and is never committed.

set -euo pipefail

. evals/bootstrap-teamcity-cli.sh

if command -v python3 >/dev/null 2>&1; then
  python_command=(python3)
elif command -v python >/dev/null 2>&1; then
  python_command=(python)
elif command -v py.exe >/dev/null 2>&1; then
  python_command=(py.exe -3)
elif command -v py >/dev/null 2>&1; then
  python_command=(py -3)
else
  echo "Python 3 is required (tried python3, python, and py -3)." >&2
  exit 1
fi

: "${TEAMCITY_URL:?TEAMCITY_URL is required}"
: "${EVAL_PIPELINES:?EVAL_PIPELINES is required (comma-separated pipeline head IDs)}"
report_dir="${EVAL_REPORT_DIR:-.teamcity/evaluation-report}"
report_limit="${EVAL_REPORT_LIMIT:-32}"
mkdir -p "$report_dir"

IFS=',' read -r -a pipeline_ids <<< "$EVAL_PIPELINES"
pipeline_args=()
for pipeline_id in "${pipeline_ids[@]}"; do
  [[ -n "$pipeline_id" ]] || {
    echo "EVAL_PIPELINES contains an empty pipeline ID." >&2
    exit 2
  }
  pipeline_args+=(--pipeline "$pipeline_id")
done

"${python_command[@]}" evals/collect_teamcity_eval_runs.py \
  --server "$TEAMCITY_URL" \
  "${pipeline_args[@]}" \
  --limit "$report_limit" \
  --exclude-job-name "Publish evaluation report" \
  --output "$report_dir/runs.json"
"${python_command[@]}" evals/render_teamcity_eval_report.py \
  --input "$report_dir/runs.json" \
  --output "$report_dir/index.html"
