"""Publish completed active-case grader checks as TeamCity tests."""

import json
import os
import re


def safe_check_result(check: dict) -> dict:
    """Keep simple outcomes, never arbitrary grader text or server values."""
    safe = {"passed": check.get("passed")}
    for field in ("expected", "observed"):
        value = check.get(field)
        if field in check and (value is None or type(value) in (bool, int)
                or isinstance(value, str) and re.fullmatch(
                    r"(?:SUCCESS|FAILURE|ERROR|UNKNOWN|CANCELED|none|changed|not-evidenced|\d{1,3}\+?)", value)):
            safe[field] = value
    return safe


def _details(result: dict, check_name: str, check: dict) -> str:
    lines = [f"Check: {check_name}", "Result: " + ("passed" if check["passed"] else "failed")]
    lines.extend(f"{field.capitalize()}: {json.dumps(check[field])}"
                 for field in ("expected", "observed") if field in check)
    verification = result.get("verificationDiagnostics", {})
    context = {}
    if check_name == "configurationValidated":
        context = {key: result[key] for key in ("schemaValidationDiagnostics", "configurationDiagnostics")
                   if result.get(key)}
    elif check_name == "toolchain":
        context = verification.get("jdk", {})
    elif check_name == "firstBuild":
        context = verification.get("terminalChain", {})
    elif check_name in ("testsExecutedAndReported", "requiredTests", "allTestsPassed",
                        "artifactsPublished", "jobResults"):
        context = {key: verification[key] for key in ("testCount", "artifactCount", "builds")
                   if key in verification}
    elif check_name == "evalExecution":
        context = {key: result[key] for key in (
            "errorCategory", "verificationErrorCategory", "agentExitCode", "agentTimedOut",
            "schemaValidationDiagnostics", "configurationDiagnostics", "buildMonitorDiagnostics",
        ) if key in result}
    if context:
        lines.append("Diagnostics:\n" + json.dumps(context, indent=2, sort_keys=True))
    lines.append("Result artifact: publish/eval-result.json")
    return "\n".join(lines) + "\n"


def _message(kind: str, **attributes) -> None:
    def escape(value):
        text = str(value)
        for before, after in (("|", "||"), ("'", "|'"), ("\n", "|n"),
                              ("\r", "|r"), ("[", "|["), ("]", "|]")):
            text = text.replace(before, after)
        return text

    properties = " ".join(f"{key}='{escape(value)}'" for key, value in attributes.items())
    print(f"##teamcity[{kind} {properties}]", flush=True)


def report_checks(result: dict) -> None:
    """Consume only publishable_result output, never raw grader evidence.

    Pipeline jobs cannot disable failure on failed tests. Reporting only active
    cases preserves the runner's non-gating policy for aspirational cases.
    """
    if (not os.environ.get("TEAMCITY_VERSION")
            or result.get("caseStatus") != "active"
            or result.get("status") not in ("passed", "failed", "errored")):
        return

    checks = [
        (name, check)
        for name, check in (result.get("checks") or {}).items()
        if isinstance(check, dict) and type(check.get("passed")) is bool
    ]
    # An agent or infrastructure error may leave checks empty or even passing.
    # Keep that error visible without inventing outcomes for ungraded checks.
    if result["status"] == "errored":
        checks.append(("evalExecution", {"passed": False}))
    if not checks:
        return

    identity = (result["caseId"], result["arm"], result["toolMode"])
    suite = " / ".join(("Eval", *identity))
    _message("testSuiteStarted", name=suite)
    for check_name, check in checks:
        name = ".".join(("eval", *identity, check_name))
        _message("testStarted", name=name)
        details = _details(result, check_name, check)
        _message("testStdOut", name=name, out=details)
        if not check["passed"]:
            _message(
                "testFailed", name=name,
                message=("Evaluation execution failed" if check_name == "evalExecution"
                         else f"Grader check {check_name} did not satisfy the case contract"),
                details=details,
            )
        _message("testFinished", name=name)
    _message("testSuiteFinished", name=suite)
