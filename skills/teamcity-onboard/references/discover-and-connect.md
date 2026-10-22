# Discover and connect

Confirm the server, inspect it, and find the VCS root and the branch the
pipeline uses. Commands: the `teamcity-cli` skill's "Project connections &
VCS roots" and "Working with pipelines" workflows.

## Confirm the server and the project

The flow authenticated the CLI against the target server before this skill
started. Confirm once with `teamcity auth status`. The parent project is the
project ID from the hand-over context. Without one, run `project list` and
ask the user which project the pipeline belongs to. Confirm the ID with
`project view <project-id>`.

## Inspect the server

List the project's pipelines and VCS roots, the connected agents, and the
Pipeline schema: `pipeline list --project <project-id>`,
`project vcs list --project <project-id>`, `agent list`,
`pipeline schema --refresh`. When a pipeline for this repository exists,
update it. One repository, one pipeline.

## Find the VCS root

Use the VCS root ID from the hand-over context. Without one, list the roots
in the project with `project vcs list --project <project-id>` and reuse the
one whose URL matches the repository. Read URL, default branch, and auth with
`project vcs view <id>`.

- A matching authorized root: use it.
- No root, public repository: create one in the project with
  `--project <project-id>`, `--auth anonymous`, and
  `--branch refs/heads/<checked-out-branch>`. Without `--branch` the CLI
  assumes `main`. This is the only root this skill creates.
- No authorized root, private repository: the pipeline cannot read the
  sources. Write a [manual prerequisite](manual-prerequisites.md) for the
  repository App or a project-scoped connection, then stop. Connections,
  token-based roots, and token requests are out of scope.

## Choose the branch

The safe setup: one branch, a pinned revision with `--branch`, no triggers.
Read the root's default branch and branch specification from `vcs view`.
TeamCity builds the root's default branch unless the run names another one.
When the checked-out branch is not the default, a run without `--branch`
builds code you never inspected, and its result proves nothing. Always pass
the pinned revision and the branch together.

- Pin the checked-out commit with `--revision <root-id>=<sha>@<branch>` and
  pass `--branch` as well. Without `--branch` the checkout fails with
  `couldn't find remote ref <unspecified>`. A bare `--revision <sha>` or a
  literal `--branch main` fails with `invalid_branch_name` when the
  specification does not list the branch.
- For a branch with another name, derive the logical name from the
  specification: `+:refs/heads/*` names `feature/x` as `feature/x`.
- When the specification does not cover the checked-out branch, write a
  [manual prerequisite](manual-prerequisites.md) for the root's branch
  specification. A switch to `main` or a wider specification hides the error
  and is forbidden.

After queueing, read back the run's branch and revision before you wait on
it. A red head with `invalid_branch_name` and green jobs is a branch binding
error: fix the branch selection. The steps stay unchanged. That run is not
green.

## Remote run as the fallback

When the root exists but the branch or the latest commit is not pushed, run a
personal build from the local checkout:
`run start --local-changes=git --no-push --personal` with the chosen
`--branch` (CLI skill, "Personal Builds"). It gives early evidence. The
pipeline still needs the root for ordinary runs. A missing custom-patch
permission is a [manual prerequisite](manual-prerequisites.md).
