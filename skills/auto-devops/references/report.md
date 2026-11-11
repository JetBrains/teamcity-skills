# Report contract

Use [report.schema.json](report.schema.json), a Draft 7 JSON Schema, as the field contract.
Installation by hand: copy the entire `auto-devops` folder into the agent's skill directory,
keeping `references/`. Invoke it with a root job ID, branch, and local output file, for example:
“Use auto-devops for Example_Verify on main; save the report to /tmp/chain-report.json.”

- `target` identifies the server/job/branch, per-run VCS revisions when known, and the
  configuration source/revision/association. Empty `revisions` requires an honest
  `revisionNote`; a null configuration revision is unknown, with an explanation.
- `sample` records the actual ISO-8601 time window, root IDs, all distinct run IDs,
  successful baseline roots, and the collection limits. No successful baseline is evidence
  of missing comparison data, not evidence that the chain is inefficient.
- Optional `timing` holds derived values and all supporting evidence IDs; follow
  [timing.md](timing.md). Raw command observations must not silently combine other reads.
- `coverage.state` is `complete` for sufficient supported analysis of the declared sample,
  `partial` for useful analysis with gaps, and `blocked` when evidence cannot support analysis.
  Record missing/denied/expired data, settings association, caps, and truncation in `gaps`.
- `conclusion` is separately `opportunity`, `none` (no worthwhile improvement supported),
  or `insufficient-evidence` for unsupported recommendations. Partial analysis can still
  provide useful observations with this conclusion. `none` and insufficient-evidence
  reports have no recommendations; blocked analysis always has insufficient evidence.
- `evidence` contains stable IDs, associated run IDs, and concise observations.
  Each `sourceCommand` is one exact executed CLI invocation. Split observations from
  multiple reads into separate evidence records and cite their IDs from recommendations;
  do not combine commands into a compound string. Keep observed facts separate from
  estimated effects; a configured delay is not proof it ran in a historical build.
- Rank supported recommendations, each with a concrete `proposedChange`, `tradeoffs`,
  `expectedImpact`, and executable human `manualVerification` steps. Time values are seconds;
  use null when unknown and explain the basis. Positive time values mean potential savings;
  negative values mean added time. `monetaryCost.value` is an estimated change in cost per
  comparable successful chain, positive for added cost and negative for savings. It stays
  null, with null currency and a reason, unless prices and a billing model support a number.
  Provider tools report AI usage/cost separately.

Manual verification records branch, VCS/configuration revisions, agent conditions, and
outcomes before/after a separately reviewed change. Compare similar workloads where
practical and account manually for intended settings changes and unrelated changes.
Check reliability and both feedback and aggregate execution effects; describe uncertainty
without requiring reliable causal attribution or inventing gains.
Schema validation checks structure, not truth or recommendation quality.

With Python and jsonschema installed, validate a saved report using `Draft7Validator`:

```python
import json
from jsonschema import Draft7Validator
schema = json.load(open("PATH_TO_SKILL/references/report.schema.json"))
Draft7Validator(schema).validate(json.load(open("REPORT_PATH")))
```
