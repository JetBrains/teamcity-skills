#!/usr/bin/env python3
"""Collect a safe, normalized report of TeamCity evaluation runs.

The report deliberately stores verdicts and fixed failure categories, never
agent trajectories, prompts, or raw build logs.  It is intended to be run by a
TeamCity report job or locally through an already authenticated ``teamcity``
CLI session:

    python3 evals/collect_teamcity_eval_runs.py \
      --server https://<teamcity-server> \
      --pipeline <configuration-evaluation-pipeline-id> \
      --pipeline <first-green-build-pipeline-id> \
      --output /tmp/teamcity-eval-runs.json

Use ``evals/render_teamcity_eval_report.py`` to turn the resulting JSON into
an HTML report.  The two scripts do not modify TeamCity and do not require a
TeamCity token argument: the CLI's configured authentication is used.
"""

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import tempfile


HERE = pathlib.Path(__file__).resolve().parent
EVAL_JOB_NAMES = {"Run configuration eval", "Run eval case"}
ARMS = ("skill", "baseline")
USAGE_FIELDS = (
    "inputTokens", "outputTokens", "cacheReadTokens",
    "cacheWriteTokens", "totalCostUsd",
)


def teamcity_cli():
    """Return the executable installed by bootstrap-teamcity-cli.sh."""
    return os.environ.get("TEAMCITY_EVAL_CLI", "teamcity")


def cli(server, *args):
    """Run the TeamCity CLI without ever relaying its output into the report."""
    environment = os.environ.copy()
    environment["TEAMCITY_URL"] = server
    completed = subprocess.run(
        [teamcity_cli(), *args],
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed


def cli_json(warnings, server, *args):
    completed = cli(server, *args)
    if completed.returncode:
        warnings.append("TeamCity CLI command failed: " + " ".join(args[:3]))
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        warnings.append("TeamCity CLI returned non-JSON output: " + " ".join(args[:3]))
        return None


def iso_time(value):
    """Convert TeamCity's compact timestamp to ISO 8601 when present."""
    if not value:
        return None
    try:
        return dt.datetime.strptime(value, "%Y%m%dT%H%M%S%z").isoformat()
    except ValueError:
        return value


def duration_seconds(run):
    if not run.get("startDate") or not run.get("finishDate"):
        return None
    try:
        started = dt.datetime.strptime(run["startDate"], "%Y%m%dT%H%M%S%z")
        finished = dt.datetime.strptime(run["finishDate"], "%Y%m%dT%H%M%S%z")
    except ValueError:
        return None
    return int((finished - started).total_seconds())


def vcs_revision(run):
    changes = (run.get("lastChanges") or {}).get("change") or []
    return changes[0].get("version") if changes else None


def safe_agent_usage(value):
    if not isinstance(value, dict):
        return {}
    return {
        name: value[name]
        for name in USAGE_FIELDS
        if isinstance(value.get(name), (int, float))
        and not isinstance(value.get(name), bool)
        and value[name] >= 0
    }


def flatten_dependencies(tree):
    """Return each dependency once, excluding the pipeline head."""
    found = []
    seen = set()

    def walk(node):
        for child in node.get("dependencies") or []:
            identifier = child.get("id")
            if identifier in seen:
                continue
            seen.add(identifier)
            found.append(child)
            walk(child)

    walk(tree)
    return found


def inventory():
    """Read case intent from versioned contracts, not from a run log."""
    cases = []
    for path in sorted(HERE.glob("*/cases/*.json")):
        case = json.loads(path.read_text())
        kind = case["kind"]
        expected = case.get("expected", {})
        if kind == "first-green-build":
            scope = "Creates CI, validates it, then proves a real build, tests, and artifacts."
        elif kind == "pipeline-configuration":
            scope = "Grades the generated pipeline only; no project build is queued."
        elif kind == "queue-stall-diagnosis":
            scope = "Simulates a run queued for over two minutes and grades compatibility diagnosis without consuming a build agent."
        else:
            scope = "Checks TeamCity authentication, authorization, and required operations."

        assertions = []
        labels = {
            "configurationValidated": "pipeline stored/read back",
            "testsExecutedAndReported": "test reporting",
            "artifactsPublished": "artifact publication",
            "sourceMutations": "source fidelity",
            "minimumJobs": "job topology",
            "jobCount": "exact job count",
            "requiredStepTypes": "runner selection",
            "requiredArtifactRules": "artifact rules",
            "requiredAgentRequirements": "target agents",
            "requiredJobs": "per-job topology and outputs",
            "toolUse": "CLI/tool choice",
            "diagnosticAgentInventory": "agent inventory diagnostic",
            "diagnosticJobIncompatibility": "job incompatibility diagnostic",
            "diagnosticStoredParameters": "stored parameter diagnostic",
            "maximumStatusChecks": "bounded status checks",
            "maximumWaitCalls": "bounded waiting",
            "requiredDiagnostics": "agent compatibility diagnosis",
            "forbiddenActions": "no blind retry",
            "requiredConclusions": "classified blocker",
            "authenticated": "authentication",
            "authorizationErrorsAbsent": "authorization",
            "allRequiredOperationsAvailable": "tool capabilities",
            "temporaryObjectsRemoved": "temporary-object lifecycle",
            "toolchain": "toolchain",
            "firstBuild": "first build",
            "targets": "target coverage",
        }
        for key in expected:
            # This is an internal safety guard, not a capability shown in the
            # public Case x arm matrix.
            if key in labels and key != "sourceMutations":
                assertions.append(labels[key])
        cases.append(
            {
                "id": case["id"],
                "kind": kind,
                "gate": case.get("status", "active"),
                "executionModel": (
                    "paired-arms"
                    if kind in (
                        "first-green-build", "pipeline-configuration", "queue-stall-diagnosis"
                    )
                    else "preflight"
                ),
                "scope": scope,
                "assertions": assertions,
                "targets": [target.get("name", target["id"]) for target in expected.get("targets", [])],
            }
        )
    return cases


def download_result(warnings, server, run_id):
    """Read only eval-result.json; agent traces must not enter the report."""
    artifact_list = cli(server, "run", "artifacts", str(run_id), "--path", "publish", "--json")
    if artifact_list.returncode:
        return None
    try:
        published = json.loads(artifact_list.stdout)
    except json.JSONDecodeError:
        return None
    if not any(
        item.get("name") == "eval-result.json" for item in published.get("file") or []
    ):
        return None
    with tempfile.TemporaryDirectory(prefix="teamcity-eval-report-") as directory:
        destination = pathlib.Path(directory)
        completed = cli(
            server,
            "run",
            "download",
            str(run_id),
            "--path",
            "publish",
            "--artifact",
            "eval-result.json",
            "--output",
            str(destination),
        )
        if completed.returncode:
            return None
        result_paths = list(destination.rglob("eval-result.json"))
        if not result_paths:
            return None
        try:
            result = json.loads(result_paths[0].read_text())
        except json.JSONDecodeError:
            warnings.append(f"Run {run_id} published malformed eval-result.json")
            return None
        # Current runners publish only a minimal verdict. Support legacy
        # results defensively without copying their raw diagnostics onward.
        checks = result.get("checks") or {}
        trace_tail = "\n".join(
            line for line in result.get("agentTraceTail") or [] if isinstance(line, str)
        ).lower()
        if (
            result.get("errorCategory") == "agent-timeout"
            or result.get("agentTimedOut") is True
        ):
            error_category = "agent-timeout"
        elif "requires approval" in trace_tail or "permission_denied" in trace_tail:
            error_category = "agent-permission-failure"
        else:
            error_category = None
        return {
            "caseId": result.get("caseId"),
            "caseStatus": result.get("caseStatus"),
            "status": result.get("status"),
            "gradeStatus": result.get("gradeStatus"),
            "arm": result.get("arm"),
            "agentExitCode": result.get("agentExitCode"),
            "agentTimedOut": result.get("agentTimedOut"),
            "agentUsage": safe_agent_usage(result.get("agentUsage")),
            "errorCategory": error_category,
            "checks": {
                name: {"passed": check.get("passed")}
                for name, check in checks.items()
                if isinstance(check, dict)
            },
        }


def log_category(server, run_id):
    """Classify known infrastructure errors without persisting raw logs."""
    completed = cli(server, "run", "log", str(run_id), "--tail", "100", "--raw")
    text = (completed.stdout + "\n" + completed.stderr).lower()
    patterns = (
        (
            ("no matching manifest for windows", "docker: no matching manifest"),
            ("runner-runtime-failure", "Linux container image was scheduled on a Windows container host"),
        ),
        (
            ("claude code was not provided by the jcp central ai agent feature",),
            ("agent-runtime-failure", "JCP Central did not inject Claude Code into this job"),
        ),
        (
            ("authentication failed", "invalid credentials", "write access to repository not granted"),
            ("vcs-auth-failure", "TeamCity could not authenticate to the VCS repository"),
        ),
        (
            ("could not obtain token", "http 401", "http 403"),
            ("teamcity-auth-failure", "the runner could not obtain TeamCity access"),
        ),
        (
            (
                "could not fetch",
                "failed to fetch",
                "remote: internal server error",
                "command '('git', 'fetch'",
            ),
            ("external-vcs-failure", "external repository checkout failed before the agent ran"),
        ),
        (
            ("python 3 is required", "python3: command not found"),
            ("runner-runtime-failure", "the evaluation runner could not start Python"),
        ),
    )
    for needles, verdict in patterns:
        if any(needle in text for needle in needles):
            return verdict
    return ("failed-without-result", "job failed before it published an evaluation result")


def classify(server, run, result):
    """Separate a grade of the skill from failures in the evaluator itself."""
    state = (run.get("state") or "unknown").lower()
    status = (run.get("status") or "unknown").lower()
    status_text = (run.get("statusText") or "").lower()
    if "canceled" in status_text or "cancelled" in status_text:
        return "canceled", "stopped before evaluation started"
    if state == "queued":
        return "queued", "waiting for a compatible agent"
    if state == "running":
        return "running", "agent evaluation is still running"

    if result:
        if result.get("status") == "passed":
            return "passed", "all recorded assertions passed"
        if result.get("status") == "failed":
            failed_checks = [
                name for name, check in (result.get("checks") or {}).items()
                if check.get("passed") is False
            ]
            detail = "failed assertions: " + ", ".join(failed_checks) if failed_checks else "runner graded a failed result"
            return "skill-output-failed", detail
        if result.get("errorCategory") == "agent-permission-failure":
            return "agent-permission-failure", "Claude's non-interactive tool policy denied required commands"
        if (
            result.get("errorCategory") == "agent-timeout"
            or result.get("agentTimedOut") is True
        ):
            grade = result.get("gradeStatus")
            detail = "Claude exceeded the configured agent timeout"
            failed_checks = [
                name for name, check in (result.get("checks") or {}).items()
                if check.get("passed") is False
            ]
            if failed_checks:
                detail += "; failed assertions: " + ", ".join(failed_checks)
            elif grade:
                detail += f"; recorded checks were {grade}"
            return "agent-timeout", detail
        return "runner-runtime-failure", "runner published an error result"

    if status == "success":
        return "false-green/no-result", "job succeeded but did not publish eval-result.json"
    return log_category(server, run["id"])


def normalize_run(server, warnings, node):
    detailed = cli_json(warnings, server, "run", "view", str(node["id"]), "--json") or node
    result = None
    if (detailed.get("state") or "").lower() == "finished":
        result = download_result(warnings, server, detailed["id"])
    category, detail = classify(server, detailed, result)
    triggered = detailed.get("triggered") or {}
    return {
        "id": detailed["id"],
        "number": detailed.get("number"),
        "name": detailed.get("buildType", {}).get("name") or node.get("name"),
        "job": detailed.get("buildTypeId") or node.get("buildTypeId"),
        "state": detailed.get("state"),
        "status": detailed.get("status"),
        "statusText": detailed.get("statusText"),
        "url": detailed.get("webUrl"),
        "agent": (detailed.get("agent") or {}).get("name"),
        "trigger": triggered.get("type"),
        "queuedAt": iso_time(detailed.get("queuedDate")),
        "startedAt": iso_time(detailed.get("startDate")),
        "finishedAt": iso_time(detailed.get("finishDate")),
        "durationSeconds": duration_seconds(detailed),
        "revision": vcs_revision(detailed),
        "classification": category,
        "classificationDetail": detail,
        "result": result,
    }


def latest_arm_observations(all_jobs, window_size=5, target_min_samples=3):
    """Latest arm plus a bounded pass-rate window on the same harness SHA."""
    observed = {}
    history = {}
    for job in sorted(all_jobs, key=lambda item: item["id"], reverse=True):
        result = job.get("result") or {}
        case_id = result.get("caseId")
        arm = result.get("arm")
        key = (case_id, arm)
        if not case_id or arm not in ARMS:
            continue
        history.setdefault(key, []).append(job)
        if key not in observed:
            observed[key] = {
                "classification": job["classification"],
                "detail": job["classificationDetail"],
                "runId": job["id"],
                "url": job["url"],
                "arm": arm,
                "revision": job.get("revision"),
            }
    for key, observation in observed.items():
        latest_revision = observation.get("revision")
        samples = [] if not latest_revision else [
            job for job in history[key]
            if job.get("revision") == latest_revision
        ][:window_size]
        passed = sum(job["classification"] == "passed" for job in samples)
        observation["history"] = {
            "sampleSize": len(samples),
            "passCount": passed,
            "passRate": round(passed / len(samples), 3) if samples else None,
            "targetMinSamples": target_min_samples,
            "windowSize": window_size,
        }
    return observed


def collect(server, pipelines, limit, excluded_job_names):
    warnings = []
    report = {
        "schemaVersion": 2,
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "server": server.rstrip("/"),
        "cases": inventory(),
        "pipelines": [],
        "warnings": warnings,
    }
    all_jobs_by_id = {}
    normalized_by_id = {}

    def normalized(node):
        identifier = node["id"]
        if identifier not in normalized_by_id:
            normalized_by_id[identifier] = normalize_run(server, warnings, node)
        return normalized_by_id[identifier]

    for pipeline in pipelines:
        listed = cli_json(
            warnings, server, "run", "list", "--job", pipeline, "--limit", str(limit), "--json"
        ) or {}
        heads = []
        for head in listed.get("build") or []:
            detailed_head = (
                cli_json(warnings, server, "run", "view", str(head["id"]), "--json")
                or head
            )
            head_revision = vcs_revision(detailed_head)
            tree = cli_json(warnings, server, "run", "tree", str(head["id"]), "--json") or head
            jobs = []
            for node in flatten_dependencies(tree):
                if (
                    node.get("name") not in EVAL_JOB_NAMES
                    or node.get("name") in excluded_job_names
                ):
                    continue
                job = normalized(node)
                if not job.get("revision"):
                    # Snapshot-dependency jobs omit lastChanges on this server;
                    # the pipeline head owns the exact VCS revision for all of
                    # them in the chain.
                    job["revision"] = head_revision
                jobs.append(job)
                all_jobs_by_id.setdefault(
                    job["id"], {**job, "pipeline": pipeline, "headId": head["id"]}
                )
            normalized_head = {
                "id": head["id"],
                "number": detailed_head.get("number"),
                "state": detailed_head.get("state"),
                "status": detailed_head.get("status"),
                "statusText": detailed_head.get("statusText"),
                "url": detailed_head.get("webUrl"),
                "trigger": (detailed_head.get("triggered") or {}).get("type"),
                "queuedAt": iso_time(detailed_head.get("queuedDate")),
                "startedAt": iso_time(detailed_head.get("startDate")),
                "finishedAt": iso_time(detailed_head.get("finishDate")),
                "revision": head_revision,
                "jobs": jobs,
            }
            heads.append(normalized_head)
        report["pipelines"].append({"id": pipeline, "runs": heads})

    all_jobs = list(all_jobs_by_id.values())
    observed = latest_arm_observations(all_jobs)
    for case in report["cases"]:
        if case["executionModel"] == "paired-arms":
            case["arms"] = {arm: observed.get((case["id"], arm)) for arm in ARMS}
        else:
            case["arms"] = None

    counts = {}
    for job in all_jobs:
        counts[job["classification"]] = counts.get(job["classification"], 0) + 1
    usage_rows = [
        safe_agent_usage((job.get("result") or {}).get("agentUsage"))
        for job in all_jobs
    ]
    usage_rows = [usage for usage in usage_rows if usage]
    usage_totals = {"runsMeasured": len(usage_rows)}
    for field in USAGE_FIELDS:
        values = [usage[field] for usage in usage_rows if field in usage]
        if values:
            usage_totals[field] = round(sum(values), 6)
    usage_totals["fieldsMeasured"] = {
        field: sum(field in usage for usage in usage_rows)
        for field in USAGE_FIELDS
    }
    report["summary"] = {
        "caseContracts": len(report["cases"]),
        "pairedCaseContracts": sum(
            case["executionModel"] == "paired-arms" for case in report["cases"]
        ),
        "expectedArmSlots": sum(
            2 for case in report["cases"] if case["executionModel"] == "paired-arms"
        ),
        "distinctCasesObserved": len({case_id for case_id, _arm in observed}),
        "distinctArmsObserved": len(observed),
        "jobRunsObserved": len(all_jobs),
        "classifications": counts,
        "agentUsage": usage_totals,
    }
    report["recommendations"] = [
        "Complete skill and baseline arms on one pinned revision; a single skill-arm pass does not measure skill lift.",
        "Run teamcity-cli-not-curl with curl and the TeamCity CLI both available, so the tool-choice assertion is meaningful.",
        "Run queued-no-compatible-agent as paired arms to measure whether the skill prevents blind queue polling.",
        "Run the Spring Petclinic first-green case before the aspirational Kotlin Multiplatform case.",
        "Keep access preflight separate from paired agent evaluations until it has an executable runner.",
    ]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True, help="TeamCity base URL")
    parser.add_argument(
        "--pipeline", action="append", dest="pipelines", required=True,
        help="Pipeline head build type ID (repeatable)"
    )
    parser.add_argument("--limit", type=int, default=32, help="Recent pipeline heads per pipeline")
    parser.add_argument(
        "--exclude-job-name", action="append", default=[],
        help="Job display name to omit from the report (repeatable)",
    )
    parser.add_argument("--output", required=True, type=pathlib.Path, help="Normalized report JSON")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    report = collect(args.server, args.pipelines, args.limit, set(args.exclude_job_name))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {args.output} ({report['summary']['jobRunsObserved']} job run(s))")


if __name__ == "__main__":
    main()
