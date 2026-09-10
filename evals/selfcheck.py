#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Prove the grader reads a real TeamCity pipeline correctly, without an agent.

Every defect found so far cost a full agent run to surface, and none of them
were the skill's: a 404 treated as an error, jobs read from build
configurations that do not exist until a build runs, a pipeline project that no
project locator returns. All three are visible in seconds against a pipeline
this script creates itself.

It builds a pipeline whose shape is known, grades it, and compares the verdict
against the one the shape demands.

    TEAMCITY_URL=... TEAMCITY_TOKEN=... python3 evals/selfcheck.py
"""

import json
import os
import pathlib
import secrets
import subprocess
import sys
import tempfile
import time
import importlib.util

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("run_case", HERE / "run_case.py")
run_case = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_case)

FIXTURE = """\
name: selfcheck fixture
jobs:
  android:
    name: Android
    runs-on: Linux-Medium
    files-publication:
      - path: composeApp/build/outputs/apk/debug/app-debug.apk
        publish-artifact: true
    steps:
      - type: gradle
        name: Assemble
        tasks: assembleDebug
  ios:
    name: iOS
    runs-on: Mac-Medium
    steps:
      - type: script
        name: xcodebuild
        script-content: xcodebuild -list
  desktop:
    name: Desktop
    runs-on: Linux-Medium
    steps:
      - type: gradle
        name: Package
        tasks: packageDistributionForCurrentOS
"""

# What the fixture above must produce, if the grader reads it correctly.
EXPECTATIONS = {
    "configurationValidated": True,
    "minimumJobs": True,
    "jobCount": True,
    "requiredStepTypes": True,
    "requiredArtifactRules": True,
    "requiredAgentRequirements": True,
    "requiredJobs": True,
    "sourceMutations": True,
}

CASE = {
    "expected": {
        "configurationValidated": True,
        "sourceMutations": "none",
        "minimumJobs": 3,
        "expectedJobCount": 3,
        "requiredStepTypes": ["gradle", "script"],
        "requiredArtifactRules": [r"\.apk"],
        "requiredAgentRequirements": ["Mac-Medium"],
        "requiredJobs": [
            {
                "jobMatches": "(?i)android",
                "requiredStepTypes": ["gradle"],
                "requiredStepProperties": [
                    {"stepType": "gradle", "property": "tasks", "matches": "assembleDebug"}
                ],
                "requiredArtifactRules": [r"\.apk"],
                "requiredAgentRequirements": ["Linux-Medium"],
            },
            {
                "jobMatches": "(?i)ios",
                "requiredStepTypes": ["script"],
                "requiredStepProperties": [
                    {"stepType": "script", "property": "script-content", "matches": "xcodebuild"}
                ],
                "requiredAgentRequirements": ["Mac-Medium"],
            },
            {
                "jobMatches": "(?i)desktop",
                "requiredStepTypes": ["gradle"],
                "requiredStepProperties": [
                    {
                        "stepType": "gradle",
                        "property": "tasks",
                        "matches": "packageDistributionForCurrentOS",
                    }
                ],
            },
        ],
    }
}


def teamcity_cli() -> str:
    """Return the executable installed by bootstrap-teamcity-cli.sh."""
    return os.environ.get("TEAMCITY_EVAL_CLI", "teamcity")


def main() -> int:
    url, token = os.environ.get("TEAMCITY_URL"), os.environ.get("TEAMCITY_TOKEN")
    if not url or not token:
        sys.exit("TEAMCITY_URL and TEAMCITY_TOKEN must be set")

    tc = run_case.TeamCity(url, token)
    parent = os.environ.get("EVAL_PARENT_PROJECT", "_Root")
    # Container PIDs repeat between TeamCity builds; they do not make a unique
    # project name. A short random suffix keeps a failed cleanup from blocking
    # the next self-check.
    project_id = tc.create_project(f"selfcheck-{secrets.token_hex(4)}", parent)
    try:
        tc.mark_temporary_project(
            project_id, float(os.environ.get("EVAL_PROJECT_TTL_HOURS", "6"))
        )
    except (run_case.EvalError, ValueError) as exc:
        print(f"warning: could not set temporary-project lifecycle markers: {exc}",
              file=sys.stderr)
    workspace = pathlib.Path(tempfile.mkdtemp(prefix="selfcheck-"))
    failures = []

    try:
        fixture = workspace / "fixture.yml"
        fixture.write_text(FIXTURE)
        created = subprocess.run(
            [teamcity_cli(), "pipeline", "create", "selfcheck", "--project", project_id,
             "--vcs-root", os.environ["EVAL_SELFCHECK_VCS_ROOT"], "--file", str(fixture)],
            capture_output=True, text=True,
        )
        if created.returncode:
            raise RuntimeError(f"could not create the fixture pipeline: {created.stderr.strip()}")

        jobs = []
        for attempt in range(5):
            jobs = tc.jobs(project_id)
            if jobs:
                break
            if attempt < 4:
                time.sleep(2)
        print(f"read back {len(jobs)} job(s): {[j['name'] for j in jobs]}")
        for job in jobs:
            print(f"  {job['name']:10} steps={[s['type'] for s in job['steps']]} "
                  f"runs-on={job['agentRequirements']} artifacts={job['artifactRules'].splitlines()}")

        checks = run_case.grade_configuration(CASE, {"jobs": jobs, "mutations": []})
        for name, wanted in EXPECTATIONS.items():
            got = checks.get(name, {}).get("passed")
            mark = "ok " if got == wanted else "BAD"
            if got != wanted:
                failures.append(f"{name}: expected {wanted}, grader said {got} "
                                f"({checks.get(name, {}).get('detail')})")
            print(f"  {mark} {name}")
    finally:
        # Temporary project deletion is disabled while the target server does not
        # complete the project DELETE request. The random name prevents a
        # retained project from blocking the next self-check.
        pass

    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    print(f"\n{len(failures)} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
