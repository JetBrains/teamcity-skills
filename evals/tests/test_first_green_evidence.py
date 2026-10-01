import copy
import importlib.util
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
import first_green_evidence as evidence

spec = importlib.util.spec_from_file_location("chain_runner", EVALS / "run_case.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def node(build_id, job, status="SUCCESS", state="finished", children=None):
    return {"id": build_id, "buildTypeId": job, "state": state,
            "status": status, "dependencies": children or []}


class FirstGreenEvidenceTest(unittest.TestCase):
    def fixture(self):
        tc = mock.Mock()
        tc.pipeline_ids.return_value = ["main"]
        tc.pipeline_definition.return_value = {"jobs": {"test": {}, "package": {}}}
        tc.builds.return_value = [{"id": 10, "buildTypeId": "main"},
                                  {"id": 999, "buildTypeId": "probe"},
                                  {"id": 102, "buildTypeId": "package"}]
        tree = node(10, "main", children=[node(101, "test"), node(102, "package")])
        tc.build_tree.return_value = tree
        tc.build.side_effect = lambda build_id: {
            **next(item for item in tree["dependencies"] if item["id"] == build_id),
            "buildType": {"name": "Tests" if build_id == 101 else "Package"},
        }
        tc.jobs.return_value = [{"name": name, "parameters": {"env.JAVA_HOME": "%env.JDK_21_0%"}}
                                for name in ("Tests", "Package")]
        tc.test_results.side_effect = lambda build_id: [
            {"name": "Example.contextLoads", "status": "SUCCESS", "ignored": False}
        ] if build_id == 101 else []
        tc.artifacts.side_effect = lambda build_id: ["app.jar"] if build_id == 102 else []
        return tc, tree

    def test_selects_source_not_probe_name_or_latest_id(self):
        source = {"jobs": {"test": {}, "package": {}}}
        definitions = {"anything": source, "MainVerification": {"jobs": {"probe": {}}}}
        self.assertEqual(("anything", "source-matched"), evidence.select_pipeline(definitions, source))
        tc, _ = self.fixture()
        build = runner.wait_for_build(tc, "project", 10)
        self.assertEqual(10, build["id"])
        self.assertEqual(1, build["attempts"])
        tc.builds.assert_called_once_with("project", "main")

    def test_ambiguous_or_mismatched_source_fails_closed(self):
        for definitions, source in [({"a": {}, "b": {}}, None),
                                    ({"a": {}, "b": {}}, {}),
                                    ({"a": {"jobs": {"probe": {}}}}, {"jobs": {"test": {}}})]:
            with self.subTest(definitions=definitions, source=source):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.select_pipeline(definitions, source)

    def test_local_source_binds_multiple_pipelines(self):
        tc, _ = self.fixture()
        tc.pipeline_ids.return_value = ["main", "probe"]
        tc.pipeline_definition.side_effect = lambda key: {"jobs": {"test": {}} if key == "main" else {"probe": {}}}
        for source_path in (".teamcity.yml", "ci/final.yml"):
            with self.subTest(source_path=source_path), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                source = root / source_path
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("jobs:\n  test: {}\n")
                build = runner.wait_for_build(tc, "project", 10, checkout=root,
                                              case={"requestedConfiguration": {"sourcePath": source_path}})
            self.assertEqual("source-matched", build["selection"])

    def test_waits_failed_sibling_despite_successful_head_and_package(self):
        tc, terminal = self.fixture()
        terminal["dependencies"][0]["status"] = "FAILURE"
        running = copy.deepcopy(terminal)
        running["dependencies"][0]["state"] = "running"
        tc.build_tree.side_effect = [running, terminal]
        with mock.patch.object(runner.time, "sleep") as pause:
            build = runner.wait_for_build(tc, "project", 10)
        self.assertEqual("FAILURE", build["status"])
        pause.assert_called_once()
        self.assertEqual([mock.call(10), mock.call(10)], tc.build_tree.call_args_list)

    def test_actual_chain_outlives_failed_agents_no_build_grace(self):
        tc, terminal = self.fixture()
        running = copy.deepcopy(terminal)
        running["dependencies"][0]["state"] = "running"
        tc.build_tree.side_effect = [running, terminal]
        clock = [0]
        with mock.patch.object(runner.time, "time", side_effect=lambda: clock[0]), \
                mock.patch.object(runner.time, "sleep", side_effect=lambda _: clock.__setitem__(0, 5)):
            self.assertEqual("SUCCESS", runner.wait_for_build(tc, "project", 10, no_build_timeout=1)["status"])

    def test_nested_reused_dependency_counted_once(self):
        tc, tree = self.fixture()
        tree["dependencies"][1]["dependencies"] = [copy.deepcopy(tree["dependencies"][0])]
        build = runner.wait_for_build(tc, "project", 10)
        observed, diagnostics = evidence.observe_chain(tc, "project", build, "21")
        self.assertEqual(1, observed["testCount"])
        self.assertEqual(["app.jar"], observed["artifacts"])
        self.assertEqual(2, tc.test_results.call_count)
        self.assertEqual([101, 102], [item["id"] for item in diagnostics["builds"]])
        self.assertTrue(diagnostics["jdk"]["declaredMatch"])
        self.assertFalse(diagnostics["jdk"]["runtimeVerified"])

    def test_missing_or_conflicting_tree_is_not_green(self):
        tc, tree = self.fixture()
        for corrupt in [node(10, "wrong"), {"id": 10, "buildTypeId": "main"},
                        node(10, "main"), node(10, "main", children=[node(1, "test"), node(1, "test", "FAILURE")])]:
            tc.build_tree.return_value = corrupt
            with self.subTest(tree=corrupt):
                with self.assertRaises(evidence.EvidenceError):
                    runner.wait_for_build(tc, "project", 10)

    def test_missing_or_foreign_job_is_not_used_for_jdk_or_counts(self):
        tc, _ = self.fixture()
        tc.jobs.return_value = [{"name": "Different"}]
        build = runner.wait_for_build(tc, "project", 10)
        with self.assertRaises(evidence.EvidenceError):
            evidence.observe_chain(tc, "project", build, "21")
        tc.test_results.assert_not_called()

    def test_queued_dependency_checks_compatibility_not_just_head(self):
        tc, tree = self.fixture()
        tree["state"] = "running"
        tree["dependencies"][0]["state"] = "queued"
        tc.queue_wait_reason.return_value = "no-compatible-agents"
        clock = [0]
        with mock.patch.object(runner.time, "time", side_effect=lambda: clock[0]), \
                mock.patch.object(runner.time, "sleep", side_effect=lambda _: clock.__setitem__(0, 2)):
            with self.assertRaises(runner.BuildQueueStalled):
                runner.wait_for_build(tc, "project", 10, queue_check_after=2)
        self.assertEqual(101, tc.queue_wait_reason.call_args.args[0]["id"])

    def test_adapter_retains_only_selected_jdk_fields_and_inheritance(self):
        tc = runner.TeamCity("teamcity", "https://example.invalid", "private", {})
        definition = {"parameters": {"env.JAVA_HOME": "%env.JDK_17_0%", "private": "canary"},
                      "jobs": {"test": {"parameters": {"env.JAVA_HOME": "%env.JDK_21_0%"},
                                        "environment": {"JDK_HOME": "/jdk-21", "PASSWORD": "canary"}}}}
        with mock.patch.object(tc, "pipeline_definition", return_value=definition):
            jobs = tc.jobs("project", "main")
        self.assertNotIn("canary", json.dumps(jobs))
        self.assertEqual({"env.JAVA_HOME": "%env.JDK_21_0%"}, jobs[0]["parameters"])
        self.assertTrue(evidence.jdk_evidence({}, "21", jobs)[0])

    def test_available_jdk_wrong_version_or_unconfigured_job_is_not_selection(self):
        for jobs in [[{"parameters": {"env.JDK_21_0": "/jdk-21"}}],
                     [{"parameters": {"env.JAVA_HOME": "%env.JDK_121_0%"}}],
                     [{"environment": {"JAVA_HOME": "/jdk-21"}}, {}]]:
            with self.subTest(jobs=jobs):
                self.assertFalse(evidence.jdk_evidence({}, "21", jobs)[0])

    def test_runtime_version_is_separate_and_overrides_declaration(self):
        jobs = [{"environment": {"JAVA_HOME": "/jdk-21"}}]
        matched, _, diagnostic = evidence.jdk_evidence({"java.version": "17.0.1"}, "21", jobs)
        self.assertFalse(matched)
        self.assertTrue(diagnostic["declaredMatch"])
        self.assertFalse(diagnostic["runtimeVerified"])
        self.assertTrue(evidence.jdk_evidence({"java.version": "21.0.1"}, "21", jobs)[2]["runtimeVerified"])

    def test_safe_diagnostics_strip_private_values(self):
        published = runner.publishable_result({"checks": {}, "verificationDiagnostics": {
            "headId": 10, "private": "canary", "selection": "source-matched",
            "builds": [{"id": 101, "status": "SUCCESS", "testCount": 1, "script": "canary"}],
            "jdk": {"requiredMajor": 21, "runtimeVerified": False, "JAVA_HOME": "canary"},
        }})
        self.assertNotIn("canary", json.dumps(published))
        self.assertEqual(10, published["verificationDiagnostics"]["headId"])


class AgentBudgetTest(unittest.TestCase):
    def test_budget_validation(self):
        self.assertEqual(3, runner.agent_budget("3"))
        for value in ("nan", "inf", "0", "-1", "3; echo canary", "1e9", ""):
            with self.subTest(value=value), self.assertRaises(runner.EvalError):
                runner.agent_budget(value)

    def test_budget_flag_and_new_process_group(self):
        process = mock.Mock(returncode=0)
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(runner.subprocess, "Popen", return_value=process) as invoked:
            root = pathlib.Path(directory)
            runner.invoke_agent("synthetic", root, {"EVAL_AGENT_MAX_BUDGET_USD": "3"}, root / "trace", 10)
        self.assertIn("--max-budget-usd 3", invoked.call_args.args[0])
        self.assertEqual(os.name == "posix", invoked.call_args.kwargs["start_new_session"])

    def test_budget_error_with_exit_zero_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "synthetic"
            trace.write_text(json.dumps({"type": "result", "subtype": "error_max_budget_usd", "is_error": True}))
            category = runner.agent_result_category(trace)
        result = {"checks": {"build": {"passed": True}}}
        runner.set_graded_status(result, {"timedOut": False, "exitCode": 0, "failureCategory": category})
        self.assertEqual("agent-budget-exhausted", result["errorCategory"])
        self.assertEqual("errored", result["status"])

    @unittest.skipUnless(os.name == "posix", "POSIX process group test")
    def test_timeout_stops_descendant_instead_of_only_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            # The delayed marker would appear if a grandchild survived timeout.
            child = "import time,pathlib; time.sleep(2); pathlib.Path('orphan').touch()"
            program = f"import subprocess,time; subprocess.Popen([{sys.executable!r}, '-c', {child!r}]); time.sleep(30)"
            command = shlex.quote(sys.executable) + " -c " + shlex.quote(program)
            result = runner.invoke_agent("synthetic", root, {"EVAL_AGENT_CMD": command}, root / "trace", timeout=1)
            time.sleep(1.5)
            self.assertTrue(result["timedOut"])
            self.assertFalse((root / "orphan").exists())


if __name__ == "__main__":
    unittest.main()
