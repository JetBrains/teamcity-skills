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
