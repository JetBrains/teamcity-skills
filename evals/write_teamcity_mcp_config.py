#!/usr/bin/env python3
"""Write a minimal Claude MCP configuration for TeamCity's OAuth endpoint.

The configuration deliberately holds no token, client secret, or OAuth cache.
Claude Code discovers OAuth from the HTTP MCP server and keeps any resulting
session outside this ephemeral per-build file.
"""

import argparse
import json
import pathlib
import urllib.parse


def endpoint(server: str) -> str:
    parsed = urllib.parse.urlparse(server)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("TeamCity server must be an HTTPS base URL without query or fragment")
    return server.rstrip("/") + "/app/mcp"


def config(server: str) -> dict:
    return {
        "mcpServers": {
            "teamcity": {
                "type": "http",
                "url": endpoint(server),
            }
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        contents = json.dumps(config(args.server), separators=(",", ":")) + "\n"
    except ValueError as exc:
        parser.error(str(exc))
    args.output.write_text(contents)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
