#!/usr/bin/env python3
"""Deterministic TeamCity CLI responses for the queue-stall behavioral eval."""

import json
import os
import pathlib
import sys


args = [arg for arg in sys.argv[1:] if arg not in ("--no-color", "--no-input")]
server = os.environ.get("TEAMCITY_URL", "https://teamcity.queue-fixture.invalid")


def emit(payload):
    print(json.dumps(payload))


if not args or args == ["--version"] or args == ["-v"]:
    print("TeamCity CLI fixture v1")
elif args[:2] == ["auth", "status"]:
    emit({"authenticated": True, "server": server})
elif args[:2] == ["run", "view"]:
    emit({
        "id": 73142,
        "state": "queued",
        "status": "UNKNOWN",
        "statusText": "Queued: no compatible agents",
        "waitReason": "There are no compatible agents for QueueFixture_Build",
        "queuedDurationSeconds": 130,
        "buildTypeId": "QueueFixture_Build",
    })
elif args[:2] == ["queue", "list"]:
    emit({
        "count": 1,
        "build": [{
            "id": 73142,
            "state": "queued",
            "waitReason": "There are no compatible agents for QueueFixture_Build",
            "queuedDurationSeconds": 130,
        }],
    })
elif args[:2] == ["agent", "list"]:
    emit({
        "count": 2,
        "agent": [
            {"id": 101, "name": "linux-agent-a", "connected": True,
             "enabled": True, "authorized": True},
            {"id": 102, "name": "linux-agent-b", "connected": True,
             "enabled": True, "authorized": True},
        ],
    })
elif args[:2] == ["agent", "view"]:
    agent_id = args[2] if len(args) > 2 else "101"
    emit({
        "id": int(agent_id) if agent_id.isdigit() else 101,
        "connected": True,
        "enabled": True,
        "authorized": True,
        "parameters": {
            "teamcity.agent.jvm.os.name": "Linux",
            "env.JDK_17": "/opt/jdk-17",
            "env.JDK_21": "/opt/jdk-21",
        },
    })
elif args[:2] == ["agent", "jobs"] and "--incompatible" in args:
    emit({
        "agent": {"id": args[2] if len(args) > 2 else "101"},
        "incompatibleJobs": [{
            "id": "QueueFixture_Build",
            "reasons": [
                "Unresolved parameter: env.JDK_25",
                "Agent requirement cannot resolve %env.JDK_25%",
            ],
        }],
    })
elif args[:2] == ["job", "view"]:
    emit({
        "id": "QueueFixture_Build",
        "compatibleAgents": 0,
        "unresolvedParameters": ["env.JDK_25"],
        "requirements": ["env.JDK_25 exists"],
    })
elif args[:2] == ["pipeline", "list"]:
    emit({"pipelines": [{"id": "QueueFixture", "name": "Queue compatibility fixture"}]})
elif args[:2] == ["pipeline", "view"]:
    emit({"id": "QueueFixture", "name": "Queue compatibility fixture"})
elif args[:2] == ["pipeline", "pull"]:
    output = None
    for flag in ("--output", "-o"):
        if flag in args and args.index(flag) + 1 < len(args):
            output = args[args.index(flag) + 1]
    if output is None:
        output = ".teamcity.yml"
    pathlib.Path(output).write_text("""name: Queue compatibility fixture
jobs:
  build:
    name: QueueFixture_Build
    runs-on: self-hosted
    steps:
      - type: script
        script-content: '\"%env.JDK_25%/bin/java\" -version'
""")
    emit({"pipelineId": "QueueFixture", "output": output})
elif args[:2] == ["pipeline", "schema"]:
    emit({"valid": True, "runsOn": ["self-hosted"]})
else:
    print("TeamCity CLI fixture: unsupported command", file=sys.stderr)
    sys.exit(2)
