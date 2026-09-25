#!/usr/bin/env bash
# Runs one agent evaluation on a POSIX shell. Pipeline script steps invoke this
# directly on Linux/macOS and through Git Bash on Windows.

set -euo pipefail

case_path=${1:?case path is required}
. evals/bootstrap-teamcity-cli.sh

# A generated MCP config contains a server-provided bearer token. Keep its
# lifetime to this script and remove it even when the runner fails.
mcp_config_path=""
cleanup_mcp_config() {
  if [ -n "$mcp_config_path" ]; then
    rm -f -- "$mcp_config_path"
  fi
}
trap cleanup_mcp_config EXIT

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

case "${EVAL_TOOL_MODE:-cli-only}" in
  cli-only) ;;
  mcp-only|cli+mcp)
    if [ -z "${EVAL_MCP_CONFIG:-}" ]; then
      : "${TEAMCITY_URL:?TEAMCITY_URL is required to create the TeamCity MCP config}"
      : "${EVAL_MCP_TOKEN:?EVAL_MCP_TOKEN must be a secure TeamCity parameter for MCP modes}"
      mcp_config_directory="${TEAMCITY_BUILD_TEMP_DIR:-${TMPDIR:-/tmp}}"
      umask 077
      mcp_config_path="$(mktemp "$mcp_config_directory/teamcity-evals-mcp.XXXXXX")"
      "${python_command[@]}" evals/write_teamcity_mcp_config.py \
        --server "$TEAMCITY_URL" \
        --output "$mcp_config_path"
      export EVAL_MCP_CONFIG="$mcp_config_path"
    fi
    # Use the same Claude MCP client as the agent to probe this ephemeral
    # configuration. The command's text can include connection details, so it
    # is reduced to a fixed status before the runner starts.
    mcp_preflight_output="$(claude --mcp-config "$EVAL_MCP_CONFIG" --strict-mcp-config mcp list 2>&1 || true)"
    mcp_preflight_text="$(printf '%s' "$mcp_preflight_output" | tr '[:upper:]' '[:lower:]')"
    case "$mcp_preflight_text" in
      *"disable sideload"*|*"disablesideloadflags"*) EVAL_MCP_PREFLIGHT_STATUS="sideload-flags-disabled" ;;
      *"enterprise mcp config"*|*"managed-mcp.json"*) EVAL_MCP_PREFLIGHT_STATUS="enterprise-managed-config" ;;
      *"blocked by enterprise policy"*|*"mcp server blocked"*) EVAL_MCP_PREFLIGHT_STATUS="enterprise-policy-blocked" ;;
      *"pending approval"*|*"approval required"*) EVAL_MCP_PREFLIGHT_STATUS="approval-required" ;;
      *"unauthorized"*|*"authentication failed"*|*"401"*) EVAL_MCP_PREFLIGHT_STATUS="authentication-failed" ;;
      *"forbidden"*|*"403"*|*"permission denied"*) EVAL_MCP_PREFLIGHT_STATUS="access-denied" ;;
      *"failed to connect"*|*"connection refused"*|*"not connected"*) EVAL_MCP_PREFLIGHT_STATUS="connection-failed" ;;
      *"invalid mcp configuration"*|*"mcp config"*"not valid json"*) EVAL_MCP_PREFLIGHT_STATUS="config-invalid" ;;
      *"connected"*) EVAL_MCP_PREFLIGHT_STATUS="connected" ;;
      *) EVAL_MCP_PREFLIGHT_STATUS="unknown" ;;
    esac
    export EVAL_MCP_PREFLIGHT_STATUS
    unset mcp_preflight_output mcp_preflight_text
    # The agent receives the configured MCP client, never the source variable.
    unset EVAL_MCP_TOKEN
    ;;
  *)
    echo "EVAL_TOOL_MODE must be cli-only, mcp-only, or cli+mcp." >&2
    exit 2
    ;;
esac

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
