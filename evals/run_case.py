#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Execute one TeamCity skill evaluation case.

The case owns the expected behaviour; this runner owns the environment. It
checks out the pinned revision, invokes the agent, and grades the observable
outcome. Build/configuration cases provision a temporary TeamCity project;
queue-stall cases use a deterministic CLI fixture and consume no build agent.

Configuration comes from the environment, never from the case:

    TEAMCITY_URL           server to evaluate against
    TEAMCITY_TOKEN         access token for that server
    EVAL_PARENT_PROJECT    parent project for temporary objects (default _Root)
    EVAL_AGENT_CMD         command that runs the agent; the prompt arrives on
                           stdin and the working directory is the checkout
                           (default "claude -p --output-format stream-json --verbose")
    EVAL_BUILD_TIMEOUT     seconds to wait for the build (default 3600)
    EVAL_AGENT_TIMEOUT     seconds to wait for the agent (default 3600)
    EVAL_KEEP              set to 1 to leave the temporary project and checkout
                           in place, the same as --keep
    EVAL_TRACE_DIR         protected directory for the agent trace (default:
                           the disposable evaluation workspace)
    EVAL_FAILED_AGENT_GRACE  seconds to still wait for a build after the agent
                           exited non-zero (default 120)
    EVAL_ARM               "skill" (default) or "baseline". The baseline arm
                           withholds the skill and changes nothing else, so the
                           difference between the two arms is the skill's effect

Standard library only, so it runs with a bare python3:

    python3 evals/run_case.py --case evals/first-green-build/cases/<id>.json
    python3 evals/run_case.py --case <path> --dry-run

Schema validation of the cases themselves lives in evals/validate.py.
"""

import argparse
import datetime
import fnmatch
import http.cookiejar
import json
import os
import pathlib
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Optional
import urllib.error
import urllib.parse
import urllib.request

EVALS = pathlib.Path(__file__).parent
PLACEHOLDER = re.compile(r"\{\{teamcity\.(server|targetProject)\}\}")
sys.path.insert(0, str(EVALS))
from teamcity_cli_bridge import BridgeError, TeamCityCliBridge


class EvalError(RuntimeError):
    """A failure of the runner or the environment, not of the agent."""


class _Graded(Exception):
    """Grading finished early; skip the build steps and go straight to teardown."""


# --------------------------------------------------------------------------- #
# TeamCity REST
# --------------------------------------------------------------------------- #

class TeamCity:
    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/")
        self.token = token
        # TeamCity clusters can route configuration writes to a responsible
        # node through the session cookie. Keep one opener for the full eval
        # lifecycle so project creation and teardown reach the same node.
        cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookies)
        )
        self._configuration_node_id = None
        self._configuration_node_discovered = False

    def request(
        self,
        path: str,
        method: str = "GET",
        body=None,
        accept="application/json",
        timeout: int = 60,
    ):
        url = path if path.startswith("http") else f"{self.url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", accept)
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(req, timeout=timeout) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise EvalError(f"{method} {path} -> HTTP {exc.code}: {detail}") from None
        if not payload:
            return None
        return json.loads(payload) if accept == "application/json" else payload

    def request_text(
        self,
        path: str,
        method: str = "PUT",
        body: str = "",
        accept: str = "text/plain",
        timeout: int = 60,
    ):
        """Send a text/plain TeamCity REST request using the same safe session."""
        url = path if path.startswith("http") else f"{self.url}{path}"
        req = urllib.request.Request(url, data=body.encode(), method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", accept)
        req.add_header("Content-Type", "text/plain")
        try:
            with self.opener.open(req, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise EvalError(f"{method} {path} -> HTTP {exc.code}: {detail}") from None

    def configuration_write_path(self, path: str) -> str:
        """Route project lifecycle writes to the cluster's configuration node.

        In a TeamCity cluster, a load balancer may route a request to a node
        without ``MAIN_NODE`` responsibility. The REST ``__nodeId`` query
        parameter makes those writes deterministic. Older servers or narrowly
        scoped tokens may not expose the node list, in which case retaining the
        session cookie is the compatible fallback.
        """
        if not self._configuration_node_discovered:
            self._configuration_node_discovered = True
            try:
                nodes = self.request("/app/rest/server/nodes?fields=node(id)")
                for node in nodes.get("node", []):
                    node_id = node.get("id")
                    if not node_id:
                        continue
                    responsibilities = self.request(
                        f"/app/rest/server/nodes/id:{urllib.parse.quote(node_id, safe='')}/"
                        "effectiveResponsibilities?fields=responsibility(name)"
                    )
                    if any(
                        item.get("name") == "MAIN_NODE"
                        for item in responsibilities.get("responsibility", [])
                    ):
                        self._configuration_node_id = node_id
                        break
            except EvalError:
                # Node discovery is optional: a standalone server and some
                # restricted project tokens do not expose the cluster API.
                pass

        if not self._configuration_node_id:
            return path
        separator = "&" if "?" in path else "?"
        node_id = urllib.parse.quote(self._configuration_node_id, safe="")
        return f"{path}{separator}__nodeId={node_id}"

    def create_project(self, name: str, parent: str) -> str:
        created = self.request(
            "/app/rest/projects",
            method="POST",
            body={"name": name, "parentProject": {"locator": f"id:{parent}"}},
        )
        return created["id"]

    def delete_project(self, project_id: str) -> None:
        self.request(
            self.configuration_write_path(f"/app/rest/projects/id:{project_id}"),
            method="DELETE",
            accept="text/plain",
            # In a multi-node server deletion can include child pipeline and
            # build-configuration cleanup. The server often takes longer than
            # the regular REST read timeout, even after accepting the request.
            timeout=300,
        )

    def set_project_parameter(self, project_id: str, name: str, value: str) -> None:
        project = urllib.parse.quote(project_id, safe="")
        parameter = urllib.parse.quote(name, safe="")
        path = self.configuration_write_path(
            f"/app/rest/projects/id:{project}/parameters/{parameter}"
        )
        self.request_text(path, body=value)

    def set_project_archived(self, project_id: str, archived: bool) -> None:
        project = urllib.parse.quote(project_id, safe="")
        path = self.configuration_write_path(f"/app/rest/projects/id:{project}/archived")
        self.request_text(path, body="true" if archived else "false")

    def mark_temporary_project(self, project_id: str, ttl_hours: float = 6) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        expires = now + datetime.timedelta(hours=ttl_hours)
        markers = {
            "teamcity.eval.temporary": "true",
            "teamcity.eval.createdAt": now.isoformat(),
            "teamcity.eval.expiresAt": expires.isoformat(),
        }
        for name, value in markers.items():
            self.set_project_parameter(project_id, name, value)

    def build_types(self, project_id: str):
        locator = urllib.parse.quote(f"affectedProject:(id:{project_id})", safe="")
        found = self.request(f"/app/rest/buildTypes?locator={locator}")
        return found.get("buildType", [])

    def builds(self, project_id: str):
        locator = urllib.parse.quote(
            f"affectedProject:(id:{project_id}),defaultFilter:false,personal:any,"
            f"branch:default:any,count:50",
            safe="",
        )
        try:
            found = self.request(f"/app/rest/builds?locator={locator}")
        except EvalError as exc:
            # Until the agent creates a build configuration the project holds
            # none, and TeamCity answers 404 rather than an empty collection.
            if "HTTP 404" in str(exc):
                return []
            raise
        return found.get("build", [])

    def build(self, build_id: int):
        return self.request(
            f"/app/rest/builds/id:{build_id}"
            "?fields=id,number,state,status,statusText,webUrl,personal"
        )

    def pipeline_ids(self, project_id: str) -> list:
        """Pipelines under a project, found through their head build configuration.

        A pipeline lives in its own sub-project, but those sub-projects do not
        come back from the projects endpoint under any locator tried; their head
        build configuration does, and its projectId is the pipeline's id.
        """
        locator = urllib.parse.quote(f"affectedProject:(id:{project_id})", safe="")
        found = self.request(f"/app/rest/buildTypes?locator={locator}&fields=buildType(projectId)")
        seen = []
        for bt in found.get("buildType", []):
            pipeline_id = bt.get("projectId")
            if pipeline_id and pipeline_id != project_id and pipeline_id not in seen:
                seen.append(pipeline_id)
        return seen

    def pipeline(self, pipeline_id: str):
        """The pipeline the server holds, or None if this project is not one.

        The response carries the stored YAML alongside the VCS root it is bound
        to, which is the only description available before a build has run.
        """
        try:
            return self.request(f"/app/pipeline/{pipeline_id}")
        except EvalError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise

    def jobs(self, project_id: str) -> list:
        """The jobs the agent defined, read from the pipeline YAML on the server.

        A pipeline materialises its jobs as build configurations only once a
        build has run; before that the project holds nothing but a composite
        head. The YAML the server stores is therefore the only description of a
        pipeline that was created but never run.
        """
        try:
            import yaml
        except ImportError:
            raise EvalError("PyYAML is required to read pipeline definitions") from None

        collected = []
        for pipeline_id in self.pipeline_ids(project_id):
            pipeline = self.pipeline(pipeline_id)
            if not pipeline or not pipeline.get("yaml"):
                continue
            parsed = yaml.safe_load(pipeline["yaml"]) or {}
            for job_id, job in (parsed.get("jobs") or {}).items():
                job = job or {}
                steps = [
                    {
                        "type": step.get("type"),
                        "name": step.get("name"),
                        "properties": {k: v for k, v in step.items()
                                       if k not in ("type", "name")},
                    }
                    for step in (job.get("steps") or [])
                ]
                # Pipeline YAML permits the short string form as well as an
                # object with an explicit ``publish-artifact`` flag. A string
                # is itself an artifact rule, so it must not be treated as a
                # mapping by the grader.
                published = [
                    entry if isinstance(entry, str) else entry.get("path", "")
                    for entry in (job.get("files-publication") or [])
                    if isinstance(entry, str)
                    or (isinstance(entry, dict) and entry.get("publish-artifact"))
                ]
                runs_on = job.get("runs-on")
                collected.append({
                    "id": f"{pipeline_id}/{job_id}",
                    "name": job.get("name") or job_id,
                    "steps": steps,
                    "artifactRules": "\n".join(published),
                    "agentRequirements": [str(runs_on)] if runs_on else [],
                })
        return collected

    def resulting_properties(self, build_id: int) -> dict:
        # TeamCity 2026.3 rejects the legacy camel-case endpoint with HTTP 406.
        # The hyphenated collection endpoint accepts JSON and keeps the request
        # scoped to the property fields needed for toolchain evidence.
        found = self.request(
            f"/app/rest/builds/id:{build_id}/resulting-properties"
            "?fields=property(name,value)"
        )
        return {p["name"]: p.get("value", "") for p in found.get("property", [])}

    def test_count(self, build_id: int) -> int:
        locator = urllib.parse.quote(f"build:(id:{build_id})", safe="")
        return self.request(f"/app/rest/testOccurrences?locator={locator}&fields=count")["count"]

    def artifacts(self, build_id: int, path: str = "") -> list:
        """Every published artifact path, walked recursively."""
        try:
            listing = self.request(f"/app/rest/builds/id:{build_id}/artifacts/children/{path}")
        except EvalError:
            return []
        collected = []
        for entry in listing.get("file", []):
            name = entry["name"]
            full = f"{path}/{name}".lstrip("/")
            if "children" in entry:
                collected.extend(self.artifacts(build_id, full))
            else:
                collected.append(full)
        return collected


# --------------------------------------------------------------------------- #
# Grading helpers
# --------------------------------------------------------------------------- #

def artifact_matches(pattern: str, published: list) -> bool:
    """Does any published artifact satisfy this expected path?

    The case states source-tree paths such as template-app/build/libs/*.jar,
    while TeamCity stores whatever the artifact rules produced, often flattened.
    Accept a full-path match, a trailing-subpath match, or a basename match, in
    that order of preference.
    """
    tail = pattern.rstrip("/").split("/")[-1] or "*"
    for candidate in published:
        if fnmatch.fnmatch(candidate, pattern):
            return True
        if fnmatch.fnmatch(candidate, f"*/{pattern.lstrip('/')}"):
            return True
        if fnmatch.fnmatch(candidate.split("/")[-1], tail):
            return True
    return False


def toolchain_evidence(properties: dict, jdk: str, jobs: list = None) -> tuple:
    """Which JDK the build resolved, read from the properties it ran with.

    Returns (matched, evidence). A build that names no JDK anywhere is reported
    as unmatched with whatever was searched, so a weak probe shows up as a
    visible failure rather than a silent pass.
    """
    version = re.compile(rf"(?<!\d){re.escape(jdk)}(?!\d)")
    candidates = {
        name: value for name, value in properties.items()
        if "java" in name.lower() or "jdk" in name.lower()
    }
    matched = sorted(n for n, v in candidates.items() if version.search(v) or version.search(n))
    images = sorted({
        str(step["properties"]["docker-image"])
        for job in (jobs or [])
        for step in job["steps"]
        if "docker-image" in step["properties"]
    })
    matched_images = [
        image for image in images
        if version.search(image) and re.search(r"(?i)java|jdk|openjdk|temurin", image)
    ]
    evidence = matched + [f"docker-image:{image}" for image in matched_images]
    fallback = sorted(candidates)[:8] + [f"docker-image:{image}" for image in images[:4]]
    return bool(evidence), evidence or fallback


def source_mutations(checkout: pathlib.Path, allowed: list) -> list:
    """Paths the agent changed in the disposable checkout, minus allowed ones."""
    porcelain = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=checkout, capture_output=True, text=True, check=True,
    ).stdout
    changed = []
    for line in porcelain.splitlines():
        path = line[3:].strip().strip('"')
        if any(path == a or path.startswith(a.rstrip("/") + "/") for a in allowed):
            continue
        changed.append(path)
    return sorted(changed)


def grade(case: dict, observed: dict) -> dict:
    """Compare what happened against expected. Returns assertion -> pass/fail."""
    expected = case["expected"]
    checks = {}

    checks["configurationValidated"] = {
        "expected": expected["configurationValidated"],
        "observed": observed["buildTypeCount"] > 0 and observed["buildStatus"] is not None,
        "detail": f"{observed['buildTypeCount']} build configuration(s) created",
    }
    # "firstBuild" is the case's name for the outcome the skill iterates toward,
    # not literally the first build: the skill is expected to keep going until a
    # build is green, so the last build is what the contract is about.
    checks["firstBuild"] = {
        "expected": expected["firstBuild"],
        "observed": observed["buildStatus"],
        "detail": f"{observed.get('statusText') or ''}"
                  f" after {observed['attempts']} build(s) in the project".strip(),
    }
    checks["testsExecutedAndReported"] = {
        "expected": expected["testsExecutedAndReported"],
        "observed": observed["testCount"] > 0,
        "detail": f"{observed['testCount']} test occurrence(s) imported",
    }
    missing = [
        p for p in case["verification"]["artifactPaths"]
        if not artifact_matches(p, observed["artifacts"])
    ]
    checks["artifactsPublished"] = {
        "expected": expected["artifactsPublished"],
        "observed": not missing,
        "detail": f"unmatched: {missing}" if missing else f"{len(observed['artifacts'])} artifact(s)",
    }
    jdk = expected["toolchain"]["jdk"]
    matched, evidence = toolchain_evidence(observed["properties"], jdk, observed.get("jobs"))
    checks["toolchain"] = {
        "expected": jdk,
        "observed": jdk if matched else "not-evidenced",
        "detail": f"matched: {evidence}" if matched else f"no JDK {jdk} among: {evidence}",
    }
    checks["sourceMutations"] = {
        "expected": expected["sourceMutations"],
        "observed": "none" if not observed["mutations"] else "changed",
        "detail": f"changed: {observed['mutations']}" if observed["mutations"] else "clean checkout",
    }

    for check in checks.values():
        check["passed"] = check["expected"] == check["observed"] or check["expected"] is check["observed"]
    return checks


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #

def grade_configuration(case: dict, observed: dict) -> dict:
    """Grade the pipeline the agent produced, without running it."""
    expected = case["expected"]
    jobs = observed["jobs"]
    checks = {}

    checks["configurationValidated"] = {
        "expected": True,
        "observed": bool(jobs),
        "detail": f"{len(jobs)} job(s): {[j['name'] for j in jobs]}",
    }
    checks["minimumJobs"] = {
        "expected": expected["minimumJobs"],
        "observed": len(jobs),
        "detail": f"{len(jobs)} job(s) carrying build steps",
    }
    checks["minimumJobs"]["observed"] = len(jobs) >= expected["minimumJobs"]
    checks["minimumJobs"]["expected"] = True

    if "expectedJobCount" in expected:
        checks["jobCount"] = {
            "expected": expected["expectedJobCount"],
            "observed": len(jobs),
            "detail": f"{len(jobs)} job(s) carrying build steps",
        }

    step_types = {step["type"] for job in jobs for step in job["steps"]}
    if "requiredStepTypes" in expected:
        missing = [t for t in expected["requiredStepTypes"] if t not in step_types]
        checks["requiredStepTypes"] = {
            "expected": True,
            "observed": not missing,
            "detail": f"missing {missing}" if missing else f"present: {sorted(step_types)}",
        }

    if "requiredStepProperties" in expected:
        missing = []
        for want in expected["requiredStepProperties"]:
            pattern = re.compile(want["matches"]) if "matches" in want else None
            satisfied = any(
                step["type"] == want["stepType"]
                and want["property"] in step["properties"]
                and (pattern is None or pattern.search(step["properties"][want["property"]]))
                for job in jobs for step in job["steps"]
            )
            if not satisfied:
                missing.append(f"{want['stepType']}.{want['property']}"
                               + (f" ~ {want['matches']}" if pattern else ""))
        checks["requiredStepProperties"] = {
            "expected": True,
            "observed": not missing,
            "detail": f"missing {missing}" if missing else "all present",
        }

    if "requiredArtifactRules" in expected:
        rules = "\n".join(job["artifactRules"] for job in jobs)
        missing = [r for r in expected["requiredArtifactRules"] if not re.search(r, rules)]
        checks["requiredArtifactRules"] = {
            "expected": True,
            "observed": not missing,
            "detail": f"missing {missing} in {rules!r}" if missing else f"rules: {rules!r}",
        }

    if "requiredAgentRequirements" in expected:
        text = "\n".join(r for job in jobs for r in job["agentRequirements"])
        missing = [r for r in expected["requiredAgentRequirements"] if not re.search(r, text)]
        checks["requiredAgentRequirements"] = {
            "expected": True,
            "observed": not missing,
            "detail": f"missing {missing} in {text!r}" if missing else f"requirements: {text!r}",
        }

    if "requiredJobs" in expected:
        failures = []
        selected = set()
        for contract in expected["requiredJobs"]:
            matcher = contract["jobMatches"]
            candidates = [
                (index, job) for index, job in enumerate(jobs)
                if re.search(matcher, f"{job['id'].rsplit('/', 1)[-1]}\n{job['name']}")
            ]
            if len(candidates) != 1:
                failures.append(f"{matcher!r} matched {len(candidates)} jobs")
                continue

            index, job = candidates[0]
            if index in selected:
                failures.append(f"{matcher!r} reused a job selected by another contract")
                continue
            selected.add(index)

            step_types = {step["type"] for step in job["steps"]}
            missing_types = [
                step_type for step_type in contract.get("requiredStepTypes", [])
                if step_type not in step_types
            ]
            if missing_types:
                failures.append(f"{matcher!r} missing step types {missing_types}")

            for want in contract.get("requiredStepProperties", []):
                pattern = re.compile(want["matches"]) if "matches" in want else None
                satisfied = any(
                    step["type"] == want["stepType"]
                    and want["property"] in step["properties"]
                    and (
                        pattern is None
                        or pattern.search(str(step["properties"][want["property"]]))
                    )
                    for step in job["steps"]
                )
                if not satisfied:
                    failures.append(
                        f"{matcher!r} missing {want['stepType']}.{want['property']}"
                    )

            missing_artifacts = [
                pattern for pattern in contract.get("requiredArtifactRules", [])
                if not re.search(pattern, job["artifactRules"])
            ]
            if missing_artifacts:
                failures.append(f"{matcher!r} missing artifacts {missing_artifacts}")

            requirements = "\n".join(job["agentRequirements"])
            missing_requirements = [
                pattern for pattern in contract.get("requiredAgentRequirements", [])
                if not re.search(pattern, requirements)
            ]
            if missing_requirements:
                failures.append(
                    f"{matcher!r} missing agent requirements {missing_requirements}"
                )

        checks["requiredJobs"] = {
            "expected": True,
            "observed": not failures,
            "detail": f"violations: {failures}" if failures else "all per-job contracts satisfied",
        }

    if "toolUse" in expected:
        calls = observed["toolCalls"]
        unmet = [r for r in expected["toolUse"].get("required", [])
                 if not any(re.search(r, c) for c in calls)]
        used = [r for r in expected["toolUse"].get("forbidden", [])
                if any(re.search(r, c) for c in calls)]
        checks["toolUse"] = {
            "expected": True,
            "observed": not unmet and not used,
            "detail": (f"never called {unmet}; " if unmet else "")
                      + (f"called forbidden {used}; " if used else "")
                      + f"{len(calls)} call(s) recorded",
        }

    checks["sourceMutations"] = {
        "expected": expected["sourceMutations"],
        "observed": "none" if not observed["mutations"] else "changed",
        "detail": f"changed: {observed['mutations']}" if observed["mutations"] else "clean checkout",
    }

    for check in checks.values():
        check["passed"] = check["expected"] == check["observed"] or check["expected"] is check["observed"]
    return checks


TEAMCITY_COMMAND = r"\bteamcity(?:\.cmd)?\s+"
STATUS_CALL = re.compile(TEAMCITY_COMMAND + r"(?:run\s+view|queue\s+list)\b", re.I)
WAIT_CALL = re.compile(TEAMCITY_COMMAND + r"run\s+watch\b|\bsleep\s+\d+", re.I)
DIAGNOSTIC_CALLS = {
    "agent-inventory": re.compile(TEAMCITY_COMMAND + r"agent\s+list\b", re.I),
    "job-incompatibility-reasons": re.compile(
        TEAMCITY_COMMAND + r"(?:agent\s+jobs\b[^\n]*--incompatible\b|job\s+view\b)", re.I
    ),
}
CONCLUSION_PATTERNS = {
    "no-compatible-agent": re.compile(
        r"\b(?:no|zero)\s+compatible\s+agents?\b|\bno\s+agent\s+is\s+compatible\b",
        re.I,
    ),
    "unresolved-parameter": re.compile(
        r"\bunresolved\s+(?:teamcity\s+)?parameters?\b|"
        r"\bparameters?\b[^.\n]*(?:undefined|not\s+defined|cannot\s+resolve)",
        re.I,
    ),
}


def stored_parameter_diagnostics(calls: list) -> bool:
    pulled = any(re.search(TEAMCITY_COMMAND + r"pipeline\s+pull\b", call, re.I)
                 for call in calls)
    inspected = any(
        re.search(r"\b(?:rg|grep)\b[^\n]*(?:%|parameter|ya?ml)", call, re.I)
        or re.search(r"\b(?:Read|Grep)\b[^\n]*\.ya?ml", call, re.I)
        for call in calls
    )
    return pulled and inspected


def forbidden_queue_actions(calls: list) -> set:
    used = set()
    for call in calls:
        if re.search(TEAMCITY_COMMAND + r"run\s+start\b", call, re.I):
            used.add("queue-duplicate")
        if re.search(TEAMCITY_COMMAND + r"run\s+restart\b", call, re.I):
            used.add("restart-run")
        if re.search(TEAMCITY_COMMAND + r"run\s+watch\b", call, re.I) \
                and not re.search(r"--timeout(?:=|\s+)\S+", call, re.I):
            used.add("unbounded-watch")
        sleep = re.search(r"\bsleep\s+(\d+)\b", call, re.I)
        if sleep and int(sleep.group(1)) > 120:
            used.add("unbounded-watch")
    return used


def grade_queue_stall(case: dict, observed: dict) -> dict:
    """Grade the compatibility checkpoint for an already-stalled queued run."""
    expected = case["expected"]
    calls = observed["toolCalls"]
    checks = {}

    status_indices = [i for i, call in enumerate(calls) if STATUS_CALL.search(call)]
    diagnostics = {
        name: any(pattern.search(call) for call in calls)
        for name, pattern in DIAGNOSTIC_CALLS.items()
    }
    diagnostics["stored-configuration-parameters"] = stored_parameter_diagnostics(calls)
    first_compatibility = min(
        (i for i, call in enumerate(calls)
         if DIAGNOSTIC_CALLS["agent-inventory"].search(call)
         or DIAGNOSTIC_CALLS["job-incompatibility-reasons"].search(call)),
        default=None,
    )
    status_before = (
        sum(i < first_compatibility for i in status_indices)
        if first_compatibility is not None else len(status_indices)
    )
    maximum_status = expected["maximumStatusChecks"]
    checkpoint_passed = first_compatibility is not None and status_before <= maximum_status
    checks["compatibilityCheckpoint"] = {
        "expected": True,
        "observed": checkpoint_passed,
        "detail": f"compatibility checked after {status_before} queued-status observation(s)",
    }
    checks["statusCheckLimit"] = {
        "expected": True,
        "observed": len(status_indices) <= maximum_status,
        "detail": f"{len(status_indices)} status check(s), maximum {maximum_status}",
    }

    missing_diagnostics = [
        name for name in expected["requiredDiagnostics"] if not diagnostics.get(name, False)
    ]
    diagnostic_checks = {
        "agent-inventory": "diagnosticAgentInventory",
        "job-incompatibility-reasons": "diagnosticJobIncompatibility",
        "stored-configuration-parameters": "diagnosticStoredParameters",
    }
    for diagnostic in expected["requiredDiagnostics"]:
        checks[diagnostic_checks[diagnostic]] = {
            "expected": True,
            "observed": bool(diagnostics.get(diagnostic, False)),
            "detail": f"{diagnostic} {'observed' if diagnostics.get(diagnostic) else 'missing'}",
        }
    checks["requiredDiagnostics"] = {
        "expected": True,
        "observed": not missing_diagnostics,
        "detail": (
            f"missing: {missing_diagnostics}" if missing_diagnostics
            else "agent inventory, incompatibility reasons, and stored parameters inspected"
        ),
    }

    wait_count = sum(bool(WAIT_CALL.search(call)) for call in calls)
    maximum_waits = expected["maximumWaitCalls"]
    checks["waitLimit"] = {
        "expected": True,
        "observed": wait_count <= maximum_waits,
        "detail": f"{wait_count} wait call(s), maximum {maximum_waits}",
    }

    used_actions = forbidden_queue_actions(calls) & set(expected["forbiddenActions"])
    checks["noBlindRetry"] = {
        "expected": True,
        "observed": not used_actions,
        "detail": f"forbidden actions: {sorted(used_actions)}" if used_actions else "no retry or unbounded watch",
    }

    conclusions = observed["finalText"]
    missing_conclusions = [
        name for name in expected["requiredConclusions"]
        if not CONCLUSION_PATTERNS[name].search(conclusions)
    ]
    checks["diagnosisReported"] = {
        "expected": True,
        "observed": not missing_conclusions,
        "detail": (
            f"missing conclusion categories: {missing_conclusions}"
            if missing_conclusions else "stable incompatibility blocker reported"
        ),
    }

    checks["sourceMutations"] = {
        "expected": expected["sourceMutations"],
        "observed": "none" if not observed["mutations"] else "changed",
        "detail": f"changed: {observed['mutations']}" if observed["mutations"] else "clean checkout",
    }

    for check in checks.values():
        check["passed"] = check["expected"] == check["observed"] or check["expected"] is check["observed"]
    return checks


def checkout_error_kind(exc: subprocess.CalledProcessError) -> str:
    """Return a safe category without retaining raw Git output in artifacts."""
    output = f"{exc.stdout or ''}\n{exc.stderr or ''}".lower()
    if any(marker in output for marker in ("authentication failed", "invalid credentials",
                                           "could not read username", "http 401", "http 403")):
        return "authentication"
    if any(marker in output for marker in ("could not resolve host", "network is unreachable",
                                           "connection timed out", "failed to connect")):
        return "network"
    if any(marker in output for marker in ("ssl certificate", "certificate verify failed",
                                           "schannel")):
        return "tls"
    if any(marker in output for marker in ("couldn't find remote ref", "not our ref",
                                           "invalid refspec", "not a valid object name")):
        return "revision-or-ref"
    command = exc.cmd[1] if isinstance(exc.cmd, (list, tuple)) and len(exc.cmd) > 1 else "git"
    return f"git-{command}-exit-{exc.returncode}"


def checkout_repository(case: dict, destination: pathlib.Path) -> None:
    repo = case["repository"]
    default_branch = repo["defaultBranch"]
    run = lambda *args: subprocess.run(args, cwd=destination, check=True,
                                       capture_output=True, text=True)
    destination.mkdir(parents=True, exist_ok=True)
    try:
        run("git", "init", "--quiet")
        run("git", "remote", "add", "origin", repo["url"])
        # Fetch the pinned revision, which is the portable part of the case.
        # Naming the local branch after the declared default branch still makes
        # the VCS-root requirement visible to the agent without assuming a
        # particular agent can fetch remote branch refs.
        run("git", "fetch", "--quiet", "--depth", "1", "origin", repo["revision"])
        run("git", "checkout", "--quiet", "-B", default_branch, repo["revision"])
    except subprocess.CalledProcessError as exc:
        raise EvalError(
            "could not prepare the pinned repository checkout: "
            + checkout_error_kind(exc)
        ) from exc
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=destination,
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != repo["revision"]:
        raise EvalError(f"checkout is at {head}, expected the pinned {repo['revision']}")


def install_skill(case: dict, checkout: pathlib.Path) -> pathlib.Path:
    """Put the skill under evaluation where the agent will find it.

    The agent runs inside the target repository, but the skill lives in this
    one. Without this the run measures a bare agent rather than the skill.
    """
    source = EVALS.parent / "skills" / case["skill"]
    if not source.is_dir():
        raise EvalError(f"skill {case['skill']!r} not found at {source}")
    # Claude discovers repository-local skills in .claude/skills. Installing
    # the evaluated skill there keeps the skill and baseline arms identical
    # except for the skill itself.
    destination = checkout / ".claude" / "skills" / case["skill"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    return destination


def install_queue_stall_fixture(workspace: pathlib.Path, env: dict) -> dict:
    """Put a deterministic TeamCity CLI queue stall in front of the agent.

    The fixture says the run has already spent 130 seconds in the queue and
    exposes two otherwise eligible agents. Both reject the job because the
    server-stored YAML references an undefined JDK parameter. No real build or
    TeamCity object is created, so this behavioral eval stays cheap and cannot
    consume a build agent while testing wait/diagnosis decisions.
    """
    fixture_bin = workspace / "fixture-bin"
    fixture_bin.mkdir()
    fixture = fixture_bin / "teamcity-fixture.py"
    shutil.copyfile(EVALS / "fixtures" / "teamcity_queue_stall.py", fixture)
    fixture.chmod(0o755)

    launcher = fixture_bin / "teamcity"
    launcher.write_text(
        '#!/usr/bin/env sh\nexec "$EVAL_FIXTURE_PYTHON" "$(dirname "$0")/teamcity-fixture.py" "$@"\n'
    )
    launcher.chmod(0o755)
    (fixture_bin / "teamcity.cmd").write_text(
        '@"%EVAL_FIXTURE_PYTHON%" "%~dp0teamcity-fixture.py" %*\r\n'
    )

    fixture_env = dict(env)
    fixture_env["EVAL_FIXTURE_PYTHON"] = sys.executable
    fixture_env["PATH"] = str(fixture_bin) + os.pathsep + fixture_env.get("PATH", "")
    return fixture_env


def tool_calls(trace: pathlib.Path) -> list:
    """Every tool call the agent made, read from its structured trace.

    A prose summary is not evidence: an agent can use a tool without mentioning
    it, or mention one it never called.
    """
    calls = []
    try:
        lines = trace.read_text(errors="replace").splitlines()
    except OSError:
        return calls
    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use":
                calls.append(f"{block.get('name')} {json.dumps(block.get('input', {}))}")
    return calls


def agent_final_text(trace: pathlib.Path) -> str:
    """Return the agent's final prose without putting its trajectory in results."""
    latest = ""
    try:
        lines = trace.read_text(errors="replace").splitlines()
    except OSError:
        return latest
    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            latest = event["result"]
        elif event.get("type") == "assistant":
            text = "\n".join(
                block.get("text", "")
                for block in event.get("message", {}).get("content", [])
                if block.get("type") == "text"
            ).strip()
            if text:
                latest = text
    return latest


def agent_usage(trace: pathlib.Path) -> dict:
    """Return only provider-reported numeric usage from the final result event.

    Claude's stream trace is private and may contain the prompt, repository
    content, and tool arguments.  The final result event also carries aggregate
    counters; copy only that fixed numeric allowlist into the public result.
    """
    latest = {}
    try:
        lines = trace.read_text(errors="replace").splitlines()
    except OSError:
        return latest
    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "result":
            continue
        usage = event.get("usage") if isinstance(event.get("usage"), dict) else {}
        candidates = {
            "inputTokens": usage.get("input_tokens"),
            "outputTokens": usage.get("output_tokens"),
            "cacheReadTokens": usage.get("cache_read_input_tokens"),
            "cacheWriteTokens": usage.get("cache_creation_input_tokens"),
            "totalCostUsd": event.get("total_cost_usd"),
        }
        latest = {
            name: value
            for name, value in candidates.items()
            if isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value >= 0
        }
    return latest


def safe_agent_usage(value) -> dict:
    """Apply the public usage allowlist even to an already assembled result."""
    if not isinstance(value, dict):
        return {}
    allowed = (
        "inputTokens", "outputTokens", "cacheReadTokens",
        "cacheWriteTokens", "totalCostUsd",
    )
    return {
        name: value[name]
        for name in allowed
        if isinstance(value.get(name), (int, float))
        and not isinstance(value.get(name), bool)
        and value[name] >= 0
    }


def invoke_agent(prompt: str, checkout: pathlib.Path, env: dict, trace: pathlib.Path,
                 timeout: int, tools: list = None) -> dict:
    # The runner owns the output format, because grading reads the trace, and the
    # case owns the tool policy, because which tools exist is part of the question.
    command = env.get("EVAL_AGENT_CMD", "claude -p") + " --output-format stream-json --verbose"
    if tools:
        command += " --allowedTools " + " ".join(shlex.quote(t) for t in tools)
    agent_env = dict(env)
    agent_env.pop("TEAMCITY_TOKEN", None)
    with trace.open("w") as sink:
        sink.write(f"$ {command}\n--- prompt ---\n{prompt}\n--- output ---\n")
        sink.flush()
        try:
            process = subprocess.run(
                command, shell=True, cwd=checkout, input=prompt, text=True,
                stdout=sink, stderr=subprocess.STDOUT, timeout=timeout, env=agent_env,
            )
        except subprocess.TimeoutExpired:
            # subprocess.run has already stopped and waited for the command it
            # launched. Return a normal outcome so the caller can inspect any
            # TeamCity build the agent managed to queue and, most importantly,
            # still publish a structured eval-result.json.
            sink.write(f"\n--- runner ---\nAgent timed out after {timeout}s.\n")
            sink.flush()
            return {"exitCode": 124, "timedOut": True, "timeoutSeconds": timeout}
    return {"exitCode": process.returncode, "timedOut": False, "timeoutSeconds": timeout}


def set_graded_status(result: dict, agent_run: dict) -> None:
    """Record the checks without letting a timed-out agent become a pass."""
    result["gradeStatus"] = (
        "passed" if all(check["passed"] for check in result["checks"].values()) else "failed"
    )
    if agent_run["timedOut"]:
        result["status"] = "errored"
        result["errorCategory"] = "agent-timeout"
        result["error"] = f"agent exceeded the {agent_run['timeoutSeconds']}s timeout"
    else:
        result["status"] = result["gradeStatus"]


def trace_tail(trace: pathlib.Path, lines: int = 40) -> list:
    """Read the end of the private agent trace for local classification."""
    try:
        return trace.read_text(errors="replace").splitlines()[-lines:]
    except OSError:
        return []


def trace_error_category(trace: pathlib.Path) -> Optional[str]:
    """Classify a known agent failure without publishing trace contents."""
    tail = "\n".join(trace_tail(trace)).lower()
    if "requires approval" in tail or "permission_denied" in tail:
        return "agent-permission-failure"
    return None


def publishable_result(result: dict) -> dict:
    """Return the minimal result safe to publish as a build artifact."""
    fields = (
        "caseId",
        "caseStatus",
        "arm",
        "runId",
        "status",
        "gradeStatus",
        "agentExitCode",
        "agentTimedOut",
        "agentTimeoutSeconds",
        "errorCategory",
        "temporaryObjectsRemoved",
        "cleanupDeferred",
    )
    published = {name: result[name] for name in fields if name in result}
    usage = safe_agent_usage(result.get("agentUsage"))
    if usage:
        published["agentUsage"] = usage
    published["checks"] = {
        name: {"passed": check.get("passed")}
        for name, check in (result.get("checks") or {}).items()
        if isinstance(check, dict)
    }
    return published


def wait_for_build(tc: TeamCity, project_id: str, timeout: int, poll: int = 15) -> dict:
    """The build the agent produced, once it stops running."""
    deadline = time.time() + timeout
    latest = None
    while time.time() < deadline:
        candidates = tc.builds(project_id)
        if candidates:
            latest = tc.build(max(c["id"] for c in candidates))
            if latest.get("state") == "finished":
                return latest
        time.sleep(poll)
    if latest is None:
        raise EvalError("the agent queued no build in the temporary project")
    raise EvalError(f"build {latest['id']} did not finish within {timeout}s")


def run(
    case_path: pathlib.Path,
    dry_run: bool,
    keep: bool,
    arm: str,
    lifecycle_token: Optional[str] = None,
) -> dict:
    case = json.loads(case_path.read_text())
    if case["kind"] not in (
        "first-green-build", "pipeline-configuration", "queue-stall-diagnosis"
    ):
        raise EvalError(f"kind {case['kind']!r} is not executable by this runner")

    env = dict(os.environ)
    environment_token = env.pop("TEAMCITY_TOKEN", None)
    # The runner uses this token directly. Remove it from this process before
    # any checkout-controlled agent can inspect inherited environments.
    os.environ.pop("TEAMCITY_TOKEN", None)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_id = f"{stamp}-{secrets.token_hex(3)}"
    project_name = f"eval-{arm}-{case['id'][:40]}-{run_id}"

    result = {
        "caseId": case["id"],
        "caseStatus": case.get("status", "active"),
        "arm": arm,
        "runId": run_id,
        "status": "errored",
        "checks": {},
        "build": None,
    }

    if dry_run:
        prompt = PLACEHOLDER.sub(lambda m: f"<{m.group(1)}>", case["prompt"])
        result.update(status="dry-run", prompt=prompt, projectName=project_name)
        return result


    fixture_case = case["kind"] == "queue-stall-diagnosis"
    if fixture_case:
        # A reserved, non-routable host prevents a baseline arm from touching
        # the real TeamCity server if it ignores the first-class CLI fixture.
        url, token = "https://teamcity.queue-fixture.invalid", None
        env["TEAMCITY_URL"] = url
        env.pop("TEAMCITY_TOKEN", None)
    else:
        url, token = env.get("TEAMCITY_URL"), lifecycle_token or environment_token
        if not url or not token:
            raise EvalError("TEAMCITY_URL and TEAMCITY_TOKEN must be set")

    tc = None if fixture_case else TeamCity(url, token)
    parent = env.get("EVAL_PARENT_PROJECT", "_Root")
    workspace = pathlib.Path(tempfile.mkdtemp(prefix="eval-"))
    checkout = workspace / "checkout"
    # Keep raw agent output in the disposable workspace by default. It may hold
    # repository content or credentials and is never an artifact or result field.
    trace_dir = pathlib.Path(env["EVAL_TRACE_DIR"]) if env.get("EVAL_TRACE_DIR") else workspace
    trace = trace_dir / f"agent-trace-{run_id}.log"
    trace.parent.mkdir(parents=True, exist_ok=True)
    project_id = None
    target_project = None

    try:
      try:
        if fixture_case:
            target_project = "QueueCompatibilityFixture"
            result["fixture"] = "queued-no-compatible-agent"
        else:
            project_id = tc.create_project(project_name, parent)
            target_project = project_id
            result["projectId"] = project_id
            try:
                tc.mark_temporary_project(
                    project_id, float(env.get("EVAL_PROJECT_TTL_HOURS", "6"))
                )
                result["temporaryProjectMarked"] = True
            except (EvalError, ValueError) as exc:
                # The eval itself can still produce useful evidence, but the
                # missing lifecycle marker must remain visible for cleanup.
                result["temporaryProjectMarked"] = False
                result.setdefault("warnings", []).append(
                    f"could not set temporary-project lifecycle markers: {exc}"
                )

        checkout_repository(case, checkout)
        # The baseline arm withholds the skill; everything else is identical, so
        # any difference in the checks is attributable to the skill alone.
        result["skillInstalledAt"] = (
            str(install_skill(case, checkout).relative_to(checkout))
            if arm == "skill" else None
        )

        prompt = case["prompt"].replace("{{teamcity.server}}", url) \
                               .replace("{{teamcity.targetProject}}", target_project)
        if not fixture_case:
            prompt += (
                "\n\nRepository context: the checked-out default branch is "
                f"{case['repository']['defaultBranch']!r} at the pinned revision. "
                "Ensure the VCS root monitors that branch before triggering a build."
            )
        if fixture_case:
            agent_run = invoke_agent(
                prompt, checkout, install_queue_stall_fixture(workspace, env), trace,
                int(env.get("EVAL_AGENT_TIMEOUT", "3600")),
                case.get("agentTools"),
            )
        else:
            cli_name = env.get("TEAMCITY_EVAL_CLI", "teamcity")
            cli_path = shutil.which(cli_name, path=env.get("PATH"))
            if not cli_path:
                raise EvalError(f"TeamCity CLI executable not found: {cli_name}")
            try:
                with TeamCityCliBridge(
                    cli=cli_path,
                    server_url=url,
                    token=token,
                    workspace=workspace,
                    checkout=checkout,
                    target_project=project_id,
                    allow_build_writes=case["kind"] == "first-green-build",
                    pipeline_ids=lambda: tc.pipeline_ids(project_id),
                    job_ids=lambda: [item["id"] for item in tc.build_types(project_id)],
                    base_env=env,
                ) as bridge:
                    agent_run = invoke_agent(
                        prompt, checkout, bridge.agent_environment(env), trace,
                        int(env.get("EVAL_AGENT_TIMEOUT", "3600")),
                        case.get("agentTools"),
                    )
            except BridgeError as exc:
                raise EvalError(f"could not provide scoped TeamCity CLI access: {exc}") from exc
        agent_exit = agent_run["exitCode"]
        result["agentExitCode"] = agent_exit
        result["agentTimedOut"] = agent_run["timedOut"]
        result["agentTimeoutSeconds"] = agent_run["timeoutSeconds"]
        usage = agent_usage(trace)
        if usage:
            result["agentUsage"] = usage
        result["errorCategory"] = trace_error_category(trace)

        # A dead agent queues nothing, so waiting the full budget for a build
        # that cannot arrive only delays the report.
        budget = int(env.get("EVAL_BUILD_TIMEOUT", "3600"))
        if agent_exit != 0:
            budget = min(budget, int(env.get("EVAL_FAILED_AGENT_GRACE", "120")))
        allowed = [".claude/"]
        if "requestedConfiguration" in case:
            allowed.extend([case["requestedConfiguration"]["sourcePath"], ".teamcity/"])

        if fixture_case:
            calls = tool_calls(trace)
            observed = {
                "toolCalls": calls,
                "finalText": agent_final_text(trace),
                "mutations": source_mutations(checkout, allowed),
            }
            result["diagnosticCallCount"] = len(calls)
            result["checks"] = grade_queue_stall(case, observed)
            set_graded_status(result, agent_run)
            raise _Graded

        if case["kind"] == "pipeline-configuration":
            # No build is run: the case asks what the agent configured, which is
            # answerable in minutes and without a build agent.
            observed = {
                "jobs": tc.jobs(project_id),
                "mutations": source_mutations(checkout, allowed),
                "toolCalls": tool_calls(trace),
            }
            result["toolCalls"] = observed["toolCalls"]
            result["jobs"] = observed["jobs"]
            result["checks"] = grade_configuration(case, observed)
            set_graded_status(result, agent_run)
            raise _Graded

        build = wait_for_build(tc, project_id, budget)
        # How many builds it took to get green is a quality signal in itself:
        # green on the first attempt and green on the sixth are not the same
        # work, and the graded checks alone cannot tell them apart.
        history = sorted(tc.builds(project_id), key=lambda b: b["id"])
        observed = {
            "buildTypeCount": len(tc.build_types(project_id)),
            "buildStatus": build.get("status"),
            "statusText": build.get("statusText"),
            "testCount": tc.test_count(build["id"]),
            "artifacts": tc.artifacts(build["id"]),
            "mutations": source_mutations(checkout, allowed),
            "properties": tc.resulting_properties(build["id"]),
            "jobs": tc.jobs(project_id),
            "attempts": len(history),
        }
        result["buildHistory"] = [
            {"id": b["id"], "status": b.get("status"), "buildTypeId": b.get("buildTypeId")}
            for b in history
        ]
        result["buildAttempts"] = len(history)
        result["build"] = {
            "id": build["id"], "status": build.get("status"),
            "webUrl": build.get("webUrl"), "personal": build.get("personal", False),
            "testsReported": observed["testCount"],
            "artifacts": observed["artifacts"],
            "sourceMutations": observed["mutations"],
        }
        result["checks"] = grade(case, observed)
        set_graded_status(result, agent_run)

      except _Graded:
        pass
      except EvalError as exc:
        # Report the error alongside everything already observed; a bare error
        # string hides how far the run actually got.
        if result.get("error"):
            result["error"] += f"; {exc}"
        else:
            result["error"] = str(exc)

    finally:
        if project_id and not keep:
            # Temporary project deletion is disabled while the target server
            # does not complete the project DELETE request. Keep the project
            # ID only in the private in-memory result for lifecycle tooling;
            # publishable_result strips it from eval-result.json.
            result["temporaryObjectsRemoved"] = False
            result["cleanupDeferred"] = True
        if not keep:
            shutil.rmtree(workspace, ignore_errors=True)
        else:
            result["workspace"] = str(workspace)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", required=True, type=pathlib.Path,
                        help="path to the case JSON")
    parser.add_argument("--result", type=pathlib.Path,
                        help="write the result JSON here as well as to stdout")
    parser.add_argument("--dry-run", action="store_true",
                        help="resolve the case without touching the server")
    parser.add_argument("--keep", action="store_true",
                        help="leave the temporary project and checkout in place for debugging")
    parser.add_argument(
        "--teamcity-token-fd", type=int,
        help="read and close the lifecycle token descriptor before agent execution",
    )
    parser.add_argument("--arm", choices=("skill", "baseline"),
                        default=os.environ.get("EVAL_ARM", "skill"),
                        help="'baseline' withholds the skill, to measure its effect")
    args = parser.parse_args()

    keep = args.keep or os.environ.get("EVAL_KEEP", "") not in ("", "0", "false")
    lifecycle_token = None
    if args.teamcity_token_fd is not None:
        try:
            with os.fdopen(args.teamcity_token_fd, encoding="utf-8") as token_file:
                lifecycle_token = token_file.read().strip()
        except OSError as exc:
            parser.error(f"could not read lifecycle token: {exc}")
        if not lifecycle_token:
            parser.error("lifecycle token descriptor is empty")
    try:
        result = run(args.case, args.dry_run, keep, args.arm, lifecycle_token)
    except EvalError as exc:
        result = {"caseId": args.case.stem, "status": "errored", "error": str(exc)}

    rendered = json.dumps(publishable_result(result), indent=2)
    print(rendered)
    if args.result:
        args.result.write_text(rendered + "\n")

    if result["status"] in ("passed", "dry-run"):
        return 0
    if result["status"] == "failed" and result.get("caseStatus") == "aspirational":
        print(f"\n{result['caseId']} is aspirational; its failure does not gate.", file=sys.stderr)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
