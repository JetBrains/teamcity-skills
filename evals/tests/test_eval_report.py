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
        self.assertEqual(1, report.count("<td>42</td>"))


if __name__ == "__main__":
    unittest.main()
