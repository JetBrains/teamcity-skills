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
