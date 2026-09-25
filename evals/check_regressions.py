#!/usr/bin/env python3
"""Evaluate reproducible skill-comparison gates from a safe report snapshot.

The collector already strips prompts, traces, temporary project identifiers,
and credentials.  This checker consumes only that normalized ``runs.json`` and
therefore publishes a safe regression verdict alongside the HTML report.

By default it reports failures but exits successfully.  Use ``--enforce`` only
after the evaluation owner has approved the initial reference samples.
"""

import argparse
import json
import pathlib


TOOL_MODES = ("cli-only", "mcp-only", "cli+mcp")
WINDOW_SIZE = 5


def profile(result):
    result = result if isinstance(result, dict) else {}
    return (
        result.get("caseVersion", "legacy"),
        result.get("agentConfigId", "default"),
        result.get("agentVersion", "default"),
    )


def tool_mode(result):
    mode = (result or {}).get("toolMode", "cli-only")
    return mode if mode in TOOL_MODES else "unknown"


def score(job):
    checks = ((job.get("result") or {}).get("checks") or {})
    values = [item.get("passed") for item in checks.values() if isinstance(item, dict)]
    values = [value for value in values if isinstance(value, bool)]
    return round(sum(values) / len(values), 3) if values else None


def jobs_from(data):
    """Read each evaluator job once even though snapshot trees repeat it."""
    jobs = {}
    for pipeline in data.get("pipelines") or []:
        for run in pipeline.get("runs") or []:
            for job in run.get("jobs") or []:
                jobs.setdefault(job.get("id"), job)
    return sorted((job for job in jobs.values() if job.get("id") is not None),
                  key=lambda job: job["id"], reverse=True)


def samples(jobs, revision, identity, minimum):
    matched = [
        job for job in jobs
        if job.get("revision") == revision
        and profile(job.get("result")) == identity
    ][:WINDOW_SIZE]
    scores = [score(job) for job in matched]
    scores = [value for value in scores if value is not None]
    # A run without any check score is not evidence for a numeric comparison.
    # Do not let three incomplete artifacts qualify by borrowing one score.
    if len(scores) < minimum:
        return None
    return {
        "sampleSize": len(scores),
        "averageMetricScore": round(sum(scores) / len(scores), 3),
    }


def grouped(jobs, case_id, mode, arm):
    values = [
        job for job in jobs
        if (job.get("result") or {}).get("caseId") == case_id
        and tool_mode(job.get("result")) == mode
        and (job.get("result") or {}).get("arm") == arm
    ]
    by_revision = {}
    for job in values:
        revision = job.get("revision")
        if not revision:
            continue
        identity = profile(job.get("result"))
        by_revision.setdefault((revision, identity), []).append(job)
    return by_revision


def newest_common_revision(skill_groups, baseline_groups):
    candidates = set(skill_groups) & set(baseline_groups)
    if not candidates:
        return None
    return max(candidates, key=lambda key: max(
        job["id"] for job in skill_groups[key] + baseline_groups[key]
    ))


def evaluate(data, minimum_samples=3):
    jobs = jobs_from(data)
    findings = []
    failures = []
    for case in data.get("cases") or []:
        if case.get("gate") != "active" or case.get("executionModel") != "paired-arms":
            continue
        for mode in TOOL_MODES:
            skill_groups = grouped(jobs, case["id"], mode, "skill")
            baseline_groups = grouped(jobs, case["id"], mode, "baseline")
            common = newest_common_revision(skill_groups, baseline_groups)
            comparison = {
                "caseId": case["id"],
                "toolMode": mode,
                "kind": "skill-vs-baseline",
            }
            if not common:
                comparison["status"] = "insufficient-samples"
                findings.append(comparison)
            else:
                revision, identity = common
                skill_samples = samples(skill_groups[common], revision, identity, minimum_samples)
                baseline_samples = samples(
                    baseline_groups[common], revision, identity, minimum_samples
                )
                if not skill_samples or not baseline_samples:
                    comparison["status"] = "insufficient-samples"
                    findings.append(comparison)
                else:
                    comparison.update(
                        revision=revision,
                        skill=skill_samples,
                        baseline=baseline_samples,
                    )
                    if skill_samples["averageMetricScore"] > baseline_samples["averageMetricScore"]:
                        comparison["status"] = "skill-better"
                    else:
                        comparison["status"] = "skill-not-better"
                        failures.append(comparison)
                    findings.append(comparison)

            skill_revisions = sorted(
                skill_groups,
                key=lambda key: max(job["id"] for job in skill_groups[key]),
                reverse=True,
            )
            qualified = []
            for revision, identity in skill_revisions:
                value = samples(skill_groups[(revision, identity)], revision, identity, minimum_samples)
                if value:
                    qualified.append((revision, identity, value))
            regression = {
                "caseId": case["id"],
                "toolMode": mode,
                "kind": "skill-vs-previous-skill",
            }
            if len(qualified) < 2:
                regression["status"] = "insufficient-history"
            else:
                current_revision, _, current = qualified[0]
                previous_revision, _, previous = qualified[1]
                regression.update(
                    revision=current_revision,
                    previousRevision=previous_revision,
                    skill=current,
                    previousSkill=previous,
                )
                if current["averageMetricScore"] < previous["averageMetricScore"]:
                    regression["status"] = "skill-regression"
                    failures.append(regression)
                else:
                    regression["status"] = "no-skill-regression"
            findings.append(regression)

    return {
        "schemaVersion": 1,
        "minimumSamples": minimum_samples,
        "findings": findings,
        "failures": failures,
        "status": "failed" if failures else "passed",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--minimum-samples", type=int, default=3)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    if args.minimum_samples < 1:
        parser.error("--minimum-samples must be positive")
    result = evaluate(json.loads(args.input.read_text()), args.minimum_samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"{result['status']}: {len(result['failures'])} regression finding(s)")
    return 1 if args.enforce and result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
