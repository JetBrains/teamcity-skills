# TeamCitySkills Evaluation Cases Proposal

## Purpose

Store versioned, machine-readable evaluation cases for TeamCity skills in this
repository. A case defines stable inputs and observable success criteria.

## Repository Layout

```text
evals/
  schema.json
  validate.py
  run_case.py
  compare_arms.py
  requirements.txt
  first-green-build/
    cases/
      spring-petclinic-maven-yaml.json
  pipeline-configuration/
    cases/
      cmp-unit-converter-targets.json
      ...
  queue-stall-diagnosis/
    cases/
      queued-no-compatible-agent.json
  teamcity-access-preflight/
    cases/
      teamcity-mcp-access-permissions.json
```

### Measuring The Skill's Effect

`EVAL_ARM=baseline` withholds the skill and changes nothing else, so the
difference between the two arms is the skill's contribution.
`evals/compare_arms.py` reports it per assertion, because a single verdict
hides it: two runs can both be `failed` while the skill fixes three checks out
of six.

All cases validate against `evals/schema.json`. Its `kind` field selects the
strict contract for the case type while shared fields, including the pinned
repository revision and user prompt, are defined once.

Cases are JSON files. At runtime, the evaluation runner authenticates to the
target TeamCity environment through its configured credential flow. It may
start with an authenticated client or obtain a short-lived token. Cases must
not contain or assume OAuth sessions, OAuth tokens, other credentials, or
personal staging URLs. The runner supplies the server URL, target project, and
cleanup scope.

### Prompt Placeholders

`teamcity.server` and `teamcity.targetProject` are the sentinel value
`runner-configured`: the case states that the environment is supplied from
outside, and never pins a concrete server URL or project ID.

The skill requires the assistant to obtain the exact TeamCity server and parent
project from the user's own request, and forbids inferring them from
environment variables, command history, or repository files. A case prompt must
therefore carry both values. Every `first-green-build` prompt contains the
placeholders `{{teamcity.server}}` and `{{teamcity.targetProject}}`, which the
runner substitutes with the provisioned environment before invoking the agent;
`evals/schema.json` rejects a `first-green-build` case whose prompt omits
either one.

A case that deliberately withholds the server or the parent project, in order
to assert that the assistant stops and asks for them, is a separate case kind
and is not covered by this contract.

## Case Types

### Current Evaluation Cases

The suite currently contains 10 contracts over 6 unique repositories: 2
first-green builds, 6 configuration-only evaluations, 1 deterministic queue
stall diagnosis, and 1 TeamCity access preflight. Configuration-only and queue
diagnosis cases are the default expansion path because they exercise Claude
without compiling the target project.

| Case | What it verifies |
| --- | --- |
| `spring-petclinic-maven-yaml` | A Java 17 Spring Boot/Maven repository can receive a valid TeamCity YAML pipeline, execute Maven verification, import JUnit XML, publish its JAR, and finish its first verification build successfully. |
| `kotlinconf-app-compose-multiplatform` | A Compose Multiplatform application must build its desktop, Android, iOS simulator, web, and backend targets, report every applicable test target, and publish each distributable artifact without silently changing the source toolchain. |
| `cmp-unit-converter-targets` | A Compose Multiplatform pipeline keeps Android, iOS, and desktop work separate, publishes an APK, and assigns iOS to a macOS environment without building the repository during evaluation. |
| `teamcity-cli-not-curl` | The agent uses an authenticated first-class TeamCity tool path rather than raw REST through `curl` or `wget`. |
| `queued-no-compatible-agent` | Once a run has already been queued for over two minutes, the agent checks inventory, job incompatibility reasons, and unresolved stored-pipeline parameters by its second status observation, then stops instead of polling or requeueing. The runner simulates the queue and consumes no target build agent. |
| `spring-petclinic-maven-pipeline` | The configuration-only Spring Petclinic case uses its documented Maven verification path and publishes the JAR. |
| `clean-spring-boot-maven-pipeline` | A Maven-only Spring Boot project receives a Maven verification job and JAR publication contract; a later first-green case must prove Java 21. |
| `kmm-basic-sample-mobile-targets` | JetBrains' official basic KMP sample gets distinct shared-test, Android, and macOS/iOS jobs with APK and simulator-app artifacts. |
| `jetcaster-kmp-multi-targets` | Jetcaster preserves seven independent test, Android, iOS, desktop-platform, and Wasm jobs with platform-specific agents and artifacts. |
| `teamcity-mcp-access-permissions` | The evaluation environment is authenticated and exposes the TeamCity operations needed for first-green-build setup. It classifies an actual `401`/`403` authorization failure separately from an operation that the selected TeamCity tool surface does not provide. |

The cases define expected behavior, not stored results. A case can therefore be
committed before it passes; each execution publishes only its minimal verdict.
Private execution traces and created object IDs remain in the runner's
disposable workspace.

### Gating Status

A case that is committed before it passes must say so, otherwise a permanently
red check trains reviewers to ignore the suite.

- `status: "active"` — the case is expected to pass. A failure is a regression
  and blocks the merge.
- `status: "aspirational"` — the case states a contract the current baseline
  does not meet. The runner executes it and reports the result, but must not
  gate on it.

The label is not left to the author's memory. When a case carries a
`observedBaseline`, `evals/validate.py` compares that baseline against `expected`
and requires `aspirational` whenever the baseline falls short, and `active`
whenever it does not. `kotlinconf-app-compose-multiplatform` is currently the
only aspirational case.

### Source Fidelity

`expected.sourceMutations` states whether the agent may edit the checked-out
sources to reach a green build:

- `none` — the disposable checkout must hold no change after the run, apart
  from the TeamCity configuration at `requestedConfiguration.sourcePath`, which
  the agent is expected to create. The runner verifies this with `git diff` on
  the checkout, not by reading the build log.
- `allowed` — the case tolerates source edits and must say in its
  `observedBaseline.limitations` which ones the baseline needed.

Without this assertion a green build is not evidence of a working pipeline: an
agent that lowers `compileSdk` until the build passes produces the same
`SUCCESS` as one that configures the correct toolchain. Every current
first-green-build case requires `none`.

### First Green Build

The case fixes the repository URL and commit SHA, the request, expected
configuration format, required pipeline step properties, verification command,
test report paths, artifact paths, required test services, and observable
completion contract.

The runner must not treat a green checkout-only job as a pass. A passing run
requires all of the following:

- server-side validation of the generated pipeline YAML;
- a successful verification build;
- at least one reported test when the case expects tests;
- every declared artifact path present in the build artifacts.

`stack.declaredJdk` exists for a repository whose declared JDK differs from
the one a run is known to work on. The Spring Boot/Gradle case used it while
its recorded baseline was JDK 21 against a declared 25. The first executed run
settled the question: the agent pointed `JAVA_HOME` at the agent's JDK 25 and
reached a green build with a passing test, so the case now expects 25 and the
field is gone. A case should carry `declaredJdk` only while a real discrepancy
is still unresolved.

`expected.toolchain.jdk` is checked against the properties the build actually
ran with, matching the version against every JDK- or Java-named property. A
build that evidences no JDK at all fails the check and reports what was
searched, so a probe that stops working shows up instead of quietly passing.

### Target-Level Expectations And Observed Baseline

`expected.targets` adds target-level completion criteria to a first-green-build
case. A runner must check the named target's status, required artifact paths,
and whether its tests must be imported into TeamCity. `not-applicable` is
reserved for targets that do not have a test action; it must not be used to
hide an unreported test task.

`verification.command` remains the primary verification command for simple
repositories. `verification.commands` lists the target-specific commands when
one command cannot represent a multi-platform pipeline, such as an iOS
`xcodebuild` action alongside Gradle targets.

`expected` is the reference value: the contract a run must meet, and the only
thing a verdict is decided against. `observedBaseline` is the opposite kind of
statement — what a reference run was actually seen to produce, shortfalls
included. The two are never interchangeable, and a baseline never softens the
contract. The field was called `groundTruth`, which promised the reverse: in
common usage ground truth *is* the criterion of correctness, while this field
is explicitly subordinate to `expected`.

`observedBaseline` records a verified baseline without retaining a staging URL,
temporary TeamCity object ID, user identity, or credentials. It makes the
observed build quality reviewable alongside the desired contract. The
KotlinConf App baseline is successful across all six targets, but is only a
partial-quality result: its three test-producing jobs imported zero test
occurrences, its desktop release job published no distributable, and its
Android job used an API 36 build-time compatibility shim because the available
image lacked API 37. A future run satisfies the case only when it meets the
`expected` contract; the baseline does not lower that bar. Because that
baseline does not yet clear the bar, the case is marked
`status: "aspirational"` and does not gate merges.

### Pipeline Configuration

This kind grades the pipeline the agent produced and never runs a build. It
answers what the agent knows about TeamCity - step types, topology, artifact
rules, agent requirements - in minutes, without a build agent, and without the
failure modes of a real build. A green-build case costs tens of minutes and
cloud-agent provisioning, so it cannot cover many repositories; this one can.

`stack.jdk` remains useful input metadata for a configuration-only case, but it
is not runtime evidence. Only a first-green case checks TeamCity's resulting
build properties and can prove that the requested JDK actually executed the
build.

The runner reads the build configurations the agent created, skipping the
composite pipeline heads a pipeline materialises per chain, and checks:

| Assertion | Question |
| --- | --- |
| `minimumJobs` | Did independent targets get a job each, or one job that builds everything? |
| `requiredStepTypes` | Was the dedicated runner used where the skill requires one? |
| `requiredStepProperties` | Do the steps carry the properties the server's schema needs, with the values the case demands? |
| `requiredArtifactRules` | Is anything published at all, and the right thing? |
| `requiredAgentRequirements` | Does an iOS job name a macOS agent, rather than a generic requirement? |
| `sourceMutations` | Were the sources left alone? |

`verification` is meaningless here and the schema rejects it: no command runs.

#### Which Tool The Agent Reaches For

`expected.toolUse` asserts on the calls the Claude agent actually made, read
from its structured stream trace rather than from its prose summary: an agent
can use a tool without mentioning it, or mention one it never called. A call is
recorded as `<tool> <arguments as JSON>`, for example
`Bash {"command": "teamcity pipeline validate ..."}`.

The first case of this shape is `teamcity-cli-not-curl`. A baseline run
observed on 2026-09-03 reached for the REST API over `curl`, did not use the
installed `teamcity` CLI, and stalled on credentials it could not read from the
environment - while the CLI would have picked them up by itself. Knowing to
drive TeamCity through its CLI is a concrete thing the skill supplies.

Such a case only means something when the forbidden tools are actually
available, which is why `agentTools` belongs to the case: asserting that an
agent did not use `curl` proves nothing when its tool policy blocked `curl` for
everyone. This case therefore grants plain `Bash`, and the pipeline checks that
`curl`, `wget`, and the `teamcity` CLI are present before the case starts.
Reaching for `curl` is therefore a choice rather than an impossibility.

### Queue Stall Diagnosis

This kind runs Claude against a deterministic TeamCity CLI fixture. The fixture
reports that run `73142` has already been queued for 130 seconds, that two
enabled agents exist, and that both reject the job because the server-stored
Pipeline references an unresolved JDK parameter. It creates no TeamCity object
and starts no target build.

The grader requires the agent to inspect agent inventory, per-agent incompatible
job reasons, and the stored Pipeline parameters. Compatibility diagnosis must
begin by the second run/queue status observation; no more than two status checks
and one additional bounded wait are allowed. Starting or restarting a run and
an unbounded watch fail the case. The final answer must classify both the lack
of a compatible agent and the unresolved parameter.

### TeamCity Access Preflight

This case checks that the runner has the read and write operations needed by a
first-green-build evaluation: VCS root and pipeline lifecycle, validation, and
personal-build queueing. It distinguishes:

- `authorizationDenied`: an actual 401 or 403 response;
- `capabilityMissing`: a required operation is not exposed by the selected
  TeamCity tool surface.

This distinction prevents a read-only MCP connector from being reported as an
OAuth permission failure.

## Running Evaluations

The `validate` job in the server-stored TeamCity `validate-eval-cases` pipeline
is the single continuous gate for a change to a skill, schema, or case. Its VCS
and pull-request trigger policy belongs to the hosting TeamCity project, rather
than to a second CI system. The job runs `evals/validate.py`, which:

1. validates every case against `evals/schema.json`, which also enforces that
   every repository revision is a full pinned commit SHA and that required
   commands, report paths, and artifact paths are present;
2. checks the conventions that JSON Schema cannot state: file name matches
   `id`, the case lives under the directory named by its `kind`, `id` values
   are unique, `observedBaseline.targets` and `expected.targets` describe the same
   targets, per-target artifact paths are covered by
   `verification.artifactPaths`, `status` agrees with what the recorded
   `observedBaseline` achieved, and no case pins a concrete server.

`evals/validate.py` declares its own dependency inline (PEP 723), so it needs
no setup on a machine that has `uv` or `pipx`:

```bash
uv run evals/validate.py
```

```bash
pipx run evals/validate.py
```

With neither, use a virtualenv. A Homebrew or system Python refuses a direct
`pip install` (PEP 668):

```bash
python3 -m venv .venv && .venv/bin/pip install --requirement evals/requirements.txt
.venv/bin/python evals/validate.py
```

`evals/requirements.txt` pins the same dependency for CI.

On demand, by label, or on a schedule:

1. provision an isolated TeamCity project selected by the runner;
2. run Claude, supplied and authenticated by the JCP Central AI Agent build
   feature, with the target environment's authenticated TeamCity client;
3. create or update the temporary VCS root and pipeline;
4. run `teamcity pipeline validate` against the active server before queueing;
5. queue a personal build, inspect test occurrences and artifact metadata, and
   evaluate the assertions;
6. publish only the minimal result JSON as a CI artifact;
7. delete temporary TeamCity objects.

A failing `active` case fails the run. A failing `aspirational` case is
reported and does not.

Do not commit runtime results, traces, OAuth tokens or sessions, credentials,
or temporary TeamCity IDs to this repository.

### Reporting Runs

`evals/collect_teamcity_eval_runs.py` creates a normalized, credential-free
snapshot of recent agent runs from the two executable evaluation pipelines. It
uses only the already authenticated `teamcity` CLI, downloads only
`publish/eval-result.json`, and reduces known runner problems to fixed
categories. In particular it keeps skill-output failures apart from agent
permission, JCP injection, VCS, and container-runtime failures. It never
includes an agent trajectory, prompt, raw build log, temporary project ID, or
trace path in the JSON report.

```bash
python3 evals/collect_teamcity_eval_runs.py \
  --server https://<teamcity-server> \
  --output /tmp/teamcity-eval-runs.json
python3 evals/render_teamcity_eval_report.py \
  --input /tmp/teamcity-eval-runs.json \
  --output /tmp/teamcity-eval-runs.html
```

The rendered report shows every contract as a row and keeps the latest `skill`
and `baseline` observations in separate columns. The access preflight contract
is shown separately as non-arm-based until it has an executable runner. The
execution ledger includes each evaluator build ID once and excludes validation,
self-check, and report jobs. The default collection window is 32 pipeline heads
per evaluation pipeline so completed observations do not disappear as soon as
several paired cases and retries have run; set `EVAL_REPORT_LIMIT` explicitly
when a different retention window is needed.

`evals/run-eval-report.sh` is the cross-platform wrapper for that job. It
bootstraps the TeamCity CLI when needed, detects Python on Linux/macOS/Windows,
and excludes its own job from the collected totals.

Run that wrapper as a `Publish evaluation report` job in each server-stored
evaluation pipeline. In the two on-demand pipelines it depends on the case job
with `run-job-if-upstream-fails: true`, so a failed grading run is still
recorded. In `validate-eval-cases` it is independent of the validation jobs for
the same reason. Publish `.teamcity/evaluation-report/**` as artifacts. TeamCity
places that job's artifact files below `publish/`, so add a project Report Tab
whose start page is `publish/index.html`. Each new eval pipeline head then
refreshes the report; result files stay outside version control.

## Result Contract

The runner publishes one JSON object per execution, for example:

```json
{
  "caseId": "spring-petclinic-maven-yaml",
  "caseStatus": "active",
  "status": "passed",
  "configuration": {
    "format": "yaml",
    "validationMethod": "teamcity pipeline validate",
    "valid": true
  },
  "build": {
    "status": "SUCCESS",
    "testsReported": true,
    "artifactsPublished": true,
    "sourceMutations": []
  },
  "checks": {
    "firstBuild": { "passed": true }
  }
}
```

## The Runner

`evals/run_case.py` executes `first-green-build`, `pipeline-configuration`, and
`queue-stall-diagnosis` cases. It is standard library only and takes its whole
environment from outside the case:

| Variable | Meaning |
| --- | --- |
| `TEAMCITY_URL` | server to evaluate against |
| `TEAMCITY_TOKEN` | access token for that server |
| `EVAL_PARENT_PROJECT` | parent project that holds temporary eval projects |
| `EVAL_PIPELINES` | comma-separated head build configuration IDs collected by the report job |
| `EVAL_AGENT_CMD` | optional base command for the agent; by default `claude -p`, with `--output-format stream-json --verbose` added by the runner and the prompt arriving on stdin in the checkout |
| `EVAL_BUILD_TIMEOUT`, `EVAL_AGENT_TIMEOUT` | seconds, both default to 3600 |

`EVAL_AGENT_TIMEOUT` limits the `claude -p` process, not the TeamCity build
that Claude creates. If Claude exceeds that budget, the runner stops it,
records `agent-timeout`, uses `EVAL_FAILED_AGENT_GRACE` to inspect any build
already queued in TeamCity, and publishes the resulting checks. A timeout is
still an evaluation failure even when those checks pass: the output remains
visible, but an agent that did not finish within its budget cannot become a
false green.

Claude's authentication is not an environment parameter in this repository.
For each of the two on-demand eval build configurations, add the **JCP Central
AI Agent** build feature in TeamCity, select **Claude Code**, and select the
project's JCP Central connection. The feature makes `claude` available and
injects a short-lived credential at build time. It does not require
`ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `CODEX_API_KEY`, or
`CODEX_HOME` in the YAML, repository, or TeamCity parameters.

For the evaluation project on each installation, configure the normal runner
parameters in TeamCity: `env.TEAMCITY_URL` for that server, and
`env.TEAMCITY_TOKEN` as a
TeamCity **Password** (secure) parameter for temporary-project lifecycle
operations. Do not create it as a plain environment parameter: TeamCity can
include plain parameter values in container-wrapper logs. Use protected UI
input or the CLI's `--secure` option without placing the token in shell history.
Also set
`env.EVAL_PARENT_PROJECT=<temporary-evals-parent-project-id>`. The latter is
deployment configuration, not a case value, so the same cases remain portable
between installations. Set `env.EVAL_PIPELINES` to the comma-separated head
build configuration IDs for the two evaluation pipelines before running the
report job.

One execution:

1. creates the temporary project `eval-<caseId>-<timestamp>-<random>`;
2. checks the repository out on its declared default branch at the pinned
   revision and verifies `HEAD` actually equals it. This exposes the real
   branch name to the agent, so it can configure a VCS root that monitors the
   branch it will build;
3. substitutes `{{teamcity.server}}` and `{{teamcity.targetProject}}` into the
   prompt and invokes the agent inside the checkout;
4. waits for the build the agent queued in that project;
5. grades it: a build configuration exists, the build reached the expected
   status, TeamCity imported at least one test occurrence, every expected
   artifact path matched a published artifact, and `git status` in the checkout
   is clean apart from the TeamCity configuration the agent was asked to
   create;
6. preserves the temporary project while the current staging server's project
   deletion is under investigation, and removes the disposable checkout.

For `queue-stall-diagnosis`, steps that create a TeamCity project or wait for a
build are replaced by the deterministic CLI fixture described above. This keeps
the skill/baseline comparison reproducible and prevents the eval itself from
occupying a scarce compatible agent.

A build that TeamCity marks failed because its requested branch is not
monitored is never a first-green success, even if tests passed. In that state
TeamCity may have substituted a default revision. The skill must repair the
VCS root branch specification and rerun on a monitored branch.

The runner records the retained project ID and sets `cleanupDeferred: true` in
its result. This temporary infrastructure workaround is not a user-build
requirement and does not affect grading.

A failing `active` case exits non-zero. A failing `aspirational` case is
reported and exits zero. `--dry-run` resolves the case without touching the
server; `--keep` leaves the project and checkout in place for debugging.

Refresh the evaluation report after the case job reaches a terminal state and
publishes `eval-result.json`. The dependent `Publish evaluation report` job
does this automatically even when grading fails. While Claude is still
running there is no final grade to publish; monitoring should state that it is
waiting for the agent timeout or terminal result and what action follows.

Expected artifact paths are source-tree paths, while TeamCity stores whatever
the artifact rules produced. The runner therefore accepts a full-path match, a
trailing-subpath match, or a basename match, and records the full published
list so a reviewer can judge a loose match.

### Build Configurations

The TCEvals pipelines are server-stored YAML: `validate-eval-cases` is the
continuous static gate; `run-eval-case` and `run-configuration-eval` run a
selected case on demand. The checked-in `.teamcity.yml` and `.teamcity/*.yml`
files are their reviewable desired definitions, not an automatic source of
truth. Pull the server definition to a scratch file, validate it against that
server, and push the corresponding checked-in file explicitly after a review.
Configure VCS and pull-request triggers on the hosting TeamCity project; the
YAML files do not name a server.
The URL and TeamCity access token are project parameters on whichever TeamCity
installation hosts them. Claude's own authentication comes only from the JCP
Central AI Agent build feature configured in the TeamCity UI.

The server-side `validate-eval-cases` definition is `.teamcity.yml`. It has
separate schema, grader self-check, and report jobs. All three select a
self-hosted Linux agent by durable OS capability so an unrestricted
`self-hosted` match cannot schedule the bootstrap scripts on unsupported
legacy Windows images.

Two operational facts, both learned the hard way:

- `teamcity pipeline create` uploads a snapshot of the YAML. Later commits do
  **not** reach the server, so a change to either file needs an explicit
  `teamcity pipeline push <pipeline-id> <file>`. Scripts under `evals/` are
  repository content and do arrive with the checkout, which makes the
  discrepancy easy to miss: the Python changes take effect while the pipeline
  step stays on the old version.
- The JCP Central AI Agent build feature installs or finds `claude`; do not
  install Claude Code in the job script. It makes Claude available on the
  TeamCity **host agent**, not inside a `docker-image` step. The two agent-eval
  jobs run on any `self-hosted` agent: their script calls a POSIX runner
  directly on Linux/macOS and via Git Bash on Windows. Before invoking the
  runner, it bootstraps the TeamCity CLI in an isolated temporary directory
  when the selected agent lacks npm. The generated KMP pipeline still needs a
  macOS job where its iOS target requires it.

Claude is invoked as `claude -p --output-format stream-json --verbose`. The
JCP Central feature supplies the short-lived agent credential and can write
telemetry under `.teamcity/jcp-central/`. Treat those files as private build
data and keep their artifact access restricted. The runner separately needs the
scoped `TEAMCITY_TOKEN` described above to create its temporary TeamCity
projects; the standard wrapper passes it through a one-use descriptor and
removes it before the agent starts.

Claude's non-interactive permission policy remains in force. A configuration-
only case can use a narrow `agentTools` allowlist, for example
`["Bash(teamcity:*)", "Write"]`. A first-green-build case also needs local
inspection and build commands such as `git`, `./gradlew`, or `./mvnw`; a
compound `cd … && command` is not covered reliably by command-specific Bash
rules. The current first-green cases therefore explicitly declare
`["Bash", "Read", "Write", "Edit", "Glob", "Grep"]`.

This permission is part of the case input and is identical in skill and
baseline arms. It is not a global bypass: run such cases only in the isolated
evaluation project, with a scoped TeamCity lifecycle token and a pinned,
reviewed repository revision. A case that tests tool choice, such as
`teamcity-cli-not-curl`, must keep the narrower policy it is intended to
measure.

## Ownership Boundary

`TeamCitySkills` owns case definitions, schemas, expected assertions, and
lightweight validation. The evaluation runner owns private staging credentials,
agent invocation, TeamCity lifecycle, build execution, cleanup, and disposable
traces; it publishes only minimized verdicts. This keeps cases reviewable and
prevents infrastructure secrets from entering the skills repository or build
artifacts.

## Suggested list of projects to test
| Repository | Stack | Evaluation focus |
| --- | --- | --- |
| [spring-projects/spring-petclinic](https://github.com/spring-projects/spring-petclinic) | Spring Boot 4, Maven, Java 17, H2 by default with optional PostgreSQL | Maven verification, JDK 17, and JAR publication |
| [kawser2133/clean-spring-boot-project](https://github.com/kawser2133/clean-spring-boot-project) | Spring Boot, Maven, Java 21, JPA, Security, Mail, Actuator | Maven and JDK 21 setup |
| [unildhiman90/RecipeApp-KMP-Compose-Multiplatform](https://github.com/unildhiman90/RecipeApp-KMP-Compose-Multiplatform) | Compose Multiplatform, Android and iOS | Gradle setup; macOS agent requirement for iOS |
| [tkuenneth/CMP-Unit-Converter](https://github.com/tkuenneth/CMP-Unit-Converter) | Compose Multiplatform, Android, iOS, desktop, Java 17, KSP | Android, iOS, and desktop target selection |
| [inassar0/kotlin-multiplatform-template](https://github.com/inassar0/kotlin-multiplatform-template) | Kotlin Multiplatform template, Android, iOS, desktop, Java 17 | Baseline for generated YAML and Kotlin DSL |
| [KaushalVasava/XPhotogram_KMP](https://github.com/KaushalVasava/XPhotogram_KMP) | Kotlin Multiplatform app, Android, iOS simulator, desktop, Java 17 | Multi-target Gradle pipeline generation |
| [chouaibMo/Snake-Compose-Multiplatform](https://github.com/chouaibMo/Snake-Compose-Multiplatform) | Compose Multiplatform, Android, iOS, Java 11 | Older toolchain compatibility |
| [shengyou/kotlin-multiplatform-with-compose-demo](https://github.com/shengyou/kotlin-multiplatform-with-compose-demo) | Kotlin Multiplatform, Android, iOS, desktop, Kotlin/JVM server, Java 17 | Multi-module topology combining mobile and server targets |
