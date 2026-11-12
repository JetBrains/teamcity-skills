"""Exercise the local report contract with synthetic documents."""

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures" / "auto-devops-reports"


class AutoDevopsReportSchemaTest(unittest.TestCase):
    def test_partial_report_is_valid_but_an_unknown_contract_version_is_not(self):
        schema = json.loads((ROOT / "skills/auto-devops/references/report.schema.json").read_text())
        Draft7Validator.check_schema(schema)
        validator = Draft7Validator(schema)
        report = json.loads((FIXTURES / "partial-opportunity.json").read_text())
        validator.validate(report)
        report["schemaVersion"] = 2
        self.assertFalse(validator.is_valid(report))

    def test_coverage_and_conclusion_do_not_confuse_missing_data_with_no_opportunity(self):
        validator = Draft7Validator(json.loads(
            (ROOT / "skills/auto-devops/references/report.schema.json").read_text()))
        report = json.loads((FIXTURES / "partial-opportunity.json").read_text())
        no_opportunity = copy.deepcopy(report)
        no_opportunity.update(conclusion="none", recommendations=[])
        validator.validate(no_opportunity)
        blocked = copy.deepcopy(no_opportunity)
        blocked["coverage"]["state"] = "blocked"
        blocked["conclusion"] = "insufficient-evidence"
        validator.validate(blocked)
        blocked["conclusion"] = "none"
        self.assertFalse(validator.is_valid(blocked), "blocked analysis cannot assert no opportunity")
        report["recommendations"] = []
        self.assertFalse(validator.is_valid(report), "opportunity requires a concrete recommendation")
        no_opportunity["coverage"].update(state="complete", truncated=True)
        self.assertFalse(validator.is_valid(no_opportunity), "truncated analysis cannot be complete")

    def test_requested_expansion_and_partial_insufficient_evidence_are_representable(self):
        validator = Draft7Validator(json.loads(
            (ROOT / "skills/auto-devops/references/report.schema.json").read_text()))
        report = json.loads((FIXTURES / "partial-opportunity.json").read_text())
        expanded = copy.deepcopy(report)
        expanded["sample"]["limits"]["rootRuns"] = 60
        report.update(conclusion="insufficient-evidence", recommendations=[])
        for name, valid in (("requested-expansion", expanded), ("partial-insufficient", report)):
            with self.subTest(name=name):
                validator.validate(valid)
        expanded["sample"]["limits"]["rootRuns"] = 0
        self.assertFalse(validator.is_valid(expanded))

    def test_timing_separates_parallel_execution_feedback_and_unknown_agent_queue(self):
        validator = Draft7Validator(json.loads(
            (ROOT / "skills/auto-devops/references/report.schema.json").read_text()))
        report = json.loads((FIXTURES / "slow-shared.json").read_text())
        validator.validate(report)
        self.assertEqual(1200, report["timing"]["aggregateExecutionSeconds"])
        self.assertEqual(965, report["timing"]["roots"][0]["feedbackElapsedSeconds"])
        self.assertIsNone(report["timing"]["roots"][0]["agentQueueSeconds"])
        report["timing"]["distinctRunIds"].append(100)
        self.assertFalse(validator.is_valid(report), "shared run IDs must be unique")
        report["timing"]["distinctRunIds"].pop()
        report["timing"]["roots"][0]["queuedToStartSeconds"] = -1
        self.assertFalse(validator.is_valid(report))


    def test_missing_data_efficiency_settings_changes_and_requested_caps_are_representable(self):
        validator = Draft7Validator(json.loads(
            (ROOT / "skills/auto-devops/references/report.schema.json").read_text()))
        for name in ("efficient-none", "denied-partial", "changed-settings", "blocked", "capped"):
            with self.subTest(name=name):
                report = json.loads((FIXTURES / (name + ".json")).read_text())
                validator.validate(report)
                self.assertTrue(all(value > 0 for value in report["sample"]["limits"].values()))


    def test_composite_agent_subset_and_unknown_allocation_fit_version_one(self):
        validator=Draft7Validator(json.loads((ROOT/'skills/auto-devops/references/report.schema.json').read_text()))
        report=json.loads((FIXTURES/'composite-generated.json').read_text())
        validator.validate(report)
        self.assertIn(101,report['sample']['runIds'])
        self.assertNotIn(101,report['timing']['distinctRunIds'])
        report['timing']['aggregateExecutionSeconds']=None
        validator.validate(report)


    def test_adaptive_collection_is_optional_and_validates_budget_and_job_coverage(self):
        validator = Draft7Validator(json.loads(
            (ROOT / "skills/auto-devops/references/report.schema.json").read_text()))
        report = json.loads((FIXTURES / "partial-opportunity.json").read_text())
        report["sample"]["limits"]["logRuns"] = 5
        validator.validate(report)  # Existing v1 reports remain valid without collection.
        report["collection"] = {
            "budget": {"maxBytes": 120000, "excerptMaxBytes": 8000, "discoveryReserveBytes": 30000},
            "usage": {"exposedBytes": 456, "breadthComplete": False},
            "jobs": [{"jobId": "Example_Build", "runIds": [100], "statisticsRunIds": [100],
                      "logRunIds": [], "state": "sufficient", "reason": "Statistics cover café timing."}],
            "skips": [{"jobId": "Example_Verify", "runIds": [101], "reason": "Discovery reserve retained."}],
            "nextReads": [{"jobId": "Example_Verify", "runId": 101, "source": "statistics",
                           "reason": "Read the remaining selected run before deeper logs."}]}
        validator.validate(report)
        for path, invalid in ((["budget", "maxBytes"], 0), (["usage", "exposedBytes"], -1),
                              (["jobs", 0, "statisticsRunIds"], [100, 100]),
                              (["jobs", 0, "state"], "complete"), (["nextReads", 0, "reason"], "")):
            broken = copy.deepcopy(report)
            target = broken["collection"]
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = invalid
            with self.subTest(path=path):
                self.assertFalse(validator.is_valid(broken))


    def test_adaptive_unexplored_jobs_require_a_next_read_and_preclude_none(self):
        validator = Draft7Validator(json.loads(
            (ROOT / "skills/auto-devops/references/report.schema.json").read_text()))
        report = json.loads((FIXTURES / "partial-opportunity.json").read_text())
        report["collection"] = {
            "budget": {"maxBytes": 120000, "excerptMaxBytes": 8000, "discoveryReserveBytes": 30000},
            "usage": {"exposedBytes": 0, "breadthComplete": False},
            "jobs": [{"jobId": "Example_Verify", "runIds": [101], "statisticsRunIds": [],
                      "logRunIds": [], "state": "unexplored", "reason": "Budget exhausted."}],
            "skips": [], "nextReads": []}
        self.assertFalse(validator.is_valid(report), "remaining scope needs a concrete next read")
        report["collection"]["nextReads"] = [{"jobId": "Example_Verify", "runId": 101,
            "source": "statistics", "reason": "First selected run without statistics."}]
        validator.validate(report)
        report.update(conclusion="none", recommendations=[])
        self.assertFalse(validator.is_valid(report), "unexplored jobs cannot imply efficiency")
