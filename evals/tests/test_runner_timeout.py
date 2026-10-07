import importlib.util
import io
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
    def test_first_green_agent_has_no_default_deadline(self):
        self.assertIsNone(run_case.agent_timeout_seconds(None, "first-green-build"))
        self.assertEqual(3600, run_case.agent_timeout_seconds(None, "pipeline-configuration"))
        self.assertEqual(7200, run_case.agent_timeout_seconds("7200", "first-green-build"))
        self.assertIsNone(run_case.agent_timeout_seconds("0", "pipeline-configuration"))
        with self.assertRaises(run_case.EvalError):
            run_case.agent_timeout_seconds("-1", "first-green-build")

    def test_phase_monitor_records_fixed_durations_and_safe_events(self):
        ticks = iter((0, 1, 3, 8, 10))
        output = io.StringIO()
        with mock.patch.object(run_case.sys, "stderr", output):
            phases = run_case.PhaseMonitor(heartbeat_seconds=3600, clock=lambda: next(ticks))
            phases.enter("preparation")
            phases.enter("agent")
            phases.enter("buildWait")
            timings = phases.finish()

        self.assertEqual(
            {
                "preparationSeconds": 2,
                "agentSeconds": 5,
                "buildWaitSeconds": 2,
                "totalSeconds": 10,
            },
            timings,
        )
        self.assertIn("[eval-timing] agent finished in 5s", output.getvalue())

    def test_phase_timings_allowlist_rejects_private_and_invalid_values(self):
        published = run_case.publishable_result({
            "checks": {},
            "phaseTimings": {
                "bootstrapSeconds": 8,
                "agentSeconds": 123.4567,
                "buildWaitSeconds": 60,
                "totalSeconds": float("inf"),
                "privateProjectId": "do-not-publish",
                "gradingSeconds": True,
            },
        })

        self.assertEqual(
            {"bootstrapSeconds": 8, "agentSeconds": 123.457, "buildWaitSeconds": 60},
            published["phaseTimings"],
        )
        self.assertNotIn("do-not-publish", json.dumps(published))

    def test_harness_revision_is_checked_before_publication(self):
        revision = "a" * 40
        with mock.patch.object(
            run_case.subprocess, "run",
            return_value=subprocess.CompletedProcess([], 0, stdout=revision + "\n"),
        ):
            self.assertEqual(revision, run_case.harness_revision())

        self.assertEqual(
            revision,
            run_case.publishable_result({"harnessRevision": revision, "checks": {}})["harnessRevision"],
        )
        self.assertNotIn(
            "harnessRevision",
            run_case.publishable_result({"harnessRevision": "private-value", "checks": {}}),
        )

    def test_build_wait_distinguishes_no_build_from_unfinished_build(self):
        tc = mock.Mock()
        tc.builds.return_value = []
        with self.assertRaises(run_case.NoBuildQueued):
            run_case.wait_for_build(tc, "project", timeout=0)

        tc.builds.return_value = [{"id": 42}]
        tc.pipeline_ids.return_value = ["pipeline"]
        tc.pipeline_definition.return_value = {"jobs": {"verify": {}}}
        tc.builds.return_value = [{"id": 42, "buildTypeId": "pipeline"}]
        tc.build_tree.return_value = {"id": 42, "buildTypeId": "pipeline", "state": "running", "dependencies": []}
        with mock.patch.object(run_case.time, "time", side_effect=(0, 0, 0, 2)), \
                mock.patch.object(run_case.time, "sleep"):
            with self.assertRaises(run_case.BuildWaitTimeout):
                run_case.wait_for_build(tc, "project", timeout=1)

    def test_queue_reason_is_read_only_for_the_queued_job_and_sanitized(self):
        tc = run_case.TeamCity("teamcity", "https://teamcity.example", "private", {})
        with mock.patch.object(tc, "_run", return_value={
            "build": [
                {"id": 41, "waitReason": "another build"},
                {"id": 42, "waitReason": "There are no idle compatible agents which can run this build"},
            ]
        }) as command:
            reason = tc.queue_wait_reason({"id": 42, "buildTypeId": "target-job"})

        self.assertEqual("no-idle-compatible-agents", reason)
        command.assert_called_once_with(
            ["queue", "list", "--job", "target-job", "--json=id,waitReason"],
            json_output=True,
        )
        published = run_case.publishable_result({
            "checks": {}, "queueWaitReason": "private queue details",
        })
        self.assertEqual("other", published["queueWaitReason"])

    def test_queued_build_stops_after_grace_period_instead_of_full_build_timeout(self):
        tc = mock.Mock()
        tc.pipeline_ids.return_value = ["target-job"]
        tc.pipeline_definition.return_value = {"jobs": {"verify": {}}}
        tc.builds.return_value = [{"id": 42, "buildTypeId": "target-job"}]
        tc.build_tree.return_value = {"id": 42, "state": "queued", "buildTypeId": "target-job", "dependencies": []}
        tc.queue_wait_reason.return_value = "no-idle-compatible-agents"
        clock = [0]

        with mock.patch.object(run_case.time, "time", side_effect=lambda: clock[0]), \
                mock.patch.object(run_case.time, "sleep", side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
            with self.assertRaises(run_case.BuildQueueStalled) as stalled:
                run_case.wait_for_build(
                    tc, "project", timeout=3600, poll=1,
                    queue_check_after=2, queue_stall_timeout=4,
                )

        self.assertEqual(4, clock[0])
        self.assertEqual("no-idle-compatible-agents", stalled.exception.reason)
        self.assertEqual(1, tc.queue_wait_reason.call_count)
        self.assertEqual(
            ("build-queue-stalled", "build remained queued; TeamCity reported no idle compatible agents"),
            collector.classify(None, {"state": "finished", "status": "FAILURE"}, {
                "errorCategory": "build-queue-stalled",
                "queueWaitReason": stalled.exception.reason,
            }),
        )

    def test_unresolved_queue_requirement_stops_at_checkpoint(self):
        tc = mock.Mock()
        tc.pipeline_ids.return_value = ["target-job"]
        tc.pipeline_definition.return_value = {"jobs": {"verify": {}}}
        tc.builds.return_value = [{"id": 42, "buildTypeId": "target-job"}]
        tc.build_tree.return_value = {"id": 42, "state": "queued", "buildTypeId": "target-job", "dependencies": []}
        tc.queue_wait_reason.return_value = "unresolved-parameters"
        clock = [0]

        with mock.patch.object(run_case.time, "time", side_effect=lambda: clock[0]), \
                mock.patch.object(run_case.time, "sleep", side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
            with self.assertRaises(run_case.BuildQueueStalled) as stalled:
                run_case.wait_for_build(
                    tc, "project", timeout=3600, poll=1,
                    queue_check_after=2, queue_stall_timeout=600,
                )

        self.assertEqual(2, clock[0])
        self.assertEqual("unresolved-parameters", stalled.exception.reason)

    def test_first_green_error_publishes_phase_timings_and_fixed_wait_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            case_path = pathlib.Path(directory) / "case.json"
            case_path.write_text(json.dumps({
                "id": "example-first-green",
                "kind": "first-green-build",
                "status": "draft",
                "prompt": "create a build",
                "repository": {"defaultBranch": "main"},
            }))
            teamcity = mock.Mock()
            teamcity.create_project.return_value = "private-project"
            bridge = mock.MagicMock()
            bridge.__enter__.return_value.agent_environment.return_value = {}
            environment = {
                "TEAMCITY_URL": "https://teamcity.example",
                "TEAMCITY_TOKEN": "private-token",
                "EVAL_WRAPPER_BOOTSTRAP_SECONDS": "3",
            }
            with mock.patch.dict(run_case.os.environ, environment, clear=True), \
                    mock.patch.object(run_case.shutil, "which", return_value="teamcity"), \
                    mock.patch.object(run_case, "TeamCity", return_value=teamcity), \
                    mock.patch.object(run_case, "TeamCityCliBridge", return_value=bridge), \
                    mock.patch.object(run_case, "checkout_repository"), \
                    mock.patch.object(run_case, "invoke_agent", return_value={
                        "exitCode": 0, "timedOut": False, "timeoutSeconds": None,
                    }) as invoked, \
                    mock.patch.object(run_case, "agent_usage", return_value={}), \
                    mock.patch.object(run_case, "trace_error_category", return_value=None), \
                    mock.patch.object(run_case, "permission_failure_surface", return_value=None), \
                    mock.patch.object(run_case, "agent_tool_summary", return_value={}), \
                    mock.patch.object(run_case, "wait_for_build", side_effect=run_case.NoBuildQueued("private")), \
                    mock.patch.object(run_case.sys, "stderr", io.StringIO()):
                result = run_case.run(case_path, False, False, "baseline", "cli-only")

        published = run_case.publishable_result(result)
        self.assertEqual("errored", published["status"])
        self.assertEqual("build-not-queued", published["errorCategory"])
        self.assertEqual(3, published["phaseTimings"]["bootstrapSeconds"])
        self.assertIn("agentSeconds", published["phaseTimings"])
        self.assertIn("buildWaitSeconds", published["phaseTimings"])
        self.assertIsNone(invoked.call_args.args[4])
        self.assertNotIn("agentTimeoutSeconds", published)
        self.assertNotIn("private-project", json.dumps(published))
        self.assertNotIn("private-token", json.dumps(published))

    def test_invoke_agent_without_limit_waits_for_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            process = mock.Mock(returncode=0)
            with mock.patch.object(run_case.subprocess, "Popen", return_value=process), \
                    mock.patch.object(run_case, "stop_agent_processes") as stop:
                outcome = run_case.invoke_agent(
                    "prompt", pathlib.Path(directory), {}, trace, timeout=None,
                )

            self.assertEqual(0, outcome["exitCode"])
            self.assertFalse(outcome["timedOut"])
            self.assertIsNone(outcome["timeoutSeconds"])
            process.communicate.assert_called_once_with(input="prompt", timeout=None)
            stop.assert_not_called()

    def test_invoke_agent_turns_timeout_into_structured_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            trace = root / "trace.log"
            process = mock.Mock(returncode=0)
            process.communicate.side_effect = subprocess.TimeoutExpired("claude", 7)
            with mock.patch.object(run_case.subprocess, "Popen", return_value=process), \
                    mock.patch.object(run_case, "stop_agent_processes") as stop:
                outcome = run_case.invoke_agent(
                    "prompt", root, {}, trace, timeout=7, tools=["Read"]
                )

            self.assertEqual(124, outcome["exitCode"])
            self.assertTrue(outcome["timedOut"])
            self.assertEqual(7, outcome["timeoutSeconds"])
            self.assertIn("Agent timed out after 7s", trace.read_text())
            stop.assert_called_once_with(process)

    def test_invoke_agent_does_not_pass_lifecycle_token_to_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            completed = mock.Mock(returncode=0)
            with mock.patch.object(run_case.subprocess, "Popen", return_value=completed) as invoked:
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
            completed = mock.Mock(returncode=0)
            with mock.patch.object(run_case.subprocess, "Popen", return_value=completed) as invoked:
                run_case.invoke_agent(
                    "prompt", root, {}, trace, timeout=7,
                    tools=["Read"], mcp_config=mcp_config,
                )

        command = invoked.call_args.args[0]
        self.assertIn("Read", command)
        self.assertIn("mcp__teamcity__*", command)

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
            completed = mock.Mock(returncode=0)
            with mock.patch.object(run_case.subprocess, "Popen", return_value=completed) as invoked:
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
            completed = mock.Mock(returncode=0)
            with mock.patch.object(run_case.subprocess, "Popen", return_value=completed) as invoked:
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

    def test_nonzero_exit_cannot_pass_even_when_checks_are_green(self):
        result = {"checks": {"build": {"passed": True}}}
        run_case.set_graded_status(result, {"exitCode": 1, "timedOut": False, "timeoutSeconds": 300})
        self.assertEqual("passed", result["gradeStatus"])
        self.assertEqual("errored", result["status"])
        self.assertEqual("agent-exit-failed", result["errorCategory"])

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

    def test_collector_classifies_build_wait_failures_without_raw_errors(self):
        run = {"id": 1, "state": "finished", "status": "FAILURE"}
        category, detail = collector.classify(
            "https://teamcity.example", run,
            {"status": "errored", "errorCategory": "build-not-queued"},
        )
        self.assertEqual("build-not-queued", category)
        self.assertIn("no build appeared", detail)

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
            "phaseTimings": {
                "agentSeconds": 42.25,
                "buildWaitSeconds": 60,
                "totalSeconds": float("inf"),
                "private": "must not escape",
            },
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
        self.assertEqual(
            collector.agent_metadata_fingerprint("claude-teamcity"),
            result["agentConfigId"],
        )
        self.assertEqual(
            collector.agent_metadata_fingerprint("1.2.3"),
            result["agentVersion"],
        )
        self.assertEqual(
            {"totalCalls": 2, "mcpTeamCityCalls": 1},
            result["agentToolSummary"],
        )
        self.assertEqual(
            {"connectionStatus": "authentication-failed", "teamcityToolsAdvertised": False},
            result["mcpRuntime"],
        )
        self.assertEqual("mcp-authentication-failed", result["errorCategory"])
        self.assertEqual(
            {"agentSeconds": 42.25, "buildWaitSeconds": 60},
            result["phaseTimings"],
        )

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
        revision = "0123456789abcdef" + "0" * 24
        self.assertEqual(
            revision,
            collector.vcs_revision(
                {"lastChanges": {"change": [{"version": revision}]}}
            ),
        )


if __name__ == "__main__":
    unittest.main()
