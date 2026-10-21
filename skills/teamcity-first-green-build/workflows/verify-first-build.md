# Verify the first build

Read this guide after discovery, validation, and compatibility checks in
[Configure and validate CI](configure-and-validate.md).

## Queue the verification build

Skip this guide only when the user explicitly requests configuration only or
prohibits a build. Before queueing, inspect the pipeline for deploy, publish,
data migration, cleanup, external mutation, and material cost. Ask the user for
approval when any of these effects are possible or unclear.

Queue a personal or isolated build when supported. Poll the pipeline head and
jobs with bounded backoff: 5, 10, 20, then 30 seconds.

For every verification run, inspect each queued job's exact compatibility as
soon as its build ID exists. With CLI 1.6+, use
`teamcity run view <job-build-id> --json`; on TeamCity 2026.3+ the
`compatibility` entries cover agents and cloud images with unmet requirements.
List candidate agents in the job's pool and explicitly query
`teamcity agent jobs <agent-id> --incompatible --json` for each one. Match the
generated job ID: without `--incompatible`, the command lists only jobs the
agent can run. Repeat this check for each new verification run, even if the
queue reason only says that no idle agent is available.

An absent job in an agent's incompatible list is not proof that it can run.
Include cloud images from the queued-run result; use another permitted
compatibility helper if the CLI omits a candidate. Distinguish zero compatible
resources from compatible but busy or provisioning resources before changing
YAML or declaring an infrastructure blocker. Do not restart an unchanged run
to diagnose capacity.

After two observations or 60–120 seconds in the queue, record the ID and queue
state. Read [Build diagnostics](../shared/build-diagnostics.md). Queue the next
build only after a documented correction or blocker.

## Handle a failed build

Record the build ID and terminal state. Read
[Build diagnostics](../shared/build-diagnostics.md). Apply its correction or
manual blocker. Before retrying, compare the source YAML with the server-stored
Pipeline YAML, reconcile any difference, and validate the result. Then queue
the next verification build.

## Confirm the result

Continue only when new evidence supports a correction. Confirm the primary
pipeline's dependency chain, required tests, outputs, and final source/stored
YAML match. A successful probe or child does not make a failed primary head
green.

Finish when the first verification build is green or an external blocker is
proven. Report the server, parent project ID, TeamCity object, repository and
branch, VCS strategy, validation result, build IDs, and manual prerequisites.
