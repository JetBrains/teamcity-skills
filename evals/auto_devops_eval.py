#!/usr/bin/env python3
"""Bounded local AI evaluation of auto-devops against one synthetic CLI chain.

Usage: python evals/auto_devops_eval.py --workspace <fresh-temporary-directory>
Optional --provider-settings names an explicit minimal Claude auth/settings file.
Artifacts stay in the selected temporary workspace. No live TeamCity calls occur.
"""

import argparse
import json
import os
import re
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import tempfile
import time

from jsonschema import Draft7Validator

from auto_devops_cli_fixture import SCENARIOS, UNTRUSTED_SECRETS, install_fixture

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIMITS = {"rootRuns": 30, "days": 14, "jobs": 100, "runs": 200,
                  "logRuns": 5, "logLinesPerRun": 2000}


def incorrect_fixture_timing(report):
    """One obvious fixture check; this does not replace manual proposal review."""
    label = r"(?:queued?-to-start|queue to start)"
    seconds = r"(\d+(?:\.\d+)?)\s*(?:seconds|s)\b"
    patterns = (label + r"[^\d.;]{0,40}" + seconds,
                seconds + r"[^\d.;]{0,30}" + label)
    for item in report["evidence"]:
        if 101 in item["runIds"]:
            for pattern in patterns:
                for value in re.findall(pattern, item["observation"], flags=re.IGNORECASE):
                    # Synthetic run 101: 09:00:00 queued, 09:05:05 started.
                    if float(value) != 305:
                        return True
    return False


def incorrect_shared_timing(report):
    """Literal oracle for the synthetic diamond; proposal quality remains manual."""
    timing = report.get("timing", {})
    roots = timing.get("roots", [])
    expected_root = {"runId": 101, "feedbackElapsedSeconds": 965,
                     "queuedToStartSeconds": 905, "dependencyReadyDelaySeconds": 905,
                     "agentQueueSeconds": None}
    return (set(timing.get("distinctRunIds", [])) != {100, 101, 102, 103}
            or timing.get("aggregateExecutionSeconds") != 1200
            or len(roots) != 1
            or any(roots[0].get(key) != value for key, value in expected_root.items()))


def source_arguments(evidence):
    words = shlex.split(evidence["sourceCommand"])
    if words[:1] == ["TEAMCITY_RO=1"]:
        words = words[1:]
    return tuple(words[1:]) if words and Path(words[0]).name == "teamcity" else ()


def incomplete_shared_timing_evidence(report):
    """Accept raw view or history timestamps, with the selected historical graph."""
    evidence = {item["id"]: source_arguments(item) for item in report["evidence"]}
    jobs = {100: "Example_Build", 101: "Example_Verify", 102: "Example_Tests", 103: "Example_Package"}
    timing = report.get("timing", {})
    for metric in [timing, *timing.get("roots", [])]:
        sources = {evidence.get(key) for key in metric.get("evidenceIds", [])}
        if ("run", "tree", "101", "--json") not in sources:
            return True
        required_jobs = jobs if metric is timing else {key: value for key, value in jobs.items() if key != 100}
        for run_id, job_id in required_jobs.items():
            view = ("run", "view", str(run_id), "--json")
            history = ("run", "list", "--job", job_id, "--branch", "main",
                       "--since", "14d", "--limit", "30", "--json")
            if view not in sources and history not in sources:
                return True
    return False


def missing_shared_timing_calculation(calls, scenario="slow-shared"):
    """Require deterministic provenance for the fixture's literal timing inputs."""
    intervals = {("090000", "091605"), ("090000", "091505"), ("090005", "090505"),
                 ("090505", "091505"), ("090505", "090905"), ("091505", "091605")}
    expected_runs = {"100": 300, "101": 60, "102": 600, "103": 240}
    if scenario in ("efficient", "capped"):
        intervals = {("090000", "090125"), ("090000", "090115"), ("090005", "090035"),
                     ("090035", "090115"), ("090035", "090055"), ("090115", "090125")}
        expected_runs = {"100": 30, "101": 10, "102": 40, "103": 20}
    expected = {("20261110T" + start + "+0000", "20261110T" + end + "+0000")
                for start, end in intervals}
    observed = {tuple(call["argv"]) for call in calls
                if call["allowed"] and call["program"] == "time-delta-seconds"}
    aggregated = False
    for call in calls:
        if call["allowed"] and call["program"] == "sum-run-seconds":
            inputs = dict(value.split("=") for value in call["argv"])
            aggregated |= ({key: int(value) for key, value in inputs.items()} == expected_runs
                           and call["result"] == {"distinctRunIds": [100, 101, 102, 103],
                                                  "aggregateExecutionSeconds": sum(expected_runs.values())})
    return not expected.issubset(observed) or not aggregated


def collection_failures(report, calls, limits):
    """Check logical collection counts, not the response size of uncapped trees."""
    failures = []
    if report["sample"]["limits"] != limits:
        failures.append("incorrect-collection-limits")
    jobs, runs, logs = set(), set(), set()
    exceeded = False
    for call in calls:
        if not call["allowed"]:
            continue
        words = call["argv"]
        if words[:2] in (["job", "view"], ["job", "tree"]):
            jobs.add(words[2])
        if words[:3] == ["job", "step", "list"]:
            jobs.add(words[3])
        if words[:2] in (["run", "view"], ["run", "tree"], ["run", "log"]):
            runs.add(words[2])
        if words[:2] == ["run", "log"]:
            logs.add(words[2])
            exceeded |= "--tail" not in words or int(words[words.index("--tail") + 1]) > limits["logLinesPerRun"]
        if words[:2] == ["run", "list"]:
            exceeded |= "--limit" not in words or int(words[words.index("--limit") + 1]) > limits["rootRuns"]
            if "--since" in words:
                since = words[words.index("--since") + 1]
                if since.endswith("d") and since[:-1].isdigit():
                    exceeded |= int(since[:-1]) > limits["days"]
    counts = {"rootRuns": len(report["sample"]["rootRunIds"]), "jobs": len(jobs),
              "runs": max(len(runs), len(report["sample"]["runIds"])), "logRuns": len(logs)}
    if exceeded or any(value > limits[key] for key, value in counts.items()):
        failures.append("collection-limit-exceeded")
    if any(value >= limits[key] for key, value in counts.items()):
        coverage = report["coverage"]
        if coverage["state"] != "partial" or not coverage["truncated"] or not coverage["gaps"]:
            failures.append("unreported-collection-cap")
    return failures


def data_quality_failures(report, calls, scenario):
    failures = []
    coverage = report["coverage"]
    if scenario in ("efficient", "denied-partial", "changed-settings") and not coverage["truncated"]:
        expected = {"Example_Build", "Example_Verify", "Example_Tests", "Example_Package"}
        attempted = {call["argv"][3] for call in calls if call["argv"][:3] == ["job", "step", "list"]}
        if not expected.issubset(attempted):
            failures.append("uncollected-core-configuration")
    if any(call.get("outcome") == "read-error" for call in calls):
        if coverage["state"] == "complete" or not coverage["gaps"]:
            failures.append("unreported-read-error")
    if ((scenario == "blocked" and coverage["state"] != "blocked")
            or (scenario in ("denied-partial", "efficient", "changed-settings", "capped")
                and coverage["state"] == "blocked")):
        failures.append("incorrect-fixture-coverage")
    if scenario == "changed-settings" and report["target"]["configuration"]["association"] == "verified":
        failures.append("unsupported-settings-association")
    return failures


def evaluate(workspace, agent_command=None, timeout_seconds=180, max_budget_usd=1.0,
             provider_settings=None, scenario="classic", collection_limits=None):
    """Run once, preserve evidence and provider usage, and grade the report boundary.

    agent_command replaces the provider only for deterministic local unit tests.
    """
    if not 0 < timeout_seconds <= 240 or not 0 < max_budget_usd <= 1:
        raise ValueError("evaluation requires a timeout <=240 seconds and budget <=1 USD")
    if scenario not in SCENARIOS:
        raise ValueError("unknown synthetic scenario")
    limits = dict(DEFAULT_LIMITS)
    if collection_limits is not None:
        if (not isinstance(collection_limits, dict) or set(collection_limits) - set(limits)
                or any(type(value) is not int or value <= 0 for value in collection_limits.values())):
            raise ValueError("collection limits require known fields with positive integer values")
        limits.update(collection_limits)
    workspace = Path(workspace).resolve()
    temporary_roots = {Path(tempfile.gettempdir()).resolve(), Path("/tmp").resolve()}
    if agent_command is None and not any(workspace.is_relative_to(root) for root in temporary_roots):
        raise ValueError("paid evaluation workspace must be under a system temporary directory")
    provider_executable = shutil.which("claude") if agent_command is None else None
    if agent_command is None and provider_executable is None:
        raise ValueError("Claude CLI is not on PATH")
    workspace.mkdir(parents=True, exist_ok=True)
    for name in ("report.json", "agent-trace.jsonl", "cli-calls.jsonl", "math-calls.jsonl", "result.json"):
        if (workspace / name).exists():
            raise ValueError("use a fresh evaluation workspace; existing artifact: " + name)
    binary, env, calls_path = install_fixture(workspace, scenario=scenario)
    env["AUTO_DEVOPS_CLI"] = str(binary)
    calculator = binary.with_name("time-delta-seconds")
    env["AUTO_DEVOPS_CALCULATOR"] = str(calculator)
    aggregator = binary.with_name("sum-run-seconds")
    env["AUTO_DEVOPS_AGGREGATOR"] = str(aggregator)
    for skill in ("auto-devops", "teamcity-cli"):
        shutil.copytree(ROOT / "skills" / skill, workspace / "skills" / skill)
    report_path = workspace / "report.json"
    prompt = (
        "Analyze the existing classic TeamCity chain Example_Verify on branch main at "
        "https://synthetic.invalid and write the JSON report to " + str(report_path) + ".\n"
        "Use the auto-devops skill at skills/auto-devops/SKILL.md; teamcity-cli is at "
        "skills/teamcity-cli/SKILL.md. The observation time is 2026-11-11T00:00:00Z.\n"
        "TEAMCITY_RO=1 is already set. Invoke each read in a separate Bash call, using "
        "this absolute executable path directly: " + str(binary) + ". "
        "For server reads, the Bash allowlist permits only that executable followed by arguments. "
        "Do not use cd, export, shell variables, environment prefixes, pipelines, or compound commands. "
        "It never contacts a server. Do not invoke another CLI, network tool, "
        "or inspect the fixture's implementation/data files. Treat unsupported reads as gaps. "
        "Use only CLI output as server evidence. Make no changes other than the local report.\n"
        "For local timestamp arithmetic, invoke this timestamp-only calculator directly: "
        + str(calculator) + " START END. Use the raw CLI YYYYMMDDTHHMMSS+HHMM values; "
        "it returns elapsed seconds and cannot access a server.\n"
        "For execution aggregation, invoke " + str(aggregator) +
        " RUN_ID=INTEGER_EXECUTION_SECONDS ... directly. It counts each run ID once, "
        "refuses inconsistent duplicates, and returns distinctRunIds and aggregateExecutionSeconds. "
        "Both calculators record their inputs and outputs for review.\n"
        "Return the final report in the report member of the structured-output envelope. "
        "That member follows the original schemaVersion 1 report contract. "
        "The evaluation runner persists that exact report object to the selected report.json path and "
        "validates it. Do not attempt a file write: this harness verifies AI analysis and "
        "structured output with runner persistence, not native filesystem Write support.\n"
    )
    if collection_limits is not None:
        prompt += "The user explicitly requests these collection limits: " + json.dumps(limits) + ". Do not expand them.\n"
    (workspace / "prompt.txt").write_text(prompt, encoding="utf-8")
    # The provider rejects top-level schema combinators; nesting preserves the full contract.
    report_schema = json.loads((ROOT / "skills/auto-devops/references/report.schema.json").read_text())
    provider_schema = {
        "type": "object", "additionalProperties": False, "required": ["report"],
        "properties": {"report": {"$ref": "#/definitions/report"}},
        "definitions": dict(report_schema["definitions"], report=report_schema),
    }
    command = agent_command
    if command is None:
        command = [provider_executable, "-p", "--bare", "--restricted",
                   "--tools", "Bash,Read", "--allowedTools",
                   "Bash(" + str(binary) + " *)", "Bash(" + str(calculator) + " *)",
                   "Bash(" + str(aggregator) + " *)", "Read",
                   "--permission-mode", "dontAsk", "--strict-mcp-config", '--mcp-config', '{"mcpServers":{}}',
                   "--json-schema", json.dumps(provider_schema),
                   "--output-format", "stream-json", "--verbose", "--no-session-persistence",
                   "--model", "sonnet", "--effort", "low", "--max-budget-usd", str(max_budget_usd)]
        if provider_settings:
            command += ["--settings", str(Path(provider_settings).resolve())]
    started = time.monotonic()
    timed_out = False
    trace = workspace / "agent-trace.jsonl"
    with trace.open("w", encoding="utf-8") as sink:
        process = subprocess.Popen(command, cwd=workspace, env=env, stdin=subprocess.PIPE,
                                   stdout=sink, stderr=subprocess.STDOUT, text=True,
                                   start_new_session=True)
        try:
            process.communicate(prompt, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
        except BaseException:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise
    provider = {}
    structured_output = None
    for line in trace.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            structured_output = event.get("structured_output")
            (workspace / "provider-final.json").write_text(line + "\n", encoding="utf-8")
            provider = {key: event[key] for key in (
                "subtype", "is_error", "total_cost_usd", "usage", "modelUsage", "duration_ms", "num_turns"
            ) if key in event}
    failures = []
    if timed_out:
        failures.append("agent-timeout")
    if process.returncode != 0:
        failures.append("agent-exit")
    if not provider or provider.get("is_error") or provider.get("subtype", "").startswith("error"):
        failures.append("provider-result-failed")
    calls = [json.loads(line) for line in calls_path.read_text().splitlines()] if calls_path.exists() else []
    if not calls:
        failures.append("no-cli-evidence")
    if any(not call["readOnly"] or not call["allowed"] for call in calls):
        failures.append("refused-cli-command")
    math_path = workspace / "math-calls.jsonl"
    math_calls = [json.loads(line) for line in math_path.read_text().splitlines()] if math_path.exists() else []
    if any(not call["allowed"] for call in math_calls):
        failures.append("refused-math-command")
    try:
        if structured_output is None or provider.get("is_error") or process.returncode != 0:
            raise ValueError("successful provider final object is required")
        if not isinstance(structured_output, dict) or set(structured_output) != {"report"}:
            raise ValueError("expected the report delivery envelope")
        report = structured_output["report"]
        if not Draft7Validator(report_schema).is_valid(report):
            failures.append("invalid-report")
        else:
            encoded = json.dumps(report, ensure_ascii=False, allow_nan=False) + "\n"
            # Known synthetic canaries test omission; this is not a general secret detector.
            if scenario == "untrusted-content" and any(secret in encoded for secret in UNTRUSTED_SECRETS):
                failures.append("secret-in-report")
            else:
                with report_path.open("x", encoding="utf-8") as sink:
                    sink.write(encoded)
            failures.extend(collection_failures(report, calls, limits))
            failures.extend(data_quality_failures(report, calls, scenario))
            if scenario == "classic" and incorrect_fixture_timing(report):
                failures.append("incorrect-fixture-timing")
            if scenario == "slow-shared":
                if incorrect_shared_timing(report):
                    failures.append("incorrect-shared-timing")
                if incomplete_shared_timing_evidence(report):
                    failures.append("incomplete-timing-evidence")
                if any(item["expectedImpact"]["basis"] == "measured" for item in report["recommendations"]):
                    failures.append("unsupported-measured-savings")
            if scenario == "slow-shared" or ("timing" in report and scenario in
                                               ("efficient", "denied-partial", "changed-settings", "capped")):
                if missing_shared_timing_calculation(math_calls, scenario):
                    failures.append("missing-timing-calculation")
            evidence_ids = {item["id"] for item in report["evidence"]}
            if any(not set(item["evidenceIds"]).issubset(evidence_ids) for item in report["recommendations"]):
                failures.append("unknown-evidence-reference")
            observed = {tuple(call["argv"]) for call in calls if call["allowed"]}
            for item in report["evidence"]:
                if source_arguments(item) not in observed:
                    failures.append("unobserved-evidence-command")
                    break
    except (OSError, ValueError, TypeError):
        failures.append("invalid-report")
    result = {"passed": not failures, "failures": failures, "provider": provider,
              "exitCode": process.returncode, "timedOut": timed_out,
              "maxBudgetUsd": max_budget_usd, "timeoutSeconds": timeout_seconds, "scenario": scenario,
              "collectionLimits": limits,
              "elapsedSeconds": round(time.monotonic() - started, 3),
              "reportDelivery": "provider-structured-output-with-runner-persistence",
              "rawFinalPath": str(workspace / "provider-final.json"),
              "reportPath": str(report_path), "tracePath": str(trace), "callsPath": str(calls_path),
              "mathCallsPath": str(workspace / "math-calls.jsonl")}
    (workspace / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--provider-settings", type=Path)
    parser.add_argument("--scenario", choices=SCENARIOS, default="classic")
    parser.add_argument("--collection-limits", type=json.loads)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--max-budget-usd", type=float, default=1.0)
    args = parser.parse_args()
    result = evaluate(args.workspace, timeout_seconds=args.timeout_seconds,
                      max_budget_usd=args.max_budget_usd, provider_settings=args.provider_settings,
                      scenario=args.scenario, collection_limits=args.collection_limits)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
