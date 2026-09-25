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

    def test_publishable_result_keeps_only_numeric_tool_summary(self):
        published = run_case.publishable_result(
            {
                "agentToolSummary": {
                    "totalCalls": 4,
                    "mcpTeamCityCalls": 2,
                    "teamcityCliCalls": 1,
                    "otherCalls": 1,
                    "toolName": "must not escape",
                },
                "checks": {},
            }
        )

        self.assertEqual(
            {
                "totalCalls": 4,
                "mcpTeamCityCalls": 2,
                "teamcityCliCalls": 1,
                "otherCalls": 1,
            },
            published["agentToolSummary"],
        )

    def test_publishable_result_keeps_tool_mode_and_safe_agent_identity(self):
        published = run_case.publishable_result(
            {
                "caseId": "example",
                "status": "passed",
                "toolMode": "cli+mcp",
                "agentConfigId": "claude-teamcity",
                "agentVersion": "1.2.3",
                "checks": {},
            }
        )

        self.assertEqual("cli+mcp", published["toolMode"])
        self.assertEqual("claude-teamcity", published["agentConfigId"])
        self.assertEqual("1.2.3", published["agentVersion"])

    def test_tool_modes_are_explicit_and_mcp_never_falls_back_to_cli(self):
        self.assertEqual("cli-only", run_case.resolve_tool_mode("cli-only"))
        self.assertEqual("mcp-only", run_case.resolve_tool_mode("mcp-only"))
        with self.assertRaises(run_case.EvalError):
            run_case.resolve_tool_mode("automatic")
        with self.assertRaises(run_case.EvalError):
            run_case.mcp_config_for_mode({}, "mcp-only")

    def test_local_probe_diagnostic_requires_probe_in_its_config(self):
        with tempfile.TemporaryDirectory() as directory:
            config = pathlib.Path(directory) / "mcp.json"
            config.write_text(json.dumps({"mcpServers": {"teamcity": {}}}))
            with self.assertRaises(run_case.EvalError):
                run_case.mcp_config_for_mode(
                    {"EVAL_MCP_CONFIG": str(config)}, "mcp-only", True,
                )
            config.write_text(json.dumps({"mcpServers": {"probe": {}}}))
            self.assertEqual(
                config,
                run_case.mcp_config_for_mode(
                    {"EVAL_MCP_CONFIG": str(config)}, "mcp-only", True,
                ),
            )

    def test_mcp_only_environment_hides_teamcity_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            cli_dir = pathlib.Path(directory) / "cli"
            other_dir = pathlib.Path(directory) / "other"
            cli_dir.mkdir()
            other_dir.mkdir()
            (cli_dir / "teamcity").write_text("#!/bin/sh\n")

            environment = run_case.agent_environment_without_cli(
                {
                    "TEAMCITY_TOKEN": "private",
                    "EVAL_MCP_TOKEN": "mcp-private",
                    "TEAMCITY_EVAL_CLI": "teamcity",
                    "TEAMCITY_EVAL_CLI_DIR": str(cli_dir),
                    "PATH": str(cli_dir) + run_case.os.pathsep + str(other_dir),
                },
                "https://teamcity.example",
            )

        self.assertNotIn("TEAMCITY_TOKEN", environment)
        self.assertNotIn("EVAL_MCP_TOKEN", environment)
        self.assertNotIn("TEAMCITY_EVAL_CLI", environment)
        self.assertNotIn("TEAMCITY_EVAL_CLI_DIR", environment)
        self.assertEqual(str(other_dir), environment["PATH"])
        self.assertEqual("https://teamcity.example", environment["TEAMCITY_URL"])

    def test_mcp_config_authorizes_only_dynamic_teamcity_server_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            trace = root / "trace.log"
            mcp_config = root / "mcp.json"
            mcp_config.write_text("{}")
            completed = subprocess.CompletedProcess([], 0)
            with mock.patch.object(run_case.subprocess, "run", return_value=completed) as invoked:
                run_case.invoke_agent(
                    "prompt", root, {}, trace, timeout=7,
                    tools=["Read"], mcp_config=mcp_config,
                )

        command = invoked.call_args.args[0]
        self.assertIn("Read", command)
        self.assertIn("mcp__teamcity__*", command)
        self.assertIn("--strict-mcp-config", command)

    def test_ambient_mcp_diagnostic_omits_strict_config_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            trace = root / "trace.log"
            completed = subprocess.CompletedProcess([], 0)
            with mock.patch.object(run_case.subprocess, "run", return_value=completed) as invoked:
                run_case.invoke_agent(
                    "prompt", root, {}, trace, timeout=7,
                    use_strict_mcp_config=False,
                )

        self.assertNotIn("--strict-mcp-config", invoked.call_args.args[0])

    def test_strict_mcp_config_defaults_to_true_and_rejects_ambiguous_values(self):
        self.assertTrue(run_case.strict_mcp_config("mcp-only", None))
        self.assertTrue(run_case.strict_mcp_config("mcp-only", "true"))
        self.assertFalse(run_case.strict_mcp_config("mcp-only", "false"))
        self.assertTrue(run_case.strict_mcp_config("cli-only", "false"))
        with self.assertRaises(run_case.EvalError):
            run_case.strict_mcp_config("mcp-only", "sometimes")

    def test_local_mcp_probe_is_opt_in_and_requires_an_mcp_mode(self):
        self.assertFalse(run_case.local_mcp_probe("mcp-only", None))
        self.assertTrue(run_case.local_mcp_probe("mcp-only", "true"))
        with self.assertRaises(run_case.EvalError):
            run_case.local_mcp_probe("cli+mcp", "yes")
        with self.assertRaises(run_case.EvalError):
            run_case.local_mcp_probe("mcp-only", "perhaps")

    def test_agent_tool_summary_counts_surfaces_without_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            trace.write_text("\n".join([
                json.dumps({"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "name": "mcp__teamcity__projects_list", "input": {"secret": "no"}},
                    {"type": "tool_use", "name": "mcp__probe__ping", "input": {}},
                    {"type": "tool_use", "name": "Bash", "input": {"command": "teamcity pipeline list"}},
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "private"}},
                ]}}),
            ]))

            summary = run_case.agent_tool_summary(trace)

        self.assertEqual(
            {
                "totalCalls": 4, "mcpTeamCityCalls": 1, "mcpProbeCalls": 1,
                "teamcityCliCalls": 1, "otherCalls": 1,
            },
            summary,
        )

    def test_mcp_configuration_error_category_distinguishes_no_mcp_call(self):
        checks = {
            "configurationValidated": {"passed": False},
            "requiredMcpToolUse": {"passed": False},
            "forbiddenCliToolUse": {"passed": True},
        }
        self.assertEqual(
            "mcp-not-invoked",
            run_case.mcp_configuration_error_category(
                "mcp-only", checks,
                {"mcpTeamCityCalls": 0},
            ),
        )

    def test_mcp_probe_distinguishes_mcp_client_from_teamcity_tools(self):
        checks = {
            "configurationValidated": {"passed": False},
            "requiredMcpToolUse": {"passed": False},
            "forbiddenCliToolUse": {"passed": True},
            "requiredLocalMcpProbeUse": {"passed": False},
        }
        self.assertEqual(
            "mcp-local-probe-not-invoked",
            run_case.mcp_configuration_error_category(
                "mcp-only", checks, {}, {}, use_local_mcp_probe=True,
            ),
        )
        checks["requiredLocalMcpProbeUse"] = {"passed": True}
        self.assertEqual(
            "mcp-teamcity-tools-not-advertised",
            run_case.mcp_configuration_error_category(
                "mcp-only", checks, {},
                {"teamcityToolsAdvertised": False}, use_local_mcp_probe=True,
            ),
        )
        self.assertEqual(
            "mcp-teamcity-tools-not-used-after-local-probe",
            run_case.mcp_configuration_error_category(
                "mcp-only", checks, {},
                {"teamcityToolsAdvertised": True}, use_local_mcp_probe=True,
            ),
        )
        checks["requiredMcpToolUse"] = {"passed": True}
        checks["forbiddenCliToolUse"] = {"passed": False}
        self.assertEqual(
            "mcp-cli-invoked",
            run_case.mcp_configuration_error_category(
                "mcp-only", checks,
                {"mcpTeamCityCalls": 1, "teamcityCliCalls": 1},
            ),
        )
        checks["forbiddenCliToolUse"] = {"passed": True}
        self.assertEqual(
            "mcp-no-configuration",
            run_case.mcp_configuration_error_category(
                "mcp-only", checks,
                {"mcpTeamCityCalls": 1},
            ),
        )

    def test_mcp_runtime_classifies_only_safe_system_startup_state(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            trace.write_text("\n".join([
                json.dumps({
                    "type": "system",
                    "mcpServerStatus": {"teamcity": "Blocked by enterprise policy"},
                }),
                json.dumps({
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "private"}]},
                }),
            ]))

            runtime = run_case.mcp_runtime(trace)

        self.assertEqual("enterprise-policy-blocked", runtime["connectionStatus"])
        self.assertFalse(runtime["teamcityToolsAdvertised"])

    def test_mcp_runtime_classifies_safe_plain_startup_policy_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            trace.write_text(
                "--- prompt ---\nprivate\n--- output ---\n"
                "Warning: an enterprise MCP config (managed-mcp.json) is present and "
                "has exclusive control over MCP servers.\n"
            )

            runtime = run_case.mcp_runtime(trace)

        self.assertEqual("enterprise-managed-config", runtime["connectionStatus"])

    def test_mcp_runtime_detects_advertised_tools_without_retaining_names(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            trace.write_text(json.dumps({
                "type": "system",
                "tools": ["mcp__teamcity__private_tool"],
            }))

            runtime = run_case.mcp_runtime(trace)

        self.assertEqual("tools-advertised", runtime["connectionStatus"])
        self.assertTrue(runtime["teamcityToolsAdvertised"])

    def test_mcp_runtime_detects_local_probe_without_retaining_tool_names(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            trace.write_text(json.dumps({
                "type": "system",
                "tools": ["mcp__probe__ping"],
            }))

            runtime = run_case.mcp_runtime(trace)

        self.assertEqual("tools-advertised", runtime["connectionStatus"])
        self.assertFalse(runtime["teamcityToolsAdvertised"])
        self.assertTrue(runtime["localProbeToolsAdvertised"])

    def test_mcp_error_category_uses_runtime_without_copying_diagnostics(self):
        checks = {
            "requiredMcpToolUse": {"passed": False},
            "forbiddenCliToolUse": {"passed": True},
        }

        category = run_case.mcp_configuration_error_category(
            "mcp-only", checks, {}, {"connectionStatus": "authentication-failed"},
        )

        self.assertEqual("mcp-authentication-failed", category)

    def test_permission_failure_surface_uses_only_fixed_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            trace.write_text(
                "--- prompt ---\nprivate MCP text\n--- output ---\n"
                "Tool requires approval before a TeamCity MCP action.\n"
            )

            surface = run_case.permission_failure_surface(trace)

        self.assertEqual("mcp", surface)

    def test_permission_failure_surface_ignores_prompt_text(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            trace.write_text(
                "--- prompt ---\nMCP requires approval\n--- output ---\n"
                "Tool requires approval.\n"
            )

            surface = run_case.permission_failure_surface(trace)

        self.assertEqual("unknown", surface)

    def test_mcp_only_contract_is_scoped_to_the_eval_not_the_skill(self):
        contract = run_case.transport_prompt_contract("mcp-only")

        self.assertIn("mcp__teamcity__*", contract)
        self.assertIn("hard success criterion", contract)
        self.assertIn("first TeamCity operation must be a read-only MCP discovery", contract)
        self.assertIn("Do not fall back", contract)
        probe_contract = run_case.transport_prompt_contract("mcp-only", True)
        self.assertIn("mcp__probe__ping", probe_contract)
        self.assertEqual("", run_case.transport_prompt_contract("cli-only"))
        self.assertEqual("", run_case.transport_prompt_contract("cli+mcp"))

    def test_invoke_agent_adds_the_transport_contract_as_a_system_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            completed = subprocess.CompletedProcess([], 0)
            with mock.patch.object(run_case.subprocess, "run", return_value=completed) as invoked:
                run_case.invoke_agent(
                    "case prompt", pathlib.Path(directory), {}, trace, timeout=7,
                    transport_contract="MCP transport contract",
                )

        command = invoked.call_args.args[0]
        self.assertIn("--append-system-prompt", command)
        self.assertIn("MCP transport contract", command)

    def test_probe_diagnostic_authorizes_the_probe_and_teamcity_servers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            trace = root / "trace.log"
            mcp_config = root / "mcp.json"
            mcp_config.write_text("{}")
            completed = subprocess.CompletedProcess([], 0)
            with mock.patch.object(run_case.subprocess, "run", return_value=completed) as invoked:
                run_case.invoke_agent(
                    "prompt", root, {}, trace, timeout=7, mcp_config=mcp_config,
                    use_local_mcp_probe=True,
                )

        command = invoked.call_args.args[0]
        self.assertIn("mcp__teamcity__*", command)
        self.assertIn("mcp__probe__*", command)

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

    def test_collector_keeps_only_safe_transport_profile_fields(self):
        raw = {
            "caseId": "example",
            "caseVersion": "a" * 64,
            "toolMode": "cli+mcp",
            "agentConfigId": "claude-teamcity",
            "agentVersion": "1.2.3",
        }

        self.assertEqual("cli+mcp", collector.tool_mode_of(raw))
        self.assertEqual(
            ("a" * 64, "claude-teamcity", "1.2.3"),
            collector.evaluation_profile(raw),
        )
        self.assertEqual(
            ("legacy", "default", "default"),
            collector.evaluation_profile(
                {
                    "caseVersion": "not-a-hash",
                    "agentConfigId": "unsafe value",
                    "agentVersion": "private/token",
                }
            ),
        )

    def test_collector_extracts_safe_transport_profile_from_artifact(self):
        artifact = {
            "caseId": "example",
            "caseVersion": "b" * 64,
            "toolMode": "mcp-only",
            "agentConfigId": "claude-teamcity",
            "agentVersion": "1.2.3",
            "agentToolSummary": {
                "totalCalls": 2,
                "mcpTeamCityCalls": 1,
                "privateInput": "must not escape",
            },
            "mcpRuntime": {
                "connectionStatus": "authentication-failed",
                "teamcityToolsAdvertised": False,
                "private": "must not escape",
            },
            "errorCategory": "mcp-authentication-failed",
            "checks": {"build": {"passed": True}},
        }

        def fake_cli(_server, *arguments):
            if arguments[1] == "artifacts":
                return subprocess.CompletedProcess(
                    [], 0, stdout=json.dumps({"file": [{"name": "eval-result.json"}]}), stderr=""
                )
            if arguments[1] == "download":
                destination = pathlib.Path(arguments[arguments.index("--output") + 1])
                (destination / "publish").mkdir()
                (destination / "publish" / "eval-result.json").write_text(json.dumps(artifact))
                return subprocess.CompletedProcess([], 0, stdout="", stderr="")
            self.fail(f"unexpected CLI call: {arguments}")

        with mock.patch.object(collector, "cli", side_effect=fake_cli):
            result = collector.download_result([], "https://teamcity.example", 99)

        self.assertEqual("mcp-only", result["toolMode"])
        self.assertEqual("b" * 64, result["caseVersion"])
        self.assertEqual("claude-teamcity", result["agentConfigId"])
        self.assertEqual("1.2.3", result["agentVersion"])
        self.assertEqual(
            {"totalCalls": 2, "mcpTeamCityCalls": 1},
            result["agentToolSummary"],
        )
        self.assertEqual(
            {"connectionStatus": "authentication-failed", "teamcityToolsAdvertised": False},
            result["mcpRuntime"],
        )
        self.assertEqual("mcp-authentication-failed", result["errorCategory"])

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

        history = observed[("example", "cli-only", "skill")]["history"]
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

        self.assertEqual(0, observed[("example", "cli-only", "skill")]["history"]["sampleSize"])

    def test_pass_rate_does_not_mix_tool_modes(self):
        def job(identifier, tool_mode, classification):
            return {
                "id": identifier,
                "revision": "same",
                "classification": classification,
                "classificationDetail": classification,
                "url": f"https://teamcity.example/{identifier}",
                "result": {
                    "caseId": "example",
                    "toolMode": tool_mode,
                    "arm": "skill",
                },
            }

        observed = collector.latest_arm_observations(
            [job(3, "cli-only", "passed"), job(2, "mcp-only", "skill-output-failed")]
        )

        self.assertEqual(1, observed[("example", "cli-only", "skill")]["history"]["sampleSize"])
        self.assertEqual(1, observed[("example", "mcp-only", "skill")]["history"]["sampleSize"])

    def test_vcs_revision_reads_the_pipeline_head_change(self):
        self.assertEqual(
            "0123456789abcdef",
            collector.vcs_revision(
                {"lastChanges": {"change": [{"version": "0123456789abcdef"}]}}
            ),
        )


if __name__ == "__main__":
    unittest.main()
