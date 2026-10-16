# Discover and connect

Read [TeamCity tool policy](teamcity-tool-policy.md) first. This guide
confirms the target and the repository facts, and finds the VCS root that the
pipeline will use. In the onboarding flow the target and the repository are
already resolved. The `teamcity-cli` skill's "Project connections & VCS
roots" and "Working with pipelines" workflows give the commands.

## Confirm the target

Take the TeamCity server and the parent project ID from the hand-over
context. Use them as given: no project lookup by name, no saved CLI default.
Without a parent project ID, the parent is `_Root`.

Confirm the authenticated identity once with `teamcity auth status`. The flow
authenticated the CLI before this skill started. Do not run
`teamcity auth login`. Keep tokens, keys, passwords, and authorization
headers out of commands, logs, configuration, and reports.

## Inspect the repository

Read [Project inspection](project-inspection.md) for the workflow choice and
the translation table. Then find the smallest build and test commands that
prove the project works. Record:

- the required JDK or runtime, from build files, the workflow's `setup-*`
  steps, and repository documentation;
- test report paths and the packaged output;
- required services, environment variables, and credentials that the build
  and test jobs cannot do without;
- checked-in TeamCity YAML or Kotlin DSL. This means CI already exists.
  Reuse it.

Treat a command from the workflow as a candidate. Verify it against the build
files. Do not run `teamcity migrate`: it recreates the whole workflow, and
this skill recreates only its build and test core.

## Inspect TeamCity

On the confirmed server, list the parent project's pipelines and VCS roots,
the connected agents, and the Pipeline schema (`pipeline list`,
`project vcs list`, `agent list`, `pipeline schema --refresh`). If a pipeline
for this repository already exists, update it. One repository, one pipeline.
The agent inventory and the schema decide `runs-on`; see "Choose where it
runs" in the skill.

## Find the VCS root

Use the VCS root ID from the hand-over context. Without one, list the roots
in the parent project and its ancestors. Reuse the one whose URL matches the
repository. Follow the CLI skill's required sequence: `project vcs list`,
then `project vcs view <id>` for URL, default branch, and auth. The ID comes
from that output only.

- A matching authorized root: use it.
- No root and a public repository: create one with `--auth anonymous` and
  `--branch refs/heads/<checked-out-branch>`, so the root's default branch is
  the branch in the checkout. Without `--branch`, the CLI assumes `main`.
  This is the only root this skill creates.
- No authorized root and a private repository: the pipeline cannot read the
  sources. Report a [manual prerequisite](manual-prerequisites.md) that names
  the web step's repository authorization. Then stop. Connections,
  token-based roots, and token requests are out of scope.

## Choose the branch

Read the root's default branch and branch specification from the `vcs view`
output. The web step created the root, so its default branch may differ from
the checked-out branch. Then:

- To pin the checked-out commit, use the CLI skill's form
  `--revision <root-id>=<sha>@<branch>`, which binds the commit to its
  branch. A bare `--revision <sha>` or a literal `--branch main` fails with
  `invalid_branch_name` whenever the specification does not list the branch.
- For any other branch, pass `--branch` with a logical name the
  specification accepts. Derive the name from the specification:
  `+:refs/heads/*` names `feature/x` as `feature/x`.

After queueing, read back the run's branch and revision before you wait on
it. A red head with the problem `invalid_branch_name` and green jobs is a
branch binding error. Fix the branch selection. The steps stay unchanged, and
that run is not green.

If the specification does not cover the checked-out branch, report a
[manual prerequisite](manual-prerequisites.md) for the root's branch
specification. A switch to `main` or `master`, or a wider branch
specification, only hides the error and is forbidden. For
`invalid_branch_name` on a queued run, read "Diagnose Branch And VCS Access
Failures" in [Build diagnostics](build-diagnostics.md).

## Remote run as the fallback

When the root exists but the branch or the latest commit is not pushed, run a
personal build from the local checkout:
`run start --local-changes=git --no-push --personal` with the chosen
`--branch`, as in the CLI skill's "Personal Builds" section. A remote run
gives early evidence. The pipeline still needs the root for ordinary runs.
For a missing custom-patch permission, use
[Manual prerequisites](manual-prerequisites.md). For a change-collection
failure before checkout, read [Build diagnostics](build-diagnostics.md).
