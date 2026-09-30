import ast
import importlib.util
import json
import pathlib
import subprocess
import unittest
from unittest import mock


EVALS = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, EVALS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renderer = load_module("render_eval_report_test", "render_teamcity_eval_report.py")
collector = load_module("collect_eval_runs_test", "collect_teamcity_eval_runs.py")


class EvalReportTest(unittest.TestCase):
    def test_assisted_result_is_visible_but_excluded_from_comparison(self):
        result = {
            "caseId": "tdd-spring-maven", "arm": "skill", "status": "passed",
            "harnessRevision": "eba480c026f5b662f77f30b94c18f480c5534bf0",
            "checks": {"firstBuild": {"passed": True}},
        }
        with mock.patch.object(collector, "cli_json", return_value={
            "id": 9505871, "state": "finished", "status": "SUCCESS",
        }), mock.patch.object(collector, "download_result", return_value=result):
            job = collector.normalize_run("https://teamcity.example", [], {"id": 9505871})
        self.assertTrue(job["assisted"])
        self.assertIn("assisted", job["classificationDetail"])
        observation = collector.latest_arm_observations([job])[("tdd-spring-maven", "cli-only", "skill")]
        self.assertEqual(0, observation["history"]["sampleSize"])
        self.assertEqual("assisted-run-excluded", collector.compare_arms(observation, observation)["status"])
        checker = load_module("check_assisted_test", "check_regressions.py")
        self.assertEqual({}, checker.grouped([job], "tdd-spring-maven", "cli-only", "skill"))

    def test_missing_result_never_reads_logs(self):
        with mock.patch.object(collector, "cli") as cli:
            category, detail = collector.classify(
                "https://teamcity.example",
                {"id": 1, "state": "finished", "status": "FAILURE"}, None,
            )
        cli.assert_not_called()
        self.assertEqual("failed-without-result", category)
        self.assertIn("cause not inspected", detail)

    def test_full_history_recovers_old_case_and_other_pipeline_without_duplicates(self):
        def cli_json(_warnings, _server, *args):
            if args[:2] == ("run", "list"):
                self.assertEqual("0", args[args.index("--limit") + 1])
                return {"build": [{"id": i} for i in range(40, 0, -1)]}
            if args[:2] == ("run", "view"):
                return {"id": int(args[2]), "state": "finished", "status": "SUCCESS"}
            if args[:2] == ("run", "tree"):
                return {"dependencies": [{"id": int(args[2]) + 100, "name": "Run eval case"}]}
            self.fail(f"unexpected CLI call: {args}")

        def result(_warnings, _server, identifier, _known):
            return {
                "caseId": "old-case" if identifier == 101 else "recent-case",
                "arm": "skill", "status": "passed", "harnessRevision": "a" * 40,
                "checks": {"firstBuild": {"passed": True}},
            }

        with mock.patch.object(collector, "cli_json", side_effect=cli_json), \
                mock.patch.object(collector, "download_result", side_effect=result), \
                mock.patch.object(collector, "inventory", return_value=[
                    {"id": "old-case", "executionModel": "paired-arms"},
                    {"id": "recent-case", "executionModel": "paired-arms"},
                ]):
            report = collector.collect("https://teamcity.example", ["config", "green"], 0, [])

        self.assertEqual(40, report["summary"]["jobRunsObserved"])
        self.assertEqual(2, report["collection"]["pipelineCount"])
        self.assertEqual("all-retained-heads", report["collection"]["scope"])
        self.assertEqual(101, report["cases"][0]["toolModes"]["cli-only"]["skill"]["runId"])

    def test_empty_cell_does_not_claim_case_never_ran(self):
        cell = renderer.arm_cell({"executionModel": "paired-arms"}, "cli-only", "skill")
        self.assertIn("no result in collected history", cell)
        self.assertNotIn("not run", cell)
        rendered = renderer.render({"pipelines": [{"runs": []}, {"runs": []}],
                                    "collection": {"scope": "all-retained-heads"},
                                    "warnings": ["safe collection warning"]})
        self.assertIn("All retained heads from 2", rendered)
        self.assertIn("Collection is incomplete", rendered)

    def test_result_revision_scopes_history_when_teamcity_has_no_changes(self):
        revision = "a" * 40
        result = {
            "caseId": "example",
            "arm": "skill",
            "toolMode": "cli-only",
            "status": "passed",
            "harnessRevision": revision,
            "checks": {"firstBuild": {"passed": True}},
        }
        with mock.patch.object(
            collector, "cli_json",
            return_value={"id": 42, "state": "finished", "status": "SUCCESS"},
        ), mock.patch.object(collector, "download_result", return_value=result):
            job = collector.normalize_run("https://teamcity.example", [], {"id": 42})

        self.assertEqual(revision, job["revision"])
        observation = collector.latest_arm_observations([job])[("example", "cli-only", "skill")]
        self.assertEqual(1, observation["history"]["sampleSize"])
        self.assertEqual(1, observation["history"]["passCount"])

    def test_conflicting_revisions_are_not_treated_as_evidence(self):
        warnings = []
        result = {
            "caseId": "example",
            "arm": "skill",
            "toolMode": "cli-only",
            "status": "passed",
            "harnessRevision": "a" * 40,
        }
        detailed = {
            "id": 42,
            "state": "finished",
            "status": "SUCCESS",
            "lastChanges": {"change": [{"version": "b" * 40}]},
        }
        with mock.patch.object(collector, "cli_json", return_value=detailed), \
                mock.patch.object(collector, "download_result", return_value=result):
            job = collector.normalize_run("https://teamcity.example", warnings, {"id": 42})

        self.assertIsNone(job["revision"])
        self.assertEqual(1, len(warnings))

    def test_report_check_allowlist_covers_runner_check_keys(self):
        tree = ast.parse((EVALS / "run_case.py").read_text())
        names = {
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "checks"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        }
        names.update({
            value.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "diagnostic_checks"
                for target in node.targets
            )
            and isinstance(node.value, ast.Dict)
            for value in node.value.values
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        })
        self.assertLessEqual(names, collector.SAFE_CHECK_NAMES)

    def test_legacy_result_strings_do_not_escape_into_shareable_report(self):
        private = "internal-only-canary"
        artifact = {
            "caseId": private,
            "caseStatus": private,
            "harnessRevision": private,
            "status": "failed",
            "gradeStatus": private,
            "arm": "skill",
            "agentConfigId": private,
            "agentVersion": private,
            "agentExitCode": private,
            "checks": {
                private: {"passed": False},
                "firstBuild": {"passed": False},
            },
        }

        def cli(_server, *arguments):
            if arguments[1] == "artifacts":
                return subprocess.CompletedProcess(
                    [], 0, stdout=json.dumps({"file": [{"name": "eval-result.json"}]}), stderr=""
                )
            if arguments[1] == "download":
                destination = pathlib.Path(arguments[arguments.index("--output") + 1])
                (destination / "eval-result.json").write_text(json.dumps(artifact))
                return subprocess.CompletedProcess([], 0, stdout="", stderr="")
            self.fail(f"unexpected CLI call: {arguments}")

        with mock.patch.object(collector, "cli", side_effect=cli):
            result = collector.download_result([], "https://teamcity.example", 42, {"example"})

        category, detail = collector.classify(
            "https://teamcity.example",
            {"id": 42, "state": "finished", "status": "FAILURE"},
            result,
        )
        self.assertEqual("skill-output-failed", category)
        self.assertEqual("failed assertions: firstBuild", detail)
        self.assertIsNone(result["caseId"])
        self.assertIsNone(result["caseStatus"])
        self.assertIsNone(result["harnessRevision"])
        self.assertIsNone(result["gradeStatus"])
        self.assertIsNone(result["agentExitCode"])
        self.assertEqual({"firstBuild": {"passed": False}}, result["checks"])
        self.assertNotIn(private, json.dumps(result))

    def test_shareable_report_excludes_internal_teamcity_details(self):
        private = "internal-only-canary"
        server = f"https://{private}.example"

        def cli_json(_warnings, _server, *args):
            if args[:2] == ("run", "list"):
                return {"build": [{"id": 43, "name": "Pipeline Head"}]}
            if args[:2] == ("run", "tree"):
                return {"dependencies": [{"id": 42, "name": "Run eval case"}]}
            if args[:2] == ("run", "view"):
                return {
                    "id": int(args[2]),
                    "state": "finished",
                    "status": private,
                    "statusText": private,
                    "webUrl": f"{server}/build/{args[2]}",
                    "agent": {"name": private},
                    "buildTypeId": f"{private}-job",
                    "triggered": {"type": private},
                    "queuedDate": private,
                    "lastChanges": {"change": [{"version": private}]},
                }
            self.fail(f"unexpected CLI call: {args}")

        result = {
            "caseId": "example",
            "arm": "skill",
            "toolMode": "cli-only",
            "status": "passed",
            "checks": {"firstBuild": {"passed": True}},
        }
        with mock.patch.object(collector, "cli_json", side_effect=cli_json), \
                mock.patch.object(collector, "download_result", return_value=result), \
                mock.patch.object(collector, "inventory", return_value=[]):
            report = collector.collect(server, [f"{private}-pipeline"], 1, [])

        self.assertNotIn(private, json.dumps(report))
        self.assertEqual(3, report["schemaVersion"])
        self.assertEqual("pipeline-1", report["pipelines"][0]["id"])
        self.assertEqual(42, report["pipelines"][0]["runs"][0]["jobs"][0]["id"])

        # Older snapshots may still carry these fields; the HTML does not show them.
        report["server"] = server
        job = report["pipelines"][0]["runs"][0]["jobs"][0]
        job.update(agent=private, statusText=private, url=f"{server}/build/42")
        html = renderer.render(report)
        self.assertNotIn(private, html)
        self.assertNotIn('<th scope="col">Agent</th>', html)
        self.assertNotIn("<a href=", html)

    def test_inventory_hides_internal_source_mutation_guard(self):
        cases = collector.inventory()

        self.assertTrue(cases)
        self.assertTrue(all("source fidelity" not in case["assertions"] for case in cases))

    def test_inventory_distinguishes_unimplemented_preflight_and_unsupported_fixture_mode(self):
        cases = {case["id"]: case for case in collector.inventory()}
        preflight = cases["teamcity-mcp-access-permissions"]
        self.assertEqual("not-implemented", preflight["runnerSupport"])
        self.assertEqual([], preflight["supportedToolModes"])
        queue = cases["queued-no-compatible-agent"]
        self.assertEqual(["cli-only", "cli+mcp"], queue["supportedToolModes"])
        with mock.patch.object(collector, "cli_json", return_value={}):
            data = collector.collect("https://teamcity.example", ["pipeline"], 0, [])
        by_id = {case["id"]: case for case in data["cases"]}
        self.assertEqual("unsupported-tool-mode", by_id[queue["id"]]["comparisons"]["mcp-only"]["status"])
        self.assertEqual(116, data["summary"]["expectedArmSlots"])
        rendered = renderer.render({"cases": [preflight, queue]})
        self.assertIn('colspan="6"><span class="status">not executable', rendered)
        self.assertIn("preflight runner is not implemented", rendered)
        self.assertIn("unsupported tool mode for this fixture", rendered)
        self.assertNotIn("not arm-based", rendered)

    def test_report_renders_separate_arm_columns_and_unique_jobs(self):
        job = {
            "id": 42,
            "classification": "passed",
            "classificationDetail": "all recorded assertions passed",
            "result": {"caseId": "example", "toolMode": "cli-only", "arm": "skill"},
            "durationSeconds": 10,
        }
        data = {
            "summary": {
                "caseContracts": 2,
                "pairedCaseContracts": 1,
                "expectedArmSlots": 6,
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
                    "assertions": ["pipeline stored/read back"],
                    "targets": [],
                    "toolModes": {
                        "cli-only": {
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
                        "mcp-only": {"skill": None, "baseline": None},
                        "cli+mcp": {"skill": None, "baseline": None},
                    },
                    "comparisons": {
                        "cli-only": {"status": "insufficient-samples"},
                        "mcp-only": {"status": "missing-arm"},
                        "cli+mcp": {"status": "missing-arm"},
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
                    "toolModes": None,
                    "comparisons": None,
                },
            ],
            "pipelines": [
                {"id": "one", "runs": [{"jobs": [job]}]},
                {"id": "two", "runs": [{"jobs": [job]}]},
            ],
        }

        report = renderer.render(data, {"failures": []})

        self.assertIn("Case x tool mode x arm matrix", report)
        self.assertIn('<th scope="colgroup" colspan="2">CLI only</th>', report)
        self.assertIn('<th scope="colgroup" colspan="2">MCP only</th>', report)
        self.assertIn("comparison needs 3 samples per arm", report)
        self.assertIn("No mature skill-comparison regression is recorded.", report)
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

        self.assertIn("100 in / 20 out", report)
        self.assertIn("provider cost not reported", report)
        self.assertIn("provider cost unavailable", report)

    def test_report_shows_agent_and_post_agent_wait_separately(self):
        job = {
            "id": 42,
            "classification": "build-not-queued",
            "classificationDetail": "no build appeared during the post-agent wait",
            "durationSeconds": 6900,
            "result": {
                "caseId": "example",
                "arm": "skill",
                "phaseTimings": {
                    "bootstrapSeconds": 8,
                    "preparationSeconds": 5,
                    "agentSeconds": 3200,
                    "buildWaitSeconds": 3600,
                    "totalSeconds": 6810,
                },
            },
        }
        data = {
            "summary": {
                "jobRunsObserved": 1,
                "classifications": {"build-not-queued": 1},
                "phaseTimings": {
                    "runsMeasured": 1,
                    "bootstrapSeconds": 8,
                    "agentSeconds": 3200,
                    "buildWaitSeconds": 3600,
                    "fieldsMeasured": {
                        "bootstrapSeconds": 1, "agentSeconds": 1, "buildWaitSeconds": 1,
                    },
                },
            },
            "cases": [],
            "pipelines": [{"id": "one", "runs": [{"jobs": [job]}]}],
        }

        report = renderer.render(data)

        self.assertIn("agent process 53m 20s", report)
        self.assertIn("bootstrap 8s", report)
        self.assertIn("build wait 60m 00s", report)
        self.assertIn("runner total 113m 30s", report)
        self.assertIn("cumulative, not wall clock", report)
        self.assertIn("not that Claude is making progress", report)

    def test_report_renders_safe_regression_finding(self):
        report = renderer.render(
            {"summary": {}, "cases": [], "pipelines": []},
            {
                "failures": [
                    {
                        "caseId": "example",
                        "toolMode": "cli-only",
                        "kind": "skill-vs-baseline",
                    }
                ]
            },
        )

        self.assertIn("Mature skill-comparison regression detected.", report)
        self.assertIn("example</code> / CLI only: skill is not better than baseline", report)


if __name__ == "__main__":
    unittest.main()
