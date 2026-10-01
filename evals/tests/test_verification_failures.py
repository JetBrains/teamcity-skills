"""Synthetic failure propagation only; no server, agent, or real trace access."""

import contextlib
import importlib.util
import io
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock


EVALS = pathlib.Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, EVALS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load("verification_failure_runner", "run_case.py")
collector = load("verification_failure_collector", "collect_teamcity_eval_runs.py")


class VerificationFailureTest(unittest.TestCase):
    def run_failure(self, error, timed_out=True):
        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as stack:
            case = pathlib.Path(directory) / "case.json"
            case.write_text(json.dumps({
                "id": "example", "kind": "first-green-build", "status": "draft",
                "prompt": "synthetic task", "repository": {"defaultBranch": "main"},
            }))
            tc = mock.Mock()
            tc.create_project.return_value = "private-project"
            bridge = mock.MagicMock()
            bridge.__enter__.return_value.agent_environment.return_value = {}
            stack.enter_context(mock.patch.dict(runner.os.environ, {
                "TEAMCITY_URL": "https://example.invalid", "TEAMCITY_TOKEN": "private-token",
                "EVAL_AGENT_TIMEOUT": "7200", "EVAL_BUILD_TIMEOUT": "7200",
            }, clear=True))
            stack.enter_context(mock.patch.object(runner.shutil, "which", return_value="teamcity"))
            stack.enter_context(mock.patch.object(runner, "TeamCity", return_value=tc))
            stack.enter_context(mock.patch.object(runner, "TeamCityCliBridge", return_value=bridge))
            stack.enter_context(mock.patch.object(runner, "checkout_repository"))
            stack.enter_context(mock.patch.object(runner, "harness_revision", return_value="a" * 40))
            stack.enter_context(mock.patch.object(runner.sys, "stderr", io.StringIO()))
            for name, value in (("agent_usage", {}), ("trace_error_category", None),
                                ("permission_failure_surface", None), ("agent_tool_summary", {})):
                stack.enter_context(mock.patch.object(runner, name, return_value=value))
            invoke = stack.enter_context(mock.patch.object(runner, "invoke_agent", return_value={
                "exitCode": 124 if timed_out else 0,
                "timedOut": timed_out, "timeoutSeconds": 7200,
            }))
            wait = stack.enter_context(mock.patch.object(runner, "wait_for_build", side_effect=error))
            published = runner.publishable_result(runner.run(case, False, False, "baseline", "cli-only"))
            self.assertEqual(7200, invoke.call_args.args[4])
            self.assertEqual(7200, wait.call_args.args[2])
            self.assertEqual(120 if timed_out else 7200, wait.call_args.kwargs["no_build_timeout"])
            self.assertNotIn("private", json.dumps(published))
            return published

    def test_timeout_keeps_secondary_verification_failures_without_fabricated_grade(self):
        errors = [
            (runner.NoBuildQueued("private"), "build-not-queued"),
            (runner.NoBuildQueued("private", "verification-no-pipeline"), "verification-no-pipeline"),
            (runner.BuildWaitTimeout("private"), "build-wait-timeout"),
            (runner.BuildQueueStalled("no-idle-compatible-agents"), "build-queue-stalled"),
            (runner.EvidenceError("verification-pipeline-ambiguous"), "verification-pipeline-ambiguous"),
            (runner.EvidenceError("verification-chain-incomplete"), "verification-chain-incomplete"),
            (runner.EvalError("private server output"), "verification-observation-failed"),
        ]
        for error, category in errors:
            with self.subTest(category=category):
                result = self.run_failure(error)
                self.assertEqual("errored", result["status"])
                self.assertEqual("agent-timeout", result["errorCategory"])
                self.assertEqual(category, result["verificationErrorCategory"])
                self.assertEqual(7200, result["agentTimeoutSeconds"])
                self.assertEqual(7200, result["buildTimeoutSeconds"])
                self.assertEqual({}, result["checks"])
                self.assertNotIn("gradeStatus", result)
                self.assertNotIn("agentUsage", result)

    def test_normal_agent_exit_retains_primary_build_failure(self):
        result = self.run_failure(runner.BuildWaitTimeout("private"), timed_out=False)
        self.assertEqual("build-wait-timeout", result["errorCategory"])
        self.assertEqual("build-wait-timeout", result["verificationErrorCategory"])

    def test_no_pipeline_is_distinct_from_no_queued_head(self):
        tc = mock.Mock()
        tc.pipeline_ids.return_value = []
        with self.assertRaises(runner.NoBuildQueued) as failure:
            runner.wait_for_build(tc, "private-project", timeout=7200)
        self.assertEqual("verification-no-pipeline", failure.exception.category)
        tc.builds.assert_not_called()

    def test_secondary_error_and_timeout_publication_are_allowlisted(self):
        for value in ("private payload", {}, [], True, None):
            result = runner.publishable_result({"verificationErrorCategory": value,
                                                "buildTimeoutSeconds": value})
            self.assertNotIn("verificationErrorCategory", result)
            self.assertNotIn("buildTimeoutSeconds", result)

    def test_collector_keeps_safe_secondary_error_and_limits_only(self):
        artifact = {"caseId": "example", "arm": "skill", "status": "errored",
                    "agentTimedOut": True, "errorCategory": "agent-timeout", "checks": {},
                    "verificationErrorCategory": "verification-no-pipeline",
                    "agentTimeoutSeconds": 7200, "buildTimeoutSeconds": 7200,
                    "error": "private raw error"}

        def cli(_server, *arguments):
            if arguments[1] == "artifacts":
                return subprocess.CompletedProcess([], 0, json.dumps({"file": [{"name": "eval-result.json"}]}))
            self.assertEqual("download", arguments[1])
            destination = pathlib.Path(arguments[arguments.index("--output") + 1])
            (destination / "eval-result.json").write_text(json.dumps(artifact))
            return subprocess.CompletedProcess([], 0, "")

        with mock.patch.object(collector, "cli", side_effect=cli):
            result = collector.download_result([], "https://example.invalid", 42, {"example"})
            self.assertEqual("agent-timeout", result["errorCategory"])
            self.assertEqual("verification-no-pipeline", result["verificationErrorCategory"])
            self.assertEqual(7200, result["agentTimeoutSeconds"])
            self.assertEqual(7200, result["buildTimeoutSeconds"])
            self.assertNotIn("private", json.dumps(result))
            artifact.update(verificationErrorCategory={"private": True},
                            agentTimeoutSeconds=True, buildTimeoutSeconds=-1)
            result = collector.download_result([], "https://example.invalid", 42, {"example"})
            self.assertIsNone(result["verificationErrorCategory"])
            self.assertNotIn("agentTimeoutSeconds", result)
            self.assertNotIn("buildTimeoutSeconds", result)


if __name__ == "__main__":
    unittest.main()
