"""Synthetic command-counter tests; never load a real agent trajectory."""

import importlib.util
import json
import pathlib
import unittest
from unittest import mock


EVALS = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_case_tool_summary_test", EVALS / "run_case.py")
run_case = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_case)


class ToolSummaryCommandTest(unittest.TestCase):
    def summarize(self, commands):
        event = {
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": command}}
                for command in commands
            ]},
        }
        with mock.patch.object(pathlib.Path, "read_text", return_value=json.dumps(event)):
            return run_case.agent_tool_summary(pathlib.Path("synthetic-trace.jsonl"))

    def test_explicit_server_assignments_count_as_cli_calls(self):
        commands = [
            "TEAMCITY_URL=https://example.invalid teamcity run list",
            "MODE='two words' TEAMCITY_URL=https://example.invalid teamcity run list",
            'TEAMCITY_URL="https://example.invalid" teamcity run list',
        ]
        summary = self.summarize(commands)
        self.assertEqual(3, summary["teamcityCliCalls"])
        self.assertEqual(0, summary["otherCalls"])

    def test_env_launcher_and_binary_paths_count(self):
        commands = [
            "env TEAMCITY_URL=https://example.invalid teamcity run list",
            "env -- TEAMCITY_URL=https://example.invalid teamcity run list",
            "/usr/bin/env TEAMCITY_URL=https://example.invalid /opt/bin/teamcity run list",
            "TEAMCITY_URL=https://example.invalid ./teamcity run list",
        ]
        self.assertEqual(4, self.summarize(commands)["teamcityCliCalls"])

    def test_existing_direct_calls_remain_one_count_per_bash_tool(self):
        commands = [
            "teamcity run list",
            "  teamcity run list; teamcity run view 42",
            "teamcity run list | jq '.count'",
            "'teamcity' run list",
        ]
        self.assertEqual(4, self.summarize(commands)["teamcityCliCalls"])

    def test_mentions_prefix_lookalikes_and_incomplete_commands_do_not_count(self):
        commands = [
            "echo teamcity run list",
            "TEAMCITY_URL=https://example.invalid echo teamcity",
            "teamcity-helper run list",
            "teamcity_fake run list",
            "'teamcity run list'",
            "TEAMCITY_URL=https://example.invalid",
            "env TEAMCITY_URL=https://example.invalid",
            "teamcity run view 'unterminated",
            "",
        ]
        summary = self.summarize(commands)
        self.assertEqual(0, summary["teamcityCliCalls"])
        self.assertEqual(len(commands), summary["otherCalls"])

    def test_unparsed_shell_wrappers_are_not_claimed_as_cli_evidence(self):
        summary = self.summarize(["bash -c 'teamcity run list'", "true && teamcity run list"])
        self.assertEqual(0, summary["teamcityCliCalls"])

    def test_published_summary_contains_only_existing_numeric_counters(self):
        summary = self.summarize([
            "PRIVATE_LABEL=synthetic-do-not-publish teamcity run list",
        ])
        self.assertEqual({
            "totalCalls": 1,
            "mcpTeamCityCalls": 0,
            "mcpProbeCalls": 0,
            "teamcityCliCalls": 1,
            "otherCalls": 0,
        }, summary)
        self.assertNotIn("synthetic-do-not-publish", json.dumps(summary))


if __name__ == "__main__":
    unittest.main()
