#!/usr/bin/env python3
"""A tiny token-free stdio MCP server used only by the eval diagnostic.

It exposes a single no-input ``ping`` tool with a fixed result.  The process
uses JSON-RPC over stdio and must never write non-protocol data to stdout: the
Claude MCP client owns that stream.  This fixture has no TeamCity access and
does not inspect the checked-out repository.
"""

import json
import sys


SERVER_INFO = {"name": "eval-local-probe", "version": "1.0.0"}
PING_TOOL = {
    "name": "ping",
    "description": "Return a fixed local MCP health-check result.",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}


def send(message: dict) -> None:
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def response(identifier, result: dict) -> None:
    send({"jsonrpc": "2.0", "id": identifier, "result": result})


def error(identifier, code: int, message: str) -> None:
    send({
        "jsonrpc": "2.0",
        "id": identifier,
        "error": {"code": code, "message": message},
    })


def handle(message: dict) -> None:
    method = message.get("method")
    identifier = message.get("id")

    if method == "initialize":
        requested = (message.get("params") or {}).get("protocolVersion")
        response(identifier, {
            "protocolVersion": requested or "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        })
    elif method == "tools/list":
        response(identifier, {"tools": [PING_TOOL]})
    elif method == "tools/call":
        name = (message.get("params") or {}).get("name")
        if name == "ping":
            response(identifier, {
                "content": [{"type": "text", "text": "ok"}],
                "isError": False,
            })
        else:
            error(identifier, -32602, "unknown tool")
    elif identifier is not None:
        error(identifier, -32601, "method not found")


def main() -> int:
    for raw in sys.stdin:
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(message, dict):
            handle(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
