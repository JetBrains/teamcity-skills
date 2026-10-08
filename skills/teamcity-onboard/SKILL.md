---
name: teamcity-onboard
version: 0.1.3
description: Use inside the TeamCity onboarding flow, after the web step created the instance and handed over its context. Reads a checked-out repository and its GitHub Actions workflow, recreates the build and test core as a TeamCity pipeline with native runners and parallel tests, and runs it until green.
---

# TeamCity Onboard

Show that is leaving GitHub Actions what the same build looks like on
TeamCity. Recreate only the core of one workflow, use native runners, turn on
parallel tests, and run the pipeline until it is green and the speedup is
visible. The web step before this skill created the instance and, when it
could, an authenticated VCS root. This skill is not a stand-alone setup tool.

## Inputs

Take these from the hand-over context. Do not ask for them and never take the
server from a saved CLI default:

- TeamCity server URL and the parent project ID. The parent is never `_Root`.
- The checked-out repository: its path, remote URL, and current branch.
- The VCS root ID, when the web step created one.

The CLI is already authenticated. Confirm the identity once with
`TEAMCITY_URL=<server> teamcity auth status`, then prefix every command with
the same `TEAMCITY_URL`. If a value is missing from the context, stop and report which
one the web step must provide.

## Rules

Read [TeamCity tool policy](references/teamcity-tool-policy.md) and
[Token safety](references/token-safety.md). Then:

- do not create connections, VCS roots, triggers, or pull-request handling;
- recreate only build and test jobs, never the whole workflow;
- prefer dedicated runners over script steps; and
- add dependency cache and parallel tests even when the workflow had none.

## 1. Read the repository

Read [Discover and connect](references/discover-and-connect.md) to confirm the
target, inspect the repository and the server, and find the VCS root. Then read
[Project inspection](references/project-inspection.md). Its GitHub Actions
section chooses the workflow: one workflow, use it; several, prefer the classic
build, test, and publish flow; otherwise propose the one that other workflows
depend on, runs most often, or suits TeamCity best. State the choice and the
reason in the report. A repository without workflows is supported but not the
priority: design from the build files and README alone.

From the chosen workflow keep only the jobs that build and test. Drop publish,
release, deploy, scan, and bot jobs, and list them in the report as not
migrated. Keep one matrix combination, Linux first.

## 2. Choose where it runs

A wrong `runs-on` is the most common way an onboarding freezes: the build
stays queued forever because no agent satisfies the requirement. Decide the
selector from this server's evidence before writing any YAML:

```bash
TEAMCITY_URL=<server> teamcity pipeline schema --refresh
TEAMCITY_URL=<server> teamcity agent list --connected --enabled --authorized \
  --limit 0 --json=id,name,typeId,pool.id,pool.name
```

- Use a hosted selector only when the schema lists it and TeamCity confirms a
  compatible image, or use a self-hosted capability observed on a connected
  agent. Never copy a selector from another server, a GitHub `ubuntu-latest`
  label, or a transient VM name.
- Do not add OS, JDK, Docker, or parameter requirements the workflow did not
  need. Each one shrinks the compatible agent set. `os-family` maps to
  `teamcity.agent.jvm.os.family`, which may be absent even on Linux agents.
  Use an explicit custom requirement for an observed agent parameter; a bare
  parameter name in `self-hosted` is not a custom requirement. Changing a
  value's case cannot make a missing parameter exist.
- An exact JDK is a `parameters.env.JAVA_HOME` value taken from an observed
  agent key such as `%env.JDK_21_0%`, never a guessed key. A referenced key
  that no agent advertises is an unmet requirement before dispatch, and no
  build step can download the JDK because the build never starts. On Linux,
  prefer a pinned JDK image through `docker-image` on the step when the
  server has Docker-capable agents.
- Keep one Linux job unless the repository needs macOS or Windows.

## 3. Write the pipeline

Read [Build-step selection](references/build-step-selection.md) for runner
choice, the Script Parameter Gate, and status messages.

Add these to every pipeline, whether or not the workflow had them:

- `enable-dependency-cache: true` on each job.
- `parallelism: <n>` on the job whose primary step runs the tests through a
  Gradle, Maven, or .NET runner. Start with 3. TeamCity splits the tests into
  that many batches once it has test history. Keep packaging out of that job,
  because every batch runs the whole job.
- For a test step that must stay a script, an `xml-report` job feature
  (`report-type: junit` and `rules:` for the report files) so the tests show
  in the TeamCity UI.
- `files-publication` for the packaged output: what the workflow uploaded,
  or the application JAR or package the build produces.

```yaml
jobs:
  test:
    name: Build and test
    runs-on: <a value from the schema enum, for example Linux-Medium>
    enable-dependency-cache: true
    parallelism: 3
    steps:
      - type: gradle
        name: Test
        tasks: test
```

Then read
[Validate and check compatibility](references/validate-and-check-compatibility.md)
and run its checks. Before queueing, pull the stored YAML and check the exact
job against every candidate agent or cloud image. An agent name, host
architecture, or successful YAML validation does not prove compatibility.
Zero compatible agents is a configuration defect to fix now, not something to
wait out.

## 4. Attach it to the repository

Use the VCS root found in [Discover and connect](references/discover-and-connect.md)
and create the pipeline:

```bash
TEAMCITY_URL=<server> teamcity pipeline create <repo>-pipeline \
  --project <parent-id> --vcs-root <vcs-root-id> --file .teamcity.yml
```

That guide also covers the branch to pass with `--branch`, the anonymous root
for a public repository, the manual prerequisite for a private one, and the
remote run when the checked-out commit is not pushed yet.

## 5. Run it until green, then show the speedup

Read [Verify a build](references/verify-build.md) to queue, watch, and correct
the first run. Keep going until the pipeline head and every job are green or a
blocker is proven.

A runnable job still queued after two observations or 120 seconds needs a
compatibility check. Inspect that job, not a pipeline head waiting for it, and
read its wait reason:

```bash
TEAMCITY_URL=<server> teamcity queue list --job <job-id> --json=id,waitReason,queuedDate
```

For **no compatible agents**, **no idle compatible agents**, or **unresolved
parameters**, follow "Diagnose A Build That Remains Queued" in
[Build diagnostics](references/build-diagnostics.md). Check every candidate's
exact incompatibility reason. Treat **no idle compatible agents** as busy
capacity only when at least one candidate is confirmed compatible. Make one
evidence-backed correction, validate, and only then queue again. Do not requeue
unchanged, add another requirement, or switch branches to hide the error.

Then run the pipeline two more times on the same revision. The first green run
gives TeamCity the test history; the later runs split the tests into
parallel batches. Compare them:

```bash
TEAMCITY_URL=<server> teamcity run list --job <job-id> \
  --json=id,status,startDate,finishDate
```

Report only what you observed. When the test job takes under a minute,
say that parallel tests will not help yet and keep `parallelism` small or
remove it.

## Report

Lead with the pipeline URL confirmed by `teamcity pipeline view <id> --web`.
Then:

- the workflow chosen and why, and the jobs that were not migrated;
- each job with its runner type and the features added;
- a table of the runs: ID, state, duration, and number of test batches;
- each manual prerequisite, in the form the shared guide requires.
