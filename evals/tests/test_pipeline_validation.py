"""Synthetic script-source regressions; never load agent logs or trajectories."""

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

EVALS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS))
from pipeline_validation import (
    ScriptConfigurationError, script_step_diagnostics, validate_pipeline_scripts,
)
from teamcity_cli_bridge import TeamCityCliBridge

spec = importlib.util.spec_from_file_location("script_validation_runner", EVALS / "run_case.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
import collect_teamcity_eval_runs as collector


def definition(properties):
    return {"jobs": {"verify": {"steps": [{"type": "script", **properties}]}}}


class PipelineScriptValidationTest(unittest.TestCase):
    def test_nonempty_inline_and_file_sources_are_supported(self):
        for properties in ({"script-content": "echo synthetic"},
                           {"script-file": "ci/verify.sh"},
                           {"script-file": "ci/verify.sh", "script-content": ""}):
            with self.subTest(properties=properties):
                diagnostics = validate_pipeline_scripts(definition(properties))
                self.assertEqual(1, diagnostics["checkedScriptStepCount"])
                self.assertEqual([], diagnostics["issues"])

    def test_wrong_alias_missing_blank_and_nonstring_sources_fail(self):
        for properties, category in (
            ({"script": "private-canary"}, "unsupported-script-key"),
            ({"script": "private-canary", "script-content": "echo ok"}, "unsupported-script-key"),
            ({}, "missing-script-source"),
            ({"script-content": " \n\t"}, "missing-script-source"),
            ({"script-file": " "}, "missing-script-source"),
            ({"script-content": None}, "invalid-script-source-type"),
            ({"script-content": ["private-canary"]}, "invalid-script-source-type"),
            ({"script-file": 42}, "invalid-script-source-type"),
            ({"script-content": "echo ok", "script-file": "ci/verify.sh"}, "conflicting-script-sources"),
        ):
            with self.subTest(category=category, properties=properties):
                with self.assertRaises(ScriptConfigurationError) as raised:
                    validate_pipeline_scripts(definition(properties))
                self.assertEqual(category, raised.exception.diagnostics["issues"][0]["category"])
                self.assertNotIn("private-canary", str(raised.exception))

    def test_all_eight_scripts_in_three_jobs_are_checked(self):
        document = {"jobs": {
            str(index): {"steps": [{"type": "maven", "goals": "verify"}] +
                        [{"type": "script", "script": "private-canary"}] * count}
            for index, count in enumerate((2, 3, 3))
        }}
        with self.assertRaises(ScriptConfigurationError) as raised:
            validate_pipeline_scripts(document)
        diagnostics = raised.exception.diagnostics
        self.assertEqual(8, diagnostics["checkedScriptStepCount"])
        self.assertEqual(8, diagnostics["invalidScriptStepCount"])
        self.assertEqual({1, 2, 3}, {issue["jobIndex"] for issue in diagnostics["issues"]})
        self.assertEqual(2, diagnostics["issues"][0]["stepIndex"])
        self.assertNotIn("private-canary", json.dumps(diagnostics))

    def test_native_runners_are_not_reinterpreted_as_scripts(self):
        document = {"jobs": {"verify": {"steps": [
            {"type": "maven", "goals": "verify"}, {"type": "gradle", "tasks": "test"},
        ]}}}
        self.assertEqual(0, validate_pipeline_scripts(document)["checkedScriptStepCount"])

    def test_adapter_and_raw_validation_agree(self):
        tc = runner.TeamCity("teamcity", "https://example.invalid", "private", {})
        raw = definition({"script": "private-canary"})
        with mock.patch.object(tc, "pipeline_definition", return_value=raw):
            jobs = tc.jobs("project", "pipeline")
        with self.assertRaises(ScriptConfigurationError) as raised:
            validate_pipeline_scripts(raw)
        self.assertEqual(raised.exception.diagnostics, script_step_diagnostics(jobs))

    def test_pre_wait_gate_does_not_poll_or_sleep_on_invalid_configuration(self):
        tc = mock.Mock()
        tc.pipeline_ids.return_value = ["pipeline"]
        tc.pipeline_definition.return_value = definition({"script": "private-canary"})
        with mock.patch.object(runner.time, "sleep") as pause:
            with self.assertRaises(ScriptConfigurationError):
                runner.wait_for_build(tc, "project", 3600)
        tc.builds.assert_not_called()
        tc.build_tree.assert_not_called()
        tc.queue_wait_reason.assert_not_called()
        pause.assert_not_called()

    def test_invalid_probe_does_not_override_valid_selected_pipeline(self):
        tc = mock.Mock()
        tc.pipeline_ids.return_value = ["main", "probe"]
        valid = definition({"script-content": "echo synthetic"})
        tc.pipeline_definition.side_effect = lambda key: valid if key == "main" else definition({"script": "bad"})
        tc.builds.return_value = [{"id": 1, "buildTypeId": "main"}]
        tc.build_tree.return_value = {
            "id": 1, "buildTypeId": "main", "state": "finished", "status": "SUCCESS",
            "dependencies": [{"id": 2, "buildTypeId": "child", "state": "finished",
                              "status": "SUCCESS", "dependencies": []}],
        }
        with tempfile.TemporaryDirectory() as directory:
            checkout = pathlib.Path(directory)
            (checkout / "pipeline.json").write_text(json.dumps(valid))
            build = runner.wait_for_build(tc, "project", 10, checkout=checkout,
                case={"requestedConfiguration": {"sourcePath": "pipeline.json"}})
        self.assertEqual("main", build["pipelineId"])
        self.assertEqual(0, build["configurationDiagnostics"]["invalidScriptStepCount"])

    def test_both_graders_reject_invalid_script_even_with_green_build(self):
        jobs = [{"name": "Verify", "steps": [{"type": "script", "properties": {"script": "bad"}}],
                 "artifactRules": "", "agentRequirements": []}]
        configuration = runner.grade_configuration({"expected": {
            "minimumJobs": 1, "sourceMutations": "none",
        }}, {"jobs": jobs, "mutations": [], "toolCalls": []})
        runtime_case = json.loads((EVALS / "first-green-build/cases/spring-petclinic-maven-yaml.json").read_text())
        runtime = runner.grade(runtime_case, {
            "jobs": jobs, "buildTypeCount": 2, "buildStatus": "SUCCESS", "attempts": 1,
            "testCount": 1, "artifacts": ["app.jar"], "properties": {}, "mutations": [],
        })
        self.assertFalse(configuration["configurationValidated"]["passed"])
        self.assertFalse(runtime["configurationValidated"]["passed"])

    def test_publication_strips_values_and_preserves_error_category(self):
        diagnostics = {"checkedScriptStepCount": 1, "invalidScriptStepCount": 1,
            "script": "private-canary", "issues": [
                {"jobIndex": 1, "stepIndex": 2, "category": "missing-script-source", "name": "private-canary"},
                {"jobIndex": 1, "stepIndex": 3, "category": "private-canary"},
                {"jobIndex": True, "stepIndex": 3, "category": "missing-script-source"},
            ]}
        safe = runner.publishable_result({"configurationDiagnostics": diagnostics,
            "verificationErrorCategory": "verification-invalid-script-steps", "checks": {}})
        self.assertNotIn("private-canary", json.dumps(safe))
        self.assertEqual(1, len(safe["configurationDiagnostics"]["issues"]))
        self.assertEqual("verification-invalid-script-steps", safe["verificationErrorCategory"])
        outcome, _ = collector.classify(None, {"state": "finished", "status": "FAILURE"},
            {"status": "errored", "errorCategory": "verification-invalid-script-steps"})
        self.assertEqual("verification-invalid-script-steps", outcome)


class BridgeScriptValidationTest(unittest.TestCase):
    def bridge(self, root):
        return TeamCityCliBridge("teamcity", "https://example.invalid", "private", root,
            root, "Eval", True, lambda: ["Eval_Pipeline"], lambda: [], {})

    def test_validate_create_and_push_check_the_actual_input_file(self):
        for arguments, filename in (
            (["pipeline", "validate"], ".teamcity.yml"),
            (["pipeline", "validate", "custom.yml", "--refresh-schema"], "custom.yml"),
            (["pipeline", "create", "main", "--project", "Eval"], ".teamcity.yml"),
            (["pipeline", "create", "main", "--project=Eval", "--file=custom.yml"], "custom.yml"),
            (["pipeline", "create", "main", "-p", "Eval", "-f", "custom.yml"], "custom.yml"),
            (["pipeline", "push", "Eval_Pipeline"], ".teamcity.yml"),
            (["pipeline", "push", "Eval_Pipeline", "custom.yml"], "custom.yml"),
        ):
            with self.subTest(arguments=arguments), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                (root / filename).write_text(json.dumps(definition({"script": "private-canary"})))
                with mock.patch("teamcity_cli_bridge.subprocess.run") as command:
                    with self.assertRaises(ScriptConfigurationError):
                        self.bridge(root).execute(arguments, root)
                command.assert_not_called()

    def test_corrected_file_continues_to_real_server_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / ".teamcity.yml").write_text(json.dumps(definition({"script-content": "echo ok"})))
            outcome = subprocess.CompletedProcess([], 0, stdout="valid", stderr="")
            with mock.patch("teamcity_cli_bridge.subprocess.run", return_value=outcome) as command:
                result = self.bridge(root).execute(["pipeline", "validate"], root)
            self.assertIs(outcome, result)
            command.assert_called_once()

    def test_help_does_not_require_a_yaml_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with mock.patch("teamcity_cli_bridge.subprocess.run") as command:
                self.bridge(root).execute(["pipeline", "create", "--help"], root)
            command.assert_called_once()


if __name__ == "__main__":
    unittest.main()
