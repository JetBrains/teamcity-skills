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

After two observations or 60–120 seconds in the queue, record the ID and queue
state. Read [Build diagnostics](../shared/build-diagnostics.md). Queue the next
build only after a documented correction or blocker.

## Handle a failed build

Record the build ID and terminal state. Read
[Build diagnostics](../shared/build-diagnostics.md). Apply its correction or
manual blocker, then queue the next verification build.

## Confirm the result

Continue only when new evidence supports a correction. Confirm the primary
pipeline's dependency chain, required tests, and outputs. A successful probe or
child does not make a failed primary head green.

Finish when the first verification build is green or an external blocker is
proven. Report the server, parent project ID, TeamCity object, repository and
branch, VCS strategy, validation result, build IDs, and manual prerequisites.
