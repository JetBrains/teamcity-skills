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

## Before the first command

Load the `teamcity-cli` skill: through the Skill tool when it is available,
otherwise by reading `../teamcity-cli/SKILL.md`; if it is not installed, run
`teamcity skill install`. It owns command syntax, output formats, run and
watch, failure investigation, and the pipeline pull, validate, push loop. Do
not guess a flag it documents.

Read [TeamCity tool policy](references/teamcity-tool-policy.md) and
[Token safety](references/token-safety.md). Where this skill and the CLI
skill differ, this skill wins:

- every command carries `TEAMCITY_URL=<server>` from the hand-over context;
  no saved default server, no `teamcity auth login`, no `teamcity api`;
- no repository source edits, skipped tests, or disabled steps to get green;
- no connections, triggers, or pull-request handling; and
- no probe or diagnostic pipelines: every pipeline you create is a
  deliverable.

The hand-over context supplies the server URL, the parent project ID, the
checked-out repository with its remote URL and branch, and the VCS root ID
when one exists. Never ask for these. If one is missing, stop and name it.

## 1. Read the repository

[Discover and connect](references/discover-and-connect.md) confirms the
target, inspects the server, and finds the VCS root and the branch.
[Project inspection](references/project-inspection.md) chooses the workflow:
prefer the classic build, test, and publish flow; otherwise the one that
others depend on or that suits TeamCity best. Record the choice and the
reason. A repository without workflows is designed from its build files.

Keep only the jobs that build and test, one matrix combination, Linux first.
List everything dropped as not migrated.

## 2. Choose where it runs

[Agents, JDK, and compatibility](references/agents-and-jdk.md) decides
`runs-on`, the JDK, and the CPU architecture from the server's own evidence,
before any YAML is written.

## 3. Write the pipeline

[Build-step selection](references/build-step-selection.md) picks dedicated
runners; a script step is for glue only.
[Pipeline features](references/pipeline-features.md) adds the dependency
cache, parallel tests, test reports, and artifacts, even if the workflow had
none. Validate the file and check compatibility as the agents guide says.

## 4. Create the pipeline

Create it with `teamcity pipeline create` against the parent project and the
VCS root, as the CLI skill's pipelines workflow shows. The root, the
`--branch` value, and the remote-run fallback for an unpushed commit come from
[Discover and connect](references/discover-and-connect.md).

## 5. Run it until green, then show the speedup

[Verify a build](references/verify-build.md) queues the run, tells a blocked
queue, a branch binding error, a batch-only test failure, and a repository
failure apart, and then runs the pipeline twice more to show the split.

## Report

Lead with the pipeline URL from `teamcity pipeline view <id> --web`. Then:

- the workflow chosen and why, and the jobs not migrated;
- each job with its runner type and the features added;
- the runs: ID, state, duration, number of test batches;
- each manual prerequisite, in the form
  [Manual prerequisites](references/manual-prerequisites.md) requires.
