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


# Replay CLI responses; schema validation itself belongs to the CLI.
def cli_result(arguments, status):
    path = arguments[2]
    if status == "valid":
        return subprocess.CompletedProcess(arguments, 0, stdout=f"{path} is valid\n", stderr="")
    if status == "unavailable":
        return subprocess.CompletedProcess(arguments, 1, "", "failed to download schema: private-canary")
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

        def execute(arguments, **kwargs):
            self.assertEqual("teamcity", arguments[0])
            self.assertEqual(["pipeline", "validate"], arguments[1:3])
            self.assertEqual(["--refresh-schema"], arguments[4:])
            self.assertEqual("https://target.invalid", kwargs["env"]["TEAMCITY_URL"])
            self.assertEqual("private-token", kwargs["env"]["TEAMCITY_TOKEN"])
            self.assertNotIn("TEAMCITY_GUEST", kwargs["env"])
            path = pathlib.Path(arguments[3])
            self.assertEqual(text, path.read_text(encoding="utf-8"))
            return cli_result(arguments[1:], "valid")

        with mock.patch.object(tc, "pipeline", return_value={"yaml": text}) as pull, \
                mock.patch.object(runner.subprocess, "run", side_effect=execute):
            result = tc.validate_pipeline("selected", document())
        pull.assert_called_once_with("selected")
        self.assertEqual("valid", result["status"])

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
                              (2, "x pipeline.yml has 1 error(s)\n")):
            with self.subTest(message=message), self.assertRaises(PipelineSchemaError) as raised:
                pipeline_schema_result(subprocess.CompletedProcess([], code, "", message), "pipeline.yml")
            self.assertEqual("unavailable", raised.exception.diagnostics["status"])

    def run_evaluation(self, feature="xml-report", kind="first-green-build", unavailable=False,
                       timed_out=False, *, final_updates=None, server_changes_during_wait=None):
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
            for name, value in (
                ("create_project", "project"), ("mark_temporary_project", None),
                ("pipeline_ids", ["selected", "probe"]), ("build_types", [{"id": "selected"}]),
                ("builds", [{"id": 1, "buildTypeId": "selected", "status": "SUCCESS"}]),
                ("build", {"id": 2, "buildTypeId": "child", "state": "finished", "status": "SUCCESS",
                           "buildType": {"name": "Verify"}}),
                ("test_results", [{"name": "Example.test", "status": "SUCCESS", "ignored": False}]),
                ("artifacts", ["app.jar"]),
            ):
                stack.enter_context(mock.patch.object(tc, name, return_value=value))
            probe = {"jobs": {"Probe": {"features": [{"type": "invalid-probe"}]}}}

            def saved_pipeline(key):
                saved = source if key == "selected" else probe
                return {"yaml": yaml.safe_dump(saved, sort_keys=False)}

            def build_tree(_head_id):
                source.update(server_changes_during_wait or {})
                return tree

            stack.enter_context(mock.patch.object(tc, "pipeline", side_effect=saved_pipeline))
            stack.enter_context(mock.patch.object(tc, "build_tree", side_effect=build_tree))
            status = "unavailable" if unavailable else "invalid" if feature == "junit" else "valid"
            stack.enter_context(mock.patch.object(tc, "_execute", side_effect=lambda args: cli_result(args, status)))

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
            self.assertNotIn("private", json.dumps(result))
            return result, (tc.builds, tc.build_tree)

    def test_valid_xml_report_passes_in_both_live_case_kinds(self):
        for kind in ("first-green-build", "pipeline-configuration"):
            with self.subTest(kind=kind):
                result, build_reads = self.run_evaluation(kind=kind)
                self.assertEqual("passed", result["status"])
                self.assertTrue(result["checks"]["configurationValidated"]["passed"])
                self.assertEqual("valid", result["schemaValidationDiagnostics"]["status"])
                if kind == "pipeline-configuration":
                    for read in build_reads:
                        read.assert_not_called()

    def test_unsupported_junit_feature_fails_before_polling_builds(self):
        for kind in ("first-green-build", "pipeline-configuration"):
            with self.subTest(kind=kind):
                result, build_reads = self.run_evaluation("junit", kind)
                self.assertEqual("failed", result["status"])
                self.assertFalse(result["checks"]["configurationValidated"]["passed"])
                self.assertEqual({"status": "invalid", "errorCount": 1, "issues": [
                    {"line": 12, "category": "invalid-enum-value"},
                ]}, result["schemaValidationDiagnostics"])
                for read in build_reads:
                    read.assert_not_called()

    def test_final_yaml_root_mismatch_cannot_pass_either_case_kind(self):
        for kind in ("first-green-build", "pipeline-configuration"):
            with self.subTest(kind=kind):
                result, _ = self.run_evaluation(kind=kind, final_updates={"version": 999})
                self.assertEqual("errored", result["status"])
                self.assertEqual("verification-pipeline-ambiguous", result["verificationErrorCategory"])
                self.assertNotIn("gradeStatus", result)

    def test_changed_server_yaml_after_validation_is_not_graded(self):
        result, _ = self.run_evaluation(server_changes_during_wait={"version": 999})
        self.assertEqual("errored", result["status"])
        self.assertEqual("verification-pipeline-ambiguous", result["verificationErrorCategory"])
        self.assertNotIn("gradeStatus", result)

    def test_unavailable_validation_is_an_error_not_a_failed_agent_grade(self):
        result, _ = self.run_evaluation(unavailable=True)
        self.assertEqual("errored", result["status"])
        self.assertEqual("verification-schema-validation-unavailable", result["errorCategory"])
        self.assertEqual("unavailable", result["schemaValidationDiagnostics"]["status"])
        self.assertNotIn("gradeStatus", result)
        outcome, _ = collector.classify(None, {"state": "finished", "status": "FAILURE"}, result)
        self.assertEqual("verification-schema-validation-unavailable", outcome)

    def test_schema_failure_does_not_hide_an_agent_timeout(self):
        result, _ = self.run_evaluation("junit", timed_out=True)
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

    def test_publisher_and_collector_keep_only_safe_validation_diagnostics(self):
        expected = {"status": "invalid", "errorCount": 1,
                    "issues": [{"line": 12, "category": "invalid-enum-value"}]}
        artifact = {"caseId": "synthetic", "status": "failed", "schemaValidationDiagnostics": {
            **expected, "output": "private-canary",
            "issues": [{**expected["issues"][0], "path": "private-canary"}],
        }}
        published = runner.publishable_result(artifact)
        self.assertEqual(expected, published["schemaValidationDiagnostics"])

        def cli(_server, *arguments):
            if arguments[1] == "artifacts":
                return subprocess.CompletedProcess([], 0, json.dumps({"file": [{"name": "eval-result.json"}]}))
            destination = pathlib.Path(arguments[arguments.index("--output") + 1])
            (destination / "eval-result.json").write_text(json.dumps(artifact))
            return subprocess.CompletedProcess([], 0, "")

        with mock.patch.object(collector, "cli", side_effect=cli):
            result = collector.download_result([], "https://example.invalid", 42, {"synthetic"})
        self.assertEqual(expected, result["schemaValidationDiagnostics"])
        self.assertNotIn("private", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
