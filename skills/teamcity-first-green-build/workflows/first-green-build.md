# First Green Build

Load only the guides needed for the requested outcome.

## Common work

Read these guides in order:

1. [TeamCity tool policy](../shared/teamcity-tool-policy.md)
2. [Discover and connect](discover-and-connect.md)
3. [Configure and validate CI](configure-and-validate.md)

They establish the target, inspect the repository, prepare VCS access, save and
validate the configuration, and check compatibility.

## Explicit configuration-only request

Stop after common work only when the user explicitly requests configuration only
or prohibits a build. Completion needs a saved pipeline, its intended VCS root,
server validation, and a read-back audit of jobs, runners, selectors, and
artifact rules.

## First green

After common work, read [Verify the first build](verify-first-build.md). Finish
with a green verification build or a proven external blocker.

## Extra guides

- [Project inspection](../shared/project-inspection.md) — repository structure,
  technology, and GitHub Actions workflows.
  and technology.
- [Build-step selection](../shared/build-step-selection.md) — runner choice,
  scripts, JVMs, outputs, and status messages.
- [KMP and mobile](../shared/kmp-mobile.md) — Kotlin Multiplatform, Android,
  Compose, or iOS.
- [Token safety](../shared/token-safety.md) — credentials.
- [VCS connections and authentication](../shared/vcs-connections-and-auth.md)
  — VCS roots and connections.
- [Build diagnostics](../shared/build-diagnostics.md) — failed, stalled, or
  queued verification builds.
- [Manual prerequisites](../shared/manual-prerequisites.md) — a required
  operation that the available tools cannot complete safely.
