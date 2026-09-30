import copy
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

EVALS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS))
from queue_recovery import JOB, ORIGINAL, PIPELINE, VERIFICATION, QueueRecoveryFixture, forbidden_queue_transport, safe_fixture_diagnostics


class QueueRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.workspace = pathlib.Path(self.directory.name)
        self.checkout = self.workspace / "checkout"
        self.checkout.mkdir()
        self.fixture = QueueRecoveryFixture("missing-os-family", self.workspace, self.checkout, {})

    def call(self, *args, succeeds=True):
        result = self.fixture.execute(list(args), self.checkout)
        self.assertEqual(0 if succeeds else 2, result.returncode, result.stderr)
        return result.stdout

    def diagnose(self):
        self.call("build", "view", ORIGINAL)
        self.call("agent", "list", "--connected", "--enabled", "--authorized")
        self.call("agent", "view", "101")
        self.call("agent", "jobs", "101", "--incompatible")
        self.path = self.workspace / "pipeline.yml"
        self.call("pipeline", "pull", PIPELINE, "--output", str(self.path))

    def correction(self):
        config = copy.deepcopy(self.fixture.config)
        if self.fixture.scenario == "missing-os-family":
            config["jobs"]["Build"]["runs-on"] = {"self-hosted": [{
                "requirement": "equals", "name": "actual-linux-engine",
                "parameter": "container.engine.osType", "value": "linux",
            }]}
        else:
            config["jobs"]["Build"]["steps"][-1]["script-content"] = ":; exit 0\n@echo off\nexit /b"
        self.path.write_text(yaml.safe_dump(config))
        return config

    def repair(self):
        self.diagnose()
        self.correction()
        self.call("pipeline", "validate", str(self.path))
        self.call("pipeline", "push", PIPELINE, "--file", str(self.path))
        self.call("pipeline", "pull", PIPELINE, "--output", str(self.path))
        self.call("job", "view", JOB)
        self.call("run", "cancel", ORIGINAL)
        self.call("run", "start", JOB, "--settings", "current")
        result = self.call("run", "watch", VERIFICATION, "--timeout", "60s")
        self.assertEqual("SUCCESS", json.loads(result)["status"])

    def test_os_repair_is_successful_only_after_actual_state_transitions(self):
        self.repair()
        self.assertTrue(all(c["passed"] for c in self.fixture.grade([]).values()))
        self.assertEqual(1, self.fixture.diagnostics()["pushAttempts"])
        self.assertEqual(0, self.fixture.diagnostics()["unrelatedChangeAttempts"])

    def test_rejected_changes_publish_categories_not_configuration(self):
        self.diagnose()
        config = self.correction()
        config["jobs"]["Build"]["steps"][0]["name"] = "private name"
        config["jobs"]["Build"]["steps"][0]["goals"] = "package"
        self.path.write_text(yaml.safe_dump(config))
        self.call("pipeline", "validate", str(self.path))
        self.call("pipeline", "push", PIPELINE, "--file", str(self.path), succeeds=False)
        diagnostics = self.fixture.diagnostics()
        self.assertEqual(1, diagnostics["stepMetadataChanges"])
        self.assertEqual(1, diagnostics["stepBehaviorChanges"])
        self.assertEqual(0, diagnostics["acceptedPushes"])
        self.assertNotIn("private", json.dumps(diagnostics))
        self.assertNotIn("package", json.dumps(diagnostics))

    def test_diagnostics_allowlist_drops_raw_data_and_invalid_counters(self):
        self.assertEqual({"acceptedPushes": 1}, safe_fixture_diagnostics({
            "acceptedPushes": 1, "pushAttempts": True, "statusReads": -1,
            "startAttempts": "secret", "cancellations": 1000001,
            "private configuration": 3,
        }))

    def test_unresolved_script_parameter_repair_preserves_verification(self):
        self.fixture = QueueRecoveryFixture("unresolved-script-parameter", self.workspace, self.checkout, {})
        self.repair()
        self.assertTrue(all(c["passed"] for c in self.fixture.grade([]).values()))

    def test_busy_compatible_agent_completes_without_config_change_or_retry(self):
        self.fixture = QueueRecoveryFixture("busy-compatible", self.workspace, self.checkout, {})
        self.diagnose()
        self.call("build", "watch", ORIGINAL, "--timeout", "1m")
        self.assertTrue(all(c["passed"] for c in self.fixture.grade([]).values()))
        self.assertEqual(0, self.fixture.pushes)
        self.assertEqual(0, self.fixture.starts)

    def test_changing_case_of_value_cannot_repair_missing_key(self):
        self.diagnose()
        config = copy.deepcopy(self.fixture.config)
        config["jobs"]["Build"]["runs-on"]["self-hosted"][0]["os-family"] = "linux"
        self.path.write_text(yaml.safe_dump(config))
        self.call("pipeline", "validate", str(self.path))
        self.call("pipeline", "push", PIPELINE, "--file", str(self.path))
        self.assertFalse(self.fixture.grade([])["compatibleAgentConfirmed"]["passed"])

    def test_removing_all_requirements_does_not_pass(self):
        self.diagnose()
        config = self.correction()
        config["jobs"]["Build"]["runs-on"] = "self-hosted"
        self.path.write_text(yaml.safe_dump(config))
        self.call("pipeline", "validate", str(self.path))
        self.call("pipeline", "push", PIPELINE, "--file", str(self.path))
        self.assertFalse(self.fixture.grade([])["compatibleAgentConfirmed"]["passed"])

    def test_weakening_build_or_artifacts_is_rejected(self):
        self.diagnose()
        config = self.correction()
        config["jobs"]["Build"]["steps"] = [{"type": "script", "script-content": "echo green"}]
        self.path.write_text(yaml.safe_dump(config))
        self.call("pipeline", "validate", str(self.path))
        self.call("pipeline", "push", PIPELINE, "--file", str(self.path), succeeds=False)
        self.assertFalse(self.fixture.grade([])["configurationPreserved"]["passed"])

    def test_unvalidated_push_remains_failure_even_if_later_validated(self):
        self.diagnose()
        self.correction()
        self.call("pipeline", "push", PIPELINE, "--file", str(self.path))
        self.call("pipeline", "validate", str(self.path))
        self.assertFalse(self.fixture.grade([])["noBlindRetry"]["passed"])

    def test_start_without_read_back_and_compatibility_is_not_a_pass(self):
        self.diagnose()
        self.correction()
        self.call("pipeline", "validate", str(self.path))
        self.call("pipeline", "push", PIPELINE, "--file", str(self.path))
        self.call("run", "cancel", ORIGINAL)
        self.call("run", "start", JOB, "--settings", "current")
        self.assertFalse(self.fixture.grade([])["noBlindRetry"]["passed"])

    def test_duplicate_and_unbounded_watch_are_failures(self):
        self.call("run", "start", JOB)
        for timeout in (None, "forever", "0s", "999m"):
            args = ["run", "watch", ORIGINAL]
            if timeout:
                args += ["--timeout", timeout]
            self.call(*args, succeeds=False)
        self.assertFalse(self.fixture.grade([])["noBlindRetry"]["passed"])

    def test_diagnosis_after_repeated_status_polling_is_too_late(self):
        self.call("run", "view", ORIGINAL)
        self.call("queue", "list")
        self.repair()
        self.assertFalse(self.fixture.grade([])["compatibilityCheckpoint"]["passed"])

    def test_unexecuted_command_claims_cannot_satisfy_checks(self):
        checks = self.fixture.grade([])
        self.assertFalse(checks["diagnosticAgentInventory"]["passed"])
        self.assertFalse(checks["fixtureBuildSucceeded"]["passed"])

    def test_source_change_is_not_hidden_by_green(self):
        self.repair()
        self.assertFalse(self.fixture.grade(["pom.xml"])["sourceMutations"]["passed"])

    def test_forbidden_transport_is_not_hidden_by_later_recovery(self):
        self.repair()
        self.assertFalse(self.fixture.grade([], forbidden_transport=True)["noBlindRetry"]["passed"])

    def test_transport_classifier_does_not_publish_or_execute_calls(self):
        self.assertTrue(forbidden_queue_transport(['Bash {"command":"teamcity api private"}']))
        self.assertTrue(forbidden_queue_transport(['Bash {"command":"curl https://teamcity.example/app/rest/builds"}']))
        self.assertFalse(forbidden_queue_transport(['Bash {"command":"teamcity build view 73142"}']))

    def test_busy_agent_must_not_be_cancelled(self):
        self.fixture = QueueRecoveryFixture("busy-compatible", self.workspace, self.checkout, {})
        self.diagnose()
        self.call("run", "cancel", ORIGINAL)
        self.assertFalse(self.fixture.grade([])["boundedRecovery"]["passed"])

    def test_capacity_progress_does_not_depend_on_doing_the_expected_diagnostics(self):
        self.fixture = QueueRecoveryFixture("busy-compatible", self.workspace, self.checkout, {})
        for _ in range(3):
            result = self.call("run", "view", ORIGINAL)
        self.assertEqual("SUCCESS", json.loads(result)["status"])
        self.assertTrue(self.fixture.grade([])["fixtureBuildSucceeded"]["passed"])
        self.assertFalse(self.fixture.grade([])["compatibilityCheckpoint"]["passed"])

    def test_actual_cli_client_uses_private_broker_state_without_real_token(self):
        with self.fixture:
            env = self.fixture.agent_environment({**os.environ, "TEAMCITY_TOKEN": "never-expose"})
            self.assertNotIn("TEAMCITY_TOKEN", env)
            client = self.fixture.wrapper_dir / "client.py"
            result = subprocess.run([sys.executable, str(client), "agent", "list"],
                                    cwd=self.checkout, env=env, capture_output=True, text=True, check=True)
            self.assertEqual(2, json.loads(result.stdout)["count"])
            self.assertEqual(["inventory"], self.fixture.events)
            self.assertNotIn("missing-os-family", client.read_text())
            self.assertNotIn("never-expose", client.read_text())

    def test_fixture_environment_is_explicitly_labelled_in_safe_result(self):
        spec = importlib.util.spec_from_file_location("run_case_recovery_test", EVALS / "run_case.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        result = runner.publishable_result({"evaluationEnvironment": "simulated", "checks": {}, "events": ["private"],
                                           "queueRecoveryDiagnostics": {"pushAttempts": 1, "private": "secret"}})
        self.assertEqual("simulated", result["evaluationEnvironment"])
        self.assertNotIn("events", result)
        self.assertEqual({"pushAttempts": 1}, result["queueRecoveryDiagnostics"])
        self.assertNotIn("evaluationEnvironment", runner.publishable_result({"evaluationEnvironment": "private text"}))

    def test_runner_uses_stateful_broker_and_does_not_create_live_project(self):
        spec = importlib.util.spec_from_file_location("run_case_recovery_integration", EVALS / "run_case.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        case_path = EVALS / "queue-recovery/cases/queued-busy-compatible-agent.json"

        def checkout(_case, path):
            path.mkdir()

        def invoke(_prompt, checkout, env, _trace, *args):
            cli = pathlib.Path(env["PATH"].split(os.pathsep)[0]) / "client.py"
            for command in (["run", "view", ORIGINAL], ["agent", "list"],
                            ["agent", "view", "101"], ["job", "view", JOB],
                            ["pipeline", "pull", PIPELINE], ["run", "watch", ORIGINAL, "--timeout", "60s"]):
                subprocess.run([sys.executable, str(cli), *command], cwd=checkout,
                               env=env, capture_output=True, check=True)
            return {"exitCode": 0, "timedOut": False, "timeoutSeconds": 300}

        with mock.patch.object(runner, "checkout_repository", side_effect=checkout), \
                mock.patch.object(runner, "invoke_agent", side_effect=invoke), \
                mock.patch.object(runner, "source_mutations", return_value=[]), \
                mock.patch.object(runner, "TeamCity") as live:
            result = runner.run(case_path, False, False, "baseline", "cli-only")
        live.assert_not_called()
        self.assertEqual("passed", result["status"])
        self.assertEqual("simulated", result["evaluationEnvironment"])
        self.assertEqual(set(json.loads(case_path.read_text())["expected"]), set(result["checks"]))


if __name__ == "__main__":
    unittest.main()
