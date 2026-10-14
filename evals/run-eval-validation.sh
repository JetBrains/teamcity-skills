#!/usr/bin/env bash
# Run the static validation or grader self-check without a Linux container.
# It is invoked through Git Bash on Windows, so the detection below must work
# on Linux, macOS, and Windows agents.

set -euo pipefail

mode=${1:?expected validate or selfcheck}
case "$mode" in
  validate|selfcheck) ;;
  *) echo "unknown validation mode: $mode" >&2; exit 2 ;;
esac

# Only the self-check creates and reads a fixture through the TeamCity CLI.
# Schema validation stays independent of Node/npm so it can run on every
# self-hosted agent with Python.
if [ "$mode" = selfcheck ]; then
  . evals/bootstrap-teamcity-cli.sh
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
  echo "Python 3 is required (tried python3, python, and py -3)." >&2
  exit 1
fi

venv_dir="${TEAMCITY_EVAL_VENV_DIR:-${TMPDIR:-/tmp}/teamcity-evals-venv}"
"${python_command[@]}" -m venv "$venv_dir"
if [ -x "$venv_dir/bin/python" ]; then
  venv_python="$venv_dir/bin/python"
else
  venv_python="$venv_dir/Scripts/python.exe"
fi
"$venv_python" -m pip install --quiet --requirement evals/requirements.txt PyYAML

if [ "$mode" = validate ]; then
  "$venv_python" evals/validate.py
  "$venv_python" -m unittest discover -s evals/tests -p 'test_*.py'
else
  "$venv_python" evals/selfcheck.py
fi
