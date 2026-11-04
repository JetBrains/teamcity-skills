"""Publish completed active-case grader checks as TeamCity tests."""

import os


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
        (name, check["passed"])
        for name, check in (result.get("checks") or {}).items()
        if isinstance(check, dict) and type(check.get("passed")) is bool
    ]
    # An agent or infrastructure error may leave checks empty or even passing.
    # Keep that error visible without inventing outcomes for ungraded checks.
    if result["status"] == "errored":
        checks.append(("evalExecution", False))
    if not checks:
        return

    identity = (result["caseId"], result["arm"], result["toolMode"])
    suite = " / ".join(("Eval", *identity))
    _message("testSuiteStarted", name=suite)
    for check_name, passed in checks:
        name = ".".join(("eval", *identity, check_name))
        _message("testStarted", name=name)
        if not passed:
            _message(
                "testFailed", name=name,
                message=("Evaluation execution failed" if check_name == "evalExecution"
                         else f"Grader check {check_name} did not satisfy the case contract"),
                details="See publish/eval-result.json for the result and sanitized diagnostics.",
            )
        _message("testFinished", name=name)
    _message("testSuiteFinished", name=suite)
