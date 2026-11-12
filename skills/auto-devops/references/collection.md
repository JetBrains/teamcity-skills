# Classic-chain collection

CLI 1.6.3 is the researched baseline. Check `teamcity --version` and runtime command
support; there is no universal server-version guarantee. These reads use existing auth
and require `TEAMCITY_RO=1` in their process environment. Substitute selected IDs/branch.

```sh
teamcity --version
teamcity job view ROOT_JOB --json
teamcity job tree ROOT_JOB --only dependencies --json
teamcity run list --job ROOT_JOB --branch BRANCH --since 14d --limit 30 --json
teamcity run tree RUN_ID --json
teamcity run view RUN_ID --json
teamcity job step list JOB_ID --json
```

The list includes unfinished runs: retain completed roots, record failures/cancellations
as context, and use successful roots for comparisons. Visit the sampled run trees and
read each distinct run/job once. Collect current step lists for the distinct selected jobs
before ranking opportunities; record unavailable reads as gaps. Run views provide `queuedDate`, `startDate`, and
`finishDate`; job step lists return `{count, step: [...]}` with current runner properties.
Run view does not guarantee VCS/settings revisions. Record unknown revisions and the
reason; do not infer them from today's checkout. Use verified CLI GET reads if available.

`job tree` may silently omit inaccessible dependencies. Its success alone never proves
coverage complete. Record graph uncertainty when reads cannot independently establish it.
A current job step list does not prove which settings a historical run used. Label the
association `unverified` unless separately established; label an observed difference
`mismatch`. Restrict claims and manual verification accordingly.
Compare current steps with bounded historical logs when historical work suggests a change.
A log proves execution, not that the step still exists today. If work was already removed,
record that difference; do not recommend removing it again or blame current settings for
historical duration. Keep unverified associations explicit when revisions are unavailable.

Denied, expired, and unsupported reads are coverage gaps. Preserve existing authorization;
continue useful reads within the remaining budget without repeatedly retrying unavailable
data or seeking broader permissions. A failed read does not invalidate other observations.

Initial limits: 30 completed root runs within 14 days on the selected branch, 100 jobs,
200 distinct runs total, logs from at most five runs and 2,000 lines per run.
Track distinct selected IDs and root/log counts before further targeted reads. Stop at a
cap and report partial coverage, truncation, and the affected scope as a gap. A history
response filling its requested limit leaves additional roots unknown; do not silently expand.
User-requested smaller or larger limits replace the corresponding defaults; record all
actual positive limits and use them in collection commands. Expand only on explicit request.
The tree commands themselves have no job/run-count cap; for a potentially large graph,
inspect a bounded depth (`--depth 1`) and expand only within the remaining budget.
Describe depth limits and hidden children as gaps. For targeted logs use
`teamcity run log RUN_ID --tail 2000 --raw`; consult CLI help for targeted tests.

Follow [timing.md](timing.md) for deterministic timestamp calculations, shared-run handling,
queue attribution, and ranking feedback/execution opportunities.
