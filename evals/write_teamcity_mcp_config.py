#!/usr/bin/env python3
"""Write a per-build Claude MCP configuration with bearer authentication.

The bearer token is read only from a server-injected environment variable. It
must never be supplied on the command line, committed, printed, or copied into
an evaluation result. The caller creates the output with mode 0600 and removes
it after the agent exits.
"""

import argparse
import json
import os
import pathlib
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


def config(server: str, token: str) -> dict:
    return {
        "mcpServers": {
            "teamcity": {
                "type": "http",
                "url": endpoint(server),
                "headers": {
                    "Authorization": "Bearer " + bearer_token(token),
                },
            }
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument(
        "--token-env", default="EVAL_MCP_TOKEN",
        help="name of the server-injected environment variable holding the bearer token",
    )
    args = parser.parse_args()
    try:
        contents = json.dumps(
            config(args.server, os.environ.get(args.token_env, "")),
            separators=(",", ":"),
        ) + "\n"
    except ValueError as exc:
        parser.error(str(exc))
    args.output.write_text(contents)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
