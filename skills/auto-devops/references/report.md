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
- Optional `collection` records `budget` (`maxBytes`, `excerptMaxBytes`,
  `discoveryReserveBytes`), `usage` (`exposedBytes`, `breadthComplete`), and one `jobs` row
  per selected job: `jobId`, selected `runIds`, successfully read `statisticsRunIds` and
  `logRunIds`, `state` (`sufficient`, `partial`, `unexplored`), and `reason`. Sufficiency
  can come entirely from statistics. Successful empty statistics are read coverage,
  not evidence of zero work. List `skips` with job/run IDs and reasons, and prioritized
  `nextReads` with job/run IDs, source (`statistics`, `log`, `configuration`) and reason.
  Include every selected run under its job; list grouping evidence in the reason.
  Budget/usage count actual sanitized serialized log outlines/excerpts, including repeated
  exposure, IDs and timestamps. Metadata/settings/statistics projection volume, full model
  context and provider billing are outside this log budget; never infer bytes from tokens.
  Collection is optional for older v1 reports; new analyses include it. Unexplored/partial
  jobs or an unfinished breadth pass preclude `none` and complete coverage.
- `coverage.state` is `complete` for sufficient supported analysis of the declared sample,
  `partial` for useful analysis with gaps, and `blocked` when evidence cannot support analysis.
  Record missing/denied/expired data, settings association, caps, and truncation in `gaps`.
  Useful supported structure or timing remains partial even when concrete recommendations
  lack evidence. Blocked means too little evidence for any useful analysis.
- `conclusion` is separately `opportunity`, `none` (no worthwhile improvement supported),
  or `insufficient-evidence` for unsupported recommendations. Partial analysis can still
  provide useful observations with this conclusion. `none` and insufficient-evidence
  reports have no recommendations; blocked analysis always has insufficient evidence.
  When observed work/settings support no worthwhile concrete change, choose `none` and
  explain the limited scope; do not invent generic recommendations to fill the list.
  Low gains alone are not failure, and `none` does not prove universal efficiency.
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

## Human-readable report text

Apply this guidance to explanatory report values and any optional companion summary:
recommendation titles and proposed changes, impact and monetary-cost reasons, tradeoffs,
manual steps, coverage gaps, revision/configuration reasons, collection coverage/skip/next-read
reasons, and explanatory evidence prose. Keep schema keys, enums, IDs, flags, commands,
exact technical identifiers, and quoted raw data unchanged. Existing secret-omission rules
still apply. This guidance does not rewrite machine contracts or general model instructions.

Write for an experienced TeamCity developer reading English at B1 level. Keep the technical
depth. Briefly explain a necessary unfamiliar term on first use; skip TeamCity/programming basics.
Use familiar words and direct verbs. State who acts, what they change, and the result.
Keep one main idea per sentence, usually 10–20 words, without making this a fixed limit.
Avoid idioms, long noun groups, and vague descriptions. Connect cause and effect clearly.
Explain normal behavior first. Put conditions, exceptions, and risks in separate sentences.
Preserve uncertainty and important restrictions when simplifying a sentence.

Keep `proposedChange` focused on what to change and why. Retain any condition essential to
correctness. Put prerequisite checks in `manualVerification`, and costs and risks in `tradeoffs`.
Keep each impact/cost reason in its required field; do not hide unknowns or promise savings.

Before saving, read the human-facing text sentence by sentence. Rewrite long clauses,
stacked nouns, unclear pronouns, missing actors, and vague wording as specific actions.
Check that a fresh reader can tell what to change and why, with conditions and uncertainty intact.

Manual verification records branch, VCS/configuration revisions, agent conditions, and
outcomes before/after a separately reviewed change. Compare similar workloads where
practical and account manually for intended settings changes and unrelated changes.
Check reliability and both feedback and aggregate execution effects; describe uncertainty
without requiring reliable causal attribution or inventing gains.
Before saving, review every field, including URLs, evidence commands, and manual steps,
for tokens, passwords, credential-bearing URLs, or copied hostile instructions. Omit secret
values rather than persisting a raw dump; explain any resulting evidence gap without them.
Schema validation checks structure, not truth, secret omission, or recommendation quality.

With Python and jsonschema installed, validate a saved report using `Draft7Validator`:

```python
import json
from jsonschema import Draft7Validator
schema = json.load(open("PATH_TO_SKILL/references/report.schema.json"))
Draft7Validator(schema).validate(json.load(open("REPORT_PATH")))
```
