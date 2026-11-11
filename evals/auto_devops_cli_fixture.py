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


def slow_shared_responses():
    """One diamond: Build is shared; Tests and Package execute in parallel."""
    responses = synthetic_responses()
    details = (
        (100, "Example_Build", "Build", "090005", "090505", "./build.sh", 0),
        (102, "Example_Tests", "Tests", "090505", "091505", "./test.sh", 180),
        (103, "Example_Package", "Package", "090505", "090905", "./package.sh", 120),
        (101, "Example_Verify", "Verify", "091505", "091605", "./verify.sh", 0),
    )
    run_nodes, job_nodes = {}, {}
    for run_id, job_id, name, start, finish, script, wait_seconds in details:
        run = {"id": run_id, "buildTypeId": job_id, "branchName": "main", "state": "finished",
               "status": "SUCCESS", "number": str(run_id), "queuedDate": "20261110T090000+0000",
               "startDate": "20261110T" + start + "+0000", "finishDate": "20261110T" + finish + "+0000"}
        responses[shlex.join(("run", "view", str(run_id), "--json"))] = run
        responses[shlex.join(("run", "list", "--job", job_id, "--branch", "main", "--since", "14d", "--limit", "30", "--json"))] = [run]
        job = {"id": job_id, "name": name, "projectId": "Example"}
        responses[shlex.join(("job", "view", job_id, "--json"))] = dict(job, paused=False)
        run_nodes[run_id] = {"id": run_id, "name": name, "buildTypeId": job_id,
                             "state": "finished", "status": "SUCCESS", "dependencies": []}
        job_nodes[run_id] = job
        steps = [{"id": "work", "name": name, "type": "simpleRunner",
                  "properties": {"property": [{"name": "script.content", "value": script}]}}]
        if wait_seconds:
            steps.insert(0, {"id": "wait", "name": "Legacy padding", "type": "simpleRunner",
                             "properties": {"property": [{"name": "script.content", "value": "sleep " + str(wait_seconds)}]}})
        responses[shlex.join(("job", "step", "list", job_id, "--json"))] = {"count": len(steps), "step": steps}
        if wait_seconds:
            ended = "09:08:05" if run_id == 102 else "09:07:05"
            log = f"[09:05:05] Step Legacy padding started: sleep {wait_seconds}\n[{ended}] Step Legacy padding finished\n[{ended}] Step {name} started: {script}\n"
        else:
            log = f"[{start[:2]}:{start[2:4]}:{start[4:]}] Step {name} started: {script}\n"
        log += f"[{finish[:2]}:{finish[2:4]}:{finish[4:]}] Step {name} finished successfully\n"
        responses[shlex.join(("run", "log", str(run_id), "--tail", "2000", "--raw"))] = log
    for run_id, dependency_ids in ((102, [100]), (103, [100]), (101, [102,103])):
        run_nodes[run_id]["dependencies"] = [run_nodes[value] for value in dependency_ids]
        job_nodes[run_id]["dependencies"] = [job_nodes[value] for value in dependency_ids]
    for run_id, node in run_nodes.items():
        responses[shlex.join(("run", "tree", str(run_id), "--json"))] = node
        job_id = node["buildTypeId"]
        responses[shlex.join(("job", "tree", job_id, "--only", "dependencies", "--json"))] = job_nodes[run_id]
        shallow = dict(job_nodes[run_id])
        if "dependencies" in shallow:
            shallow["dependencies"] = [{key:value for key,value in child.items() if key != "dependencies"} for child in shallow["dependencies"]]
        responses[shlex.join(("job", "tree", job_id, "--only", "dependencies", "--depth", "1", "--json"))] = shallow
    return responses


def install_fixture(workspace, scenario="classic"):
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
    aggregation = binary.with_name("sum-run-seconds")
    aggregation.write_text(binary.read_text(encoding="utf-8"), encoding="utf-8")
    aggregation.chmod(0o700)
    fixture = workspace / "cli-responses.json"
    if scenario not in ("classic", "slow-shared"):
        raise ValueError("unknown synthetic scenario")
    responses = slow_shared_responses() if scenario == "slow-shared" else synthetic_responses()
    fixture.write_text(json.dumps(responses), encoding="utf-8")
    trace = workspace / "cli-calls.jsonl"
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("TEAMCITY_")}
    env.update(TEAMCITY_RO="1", TEAMCITY_URL="https://synthetic.invalid",
               AUTO_DEVOPS_FIXTURE=str(fixture), AUTO_DEVOPS_CALLS=str(trace),
               AUTO_DEVOPS_MATH_CALLS=str(workspace / "math-calls.jsonl"),
               PATH=str(binary.parent) + os.pathsep + os.environ.get("PATH", os.defpath))
    return binary, env, trace


def record_math(result, allowed):
    with Path(os.environ["AUTO_DEVOPS_MATH_CALLS"]).open("a", encoding="utf-8") as sink:
        sink.write(json.dumps({"program": Path(__file__).name, "argv": sys.argv[1:],
                               "result": result, "allowed": allowed}) + "\n")


def sum_run_seconds():
    """Sum one integer execution duration per run ID; inconsistent duplicates fail."""
    try:
        if len(sys.argv) < 2:
            raise ValueError("expected run durations")
        runs = {}
        for value in sys.argv[1:]:
            run_id, execution_seconds = map(int, value.split("="))
            if run_id <= 0 or execution_seconds < 0 or (run_id in runs and runs[run_id] != execution_seconds):
                raise ValueError("invalid or conflicting run duration")
            runs[run_id] = execution_seconds
        result = {"distinctRunIds": sorted(runs), "aggregateExecutionSeconds": sum(runs.values())}
    except ValueError:
        record_math(None, False)
        print("Expected consistent RUN_ID=EXECUTION_SECONDS values.", file=sys.stderr)
        return 2
    record_math(result, True)
    print(json.dumps(result))
    return 0


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
        record_math(None, False)
        print("Expected ordered CLI timestamps: YYYYMMDDTHHMMSS+HHMM", file=sys.stderr)
        return 2
    record_math(elapsed_seconds, True)
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
    program = Path(__file__).name
    sys.exit(calculate_delta() if program == "time-delta-seconds" else
             sum_run_seconds() if program == "sum-run-seconds" else main())
