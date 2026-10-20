---
name: teamcity-onboard
version: 0.1.0
description: Use when onboarding a project to TeamCity with an authenticated `teamcity` CLI and a checked-out repository. Gets the repository to its first basic green build with native runners, parallel tests, and a live build status, runs it remotely until green, and offers follow-ups.
---

# TeamCity Onboard

Get a new TeamCity user from the hand-over to the first basic green build,
fast. The green build is the goal. Everything else is secondary. This is a
quick start:

- a basic build. What "basic" means depends on the stack. A good one
  compiles, runs the tests, and packages the output. None of the three is
  required;
- native runners in a chain of jobs;
- parallel tests and a live build status;
- a green run with a link to watch. Nothing is committed to the repository.

## Before the first command

Load the `teamcity-cli` skill. If it is not installed, run
`teamcity skill install`. It owns command syntax, output formats, failure
investigation, and the pipeline pull, validate, push loop. Use only the flags
it documents.

Read [Tool policy and secrets](references/teamcity-tool-policy.md). Where this
skill and the CLI skill differ, this skill wins:

- Use the `teamcity` CLI as the flow configured it.
- The repository sources stay unchanged. Nothing is written to or committed
  in the user's repository. The pipeline lives on the server. Your working
  YAML lives outside the checkout.
- Honest red. A failure caused by the project (a bug, lint, a flaky test) is
  reported with evidence. It is never hidden: no skipped or muted tests, no
  `|| true`, no disabled steps. A failure caused by the pipeline is fixed. A
  test subset planned before the first run, and declared, is not a skipped
  test.
- Poll runs with `run tree` and `run view`. `run watch` and `--watch` flood a
  non-interactive shell.
- Every pipeline you create is a deliverable. Probe and diagnostic pipelines
  are forbidden.
- No secret value is ever asked for or accepted.

## 1. Read the repository and the server

Read [Project inspection](references/project-inspection.md). Build files, the
README, and `.github/workflows/` show how the team builds. Design the basic
build from them: a chain of jobs when there is more than one.
Deploy, publish, release, and any job that needs a secret are follow-ups.

Read [Discover and connect](references/discover-and-connect.md). Confirm the
server. Find the VCS root and the branch.

## 2. Choose where it runs

Read [Agents and JDK](references/agents-and-jdk.md) before you write YAML.
Take `runs-on`, the JDK, and the CPU architecture from the agent type's
parameters. Always pin the JDK. Before you queue, check every job against the
candidate agents. Zero compatible candidates is a blocker to fix first.

## 3. Write the pipeline

Read [Build-step selection](references/build-step-selection.md) and
[Pipeline features](references/pipeline-features.md). Dedicated runners. A
script step only for glue and the `Status` step. Every test visible. Add the
dependency cache, test reports, artifacts, the `Status` step, and the report
tab. Parallel tests come after the first finished run. Keep the YAML file
outside the checkout. Validate it, check compatibility, and treat a push
error as the real validation.

## 4. Create the pipeline

`teamcity pipeline create` in `_Root` against the VCS root, as the CLI
skill's pipelines workflow shows. The root, the `--branch` value, and the
remote-run fallback come from
[Discover and connect](references/discover-and-connect.md).

## 5. Run it until green

Read [Verify a build](references/verify-build.md). Start the first run at
once, without asking. Announce every run as that guide says. Classify each
failure. Fix pipeline causes only. After every run, check each test job's
test count.

## 6. Improve with the evidence

After the first green run: add `parallelism` when the conditions in
[Pipeline features](references/pipeline-features.md) hold, and run twice more
to show the split. Give agent-size advice from the job's Performance Monitor
tab. Say why before each run.

## 7. Report and offer follow-ups

Read [Show the value](references/show-the-value.md). Lead with the green
run's `webUrl`. Then:

- the commands chosen and where they came from, with the reason for every
  script step;
- each test task per module and the job that runs it;
- each job with its runner type, and one line per TeamCity feature: what the
  user gets and where to look;
- the runs: ID, state, duration, number of test batches, measured speedup;
- each manual prerequisite, in the form
  [Manual prerequisites](references/manual-prerequisites.md) requires;
- the value summary: what ran, how many tests are visible, what TeamCity did
  that GitHub Actions did not, time saved;
- the next steps that apply: the full suite with parallel tests when a subset
  ran; registry integration when the project pushes images.
