#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema>=4.23"]
# ///
"""Static validation for TeamCitySkills evaluation cases.

Checks every case under evals/<kind>/cases/*.json against evals/schema.json,
plus the repository conventions that JSON Schema cannot express.

Usage:
    uv run evals/validate.py           # or: pipx run evals/validate.py
    python3 evals/validate.py          # inside a virtualenv holding jsonschema
"""

import json
import pathlib
import sys
from typing import Dict, List

try:
    import jsonschema
except ImportError:
    sys.exit("jsonschema is not installed: pip install jsonschema")

EVALS = pathlib.Path(__file__).parent
SCHEMA = EVALS / "schema.json"

errors: List[str] = []


def fail(case: pathlib.Path, message: str) -> None:
    errors.append(f"{case.relative_to(EVALS.parent)}: {message}")


def baseline_shortfalls(case: Dict) -> List[str]:
    """Ways in which the recorded observedBaseline falls short of the expected contract.

    Empty for a case with no observedBaseline: an unmeasured case is not known to fail.
    """
    truth = case.get("observedBaseline")
    if not truth:
        return []

    expected = case.get("expected", {})
    gaps: List[str] = []

    if expected.get("configurationValidated") and truth.get("configuration") != "accepted-by-server":
        gaps.append(f"configuration {truth.get('configuration')!r}")

    if truth.get("overallBuild") != expected.get("firstBuild"):
        gaps.append(f"overall build {truth.get('overallBuild')!r} != {expected.get('firstBuild')!r}")

    if expected.get("testsExecutedAndReported"):
        tests = truth.get("testReporting", {})
        if tests.get("observed", 0) < tests.get("expected", 0):
            gaps.append(f"tests reported {tests.get('observed')}/{tests.get('expected')}")

    if expected.get("artifactsPublished"):
        artifacts = truth.get("artifactPublication", {})
        if artifacts.get("observed", 0) < artifacts.get("expected", 0):
            gaps.append(f"artifacts published {artifacts.get('observed')}/{artifacts.get('expected')}")

    if expected.get("sourceMutations") == "none" and truth.get("sourceFidelity") != "exact":
        gaps.append(f"source fidelity {truth.get('sourceFidelity')!r}")

    observed = {t["id"]: t for t in truth.get("targets", [])}
    for target in expected.get("targets", []):
        actual = observed.get(target["id"])
        if actual is None:
            continue
        if actual.get("status") != target.get("status"):
            gaps.append(f"target {target['id']!r} status {actual.get('status')!r}")
        if target.get("tests") == "reported" and not actual.get("testsReported"):
            gaps.append(f"target {target['id']!r} reported no tests")
        if target.get("artifactPaths") and not actual.get("artifactsPublished"):
            gaps.append(f"target {target['id']!r} published no artifacts")

    return gaps


def check_conventions(path: pathlib.Path, case: dict) -> None:
    """Repository rules that draft-07 cannot state."""
    case_id = case.get("id")

    if path.stem != case_id:
        fail(path, f"filename does not match id {case_id!r}")

    kind_dir = path.parent.parent.name
    if kind_dir != case.get("kind"):
        fail(path, f"lives under {kind_dir!r} but declares kind {case.get('kind')!r}")

    expected = case.get("expected", {})
    verification = case.get("verification", {})

    # expected.targets and observedBaseline.targets must describe the same targets.
    expected_ids = {t["id"] for t in expected.get("targets", [])}
    truth_ids = {t["id"] for t in case.get("observedBaseline", {}).get("targets", [])}
    if truth_ids and expected_ids != truth_ids:
        fail(path, f"observedBaseline targets {sorted(truth_ids)} != expected targets {sorted(expected_ids)}")

    # Per-target artifact paths must be covered by the case-level artifact list.
    declared = set(verification.get("artifactPaths", []))
    for target in expected.get("targets", []):
        stray = set(target.get("artifactPaths", [])) - declared
        if stray:
            fail(path, f"target {target['id']!r} lists artifact paths absent from verification.artifactPaths: {sorted(stray)}")

    # The gating status must match what the recorded baseline actually achieved,
    # so that a known-failing case cannot sit in CI labelled as a regression.
    status = case.get("status", "active")
    gaps = baseline_shortfalls(case)
    if gaps and status != "aspirational":
        fail(path, f"status is {status!r} but observedBaseline falls short of expected: {'; '.join(gaps)}")
    if not gaps and status == "aspirational" and case.get("observedBaseline"):
        fail(path, "status is 'aspirational' but observedBaseline meets the expected contract; mark it 'active'")

    # A case must never pin a concrete server; the runner supplies it.
    teamcity = case.get("teamcity", {})
    for field, value in teamcity.items():
        if value != "runner-configured":
            fail(path, f"teamcity.{field} pins {value!r}; cases must stay environment-agnostic")


def main() -> int:
    schema = json.loads(SCHEMA.read_text())
    jsonschema.Draft7Validator.check_schema(schema)
    validator = jsonschema.Draft7Validator(schema)

    cases = sorted(EVALS.glob("*/cases/*.json"))
    if not cases:
        sys.exit("no evaluation cases found")

    seen: Dict[str, pathlib.Path] = {}

    for path in cases:
        try:
            case = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            fail(path, f"invalid JSON: {exc}")
            continue

        for error in sorted(validator.iter_errors(case), key=str):
            location = "/".join(str(part) for part in error.absolute_path) or "<root>"
            fail(path, f"{location}: {error.message}")

        case_id = case.get("id")
        if case_id in seen:
            fail(path, f"duplicate id {case_id!r}, already used by {seen[case_id].name}")
        elif case_id:
            seen[case_id] = path

        check_conventions(path, case)

    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)

    print(f"{len(cases)} case(s) checked, {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
