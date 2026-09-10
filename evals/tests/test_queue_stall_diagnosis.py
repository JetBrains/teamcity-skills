import importlib.util
import json
import os
import pathlib
import subprocess
import tempfile
import unittest


EVALS = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, EVALS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_case = load_module("run_case_queue_stall_test", "run_case.py")
CASE = EVALS / "queue-stall-diagnosis/cases/queued-no-compatible-agent.json"


class QueueStallDiagnosisTest(unittest.TestCase):
    def setUp(self):
        self.case = json.loads(CASE.read_text())

    def test_grader_accepts_compatibility_checkpoint_without_retry_loop(self):
        observed = {
            "toolCalls": [
                'Bash {"command": "teamcity run view 73142 --json"}',
                'Bash {"command": "teamcity agent list --connected --enabled --authorized --json"}',
                'Bash {"command": "teamcity agent jobs 101 --incompatible --json"}',
                'Bash {"command": "teamcity pipeline pull QueueFixture --output /tmp/queue.yml"}',
                'Grep {"pattern": "%[^%]+%", "path": "/tmp/queue.yml"}',
            ],
            "finalText": (
                "There are no compatible agents. The stored configuration has "
                "an unresolved parameter env.JDK_25, so I stopped without retrying."
            ),
            "mutations": [],
        }

        checks = run_case.grade_queue_stall(self.case, observed)

        self.assertTrue(all(check["passed"] for check in checks.values()))

    def test_grader_accepts_first_class_job_view_diagnostic(self):
        observed = {
            "toolCalls": [
                'Bash {"command": "teamcity run view 73142 --json"}',
                'Bash {"command": "teamcity agent list --connected --json"}',
                'Bash {"command": "teamcity job view QueueFixture_Build --json"}',
                'Bash {"command": "teamcity pipeline pull QueueFixture --output /tmp/queue.yml"}',
                'Grep {"pattern": "%[^%]+%", "path": "/tmp/queue.yml"}',
            ],
            "finalText": (
                "There are no compatible agents because of an unresolved parameter, "
                "so I stopped without retrying."
            ),
            "mutations": [],
        }

        checks = run_case.grade_queue_stall(self.case, observed)

        self.assertTrue(all(check["passed"] for check in checks.values()))

    def test_grader_rejects_repeated_polling_and_duplicate_queueing(self):
        observed = {
            "toolCalls": [
                'Bash {"command": "teamcity run view 73142 --json"}',
                'Bash {"command": "sleep 180"}',
                'Bash {"command": "teamcity run view 73142 --json"}',
                'Bash {"command": "sleep 180"}',
                'Bash {"command": "teamcity queue list --json"}',
                'Bash {"command": "teamcity run start QueueFixture_Build"}',
                'Bash {"command": "teamcity run restart 73142"}',
            ],
            "finalText": "The run is still queued, so I will continue waiting.",
            "mutations": [],
        }

        checks = run_case.grade_queue_stall(self.case, observed)

        self.assertFalse(checks["compatibilityCheckpoint"]["passed"])
        self.assertFalse(checks["statusCheckLimit"]["passed"])
        self.assertFalse(checks["requiredDiagnostics"]["passed"])
        self.assertFalse(checks["diagnosticAgentInventory"]["passed"])
        self.assertFalse(checks["diagnosticJobIncompatibility"]["passed"])
        self.assertFalse(checks["diagnosticStoredParameters"]["passed"])
        self.assertFalse(checks["waitLimit"]["passed"])
        self.assertFalse(checks["noBlindRetry"]["passed"])
        self.assertFalse(checks["diagnosisReported"]["passed"])

    def test_fixture_exposes_a_two_minute_unresolved_parameter_stall(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = pathlib.Path(directory)
            env = run_case.install_queue_stall_fixture(workspace, dict(os.environ))
            queued = subprocess.run(
                [str(workspace / "fixture-bin/teamcity"), "run", "view", "73142", "--json"],
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            details = json.loads(queued.stdout)

            self.assertEqual(130, details["queuedDurationSeconds"])
            self.assertIn("no compatible agents", details["waitReason"].lower())

            output = workspace / "stored.yml"
            subprocess.run(
                [str(workspace / "fixture-bin/teamcity"), "pipeline", "pull", "QueueFixture",
                 "--output", str(output)],
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("%env.JDK_25%", output.read_text())


if __name__ == "__main__":
    unittest.main()
