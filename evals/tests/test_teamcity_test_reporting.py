import contextlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock


EVALS = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_case_reporting_test", EVALS / "run_case.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def result(**updates):
    value = {
        "caseId": "spring-petclinic-maven-yaml",
        "caseStatus": "active",
        "arm": "skill",
        "toolMode": "cli-only",
        "status": "passed",
        "checks": {"configurationValidated": {"passed": True}},
    }
    value.update(updates)
    return value


class TeamCityTestReportingTest(unittest.TestCase):
    def report(self, value, teamcity=True):
        output = io.StringIO()
        with mock.patch.dict(runner.os.environ, {"TEAMCITY_VERSION": "2026.3"} if teamcity else {}, clear=True), \
                contextlib.redirect_stdout(output):
            runner.report_checks(value)
        return output.getvalue()

    def test_main_preserves_exit_codes_public_artifact_and_gating_policy(self):
        scenarios = (
            ("active", "passed", {"toolchain": {"passed": True}}, 0, 1, 0),
            ("active", "failed", {"toolchain": {"passed": False}}, 1, 1, 1),
            ("active", "errored", {"toolchain": {"passed": True}}, 1, 2, 1),
            ("active", "errored", {}, 1, 1, 1),
            ("aspirational", "passed", {"toolchain": {"passed": True}}, 0, 0, 0),
            ("aspirational", "failed", {"toolchain": {"passed": False}}, 0, 0, 0),
            ("aspirational", "errored", {"toolchain": {"passed": False}}, 1, 0, 0),
            ("draft", "failed", {"toolchain": {"passed": False}}, 1, 0, 0),
            ("active", "dry-run", {}, 0, 0, 0),
        )
        for case_status, status, checks, exit_code, test_count, failed_count in scenarios:
            with self.subTest(case_status=case_status, status=status, checks=checks), \
                    tempfile.TemporaryDirectory() as directory:
                raw = result(caseStatus=case_status, status=status, checks=checks)
                raw["agentOutput"] = "private-agent-output"
                for check in checks.values():
                    check["detail"] = "private-build-log"
                expected_public = runner.publishable_result(raw)
                destination = pathlib.Path(directory) / "eval-result.json"
                output = io.StringIO()
                with mock.patch.dict(runner.os.environ, {"TEAMCITY_VERSION": "2026.3"}, clear=True), \
                        mock.patch.object(runner.sys, "argv", [
                            "run_case.py", "--case", "case.json", "--result", str(destination),
                        ]), mock.patch.object(runner, "run", return_value=raw) as run, \
                        contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(exit_code, runner.main())
                run.assert_called_once()
                self.assertEqual(expected_public, json.loads(destination.read_text()))
                text = output.getvalue()
                self.assertEqual(test_count, text.count("##teamcity[testStarted "))
                self.assertEqual(test_count, text.count("##teamcity[testFinished "))
                self.assertEqual(failed_count, text.count("##teamcity[testFailed "))
                self.assertNotIn("private-agent-output", text)
                self.assertNotIn("private-build-log", text)
                if status == "errored" and case_status == "active":
                    self.assertIn(
                        "testFailed name='eval.spring-petclinic-maven-yaml.skill.cli-only.evalExecution'",
                        text,
                    )

    def test_other_cases_and_contract_checks_are_reported_with_separate_histories(self):
        suites = set()
        for arm in ("skill", "baseline"):
            for mode in runner.TOOL_MODES:
                with self.subTest(arm=arm, mode=mode):
                    text = self.report(result(arm=arm, toolMode=mode, status="failed", checks={
                        "configurationValidated": {"passed": True},
                        "customContractRule": {"passed": False},
                    }))
                    suite = text.splitlines()[0]
                    self.assertIn(f"Eval / spring-petclinic-maven-yaml / {arm} / {mode}", suite)
                    suites.add(suite)
                    self.assertEqual(2, text.count("##teamcity[testStarted "))
                    self.assertIn(
                        f"testFailed name='eval.spring-petclinic-maven-yaml.{arm}.{mode}.customContractRule'",
                        text,
                    )
        self.assertEqual(6, len(suites))

    def test_ungraded_checks_are_not_reported_as_passed(self):
        text = self.report(result(checks={
            "missing": {}, "unknown": {"passed": None}, "integer": {"passed": 1},
            "text": {"passed": "true"}, "invalid": "not a check",
        }))
        self.assertEqual("", text)

    def test_service_message_values_cannot_inject_commands_or_new_lines(self):
        text = self.report(result(
            caseId="case']\n##teamcity[buildStatus status='SUCCESS']",
            status="failed", checks={"rule|'\r\n[]": {"passed": False}},
        ))
        self.assertEqual(5, len(text.splitlines()))
        self.assertIn(".skill.cli-only.rule|||'|r|n|[|]'", text)
        self.assertNotIn("##teamcity[buildStatus", text)
        self.assertIn("##teamcity|[buildStatus", text)

    def test_local_output_stays_json_only(self):
        self.assertEqual("", self.report(result(status="failed"), teamcity=False))
        output = io.StringIO()
        with mock.patch.dict(runner.os.environ, {}, clear=True), \
                mock.patch.object(runner.sys, "argv", ["run_case.py", "--case", "case.json"]), \
                mock.patch.object(runner, "run", return_value=result()), \
                contextlib.redirect_stdout(output):
            self.assertEqual(0, runner.main())
        self.assertEqual(runner.publishable_result(result()), json.loads(output.getvalue()))


if __name__ == "__main__":
    unittest.main()
