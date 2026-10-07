---
name: teamcity-onboard
version: 0.1.0
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

Read [Project inspection](references/project-inspection.md). Its GitHub Actions
section chooses the workflow: one workflow, use it; several, prefer the classic
build, test, and publish flow; otherwise propose the one that other workflows
depend on, runs most often, or suits TeamCity best. State the choice and the
reason in the report. A repository without workflows is supported but not the
priority: design from the build files and README alone.

From the chosen workflow keep only the jobs that build and test. Drop publish,
release, deploy, scan, and bot jobs, and list them in the report as not
migrated. Keep one matrix combination, Linux first.

## 2. Write the pipeline

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
    runs-on: <selector observed on this server>
    enable-dependency-cache: true
    parallelism: 3
    steps:
      - type: gradle
        name: Test
        tasks: test
```

Then read
[Validate and check compatibility](references/validate-and-check-compatibility.md)
for JDK selection, validation, `runs-on`, and the compatibility check.

## 3. Attach it to the repository

Use the VCS root from the hand-over context. Without one, list the roots in the
parent project and its ancestors and reuse the one that matches the repository
URL:

```bash
TEAMCITY_URL=<server> teamcity project vcs list --project <parent-id> --json
TEAMCITY_URL=<server> teamcity project vcs view <vcs-root-id>
TEAMCITY_URL=<server> teamcity pipeline create <repo>-pipeline \
  --project <parent-id> --vcs-root <vcs-root-id> --file .teamcity.yml
```

When no root exists for a public repository, create one with
`--auth anonymous` and continue. For a private repository without an
authorized root, the pipeline cannot read the sources: report it as a
[manual prerequisite](references/manual-prerequisites.md) naming the web step's
repository authorization. Do not create a token-based root.

When the root exists but the branch or the latest commit is not pushed, run a
remote run instead of waiting for a push:

```bash
TEAMCITY_URL=<server> teamcity run start <job-id> --branch <branch> \
  --local-changes=git --no-push --personal
```

## 4. Run it until green, then show the speedup

Read [Verify a build](references/verify-build.md) to queue, watch, and correct
the first run. Keep going until the pipeline head and every job are green or a
blocker is proven.

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
