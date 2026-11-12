# Why eval runs take longer than 10 minutes

Research for [TW-104541](https://youtrack.jetbrains.com/issue/TW-104541).
Sources: the 2026-09-30 evals report attached to the ticket, each run's
`eval-result.json` and build log, and the 90 most recent `Run eval case`
builds on teamcity-nightly (2026-10-08 to 2026-11-04).

## Summary

- 15 of the 50 runs in the report took longer than 10 minutes. 9 are live
  first-green cases (27–114 min). 6 are configuration-only cases (12–16 min
  against a 15-minute agent limit).
- The time goes to five places: the agent itself; the harness waiting for a
  build after the agent exited; the executor token expiring after 63 minutes
  so the agent dies with a 401; the harness monitor killing the agent on a
  fixable error; and an agent-compatibility check that could not work (old
  CLI, wrong command).
- Fixed on `main` since the report: the monitor reads build problems before
  it stops the agent (commit `a7cf324`).
- Fixed in this branch: CLI pin 1.3.0 → 1.6.3 (native release archive), both
  skills check compatibility with `teamcity run view <queued-job-run-id>`
  instead of `agent jobs --incompatible` per agent.
- Open for the team: token expiry, waiting for a build after the agent, no
  transcripts on `main`, the skill arm slower than baseline on the simplest
  case, the bridge blocking `teamcity api`.

## The 15 runs

Job duration is from the report ledger. Causes are from `eval-result.json`
(`phaseTimings`, `errorCategory`) and the build log.

| Job | Case | Arm | Job, min | Agent, min | Wait after agent | Result | Cause |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 9435245 | spring-boot-kotlin-gradle-java25 | skill | 114 | unknown | unknown | errored, no category | Old harness: no phase timings or category. Agent exited 0. |
| 9428151 | spring-boot-kotlin-gradle-java25 | skill | 112 | unknown | unknown | errored, no category | `ConnectionResetError` in the CLI bridge at minute 19; usage accounting lost (354 output tokens, $9). |
| 9497653 | spring-petclinic-maven-yaml | skill | 87 | 26 | 60 min build wait | build-wait-timeout | Harness waited the whole `EVAL_BUILD_TIMEOUT` (3600 s) for a build that never finished. |
| 9470107 | spring-petclinic-maven-yaml | skill | 64 | 64 | 0 | failed, exit 1, $17 | Executor token expired at minute 63; agent exited with 401. |
| 9428148 | spring-boot-kotlin-gradle-java25 | skill | 63 | 60 | 0 | agent-timeout | Agent hit `EVAL_AGENT_TIMEOUT` 3600 s. |
| 9505871 | tdd-spring-maven | skill | 57 | 46 | 10 min queue wait | build-queue-stalled | Agent re-added `os-family: Linux`, created probe pipelines, 124 tool calls. Then the harness waited 600 s for a probe pipeline with 0 compatible agents. |
| 9435268 | spring-boot-kotlin-gradle-java25 | baseline | 42 | 42 | 0 | failed (containerImage) | Agent time: 161 tool calls around the JDK 25 container. |
| 9470110 | spring-petclinic-maven-yaml | baseline | 27 | 26 | 0 | failed | Agent time: 99 tool calls. |
| 9416640 | spring-boot-demo-gradle-testcontainers-pipeline | baseline | 16 | 15 | 0 | agent-timeout | Configuration only; agent hit the 900 s limit. |
| 9518060 | spring-boot-demo-gradle-testcontainers-pipeline | baseline | 14 | 13 | 0 | failed | Configuration only; 99 tool calls in 784 s. |
| 9401315 | spring-boot-demo-gradle-testcontainers-pipeline | baseline | 13 | 13 | 0 | failed | Configuration only; 103 tool calls. |
| 9516820 | spring-boot-demo-gradle-testcontainers-pipeline | skill | 13 | 12 | 0 | failed | Configuration only; 70 tool calls in 748 s. |
| 9416637 | spring-boot-demo-gradle-testcontainers-pipeline | skill | 13 | 12 | 0 | passed | Configuration only; 68 tool calls. |
| 9516823 | spring-boot-demo-gradle-testcontainers-pipeline | baseline | 12 | 11 | 0 | failed | Configuration only; 94 tool calls. |
| 9518088 | spring-boot-kotlin-gradle-java25-pipeline | skill | 11 | 10 | 0 | passed | Configuration only; 64 tool calls in 595 s. |

All 15 ran on CLI 1.3.0 and Claude Code 2.1.251. None has a published
transcript, so per-tool-call timing is unavailable.

### Are the long green runs correct?

Two of the 15 passed (9518088, 9416637). Both are configuration-only: the
grader checked job count, step types and properties, artifact rules, and
agent requirements against the case contract. No build ran, so runtime
correctness is not proven. On `main`, the 56-minute pass 10775935
(clean-spring-boot-maven, skill) is confirmed by the grader: 39 tests,
8 artifacts, Maven ran on JDK 21. Temporary projects are deleted after
6 hours, so the YAML itself can no longer be inspected.

## Causes

### 1. The executor token expires after about 63 minutes

The Claude build feature injects a short-lived token. About 63 minutes after
the agent starts, the API returns `401 Token is expired`; Claude Code writes
a synthetic assistant message and exits 1. The harness records
`agent-result-failed`. The run paid for an hour of agent work and got no
result.

Evidence: run 10005415, session start 23:11:12, synthetic 401 at 00:15:05.
32 of the 90 most recent builds ended this way (`agentSeconds` 3750–4040,
exit 1), $281 in total, $5–17 each.

`EVAL_AGENT_TIMEOUT` defaults to 3600 s, so the harness never stops the
agent before the token does.

### 2. The harness waits long after the agent exits

| Parameter | Default | Observed effect |
| --- | --- | --- |
| `EVAL_BUILD_TIMEOUT` | 3600 s | 9497653 waited 60 min for a build the agent had abandoned. The eval branch had 7200 s: eight runs on 2026-10-12 took 184–190 min. |
| `EVAL_QUEUE_STALL_TIMEOUT` | 600 s | 9505871 waited 10 min for a probe pipeline with 0 compatible agents. |

The agent is supposed to drive the build to green itself. A build still
running after the agent exits is a harness artifact, not a result.

### 3. The agent is slow on its own

Configuration-only cases spend 10–13 of their 15 minutes and 50–100 tool
calls on one YAML file that nobody builds.

On `main` (2026-11-02 to 2026-11-04, case clean-spring-boot-maven):

| Job | Arm | Result | Agent, min | CLI calls | Cost |
| --- | --- | --- | --- | --- | --- |
| 10795478 | baseline | passed | 29 | 65 | $6.6 |
| 10775935 | skill | passed | 56 | 100 | $11.6 |
| 10729998 | skill | failed | 55 | - | $14.5 |
| 10712862 | skill | agent-timeout | 60 | - | - |
| 10798373 | skill | killed by monitor | 19 | - | - |
| 10795694 | skill | killed by monitor | 24 | - | - |

The skill arm is about twice as slow and twice as expensive as baseline on
the simplest Maven project. `main` publishes no transcript (cause 6), so the
reason cannot be read from the artifacts. The eval-branch data from
2026-10-12 gives one known cause: the onboard skill requires two
"speed-up" runs after the first green one.

### 4. The monitor killed the agent on a fixable error

`LiveBuildMonitor` stops the agent when the head is red, all children are
green, and `problemEvidence` is `unavailable`. The data came from
`run view --json`, which never contains `problemOccurrences`. So the
evidence was always `unavailable`, and every "red head / green children"
chain killed the agent.

Real case: TeamCity records an `invalid_branch_name` problem ("triggered in
the branch development which does not correspond to any branch monitored").
Both skills describe the fix. The agent never got the chance: 4 of the last
7 skill runs ended as `verification-unexplained-head-failure` with exit code
-15 (2 of 5 on `main`, 2 of 2 on its PR branch). The baseline arm passed
the same day. This skews the comparison against the skill.

Fixed on `main` in `a7cf324` (2026-11-04): the monitor reads
`run log <head> --failed --json` and treats a non-empty `problems` list as
recorded evidence; the skills explain the `<default>` branch selector.

### 5. The compatibility check could not work

- `evals/bootstrap-teamcity-cli.sh` on `main` installed
  `@jetbrains/teamcity-cli@1.3.0` from npm. The npm package ends at 1.3.0.
  Queued-run compatibility in `run view` shipped in 1.6.0
  ([teamcity-cli#435](https://github.com/JetBrains/teamcity-cli/pull/435)).
- The onboard and first-green-build skills told the agent to run
  `teamcity agent jobs <agent-id> --incompatible --json` for every agent. On
  teamcity-nightly that is 9 887 build types and 5 MB per agent, with more
  than 800 agents. The job in question is one line among them.
- Verified on teamcity-nightly (2027.1 EAP) with CLI 1.6.3:
  `teamcity run view <queued-id>` prints the wait reason, compatible
  resources, and incompatible resources grouped by pool with unique reasons;
  `--json` holds every entry under `compatibility`. The eval CLI bridge
  allows `run view`.
- No CLI command and no REST call reports compatibility for a job that is
  not queued yet. Before queueing, the only check is to compare requirement
  keys with the observed agents. The real verdict is the first poll of the
  queued job.
- The bridge blocks `teamcity api`. The onboard skill reads JDK parameters
  from `/app/rest/agentTypes/id:<typeId>` through it, and
  `agent view --json` has no parameters. In the eval, JDK selection is a
  guess.

Fixed in this branch: native CLI 1.6.3 with checksum verification (ported
from the eval branch); both skills use `run view <queued-job-run-id>` and no
longer call `agent jobs --incompatible`.

### 6. Observability gaps

- `main` publishes only `eval-result.json`. The eval branch also publishes
  `claude/session.jsonl`. Without it, no run on `main` can be broken down by
  tool call.
- Runs before harness revision `9b9ca476` have no `phaseTimings` or
  `errorCategory` (9435245, 9428151).
- A bridge socket reset (9428151) left the usage counter at 354 output
  tokens for a $9 run.
- `EVAL_AGENT_MAX_BUDGET_USD` is not set on the pipeline. Nothing caps the
  cost of a single run.

## Done

| Change | Where |
| --- | --- |
| Monitor reads build problems from `run log --failed --json` before stopping the agent; test added | `main`, commit `a7cf324` |
| CLI pin 1.3.0 → 1.6.3, native release archive with SHA-256 verification | this branch, `evals/bootstrap-teamcity-cli.sh` |
| Compatibility via `run view <queued-job-run-id>`; configuration-only work compares requirements with the inventory locally | this branch, `skills/teamcity-onboard` 0.5.1, `skills/teamcity-first-green-build` 2.0.4 |

Not yet verified with a live eval run. Next step: one skill/baseline pair on
clean-spring-boot-maven from this branch. CLI 1.7.0 is out; the pin can move
once the bridge allowlist is checked against it.

## Open for the team

1. **Token expiry.** Ask the Claude build feature owners for a token that
   outlives the agent timeout, or for token refresh. Until then, set
   `EVAL_AGENT_TIMEOUT` below 3600 s (for example 3300 s) so the run ends as
   `agent-timeout` with a clear cause. Add a classifier for the synthetic
   `authentication_failed` event so the report separates
   `agent-token-expired` from skill errors.
2. **Waiting after the agent.** Give each case an expected build duration
   and wait no longer than that plus a margin after the agent exits. Lower
   `EVAL_QUEUE_STALL_TIMEOUT` to 300 s. A build the agent did not finish is
   not a pass.
3. **Transcripts on `main`.** Port session-log publishing from the eval
   branch (`run_case.py`, about 150 lines). Every "why so long" question
   needs them.
4. **Skill speed.** With transcripts, measure the clean-spring-boot-maven
   skill arm by tool call. Candidates: 100 CLI calls, polling frequency,
   the "speed-up" runs after green, re-reading references. Target: the skill
   arm is no slower than baseline on a single-module Maven project.
5. **Cost cap.** Set `EVAL_AGENT_MAX_BUDGET_USD` on the pipeline. The
   runner already supports it.
6. **Bridge and `teamcity api`.** Allow read-only `api` GET on
   `/app/rest/agentTypes/...`, or add a CLI command that prints agent-type
   parameters. Otherwise JDK selection in the skills cannot be evaluated.
7. **Compatibility before queueing.** Request a CLI command for the
   compatibility of a saved pipeline's job before it is queued. Until then
   the check is the first queued job; the skills now say so.
8. **Bridge reliability.** A client-side socket reset must not corrupt the
   usage counters (9428151).
