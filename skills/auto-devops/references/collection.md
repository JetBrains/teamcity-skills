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
read each distinct run/job once. Run views provide `queuedDate`, `startDate`, and
`finishDate`; job step lists return `{count, step: [...]}` with current runner properties.
Run view does not guarantee VCS/settings revisions. Record unknown revisions and the
reason; do not infer them from today's checkout. Use verified CLI GET reads if available.

`job tree` may silently omit inaccessible dependencies. Its success alone never proves
coverage complete. Record graph uncertainty when reads cannot independently establish it.
A current job step list does not prove which settings a historical run used. Label the
association `unverified` unless separately established; label an observed difference
`mismatch`. Restrict claims and manual verification accordingly.

Initial limits: 30 completed root runs within 14 days on the selected branch, 100 jobs,
200 distinct runs total, logs from at most five runs and 2,000 lines per run.
Stop collecting at a cap, report truncation as partial, and expand only on user request.
The tree commands themselves have no job/run-count cap; for a potentially large graph,
inspect a bounded depth (`--depth 1`) and expand only within the remaining budget.
Describe depth limits and hidden children as gaps. For targeted logs use
`teamcity run log RUN_ID --tail 2000 --raw`; consult CLI help for targeted tests.

Compute timestamp deltas with a local deterministic calculator, such as timezone-aware
Python datetime subtraction, and report seconds. Check the arithmetic before writing:
09:00:00 to 09:05:05 is 305 seconds. Keep feedback elapsed time, dependency waits,
agent queue delay, and total execution separate. Root queued-to-start time can include dependencies; it is not automatically
agent queue delay. Sum each distinct run only once, and do not equate aggregate execution
with billing. Detailed timing/ranking and broader edge cases require further verification.
