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
