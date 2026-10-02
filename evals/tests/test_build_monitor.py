"""Synthetic monitoring tests: no Claude, real trajectory or TeamCity writes."""

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

EVALS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS))
from build_monitor import LiveBuildMonitor, STOP_CATEGORY, safe_monitor_diagnostics
from first_green_evidence import terminal_chain_diagnostics, observe_chain


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, EVALS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load("monitor_runner", "run_case.py")
collector = load("monitor_collector", "collect_teamcity_eval_runs.py")


def node(identifier, job, status="SUCCESS", state="finished", children=None):
    return {"id": identifier, "buildTypeId": job, "status": status,
            "state": state, "dependencies": children or []}


class BuildMonitorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.path = self.root / ".teamcity.yml"
        self.path.write_text("jobs:\n  verify: {}\n")
        self.definition = {"jobs": {"verify": {}}}
        self.tree = node(10, "pipeline", "FAILURE", children=[node(11, "verify")])
        self.tc = mock.Mock(spec=["pipeline_ids", "pipeline_definition", "builds", "build_tree", "build"])
        self.tc.pipeline_ids.return_value = ["pipeline"]
        self.tc.pipeline_definition.return_value = self.definition
        self.tc.builds.return_value = [self.tree]
        self.tc.build_tree.return_value = self.tree
        self.tc.build.return_value = {**self.tree, "statusText": "canary secret, Tests passed: 39"}
        self.monitor = LiveBuildMonitor(self.tc, "only-project", self.root, ".teamcity.yml", clock=lambda: 100)
        self.output = io.StringIO()
        self.addCleanup(mock.patch.stopall)
        mock.patch("build_monitor.sys.stderr", self.output).start()

    def test_unexplained_terminal_head_stops_and_keeps_safe_ids(self):
        self.assertEqual(STOP_CATEGORY, self.monitor.checkpoint(7200))
        self.assertEqual(115, self.tc.deadline)
        diagnostic = self.monitor.diagnostics()
        self.assertEqual(60, diagnostic["intervalSeconds"])
        self.assertEqual("FAILURE", diagnostic["lastChain"]["headStatus"])
        self.assertEqual(1, diagnostic["lastChain"]["successfulChildCount"])
        self.assertEqual([{"id": 11, "state": "finished", "status": "SUCCESS"}],
                         diagnostic["lastChain"]["children"])
        self.assertEqual("unavailable", diagnostic["lastChain"]["problemEvidence"])
        self.assertNotIn("problemCount", diagnostic["lastChain"])
        self.assertNotIn("canary", json.dumps(diagnostic) + self.output.getvalue())
        self.assertFalse(diagnostic["stoppedAgent"])  # Only the process owner marks it.
        self.tc.pipeline_ids.assert_called_once_with("only-project")
        for call in self.tc.builds.call_args_list:
            self.assertEqual(("only-project", "pipeline"), call.args)

    def test_empty_problem_list_is_not_explanatory_evidence(self):
        self.tc.build.return_value["problemOccurrences"] = {"count": 0, "problemOccurrence": []}
        self.assertEqual(STOP_CATEGORY, self.monitor.checkpoint(7200))
        self.assertEqual(0, self.monitor.diagnostics()["lastChain"]["problemCount"])

    def test_available_problem_records_are_not_claimed_as_a_root_cause(self):
        self.tc.build.return_value["problemOccurrences"] = {
            "count": 1, "problemOccurrence": [{"details": "canary secret"}],
        }
        self.assertIsNone(self.monitor.checkpoint(7200))
        chain = self.monitor.diagnostics()["lastChain"]
        self.assertEqual("recorded", chain["problemEvidence"])
        self.assertTrue(chain["requiresInvestigation"])
        self.assertNotIn("canary", json.dumps(chain))

    def test_regular_build_failures_and_nonterminal_states_do_not_stop_agent(self):
        for head_status, head_state, child_status, child_state in (
            ("SUCCESS", "finished", "SUCCESS", "finished"),
            ("FAILURE", "finished", "FAILURE", "finished"),
            ("FAILURE", "running", "SUCCESS", "finished"),
            ("FAILURE", "finished", "SUCCESS", "running"),
            ("FAILURE", "queued", "SUCCESS", "queued"),
        ):
            with self.subTest(head=head_state, child=child_status, child_state=child_state):
                self.tree.update(status=head_status, state=head_state)
                self.tree["dependencies"][0].update(status=child_status, state=child_state)
                self.assertIsNone(self.monitor.checkpoint(7200))
        self.tc.build.assert_not_called()

    def test_missing_child_cannot_trigger_intervention(self):
        self.tree["dependencies"] = []
        self.assertIsNone(self.monitor.checkpoint(7200))

    def test_ignores_unbound_probe_and_ambiguous_source(self):
        for definitions in (
            {"probe": {"jobs": {"probe": {}}}},
            {"one": self.definition, "two": self.definition},
        ):
            self.tc.pipeline_ids.return_value = list(definitions)
            self.tc.pipeline_definition.side_effect = definitions.__getitem__
            self.assertIsNone(self.monitor.checkpoint(7200))
            self.assertEqual("waiting-for-pipeline", self.monitor.diagnostics()["state"])
        self.tc.build_tree.assert_not_called()

    def test_new_attempt_is_not_interrupted_using_an_old_head(self):
        self.tc.builds.side_effect = [[self.tree], [self.tree, node(12, "pipeline", state="running")]]
        self.assertIsNone(self.monitor.checkpoint(7200))

    def test_definition_changed_during_checkpoint_is_not_interrupted(self):
        self.tc.pipeline_definition.side_effect = [self.definition, {"jobs": {"different": {}}}]
        self.assertIsNone(self.monitor.checkpoint(7200))

    def test_local_source_changed_during_checkpoint_is_not_interrupted(self):
        def changed():
            self.path.write_text("jobs:\n  changed: {}\n")
            return {**self.tree}
        self.tc.build.side_effect = lambda *_: changed()
        self.assertIsNone(self.monitor.checkpoint(7200))

    def test_cli_or_identity_failure_is_visible_but_never_an_abort(self):
        self.tc.build.side_effect = RuntimeError("canary private server payload")
        self.assertIsNone(self.monitor.checkpoint(7200))
        self.assertEqual(1, self.monitor.diagnostics()["readFailureCount"])
        self.assertEqual("read-unavailable", self.monitor.diagnostics()["state"])
        self.assertNotIn("canary", self.output.getvalue())
        self.tc.build.side_effect = None
        self.tc.build.return_value = {**self.tree, "id": 999}
        self.assertIsNone(self.monitor.checkpoint(7200))

    def test_missing_incomplete_or_escaping_source_causes_no_server_reads(self):
        for source in ("missing.yml", "../outside.yml", None):
            self.monitor.source_path = source
            self.assertIsNone(self.monitor.checkpoint(7200))
        self.monitor.source_path = ".teamcity.yml"
        self.path.write_text("jobs: [")
        self.assertIsNone(self.monitor.checkpoint(7200))
        self.tc.pipeline_ids.assert_not_called()

    def test_duplicate_checkpoints_only_emit_state_changes(self):
        self.monitor.checkpoint(7200)
        first = self.output.getvalue()
        self.monitor.checkpoint(7200)
        self.assertEqual(first, self.output.getvalue())
        self.assertEqual(2, self.monitor.diagnostics()["checkCount"])

    def test_checkpoint_cannot_extend_agent_deadline(self):
        self.monitor.checkpoint(105)
        self.assertEqual(105, self.tc.deadline)
        tc = runner.TeamCity("teamcity", "https://example.invalid", "private", {}, command_timeout=10)
        tc.deadline = 105
        with mock.patch.object(runner.time, "monotonic", return_value=104), \
                mock.patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "{}")) as call:
            tc.build(10)
        self.assertEqual(1, call.call_args.kwargs["timeout"])
        self.assertEqual("https://example.invalid", call.call_args.kwargs["env"]["TEAMCITY_URL"])
        with mock.patch.object(runner.time, "monotonic", return_value=105), \
                mock.patch.object(runner.subprocess, "run") as call:
            with self.assertRaises(runner.EvalError):
                tc.build(10)
        call.assert_not_called()

    def test_post_agent_observation_also_retains_head_failure(self):
        self.tc.build.side_effect = lambda identifier: (
            {**self.tree} if identifier == 10 else
            {**self.tree["dependencies"][0], "buildType": {"name": "Verify"}}
        )
        tc = mock.Mock()
        tc.build = self.tc.build
        tc.jobs.return_value = [{"name": "Verify"}]
        tc.test_results.return_value = []
        tc.artifacts.return_value = []
        build = {"id": 10, "pipelineId": "pipeline", "selection": "source-matched",
                 "attempts": 1, "status": "FAILURE", "nodes": [self.tree, self.tree["dependencies"][0]]}
        observed, diagnostic = observe_chain(tc, "only-project", build, "21")
        self.assertEqual("FAILURE", observed["buildStatus"])
        self.assertTrue(diagnostic["terminalChain"]["requiresInvestigation"])
        self.assertEqual("unavailable", diagnostic["terminalChain"]["problemEvidence"])

    def test_missing_problem_metadata_is_distinct_from_measured_zero(self):
        nodes = [self.tree, self.tree["dependencies"][0]]
        missing = terminal_chain_diagnostics(nodes, 10, self.tree)
        zero = terminal_chain_diagnostics(nodes, 10, {**self.tree, "problemOccurrences": {"count": 0}})
        self.assertNotIn("problemCount", missing)
        self.assertEqual(0, zero["problemCount"])
        self.assertEqual("unavailable", missing["problemEvidence"])
        self.assertEqual("unavailable", zero["problemEvidence"])


class AgentInterventionTest(unittest.TestCase):
    def invoke(self, process, monitor, **patches):
        with tempfile.TemporaryDirectory() as folder, contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(runner.subprocess, "Popen", return_value=process))
            stop = stack.enter_context(mock.patch.object(runner, "stop_agent_processes"))
            stack.enter_context(mock.patch.object(runner.sys, "stderr", io.StringIO()))
            for name, value in patches.items():
                stack.enter_context(mock.patch.object(runner.time, name, **value))
            root = pathlib.Path(folder)
            result = runner.invoke_agent("synthetic", root, {}, root / "synthetic-trace", 7200,
                                         build_monitor=monitor)
            return result, stop

    def monitor(self, category=STOP_CATEGORY):
        monitor = mock.Mock(interval_seconds=60)
        monitor.checkpoint.return_value = category
        monitor.diagnostics.return_value = {"stoppedAgent": category == STOP_CATEGORY}
        return monitor

    def test_stops_whole_agent_group_without_claiming_timeout_or_grade(self):
        process = mock.Mock(returncode=-15)
        process.poll.return_value = None
        process.communicate.side_effect = subprocess.TimeoutExpired("synthetic", 60)
        monitor = self.monitor()
        result, stop = self.invoke(process, monitor)
        stop.assert_called_once_with(process)
        monitor.mark_stopped.assert_called_once()
        self.assertEqual(STOP_CATEGORY, result["failureCategory"])
        self.assertFalse(result["timedOut"])
        self.assertEqual(7200, result["timeoutSeconds"])
        self.assertNotIn("agentUsage", result)  # Missing usage is never fabricated as zero.

    def test_polling_never_resends_prompt(self):
        process = mock.Mock(returncode=0)
        process.communicate.side_effect = [subprocess.TimeoutExpired("synthetic", 60), (None, None)]
        result, stop = self.invoke(process, self.monitor(None))
        self.assertEqual("synthetic", process.communicate.call_args_list[0].kwargs["input"])
        self.assertIsNone(process.communicate.call_args_list[1].kwargs["input"])
        self.assertEqual(0, result["exitCode"])
        stop.assert_not_called()

    def test_agent_deadline_wins_without_extra_checkpoint(self):
        process = mock.Mock()
        process.communicate.side_effect = subprocess.TimeoutExpired("synthetic", 60)
        monitor = self.monitor()
        result, stop = self.invoke(process, monitor, monotonic={"side_effect": [0, 0, 7200]})
        self.assertTrue(result["timedOut"])
        stop.assert_called_once_with(process)
        monitor.checkpoint.assert_not_called()

    def test_completed_agent_is_not_falsely_marked_interrupted(self):
        process = mock.Mock(returncode=0)
        process.poll.return_value = 0
        process.communicate.side_effect = [subprocess.TimeoutExpired("synthetic", 60), (None, None)]
        monitor = self.monitor()
        result, stop = self.invoke(process, monitor)
        self.assertEqual(0, result["exitCode"])
        self.assertIsNone(result["failureCategory"])
        stop.assert_not_called()
        monitor.mark_stopped.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "POSIX process group regression")
    def test_live_intervention_stops_synthetic_descendant(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            child = "import time,pathlib; time.sleep(1); pathlib.Path('orphan').touch()"
            program = f"import subprocess,time; subprocess.Popen([{sys.executable!r}, '-c', {child!r}]); time.sleep(30)"
            command = shlex.quote(sys.executable) + " -c " + shlex.quote(program)
            monitor = self.monitor()
            monitor.interval_seconds = 0.1
            with mock.patch.object(runner.sys, "stderr", io.StringIO()):
                result = runner.invoke_agent("synthetic", root, {"EVAL_AGENT_CMD": command},
                                             root / "synthetic-trace", 10, build_monitor=monitor)
            time.sleep(1.2)
            self.assertEqual(STOP_CATEGORY, result["failureCategory"])
            self.assertFalse(result["timedOut"])
            self.assertFalse((root / "orphan").exists())

    def test_safe_result_and_collector_keep_alert_without_private_data(self):
        diagnostic = {"checkCount": 1, "readFailureCount": 0, "intervalSeconds": 60,
                      "stoppedAgent": True, "state": "intervened", "private": "canary",
                      "lastChain": {"headId": 10, "headStatus": "FAILURE",
                                    "problemEvidence": "unavailable", "statusText": "canary"}}
        published = runner.publishable_result({"status": "errored", "checks": {},
            "errorCategory": STOP_CATEGORY, "verificationErrorCategory": STOP_CATEGORY,
            "buildMonitorDiagnostics": diagnostic})
        self.assertNotIn("canary", json.dumps(published))
        self.assertNotIn("agentUsage", published)
        self.assertEqual({}, published["checks"])
        self.assertEqual(STOP_CATEGORY, collector.classify(None, {"state": "finished"}, published)[0])
        self.assertEqual(STOP_CATEGORY, collector.safe_error_category(STOP_CATEGORY))
        self.assertEqual(published["buildMonitorDiagnostics"], safe_monitor_diagnostics(diagnostic))

    def test_completed_grade_keeps_verdict_but_explains_diagnostic_gap(self):
        category, detail = collector.classify(None, {"state": "finished"}, {
            "status": "failed", "checks": {"firstBuild": {"passed": False}},
            "verificationErrorCategory": STOP_CATEGORY,
        })
        self.assertEqual("skill-output-failed", category)
        self.assertIn("cause unavailable through CLI", detail)

    def test_runner_intervention_skips_build_wait_grade_and_retry(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as stack:
            root = pathlib.Path(directory)
            case = root / "case.json"
            case.write_text(json.dumps({
                "id": "synthetic", "kind": "first-green-build", "status": "draft",
                "prompt": "synthetic", "repository": {"defaultBranch": "main"},
                "requestedConfiguration": {"format": "pipeline-yaml", "sourcePath": ".teamcity.yml"},
            }))
            tc = mock.Mock()
            tc.create_project.return_value = "only-project"
            bridge = mock.MagicMock()
            bridge.__enter__.return_value.agent_environment.return_value = {}
            stack.enter_context(mock.patch.dict(runner.os.environ, {
                "TEAMCITY_URL": "https://example.invalid", "TEAMCITY_TOKEN": "canary",
            }, clear=True))
            stack.enter_context(mock.patch.object(runner, "TeamCity", return_value=tc))
            stack.enter_context(mock.patch.object(runner, "TeamCityCliBridge", return_value=bridge))
            stack.enter_context(mock.patch.object(runner.shutil, "which", return_value="teamcity"))
            stack.enter_context(mock.patch.object(runner, "checkout_repository"))
            stack.enter_context(mock.patch.object(runner.sys, "stderr", io.StringIO()))
            for name, value in (("agent_usage", {}), ("agent_tool_summary", {}),
                                ("permission_failure_surface", None)):
                stack.enter_context(mock.patch.object(runner, name, return_value=value))
            invoke = stack.enter_context(mock.patch.object(runner, "invoke_agent", return_value={
                "exitCode": -15, "timedOut": False, "timeoutSeconds": 3600,
                "failureCategory": STOP_CATEGORY,
                "buildMonitorDiagnostics": {"stoppedAgent": True, "state": "intervened",
                    "lastChain": {"headId": 10, "headStatus": "FAILURE", "problemEvidence": "unavailable"}},
            }))
            wait = stack.enter_context(mock.patch.object(runner, "wait_for_build"))
            grade = stack.enter_context(mock.patch.object(runner, "grade"))
            result = runner.publishable_result(runner.run(case, False, False, "baseline", "cli-only"))
            self.assertIsInstance(invoke.call_args.kwargs["build_monitor"], LiveBuildMonitor)
            self.assertEqual("errored", result["status"])
            self.assertEqual(STOP_CATEGORY, result["errorCategory"])
            self.assertEqual(STOP_CATEGORY, result["verificationErrorCategory"])
            self.assertEqual({}, result["checks"])
            self.assertNotIn("gradeStatus", result)
            self.assertNotIn("agentUsage", result)
            self.assertNotIn("canary", json.dumps(result))
            wait.assert_not_called()
            grade.assert_not_called()
            invoke.assert_called_once()

    def test_collector_download_preserves_safe_monitor_evidence(self):
        def cli(_server, *args):
            if args[:2] == ("run", "artifacts"):
                return subprocess.CompletedProcess([], 0, json.dumps({"file": [{"name": "eval-result.json"}]}))
            destination = pathlib.Path(args[args.index("--output") + 1]) / "publish"
            destination.mkdir()
            (destination / "eval-result.json").write_text(json.dumps({
                "caseId": "synthetic", "status": "errored", "errorCategory": STOP_CATEGORY,
                "buildMonitorDiagnostics": {"stoppedAgent": True, "private": "canary",
                    "lastChain": {"headId": 10, "headStatus": "FAILURE", "private": "canary"}},
            }))
            return subprocess.CompletedProcess([], 0, "")
        with mock.patch.object(collector, "cli", side_effect=cli):
            result = collector.download_result([], "https://example.invalid", 20, {"synthetic"})
        self.assertEqual(10, result["buildMonitorDiagnostics"]["lastChain"]["headId"])
        self.assertEqual(STOP_CATEGORY, result["errorCategory"])
        self.assertNotIn("canary", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
