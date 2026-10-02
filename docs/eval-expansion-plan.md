# Bounded evaluation expansion

## Objective and evidence

Obtain three to five additional fully passing skill cases and measure their
baseline arms under identical conditions. A local grader test is not a Claude
evaluation, a simulated build is not a live first-green build, and a skill pass
is not automatically a skill win. Keep every failed or tied observation.

## Execution order

1. Validate the three stateful queue contracts and positive/negative grader
   tests locally. State lives in the runner, not an agent-editable result file.
2. Run a bounded skill/baseline pilot for each selected case. Start with one
   pair rather than a large batch. Existing configuration pilots may run while
   the new fixture contracts are being verified.
3. Inspect only safe results, targeted build metadata, and published reports.
   Fix demonstrated harness/skill defects; do not change a live evaluated
   agent's target configuration. A changed harness/case starts a new pair.
4. Qualify promising cases with at least three scored samples per arm on the
   same harness, contract, tool mode and agent profile. Report ties as ties.
5. Keep new contracts draft until evidence has been reviewed; publish the
   result/check/time/cost comparison without traces or private target IDs.

## Selected cases

| Case | Environment | Required outcome |
| --- | --- | --- |
| `queued-missing-os-family-recovery` | Stateful CLI simulation | Discover the absent OS-family key, replace only the selector using an observed relevant capability, validate/read back, confirm compatibility and finish one verification. |
| `queued-unresolved-script-parameter-recovery` | Stateful CLI simulation | Repair unresolved shell-variable substitution without weakening Maven verification or artifact publication. |
| `queued-busy-compatible-agent` | Stateful CLI simulation | Establish compatibility and wait for the original run, without changing configuration, canceling or queueing a duplicate. |
| `spring-boot-demo-gradle-testcontainers-pipeline` | Live configuration only | Preserve build/test separation, generation tasks, runtime/Docker requirements and per-job outputs. |
| `spring-boot-kotlin-gradle-java25-pipeline` | Live configuration only | Configure the declared JDK 25 container and Gradle verification without requiring a preinstalled host JDK 25. |

The existing `queued-no-compatible-agent` remains a separate diagnosis-only
contract; it does not prove repair. The three new cases deliberately share a
neutral task request: the cause and correct action must come from observation.

## Boundaries

- CLI-only, same model/configuration and per-case timeout for both arms.
- Initial budgets: 300 seconds per simulated case, 900 seconds per live
  configuration case. Record the budget in the comparison profile.
- The fixture advances virtual queue state through bounded observations; no
  target cloud agent or real two-minute sleep is needed.
- New fixture results explicitly carry `evaluationEnvironment: simulated`.
- No source changes, removal of tests/artifacts, speculative retries or manual
  intervention can turn a failing evaluated run into a pass.
- Preserve unrelated local work. Use approved delivery (a scoped personal
  patch or an explicitly authorized commit/push), and label patch profiles so
  different harness contents are not combined under the same base Git SHA.
- Do not run full KMP/Testcontainers first-green builds as part of this batch.

## Fixture acceptance tests

Exercise successful repair and unchanged busy-agent completion, missing-key
case changes, requirements removal, source changes, build weakening, missing
validation/read-back/compatibility, duplicate starts, unbounded watches and
late diagnosis. A failed or timed-out agent exit must never become a pass,
even if intermediate checks were green.

## Pilot audit

The first OS-recovery pairs at `b902002` and `c7ef78e` failed the evaluation,
with 11/13 checks passing in both arms. Both arms diagnosed and repaired the
missing key; baseline did not wait forever. Baseline omitted stored-configuration read-back before its
verification. Fixed-category diagnostics on `c7ef78e` proved that the skill
arm's rejected push changed only a step display name. This was a fixture
false negative, not a change to Maven, runtime or outputs. The correction
ignores step display names for both arms, while retaining strict executable
properties, job/step topology and publications. Re-run both arms on the new
revision; do not relabel the historical failures as passing observations.

Before the first unresolved-parameter pilot, unit tests also cover both
equivalent bounded repairs: implicit `exit /b` and TeamCity percent escaping.
Neither arm is required to emit one exact spelling; Maven verification and
publication behavior remain mandatory.

## Final batch results — 2026-09-30

Four of the five selected cases produced at least one fully passing skill
evaluation. This is **not** four established, stable skill wins. The three
new queue contracts remain draft. No evaluated skill instructions were
changed and no agent-created target configuration was manually repaired.

All 21 pipeline heads and their children are terminal. They represent 18
unique evaluated agent invocations, not 21 samples. All 18 report jobs
published `publish/index.html` and `publish/runs.json`. Every evaluated agent
exited with code 0 without timeout; failed rows below are grader failures.

| Case | Environment | Skill | Baseline | Evidence scope |
| --- | --- | --- | --- | --- |
| OS-family recovery | Simulated CLI | 2/3 full passes; checks 13/13, 10/13, 13/13 | 0/3; checks 11/13, 11/13, 12/13 | Three distinct samples per arm on `01acda4`; skill is not yet reliable. |
| Busy compatible agent | Simulated CLI | [13/13](https://teamcity-nightly.labs.intellij.net/build/9518074) | [12/13](https://teamcity-nightly.labs.intellij.net/build/9518076) | One pair on `01acda4`; pilot only. |
| Unresolved script parameter | Simulated CLI | [11/13, failed](https://teamcity-nightly.labs.intellij.net/build/9518080) | [11/13, failed](https://teamcity-nightly.labs.intellij.net/build/9518083) | One pair on `01acda4`; no full pass or demonstrated advantage. |
| Testcontainers pipeline | Live configuration only | [9/9](https://teamcity-nightly.labs.intellij.net/build/9518061) | [6/9](https://teamcity-nightly.labs.intellij.net/build/9518060) | One pair on `c7ef78e`; pilot only. |
| Java 25 pipeline | Live configuration only | [8/8](https://teamcity-nightly.labs.intellij.net/build/9518088) | [5/8](https://teamcity-nightly.labs.intellij.net/build/9518086) | One pair on `01acda4`; pilot only. |

OS skill evals are [9518070](https://teamcity-nightly.labs.intellij.net/build/9518070),
[9518095](https://teamcity-nightly.labs.intellij.net/build/9518095), and
[9518113](https://teamcity-nightly.labs.intellij.net/build/9518113); baseline evals
are [9518069](https://teamcity-nightly.labs.intellij.net/build/9518069),
[9518093](https://teamcity-nightly.labs.intellij.net/build/9518093), and
[9518108](https://teamcity-nightly.labs.intellij.net/build/9518108).
The published three-sample average check score is 0.923 versus 0.872. This
small descriptive comparison is not evidence of universal superiority.
Baseline did not wait forever: it diagnosed and recovered the simulated
build, but failed process checks. The second skill sample failed compatibility
confirmation and simulated verification success.

### Remaining failures and interpretation

- Busy baseline failed `noBlindRetry`, despite zero pushes, cancellations,
  and starts. The safe artifact does not identify that composite check's
  exact subreason; do not invent one or claim indefinite waiting.
- Unresolved-parameter skill failed `configurationPreserved` and
  `boundedRecovery`. Safe counters show one rejected attempt changing step
  behavior, followed by an accepted repair. Baseline failed `noBlindRetry`
  and saved-configuration read-back. Neither result was relabeled as passed.
- Testcontainers baseline failed job count, artifact rules, and per-job
  contracts. Java 25 baseline failed required step types/properties and
  per-job contracts. These are the specified configuration checks, not
  proof that either generated pipeline would fail at runtime.
- Queue fixtures do not run Maven or a cloud target build. Configuration
  cases do not execute the target repository. No live first-green or
  Testcontainers-runtime success is claimed.
- Case fingerprints, harness revision, CLI-only mode, and configured agent
  profile match within each comparison. The safe artifacts do not record
  an exact agent/model runtime version; matching profile labels are not
  proof of identical runtime binaries.

### Measured time and cost

Times below are agent-process wall seconds, including tool activity and
waiting inside that process, not model thinking time. OS values sum three
distinct samples per arm; the other rows each contain one sample per arm.
TeamCity queue duration, bootstrap, preparation, observation, grading,
cleanup, runner total, and token counters are recorded separately in the
[machine-readable audit](eval-expansion-results.json).

| Case | Skill agent seconds | Baseline agent seconds | Skill USD | Baseline USD |
| --- | ---: | ---: | ---: | ---: |
| OS-family recovery, three samples | 335.430 | 226.981 | 2.8946760 | 1.8104275 |
| Busy compatible agent | 66.958 | 89.931 | 0.6272560 | 0.6962700 |
| Unresolved script parameter | 169.611 | 55.760 | 1.2298580 | 0.4397595 |
| Testcontainers pipeline | 474.539 | 784.060 | 3.4432680 | 6.1995905 |
| Java 25 pipeline | 594.680 | 490.035 | 4.1266135 | 2.5116860 |

The 14 evaluations in the final case cohorts cost **$23.979405**. Four earlier
OS fixture-calibration evaluations cost **$3.608090**, for **$27.587495**
measured across the 18 post-commit evaluations. Do not discard calibration
costs or treat the reused heads as extra paid invocations. The earlier
old-revision Testcontainers pair cost another $10.3684855 and is outside this
batch total; startup/personal-delivery attempts without usage evidence have
unknown cost, not assumed zero. These are reported agent costs, not an
infrastructure bill or estimated token pricing.

### Reuse, validation, and publication audit

Heads `9518096` and `9518103` reused eval `9518095`; head `9518097` reused
eval `9518093`. They are excluded as independent samples. `--rebuild-deps`
alone did not reliably prevent reuse. The final skill sample used the
non-environment parameter `eval.sample.id=os-recovery-qualification-3`, and
its distinct child `9518113` was verified. The parameter does not enter the
agent task or alter the evaluation profile.

Local validation: **153 unit tests passed; 22 cases, zero schema errors**.
The [final TeamCity report](https://teamcity-nightly.labs.intellij.net/build/9518089)
was generated at 2026-09-30 19:34:29 UTC and finished publishing at 19:35:48
UTC. Both its HTML and JSON were downloaded and checked against the safe
individual results. The JSON correctly reports three samples per OS arm and
`insufficient-samples` for the other four case comparisons. No draft case
was promoted, and no further unchanged evaluations were queued after
completion of this batch.

## Historical dashboard recovery — 2026-09-30

The later dashboard's empty cells were not evidence that cases had never run.
The configuration evaluator's pipeline-local `env.EVAL_PIPELINES` named only
itself, overriding the parent project's two-pipeline list. The collector also
limited each source to the latest 32 heads. TeamCity retained 155 configuration
heads and 49 first-green heads at the start of this investigation.

Report build `9020058` preserved the three KMP configuration results; report
`9505870` preserved five of the six first-green rows requested by the user.
These are historical verdicts at their original revisions, not new passes or
regrades against today's contracts.

| Requested case | Historical skill evidence | Historical baseline evidence |
| --- | --- | --- |
| `jetcaster-kmp-multi-targets` | `9004209`, passed | `9006940`, failed assertions |
| `kmm-basic-sample-mobile-targets` | `8994259`, passed | `8994766`, failed assertions |
| `kotlinconf-app-multi-targets` | `9008326`, passed | `9009420`, failed assertions |
| `clean-spring-boot-maven` | `9391726`, passed | `9393068`, passed |
| `kotlinconf-app-compose-multiplatform` | `9009549`, agent timeout | `9011778`, agent timeout |
| `spring-boot-kotlin-gradle-java25` | `9435245`, runner error | `9435268`, failed assertions |
| `spring-petclinic-maven-yaml` | `9497653`, build wait timeout | `9470110`, failed assertions |
| `tdd-spring-maven` | `9505871`, queue stalled, **assisted** | No safe result identified |
| `spring-boot-demo-gradle-testcontainers` | No historical first-green result identified | No historical first-green result identified |

The TDD result was independently downloaded: agent exit 0, no agent timeout,
`build-queue-stalled`, no completed grade. Agent-process wall time was
2750.874 seconds (45:51), including tool activity and waits; it is not measured
model-thinking time. The harness subsequently waited another 612.875 seconds
for a build. Measured agent cost was $9.490015. Raw logs and trajectories were
not inspected, so no finer attribution is asserted. Four manual selector-only
repairs were previously recorded (main, diagnostic probe, main reversion,
probe reversion); successful Maven children did not make their failing heads
green. The report now explicitly labels this run assisted and excludes it from
skill comparisons.

Fix `9086dcd25f504435cd4cc08d5cab5a26651a583c` restores all retained heads by
default, prioritizes a canonical parent-scoped `env.EVAL_REPORT_PIPELINES`,
removes all log/trace fallback inspection, and changes empty cells to
"no result in collected history". It retains revision/profile separation and
actual-child-ID deduplication. All **157 unit tests** pass and all **22 cases**
validate. A new report-only pipeline, `TeamCity_Sandbox_TCEvals_EvaluationHistoryReport`,
is attached to the existing repository root and has no Claude feature or
evaluation dependency. Its YAML was server-validated and read back. Report-only
head/job `9518779`/`9518780` completed successfully at 20:19:39/20:19:37 UTC.
The report job ran for 562 seconds; collection began at 20:10:37 UTC. Its
`publish/index.html`, `publish/runs.json` and `publish/regressions.json` were
downloaded and verified. All ten historical rows (including the two queue
cases below) are restored, with their original revisions and the TDD assisted
annotation. The snapshot contains 155 configuration heads and 51 first-green
heads, including the two newly running evals, and 202 unique eval jobs. There
are no collection warnings. A final report-only refresh after the new pair
finishes must use `2d668a4` or a later descendant preserving both the clearer
preflight/unsupported-mode labels and the expanded 50-row execution ledger.

Only the genuine first-green Testcontainers gap was queued again: one CLI-only
pair on the same `9086dcd` revision, with profile
`claude-default-first-green-1800s`, agent/build-wait budgets of 1800 seconds,
queue compatibility check at 120 seconds and stall budget of 600 seconds.
Skill head/eval/report: `9519017`/`9519019`/`9519018`.
Baseline head/eval/report: `9519020`/`9519022`/`9519021`.
Both distinct eval children started; at dispatch these were **pending**, not successes.
Do not repair their generated targets manually, rerun merely to seek green,
or confuse their results with the existing configuration-only Testcontainers
case. Preserve all outcomes and measured costs when the safe artifacts arrive.

At the 20:36 UTC heartbeat, original baseline eval `9519022` was terminal:
`Canceled (Exit code 143)`, finished at 20:32:32 UTC after starting at
20:12:51 UTC. Its artifact listing was empty; no safe result, phase breakdown,
or measured cost was available. The cancellation's cause/actor is not exposed
in the inspected metadata and is not inferred. The live dependency tree for
baseline head `9519020` and report `9519021` now points to eval `9518861`,
queued at 20:32:32 and started at 20:32:34 UTC with trigger type
`reAddedOnStop`. No replacement or retry was requested by this monitor.
Keep the canceled attempt in the audit; do not silently merge it with the
replacement or count it as a scored baseline sample. Verify the replacement's
case, arm, revision, and profile from its safe result before comparison.
At that check, both evals were running and both report jobs were queued with
"Build dependencies have not been built yet".

At 20:43:21 UTC, skill eval `9519019` finished **FAILURE**. Its downloaded
safe result identifies `spring-boot-demo-gradle-testcontainers`, arm `skill`,
`cli-only`, harness `9086dcd25f504435cd4cc08d5cab5a26651a583c`, profile
`claude-default-first-green-1800s`, case version
`5ff75acc6baffac4a0b99862745ea9a14272bf6af6825eb260b3e6eb766d4e84`.
The result is `errored` / `agent-timeout`: agent exit **124**, timeout **true**,
1800-second budget. The failed grade has **4/6** checks passed:
`configurationValidated`, `firstBuild`, `artifactsPublished`, and
`sourceMutations`; `testsExecutedAndReported` and `toolchain` failed.
This is not a first-green evaluation pass, despite the recorded build and
artifact checks. No measured usage or cost was published; absence is not zero.
Phase timings (seconds): bootstrap 9, preparation 3.223, agent 1800.002,
observation 0.368, build wait 1.053, grading 4.049, cleanup 0.005, runner total
1808.699. The evaluator job ran 1831 seconds overall. Cleanup is deferred and
temporary objects remain, as required by the no-deletion boundary.
Report `9519018` ran from 20:43:26 to 20:53:18 UTC (592 seconds), finishing
**SUCCESS**; head `9519017` finished **FAILURE** at 20:53:23 UTC. Its three
published artifacts (`index.html`, `runs.json`, `regressions.json`) were
downloaded and checked. The snapshot generated at 20:43:30 UTC correctly
records skill `9519019` as an agent timeout with the two failed checks, keeps
all ten recovered historical rows and their provenance unchanged, and retains
the TDD assisted annotation. It has no collection warnings: 206 head/job
references deduplicate to 202 eval IDs with the same three reused-ID groups.
The regression check has zero mature failures; this is not an eval pass.

The current-dependency snapshot includes replacement `9518861` but omits
the canceled original `9519022`, which is no longer referenced by its head.
That attempt remains explicit evidence in this audit, not a scored sample;
the report's totals do not represent every interrupted invocation or its
unknown usage. Do not conceal this limitation in the final handoff.
This report is on the original evaluator revision, so the final report-only
refresh must still include the later preflight labels and 50-row ledger.
At the 20:56 UTC check, replacement eval `9518861` remains running and report
`9519021` still waits for its dependency. The single final refresh remains
deferred until the remaining dependencies finish.

At 21:02:55 UTC, replacement baseline eval `9518861` finished **FAILURE**
(1821 seconds of evaluator wall time). Its independently downloaded safe
result confirms arm `baseline`, `cli-only`, the same case ID, case version,
harness `9086dcd25f504435cd4cc08d5cab5a26651a583c`, and profile
`claude-default-first-green-1800s` as skill `9519019`. The agent exited **0**
without timeout under the 1800-second budget; result and grade are **failed**,
with no fixed error category. Four of six checks passed:
`configurationValidated`, `firstBuild`, `testsExecutedAndReported`, and
`sourceMutations`; `artifactsPublished` and `toolchain` failed. Preserve this
original grade, not a corrected or successful result.

Measured baseline agent usage: 248 input tokens, 74973 output tokens,
14305724 cache-read tokens, 170221 cache-write tokens, **$10.738732**.
Phase timings (seconds): bootstrap 5, preparation 3.088, agent 1793.642,
observation 0.197, build wait 1.150, grading 5.689, cleanup 0.005, runner total
1803.771. Cleanup remains deferred. This cost covers replacement `9518861`
only; skill usage and canceled original `9519022` usage remain unknown.
The safe result is retained at
`/tmp/tc-eval-history.SbTScX/new-first-green-baseline/publish/eval-result.json`.
At the 21:04 UTC check, report `9519021` is running (started 21:02:55 UTC) and
head `9519020` is nonterminal with a failed dependency. No further evaluation
or final report-only refresh has been queued; await report publication first.

At 21:12:17 UTC, baseline report `9519021` finished **SUCCESS** after 562
seconds, and baseline head `9519020` finished **FAILURE**. Both evaluator
chains are now terminal; the original canceled baseline attempt remains
separate. All three safe report artifacts were downloaded to
`/tmp/tc-eval-history.SbTScX/new-first-green-baseline-report/publish/`.
The snapshot generated at 21:03:01 UTC contains both terminal eval outcomes,
their matching original revision/case/profile, the measured baseline cost,
and absent skill usage. All 19 historical eval records underlying the ten
restored rows match the earlier verified restoration snapshot exactly,
including grades, revisions, result metadata, and assisted TDD evidence.
All ten rows and both new outcomes are present in HTML. There are no warnings;
206 head/job references still deduplicate to 202 eval IDs, with duplicates
`8798307` (2), `9518093` (2), and `9518095` (3). The canceled `9519022` is
still absent from this current-dependency report, not from the audit. The
regression checker reports no mature failures at minimum 3 samples, while
the new pair comparison remains `insufficient-samples`.

The **single authorized final report-only refresh** was dispatched at
21:15:38 UTC on `5664fc5e0578dd080863fc1655ff30336e99f639` (a descendant
preserving the 50-row ledger and preflight/unsupported-mode labels).
At dispatch, head `9520474` and report child `9520475` were running; their
read-back tree contains only the report job, no evaluator dependency. The report-only YAML
was revalidated against the server and its stored topology and existing VCS
root attachment were checked before dispatch. No new Claude evaluation was
started. This uses the one refresh allowance: do not queue another refresh.
Wait for these exact jobs, then verify the final safe publication and close
the monitor only after the final evidence has been assessed and reported.

### Completed restoration and final publication

Final report head `9520474` finished **SUCCESS** at 21:24:30 UTC, and child
`9520475` finished **SUCCESS** at 21:24:31 UTC; the report job ran for 532
seconds. The three safe artifacts were downloaded to
`/tmp/tc-eval-history.SbTScX/final-restoration/publish/` and verified. Snapshot
time is 21:15:45.928583 UTC; report source is pinned to `5664fc5`, while each
evaluation retains its own original source revision and case/profile identity.

- All 202 unique evaluator job records equal the preceding verified snapshot.
  The 19 historical records supporting all ten restored rows preserve their
  verdicts, revisions, metadata, and assisted labels. Both new terminal results
  match the independently downloaded safe artifacts, including checks, exit/
  timeout flags, phase timings, and measured/absent usage.
- The HTML ledger contains exactly the latest 50 unique evaluator IDs in the
  existing order and visibly says **Showing 50 of 202 unique evaluator jobs**.
- Preflight is explicitly **not executable**, with its runner unimplemented;
  MCP-only queue-fixture cells are explicitly unsupported. Unsupported modes
  are excluded from the denominator: **116** supported arm slots, not 126.
- Assisted TDD remains excluded from comparison (`sampleSize: 0`). Both new
  first-green results remain unsuccessful, with `insufficient-samples` for
  comparison. The separate regression gate has no mature failures at minimum
  3 samples, not a claim that the evaluated tasks succeeded.
- Collection has zero warnings. The 206 head/job references still deduplicate
  to 202 evaluator IDs with the same three reused-ID groups. Both evaluator
  chains, both reports, and the final report-only chain are terminal.
- Report cost is **$257.949359 measured across 82 of 202 evaluator jobs**,
  not a complete total. Replacement baseline `9518861` contributes $10.738732;
  skill `9519019` and canceled original `9519022` have unknown usage. The
  canceled original remains in this audit and is absent from current-head
  collection; it is neither silently merged nor counted as a scored sample.

Restoration and the authorized first-green pair assessment are complete. No
further eval or report refresh is authorized; this restoration monitor can be
closed. No evaluated target or unrelated cleanup file was changed, no project
was deleted, and the user's earlier PDF was not overwritten. The grading
improvements described below are separate proposed work awaiting approval.

### First-green grading caveats discovered during read-only diagnosis

The user's improvement question prompted inspection of the completed skill
target, without mutations or reruns. `wait_for_build()` selects the greatest
build ID in the target project, not a verification pipeline and its complete
dependency chain. Here that selects packaging child `9519271`, successful at
20:41:49 UTC. The sibling test job `9519270` finished **FAILURE** at 20:44:33,
and head `9518864` finished **FAILURE** at 20:44:37, both after the evaluator
finished grading. A subsequent name/status/duration-only test query showed
one successful `SpringBootDemoApplicationTests.contextLoads` occurrence in
the failed test job, versus zero in packaging. It does not establish what was
already reported at the earlier grading instant or a successful test job.
The failure cause is not exposed by the inspected first-class CLI metadata;
the custom "tests passed" status text is not evidence overriding FAILURE.

Both stored skill jobs select `env.JAVA_HOME` through `%env.JDK_21_0%`, but
the adapter discards job environment and parameter declarations while the JDK
checker reads only environment/image evidence. Two local, non-mutating
reproductions confirmed lost environment evidence and ignored JDK parameters.
This establishes a declaration-evidence gap, not independent runtime JDK proof.
Proposed chain-aware observation and allowlisted JDK parsing fixes await user
approval. No implementation or historical regrade has been made; the skill
timeout and both failed original grades remain unchanged. Comparisons of
individual checks must disclose these harness limitations.

### Additional queue and preflight rows

The user's additional two queue rows also had historical safe results, now
downloaded independently from their evaluator jobs. No paid reruns are needed:

| Case | Skill | Baseline | Original revision |
| --- | --- | --- | --- |
| `java25-agent-requirement-blocks-provisioning` | `9399715`: failed, 7/11; $0.7823825 | `9400206`: failed, 4/11; $0.4012035 | `7fdd55bfbe4811ac4661031262b4b254534ffaf1` |
| `queued-no-compatible-agent` | `9018952`: passed, 10/10; $0.7721540 | `9020059`: failed, 8/10; $0.5244435 | `ec026f507d831b70cf08c285d909c25ef116531f` |

All four agents exited 0 without timeout. These older artifacts have no phase
timings or embedded harness SHA; revisions above come from the historical
normalized TeamCity reports (`9505870` and `9020058`), not invented artifact
fields. The generic queue pair predates the explicit tool-mode result field.
One pair per case does not establish a stable skill advantage.

`teamcity-mcp-access-permissions` is a catalog contract only: `run_case.py`
rejects `teamcity-access-preflight` as not executable. Do not dispatch it to
Claude or count it as a pass. The report now shows **not executable — preflight
runner not implemented**, separately from missing history and paired-arm
results. MCP-only is explicitly unsupported by the CLI queue fixture; these
cells are marked unsupported and excluded from expected runnable arm slots.
No contract is promoted and no new preflight runner is claimed.

## Authorized chain/JDK repair and bounded repeat — 2026-10-01

The user subsequently approved the proposed harness repair and necessary
reruns ("ок, настрой, перезапусти что надо" / "исправь и продолжи"). This is
new authorization after the completed restoration above, not a revival of
its deleted monitor or an amendment of historical grades. Scope is one fresh
comparable first-green Testcontainers skill/baseline pair; no other cases,
manual target repairs, project deletion, or unbounded retries.

The previous $10.738732 measurement covers replacement baseline `9518861`
only: 1793.642 agent seconds, 74973 output tokens, 14305724 cache-read tokens,
and 134 reported tool calls. Skill `9519019` and canceled `9519022` costs are
unknown. These aggregate counters establish usage, not which individual
activity caused it. No logs, prompts, or real trajectories were inspected.

Implemented changes:

- Bind verification to the generated source YAML's stored job topology and
  settings; allow a unique pipeline when no source file exists. Multiple or
  mismatching candidates fail closed. Do not choose by probe name or highest
  arbitrary project build ID. Pin the latest head of that selected pipeline.
- Wait for its full dependency DAG, including queued/running siblings; any
  non-successful member prevents a green chain. Deduplicate actual build IDs
  and aggregate tests/artifacts only from that chain. Bind declarations via
  unique CLI job names, rejecting missing/foreign/ambiguous jobs. Do not parse
  undocumented virtual-ID suffixes or mix retries/pipelines.
- Preserve only allowlisted JAVA_HOME/JDK_HOME selectors (including inherited
  `env.JAVA_HOME` parameters). Require evidence for every evaluated job and
  distinguish a declaration from a measured runtime version. Merely available
  JDK parameters do not establish selection. Publish safe IDs/counts/statuses
  and fixed JDK booleans, never parameter values, scripts, or free-form details.
- Add validated `EVAL_AGENT_MAX_BUDGET_USD` forwarding to Claude's spending
  limit and classify structured budget/error completions even with exit 0.
  Stop the process group on timeout, not just its shell. This closes a possible
  orphan-process risk; it is **not** attribution for the old unknown charges.
  After abnormal agent exit, bound discovery of a missing head separately from
  the full wait for a chain already queued (no additional Claude invocation).

Validation: **176 unit tests passed**, including process-group termination,
budget exhaustion, delayed failed siblings, reused dependencies, ambiguous
selection, JDK inheritance, unavailable runtime proof, and sanitization.
All **22 cases** validate. Existing `.teamcity/eval-runner.yml` was validated
by the nightly server and its stored jobs/report dependency read back.

A read-only adapter check of old chain `9518864` now sees packaging `9519271`
SUCCESS (0 tests, 3 artifacts) and test job `9519270` FAILURE (1 imported test,
1 artifact). Both declare Java 21; runtime verification remains false. This
tests observation on terminal evidence only: no historical grade was rewritten
and no assertion is made about when the old test result first appeared.

The authorized repeat profile is `claude-default-chain-v2-1200s-usd3`, CLI-only,
with the same pinned case/source for both arms. Set a **$3 provider API limit
per arm**, 1200 seconds for the agent, 1800 seconds for already-queued builds,
and queue checkpoint/stall budgets of 120/600 seconds. The provider limit is
not a TeamCity-infrastructure cost cap; report actual measured spend, including
any final-call overshoot, rather than claiming a prepaid $6 total. No automatic
repeat is authorized. Dispatch IDs/revision and terminal evidence follow below.

Fix **`8543bc8923fb3ad08329ef2d3e3e26e2e05ee49b`** was committed and pushed,
then exactly one fresh pair was dispatched with dependency rebuilding to avoid
reusing old eval jobs. On 2026-09-30 at 23:50:51 UTC, skill head `9523474`
queued; eval `9523476` started at 23:50:52, report `9523475` waits for it.
Baseline head `9523477` has distinct eval `9523479` and report `9523478`.
Both evals appear in the exact full-revision-filtered CLI listing for `8543bc8`;
their heads are running and reports wait on their own evals. Running status is
not proof of Claude progress or a successful result. Verify safe terminal
artifacts before any outcome/cost claim. The previous restoration monitor
remains deleted; the unrelated CLI-eval monitor is untouched.

At the 2026-10-01 00:04 UTC check, **both original eval children had been
canceled externally**: baseline `9523479` finished at 00:03:32 UTC after
750 seconds, and skill `9523476` finished at 00:03:43 UTC after 771 seconds.
Both expose `UNKNOWN` / `Canceled (Exit code 143)` and **zero artifacts**.
No safe result, measured usage, completed grade, or cancellation actor/cause
is available from the inspected metadata. The trigger user associated with
snapshot/re-add metadata is not evidence of who canceled a job.

The original heads/reports now reference replacements: baseline eval
`9523528` (queued 00:03:32, started 00:03:37 UTC) and skill eval `9523530`
(queued 00:03:43, started 00:03:47 UTC). Both have trigger type
`reAddedOnStop`, are running, and appear in the exact full-revision-filtered
CLI listing for `8543bc8`. This monitor did not request either replacement.
The report jobs still await those dependencies. Confirm each replacement's
case/arm/profile/budget from its safe terminal artifact before comparison.

Keep originals `9523476` and `9523479` as separate interrupted invocations,
not scored samples or duplicates to discard. Their spend is unknown; the
per-process $3 cap is **not a cumulative cap across canceled/re-added
invocations**. Do not claim this pair's total is bounded by $6. Current-head
report collection may omit those now-unreferenced originals, so retain this
explicit audit even if the final dashboard does not include them. No further
evaluation, retry, or target mutation was performed.

Replacement skill eval **`9523530` finished FAILURE at 00:18:58 UTC**
(911 seconds of evaluator wall time). Its safe result was downloaded to
`/tmp/tc-eval-chain.bAnthA/skill/publish/eval-result.json`. Identity matches the
authorized case/version, skill arm, CLI-only mode, harness `8543bc8`, and
profile `claude-default-chain-v2-1200s-usd3`. It records a $3 API limit,
exit **1**, no timeout, and **`errored` / `agent-budget-exhausted`**. Actual
measured cost is **$3.0112465**, an observed $0.0112465 overshoot, not exactly
$3 and not the total cost of canceled plus replacement invocations.

The grade failed **3/6** checks: configuration validation, toolchain, and
unchanged sources passed; first green build, imported tests, and artifacts
failed. Chain `9523534` was selected via `unique-pipeline` (two observed heads).
Both members `9523604` and `9523605` finished FAILURE, with zero tests and zero
artifacts. Read-only CLI metadata places both failures in **Generate JOOQ and
OpenAPI sources (Gradle)**, exit 1 / Gradle exception; they finished at 00:12:08
UTC and the head at 00:12:12. The underlying exception cause is not exposed in
the inspected metadata; no raw logs or trajectories were read. This is not a
green build or a successful skill evaluation. Both jobs declare JDK 21, now
recognized by the adapter; `runtimeVerified` remains false.

Measured usage for this replacement only: 82 input tokens, 26304 output,
2834222 cache-read, 86963 cache-write. Phase seconds: bootstrap 4, preparation
3.031, agent 888.231, observation 0.266, build wait 1.864, grading 3.627,
cleanup 0.005, runner total 897.024. Cleanup is deferred; nothing was deleted.
At the 00:19 UTC check, skill report `9523475` is running (started 00:18:58)
and baseline replacement `9523528` remains running. No further eval or report
refresh was dispatched. Await the baseline and both publications before
closing the monitor; retain both canceled originals and their unknown costs.

Replacement baseline **`9523528` finished FAILURE at 00:25:39 UTC**
(1322 seconds of evaluator wall time). Its safe result was downloaded to
`/tmp/tc-eval-chain.bAnthA/baseline/publish/eval-result.json`; case, case
version, baseline arm, CLI-only mode, harness `8543bc8`, profile, and $3 limit
match the skill counterpart. It is **`errored` / `agent-budget-exhausted`**,
exit **1**, no timeout. There is **no completed grade**: `checks` is empty,
and gradeStatus / verificationDiagnostics are absent. Do not represent this
as a scored 0/6 or as a successful evaluation.

Measured replacement cost is **$3.032801** (observed overshoot $0.032801).
Usage: 100 input tokens, 26208 output, 2927857 cache-read, 84417 cache-write.
Phase seconds: bootstrap 6, preparation 2.698, agent 695.414, observation
0.223, build wait 609.460, cleanup 0.004, runner total 1307.800. Thus the
post-agent wait is separate from paid-agent wall time; the longer evaluator
duration is not another 22 minutes of measured model work. Cleanup is deferred.

The safe result's queue reason is `other`. A subsequent, narrowly scoped CLI
check found baseline target chain `9523533` still queued with jobs `9523602`
and `9523603` (queued 00:11:26 UTC). Both child queue reasons report **no idle
compatible agents**, while the head waits for its first child to start. This
is a capacity/provisioning observation, not proof of zero compatible agents
or a JDK mismatch. Compatible-agent counts are not exposed in the inspected
first-class view. It is also a later observation, not a reconstruction of the
exact grading instant. No evaluated target was changed or canceled.

The two completed replacement invocations measured **$6.0440475** in total.
This excludes both canceled originals `9523476`/`9523479` and is **not** a
complete experiment cost or proof of savings versus the earlier pair. Skill
report `9523475` remains running; baseline report `9523478` started at
00:25:39 UTC and is running. Both eval outcomes are now terminal and
unsuccessful. Await their safe report publications; no report-only refresh or
additional evaluation has been dispatched.

Skill report **`9523475` finished SUCCESS at 00:26:59 UTC** (481 seconds),
and evaluator head `9523474` finished FAILURE. Report SUCCESS means that
publication completed, **not** that the evaluation passed. Its safe snapshot
was collected at 00:19:04 UTC, before the baseline finished: it includes
skill `9523530` as `agent-budget-exhausted` and baseline `9523528` as running.
The matrix therefore still shows old baseline `9518861` and explicitly marks
the arms as different harness revisions. Do not compare that stale matrix
pair. Safe report artifacts are in
`/tmp/tc-eval-chain.bAnthA/skill-report/publish/`.

This snapshot contains 208 dependency references / **204 unique evaluator
IDs**, with only the previously documented reused dependencies duplicated.
All 202 earlier evaluator records retain their identities, revisions,
classifications, checks, usage, and timings; all ten restored historical
matrix rows are unchanged. Skill identity, checks, chain/JDK diagnostics,
budget, usage, and timings match its safe result. The two canceled originals
`9523476`/`9523479` are absent, so their unknown costs remain covered by the
explicit interruption audit above, not by this report's totals.

The rendered ledger is **50 of 204** unique jobs. Assisted TDD `9505871`
remains labeled and excluded (zero comparison samples); access preflight is
explicitly not implemented and claims no execution; five unsupported MCP-only
queue modes remain excluded. Measured cost is $260.960606 across 83 of 204
jobs, an incomplete historical total including the skill replacement only.
The regression check says `passed` with no mature failures, but all 66
findings are insufficient samples/history; it is not an eval pass or evidence
of skill lift. Await the baseline report; no refresh was requested.

Baseline report **`9523478` finished SUCCESS at 00:34:00 UTC** (501 seconds),
and evaluator head `9523477` finished FAILURE at the same time. Skill head
`9523474` had finished FAILURE at 00:27:00. Thus both evaluator chains and
their reports are terminal. The baseline report's snapshot, collected at
00:25:44 UTC, contains **both completed replacements**. Its canonical safe
artifacts are in `/tmp/tc-eval-chain.bAnthA/baseline-report/publish/`; no
report-only refresh or further Claude invocation was necessary or requested.

Both published result identities, statuses, exit/timeout, checks, budget,
usage, and phase timings match their safe evaluator artifacts. The opaque
profile fingerprint matches `claude-default-chain-v2-1200s-usd3` in both arms.
Skill retains failed 3/6 checks and the full chain/JDK diagnostics. Baseline
retains empty checks, null gradeStatus, and empty sanitized diagnostics, not
a fabricated 0/6 grade. The matrix selects `9523530` and `9523528` on the same
case version, harness revision, and profile; both are budget-exhausted, with
one unsuccessful sample per arm and `insufficient-samples`, not proven lift.

Final publication independently preserves all **202 historical evaluator
records and ten restored matrix rows**, including their original grades and
revisions. It has 208 dependency references / 204 unique evaluator IDs;
duplicate references are only `8798307` x2, `9518093` x2, and `9518095` x3.
The 50-row ledger, assisted TDD exclusion, non-executable preflight, five
unsupported MCP-only queue modes, and 116 supported-arm-slot denominator
remain intact. All 66 regression findings remain insufficient samples/history.
The report's rounded measured total is $263.993406 across 84 of 204 jobs
(summing the published individual measurements gives $263.9934065). This is
incomplete historical coverage, not the experiment bill. The completed new
replacements contribute exactly the measured **$6.0440475** stated above;
the absent canceled originals still have **unknown cost**.

At the final observation, baseline target head `9523533` and children
`9523602`/`9523603` remain queued. They were not canceled or altered; a later
execution must not retroactively regrade this failed evaluation. No model
process is being continued by this monitor. Green was not obtained within
the authorized pair: skill hit a Gradle code-generation failure and the API
budget, while baseline hit the API budget and its post-agent queue-stall
window without a completed grade. The narrower underlying Gradle cause and
queue capacity require separate evidence/authorization, not another paid
retry merely to obtain green. Close only this bounded-pair monitor after
pushing this audit and reporting the result.

Final evidence links:

- [Skill evaluator chain 9523474](https://teamcity-nightly.labs.intellij.net/buildConfiguration/TeamCity_Sandbox_TCEvals_RunEvalCase/9523474)
- [Baseline evaluator chain 9523477](https://teamcity-nightly.labs.intellij.net/buildConfiguration/TeamCity_Sandbox_TCEvals_RunEvalCase/9523477)
- [Final report 9523478](https://teamcity-nightly.labs.intellij.net/buildConfiguration/TeamCity_Sandbox_TCEvals_RunEvalCase_virtual_publish_eval_report_V__1/9523478)

## Two-project coverage correction — 2026-10-01

The user clarified that "почем так дорого?" was a question about expense,
**not an instruction to impose a $3 limit**. That limit was our interpretation,
not a user requirement; the previous section records what actually ran, not
continuing authorization for that cap. Keep those historical results unchanged.
The bounded-pair monitor has been deleted. The unrelated CLI-eval monitor is
untouched.

The user approved ("ок") completing coverage for
`kawser2133/clean-spring-boot-project` and
`usmanzaheer1995/spring-boot-demo`: refine the existing configuration and
first-green contracts, independently check pinned-source executability without
an LLM, add negative grader tests, then obtain comparable skill/baseline results
on the changed contracts **without the unsolicited USD cap**. This is not an
open-ended green-at-any-cost loop or permission for automatic statistical
repeats. At this checkpoint, **no new Claude evaluations have been launched**.
The evaluator's persistent `env.EVAL_AGENT_MAX_BUDGET_USD` parameter was checked
through its exact first-class CLI lookup and is absent; the previous $3 value
was supplied per run. The optional explicit-budget feature remains available.

### Independent source checks (not eval samples)

Fresh detached clones under `/tmp/tc-two-project-coverage.jHLkSk` retain the
case source revisions: Maven `315ca51dcb0ec25f2cce8f99fa239ec23717f3f6`,
Gradle `940cdb0b4d15c178ca1624095e24b69914b2c9cd`. No repository source code
was manually repaired. Neither controls nor synthetic unit tests count as
agent evaluation passes.

Maven was verified locally with Java **21.0.10**, Maven **3.9.12**, and
`mvn -B -ntp clean verify`: exit 0, **39 tests in six suites**, zero failures,
errors, or skips, and `target/clean-spring-boot-project-0.0.1-SNAPSHOT.jar`.
Suite counts: UserRepositoryTest 8, AuthenticationServiceTest 8,
AuthenticationControllerTest 4, ProductControllerTest 12,
CleanSpringBootProjectApplicationTests 1, ProductServiceTest 6. Docker was not
running; these tests use H2 and do not require it. The pinned repository has
wrapper launchers but no tracked `.mvn/wrapper` files, so the case's reference
command now uses installed Maven. The build itself changed tracked
`logs/application.log` in the disposable control clone, not evaluated sources.

Gradle source inspection establishes an important distinction: requesting
`generateJooq` starts a PostgreSQL Testcontainer during build configuration.
Consequently **packaging also needs Docker for code generation**, although
the packaging job must not execute integration tests. `openApiGenerate`
provides additional required sources; the separate test job must actually
run `SpringBootDemoApplicationTests.contextLoads`. Java 21, Gradle 8.5, and
Kotlin 1.9.21 remain pinned by the case/repository.

A separate control project was created only after checking for an existing
one: `TeamCity_Sandbox_TCEvals_CoverageControls20261001`, under sandbox
`TeamCity_Sandbox_TCEvals` on `https://teamcity-nightly.labs.intellij.net`.
Its public anonymous VCS root
`TeamCity_Sandbox_TCEvals_CoverageControls20261001_SpringBootDemoPinnedControl`
was connection-tested and attached to control pipeline
`TeamCity_Sandbox_TCEvals_CoverageControls20261001_SpringDemoReferenceNotEval`.
The checked-in reference YAML is
`.teamcity/diagnostics/spring-demo-control.yml`: two isolated native-JDK21,
Docker-capable jobs, dedicated Gradle runners, Docker preflight, separate JAR
and JUnit XML publication, no LLM. Nightly server validation and exact stored
jobs/parameters readback passed; head VCS attachment was verified.

Controls `9531386` (personal; children `9531387`/`9531388`) and `9531399`
(ordinary; children `9531501`/`9531400`) both failed before commands with
`Error while applying patch`. Personal mode was initially suspected but the
ordinary repeat disproved that attribution. The user specifically authorized
only filtered checkout errors for `9531387` and `9531501`. The CLI failure
summary exposed `UPDATE_SOURCES` / `Missing VCS reference`: checkout tried to
fetch literal `<unspecified>` (exit 128). The control dispatch had supplied
`--revision` without `--branch`. No eval logs, prompts, or trajectories were
read, and no evaluated target was altered.

After the concrete dispatch fix (`--branch main` plus the exact pinned SHA,
with rebuilt dependencies), control head **`9531520`** reached the Gradle
steps. Both children started at **10:39:20 UTC**. Package **`9531521`** failed
at **10:41:21 UTC** and test **`9531522`** at **10:41:11 UTC**: Gradle exception
/ exit 1, zero imported tests, zero artifacts. All three IDs are present in
the CLI listing filtered by the exact source revision; the branch is `main`.
This establishes that the checkout problem was fixed, **not that Gradle is
executable yet**. Available metadata does not identify the Gradle exception.
Permission for a narrow error view of these two new control builds has been
requested separately; permission for the old checkout errors is not extended
to them. Paid eval dispatch is held pending this diagnostic.

### Contract and observation changes

- Reuse all four existing cases; no duplicate inventory rows. Configuration
  and runtime cases share the same structural contract per repository.
- Accept explicit native or container Java 21 selection. Declaration remains
  distinct from measured runtime proof; contradictory runtime evidence wins.
- Maven requires verification without test skipping, XML/JAR publication, and
  runtime evidence of at least 39 successful tests across all six known suites.
- Gradle requires separate package/test jobs, generated-source prerequisites
  and Docker preflight in both, and no implicit test-running lifecycle task in
  packaging. A declared `test` task with `-x test` is rejected.
- Observe tests/artifacts on each uniquely bound member of the frozen chain.
  Packaging must succeed with zero tests and its own JAR; the test job must
  succeed with the named integration test and its own XML. Another job's
  output, ignored/failed tests, ambiguous jobs, or partial CLI test results
  cannot satisfy those assertions.
- Keep test names/job definitions private to grading. Published diagnostics
  add only successful-test counts; the collector explicitly retains the new
  safe `requiredTests` and `jobResults` booleans. Historical grades/revisions,
  restored rows, assisted exclusions, ledger size, and unsupported modes are
  unchanged. Case-version changes must prevent comparisons with old contracts.

These are structural declarations plus observed outputs, not a general shell
semantics checker or proof of arbitrary command ordering. A green control and
fresh paired evaluations are still required before claiming completed live
coverage of the changed Gradle runtime case.

Validation at this checkpoint: **194 unit tests passed**, including 17 new
two-project contract/negative tests and the collector privacy regression;
**22 cases / zero validation errors**; `git diff --check` passed. These counts
include the existing workspace test suite; unrelated cleanup/proposal changes
and the user's output/PDF are not part of this commit.

Control evidence:

- [Gradle control head 9531520](https://teamcity-nightly.labs.intellij.net/buildConfiguration/TeamCity_Sandbox_TCEvals_CoverageControls20261001_SpringDemoReferenceNotEval/9531520)
- [Package control 9531521](https://teamcity-nightly.labs.intellij.net/buildConfiguration/TeamCity_Sandbox_TCEvals_CoverageControls20261001_SpringDemoReferenceNotEval_virtual_package_V__1/9531521)
- [Test control 9531522](https://teamcity-nightly.labs.intellij.net/buildConfiguration/TeamCity_Sandbox_TCEvals_CoverageControls20261001_SpringDemoReferenceNotEval_virtual_test_V__1/9531522)

### Control Gradle diagnosis and source-preserving repair

The user then requested "найди проблему исправь и продолжи", authorizing the
focused control-error diagnosis previously requested. The first-class CLI's
failure summaries for `9531521` and `9531522` both expose the same
`WorkValidationException`: `compileKotlin` consumes `generateJooq` and
`openApiGenerate` outputs without declared task dependencies. This is a
Gradle task-graph error, not evidence of a missing JDK or unavailable Docker.
No eval logs/prompts/trajectories were inspected.

The isolated reference YAML now runs `generateJooq openApiGenerate` and then
`bootJar` or `test` in **separate Gradle runner steps**. This avoids the invalid
same-invocation task graph while keeping the pinned repository unchanged.
The case's reference verification command was corrected accordingly; the
case prompt does not give away this diagnosis or workaround. Structural
configuration grading still does not claim to execute Gradle: the runtime
checks must reject failed compilation even if the required tasks are declared.
An additional regression test makes that distinction explicit.

Validation: **195 unit tests passed**, all **22 cases valid**, whitespace check
clean. The changed control YAML passed nightly server validation and its exact
stored jobs/parameters were read back. Control **`9564788`** queued at
**15:34:20 UTC**, on branch `main`, pinned revision
`940cdb0b4d15c178ca1624095e24b69914b2c9cd`, with clean checkout and dependency
rebuilding. Exact children are package **`9564790`** and test **`9564789`**.
Initially the queue reported no idle compatible agents / waiting for a starting
agent. Those are capacity/provisioning observations, not zero-compatible
proof. The workaround is not confirmed until both jobs complete successfully
with their own outputs. No paid eval was launched at this checkpoint.

Read-only evaluator preflight found the USD-limit parameter absent. Stored
`RunEvalCase` jobs match the checked-in runner except for the server-local
Claude connection reference, which is preserved; parameters match. The
checked-in runner was server-validated. Do not overwrite its connection or
copy connection credentials into this audit.

Both repaired control jobs then finished **SUCCESS**: package `9564790`
15:42:34–15:45:37 UTC (183 s), test `9564789` 15:42:38–15:46:09 UTC (211 s).
Packaging imported zero tests and published `spring-boot-demo-local.jar`
(39,403,230 bytes). The test job imported the expected
`org.usmanzaheer1995.springbootdemo.SpringBootDemoApplicationTests.contextLoads`
as SUCCESS (741 ms), and published its JUnit XML (7,720 bytes). Both exact
source revisions were confirmed by full-SHA-filtered CLI listing. This proves
the source-preserving Gradle workaround; no runtime JDK version was inferred
from its declaration alone.

Head `9564788` nevertheless finished **FAILURE** at 15:46:14 UTC. Its focused
control failure summary reports `invalid_branch_name`: logical branch `main`
is not monitored by this default-only VCS root, so default revisions were
selected. The attached root itself correctly declares `refs/heads/main` and
has no branch specification. Do not promote the composite failure to green
because its children succeeded.

The first-class CLI has no VCS-root update command. The source-preserving
dispatch correction is to select the root's configured default branch, after
verifying public `refs/heads/main` still equals the pinned SHA, and then verify
the actual run revision via the exact full-SHA-filtered CLI listing. Control
**`9566498`** was dispatched this way with a request to reuse successful
children `9564790`/`9564789`; however the YAML's `allow-reuse: false` prevented
reuse. Actual new children are test **`9566500`** and package **`9566499`**.
They must be monitored normally, not represented as reused or already green.
No additional control was queued to bypass that accepted queue.

Control **`9566498` finished SUCCESS at 15:57:52 UTC**. Package `9566499`
ran 15:54:39–15:57:11 (152 s); test `9566500` ran 15:54:39–15:57:51
(192 s). Both succeeded on the exact pinned source revision, confirmed through
the full-SHA-filtered CLI listing. A read-only check through the actual harness
adapter and grader passes all **14** first-green assertions: package has zero
tests / one artifact, test has one successful required test / one artifact.
The two jobs declare JDK21; runtimeVerified remains false. This is reference
executability/adapter evidence only, **not an LLM eval sample**. Default-branch
dispatch resolved the composite's invalid-branch problem without VCS-root or
repository-source edits.

### Fresh four-case cohort (one pair per changed case)

After both independent source controls were successful, exactly **eight fresh
Claude invocations** were requested at approximately **15:59:57 UTC**: one
skill/baseline pair for each of the four existing changed cases. There is no
provider USD cap, no automatic retry, and no requirement to keep spending
until all arms are green. All use `RunEvalCase`, `cli-only`, `claude -p`,
profile **`claude-default-two-project-3600s-v1`**, agent/build waits of
3600/3600 seconds, queue checkpoint/stall of 120/600 seconds, and sandbox
`TeamCity_Sandbox_TCEvals`. The optional USD-limit parameter was verified absent
immediately before dispatch; terminal artifacts must confirm its absence too.

The evaluator's attached VCS root also monitors only its configured default
branch, `refs/heads/korotkova/evals`. To avoid the diagnosed dispatch issue,
the cohort used default-branch selection after checking local and remote HEAD
both equal **`e93b46cd89c752e9d8a1c18ff818db457013133a`**. Every one of the 24
head/eval/report IDs below then appeared in the CLI listing filtered by that
exact full revision. Dependencies were explicitly rebuilt: all eight eval
children are distinct. No simultaneous dirty workspace changes were included.

| Case | Arm | Head | Eval | Report |
| --- | --- | --- | --- | --- |
| clean-spring-boot-maven-pipeline | skill | 9567195 | 9567214 | 9567213 |
| clean-spring-boot-maven-pipeline | baseline | 9567197 | 9567202 | 9567201 |
| spring-boot-demo-gradle-testcontainers-pipeline | skill | 9567196 | 9567203 | 9567204 |
| spring-boot-demo-gradle-testcontainers-pipeline | baseline | 9567199 | 9567207 | 9567208 |
| clean-spring-boot-maven | skill | 9567200 | 9567212 | 9567211 |
| clean-spring-boot-maven | baseline | 9567194 | 9567210 | 9567209 |
| spring-boot-demo-gradle-testcontainers | skill | 9567193 | 9567206 | 9567205 |
| spring-boot-demo-gradle-testcontainers | baseline | 9567198 | 9567215 | 9567216 |

Expected case hashes (same for both arms):

- Maven configuration: `4010fdb37216e71fd87d1bee13b1864494f2d1e1951168490298e27d28ee8083`
- Gradle configuration: `cddaf659fc193df77f889c22e47f537f4c4f613f955c4648617fa0ac8701126f`
- Maven first-green: `c8ea3ee033a54c0ee5680ea887110be767763144f44ab1ad9aee3927dcdb5f10`
- Gradle first-green: `39558c88c58c18a15088f53b90680e3aafcc2ce964b329bffac533dd0946c885`

At 16:00 UTC all eight eval children are RUNNING, which is not proof of model
progress or success. Monitor these exact chains, download only the safe result
JSON and report publications at terminal, and retain actual cost coverage,
errors, every check, per-job diagnostics, and historical revision separation.
Any external cancellation/re-add must be audited separately, including unknown
cost when no safe result is available. No further paid eval is authorized by
this cohort.

The revision-filtered list also exposed a separate validation-pipeline
selfcheck `9566936` FAILURE (`Grade a pipeline of known shape`, exit 1), with
zero imported tests; case validation `9566935` succeeded. This selfcheck is
not one of the eight evaluations. Its underlying cause is not established by
the inspected metadata, and its raw logs were not read. Replaying its static
known shape through the local adapter/grader gives all eight expected checks;
that synthetic check does not explain or erase the server failure. Do not
attribute it to the two-project cases without evidence.

#### First terminal configuration results — 16:10 UTC

Three exact eval children have completed. Only their safe
`publish/eval-result.json` artifacts were downloaded, under
`/tmp/tc-two-project-results.55tDhX/<eval-id>/publish/`. All three match the
case hashes above, expected arm, `cli-only`, full harness revision
`e93b46cd89c752e9d8a1c18ff818db457013133a`, and profile
`claude-default-two-project-3600s-v1`. Each artifact confirms that
`agentMaxBudgetUsd` is **absent**, agent timeout is 3600 seconds, agent exit is
0, `agentTimedOut` is false, and `errorCategory` is null. These are completed
configuration grades, not runtime first-green results.

| Case / arm | Eval | UTC start–finish | TeamCity wall | Grade | Measured USD |
| --- | --- | --- | --- | --- | --- |
| Maven configuration / skill | [9567214](https://teamcity-nightly.labs.intellij.net/build/9567214) | 15:59:58–16:09:39 | 581 s | passed, 8/8 | 3.636170 |
| Maven configuration / baseline | [9567202](https://teamcity-nightly.labs.intellij.net/build/9567202) | 15:59:57–16:09:58 | 601 s | passed, 8/8 | 5.080621 |
| Gradle configuration / skill | [9567203](https://teamcity-nightly.labs.intellij.net/build/9567203) | 15:59:57–16:09:18 | 561 s | failed, 7/10 | 4.001578 |

Both Maven arms pass every check: `configurationValidated`, `minimumJobs`,
`toolchain`, `requiredStepTypes`, `requiredStepProperties`,
`forbiddenStepProperties`, `requiredArtifactRules`, and `sourceMutations`.
Their `caseStatus: draft` is inventory metadata, not a preflight-only or
unexecuted result. This fresh pair is a configuration-quality tie; its measured
time/cost difference is one observation, not evidence of statistical lift.

Gradle skill passes `configurationValidated`, `minimumJobs`, `toolchain`,
`jobCount`, `requiredStepTypes`, `requiredArtifactRules`, and `sourceMutations`.
It fails `requiredStepProperties`, `requiredAgentRequirements`, and
`requiredJobs`. The agent exited normally but the configuration grade failed;
do not turn this into an agent execution error, a runtime build diagnosis, or
a pass. The safe booleans do not identify which individual property or
requirement was wrong. Baseline is still pending, so there is no completed
Gradle comparison yet.

| Eval | Input / output tokens | Cache-read / cache-write tokens | Tool calls / recognized TeamCity CLI calls |
| --- | --- | --- | --- |
| 9567214 | 92 / 39,119 | 3,377,630 / 96,116 | 61 / 0 |
| 9567202 | 168 / 35,912 | 6,166,442 / 109,101 | 100 / 38 |
| 9567203 | 90 / 41,750 | 3,560,026 / 116,920 | 59 / 0 |

These are the published numeric tool-summary counters; zero recognized CLI
calls alone does not establish an alternative transport or explain a grade.
No raw eval logs, prompts, or trajectories were read.

| Eval | Bootstrap | Preparation | Agent | Observation | Grading | Cleanup | Harness total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 9567214 | 10 | 2.913 | 550.227 | 0.396 | 1.479 | 0.005 | 555.021 |
| 9567202 | 7 | 3.444 | 578.501 | 0.380 | 1.119 | 0.005 | 583.449 |
| 9567203 | 7 | 3.411 | 543.131 | 0.170 | 1.031 | 0.004 | 547.748 |

Timings are published seconds, with TeamCity wall time reported separately.
All three omit `verificationDiagnostics`: configuration-only results provide
no frozen runtime chain, per-job test/artifact counts, or runtime JDK proof.
The toolchain checks pass, but that must not be promoted to runtime-verified
Java 21. Cleanup is deferred and `temporaryObjectsRemoved` is false; this
monitor deleted nothing.

Measured coverage so far is **3/8 evals, $12.718369**. This is neither the final
cohort cost nor a spending cap; costs for the five running evals remain unknown.
At this checkpoint all eight heads are nonterminal; reports `9567213`,
`9567201`, and `9567204` are running. The other five reports are queued with
the exact reason `Build dependencies have not been built yet`, not evidence
of zero-compatible agents. No report artifacts are assessed as final yet.
No new eval, retry, report refresh, control, or evaluated-target mutation was
requested. Historical grades, controls, ledger, and the unrelated selfcheck
remain separate and unchanged.

#### Completed configuration pairs — 16:17 UTC

Gradle configuration baseline
[9567207](https://teamcity-nightly.labs.intellij.net/build/9567207) is now
terminal FAILURE: **15:59:58–16:15:09 UTC, 911 seconds**. Its sole downloaded
artifact is `/tmp/tc-two-project-results.55tDhX/9567207/publish/eval-result.json`.
Identity matches the expected Gradle configuration case/hash, baseline arm,
`cli-only`, full harness revision `e93b46cd89c752e9d8a1c18ff818db457013133a`,
and profile `claude-default-two-project-3600s-v1`. The USD-cap field is absent;
agent timeout is 3600 seconds, exit 0, no timeout, no error category. Overall
and grade status are **failed, 4/10**, not an execution-error result.

Passed: `configurationValidated`, `minimumJobs`, `requiredArtifactRules`, and
`sourceMutations`. Failed: `toolchain`, `jobCount`, `requiredStepTypes`,
`requiredStepProperties`, `requiredAgentRequirements`, and `requiredJobs`.
Thus the fresh Gradle pair is **skill 7/10 versus baseline 4/10**, with the
skill additionally passing the toolchain, job-count, and runner-type checks.
Both still fail the step-property, agent-requirement, and per-job checks;
neither is a successful configuration sample. These safe booleans do not
identify the precise baseline JDK, actual job count, or alternative runner.
The completed Maven configuration pair remains a tie at 8/8. These are single
pairs on the changed contracts, not statistical lift or runtime success.

Baseline measured usage: **$7.360833**, 192 input / 64,665 output tokens,
8,490,016 cache-read / 149,012 cache-write tokens. Published tool counters:
110 total, 40 recognized TeamCity CLI, zero MCP/TeamCity or MCP-probe calls,
70 other calls; no trajectory-based attribution is made. Phase seconds:
bootstrap 7, preparation 3.082, agent 886.904, observation 0.503, grading 1.513,
cleanup 0.004, harness total 892.007. `verificationDiagnostics` is absent,
so no runtime chain, per-job counts, or JDK runtime proof is available from
this configuration result. Cleanup remains deferred, with no object deletion.

Measured coverage is now **4/8 evals, $20.079202**; the four runtime eval costs
remain unknown, not zero. At this check runtime evals `9567212`, `9567210`,
`9567206`, and `9567215` are still RUNNING. All eight heads remain nonterminal.
All four configuration reports are running; the four first-green reports
wait for their unfinished eval dependencies, not a proven compatibility
blocker. No terminal report publication is available to assess yet. No new
eval, retry, report refresh, control, or evaluated-target repair was requested.

#### First three terminal reports assessed — 16:20 UTC

The following heads and reports are now terminal. Report SUCCESS describes
publication, not a successful evaluation; the failed Gradle grade is retained.

| Case / arm | Head / terminal UTC / status | Report / UTC start–finish / wall |
| --- | --- | --- |
| Maven configuration / skill | [9567195](https://teamcity-nightly.labs.intellij.net/build/9567195), 16:18:20, SUCCESS | [9567213](https://teamcity-nightly.labs.intellij.net/build/9567213), 16:09:43–16:18:15, 512 s, SUCCESS |
| Maven configuration / baseline | [9567197](https://teamcity-nightly.labs.intellij.net/build/9567197), 16:19:10, SUCCESS | [9567201](https://teamcity-nightly.labs.intellij.net/build/9567201), 16:10:03–16:19:05, 542 s, SUCCESS |
| Gradle configuration / skill | [9567196](https://teamcity-nightly.labs.intellij.net/build/9567196), 16:17:54, FAILURE | [9567204](https://teamcity-nightly.labs.intellij.net/build/9567204), 16:09:19–16:17:51, 512 s, SUCCESS |

Only `publish/index.html`, `publish/runs.json`, and
`publish/regressions.json` were downloaded, under
`/tmp/tc-two-project-results.55tDhX/report-<report-id>/publish/`.
Their `generatedAt` markers are respectively 16:09:49.344119,
16:10:07.263310, and 16:09:25.890355 UTC. Collection is not an atomic snapshot:
all three nevertheless contain all four completed configuration results,
including baseline `9567207` finished at 16:15:09. The four first-green eval
records remain RUNNING without results in these publications; older completed
matrix cells are not evidence about the new runtime cohort.

Every fresh configuration result's identity, status/grade, checks, exit/timeout,
error category, usage, numeric tool summary, and phase timings match its
independently downloaded safe artifact. The report hashes the profile label;
`e0be5a54c29b9f056e75e0abf6ab76be6bbda272af5282398ca1c35d85d638ec`
is the verified SHA-256 of `claude-default-two-project-3600s-v1`. Report
`agentMaxBudgetUsd: null` corresponds to the absent raw-artifact cap, not $0.
All eight cohort eval IDs occur once in each report, with their own revisions.

Each report contains 216 dependency references / **212 unique evaluator IDs**,
two source pipelines, all retained heads, and zero collection warnings. The
202 historical evaluator records from the final restoration preserve their
classification, revision, assisted label, identity, grade/checks, usage, and
timings. The ten restored historical matrix rows remain intact; only the two
configuration-case matrix rows differ from the later bounded-pair snapshot.
Assisted TDD is still excluded (`sampleSize: 0`), preflight is not executable,
the five unsupported MCP-only queue modes remain excluded, and the supported
denominator is 116 arm slots. Every HTML ledger has exactly 50 rows and says
`Showing 50 of 212 unique evaluator jobs`.

Both new configuration comparisons are `insufficient-samples` (one sample per
arm). The regression gate reports SUCCESS/passed with no failures at minimum
three samples; that is no mature regression finding, **not an eval pass**.
Historical report-wide measured cost is **$284.072609 across 88/212 jobs**,
not the total bill or the fresh cohort cost. Fresh measured coverage remains
4/8 and $20.079202; interrupted attempts with absent usage remain explicitly
unknown in earlier audit sections and are not recovered by these reports.
Gradle baseline report and the four runtime chains are not yet terminal at
this checkpoint. No additional evaluation or report refresh was requested.

#### Fourth configuration report assessed — 16:25 UTC

Gradle baseline head
[9567199](https://teamcity-nightly.labs.intellij.net/build/9567199) finished
FAILURE at **16:24:15 UTC**. Its report
[9567208](https://teamcity-nightly.labs.intellij.net/build/9567208) finished
SUCCESS at the same time, after 16:15:14–16:24:15 (**541 seconds**). All four
configuration chains are now terminal; publication success does not change
either failed Gradle configuration grade.

The three allowed publications were downloaded under
`/tmp/tc-two-project-results.55tDhX/report-9567208/publish/`. The collection
marker is **16:15:20.186728 UTC**. All 212 unique evaluator records and the
entire case matrix exactly equal verified report `9567201`; regression JSON
also matches exactly. Thus this fourth report preserves the same completed
configuration checks/identities/cost, original historical evidence, profile
separation, assisted exclusion, unsupported modes, and not-executable
preflight. The HTML ledger independently contains exactly 50 rows, labelled
`Showing 50 of 212 unique evaluator jobs`. No warnings or mature regression
failures are present; neither statement is a new eval pass.

At 16:25 UTC all four original first-green evals remain RUNNING; their reports
are queued waiting for unfinished dependencies. No new terminal eval result
or measured usage is available: fresh cohort coverage remains **4/8,
$20.079202**, with four unknown costs. No new run, refresh, or target change
was requested. The monitor remains active for those four runtime chains.

#### Maven baseline runtime result — 16:31 UTC

Maven first-green baseline
[9567210](https://teamcity-nightly.labs.intellij.net/build/9567210) finished
FAILURE at **16:30:19 UTC**, after starting at 15:59:58 (**1821 seconds**).
Only `/tmp/tc-two-project-results.55tDhX/9567210/publish/eval-result.json`
was downloaded. It matches `clean-spring-boot-maven`, case hash
`c8ea3ee033a54c0ee5680ea887110be767763144f44ab1ad9aee3927dcdb5f10`, baseline,
`cli-only`, harness `e93b46cd89c752e9d8a1c18ff818db457013133a`, and profile
`claude-default-two-project-3600s-v1`. The USD-cap field is absent, timeout
3600 seconds, agent exit 0, `agentTimedOut: false`, and no error category.
Overall/grade status is **failed, 11/12**.

The only failed check is `requiredArtifactRules`. Passed checks are
`configurationValidated`, `firstBuild`, `testsExecutedAndReported`,
`artifactsPublished`, `toolchain`, `sourceMutations`, `minimumJobs`,
`requiredStepTypes`, `requiredStepProperties`, `forbiddenStepProperties`, and
`requiredTests`. Therefore a real successful build was obtained, but the
complete eval contract was not satisfied. Actual artifact presence and a
complete declared publication rule set are different assertions; the safe
result does not specify which individual rule failed.

Frozen verification head
[9568295](https://teamcity-nightly.labs.intellij.net/build/9568295), selected
by `unique-pipeline`, reports seven attempts and exactly one member,
[9568849](https://teamcity-nightly.labs.intellij.net/build/9568849): SUCCESS,
**39 tests, all 39 successful, one artifact**. Read-only CLI dependency-tree
and job metadata independently confirm the head and sole child SUCCESS;
the child ran **16:23:25–16:24:28 UTC (63 seconds)** and says `Tests passed: 39`.
JDK diagnostics require 21 and show one matching declaration in one job;
`runtimeVerified` remains false. No evaluated target was repaired by this
monitor, and no attempt-level cause is inferred from logs or trajectories.

Measured usage is **$7.813103**: 224 input / 57,318 output tokens,
10,002,696 cache-read / 137,028 cache-write. Published counters: 124 tool
calls, 65 recognized TeamCity CLI, zero MCP/TeamCity or probe calls, 59 other.
Phase seconds: bootstrap 8, preparation 3.383, agent 1796.789, observation
0.395, build wait 2.091, grading 3.210, cleanup 0.005, harness total 1805.873.
Agent-process duration is not model-thinking time. Cleanup is deferred and
objects are not removed.

Fresh measured coverage is now **5/8 evals, $27.892305**; the three running
eval costs remain unknown. Maven skill `9567212` and Gradle skill/baseline
`9567206`/`9567215` are still RUNNING. Maven baseline head `9567194` is
nonterminal and report `9567209` is running; the other three runtime reports
wait for their eval dependencies. Earlier report snapshots with this baseline
marked RUNNING are superseded by its safe terminal artifact, not retroactively
rewritten. No new eval, retry, refresh, control, or target mutation was requested.

#### Final runtime results and cohort completion — assessed 19:30 UTC

The remaining safe artifacts and all reports were assessed at **19:30 UTC**
on 2026-10-01 (the queued heartbeat timestamp is not the observation time).
All eight evals finished by **17:00:19 UTC**, all reports by **17:09:11**, and
all heads by **17:09:16**. The exact full-revision-filtered CLI list contains
all original 24 IDs and no additional eval child for this revision; no new
invocation was requested by the monitor. The three remaining evals have no
cancellation metadata.

| Runtime case / arm | Eval | UTC start–finish | TeamCity wall | Outcome | Measured USD |
| --- | --- | --- | --- | --- | --- |
| Maven / skill | [9567212](https://teamcity-nightly.labs.intellij.net/build/9567212) | 15:59:58–17:00:19 | 3621 s | agent-timeout; no completed grade | unknown |
| Gradle / skill | [9567206](https://teamcity-nightly.labs.intellij.net/build/9567206) | 15:59:57–17:00:19 | 3622 s | agent-timeout; no completed grade | unknown |
| Gradle / baseline | [9567215](https://teamcity-nightly.labs.intellij.net/build/9567215) | 15:59:58–16:43:09 | 2591 s | failed, 10/14 | 9.9591695 |

All three `publish/eval-result.json` files, in the existing temporary results
directory, match their expected case/hash/arm, `cli-only`, full harness
revision `e93b46cd89c752e9d8a1c18ff818db457013133a`, and profile
`claude-default-two-project-3600s-v1`. Each confirms **no USD-cap field** and
the 3600-second agent timeout. No real prompts, trajectories, or eval logs
were inspected.

Both skill runtime results are `errored` / `agent-timeout`, exit **124**,
`agentTimedOut: true`, empty checks, and absent `gradeStatus`,
`verificationDiagnostics`, and `agentUsage`. They are not fabricated 0/12 or
0/14 grades, and no chain IDs, per-job counts, runtime JDK proof, or measured
cost can be recovered from these safe results. This does not establish the
state of every underlying target build. Published numeric counters are 123
tools for Maven and 133 for Gradle, zero recognized CLI/MCP calls in both;
these counters alone do not establish an alternative transport or explain
the timeout. No trace-based attribution is made.

Gradle baseline exits 0, without timeout or error category, but fails four
checks: `requiredStepTypes`, `requiredStepProperties`,
`requiredAgentRequirements`, and `requiredJobs`. All ten other checks pass:
`configurationValidated`, `firstBuild`, `testsExecutedAndReported`,
`artifactsPublished`, `toolchain`, `sourceMutations`, `minimumJobs`, `jobCount`,
`requiredArtifactRules`, and `jobResults`. Thus it achieves a real successful
runtime chain but not the complete configuration/runtime contract.

Its frozen `unique-pipeline` verification head is
[9569614](https://teamcity-nightly.labs.intellij.net/build/9569614), with
11 recorded attempts and two unique successful members. Test job
[9569468](https://teamcity-nightly.labs.intellij.net/build/9569468) has one
successful test and two artifacts; package job
[9568438](https://teamcity-nightly.labs.intellij.net/build/9568438) has zero
tests and two artifacts. Aggregate evidence is **one successful test / four
artifacts**. The per-job `jobResults` check passes, unlike a mere aggregate
count. Read-only CLI metadata confirms all three SUCCESS; the test job ran
16:34:12–16:36:04 (112 s), package 16:19:30–16:22:34 (184 s). The package job
appears both directly and beneath the test job in the dependency DAG; the
diagnostics correctly count it once. Both jobs declare JDK21, with
`declaredMatch: true` and **`runtimeVerified: false`**. These target builds were
not manually repaired by this monitor.

Gradle baseline usage is 260 input / 60,057 output tokens, 13,738,379 cache-read
/ 157,921 cache-write, and **$9.9591695**. Tool counters: 147 total, 56
recognized TeamCity CLI, zero MCP/TeamCity or probes, 91 other. The two timeout
usage records are absent, not zero. All three defer cleanup and report no
objects removed.

| Eval | Bootstrap | Preparation | Agent | Observation | Build wait | Grading | Cleanup | Harness total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 9567212 | 6 | 3.114 | 3600.002 | 0.038 | 1.500 | absent | 0.005 | 3604.659 |
| 9567206 | 6 | 3.132 | 3600.002 | 0.174 | 2.023 | absent | 0.006 | 3605.337 |
| 9567215 | 10 | 3.176 | 2560.151 | 0.264 | 2.068 | 4.986 | 0.005 | 2570.650 |

Values are published seconds, not inferred model-thinking time; TeamCity wall
times are separate. No budget or timeout was increased.

#### Final report verification and bounded outcome

The remaining four reports all finished SUCCESS; their evaluator heads remain
FAILURE because the evals did not satisfy the entire contract.

| Case / arm | Head / terminal UTC | Report / UTC start–finish / wall | Collection marker UTC |
| --- | --- | --- | --- |
| Maven / baseline | [9567194](https://teamcity-nightly.labs.intellij.net/build/9567194), 16:39:12 | [9567209](https://teamcity-nightly.labs.intellij.net/build/9567209), 16:30:20–16:39:11, 531 s | 16:30:26.010671 |
| Gradle / baseline | [9567198](https://teamcity-nightly.labs.intellij.net/build/9567198), 16:52:11 | [9567216](https://teamcity-nightly.labs.intellij.net/build/9567216), 16:43:10–16:52:11, 541 s | 16:43:15.358783 |
| Maven / skill | [9567200](https://teamcity-nightly.labs.intellij.net/build/9567200), 17:09:16 | [9567211](https://teamcity-nightly.labs.intellij.net/build/9567211), 17:00:20–17:09:11, 531 s | 17:00:26.508581 |
| Gradle / skill | [9567193](https://teamcity-nightly.labs.intellij.net/build/9567193), 17:09:16 | [9567205](https://teamcity-nightly.labs.intellij.net/build/9567205), 17:00:20–17:09:11, 531 s | 17:00:26.268873 |

Only the three allowed publications per report were downloaded to the existing
`report-<id>/publish/` directories. Reports `9567209` and `9567216` contain
five and six terminal cohort records, respectively; the still-running cells
in those older snapshots are not final evidence. **Both `9567211` and
`9567205` contain all eight terminal cohort results**, so no refresh is needed
or authorized. All eight identities, checks, status/grade, exit/timeout/error,
usage, numeric tool counters, phase timings, and available verification
diagnostics match their safe artifacts. Missing timeout usage/diagnostics are
sanitized to empty objects and missing gradeStatus to null, not to cost zero
or a scored failure. The verified profile fingerprint remains `e0be5a54...`.

Every remaining report preserves all **204** pre-cohort evaluator records,
including all 202 restored records plus the previous bounded-pair results,
with their original verdicts, revisions, identities, checks, usage, timings,
and assisted labels. The ten restored case rows are still represented; where
the matrix selects a fresh result, the historical run remains in history,
not regraded against the new contract. Each report has 216 references / 212
unique evaluator IDs, zero warnings, exactly 50 HTML ledger rows, and the
116-supported-slot denominator. Assisted TDD remains excluded, preflight
not executable, and the five MCP-only queue modes unsupported.

The final matrix selects the eight new results under their own matching
case/version/revision/profile. All four pairs have only one sample per arm
and `insufficient-samples`. Regression JSON has no mature failures, with
33 insufficient-sample and 33 insufficient-history findings at minimum three
samples; report/regression SUCCESS is **not** a claim of eval success.
Final report-wide measured usage is **$301.844881 across 90/212 jobs**, an
incomplete historical total, not the cost of this cohort.

The bounded fresh cohort is complete: **eight invoked/eight terminal, two
full passes, four completed failed grades, two ungraded agent timeouts**.
Fresh measured cost is **$37.8514745 across six of eight invocations**, plus
unknown costs for skill runtime `9567212` and `9567206`. Earlier unknown
interrupted-attempt costs remain separately recorded, not merged into this
cohort or treated as zero. There was no $3 cap in any of these eight runs.

For the user's requested coverage, both repositories now have fresh paired
configuration and first-green evidence on source-executable contracts. Maven
configuration ties at 8/8; Gradle configuration is 7/10 skill versus 4/10
baseline and remains active, as independently confirmed after the user's
annotation. Neither Gradle configuration arm passes completely. In runtime,
the two baseline arms obtain successful builds but fail other contract
assertions (Maven 11/12, Gradle 10/14); both skill arms time out. This does not
show a skill advantage for first-green execution, and one pair does not prove
statistical lift. Reference controls remain non-eval evidence.

No additional eval, control, retry, report refresh, target repair, or project
deletion was requested. Unrelated validation selfcheck `9566936` remains a
separate unexplained failure. Concurrent dirty code/skill/cleanup/proposal
files and the user's PDF were untouched. Only this audit is committed/pushed;
the completed cohort monitor can be deleted after this result is reported.

### Post-cohort diagnosis and CLI-counter repair — 2026-10-01

After the completed cohort was reported and its monitor deleted, the user's
"продолжи" was scoped to safe diagnosis and a confirmed harness-counter fix.
No further Claude eval, control, retry, report refresh, timeout/budget increase,
or evaluated-target mutation was requested. The monitor remains deleted.

Read-only first-class CLI inspection on the same nightly server and sandbox
resolved the exact pipeline IDs from verification heads `9568295` (Maven
baseline) and `9569614` (Gradle baseline), then pulled their stored YAML.
Only structural projections were printed, not raw YAML, scripts, parameters,
logs, prompts, or trajectories. These are **present-day saved-configuration
observations**, not a historical regrade or an immutable configuration snapshot.
Materialized pipeline-job settings can show empty steps/artifact rules; the
stored YAML, also used by the harness adapter, is the relevant source here.

- Maven has one native `maven` step and only the publication rule
  `target/clean-spring-boot-project-*.jar`; it has no XML publication rule.
  Exact artifact listing of child `9568849` shows a `publish` directory, and
  listing that directory shows only
  `clean-spring-boot-project-0.0.1-SNAPSHOT.jar` (64,457,324 bytes).
  The earlier artifact count of one refers to a root entry, not independently
  to a leaf file. This is consistent with the saved `requiredArtifactRules`
  failure: 39 successful imported tests do not also prove XML publication.
- Gradle has two jobs, `build` and `test`, with four `script` steps each and
  no native `gradle` step. Both scripts match the generator and explicit
  `docker info` patterns, but neither job's `runs-on` matches the required
  Docker/container-engine declaration. JAR and XML publication rules are
  present. Thus the missing runner types, runner-specific task properties,
  and declared Docker requirements are concrete contract gaps. This does
  **not** mean Docker was unavailable or tests failed: the frozen chain and
  per-job runtime evidence already passed. Shell-text pattern matches alone
  do not establish execution order or whether a mentioned task executes.

A separate confirmed diagnostic defect was reproduced with synthetic events:
`agent_tool_summary` previously recognized only Bash command strings beginning
with `teamcity`. It missed the skill-prescribed
`TEAMCITY_URL=... teamcity ...` form and falsely accepted executable-name
prefixes such as `teamcity-helper`. The new bounded parser recognizes leading
environment assignments, `env`/`env --`, and exact executable basenames/paths.
Counts remain one per Bash tool call and the published schema remains numeric
only. Shell wrappers, line continuations, and later compound commands are not
fully parsed; the counter is not proof of transport compliance.

Six synthetic regression tests cover the supported forms, lookalikes,
malformed commands, unparsed wrappers, and publication privacy. This correction
does not establish which commands the historical agents actually ran, explain
the two skill timeouts, recover missing usage, or change any historical grade
or counter. No real agent trajectory was read. The two timeout costs therefore
remain unknown and cohort measured coverage remains $37.8514745 across six of
eight invocations.

Local validation of the concurrent workspace: **200 unit tests passed**.
An export of the exact staged tree, excluding concurrent work, independently
passed **182 unit tests**. Both trees validated **22 cases / zero errors**;
workspace and staged whitespace checks passed. Only the counter helper/call-site,
its new synthetic test file, and this audit are included in this repair;
pre-existing MCP-isolation edits in the same runner and all other concurrent
code/skill/cleanup/proposal/PDF changes are excluded.

### User-requested 120-minute JVM rerun — preparation, 2026-10-01

The user explicitly requested Maven and Gradle build evals with a 120-minute
timeout, **after fixing problems in the skill and harness**. This is new bounded
run authorization, not a continuation of the completed eight-invocation cohort
or a revival of its deleted monitor. Clarification was requested on skill-only
versus paired reruns and agent versus build-wait timeout. No new eval has been
queued at this preparation checkpoint. No USD cap is being introduced.

The repair addresses confirmed defects and contract gaps, not an invented root
cause for the two historical skill timeouts:

- The skill now explicitly audits saved YAML per job: native Maven/Gradle
  runners, JDK/capability selectors, Docker preflight where code generation or
  tests need it, and job-local outputs. It distinguishes JUnit import from raw
  XML publication and documents source-preserving separate Gradle generator
  and compilation invocations when a diagnosed task-graph error requires them.
  It also removes an obsolete REST-fallback exception and bounds unsupported
  CLI-operation discovery. No repository/server-specific answer is hardcoded.
- The Maven case asked to import XML but graded XML artifact publication as
  well. Both runtime prompts now explicitly state the already-graded runner
  and output requirements; Gradle also states the exact two-job topology and
  Docker scheduling/preflight requirement. This resolves an instruction/contract
  mismatch rather than weakening any assertion. Expected checks, source pins,
  verification commands and case statuses are unchanged. Configuration-only
  cases, including the user's active Gradle row, are untouched.
- The harness now publishes a separately allowlisted
  `verificationErrorCategory`, preserving `agent-timeout` as the primary
  failure while identifying absent pipeline, absent queued build, ambiguous
  pipeline, incomplete chain, queue stall, wait expiry, or failed observation.
  It never publishes CLI error text, scripts or parameters. The collector
  retains that field and both numeric agent/build-wait limits. A timeout without
  a completed grade or provider usage still has no invented grade or cost.
  The previously committed environment-prefixed CLI-counter correction remains.

New runtime case versions (only the prompt field changed):

- Maven: `f8e61aed249c5d89f02f76e3d83f5346c505a9a4b4bd8e7e3eda2d01cbcfee9c`
- Gradle: `437c6bddded92924d2beb9f27f39097a38cbd8b2128704fe43042e9aff4e06fd`

These versions and the new timeout/profile must remain separate from previous
samples; a new skill-only result cannot establish paired statistical lift.
Historical grades and unknown costs remain unchanged.

Preflight uses only authenticated first-class CLI on
`https://teamcity-nightly.labs.intellij.net`, parent `TeamCity_Sandbox_TCEvals`.
The stored `RunEvalCase` YAML passed server validation and matches committed
jobs/parameters after excluding its preserved server-local Claude connection
reference. Its head is attached to `TeamCity_Sandbox_TCEvals_Evals`.
Evaluator `executionTimeoutMin` is 0 (no shorter TeamCity timeout), and the
exact `env.EVAL_AGENT_MAX_BUDGET_USD` lookup reports not found. The server-local
connection and persistent evaluator settings are not changed.

Current-workspace validation: **205 unit tests passed**, including five new
synthetic failure/timeout/privacy tests; **22 cases valid**; skill validator and
whitespace checks passed. Concurrent MCP-isolation/runner YAML/skill edits,
cleanup/proposal changes and the user's PDF remain outside this repair.

An export of the exact staged tree independently passed **187 tests**, all
22 cases, and skill validation. The VCS-root readback now shows default branch
`refs/heads/korotkova/evals` and branch specification `+:refs/heads/*`; no root
change was made here. The preflight snapshot is under
`/tmp/tc-jvm-120min.cZ6sxB` and the tested staged export under
`/tmp/tc-jvm-staged.HCxHDx`.

With no alternative selected in the optional clarification, the announced
narrow interpretation is **two skill-only first-green evals**, one Maven and
one Gradle: agent timeout **7200 seconds**, existing build wait **3600 seconds**,
unchanged queue checkpoint/stall **120/600 seconds**, no USD cap and no automatic
retry. The build wait is a separate post-agent observation phase, not a promise
that the entire evaluator/report chain ends within 120 minutes. The new profile
is `claude-default-jvm-skill-7200s-v1`. Baseline/configuration/control runs are
not part of this dispatch.

#### Exact dispatch — 19:53 UTC

The repair was pushed as **`8d75c0f7b5a9acb7214f8bed1c2c50e567fa9f86`**.
Exactly two fresh skill first-green invocations queued at **19:53:02 UTC**:

| Case | Head | Eval | Report |
| --- | --- | --- | --- |
| Maven | [9584487](https://teamcity-nightly.labs.intellij.net/build/9584487) | [9584489](https://teamcity-nightly.labs.intellij.net/build/9584489) | [9584491](https://teamcity-nightly.labs.intellij.net/build/9584491) |
| Gradle | [9584488](https://teamcity-nightly.labs.intellij.net/build/9584488) | [9584490](https://teamcity-nightly.labs.intellij.net/build/9584490) | [9584492](https://teamcity-nightly.labs.intellij.net/build/9584492) |

Both used explicit branch `korotkova/evals` and the full repair revision,
clean checkout, and rebuilt dependencies. The current root's monitored branch
specification permits that explicit branch (unlike the earlier default-only
control root). The exact full-revision-filtered CLI listing contains all six
IDs and exactly two distinct eval children. Both evals started at **19:53:04
UTC** and are RUNNING at dispatch; report jobs wait on them. A RUNNING state
is not proof of Claude progress or a successful target build.

Per-run settings are `cli-only`, `claude -p`, skill arm,
`claude-default-jvm-skill-7200s-v1`, agent/build timeouts **7200/3600 seconds**,
queue checkpoint/stall **120/600 seconds**, sandbox `TeamCity_Sandbox_TCEvals`,
and no USD-limit override. No baseline, configuration eval, control, or retry
was started. Measured cost and final outcomes are not yet available.

At completion, assess only safe eval-result/report artifacts, including exact
case versions, revision/profile, both limits, primary and secondary error
categories, all checks, frozen-chain diagnostics, per-job counts, declared
versus runtime JDK evidence, timings and measured usage. Missing cost remains
unknown. Keep canceled or externally re-added invocations separate and request
no automatic replacement. Historical grades, restored rows and assisted
exclusions remain unchanged; do not compare these new versions/profile as a
fresh pair against old baseline samples. No deleted monitor was revived.

#### Terminal 120-minute results — assessed 2026-10-02

The user requested another check, concrete repairs, and necessary reruns
("проверь еще раз, исправь, перезапусти что надо"). Read-only first-class CLI
checks confirm the original six IDs on full revision `8d75c0f7b5a9acb7214f8bed1c2c50e567fa9f86`,
with exactly two evaluator invocations and no replacements. Both agents ended
**before** their 7200-second limits, but neither produced a completed grade.

| Skill eval | Terminal UTC (2026-10-01) / wall | Outcome | Measured provider cost |
| --- | --- | --- | --- |
| Maven [9584489](https://teamcity-nightly.labs.intellij.net/build/9584489) | 20:59:35 / 3991 s | errored; exit 1, not timed out; `agent-result-failed` | $13.472917 |
| Gradle [9584490](https://teamcity-nightly.labs.intellij.net/build/9584490) | 20:57:45 / 3881 s | errored; exit 1, not timed out; `agent-result-failed` | $10.3049765 |

Both safe artifacts also report `verification-pipeline-ambiguous`. Checks are
empty; `gradeStatus` and `verificationDiagnostics` are absent. These are
**ungraded errors, not scored 0/12 or 0/14 results**. Exact case IDs/versions,
skill arm, cli-only mode, harness revision, and
`claude-default-jvm-skill-7200s-v1` match dispatch. Agent/build-wait limits
remain 7200/3600 seconds; `agentMaxBudgetUsd` is absent. Cleanup was deferred,
with no objects removed. Artifacts are under
`/tmp/tc-jvm-results.VFEQNI/<eval-id>/publish/eval-result.json`.

The pair's measured total is **$23.7778935 across both invocations**, not an
estimate or a new cap. Earlier unknown timeout/interruption costs remain
unknown and outside this amount. Safe usage and timings:

| Field | Maven | Gradle |
| --- | ---: | ---: |
| Input / output tokens | 292 / 97,650 | 226 / 89,886 |
| Cache read / cache write tokens | 18,031,244 / 200,691 | 12,579,523 / 175,834 |
| Tool calls / recognized CLI calls | 160 / 1 | 125 / 0 |
| Bootstrap / preparation seconds | 6 / 2.772 | 6 / 2.911 |
| Agent / observation seconds | 3971.682 / 0.328 | 3860.841 / 0.168 |
| Build wait / cleanup / total seconds | 1.579 / 0.005 / 3976.366 | 2.012 / 0.005 / 3865.938 |

Grading duration is absent. Agent-process duration includes tools and waits,
not measured thinking time. Recognized CLI counters undercount shell wrappers
and compound commands; 0/1 does not establish that CLI was unused. These safe
totals explain the scale of measured usage, not which activity caused it.
No real trajectories, prompts, or eval logs were read. The provider's exact
failure subtype is not retained by this harness; the primary exit cause
therefore remains unknown.

Both report jobs succeeded: [9584492](https://teamcity-nightly.labs.intellij.net/build/9584492)
ran 20:57:45–21:08:37 UTC; [9584491](https://teamcity-nightly.labs.intellij.net/build/9584491)
ran 20:59:40–21:10:01 UTC. Their heads `9584488` and `9584487` finished FAILURE
at 21:08:37 and 21:10:02. Only `index.html`, `runs.json`, and `regressions.json`
were downloaded for each report. Both snapshots contain both terminal new
records, matching all safe artifact fields and the profile's SHA256
`b172c10655d38111b10d17c5028e4e146ceb0b2c151193cb47515f270fe83344`.
Collection markers (20:57:55.375240 and 20:59:46.865814 UTC) mark the start of
collection, not a single instantaneous observation of every job.

Both reports preserve all **212** preceding unique jobs with unchanged
identities, revisions, verdicts, checks, usage, timings, and assisted flags.
There are now 214 unique evaluator jobs, 22 contracts, 116 supported arm slots,
zero warnings, all ten restored case rows, and exactly 50 HTML ledger rows.
Assisted TDD remains excluded with sampleSize 0; preflight remains not
executable and the five MCP-only queue modes unsupported. The user's Gradle
configuration case remains active. Each regression file has 33
insufficient-sample and 33 insufficient-history findings, zero mature failures,
and a minimum of three samples. Report SUCCESS is not eval success. The report
total **$325.622775 across 92/214 jobs** is incomplete historical measured
coverage, not this pair's cost. No report refresh was requested.

#### Confirmed task-context gap and bounded completion repair

Scoped saved-YAML/metadata inspection found two Maven pipelines (`maven-verify`
and `probe-b`) and three Gradle pipelines (`probeB`, `probeC`, `probeD`). Only
Gradle `probeD` topology was inspected: one job with three steps
(`script`, `gradle`, `script`) and no publication rules, not the requested
two-job verification pipeline. No topology is inferred from the other names.
Maven's saved verification job has script/Maven steps and three publication
rules but no `runs-on`. Its successful child `9585397` has zero tests and
zero artifacts; it is not proof of Maven verification. Other checked Maven
children remain queued with no idle compatible agents: compatibility count
was unavailable, so this is not proof of zero-compatible agents.

Gradle head `9590221` failed although child `9590225` succeeded. A failed head
cannot be promoted to green from its child. Its root declares
`refs/heads/main` with `+:refs/heads/main`; an invalid branch is not inferred
from earlier control failures. Permission was requested for only narrow CLI
error summaries of `9590221` and `9586812`; no such summaries have been read
at this checkpoint. No evaluated target was repaired, canceled, or deleted.

A separate harness contract gap is confirmed directly in code: observation
reads `requestedConfiguration.sourcePath`, but that path was not supplied to
the agent. Both runtime cases expect `.teamcity.yml` without mentioning it in
their prompt. The repair exposes only the requested format/path in task
context, identically for both arms, and keeps dry-run previews consistent.
Private assertions, reference commands, and historical outcomes remain hidden.
The final file must match the validated/read-back verification configuration;
temporary diagnostics remain separate. This does not authorize source edits
or builds when the task prohibits them.

The skill now keeps a primary pipeline distinct from capability probes,
returns concrete probe findings to that pipeline, retains the requested final
source, and requires its full chain/tests/outputs before claiming completion.
It does not prescribe a repository/server-specific solution or delete probes.
Strict source matching and fail-closed ambiguity remain unchanged. We cannot
tell from the safe artifacts whether the old source file was absent,
mismatched, or matched multiple pipelines; this correction is **not** proof
that either historical agent failure was caused by a missing file.

Five new synthetic tests verify public context, private-answer exclusion,
identical skill/baseline invocation context, configuration-only stopping
conditions, fixtures, and dry-run behavior. The source-binding regression now
also exercises a non-default path with multiple pipelines. Workspace validation:
**210 tests passed**, all **22 cases valid**, skill validation and whitespace
checks passed. Concurrent MCP isolation, runner YAML, skill routing, cleanup,
proposal, and PDF changes remain excluded from this repair.

Any necessary live rerun is bounded to one fresh skill-only invocation per
affected JVM runtime case, with the same 7200/3600-second limits, 120/600-second
queue settings, and no USD cap. It tests the concrete task-context/completion
repair, not a claim that the unknown primary failure has been fixed. No
baseline/control/configuration rerun, automatic retry, timeout increase,
manual target repair, or revival of a deleted monitor is authorized here.

The exact staged export at `/tmp/tc-jvm-exact.kuTskz` independently passed
**192 unit tests**, all 22 cases, and skill validation; only this audit, the
task-context helper/call sites, two synthetic test files, and three workflow
hunks are included. Server-stored evaluator YAML was validated without a push.
Its jobs match the committed evaluator except for the preserved server-local
Claude connection; parameters match. The exact eval-job execution timeout is
0 and its USD-budget parameter is absent. No persistent evaluator setting,
Claude connection, case assertion/status/hash, or source pin was changed.

#### Source-bound repair dispatch — 2026-10-01 23:19 UTC

Repair **`34d671a2023d015c367b1c4f9c44fbbef96e58f7`** is pushed. The read-back
evaluator VCS root still uses `refs/heads/korotkova/evals` and monitors
`+:refs/heads/*`; it was not changed. A full-revision-filtered listing was empty
before dispatch. Exactly two new skill-only first-green invocations were then
requested with explicit branch and full SHA, clean checkout, and rebuilt
dependencies:

| Case | Head | Eval | Report | Eval start UTC |
| --- | --- | --- | --- | --- |
| Maven | [9595989](https://teamcity-nightly.labs.intellij.net/build/9595989) | [9595992](https://teamcity-nightly.labs.intellij.net/build/9595992) | [9595993](https://teamcity-nightly.labs.intellij.net/build/9595993) | 23:19:00 |
| Gradle | [9595988](https://teamcity-nightly.labs.intellij.net/build/9595988) | [9595990](https://teamcity-nightly.labs.intellij.net/build/9595990) | [9595991](https://teamcity-nightly.labs.intellij.net/build/9595991) | 23:18:59 |

Both evals queued at 23:18:59 UTC and are RUNNING at this checkpoint; reports
wait on them. Each head's dependency tree and all six IDs in the exact-SHA
listing were checked. The two eval IDs are distinct; repeated references to
each eval within its own tree are not additional invocations. Interim
`status: SUCCESS` on a RUNNING job is not a terminal pass or proof of Claude
progress.

Requested per-run settings: `cli-only`, `claude -p`, skill arm,
`claude-default-jvm-source-bound-7200s-v1`, agent/build timeouts 7200/3600
seconds, queue checkpoint/stall 120/600 seconds, explicit nightly server and
`TeamCity_Sandbox_TCEvals`. No USD cap was supplied. Case versions remain
`f8e61aed249c5d89f02f76e3d83f5346c505a9a4b4bd8e7e3eda2d01cbcfee9c` (Maven)
and `437c6bddded92924d2beb9f27f39097a38cbd8b2128704fe43042e9aff4e06fd` (Gradle).
Source pins remain unchanged. The new task context is tracked by this new
harness revision/profile, not compared as a paired improvement against older
baseline runs.

At terminal, safe artifacts must still verify actual identity/profile/limits,
absent cap, primary/secondary errors, checks or absent grade, chain/JDK evidence,
timings, and measured usage. Cost is not yet available. No baseline/control/
configuration invocation, automatic retry, report-only refresh, target repair,
project deletion, or new/revived monitor was started. The only pending error-log
permission request still concerns `9590221` and `9586812`, not these eval logs.

#### Source-bound pair terminal evidence and shared script defect — 2026-10-02

Both source-bound skill evals and their reports are terminal. Safe artifacts
match the dispatched case hashes, `cli-only`, harness `34d671a`, profile
`claude-default-jvm-source-bound-7200s-v1`, 7200/3600-second agent/build limits,
and absent USD cap. Neither eval completed grading: checks are empty and
`gradeStatus`/`verificationDiagnostics` are absent. These are ungraded errors,
not scored zeroes or passes.

| Case / eval | Started / finished UTC | Wall | Agent exit / timeout | Primary / secondary error | Measured USD |
| --- | --- | --- | --- | --- | --- |
| [Maven 9595992](https://teamcity-nightly.labs.intellij.net/build/9595992) | Oct 1 23:19:00 / Oct 2 00:41:51 | 4971s | 1 / false | agent-result-failed / build-queue-stalled | 8.624968 |
| [Gradle 9595990](https://teamcity-nightly.labs.intellij.net/build/9595990) | Oct 1 23:18:59 / Oct 2 00:12:30 | 3211s | 0 / false | build-queue-stalled / build-queue-stalled | 11.3649215 |

Measured pair cost is **$19.9898895**, separate from the previous
9584489/9584490 pair ($23.7778935) and earlier interrupted attempts with unknown
cost. Maven usage: 210 input / 62935 output / 10980456 cache-read / 155204
cache-write tokens; Gradle: 224 / 106052 / 13316023 / 204539. Reported tool
counts are 117/121, but recognized CLI counts of 2/2 remain an undercounting
caveat, not evidence of only two actual CLI operations.

Phase seconds (bootstrap / preparation / agent / observation / build wait /
cleanup / total): Maven 6 / 3.107 / 4342.787 / 0.451 / 610.713 / 0.005 /
4957.063; Gradle 6 / 3.150 / 2580.847 / 0.097 / 611.306 / 0.005 / 3195.406.
Safe queue reason is `other` for both. Cleanup was deferred; no target deletion
or cancellation was performed.

[Gradle report 9595991](https://teamcity-nightly.labs.intellij.net/build/9595991)
succeeded at 00:21:46; its Maven cell is an interim running snapshot.
[Maven report 9595993](https://teamcity-nightly.labs.intellij.net/build/9595993)
succeeded at 00:50:23 and contains both final results. Heads 9595988/9595989
failed. No refresh is needed. The later snapshot retains 216 unique eval jobs,
116 slots, the 50-row ledger, restored historical provenance, assisted TDD
exclusion, and preflight-not-executable/unsupported-mode labels. Its
$345.612664 measured across 94/216 jobs is incomplete historical coverage, not
this pair's cost. Insufficient regression samples/history do not establish a
pass or comparative lift.

The user supplied the exact TeamCity UI error for Maven child
[9596014](https://teamcity-nightly.labs.intellij.net/build/9596014):
`Invalid step parameters: Script content must be specified`, and noted the
same issue elsewhere. Read-only stored-YAML inspection confirmed the common
defect in all eight script steps: two in Maven `maven_verify`, three each in
Gradle `Build_Package` and `Integration_Tests` (children
[9596030](https://teamcity-nightly.labs.intellij.net/build/9596030) and
[9596029](https://teamcity-nightly.labs.intellij.net/build/9596029)). They use
`script`, with neither `script-content` nor `script-file`. The working control
uses `script-content`. No raw scripts, eval logs, prompts, or trajectories were
read into this audit. The stored YAML was already available: missing this
check was our diagnostic gap, not a reason to ask the user to diagnose it.

Both malformed definitions pass `pipeline validate`; the refreshed server
schema constrains step type but not runner-specific source fields. The
harness's `configurationValidated` checks also lacked a universal script
parameter check. Generic queue metadata and empty virtual-job step listings
did not expose this defect. It is a confirmed configuration blocker, not proof
of insufficient agent capacity, and does not explain Maven's provider exit 1
or establish that no other problems remain. Historical grades are unchanged.

#### User-authorized script-parameter repair and bounded rerun

The user explicitly requested **"добавь и перезапусти"**. Scope: repair this
shared skill/harness defect, then exactly one fresh skill-only first-green
eval for each of the two affected repositories. Preserve the 7200-second agent
limit, 3600-second build wait, queue checkpoint/stall 120/600, unchanged case
hashes/source pins, `claude -p`, and no USD cap. This does not authorize baseline,
configuration, control, automatic retry, report-refresh, timeout increases,
manual evaluated-target repair, or resurrecting deleted monitors.

The skill now requires correct script source fields and saved-YAML inspection
before queueing/waiting, without treating schema success as runner validity.
A shared harness validator rejects the `script` alias, missing/blank sources,
non-string sources, and conflicting inline/file sources. The CLI bridge
applies it before `pipeline validate/create/push` for both arms, returning
only fixed reasons and numeric job/step positions so the agent can correct
the file. Real server validation remains required. Post-agent observation
independently checks the source-bound stored pipeline before polling; both
graders refuse `configurationValidated` for invalid script steps. This narrow
gate does not claim to verify shell syntax, script-file existence, parameter
resolution, or runtime/agent compatibility.

Safe `configurationDiagnostics` publish only counts, positions, and allowlisted
categories. `verification-invalid-script-steps` survives artifact/report
collection while preserving an earlier primary agent error and absent grade.
Read-only replay detects 2/2 invalid old Maven scripts and 6/6 old Gradle scripts,
and accepts both working control scripts. This is a validator regression check,
not a historical regrade or a new live control. No evaluated target was edited.

Validation: **223 workspace tests and 205 tests in the exact staged export**
passed; all 22 cases and skill validation passed, with no whitespace errors.
The exact export excludes concurrent MCP isolation, evaluator YAML, cleanup,
proposal, skill routing/debugging, and PDF changes. Stored evaluator YAML passes
the server validator and the new script check; its jobs match committed YAML
except for the preserved server-local Claude connection, and parameters match.
The exact eval job has no USD-cap parameter. Its attached root is still
`TeamCity_Sandbox_TCEvals_Evals`, `refs/heads/korotkova/evals`, monitored by
`+:refs/heads/*`; no persistent evaluator settings or root were changed.

#### Script-parameter repair dispatch — 2026-10-02 11:50 UTC

Repair **`a6577850db71510c895325c5904b0cd3bfb9d90d`** is pushed. A full-SHA
listing was empty before dispatch. Exactly two fresh skill-only runtime evals
were requested with that full revision, branch `korotkova/evals`, clean
checkout, and rebuilt dependencies. Both dependency trees and the full-SHA
listing then confirmed exactly these six IDs, including distinct eval children:

| Case | Head | Eval | Report | Eval start UTC |
| --- | --- | --- | --- | --- |
| Maven | [9620076](https://teamcity-nightly.labs.intellij.net/build/9620076) | [9620078](https://teamcity-nightly.labs.intellij.net/build/9620078) | [9620079](https://teamcity-nightly.labs.intellij.net/build/9620079) | 11:50:24 |
| Gradle | [9620077](https://teamcity-nightly.labs.intellij.net/build/9620077) | [9620081](https://teamcity-nightly.labs.intellij.net/build/9620081) | [9620080](https://teamcity-nightly.labs.intellij.net/build/9620080) | 11:50:24 |

All queued at 11:50:23 UTC. Both evals are **RUNNING**, and reports await them;
interim `SUCCESS` status on running jobs is not a pass or proof of Claude
progress. Requested profile: `claude-default-jvm-script-gate-7200s-v1`,
`cli-only`, `claude -p`, agent/build limits 7200/3600 seconds, queue
checkpoint/stall 120/600, explicit nightly server and `TeamCity_Sandbox_TCEvals`,
no USD cap. The evaluator's `executionTimeoutMin` is 0. Case hashes remain
`f8e61aed249c5d89f02f76e3d83f5346c505a9a4b4bd8e7e3eda2d01cbcfee9c` (Maven)
and `437c6bddded92924d2beb9f27f39097a38cbd8b2128704fe43042e9aff4e06fd` (Gradle).
Source pins and case assertions/statuses are unchanged. New bridge feedback is
part of this new harness/profile, not a same-harness comparison with an older
baseline or a claim of statistical lift.

This consumes the latest bounded rerun authorization. No additional eval,
control, report refresh, manual target fix/cancellation, project deletion, or
new/revived monitor was requested. Old failures remain separate. At terminal,
download only the safe eval result and report artifacts, verify identity,
limits/absent cap, configuration/chain/JDK diagnostics, checks or absent grade,
timings and measured cost. Current cost is unknown, not zero. Unexpected
external cancellations/replacements must remain separately audited; do not
request replacements. Concurrent dirty changes remain unstaged and preserved.

#### Maven script-gate result — assessed 2026-10-02 12:22 UTC

[Maven eval 9620078](https://teamcity-nightly.labs.intellij.net/build/9620078)
finished **FAILURE** at 12:20:15 UTC (started 11:50:24; wall 1791s). Its safe
`publish/eval-result.json` matches the exact Maven case/hash, skill arm,
`cli-only`, harness `a6577850db71510c895325c5904b0cd3bfb9d90d`, profile
`claude-default-jvm-script-gate-7200s-v1`, 7200/3600-second limits, and absent
USD cap. Agent exit is 0, no timeout; result and grade are **failed**, with
no primary or secondary execution-error category. This is a completed grade,
unlike the preceding ungraded source-bound pair.

**11/12 checks passed.** Only `firstBuild` failed. Passed checks:
`configurationValidated`, `testsExecutedAndReported`, `artifactsPublished`,
`toolchain`, `sourceMutations`, `minimumJobs`, `requiredStepTypes`,
`requiredStepProperties`, `forbiddenStepProperties`, `requiredArtifactRules`,
and `requiredTests`. Final stored configuration has two checked script steps,
zero invalid steps and no script-parameter issues. This establishes final
configuration validity for that narrow gate, not what every intermediate
agent attempt contained.

The source-matched verification chain has one head attempt:
[head 9620587](https://teamcity-nightly.labs.intellij.net/build/9620587) is
**FAILURE**, while its sole child
[Maven verify 9620878](https://teamcity-nightly.labs.intellij.net/build/9620878)
is **SUCCESS**, with **39/39 successful tests and 8 artifacts**. A read-only CLI
tree confirms both terminal states. The head ran 12:16:35–12:17:42 UTC; the child
12:16:35–12:17:41. Head status text reports 39 passed tests and a successful
child chain but does not explain its FAILURE. `run view` does not expose build
problem details on this CLI, so the root cause remains unknown; no raw logs,
prompts or trajectories were read. Child success does not override the failed
head or justify regrading. JDK21 is declared for the one job, but
`runtimeVerified` remains false; an agent-authored build-status message naming
Java21 is not independent runtime proof.

Measured cost: **$7.2389395** for this Maven invocation only; new Gradle cost is
not yet available. Usage: 190 input / 59323 output / 8711109 cache-read /
139109 cache-write tokens. Safe counters record 107 tools, 1 recognized CLI,
zero TeamCity MCP calls; the recognized-CLI undercount caveat still applies.
Phase seconds: bootstrap 8, preparation 2.866, agent 1762.223, observation
0.086, build wait 2.317, grading 3.215, cleanup 0.005, total 1770.713.
Cleanup is deferred; no project was deleted or target manually repaired.

Safe result retained locally at
`/tmp/tc-script-gate-results.3vJGX7/maven/publish/eval-result.json`.
Maven report 9620079 is RUNNING, head 9620076 is nonterminal FAILURE.
Gradle eval 9620081 remains RUNNING, report 9620080 waits on it. Monitor remains
active; no new evaluation, retry, control, report refresh or cancellation was
requested. Assess the terminal reports and remaining Gradle result before
closing the monitor or claiming an overall outcome.
