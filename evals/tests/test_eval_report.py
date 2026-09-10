import importlib.util
import pathlib
import unittest


EVALS = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, EVALS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renderer = load_module("render_eval_report_test", "render_teamcity_eval_report.py")


class EvalReportTest(unittest.TestCase):
    def test_report_renders_separate_arm_columns_and_unique_jobs(self):
        job = {
            "id": 42,
            "classification": "passed",
            "classificationDetail": "all recorded assertions passed",
            "result": {"caseId": "example", "arm": "skill"},
            "durationSeconds": 10,
        }
        data = {
            "summary": {
                "caseContracts": 2,
                "pairedCaseContracts": 1,
                "expectedArmSlots": 2,
                "distinctArmsObserved": 1,
                "jobRunsObserved": 1,
                "classifications": {"passed": 1},
            },
            "cases": [
                {
                    "id": "example",
                    "kind": "pipeline-configuration",
                    "gate": "active",
                    "executionModel": "paired-arms",
                    "scope": "Grades configuration.",
                    "assertions": ["server validation"],
                    "targets": [],
                    "arms": {
                        "skill": {
                            "classification": "passed",
                            "detail": "all recorded assertions passed",
                            "runId": 42,
                            "history": {
                                "sampleSize": 3,
                                "passCount": 2,
                                "passRate": 0.667,
                                "targetMinSamples": 3,
                            },
                        },
                        "baseline": None,
                    },
                },
                {
                    "id": "preflight",
                    "kind": "teamcity-access-preflight",
                    "gate": "active",
                    "executionModel": "preflight",
                    "scope": "Checks access.",
                    "assertions": ["authentication"],
                    "targets": [],
                    "arms": None,
                },
            ],
            "pipelines": [
                {"id": "one", "runs": [{"jobs": [job]}]},
                {"id": "two", "runs": [{"jobs": [job]}]},
            ],
        }

        report = renderer.render(data)

        self.assertIn("Case × arm matrix", report)
        self.assertIn('<th scope="col">Skill</th><th scope="col">Baseline</th>', report)
        self.assertIn("not arm-based", report)
        self.assertIn("run 42", report)
        self.assertIn("same-revision pass rate: 2/3 (67%); measured", report)
        self.assertIn("token/cost telemetry has not been reported", report)
        self.assertEqual(1, report.count("<td>42</td>"))

    def test_report_shows_run_usage_and_distinguishes_missing_cost(self):
        job = {
            "id": 42,
            "classification": "passed",
            "classificationDetail": "passed",
            "result": {
                "caseId": "example",
                "arm": "skill",
                "agentUsage": {"inputTokens": 100, "outputTokens": 20},
            },
        }
        data = {
            "summary": {
                "jobRunsObserved": 1,
                "classifications": {"passed": 1},
                "agentUsage": {
                    "runsMeasured": 1,
                    "inputTokens": 100,
                    "outputTokens": 20,
                    "fieldsMeasured": {
                        "inputTokens": 1,
                        "outputTokens": 1,
                        "totalCostUsd": 0,
                    },
                },
            },
            "cases": [],
            "pipelines": [{"id": "one", "runs": [{"jobs": [job]}]}],
        }

        report = renderer.render(data)

        self.assertIn("100 in · 20 out", report)
        self.assertIn("provider cost not reported", report)
        self.assertIn("provider cost unavailable", report)


if __name__ == "__main__":
    unittest.main()
