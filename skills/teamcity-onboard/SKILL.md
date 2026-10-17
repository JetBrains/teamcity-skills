---
name: teamcity-onboard
version: 0.1.0
description: Use when onboarding a project to TeamCity and the task hands over a server URL and a repository. Gets the repository to its first basic green build with native runners, parallel tests, and a live build status, runs it remotely until green, and offers follow-ups.
---

# TeamCity Onboard

Get a new TeamCity user from the hand-over to the first basic green build,
fast. That green build is the goal; everything else is secondary. This is a
quick start, not a migration:
- a basic build. What basic means depends on the stack. A good one
  compiles, runs the tests, and packages the output, but none of those is
  required;
- native runners in a chain of jobs;
- parallel tests and a live build status;
- a green run with a link to watch, and nothing committed to the repository.

## Before the first command

Load the `teamcity-cli` skill. If it is not installed,
run `teamcity skill install`. The CLI skill owns command syntax, output
formats, run and watch, failure investigation, and the pipeline pull,
validate, push loop. Use only the flags it documents.

Read [TeamCity tool policy](references/teamcity-tool-policy.md) and
[Token safety](references/token-safety.md). Where this skill and the CLI
skill differ, this skill wins:

- Every command carries `TEAMCITY_URL=<server>` from the hand-over context.
  A saved default server and `teamcity auth login` are forbidden.
- The repository sources stay unchanged. Skipped tests and disabled steps
  are not a way to get green.
- Every pipeline you create is a deliverable. Probe and diagnostic pipelines
  are forbidden, even when build logs are unreadable.
- Nothing is written to or committed in the user's repository. The pipeline
  lives on the server; your working YAML lives outside the checkout.
- No secret value is ever asked for or accepted. See
  [Token safety](references/token-safety.md).

The hand-over context supplies:

- the server URL. Without it, stop and name it;
- the parent project ID. Without it, work in `_Root`;
- the checked-out repository with its remote URL and branch. Without it,
  use the repository this skill runs in: `git remote get-url origin` and
  `git branch --show-current`;
- the VCS root ID, when one exists.

Never ask for these.

## 1. Read the repository

Read [Discover and connect](references/discover-and-connect.md). Confirm the
target, inspect the server, and find the VCS root and the branch.

Read [Project inspection](references/project-inspection.md). Read the build
files, the README, and `.github/workflows/` as signals of how the team
builds. Design the basic build from them. A good one compiles, runs the
tests, and packages the output; include whichever of those the project has,
as a chain of jobs when there is more than one. One matrix combination,
Linux first. Deploy, publish, release, and any job that needs a secret are
follow-ups, not part of the first build.

## 2. Choose where it runs

Read [Agents, JDK, and compatibility](references/agents-and-jdk.md) before
you write any YAML. Decide `runs-on`, the JDK, and the CPU architecture from
the server's own evidence. Start from the least restrictive selector. Add a
requirement only after a build proved its absence.

Before queueing, check the stored pipeline's exact jobs against every
candidate agent and cloud image. Zero compatible candidates is a
configuration blocker. Correct the requirement and check again before you
run.

## 3. Write the pipeline

Read [Build-step selection](references/build-step-selection.md). Pick
dedicated runners. A script step is for glue and for the status step.

Read [Pipeline features](references/pipeline-features.md). Add the dependency
cache, test reports, artifacts, a status step, and a report tab when the
schema has one. Parallel tests come after the first green run, when the
suite is long enough. Keep the YAML file outside the checkout. Validate it
and check compatibility as the agents guide says.

## 4. Create the pipeline

Create it with `teamcity pipeline create` against the parent project and the
VCS root, as the CLI skill's pipelines workflow shows. Take the root, the
`--branch` value, and the remote-run fallback for an unpushed commit from
[Discover and connect](references/discover-and-connect.md).

## 5. Run it until green

Read [Verify a build](references/verify-build.md). Start the first run at
once, without asking. Every time you start a run, tell the user why, say
that it runs remotely with nothing committed, and give the run's `webUrl`:
"here it is, if you want to watch". Classify each failure: blocked queue,
branch binding error, batch-only test failure, or repository failure. A
repository failure is reported and offered as a follow-up, not fixed.

## 6. Improve with the evidence

After the first green run, as [Verify a build](references/verify-build.md)
describes: add `parallelism` when the test job is long enough and run twice
more to show the split; read the run's CPU and memory use and propose a
cheaper or stronger `runs-on` when the evidence shows one. Say why before
each run.

## 7. Report and offer follow-ups

Lead with the green run's `webUrl`. Then:

- the commands chosen and where they came from;
- each test task per module and the job that runs it;
- each job with its runner type, the features added, and what each feature
  buys the team;
- the runs: ID, state, duration, number of test batches, and the speedup
  when measured;
- each manual prerequisite, in the form
  [Manual prerequisites](references/manual-prerequisites.md) requires.
