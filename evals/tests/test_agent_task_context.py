"""Task/observation contract tests using synthetic agents and server metadata."""

import contextlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock


EVALS = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("task_context_runner", EVALS / "run_case.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class AgentTaskContextTest(unittest.TestCase):
    def case(self):
        return {
            "id": "synthetic", "kind": "first-green-build",
            "prompt": "Set up CI at {{teamcity.server}} under {{teamcity.targetProject}}.",
            "repository": {"defaultBranch": "development"},
            "requestedConfiguration": {
                "format": "yaml", "sourcePath": "ci/final.yml",
                "requiredStepProperties": [{"private-property": "private-value"}],
            },
            "expected": {"private-check": True},
            "verification": {"command": "private-reference-command"},
            "observedBaseline": {"private-historical-evidence": True},
        }

    def test_context_exposes_deliverable_and_branch_not_grading_answers(self):
        case = self.case()
        prompt = runner.agent_task_prompt(case, "https://example.invalid", "SyntheticProject")
        for public_value in ("https://example.invalid", "SyntheticProject", "development",
                             "yaml", "ci/final.yml"):
            self.assertIn(public_value, prompt)
        self.assertNotIn("private-", prompt)
        self.assertNotIn("{{", prompt)
        # No hidden part of the case changes the task received by either arm.
        case.update(expected={}, verification={}, observedBaseline={})
        case["requestedConfiguration"].pop("requiredStepProperties")
        self.assertEqual(prompt, runner.agent_task_prompt(case, "https://example.invalid", "SyntheticProject"))

    def test_configuration_only_request_keeps_its_stopping_condition(self):
        case = self.case()
        case.update(kind="pipeline-configuration", prompt="Create and validate CI. Do not queue a build.")
        prompt = runner.agent_task_prompt(case, "server", "project")
        self.assertTrue(prompt.startswith(case["prompt"]))
        self.assertIn("ci/final.yml", prompt)
        self.assertIn("does not authorize builds or source changes", prompt)

    def test_fixture_without_configuration_or_repository_keeps_original_task(self):
        case = {"kind": "queue-stall-diagnosis", "prompt": "Diagnose {{teamcity.targetProject}}."}
        self.assertEqual("Diagnose Fixture.", runner.agent_task_prompt(case, "server", "Fixture"))

    def test_both_live_arms_receive_the_same_context_and_retain_ungraded_failures(self):
        prompts = []
        for arm in ("skill", "baseline"):
            with self.subTest(arm=arm), tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as stack:
                case_path = pathlib.Path(directory) / "case.json"
                case_path.write_text(json.dumps(self.case()))
                tc = mock.Mock()
                tc.create_project.return_value = "SyntheticProject"
                bridge = mock.MagicMock()
                bridge.__enter__.return_value.agent_environment.return_value = {}
                stack.enter_context(mock.patch.dict(runner.os.environ, {
                    "TEAMCITY_URL": "https://example.invalid", "TEAMCITY_TOKEN": "private-token",
                }, clear=True))
                stack.enter_context(mock.patch.object(runner.shutil, "which", return_value="teamcity"))
                stack.enter_context(mock.patch.object(runner, "TeamCity", return_value=tc))
                stack.enter_context(mock.patch.object(runner, "TeamCityCliBridge", return_value=bridge))
                stack.enter_context(mock.patch.object(runner, "checkout_repository"))
                install = stack.enter_context(mock.patch.object(
                    runner, "install_skill", side_effect=lambda _case, checkout: checkout / ".claude/skills/synthetic",
                ))
                stack.enter_context(mock.patch.object(runner, "harness_revision", return_value="a" * 40))
                stack.enter_context(mock.patch.object(runner.sys, "stderr", io.StringIO()))
                for name, value in (("agent_usage", {}), ("trace_error_category", None),
                                    ("permission_failure_surface", None), ("agent_tool_summary", {})):
                    stack.enter_context(mock.patch.object(runner, name, return_value=value))
                invoke = stack.enter_context(mock.patch.object(runner, "invoke_agent", return_value={
                    "exitCode": 1, "timedOut": False, "timeoutSeconds": 7200,
                    "failureCategory": "agent-result-failed",
                }))
                stack.enter_context(mock.patch.object(runner, "wait_for_build", side_effect=
                    runner.EvidenceError("verification-pipeline-ambiguous")))
                result = runner.publishable_result(runner.run(case_path, False, False, arm, "cli-only"))
                prompts.append(invoke.call_args.args[0])
                self.assertEqual(1 if arm == "skill" else 0, install.call_count)
                self.assertEqual("errored", result["status"])
                self.assertEqual("agent-result-failed", result["errorCategory"])
                self.assertEqual("verification-pipeline-ambiguous", result["verificationErrorCategory"])
                self.assertEqual({}, result["checks"])
                self.assertNotIn("gradeStatus", result)
        self.assertEqual(prompts[0], prompts[1])
        self.assertIn("ci/final.yml", prompts[0])
        self.assertNotIn("private-", prompts[0])

    def test_dry_run_previews_the_same_public_task_context(self):
        with tempfile.TemporaryDirectory() as directory:
            case_path = pathlib.Path(directory) / "case.json"
            case_path.write_text(json.dumps(self.case()))
            with mock.patch.dict(runner.os.environ, {}, clear=True):
                result = runner.run(case_path, True, False, "baseline", "cli-only")
        self.assertIn("<server>", result["prompt"])
        self.assertIn("<targetProject>", result["prompt"])
        self.assertIn("ci/final.yml", result["prompt"])
        self.assertNotIn("private-", result["prompt"])


if __name__ == "__main__":
    unittest.main()
