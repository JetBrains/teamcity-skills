---
name: teamcity-first-green-build
description: Use when creating, validating, updating, or repairing TeamCity CI for a repository, either as configuration-only work or through the first successful build.
---

# TeamCity First Green Build

Use this skill to set up TeamCity CI for a repository and drive it to the first
successful build.

## Select The Requested Outcome

The user's stopping condition controls the workflow. Do not turn a
configuration-only request into a build run.

When the user explicitly asks to create or update a pipeline, validate it, and
stop without queueing a build:

- Follow repository inspection, TeamCity discovery, VCS setup, pipeline
  creation, server validation, and compatibility discovery. Skip Remote Run,
  build queueing, build polling, and first-build debugging.
- Preserve every requested or repository-defined independent job. Before
  finishing, read back the server-stored YAML and audit job topology, dedicated
  runner types and task/goal properties, `runs-on`, and artifact publication
  rules against the repository and existing CI.
- Treat a locally valid file as incomplete until the target pipeline exists,
  is attached to the intended VCS root, and the exact stored configuration has
  passed server validation. Make at most one evidence-based correction to a
  validation/read-back mismatch, then report a concrete blocker.

For a first-green request, follow the full workflow through a successful build
or a proven external blocker.

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
- `shared/vcs-connections-and-auth.md` when TeamCity CLI or MCP is available
  for VCS connection discovery, authentication, or VCS-root setup.

## Non-Negotiable TeamCity Transport Rule

Never invoke `teamcity api`, address a TeamCity REST endpoint from a shell, or
use `curl`, `wget`, or another shell HTTP client for a TeamCity operation. This
applies to reads, diagnostics, and writes, including when the first-class CLI
does not expose a required field.

Use the matching first-class `teamcity` command first. If it lacks the required
capability, discover the TeamCity MCP tools available in the current
environment, read the relevant guide and tool schema, and confirm that the MCP
connection targets the exact server from the request. Prefer a dedicated MCP
operation. A generic MCP read operation is acceptable only when its guide and
schema explicitly permit the narrowly scoped read; never assume that a
similarly named MCP tool has the same allowlist on another server.

If neither surface supports the operation, stop that operation and give the
concrete manual completion checklist required below. Do not fall back from a
missing CLI or MCP capability to REST through the CLI or shell.

## Mandatory First Response

The TeamCity server must be known before querying TeamCity or making a write.
The target parent must be a named project, never `_Root`:

- The exact TeamCity server name or URL.
- A user-supplied non-`_Root` parent project name or ID, when present.

The server must come from the user's own request. Do not infer it from prior
runs, environment variables, command history, tool names, cached context, or
repository files. Use the supplied non-`_Root` parent, or derive a unique
`<repository>-CI` name and create it with `teamcity project create
<repository>-CI --parent _Root`; use its returned ID.

If the server and a non-`_Root` parent are present in the request, take them as
given and proceed. Do not ask
the user to restate or confirm them: the request is the confirmation, and a
needless question stalls an unattended run for nothing. Report the server and
resulting parent ID once the parent is resolved, then continue.

If parent creation fails, report the error; do not use `_Root` as a fallback.

## Prerequisites

At the start of every task, before repository inspection, TeamCity discovery, or
writes, ask for or confirm:

- The exact TeamCity server name or URL being targeted.
- The resolved non-`_Root` target parent project.

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
- Treat every `runs-on` value as target-server-specific. Query the live schema
  and available agents/images first, then choose a selector that fits the job.
  For self-hosted agents, express stable capabilities such as OS, architecture,
  CPU, or agent parameters. A server-managed, durable agent-family name prefix
  is valid only when the target server accepts it in the actual pipeline
  upload; do not use one transient VM name. Never carry a tier such as
  `Linux-Medium` from another server or case.
- A green build is valid only when its effective runtime satisfies the version
  declared by the repository. For a required JDK, discover the target server's
  exact agent parameter, managed tool, or image; constrain scheduling to that
  capability and select it explicitly for the job. Never reuse a JDK parameter
  name learned on another server or accept an older agent default merely
  because the build command succeeds.
- Before calling a queued Pipeline job an agent-capacity problem, inspect its
  unresolved-parameter diagnostics and the saved YAML. TeamCity expands
  `%name%` in Pipeline script content before choosing an agent, including in a
  platform-specific branch; a Windows runtime expression such as
  `%ERRORLEVEL%` is therefore an unresolved TeamCity parameter unless it was
  deliberately declared.
- A build that remains queued for 60--120 seconds has reached a mandatory
  compatibility checkpoint. After no more than two queued-status observations,
  inspect the enabled/authorized agent inventory, the job's incompatible-agent
  reasons, and unresolved `%name%` substitutions in the server-stored YAML
  before waiting again. If those checks prove that no compatible agent or cloud
  image exists, stop polling and do not start or restart another build. Make at
  most one evidence-based configuration correction, validate it, and retry only
  when the compatibility evidence changed.
- If the agent/job compatibility command returns `permission_denied`, record
  compatibility as **unverified**. Do not infer compatibility from a generic
  wait reason or agent inventory alone. Use another permitted machine-readable
  TeamCity surface. If none is available, stop with the missing permission as
  the blocker and do not retry until programmatic compatibility access is
  granted. Never substitute a manual UI confirmation for this check.
- Prefer personal builds for validation.
- Iterate only while each rerun has new evidence or a concrete fix.
- Stop on proven blockers such as missing VCS authorization, missing TeamCity
  permissions, incompatible build environments, or unavailable external
  services.
- When a manual action remains, give a concrete completion checklist rather
  than an open-ended question. State the owner, exact TeamCity scope, UI path
  or supported command, known values to enter, expected result, and the ID or
  evidence the user should return so the agent can continue.
- Validate every generated or modified TeamCity YAML or Kotlin DSL
  configuration before queueing a build. A syntax-only YAML parse is not a
  successful TeamCity validation.
- A single empty or non-idle agent query is not proof that an accepted build
  cannot run: cloud agents may be provisioned on demand.

## Final Report

Report only facts that were checked:

- TeamCity server and parent project ID.
- Repository URL and project root.
- Existing, created, updated, or selected TeamCity object.
- Important TeamCity operations performed.
- Configuration format, validation method, and validation result.
- First failed build ID and root cause, if one was observed.
- First successful build ID, if one was observed.
- A concrete manual completion checklist for every remaining prerequisite or
  blocker: who performs it, where, what values are known, how to verify it,
  and what to send back to resume the task.
