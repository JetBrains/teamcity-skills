# Source this file from a TeamCity script step before invoking `teamcity`.
# JCP Central places Claude Code on the host agent. The agent may not include
# Node/npm, so the CLI is installed in an isolated build-temporary directory.

set -eu

teamcity_eval_cli_dir="${TEAMCITY_EVAL_CLI_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/teamcity-eval-cli.XXXXXX")}"
export TEAMCITY_EVAL_CLI_DIR="$teamcity_eval_cli_dir"

# Python's subprocess does not apply PATHEXT when its executable is named
# without an extension. npm creates `teamcity.cmd` on Windows, so make the
# executable name explicit for the Python helpers below.
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) export TEAMCITY_EVAL_CLI=teamcity.cmd ;;
  *) export TEAMCITY_EVAL_CLI=teamcity ;;
esac

if command -v npm >/dev/null 2>&1; then
  teamcity_eval_npm=npm
elif command -v npm.cmd >/dev/null 2>&1; then
  teamcity_eval_npm=npm.cmd
else
  case "$(uname -s):$(uname -m)" in
    Linux:aarch64|Linux:arm64)
      node_platform=linux
      node_arch=arm64
      node_sha256=013b59cfd2819703a6f4a14ab891fc46fc2a4e3f5bcd92de3fb4929b43e35b30
      ;;
    Linux:x86_64|Linux:amd64)
      node_platform=linux
      node_arch=x64
      node_sha256=b294a556e639d64338823920e5866c21c02741742d2e1529ee1a225c1ec9252a
      ;;
    Darwin:aarch64|Darwin:arm64)
      node_platform=darwin
      node_arch=arm64
      node_sha256=61130f394c1630d211dd50aecc4353d379480f36d3ac913cd85dbba1aed585c6
      ;;
    Darwin:x86_64|Darwin:amd64)
      node_platform=darwin
      node_arch=x64
      node_sha256=58e99022c2ff89395576cc7fd4d98cea24bb68081475d5f88b801ee8729fb026
      ;;
    MINGW*:aarch64|MINGW*:arm64|MSYS*:aarch64|MSYS*:arm64|CYGWIN*:aarch64|CYGWIN*:arm64)
      node_platform=win
      node_arch=arm64
      node_sha256=fec025a6da31757e3b6af84c5a1628e9d38442ca99a2161091d78f2fcfa35ef3
      ;;
    MINGW*:x86_64|MINGW*:amd64|MSYS*:x86_64|MSYS*:amd64|CYGWIN*:x86_64|CYGWIN*:amd64)
      node_platform=win
      node_arch=x64
      node_sha256=1177b4137ba5adaa56354ae40f1080c7450e8ae09cecb47da459d1c52ac99f97
      ;;
    *)
      echo "Cannot bootstrap Node on $(uname -s) $(uname -m); install Node/npm on the TeamCity agent." >&2
      return 1
      ;;
  esac

  node_version=v22.23.2
  node_extension=tar.gz
  [ "$node_platform" = win ] && node_extension=zip
  node_archive="$teamcity_eval_cli_dir/node.$node_extension"
  node_dir="$teamcity_eval_cli_dir/node-$node_version-$node_platform-$node_arch"
  node_url="https://nodejs.org/dist/$node_version/node-$node_version-$node_platform-$node_arch.$node_extension"

  if command -v curl >/dev/null 2>&1; then
    curl --fail --silent --show-error --location "$node_url" --output "$node_archive"
  elif command -v wget >/dev/null 2>&1; then
    wget --quiet --output-document="$node_archive" "$node_url"
  elif command -v python3 >/dev/null 2>&1; then
    NODE_URL="$node_url" NODE_ARCHIVE="$node_archive" \
      python3 -c 'import os, urllib.request; open(os.environ["NODE_ARCHIVE"], "wb").write(urllib.request.urlopen(os.environ["NODE_URL"], timeout=60).read())'
  elif command -v python >/dev/null 2>&1; then
    NODE_URL="$node_url" NODE_ARCHIVE="$node_archive" \
      python -c 'import os, urllib.request; open(os.environ["NODE_ARCHIVE"], "wb").write(urllib.request.urlopen(os.environ["NODE_URL"], timeout=60).read())'
  elif command -v py.exe >/dev/null 2>&1; then
    NODE_URL="$node_url" NODE_ARCHIVE="$node_archive" \
      py.exe -3 -c 'import os, urllib.request; open(os.environ["NODE_ARCHIVE"], "wb").write(urllib.request.urlopen(os.environ["NODE_URL"], timeout=60).read())'
  else
    echo "curl, wget, or Python is required to bootstrap Node on the TeamCity agent." >&2
    return 1
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    echo "$node_sha256  $node_archive" | sha256sum --check --status
  elif command -v shasum >/dev/null 2>&1; then
    [ "$(shasum -a 256 "$node_archive" | awk '{print $1}')" = "$node_sha256" ]
  elif command -v python3 >/dev/null 2>&1; then
    NODE_ARCHIVE="$node_archive" NODE_SHA256="$node_sha256" \
      python3 -c 'import hashlib, os; assert hashlib.sha256(open(os.environ["NODE_ARCHIVE"], "rb").read()).hexdigest() == os.environ["NODE_SHA256"]'
  elif command -v python >/dev/null 2>&1; then
    NODE_ARCHIVE="$node_archive" NODE_SHA256="$node_sha256" \
      python -c 'import hashlib, os; assert hashlib.sha256(open(os.environ["NODE_ARCHIVE"], "rb").read()).hexdigest() == os.environ["NODE_SHA256"]'
  elif command -v py.exe >/dev/null 2>&1; then
    NODE_ARCHIVE="$node_archive" NODE_SHA256="$node_sha256" \
      py.exe -3 -c 'import hashlib, os; assert hashlib.sha256(open(os.environ["NODE_ARCHIVE"], "rb").read()).hexdigest() == os.environ["NODE_SHA256"]'
  else
    echo "sha256sum, shasum, or Python is required to verify the Node download." >&2
    return 1
  fi
  if [ "$node_platform" = win ]; then
    if command -v python3 >/dev/null 2>&1; then
      NODE_ARCHIVE="$node_archive" NODE_DESTINATION="$teamcity_eval_cli_dir" \
        python3 -c 'import os, zipfile; zipfile.ZipFile(os.environ["NODE_ARCHIVE"]).extractall(os.environ["NODE_DESTINATION"])'
    elif command -v python >/dev/null 2>&1; then
      NODE_ARCHIVE="$node_archive" NODE_DESTINATION="$teamcity_eval_cli_dir" \
        python -c 'import os, zipfile; zipfile.ZipFile(os.environ["NODE_ARCHIVE"]).extractall(os.environ["NODE_DESTINATION"])'
    elif command -v py.exe >/dev/null 2>&1; then
      NODE_ARCHIVE="$node_archive" NODE_DESTINATION="$teamcity_eval_cli_dir" \
        py.exe -3 -c 'import os, zipfile; zipfile.ZipFile(os.environ["NODE_ARCHIVE"]).extractall(os.environ["NODE_DESTINATION"])'
    elif command -v unzip >/dev/null 2>&1; then
      unzip -q "$node_archive" -d "$teamcity_eval_cli_dir"
    elif command -v powershell.exe >/dev/null 2>&1; then
      NODE_ARCHIVE="$node_archive" NODE_DESTINATION="$teamcity_eval_cli_dir" \
        powershell.exe -NoProfile -NonInteractive -Command \
        'Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory($env:NODE_ARCHIVE, $env:NODE_DESTINATION)'
    else
      echo "Python, unzip, or PowerShell is required to extract Node on a Windows TeamCity agent." >&2
      return 1
    fi
    export PATH="$node_dir:$PATH"
    teamcity_eval_npm=npm.cmd
  else
    tar -xzf "$node_archive" -C "$teamcity_eval_cli_dir"
    export PATH="$node_dir/bin:$PATH"
    teamcity_eval_npm=npm
  fi
fi

"$teamcity_eval_npm" install --prefix "$teamcity_eval_cli_dir/teamcity-cli" --no-save --silent @jetbrains/teamcity-cli@1.3.0
export PATH="$teamcity_eval_cli_dir/teamcity-cli/node_modules/.bin:$PATH"
