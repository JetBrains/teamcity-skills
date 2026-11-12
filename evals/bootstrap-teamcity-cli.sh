# Source this file from a TeamCity script step before invoking `teamcity`.
# Install the pinned native CLI in an isolated build-temporary directory.
# Install from the verified release archive, not the lagging npm package.

set -eu

teamcity_eval_cli_version=1.6.3
teamcity_eval_cli_dir="${TEAMCITY_EVAL_CLI_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/teamcity-eval-cli.XXXXXX")}"
export TEAMCITY_EVAL_CLI_DIR="$teamcity_eval_cli_dir"

case "$(uname -s):$(uname -m)" in
  Linux:aarch64|Linux:arm64)
    teamcity_eval_platform=linux
    teamcity_eval_arch=arm64
    teamcity_eval_sha256=e5515c3b81b2eadde2cba59ed0d05c5e4f2f109bc4c554bb8394875117db8c26
    ;;
  Linux:x86_64|Linux:amd64)
    teamcity_eval_platform=linux
    teamcity_eval_arch=x86_64
    teamcity_eval_sha256=acd52b7a6904841225dcf61cd46cc209394562a6cbef69112498a74988dc282d
    ;;
  Darwin:aarch64|Darwin:arm64)
    teamcity_eval_platform=darwin
    teamcity_eval_arch=arm64
    teamcity_eval_sha256=2ee007c11f4202c599c9abf26f2c81520ae25fd456d24ec204e579e2a7c707dd
    ;;
  Darwin:x86_64|Darwin:amd64)
    teamcity_eval_platform=darwin
    teamcity_eval_arch=x86_64
    teamcity_eval_sha256=fd4726e377907ad76f5dff799cabfa6fcf1469418f91e682f32b1e02f8cc69d2
    ;;
  MINGW*:aarch64|MINGW*:arm64|MSYS*:aarch64|MSYS*:arm64|CYGWIN*:aarch64|CYGWIN*:arm64)
    teamcity_eval_platform=windows
    teamcity_eval_arch=arm64
    teamcity_eval_sha256=dbf0201fe496e47aa748f8e416a0ce0419c8a608a74eec5b75bda77f04c0340c
    ;;
  MINGW*:x86_64|MINGW*:amd64|MSYS*:x86_64|MSYS*:amd64|CYGWIN*:x86_64|CYGWIN*:amd64)
    teamcity_eval_platform=windows
    teamcity_eval_arch=x86_64
    teamcity_eval_sha256=a0426053a0ed7a62796a9843469a7ef6eb3dd8fa278e41fb8af4c936af18914b
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
