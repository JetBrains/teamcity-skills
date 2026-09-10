#!/usr/bin/env bash
# Runs one agent evaluation on a POSIX shell. Pipeline script steps invoke this
# directly on Linux/macOS and through Git Bash on Windows.

set -euo pipefail

case_path=${1:?case path is required}
. evals/bootstrap-teamcity-cli.sh

if command -v claude >/dev/null 2>&1; then
  claude --version
elif command -v claude.cmd >/dev/null 2>&1; then
  claude.cmd --version
else
  echo "Claude Code was not provided by the JCP Central AI Agent feature." >&2
  exit 1
fi

if command -v teamcity >/dev/null 2>&1; then
  teamcity --version
elif command -v teamcity.cmd >/dev/null 2>&1; then
  teamcity.cmd --version
else
  echo "The TeamCity CLI bootstrap did not provide the teamcity command." >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  python_command=(python3)
elif command -v python >/dev/null 2>&1; then
  python_command=(python)
elif command -v py.exe >/dev/null 2>&1; then
  python_command=(py.exe -3)
elif command -v py >/dev/null 2>&1; then
  python_command=(py -3)
else
  echo "Python 3 is required to run the evaluation runner (tried python3, python, and py -3)." >&2
  exit 1
fi

"${python_command[@]}" -m pip install --user --quiet PyYAML
: "${TEAMCITY_TOKEN:?TEAMCITY_TOKEN is required}"
# Keep the lifecycle token out of the agent's inherited environment. The runner
# consumes and closes this short-lived descriptor before launching the
# checkout-controlled agent process.
exec 3<<<"$TEAMCITY_TOKEN"
unset TEAMCITY_TOKEN
"${python_command[@]}" evals/run_case.py \
  --case "$case_path" \
  --result eval-result.json \
  --teamcity-token-fd 3
test -s eval-result.json
