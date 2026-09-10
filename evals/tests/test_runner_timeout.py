import importlib.util
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock


EVALS = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, EVALS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_case = load_module("run_case_timeout_test", "run_case.py")
collector = load_module("collect_timeout_test", "collect_teamcity_eval_runs.py")


class AgentTimeoutTest(unittest.TestCase):
    def test_invoke_agent_turns_timeout_into_structured_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            trace = root / "trace.log"
            with mock.patch.object(
                run_case.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired("claude", 7),
            ):
                outcome = run_case.invoke_agent(
                    "prompt", root, {}, trace, timeout=7, tools=["Read"]
                )

            self.assertEqual(124, outcome["exitCode"])
            self.assertTrue(outcome["timedOut"])
            self.assertEqual(7, outcome["timeoutSeconds"])
            self.assertIn("Agent timed out after 7s", trace.read_text())

    def test_invoke_agent_does_not_pass_lifecycle_token_to_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            completed = subprocess.CompletedProcess([], 0)
            with mock.patch.object(run_case.subprocess, "run", return_value=completed) as invoked:
                run_case.invoke_agent(
                    "prompt",
                    pathlib.Path(directory),
                    {"TEAMCITY_TOKEN": "review-canary"},
                    trace,
                    timeout=7,
                )

            self.assertNotIn("TEAMCITY_TOKEN", invoked.call_args.kwargs["env"])

    def test_publishable_result_excludes_raw_agent_and_server_data(self):
        published = run_case.publishable_result(
            {
                "caseId": "example",
                "status": "failed",
                "checks": {"build": {"passed": False, "detail": "raw build data"}},
                "agentTraceTail": ["TEAMCITY_TOKEN=review-canary"],
                "toolCalls": ["Bash {command: env}"],
                "projectId": "internal-project",
                "error": "raw server response",
            }
        )

        self.assertEqual({"build": {"passed": False}}, published["checks"])
        self.assertNotIn("agentTraceTail", published)
        self.assertNotIn("toolCalls", published)
        self.assertNotIn("projectId", published)
        self.assertNotIn("error", published)

    def test_timed_out_agent_keeps_checks_but_cannot_pass(self):
        result = {"checks": {"build": {"passed": True}}}

        run_case.set_graded_status(
            result, {"exitCode": 124, "timedOut": True, "timeoutSeconds": 3600}
        )

        self.assertEqual("passed", result["gradeStatus"])
        self.assertEqual("errored", result["status"])
        self.assertEqual("agent-timeout", result["errorCategory"])

    def test_collector_classifies_published_timeout(self):
        category, detail = collector.classify(
            "https://teamcity.example",
            {"id": 1, "state": "finished", "status": "FAILURE"},
            {
                "status": "errored",
                "gradeStatus": "failed",
                "errorCategory": "agent-timeout",
                "checks": {
                    "firstBuild": {"passed": True},
                    "artifactsPublished": {"passed": False},
                },
            },
        )

        self.assertEqual("agent-timeout", category)
        self.assertIn("failed assertions: artifactsPublished", detail)

    def test_collector_accepts_legacy_timed_out_flag(self):
        category, _detail = collector.classify(
            "https://teamcity.example",
            {"id": 1, "state": "finished", "status": "FAILURE"},
            {"status": "errored", "agentTimedOut": True, "checks": {}},
        )

        self.assertEqual("agent-timeout", category)

    def test_dependency_tree_is_deduplicated(self):
        job = {"id": 7, "name": "Run configuration eval", "dependencies": []}
        tree = {
            "dependencies": [
                {"id": 8, "name": "Publish evaluation report", "dependencies": [job]},
                job,
            ]
        }

        flattened = collector.flatten_dependencies(tree)

        self.assertEqual([8, 7], [node["id"] for node in flattened])


if __name__ == "__main__":
    unittest.main()
