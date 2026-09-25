import importlib.util
import pathlib
import unittest


EVALS = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, EVALS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


regressions = load_module("check_regressions_test", "check_regressions.py")


def job(identifier, revision, arm, passed, mode="cli-only", *, case_id="example"):
    return {
        "id": identifier,
        "revision": revision,
        "result": {
            "caseId": case_id,
            "caseVersion": "a" * 64,
            "agentConfigId": "claude-default",
            "agentVersion": "1.0",
            "toolMode": mode,
            "arm": arm,
            "checks": {
                "first": {"passed": passed[0]},
                "second": {"passed": passed[1]},
            },
        },
    }


def snapshot(*jobs):
    return {
        "cases": [
            {"id": "example", "gate": "active", "executionModel": "paired-arms"}
        ],
        "pipelines": [{"id": "eval", "runs": [{"jobs": list(jobs)}]}],
    }


def finding(result, kind, mode="cli-only"):
    return next(
        item for item in result["findings"]
        if item["kind"] == kind and item["toolMode"] == mode
    )


class RegressionCheckTest(unittest.TestCase):
    def test_insufficient_samples_is_reported_but_not_a_failure(self):
        result = regressions.evaluate(
            snapshot(
                job(2, "sha", "skill", (True, True)),
                job(1, "sha", "baseline", (False, False)),
            )
        )

        self.assertEqual("passed", result["status"])
        self.assertFalse(result["failures"])
        self.assertEqual(
            "insufficient-samples",
            finding(result, "skill-vs-baseline")["status"],
        )

    def test_skill_must_be_strictly_better_than_baseline(self):
        jobs = []
        for offset in range(3):
            jobs.extend(
                [
                    job(20 - offset * 2, "sha", "skill", (True, True)),
                    job(19 - offset * 2, "sha", "baseline", (True, False)),
                ]
            )

        result = regressions.evaluate(snapshot(*jobs))

        self.assertEqual("passed", result["status"])
        self.assertEqual("skill-better", finding(result, "skill-vs-baseline")["status"])

    def test_tied_or_worse_skill_is_a_regression_finding(self):
        jobs = []
        for offset in range(3):
            jobs.extend(
                [
                    job(20 - offset * 2, "sha", "skill", (True, False)),
                    job(19 - offset * 2, "sha", "baseline", (True, False)),
                ]
            )

        result = regressions.evaluate(snapshot(*jobs))

        self.assertEqual("failed", result["status"])
        comparison = finding(result, "skill-vs-baseline")
        self.assertEqual("skill-not-better", comparison["status"])
        self.assertIn(comparison, result["failures"])

    def test_lower_skill_score_than_previous_revision_is_reported(self):
        jobs = []
        for offset in range(3):
            jobs.append(job(30 - offset, "new", "skill", (True, False)))
            jobs.append(job(20 - offset, "old", "skill", (True, True)))

        result = regressions.evaluate(snapshot(*jobs))

        regression = finding(result, "skill-vs-previous-skill")
        self.assertEqual("skill-regression", regression["status"])
        self.assertEqual("new", regression["revision"])
        self.assertEqual("old", regression["previousRevision"])
        self.assertIn(regression, result["failures"])

    def test_transport_modes_do_not_mix_samples(self):
        jobs = []
        for offset in range(3):
            jobs.extend(
                [
                    job(20 - offset, "sha", "skill", (True, True), "cli-only"),
                    job(10 - offset, "sha", "baseline", (False, False), "mcp-only"),
                ]
            )

        result = regressions.evaluate(snapshot(*jobs))

        self.assertEqual("passed", result["status"])
        self.assertEqual(
            "insufficient-samples",
            finding(result, "skill-vs-baseline", "cli-only")["status"],
        )
        self.assertEqual(
            "insufficient-samples",
            finding(result, "skill-vs-baseline", "mcp-only")["status"],
        )

    def test_runs_without_checks_do_not_count_toward_three_samples(self):
        jobs = [
            job(30, "new", "skill", (True, False)),
            job(29, "new", "skill", (True, False)),
            {
                "id": 28,
                "revision": "new",
                "result": {
                    "caseId": "example",
                    "caseVersion": "a" * 64,
                    "agentConfigId": "claude-default",
                    "agentVersion": "1.0",
                    "toolMode": "cli-only",
                    "arm": "skill",
                    "checks": {},
                },
            },
            job(20, "old", "skill", (True, True)),
            job(19, "old", "skill", (True, True)),
            job(18, "old", "skill", (True, True)),
        ]

        result = regressions.evaluate(snapshot(*jobs))

        self.assertEqual("passed", result["status"])
        self.assertEqual(
            "insufficient-history",
            finding(result, "skill-vs-previous-skill")["status"],
        )


if __name__ == "__main__":
    unittest.main()
