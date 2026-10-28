"""Schema regressions using synthetic YAML, CLI output and build chains only."""

import contextlib
import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import jsonschema
import yaml

EVALS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS))
from pipeline_validation import PipelineSchemaError, pipeline_schema_result

spec = importlib.util.spec_from_file_location("schema_runner", EVALS / "run_case.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
import collect_teamcity_eval_runs as collector


def document(feature="xml-report"):
    return {
        "jobs": {"Verify": {
            "parameters": {"env.JAVA_HOME": "/jdk-21"},
            "steps": [{"type": "maven", "goals": "clean verify"}],
            "features": [{"type": feature, "report-type": "junit",
                          "rules": "target/surefire-reports/*.xml"}],
        }},
    }


# Only the feature enum matters to this regression. This is a synthetic server
# schema, not a replacement for the real CLI's complete target-server schema.
SCHEMA = {
    "properties": {
        "jobs": {
            "additionalProperties": {
                "properties": {
                    "features": {"items": {"properties": {"type": {"enum": ["xml-report"]}}}},
                },
            },
        },
    },
}


def validator(arguments):
    assert arguments[:2] == ["pipeline", "validate"]
    assert arguments[3:] == ["--refresh-schema"]
    path = pathlib.Path(arguments[2])
    actual = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors = list(jsonschema.Draft202012Validator(SCHEMA).iter_errors(actual))
    if not errors:
        return subprocess.CompletedProcess(arguments, 0, stdout=f"{path} is valid\n", stderr="")
    return subprocess.CompletedProcess(arguments, 1, stdout="", stderr=(
        f"\x1b[31mX\x1b[0m {path} has 1 error(s)\n\n"
        "  Line 12: /jobs/Verify/features/0/type\n"
        '    value must be one of "xml-report"; private-canary\n\n'
    ))


class PipelineSchemaTest(unittest.TestCase):
    def test_validates_exact_saved_yaml_with_target_server_and_fresh_schema(self):
        tc = runner.TeamCity("teamcity", "https://target.invalid", "private-token", {
            "TEAMCITY_URL": "https://other.invalid", "TEAMCITY_GUEST": "1",
        })
        text = yaml.safe_dump(document(), sort_keys=False) + "# preserve this comment\n"
        paths = []

        def execute(arguments, **kwargs):
            self.assertEqual("teamcity", arguments[0])
            self.assertEqual("https://target.invalid", kwargs["env"]["TEAMCITY_URL"])
            self.assertEqual("private-token", kwargs["env"]["TEAMCITY_TOKEN"])
            self.assertNotIn("TEAMCITY_GUEST", kwargs["env"])
            path = pathlib.Path(arguments[3])
            paths.append(path)
            self.assertEqual(text, path.read_text(encoding="utf-8"))
            return validator(arguments[1:])

        with mock.patch.object(tc, "pipeline", return_value={"yaml": text}) as pull, \
                mock.patch.object(runner.subprocess, "run", side_effect=execute):
            result = tc.validate_pipeline("selected", document())
        pull.assert_called_once_with("selected")
        self.assertEqual("valid", result["status"])
        self.assertFalse(paths[0].exists())

    def test_changed_server_yaml_is_not_the_selected_configuration(self):
        tc = runner.TeamCity("teamcity", "https://target.invalid", "private", {})
        with mock.patch.object(tc, "pipeline", return_value={"yaml": yaml.safe_dump(document("junit"))}), \
                mock.patch.object(tc, "_execute") as command:
            with self.assertRaises(runner.EvidenceError):
                tc.validate_pipeline("selected", document())
        command.assert_not_called()

    def test_single_value_enum_report_from_cli_1_3_is_preserved_without_values(self):
        result = subprocess.CompletedProcess([], 1, "", (
            "x pipeline.yml has 1 error(s)\n\n"
            "  Line 8: /jobs/private-canary/features/0/type\n"
            "    value must be 'xml-report'\n\n"
        ))
        with self.assertRaises(PipelineSchemaError) as raised:
            pipeline_schema_result(result, "pipeline.yml")
        self.assertEqual({"status": "invalid", "errorCount": 1, "issues": [
            {"line": 8, "category": "invalid-enum-value"},
        ]}, raised.exception.diagnostics)
        self.assertNotIn("private", json.dumps(raised.exception.diagnostics))

    def test_schema_cli_and_schema_download_errors_cannot_pass(self):
        tc = runner.TeamCity("teamcity", "https://target.invalid", "private", {})
        for error in (OSError("private-canary"), subprocess.TimeoutExpired("private-canary", 1)):
            with self.subTest(error=type(error).__name__), \
                    mock.patch.object(tc, "pipeline", return_value={"yaml": yaml.safe_dump(document())}), \
                    mock.patch.object(runner.subprocess, "run", side_effect=error):
                with self.assertRaises(PipelineSchemaError) as raised:
                    tc.validate_pipeline("selected", document())
                self.assertEqual("unavailable", raised.exception.diagnostics["status"])
                self.assertNotIn("private", str(raised.exception))
        for code, message in ((1, "failed to fetch schema: private-canary"),
                              (1, "unknown flag: --refresh-schema"),
                              (1, "failed to compile schema"), (2, "unknown command")):
            with self.subTest(message=message), self.assertRaises(PipelineSchemaError) as raised:
                pipeline_schema_result(subprocess.CompletedProcess([], code, "", message), "pipeline.yml")
            self.assertEqual("unavailable", raised.exception.diagnostics["status"])

    def run_evaluation(self, feature="xml-report", kind="first-green-build", unavailable=False,
                       timed_out=False, *, final_updates=None, build_state="complete",
                       server_changes_after_validation=None, expected_validations=1):
        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as stack:
            source = document(feature)
            case = {
                "id": "synthetic", "kind": kind, "prompt": "Set up CI",
                "repository": {"defaultBranch": "main"},
                "requestedConfiguration": {"format": "yaml", "sourcePath": ".teamcity.yml"},
                "verification": {"artifactPaths": ["target/*.jar"]},
                "expected": {"configurationValidated": True, "minimumJobs": 1,
                    "testsExecutedAndReported": True, "artifactsPublished": True,
                    "sourceMutations": "none", "toolchain": {"jdk": "21"}, "firstBuild": "SUCCESS"},
            }
            case_path = pathlib.Path(directory) / "case.json"
            case_path.write_text(json.dumps(case))
            tc = runner.TeamCity("teamcity", "https://target.invalid", "private-token", {})
            tree = {"id": 1, "buildTypeId": "selected", "state": "finished", "status": "SUCCESS",
                    "dependencies": [{"id": 2, "buildTypeId": "child", "state": "finished",
                                      "status": "SUCCESS", "dependencies": []}]}
            if build_state == "head-only":
                tree.update(status="FAILURE", dependencies=[])
            for name, value in (
                ("create_project", "project"), ("mark_temporary_project", None),
                ("pipeline_ids", ["selected", "probe"]), ("build_types", [{"id": "selected"}]),
                ("builds", [] if build_state == "not-queued" else
                    [{"id": 1, "buildTypeId": "selected", "status": "SUCCESS"}]),
                ("build_tree", tree),
                ("build", {"id": 2, "buildTypeId": "child", "state": "finished", "status": "SUCCESS",
                           "buildType": {"name": "Verify"}}),
                ("test_results", [{"name": "Example.test", "status": "SUCCESS", "ignored": False}]),
                ("artifacts", ["app.jar"]),
            ):
                stack.enter_context(mock.patch.object(tc, name, return_value=value))
            probe = {"jobs": {"Probe": {"features": [{"type": "invalid-probe"}]}}}

            def saved_pipeline(key):
                saved = source if key == "selected" else probe
                if key == "selected" and command.call_count and server_changes_after_validation:
                    saved = {**saved, **server_changes_after_validation}
                return {"yaml": yaml.safe_dump(saved, sort_keys=False)}

            stack.enter_context(mock.patch.object(tc, "pipeline", side_effect=saved_pipeline))
            command = stack.enter_context(mock.patch.object(tc, "_execute", side_effect=(
                lambda args: subprocess.CompletedProcess(args, 1, "", "failed to download schema: private-canary")
            ) if unavailable else validator))

            def checkout(_case, path):
                path.mkdir(parents=True, exist_ok=True)
                (path / ".teamcity.yml").write_text(yaml.safe_dump({**source, **(final_updates or {})}))

            bridge = mock.MagicMock()
            bridge.__enter__.return_value.agent_environment.return_value = {}
            stack.enter_context(mock.patch.dict(runner.os.environ, {
                "TEAMCITY_URL": "https://target.invalid", "TEAMCITY_TOKEN": "private-token",
            }, clear=True))
            stack.enter_context(mock.patch.object(runner, "TeamCity", return_value=tc))
            stack.enter_context(mock.patch.object(runner, "TeamCityCliBridge", return_value=bridge))
            stack.enter_context(mock.patch.object(runner.shutil, "which", return_value="teamcity"))
            stack.enter_context(mock.patch.object(runner, "checkout_repository", side_effect=checkout))
            stack.enter_context(mock.patch.object(runner, "harness_revision", return_value="a" * 40))
            stack.enter_context(mock.patch.object(runner.sys, "stderr", io.StringIO()))
            if build_state == "not-queued":
                clock = [0]
                stack.enter_context(mock.patch.object(runner.time, "time", side_effect=lambda: clock[0]))
                stack.enter_context(mock.patch.object(runner.time, "sleep", side_effect=
                    lambda seconds: clock.__setitem__(0, clock[0] + seconds)))
            for name, value in (("agent_usage", {}), ("trace_error_category", None),
                                ("permission_failure_surface", None), ("agent_tool_summary", {}),
                                ("source_mutations", []), ("tool_calls", [])):
                stack.enter_context(mock.patch.object(runner, name, return_value=value))
            # The synthetic agent never calls a validator. Only the grader can
            # make the CLI call observed by this test.
            stack.enter_context(mock.patch.object(runner, "invoke_agent", return_value={
                "exitCode": 124 if timed_out else 0, "timedOut": timed_out, "timeoutSeconds": 3600,
            }))
            result = runner.publishable_result(runner.run(case_path, False, False, "baseline", "cli-only"))
            self.assertEqual(expected_validations, command.call_count)
            if kind == "pipeline-configuration" or feature == "junit" or unavailable or final_updates:
                tc.builds.assert_not_called()
                tc.build_tree.assert_not_called()
            self.assertNotIn("private", json.dumps(result))
            return result

    def test_valid_xml_report_passes_in_both_live_case_kinds(self):
        for kind in ("first-green-build", "pipeline-configuration"):
            with self.subTest(kind=kind):
                result = self.run_evaluation(kind=kind)
                self.assertEqual("passed", result["status"])
                self.assertTrue(result["checks"]["configurationValidated"]["passed"])
                self.assertEqual("valid", result["schemaValidationDiagnostics"]["status"])

    def test_unsupported_junit_feature_fails_even_with_green_build(self):
        for kind in ("first-green-build", "pipeline-configuration"):
            with self.subTest(kind=kind):
                result = self.run_evaluation("junit", kind)
                self.assertEqual("failed", result["status"])
                self.assertFalse(result["checks"]["configurationValidated"]["passed"])
                self.assertEqual({"status": "invalid", "errorCount": 1, "issues": [
                    {"line": 12, "category": "invalid-enum-value"},
                ]}, result["schemaValidationDiagnostics"])

    def test_final_yaml_root_mismatch_cannot_pass_either_case_kind(self):
        for kind in ("first-green-build", "pipeline-configuration"):
            with self.subTest(kind=kind):
                result = self.run_evaluation(kind=kind, final_updates={"version": 999}, expected_validations=0)
                self.assertEqual("errored", result["status"])
                self.assertEqual("verification-pipeline-ambiguous", result["verificationErrorCategory"])
                self.assertNotIn("gradeStatus", result)

    def test_invalid_yaml_is_graded_without_a_complete_or_queued_build(self):
        for state in ("head-only", "not-queued"):
            with self.subTest(state=state):
                result = self.run_evaluation("junit", build_state=state)
                self.assertEqual("failed", result["status"])
                self.assertFalse(result["checks"]["configurationValidated"]["passed"])
                self.assertEqual("invalid", result["schemaValidationDiagnostics"]["status"])
                self.assertEqual("verification-invalid-pipeline-yaml", result["verificationErrorCategory"])

    def test_changed_server_yaml_after_validation_is_not_graded(self):
        result = self.run_evaluation(server_changes_after_validation={"version": 999})
        self.assertEqual("errored", result["status"])
        self.assertEqual("verification-pipeline-ambiguous", result["verificationErrorCategory"])
        self.assertNotIn("gradeStatus", result)

    def test_unavailable_validation_is_an_error_not_a_failed_agent_grade(self):
        result = self.run_evaluation(unavailable=True)
        self.assertEqual("errored", result["status"])
        self.assertEqual("verification-schema-validation-unavailable", result["errorCategory"])
        self.assertEqual("unavailable", result["schemaValidationDiagnostics"]["status"])
        self.assertNotIn("gradeStatus", result)
        outcome, _ = collector.classify(None, {"state": "finished", "status": "FAILURE"}, result)
        self.assertEqual("verification-schema-validation-unavailable", outcome)

    def test_schema_failure_does_not_hide_an_agent_timeout(self):
        result = self.run_evaluation("junit", timed_out=True)
        self.assertEqual("errored", result["status"])
        self.assertEqual("agent-timeout", result["errorCategory"])
        self.assertEqual("failed", result["gradeStatus"])
        self.assertEqual("verification-invalid-pipeline-yaml", result["verificationErrorCategory"])

    def test_graders_require_schema_validation_evidence(self):
        jobs = [{"name": "Verify", "steps": [], "artifactRules": "", "agentRequirements": []}]
        case = {"expected": {"minimumJobs": 1, "sourceMutations": "none"}}
        runtime_case = {"expected": {"configurationValidated": True, "testsExecutedAndReported": True,
            "artifactsPublished": True, "sourceMutations": "none", "toolchain": {"jdk": "21"},
            "firstBuild": "SUCCESS"}, "verification": {"artifactPaths": []}}
        for value in (None, False, "true", True):
            with self.subTest(value=value):
                checks = runner.grade_configuration(case, {"jobs": jobs, "mutations": [],
                                                           "schemaValidated": value})
                self.assertEqual(value is True, checks["configurationValidated"]["passed"])
                runtime = runner.grade(runtime_case, {"jobs": jobs, "schemaValidated": value,
                    "buildTypeCount": 1, "buildStatus": "SUCCESS", "attempts": 1,
                    "testCount": 1, "artifacts": [], "properties": {}, "mutations": []})
                self.assertEqual(value is True, runtime["configurationValidated"]["passed"])

    def test_collector_keeps_only_safe_validation_diagnostics(self):
        artifact = self.run_evaluation("junit")
        artifact["schemaValidationDiagnostics"].update(output="private-canary")
        artifact["schemaValidationDiagnostics"]["issues"][0].update(path="private-canary")

        def cli(_server, *arguments):
            if arguments[1] == "artifacts":
                return subprocess.CompletedProcess([], 0, json.dumps({"file": [{"name": "eval-result.json"}]}))
            destination = pathlib.Path(arguments[arguments.index("--output") + 1])
            (destination / "eval-result.json").write_text(json.dumps(artifact))
            return subprocess.CompletedProcess([], 0, "")

        with mock.patch.object(collector, "cli", side_effect=cli):
            result = collector.download_result([], "https://example.invalid", 42, {"synthetic"})
        self.assertEqual("invalid", result["schemaValidationDiagnostics"]["status"])
        self.assertNotIn("private", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
