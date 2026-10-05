---
name: teamcity-first-green-build
description: Use when creating, validating, or updating TeamCity CI for a repository and driving it through its first successful build.
---

# TeamCity First Green Build

Set up TeamCity CI. Finish with a green verification build or a proven external
blocker.

## Choose the outcome

For a configuration-only request:

- create or update the pipeline;
- validate and read back its saved configuration; and
- query agent inventory and job compatibility once.

Stop after these checks. A required query that is unavailable or denied is a
blocker.

For a first-green request, continue until the verification build is green or an
external blocker is proven.

## Start

Read [the workflow router](workflows/first-green-build.md). It selects the
guides needed for the task.

## Resolve the target

Before any TeamCity query or write, resolve the server from the user's request
and a named target parent project. The parent cannot be `_Root`.

Use a supplied non-`_Root` parent. If none is supplied, create a unique
`<repository>-CI` child project under `_Root` and use its returned ID. Report a
failed creation as a blocker. Never take the server from a prior task, an
environment variable, command history, tool configuration, or repository files.

## Read shared guides only when needed

- `shared/project-inspection.md` — local repository inspection.
- `shared/build-step-selection.md` — build steps, JVM verification, outputs,
  and status messages.
- `shared/kmp-mobile.md` — Kotlin Multiplatform, Android, Compose, or iOS.
- `shared/token-safety.md` — credentials.
- `shared/vcs-connections-and-auth.md` — VCS connections, auth, and roots.
- `shared/build-diagnostics.md` — a failed, stalled, or queued verification
  build.

## Report

Report checked facts only:

- TeamCity server and parent project ID.
- Repository URL and project root.
- TeamCity object and operations.
- Configuration format and validation result.
- Verification build IDs and final states.
- First green build ID, when observed.
- Each manual prerequisite: owner, scope, action, known values, proof, and
  resume signal.
