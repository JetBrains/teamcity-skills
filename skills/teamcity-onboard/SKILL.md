---
name: teamcity-onboard
version: 0.1.0
description: Use inside the TeamCity onboarding flow, after the web step created the instance and handed over its context. Reads a checked-out repository and its GitHub Actions workflow, recreates the build and test core as a TeamCity pipeline with native runners and parallel tests, and runs it until green.
---

# TeamCity Onboard

Show a team leaving GitHub Actions what their build looks like on TeamCity:
one workflow's build and test core, native runners, parallel tests, and a
green pipeline with a visible speedup. The web step before this skill created
the instance and, when it could, an authenticated VCS root. This skill does
not work without that step.

## Load the CLI skill first

Every TeamCity operation goes through the `teamcity` CLI, and the
`teamcity-cli` skill owns how to use it. Invoke that skill before the first
TeamCity command: through the Skill tool when it is available, otherwise by
reading `../teamcity-cli/SKILL.md`. If it is not installed, run
`teamcity skill install`.

The CLI skill supplies command syntax and flags, output formats, how to start
and watch a run, failure investigation, build-chain debugging, and the
pipeline pull, validate, push loop. Do not guess a flag or re-derive a
workflow that it documents. This skill adds only the onboarding decisions and
these overrides, which win where the two differ:

- Prefix every command with `TEAMCITY_URL=<server>` from the hand-over
  context. Never use the saved default server, `teamcity auth login`, or
  `teamcity api`.
- Never edit repository sources, skip tests, or disable steps to get green.
  The "fix the code and verify with `--local-changes`" path of the CLI skill
  is out of scope here.
- Create no connections, triggers, or pull-request handling.

## Inputs and rules

The hand-over context supplies the server URL, the parent project ID, the
checked-out repository with its remote URL and branch, and the VCS root ID
when one exists. Never ask for these. If one is missing, stop and name it.
Confirm the authenticated identity once with `teamcity auth status`.

Read [Token safety](references/token-safety.md). Then:

- recreate only the build and test jobs of one workflow;
- use dedicated runners; a script step is for glue only; and
- add the dependency cache and parallel tests even if the workflow had none.

## 1. Read the repository

Read [Discover and connect](references/discover-and-connect.md): it confirms
the target, inspects the server, and finds the VCS root and the branch.

Read [Project inspection](references/project-inspection.md) and choose the
workflow by its rules: prefer the classic build, test, and publish flow; with
none, propose the one that others depend on or that suits TeamCity best.
Record the choice and the reason for the report. A repository without
workflows is supported: design from the build files and README.

Keep only the jobs that build and test, and one matrix combination, Linux
first. List everything dropped as not migrated.

## 2. Choose where it runs

A wrong `runs-on` is how an onboarding freezes: the build queues forever
because no agent matches. Decide the selector from the server before writing
YAML. `teamcity pipeline schema --refresh` gives the `runs-on` enum;
`teamcity agent list --connected --enabled --authorized` gives the agents
(see the CLI skill's agents workflow for the fields).

- Use a hosted selector from the schema's `runs-on` enum, or a capability
  observed on a connected agent. Never a GitHub label, a selector from another
  server, or a VM name.
- Add no OS, JDK, Docker, or parameter requirement the workflow did not need.
  Each one shrinks the set of compatible agents.
- Select an exact JDK through `parameters.env.JAVA_HOME` with a key an agent
  advertises, such as `%env.JDK_21_0%`. A key no agent has blocks dispatch,
  and no build step can install the JDK because the build never starts. On
  Linux, a pinned JDK `docker-image` on the step is the safer choice.
- Match the agents' CPU architecture to the images the build pulls, including
  Testcontainers images. An amd64-only image on an arm64 agent fails with
  `exec format error`.
- Count the compatible agents. Each parallel test batch needs one at the same
  time.

## 3. Write the pipeline

Read [Build-step selection](references/build-step-selection.md) for runner
choice, the Script Parameter Gate, and status messages. Then add:

- `enable-dependency-cache: true` on each job;
- `parallelism` on the test job, when its tests run through a Gradle, Maven,
  or .NET runner: 3, or the number of compatible agents if smaller, and none
  below 2. Keep packaging out of that job, because every batch runs it all;
- an `xml-report` job feature (`report-type: junit`, `rules:`) only when the
  test step has to stay a script; and
- `files-publication` for the packaged output, whether the workflow uploaded
  it or not.

```yaml
jobs:
  test:
    name: Build and test
    runs-on: Linux-Medium   # a value from this server's schema enum
    enable-dependency-cache: true
    parallelism: 3
    steps:
      - type: gradle
        name: Test
        tasks: test
```

Read [Validate and check compatibility](references/validate-and-check-compatibility.md)
and run its checks. Before queueing, ask TeamCity which agents reject the job
with `teamcity agent jobs <agent-id> --incompatible`. Zero compatible agents
is a defect to fix now, not to wait out.

## 4. Create the pipeline

Create it with `teamcity pipeline create` against the parent project and the
VCS root, as the CLI skill's pipelines workflow shows. The root, the
`--branch` value, and the remote-run fallback for an unpushed commit come from
[Discover and connect](references/discover-and-connect.md).

## 5. Run it until green

Read [Verify a build](references/verify-build.md). It uses the CLI skill's
run-and-watch and fix-and-verify workflows and adds the onboarding stop rules.
Keep going until the head and every job are green or a blocker is proven.

**Queued for 60–120 seconds** means blocked, not slow. Read the wait reason
with `teamcity queue list --job <job-id>`, then follow "Diagnose A Build That
Remains Queued" in [Build diagnostics](references/build-diagnostics.md): one
correction the evidence supports, validate, requeue. Never requeue unchanged,
add a requirement, or switch branches to hide an error. "No idle compatible
agents" with compatible agents confirmed and test batches queued means the
pipeline wants more agents than exist: lower `parallelism`, push, requeue.

**A red head with green jobs** and the problem `invalid_branch_name` is a
branch binding error. Fix the branch selection; do not touch the steps.

**A test that fails on its own**, with no TeamCity cause in the log, is a
repository failure. Report the test, the assertion, and the build ID, and
stop. A job that failed only through its snapshot dependency needs no
diagnosis.

## 6. Show the speedup

Run the pipeline two more times on the same revision. The first green run
gives TeamCity the test history; the later runs split the tests into
batches. Compare them with `teamcity run list --job <job-id>` and the
`startDate` and `finishDate` fields.

Report only what you observed. If the test job takes under a minute, say that
parallel tests do not pay off yet.

## Report

Lead with the pipeline URL from `teamcity pipeline view <id> --web`. Then:

- the workflow chosen and why, and the jobs not migrated;
- each job with its runner type and the features added;
- the runs: ID, state, duration, number of test batches;
- each manual prerequisite, in the form
  [Manual prerequisites](references/manual-prerequisites.md) requires.
