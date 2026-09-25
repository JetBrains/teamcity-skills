#!/usr/bin/env python3
"""Write a per-build Claude MCP configuration with bearer authentication.

The bearer token is read only from a server-injected environment variable. It
must never be supplied on the command line, committed, printed, or copied into
an evaluation result. The caller creates the output with mode 0600 and removes
it after the agent exits.  The explicit diagnostic mode may add a token-free
local stdio probe; it has no TeamCity access.
"""

import argparse
import json
import os
import pathlib
import sys
import urllib.parse


def endpoint(server: str) -> str:
    parsed = urllib.parse.urlparse(server)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("TeamCity server must be an HTTPS base URL without query or fragment")
    return server.rstrip("/") + "/app/mcp"


def bearer_token(value: str) -> str:
    """Validate without ever including a secret value in an error message."""
    token = value.strip()
    if not token:
        raise ValueError("EVAL_MCP_TOKEN must be supplied as a secure build parameter")
    if any(character.isspace() for character in token):
        raise ValueError("EVAL_MCP_TOKEN must not contain whitespace")
    return token


def local_probe() -> dict:
    """Return the token-free local MCP diagnostic server declaration."""
    fixture = pathlib.Path(__file__).with_name("fixtures") / "mcp_probe.py"
    return {
        "type": "stdio",
        "command": sys.executable,
        "args": [str(fixture.resolve())],
    }


def config(server: str, token: str, with_local_probe: bool = False) -> dict:
    servers = {
        "teamcity": {
            "type": "http",
            "url": endpoint(server),
            "headers": {
                "Authorization": "Bearer " + bearer_token(token),
            },
        }
    }
    if with_local_probe:
        servers["probe"] = local_probe()
    return {"mcpServers": servers}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument(
        "--token-env", default="EVAL_MCP_TOKEN",
        help="name of the server-injected environment variable holding the bearer token",
    )
    parser.add_argument(
        "--with-local-probe", action="store_true",
        help="add the token-free stdio MCP diagnostic server",
    )
    args = parser.parse_args()
    try:
        contents = json.dumps(
            config(
                args.server, os.environ.get(args.token_env, ""),
                with_local_probe=args.with_local_probe,
            ),
            separators=(",", ":"),
        ) + "\n"
    except ValueError as exc:
        parser.error(str(exc))
    args.output.write_text(contents)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
