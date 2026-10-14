#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Compare skill and baseline runs of the same case.

The baseline arm withholds the skill and changes nothing else, so a check that
the skill arm passes and the baseline arm fails is the skill's contribution,
stated per assertion rather than as one number.

    python3 evals/compare_arms.py results/*.json
    python3 evals/compare_arms.py results/*.json --markdown
"""

import argparse
import collections
import json
import pathlib
import sys

MARK = {True: "pass", False: "FAIL", None: "-"}


def checks_of(*results) -> list:
    """Every check either arm reported, in the order the runner produced them."""
    names = []
    for result in results:
        for name in result.get("checks", {}):
            if name not in names:
                names.append(name)
    return names


def outcome(result: dict, check: str):
    """Did this check pass? None when the run never got far enough to tell."""
    entry = result.get("checks", {}).get(check)
    return entry.get("passed") if entry else None


def load(paths):
    """Results grouped by case, then by arm; later files win a duplicate."""
    cases = collections.defaultdict(dict)
    for path in paths:
        result = json.loads(pathlib.Path(path).read_text())
        cases[result["caseId"]][result.get("arm", "skill")] = result
    return cases


def render(cases, markdown: bool) -> int:
    lifts = 0
    for case_id, arms in sorted(cases.items()):
        skill, baseline = arms.get("skill"), arms.get("baseline")
        if not skill or not baseline:
            print(f"{case_id}: only the {'skill' if skill else 'baseline'} arm ran, nothing to compare\n",
                  file=sys.stderr)
            continue

        rows = []
        for check in checks_of(skill, baseline):
            with_skill, without = outcome(skill, check), outcome(baseline, check)
            verdict = ""
            if with_skill and without is False:
                verdict, lifts = "skill fixes this", lifts + 1
            elif with_skill is False and without:
                verdict = "skill breaks this"
            rows.append((check, MARK[without], MARK[with_skill], verdict))

        header = f"{case_id}  (baseline {baseline['status']} -> skill {skill['status']})"
        if markdown:
            print(f"### {header}\n")
            print("| Check | Without skill | With skill | |")
            print("| --- | --- | --- | --- |")
            for row in rows:
                print(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |")
            print()
        else:
            print(header)
            for name, without, with_skill, verdict in rows:
                print(f"  {name:26} {without:5} -> {with_skill:5}  {verdict}")
            print()

    print(f"{lifts} check(s) pass only with the skill.")
    return 0 if lifts else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", nargs="+", type=pathlib.Path)
    parser.add_argument("--markdown", action="store_true", help="emit a table to paste into a report")
    args = parser.parse_args()
    return render(load(args.results), args.markdown)


if __name__ == "__main__":
    raise SystemExit(main())
