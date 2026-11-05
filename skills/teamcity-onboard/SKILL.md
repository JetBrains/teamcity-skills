---
name: teamcity-onboard
version: 0.2.0
description: Use when onboarding a project to TeamCity with an authenticated `teamcity` CLI and a checked-out repository. Gets the repository to its first green build, test, and package pipeline with native runners and a live build status, runs it remotely until green, and offers follow-ups.
---

# TeamCity Onboarding Flow

You start with:

- the `teamcity` CLI, logged in to the target TeamCity server;
- the user's repository, checked out in the working directory, on the
  branch and commit the user chose;
- a TeamCity project for the pipeline, with or without a VCS root for the
  repository, as the user chose.

You deliver, fast:

- one pipeline in that project that builds, tests, and packages the
  repository with native runners, in jobs where they run in parallel or
  pass output, steps otherwise;
- a green run, or a red one caused by the project and backed by evidence,
  with a link to watch it;
- nothing committed to the repository;
- the **TeamCity value** the user sees in this run: every feature from
  [Show the value](references/show-the-value.md) that applies, set up and
  named in one line each;
- a short report in the chat, and the details in a report file.

## Before the first command

Load the `teamcity-cli` skill. If it is not installed, run
`teamcity skill install teamcity-cli`. It owns command syntax, output
formats, failure investigation, and the pipeline pull, validate, push loop.
Use only the flags it documents.

Read [Tool policy and secrets](references/teamcity-tool-policy.md). Where this
skill and the `teamcity-cli` skill differ, this skill wins:

- The `teamcity` CLI is already logged in to the target server.
- The repository stays as handed over: same branch, same commit, same files.
  No `git checkout`, `git switch`, `git pull`, or `git push`. Nothing is
  written to or committed in the user's repository. The pipeline lives on
  the server. Your working YAML lives outside the checkout.
- Honest red. If it occurs, report a failure caused by the project (a bug, lint, a flaky
  test) with evidence. Never hide it: no skipped or muted tests, no
  `|| true`, no disabled steps. Fix only failures caused by the pipeline.
- Poll runs with `run tree` and `run view`. `run watch` and `--watch` flood a
  non-interactive shell.
- Every pipeline you create is a deliverable. Probe and diagnostic pipelines
  are forbidden.
- Never ask for or accept a secret value.

## Say what you are doing

The user sees only your messages. Report the whole time, in short lines:

- At the start of each numbered step: the step and what you do next.
- Before each server read, validation, push, or queue command: what it is
  for. After it: what you found, in one line.
- Before each decision: the evidence and the choice. Agent type, JDK, build
  commands, a fix.
- During a run: one line per change of state, as
  [Verify a build](references/verify-build.md) describes.

A long silence looks like a hang. Do not let it happen.

Name a run as the UI does: the pipeline name and the head's number, such as
"conductor run #2", with its link. A job goes by its name. The build ID is
for commands only; never show it to the user. A queued head has no number
yet: give the link, and the number once it starts. Read it from the
`number` field of `run view <id> --json`.

## 1. Read the repository and the server

Read [Project inspection](references/project-inspection.md). Use the workflow
that builds and tests on push or pull request as a guideline, or the build
files when there is none. Deploy, publish, release, and any job that needs a
secret are follow-ups.

Read [Discover and connect](references/discover-and-connect.md). Confirm the
server and the project. Find the VCS root and the branch.

## 2. Choose where it runs

Read [Agents and runtimes](references/agents-and-runtimes.md) before you
write YAML. Take `runs-on`, the runtime (JDK, .NET SDK, Node, Python), and
the CPU architecture from the agent type's parameters. Always pin the
runtime version. Zero compatible agent types is a blocker: fix it before you
queue.

## 3. Write the pipeline

Read [Build-step selection](references/build-step-selection.md) and
[Pipeline features](references/pipeline-features.md). Write the YAML outside
the checkout.

## 4. Create the pipeline

`teamcity pipeline create <name> --project <project-id> --file <yaml> --no-input`,
with `--vcs-root <root-id>` for `VCS root: exists`. Always pass `--file`: it
defaults to `.teamcity.yml` in the checkout. The root, the `--branch`
value, and the remote run come from
[Discover and connect](references/discover-and-connect.md).

## 5. Run it until green

Read [Verify a build](references/verify-build.md). Start the first run at
once, without asking. Announce every run as that guide says. Classify each
failure. Fix pipeline problems only.

## 6. Report and offer follow-ups

Read [Show the value](references/show-the-value.md). The chat keeps what the
user reads or acts on. The file keeps what someone checks later.

In the chat, short and in plain words:

- the green run's `webUrl`, or the red run and its cause in one line;
- the artifact: what is published, its size, and the Artifacts tab link;
- the path to the report file;
- the value summary that guide describes;
- one line per TeamCity feature to look at: what the user gets and where;
- each manual prerequisite in a short sentence, with a link;
- what was left out, in one line;
- the next steps that apply: the full suite when a subset ran, and the follow-ups from that guide.

In `teamcity-onboarding.md` in the checkout root:

- the commands chosen and where they came from, with the reason for every
  script step;
- each test task per module and the job that runs it;
- each job with its runner type;
- the runs: number and ID, such as "#2 (id 45)", state, duration, and the
  correction made before each rerun;
- what was left out, and why;
- each manual prerequisite in the form
  [Manual prerequisites](references/manual-prerequisites.md) requires.
