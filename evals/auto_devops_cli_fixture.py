#!/usr/bin/env python3
"""One synthetic classic chain. This executable has no live CLI/network fallback."""

from datetime import datetime
import json
import os
from pathlib import Path
import shlex
import sys


def synthetic_responses():
    responses = {("--version",): "teamcity version 1.6.3"}
    jobs = {"Example_Verify": "Verify", "Example_Build": "Build"}
    builds = {}
    for run_id, job_id, start, finish in (
        (100, "Example_Build", "090005", "090505"),
        (101, "Example_Verify", "090505", "090805"),
    ):
        builds[run_id] = {
            "id": run_id, "buildTypeId": job_id, "branchName": "main",
            "state": "finished", "status": "SUCCESS", "number": str(run_id),
            "queuedDate": "20261110T090000+0000",
            "startDate": "20261110T" + start + "+0000",
            "finishDate": "20261110T" + finish + "+0000",
        }
        responses[("run", "view", str(run_id), "--json")] = builds[run_id]
    child = {"id": 100, "name": "Build", "buildTypeId": "Example_Build",
             "state": "finished", "status": "SUCCESS", "dependencies": []}
    responses[("run", "tree", "101", "--json")] = {
        "id": 101, "name": "Verify", "buildTypeId": "Example_Verify",
        "state": "finished", "status": "SUCCESS", "dependencies": [child],
    }
    responses[("run", "tree", "100", "--json")] = child
    responses[("run", "list", "--job", "Example_Verify", "--branch", "main",
               "--since", "14d", "--limit", "30", "--json")] = [builds[101]]
    for job_id, name in jobs.items():
        responses[("job", "view", job_id, "--json")] = {
            "id": job_id, "name": name, "projectId": "Example", "paused": False}
        tree = {"id": job_id, "name": name, "projectId": "Example"}
        if job_id == "Example_Verify":
            tree["dependencies"] = [{"id": "Example_Build", "name": "Build", "projectId": "Example"}]
        responses[("job", "tree", job_id, "--only", "dependencies", "--json")] = tree
        responses[("job", "tree", job_id, "--only", "dependencies", "--depth", "1", "--json")] = tree
        steps = [{"id": "test", "name": "Test", "type": "simpleRunner",
                  "properties": {"property": [{"name": "script.content", "value": "./test.sh"}]}}]
        if job_id == "Example_Verify":
            steps.insert(0, {"id": "wait", "name": "Wait", "type": "simpleRunner",
                             "properties": {"property": [{"name": "script.content", "value": "sleep 120"}]}})
        responses[("job", "step", "list", job_id, "--json")] = {"count": len(steps), "step": steps}
    return {shlex.join(key): value for key, value in responses.items()}


def install_fixture(workspace):
    """Install a standalone CLI and return its isolated environment and call trace."""
    workspace = workspace.resolve()
    binary = workspace / "bin" / "teamcity"
    binary.parent.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).read_text(encoding="utf-8").split("\n", 1)[1]
    binary.write_text("#!" + sys.executable + "\n" + source, encoding="utf-8")
    binary.chmod(0o700)
    calculator = binary.with_name("time-delta-seconds")
    calculator.write_text(binary.read_text(encoding="utf-8"), encoding="utf-8")
    calculator.chmod(0o700)
    fixture = workspace / "cli-responses.json"
    fixture.write_text(json.dumps(synthetic_responses()), encoding="utf-8")
    trace = workspace / "cli-calls.jsonl"
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("TEAMCITY_")}
    env.update(TEAMCITY_RO="1", TEAMCITY_URL="https://synthetic.invalid",
               AUTO_DEVOPS_FIXTURE=str(fixture), AUTO_DEVOPS_CALLS=str(trace),
               PATH=str(binary.parent) + os.pathsep + os.environ.get("PATH", os.defpath))
    return binary, env, trace


def calculate_delta():
    """Subtract two CLI timestamps only; no code, files, or network access."""
    try:
        if len(sys.argv) != 3:
            raise ValueError("expected two timestamps")
        start, end = [datetime.strptime(value, "%Y%m%dT%H%M%S%z") for value in sys.argv[1:]]
        elapsed_seconds = (end - start).total_seconds()
        if elapsed_seconds < 0:
            raise ValueError("timestamps are reversed")
    except ValueError:
        print("Expected ordered CLI timestamps: YYYYMMDDTHHMMSS+HHMM", file=sys.stderr)
        return 2
    print(f"{elapsed_seconds:g}")
    return 0


def main():
    arguments = sys.argv[1:]
    responses = json.loads(Path(os.environ["AUTO_DEVOPS_FIXTURE"]).read_text())
    read_only = os.environ.get("TEAMCITY_RO") == "1"
    key = shlex.join(arguments)
    allowed = read_only and key in responses
    with Path(os.environ["AUTO_DEVOPS_CALLS"]).open("a", encoding="utf-8") as sink:
        sink.write(json.dumps({"argv": arguments, "readOnly": read_only, "allowed": allowed}) + "\n")
    if not allowed:
        print("Synthetic fixture refused command; TEAMCITY_RO=1 and an exact supported read are required.", file=sys.stderr)
        return 2
    value = responses[key]
    print(value if isinstance(value, str) else json.dumps(value))
    return 0


if __name__ == "__main__":
    sys.exit(calculate_delta() if Path(__file__).name == "time-delta-seconds" else main())
