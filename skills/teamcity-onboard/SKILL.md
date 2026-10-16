---
name: teamcity-onboard
version: 0.1.0
description: Use when onboarding a project to TeamCity and the task hands over a server URL and a repository. Recreates the build and test core as a pipeline with native runners and parallel tests, and runs it until green.
---

# TeamCity Onboard

Show a team that leaves GitHub Actions what their build looks like on
TeamCity:

- the build and test core of one workflow;
- native runners;
- parallel tests;
- a green pipeline with a visible speedup.

The web step before this skill created the instance and, when it could, an
authenticated VCS root. This skill needs that step.

## Before the first command

Load the `teamcity-cli` skill through the Skill tool. If it is not installed,
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
- Connections, triggers, and pull-request handling are out of scope.
- Every pipeline you create is a deliverable. Probe and diagnostic pipelines
  are forbidden, even when build logs are unreadable.

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

Read [Project inspection](references/project-inspection.md). Choose the
workflow. Prefer the classic build and test flow. Otherwise, choose
the one that others depend on, or the one that suits TeamCity best. Record
the choice and the reason. For a repository without workflows, design the
pipeline from its build files.

Keep only the jobs that build and test. Keep one matrix combination, Linux
first.

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
dedicated runners. A script step is for glue only.

Read [Pipeline features](references/pipeline-features.md). Add the dependency
cache, parallel tests, test reports, and artifacts, even if the workflow had
none. Validate the file and check compatibility as the agents guide says.

## 4. Create the pipeline

Create it with `teamcity pipeline create` against the parent project and the
VCS root, as the CLI skill's pipelines workflow shows. Take the root, the
`--branch` value, and the remote-run fallback for an unpushed commit from
[Discover and connect](references/discover-and-connect.md).

## 5. Run it until green, then show the speedup

Read [Verify a build](references/verify-build.md). Queue the run. Classify
each failure: blocked queue, branch binding error, batch-only test failure,
or repository failure. When time and tests allow, run the pipeline twice more
to show the split.

## Report

Lead with the pipeline URL from `teamcity pipeline view <id> --web`. Then:

- the workflow chosen and why;
- each job with its runner type, the features added, and what each feature
  buys the team;
- the runs: ID, state, duration, number of test batches, and the speedup
  when measured;
- each manual prerequisite, in the form
  [Manual prerequisites](references/manual-prerequisites.md) requires.
