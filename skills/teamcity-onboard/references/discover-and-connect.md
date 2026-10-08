# Discover and connect

Read [TeamCity tool policy](teamcity-tool-policy.md) first. This guide
establishes the target, the repository facts, and the VCS root that the
pipeline will use. In the onboarding flow the target and the repository are
already resolved; the work here is to confirm them and to find the root.

## Confirm the target

The hand-over context names the TeamCity server and the parent project ID.
Do not resolve a project by name, do not ask for either value, and do not take
the server from the saved CLI default. `_Root` is never the parent.

Confirm the authenticated identity once:

```bash
TEAMCITY_URL=<server> teamcity auth status
```

Do not run `teamcity auth login`; the flow authenticated the CLI before this
skill started. Keep tokens, keys, passwords, and authorization headers out of
commands, logs, configuration, and reports.

## Inspect the repository

Read [Project inspection](project-inspection.md) for the workflow choice and
the translation table. Then find the smallest build and test commands that
prove the project works. Record:

- the required JDK or runtime from build files, the workflow's `setup-*`
  steps, and repository documentation;
- test report paths and the packaged output;
- required services, environment variables, and credentials the build and
  test jobs cannot do without; and
- checked-in TeamCity YAML or Kotlin DSL, which means CI already exists and
  the onboarding should reuse it rather than add a second pipeline.

Treat a command from the workflow as a candidate; verify it against the build
files. Do not run `teamcity migrate`: it recreates the whole workflow, and
this skill recreates only its build and test core.

## Inspect TeamCity

On the confirmed server, inspect the parent project, its existing pipelines
and VCS roots, the connected agents, and the Pipeline schema:

```bash
TEAMCITY_URL=<server> teamcity pipeline list --project <parent-id>
TEAMCITY_URL=<server> teamcity project vcs list --project <parent-id> --json
TEAMCITY_URL=<server> teamcity pipeline schema --refresh
```

If a pipeline for this repository already exists, update it instead of
creating another. The agent inventory and the schema decide `runs-on`; see
"Choose where it runs" in the skill.

## Find the VCS root

Use the VCS root ID from the hand-over context. Without one, list the roots in
the parent project and its ancestors and reuse the one whose URL matches the
repository. Inspect it before using it; do not guess its ID:

```bash
TEAMCITY_URL=<server> teamcity project vcs view <vcs-root-id>
```

- A matching authorized root: use it.
- No root and a public repository: create one with `--auth anonymous` and
  continue. This is the only root this skill creates.
- No authorized root and a private repository: the pipeline cannot read the
  sources. Report a [manual prerequisite](manual-prerequisites.md) naming the
  web step's repository authorization. Do not create a connection, do not
  create a token-based root, and do not ask for a token.

## Choose the branch

Read the root's default branch and branch specification from the `vcs view`
output. The web step created the root, so its default branch may not be the
branch that is checked out. TeamCity's logical default branch is `<default>`:
when the checked-out Git branch equals the root's default ref, queue with
`--branch '<default>'`, including when pinning `--revision`. Do not pass its
literal name (`main`, `master`, or similar) as a named branch: without a
matching branch specification, TeamCity marks the pipeline head with
`invalid_branch_name` even when every job succeeds. For a non-default branch,
derive the accepted logical name from the root's branch specification. After
queueing, read back the run's branch and revision before waiting on it.

If the checked-out branch is not covered by the specification, report a
[manual prerequisite](manual-prerequisites.md) for the root's branch
specification. Do not switch to `main` or `master` to make the error go away.
For `invalid_branch_name` on a queued run, read "Diagnose Branch And VCS
Access Failures" in [Build diagnostics](build-diagnostics.md).

## Remote run as the fallback

When the root exists but the branch or the latest commit is not pushed, run a
personal build from the local checkout instead of waiting for a push:

```bash
TEAMCITY_URL=<server> teamcity run start <job-id> --branch '<default>' \
  --local-changes=git --no-push --personal
```

Use the accepted logical branch instead of `<default>` when the checkout is
not at the root's default ref.

A remote run gives early evidence; the pipeline still needs the root for
ordinary runs. For a missing custom-patch permission, use
[Manual prerequisites](manual-prerequisites.md). For a change-collection
failure before checkout, read [Build diagnostics](build-diagnostics.md).
