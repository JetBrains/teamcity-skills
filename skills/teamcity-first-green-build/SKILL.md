---
name: teamcity-first-green-build
description: Use when setting up, updating, or repairing TeamCity CI for a repository, then iterating through builds until the first successful build or a proven blocker.
---

# TeamCity First Green Build

Use this skill to set up TeamCity CI for a repository and drive it to the first
successful build.

## Load First

Read and follow the canonical workflow:

- `workflows/first-green-build.md`

Read shared guidance only when relevant:

- `shared/project-inspection.md` for local repository inspection.
- `shared/build-step-selection.md` for choosing TeamCity build steps and the
  required build status service messages.
- `shared/kmp-mobile.md` for Kotlin Multiplatform, Compose Multiplatform, or
  Android/iOS build and test setup.
- `shared/token-safety.md` when credentials are involved.
- `shared/build-log-debugging.md` when diagnosing failed builds.

## Mandatory First Response

Before inspecting files, querying TeamCity, using local environment context, or
making any write, the assistant must visibly ask the user to confirm:

- The exact TeamCity server name or URL.
- The target parent project name or ID. `_Root` is valid.

Do not infer these values from prior runs, environment variables, command
history, tool names, cached context, or repository files. If both values are not
present in the user's current request, stop and ask for them in the next
assistant message.

## Prerequisites

Before any TeamCity write, also make sure the following facts are known:

- Authenticated TeamCity access for that same server.
- The local repository URL and build root.
- A safe way to keep tokens and VCS credentials out of commands, logs, saved
  prompts, generated files, and final reports.

If the configured TeamCity server and the authenticated access point to
different servers, stop. Do not substitute another server.

## Default Behavior

- Prefer TeamCity Pipelines or YAML over Kotlin DSL unless the repository
  already uses Kotlin DSL successfully or the user explicitly asks for Kotlin
  DSL.
- Inspect existing TeamCity objects before creating new ones.
- Preserve checked-in TeamCity YAML topology unless the user asks for a reduced
  first pass.
- Validate every generated or modified TeamCity YAML or Kotlin DSL
  configuration before queueing a build. A syntax-only YAML parse is not a
  successful TeamCity validation.
- Prefer personal builds for validation.
- Iterate only while each rerun has new evidence or a concrete fix.
- Stop only on proven blockers such as missing VCS authorization, missing
  TeamCity permissions, incompatible build environments, or unavailable
  external services. A single empty or non-idle agent query is not proof that
  an accepted build cannot run: cloud agents may be provisioned on demand.

## Final Report

Report only facts that were checked:

- TeamCity server and parent project ID.
- Repository URL and project root.
- Existing, created, updated, or selected TeamCity object.
- Important TeamCity operations performed.
- Configuration format, validation method, and validation result.
- First failed build ID and root cause, if one was observed.
- First successful build ID, if one was observed.
- Remaining manual prerequisites or blockers.
