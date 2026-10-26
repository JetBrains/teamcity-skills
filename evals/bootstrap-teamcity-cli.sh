# Source this file from a TeamCity script step before invoking `teamcity`.
# Install the pinned native CLI in an isolated build-temporary directory.
# Install from the verified release archive, not the lagging npm package.

set -eu

teamcity_eval_cli_version=1.6.1
teamcity_eval_cli_dir="${TEAMCITY_EVAL_CLI_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/teamcity-eval-cli.XXXXXX")}"
export TEAMCITY_EVAL_CLI_DIR="$teamcity_eval_cli_dir"

case "$(uname -s):$(uname -m)" in
  Linux:aarch64|Linux:arm64)
    teamcity_eval_platform=linux
    teamcity_eval_arch=arm64
    teamcity_eval_sha256=e42e7934d8ac1ffec156c66b455a1614a941321473842edb537690188eec7c75
    ;;
  Linux:x86_64|Linux:amd64)
    teamcity_eval_platform=linux
    teamcity_eval_arch=x86_64
    teamcity_eval_sha256=de1ad9e351a0fa92771a65e43bb30663fa6663fc0e97074dddf4fd27b78ec8b6
    ;;
  Darwin:aarch64|Darwin:arm64)
    teamcity_eval_platform=darwin
    teamcity_eval_arch=arm64
    teamcity_eval_sha256=d6cf7a8ab5aaf73ec189f5482109c7954a4e60475f8a8d582680bdb40f4857dd
    ;;
  Darwin:x86_64|Darwin:amd64)
    teamcity_eval_platform=darwin
    teamcity_eval_arch=x86_64
    teamcity_eval_sha256=3a2c7a7cc76ac00dc2494c01e494afbeb8be8e70aede53b565eec9fb6e943317
    ;;
  MINGW*:aarch64|MINGW*:arm64|MSYS*:aarch64|MSYS*:arm64|CYGWIN*:aarch64|CYGWIN*:arm64)
    teamcity_eval_platform=windows
    teamcity_eval_arch=arm64
    teamcity_eval_sha256=68b017447b021be2f5c41253a26418a2ed990b6de5df12fc1ab7ad5357f0d928
    ;;
  MINGW*:x86_64|MINGW*:amd64|MSYS*:x86_64|MSYS*:amd64|CYGWIN*:x86_64|CYGWIN*:amd64)
    teamcity_eval_platform=windows
    teamcity_eval_arch=x86_64
    teamcity_eval_sha256=def6b16ac2bb5bcc1b083711b20e9c97778cfd2427cf488222f35d7548e6ab33
    ;;
  *)
    echo "No TeamCity CLI v$teamcity_eval_cli_version release for $(uname -s) $(uname -m)." >&2
    return 1
    ;;
esac

teamcity_eval_extension=tar.gz
[ "$teamcity_eval_platform" = windows ] && teamcity_eval_extension=zip
teamcity_eval_filename="teamcity_${teamcity_eval_cli_version}_${teamcity_eval_platform}_${teamcity_eval_arch}.${teamcity_eval_extension}"
teamcity_eval_archive="$teamcity_eval_cli_dir/$teamcity_eval_filename"
teamcity_eval_url="https://github.com/JetBrains/teamcity-cli/releases/download/v$teamcity_eval_cli_version/$teamcity_eval_filename"

if command -v curl >/dev/null 2>&1; then
  curl --fail --silent --show-error --location "$teamcity_eval_url" --output "$teamcity_eval_archive"
elif command -v wget >/dev/null 2>&1; then
  wget --quiet --output-document="$teamcity_eval_archive" "$teamcity_eval_url"
elif command -v python3 >/dev/null 2>&1; then
  TEAMCITY_EVAL_URL="$teamcity_eval_url" TEAMCITY_EVAL_ARCHIVE="$teamcity_eval_archive" \
    python3 -c 'import os, urllib.request; open(os.environ["TEAMCITY_EVAL_ARCHIVE"], "wb").write(urllib.request.urlopen(os.environ["TEAMCITY_EVAL_URL"], timeout=60).read())'
elif command -v python >/dev/null 2>&1; then
  TEAMCITY_EVAL_URL="$teamcity_eval_url" TEAMCITY_EVAL_ARCHIVE="$teamcity_eval_archive" \
    python -c 'import os, urllib.request; open(os.environ["TEAMCITY_EVAL_ARCHIVE"], "wb").write(urllib.request.urlopen(os.environ["TEAMCITY_EVAL_URL"], timeout=60).read())'
elif command -v py.exe >/dev/null 2>&1; then
  TEAMCITY_EVAL_URL="$teamcity_eval_url" TEAMCITY_EVAL_ARCHIVE="$teamcity_eval_archive" \
    py.exe -3 -c 'import os, urllib.request; open(os.environ["TEAMCITY_EVAL_ARCHIVE"], "wb").write(urllib.request.urlopen(os.environ["TEAMCITY_EVAL_URL"], timeout=60).read())'
else
  echo "curl, wget, or Python is required to download the TeamCity CLI." >&2
  return 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  [ "$(sha256sum "$teamcity_eval_archive" | awk '{print $1}')" = "$teamcity_eval_sha256" ]
elif command -v shasum >/dev/null 2>&1; then
  [ "$(shasum -a 256 "$teamcity_eval_archive" | awk '{print $1}')" = "$teamcity_eval_sha256" ]
elif command -v python3 >/dev/null 2>&1; then
  TEAMCITY_EVAL_ARCHIVE="$teamcity_eval_archive" TEAMCITY_EVAL_SHA256="$teamcity_eval_sha256" \
    python3 -c 'import hashlib, os; assert hashlib.sha256(open(os.environ["TEAMCITY_EVAL_ARCHIVE"], "rb").read()).hexdigest() == os.environ["TEAMCITY_EVAL_SHA256"]'
elif command -v python >/dev/null 2>&1; then
  TEAMCITY_EVAL_ARCHIVE="$teamcity_eval_archive" TEAMCITY_EVAL_SHA256="$teamcity_eval_sha256" \
    python -c 'import hashlib, os; assert hashlib.sha256(open(os.environ["TEAMCITY_EVAL_ARCHIVE"], "rb").read()).hexdigest() == os.environ["TEAMCITY_EVAL_SHA256"]'
elif command -v py.exe >/dev/null 2>&1; then
  TEAMCITY_EVAL_ARCHIVE="$teamcity_eval_archive" TEAMCITY_EVAL_SHA256="$teamcity_eval_sha256" \
    py.exe -3 -c 'import hashlib, os; assert hashlib.sha256(open(os.environ["TEAMCITY_EVAL_ARCHIVE"], "rb").read()).hexdigest() == os.environ["TEAMCITY_EVAL_SHA256"]'
else
  echo "sha256sum, shasum, or Python is required to verify the TeamCity CLI." >&2
  return 1
fi

if [ "$teamcity_eval_platform" = windows ]; then
  if command -v unzip >/dev/null 2>&1; then
    unzip -q "$teamcity_eval_archive" teamcity.exe -d "$teamcity_eval_cli_dir"
  elif command -v python3 >/dev/null 2>&1; then
    TEAMCITY_EVAL_ARCHIVE="$teamcity_eval_archive" TEAMCITY_EVAL_DEST="$teamcity_eval_cli_dir" \
      python3 -c 'import os, zipfile; zipfile.ZipFile(os.environ["TEAMCITY_EVAL_ARCHIVE"]).extract("teamcity.exe", os.environ["TEAMCITY_EVAL_DEST"])'
  elif command -v python >/dev/null 2>&1; then
    TEAMCITY_EVAL_ARCHIVE="$teamcity_eval_archive" TEAMCITY_EVAL_DEST="$teamcity_eval_cli_dir" \
      python -c 'import os, zipfile; zipfile.ZipFile(os.environ["TEAMCITY_EVAL_ARCHIVE"]).extract("teamcity.exe", os.environ["TEAMCITY_EVAL_DEST"])'
  elif command -v py.exe >/dev/null 2>&1; then
    TEAMCITY_EVAL_ARCHIVE="$teamcity_eval_archive" TEAMCITY_EVAL_DEST="$teamcity_eval_cli_dir" \
      py.exe -3 -c 'import os, zipfile; zipfile.ZipFile(os.environ["TEAMCITY_EVAL_ARCHIVE"]).extract("teamcity.exe", os.environ["TEAMCITY_EVAL_DEST"])'
  elif command -v powershell.exe >/dev/null 2>&1; then
    TEAMCITY_EVAL_ARCHIVE="$teamcity_eval_archive" TEAMCITY_EVAL_DEST="$teamcity_eval_cli_dir" \
      powershell.exe -NoProfile -NonInteractive -Command \
      'Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory($env:TEAMCITY_EVAL_ARCHIVE, $env:TEAMCITY_EVAL_DEST)'
  else
    echo "unzip, Python, or PowerShell is required to extract the TeamCity CLI on Windows." >&2
    return 1
  fi
  export TEAMCITY_EVAL_CLI=teamcity.exe
else
  tar -xzf "$teamcity_eval_archive" -C "$teamcity_eval_cli_dir" teamcity
  chmod 755 "$teamcity_eval_cli_dir/teamcity"
  export TEAMCITY_EVAL_CLI=teamcity
fi

export PATH="$teamcity_eval_cli_dir:$PATH"
teamcity_eval_actual_version="$("$TEAMCITY_EVAL_CLI" --version)"
if [ "$teamcity_eval_actual_version" != "teamcity version $teamcity_eval_cli_version" ]; then
  echo "Expected TeamCity CLI v$teamcity_eval_cli_version; got $teamcity_eval_actual_version." >&2
  return 1
fi
