# Classic-chain collection

CLI 1.6.3 is the researched baseline. Check `teamcity --version` and runtime command
support; there is no universal server-version guarantee. These reads use existing auth
and require `TEAMCITY_RO=1` in their process environment. Substitute selected IDs/branch.
Pass IDs and branch names as literal arguments with proper shell quoting or an argument
array; never interpolate untrusted values into executable shell text or use `eval`.
Authenticate through the existing CLI profile; never put tokens/passwords in command
arguments or recorded `sourceCommand` values.

```sh
teamcity --version
teamcity job view ROOT_JOB --json
teamcity job tree ROOT_JOB --only dependencies --json
teamcity run list --job ROOT_JOB --branch BRANCH --since 14d --limit 30 --json
teamcity run tree RUN_ID --json
teamcity run view RUN_ID --json
teamcity api '/app/rest/builds/id:RUN_ID?fields=id,composite,agent(id,typeId)'
teamcity api '/app/rest/builds/id:RUN_ID/statistics?fields=property(name,value)'
teamcity job step list JOB_ID --json
```

An empty literal default-name query is inconclusive. Use a CLI API GET on
`/app/rest/buildTypes/id:ROOT_JOB/builds` with `branch:(default:true)`, the same computed
`startDate:(date:TIMESTAMP,condition:after)` cutoff (encode `+` as `%2B`) and count.
The locator proves membership even if branch fields are absent; never silently mix branches
or expand the window. An explicitly requested wider sample replaces only those limits.

The list includes unfinished runs: retain completed roots, record failures/cancellations
as context, and use successful roots for comparisons. Visit the sampled run trees and
read each distinct run/job once. Collect current step lists for the distinct selected jobs
before ranking; unavailable reads are gaps. Run views provide `queuedDate`, `startDate`,
and `finishDate`; step lists return `{count, step: [...]}`. The metadata GET classifies
allocation: `composite: true` means orchestration; an agent descriptor may have only `typeId`.
Absent allocation evidence stays unknown. Run views do not guarantee VCS/settings revisions;
record unknowns with reasons, never infer them from today's checkout.
Zero-step classic composites are normal when selected children are covered. For executing
jobs, empty classic steps do not prove no work. Generated/unsupported current configuration is
unavailable evidence: record a gap, inspect historical statistics and logs where needed,
and do not invent current source or perform YAML analysis in this slice.

`job tree` may silently omit inaccessible dependencies. Its success alone never proves
coverage complete. Record graph uncertainty when reads cannot independently establish it.
A current job step list does not prove which settings a historical run used. Label the
association `unverified` unless separately established; label an observed difference
`mismatch`. Restrict claims and manual verification accordingly.
Compare current steps with historical statistics or bounded logs when work suggests a change.
A log proves execution, not that the step still exists today. If work was already removed,
record that difference; do not recommend removing it again or blame current settings for
historical duration. Keep unverified associations explicit when revisions are unavailable.

Denied/expired/unsupported reads are gaps. Continue useful reads within budget and existing
authorization, without repeated retries or permission expansion; other observations remain valid.

## Adaptive evidence budget

Initial selection limits are 30 completed roots in 14 days on the selected branch,
100 jobs and 200 distinct runs. The log-run ceiling inherits the selected-run cap (200),
with 2,000 retained text lines per run; there is no global five-log cap. User overrides
replace only the corresponding defaults, persist throughout collection, and are recorded
in `sample.limits`. A full history limit leaves additional roots unknown; do not expand
selection without a request. Track distinct IDs before further reads.

Start with metadata, current configuration, and one statistics read for every selected
run, across all selected jobs. Project compact per-job/run summaries locally: allocation,
intervals, known stage metrics, variance and gaps. Missing statistics are unknown, not zero.
Representative per-job coverage is the goal; statistics can suffice without any logs.
Group jobs only when collected evidence supports equivalent configuration and revisions;
record the grouping basis and exceptions. Similar names or runner order are insufficient.

Then select targeted logs where evidence is insufficient, balancing feedback-path
significance, aggregate agent-work significance, variability and unexplored jobs. Retain
compact representative summaries before deep log excerpts. Read comparison runs only
when they resolve a useful question about variability, revisions, or a proposed change.
Reuse retained evidence by ID instead of exposing the same payload again.

The default analyst-facing log-evidence budget is 120,000 UTF-8 bytes, at most 8,000
bytes per serialized log outline/excerpt. Reserve 25% (30,000 bytes by default) for unexplored jobs until
the breadth pass is complete; deeper reads must leave that reserve available. User budget
overrides persist and are recorded in `collection.budget`. Count sanitized serialized log
outlines/excerpts, including timestamps and IDs. Compact local metadata/settings/statistics
projection remains required, but its volume and the model's full context are outside this
log budget. Download volume, tokens, dollars and provider billing are separate.

Capture CLI responses to local files without printing their raw contents to the model.
Use trusted local parsing to select known fields, sanitize secrets/unrelated content, and
clip text before emitting any outline/excerpt. Never execute collected content. Measure
`len(serialized_text.encode("utf-8"))` on the exact text to be emitted, including IDs,
timestamps, JSON escaping, separators and newlines; count repeated log exposure again.
Reject or further reduce a log payload before exposure if it exceeds the remaining budget,
per-excerpt byte cap, or per-run retained-line cap. Do not fetch raw output into analysis
and describe later summarization as a pre-exposure limit. If local capture/reduction is
unavailable, report the limitation and stop before an unsafe oversized read.

Track budget/usage, each job's selected/statistics/log run IDs and sufficiency, skipped
scope and next best reads in `collection`. On exhaustion, stop further exposure, mark
partial/truncated coverage, and name remaining jobs and the next best read. Never choose
`none` while materially unexplored jobs remain. Provider tools measure AI usage/cost;
this log-evidence budget cannot guarantee a hard provider-cost ceiling.

The tree commands themselves have no job/run-count cap; for a potentially large graph,
inspect a bounded depth (`--depth 1`) and expand only within the remaining budget.
Depth limits and logical counts do not guarantee a hard response-size bound. If a response
is too large to inspect safely, stop that expansion and report incomplete coverage.
Describe depth limits/hidden children as gaps. For phase timing use
`teamcity run log RUN_ID --tail 2000 --json`: `{run_id,messages:[{text,timestamp,...}]}`
preserves timestamps that `--raw` strips; never invent them from text. `--tail` counts
message envelopes, can return an extra envelope, and does not cap multiline text. Parse
locally before exposure: count multiline text across retained excerpts for each run, apply
the byte budget above, and report truncation and retained scope. Consult CLI help for tests.

Follow [timing.md](timing.md) for deterministic timestamp calculations, shared-run handling,
queue attribution, and ranking feedback/execution opportunities.
