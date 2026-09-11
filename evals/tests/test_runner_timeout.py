import importlib.util
import json
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
                "agentTraceTail": ["sensitive trace data"],
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

    def test_agent_usage_copies_only_safe_numeric_aggregates(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            trace.write_text(
                "prompt and private trajectory\n"
                + json.dumps(
                    {
                        "type": "result",
                        "result": "private final answer",
                        "total_cost_usd": 0.42,
                        "session_id": "private-session",
                        "usage": {
                            "input_tokens": 100,
                            "output_tokens": 20,
                            "cache_read_input_tokens": 80,
                            "cache_creation_input_tokens": 10,
                            "private": "must not escape",
                        },
                    }
                )
                + "\n"
            )

            usage = run_case.agent_usage(trace)

        self.assertEqual(
            {
                "inputTokens": 100,
                "outputTokens": 20,
                "cacheReadTokens": 80,
                "cacheWriteTokens": 10,
                "totalCostUsd": 0.42,
            },
            usage,
        )

    def test_publishable_result_keeps_safe_usage_without_trace_fields(self):
        published = run_case.publishable_result(
            {
                "caseId": "example",
                "status": "passed",
                "agentUsage": {
                    "inputTokens": 100,
                    "totalCostUsd": 0.42,
                    "private": "must not escape",
                },
                "agentTraceTail": ["private"],
                "checks": {},
            }
        )

        self.assertEqual(
            {"inputTokens": 100, "totalCostUsd": 0.42},
            published["agentUsage"],
        )
        self.assertNotIn("agentTraceTail", published)

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

    def test_pass_rate_uses_at_most_five_runs_from_latest_revision(self):
        def job(identifier, revision, classification):
            return {
                "id": identifier,
                "revision": revision,
                "classification": classification,
                "classificationDetail": classification,
                "url": f"https://teamcity.example/{identifier}",
                "result": {"caseId": "example", "arm": "skill"},
            }

        observed = collector.latest_arm_observations(
            [
                job(9, "new", "passed"),
                job(8, "new", "skill-output-failed"),
                job(7, "old", "passed"),
            ]
        )

        history = observed[("example", "skill")]["history"]
        self.assertEqual(2, history["sampleSize"])
        self.assertEqual(1, history["passCount"])
        self.assertEqual(0.5, history["passRate"])

    def test_pass_rate_is_not_claimed_without_a_harness_revision(self):
        observed = collector.latest_arm_observations(
            [
                {
                    "id": 9,
                    "revision": None,
                    "classification": "passed",
                    "classificationDetail": "passed",
                    "url": "https://teamcity.example/9",
                    "result": {"caseId": "example", "arm": "skill"},
                }
            ]
        )

        self.assertEqual(0, observed[("example", "skill")]["history"]["sampleSize"])

    def test_vcs_revision_reads_the_pipeline_head_change(self):
        self.assertEqual(
            "0123456789abcdef",
            collector.vcs_revision(
                {"lastChanges": {"change": [{"version": "0123456789abcdef"}]}}
            ),
        )


if __name__ == "__main__":
    unittest.main()
