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
unavailable evidence: record a gap, inspect historical logs where available, and do not
invent current source or perform YAML analysis in this slice.

`job tree` may silently omit inaccessible dependencies. Its success alone never proves
coverage complete. Record graph uncertainty when reads cannot independently establish it.
A current job step list does not prove which settings a historical run used. Label the
association `unverified` unless separately established; label an observed difference
`mismatch`. Restrict claims and manual verification accordingly.
Compare current steps with bounded historical logs when historical work suggests a change.
A log proves execution, not that the step still exists today. If work was already removed,
record that difference; do not recommend removing it again or blame current settings for
historical duration. Keep unverified associations explicit when revisions are unavailable.

Denied/expired/unsupported reads are gaps. Continue useful reads within budget and existing
authorization, without repeated retries or permission expansion; other observations remain valid.

Initial limits: 30 completed root runs within 14 days on the selected branch, 100 jobs,
200 distinct runs total, logs from at most five runs and 2,000 lines per run.
Track distinct selected IDs and root/log counts before further targeted reads. Stop at a
cap and report partial coverage, truncation, and the affected scope as a gap. A history
response filling its requested limit leaves additional roots unknown; do not silently expand.
User-requested smaller or larger limits replace the corresponding defaults; record all
actual positive limits and use them in collection commands. Expand only on explicit request.
The tree commands themselves have no job/run-count cap; for a potentially large graph,
inspect a bounded depth (`--depth 1`) and expand only within the remaining budget.
Depth limits and logical counts do not guarantee a hard response-size bound. If a response
is too large to inspect safely, stop that expansion and report incomplete coverage.
Describe depth limits/hidden children as gaps. For phase timing use
`teamcity run log RUN_ID --tail 2000 --json`: `{run_id,messages:[{text,timestamp,...}]}`
preserves timestamps that `--raw` strips; never invent them from text. `--tail` counts
message envelopes, can return an extra envelope, and does not cap multiline text. Parse
locally before passing excerpts to analysis: count multiline text and retain at most the
declared text-line limit; report truncation and retained scope. Consult CLI help for tests.

Follow [timing.md](timing.md) for deterministic timestamp calculations, shared-run handling,
queue attribution, and ranking feedback/execution opportunities.
