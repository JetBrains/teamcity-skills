"""Synthetic command-boundary checks; these tests never launch a paid model."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

EVALS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS))
from auto_devops_cli_fixture import install_fixture


class AutoDevopsFixtureTest(unittest.TestCase):
    def test_reads_synthetic_history_records_read_only_and_refuses_a_remote_write(self):
        with tempfile.TemporaryDirectory() as directory:
            command, env, trace = install_fixture(Path(directory))
            result = subprocess.run([str(command), "run", "list", "--job", "Example_Verify",
                                     "--branch", "main", "--since", "14d", "--limit", "30", "--json"],
                                    env=env, text=True, capture_output=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual([101], [run["id"] for run in json.loads(result.stdout)])
            denied = subprocess.run([str(command), "run", "start", "Example_Verify"],
                                    env=env, text=True, capture_output=True)
            self.assertNotEqual(0, denied.returncode)
            calls = [json.loads(line) for line in trace.read_text().splitlines()]
            self.assertEqual([True, False], [call["allowed"] for call in calls])
            self.assertTrue(all(call["readOnly"] for call in calls))


    def test_timestamp_calculator_reports_seconds_and_refuses_non_timestamp_input(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            _, env, _ = install_fixture(workspace)
            calculator = workspace / "bin" / "time-delta-seconds"
            correct = subprocess.run([str(calculator), "20261110T090000+0000", "20261110T090505+0000"],
                                     env=env, text=True, capture_output=True)
            self.assertEqual(0, correct.returncode, correct.stderr)
            self.assertEqual(305, float(correct.stdout))
            for arguments in (["not-a-timestamp", "20261110T090505+0000"],
                              ["20261110T090000+0000"],
                              ["20261110T090505+0000", "20261110T090000+0000"]):
                with self.subTest(arguments=arguments):
                    refused = subprocess.run([str(calculator), *arguments], env=env,
                                             text=True, capture_output=True)
                    self.assertNotEqual(0, refused.returncode)


class AutoDevopsEvaluationTest(unittest.TestCase):
    def test_structured_report_requires_recorded_cli_evidence(self):
        from auto_devops_eval import evaluate
        document = json.loads((EVALS / "tests/fixtures/auto-devops-reports/partial-opportunity.json").read_text())
        for collect, expected in ((True, True), (False, False)):
            with self.subTest(collect=collect), tempfile.TemporaryDirectory() as directory:
                workspace = Path(directory)
                final = {"type": "result", "is_error": False, "total_cost_usd": 0,
                         "structured_output": {"report": document}}
                agent = workspace / "synthetic-agent.py"
                command = ("subprocess.run([os.environ['AUTO_DEVOPS_CLI'], 'job', 'step', 'list', "
                           "'Example_Verify', '--json'], check=True)\n") if collect else ""
                agent.write_text("import os, subprocess\n" + command + f"print({json.dumps(final)!r})\n")
                result = evaluate(workspace, agent_command=[sys.executable, str(agent)])
                self.assertEqual(expected, result["passed"], result)
                if not collect:
                    self.assertIn("no-cli-evidence", result["failures"])

    def test_runner_rejects_an_obviously_wrong_fixture_timestamp_delta(self):
        from auto_devops_eval import evaluate
        document = json.loads((EVALS / "tests/fixtures/auto-devops-reports/partial-opportunity.json").read_text())
        document.update(conclusion="none", recommendations=[])
        for seconds, expected in ((185, False), (305, True)):
            with self.subTest(seconds=seconds), tempfile.TemporaryDirectory() as directory:
                workspace = Path(directory)
                document["evidence"] = [{
                    "id": "e1", "sourceCommand": "teamcity run view 101 --json", "runIds": [101],
                    "observation": f"Queued-to-start time was {seconds} seconds.",
                }]
                agent = workspace / "synthetic-agent.py"
                agent.write_text(
                    "import os, subprocess\n"
                    "subprocess.run([os.environ['AUTO_DEVOPS_CLI'], 'run', 'view', '101', '--json'], check=True)\n"
                    f"print({json.dumps({'type': 'result', 'is_error': False, 'total_cost_usd': 0, 'structured_output': {'report': document}})!r})\n")
                result = evaluate(workspace, agent_command=[sys.executable, str(agent)])
                self.assertEqual(expected, result["passed"], result)
                if not expected:
                    self.assertIn("incorrect-fixture-timing", result["failures"])

    def test_persists_structured_provider_object_without_repairing_invalid_output(self):
        from auto_devops_eval import evaluate
        document = json.loads((EVALS / "tests/fixtures/auto-devops-reports/partial-opportunity.json").read_text())
        for version, expected in ((1, True), (2, False)):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                workspace = Path(directory)
                document["schemaVersion"] = version
                final = {"type": "result", "is_error": False, "total_cost_usd": 0,
                         "structured_output": {"report": document}}
                agent = workspace / "synthetic-agent.py"
                agent.write_text(
                    "import os, subprocess\n"
                    "subprocess.run([os.environ['AUTO_DEVOPS_CLI'], 'job', 'step', 'list', 'Example_Verify', '--json'], check=True)\n"
                    f"print({json.dumps(final)!r})\n")
                result = evaluate(workspace, agent_command=[sys.executable, str(agent)])
                self.assertEqual(expected, result["passed"], result)
                if expected:
                    self.assertEqual(document, json.loads((workspace / "report.json").read_text()))
                else:
                    self.assertIn("invalid-report", result["failures"])
                    self.assertFalse((workspace / "report.json").exists())

    def test_provider_command_avoids_top_level_combinators_and_preserves_report_contract(self):
        from auto_devops_eval import evaluate
        document = EVALS / "tests/fixtures/auto-devops-reports/partial-opportunity.json"
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            fake_provider = base / "claude"
            fake_provider.write_text(
                "#!" + sys.executable + "\n"
                "import json, os, pathlib, subprocess, sys\n"
                "from jsonschema import Draft7Validator\n"
                "schema = json.loads(sys.argv[sys.argv.index('--json-schema') + 1])\n"
                "assert not any(key in schema for key in ('oneOf', 'allOf', 'anyOf'))\n"
                f"report = json.loads(pathlib.Path({str(document)!r}).read_text())\n"
                "validator = Draft7Validator(schema)\n"
                "validator.validate({'report': report})\n"
                "invalid = json.loads(json.dumps(report))\n"
                "invalid['coverage']['state'] = 'blocked'\n"
                "assert not validator.is_valid({'report': invalid})\n"
                "subprocess.run([os.environ['AUTO_DEVOPS_CLI'], 'job', 'step', 'list', 'Example_Verify', '--json'], check=True)\n"
                "print(json.dumps({'type':'result', 'is_error':False, 'total_cost_usd':0, 'structured_output':{'report':report}}))\n")
            fake_provider.chmod(0o700)
            with mock.patch.dict(os.environ, {"PATH": str(base) + os.pathsep + os.environ["PATH"]}):
                result = evaluate(base / "evaluation", max_budget_usd=0.01)
            self.assertTrue(result["passed"], result)
            self.assertEqual(json.loads(document.read_text()),
                             json.loads((base / "evaluation/report.json").read_text()))
