# Verify a build

Use this guide to queue a verification build and drive it to a result. Read
[Validate and check compatibility](validate-and-check-compatibility.md) first.

## Queue and watch

Queue a personal or isolated build when supported. Read back the queued
build's branch and revision before waiting. Poll the pipeline head and jobs
with bounded backoff: 5, 10, 20, then 30 seconds.

After two observations or 60–120 seconds in the queue, record the ID and queue
state. Read [Build diagnostics](build-diagnostics.md). Queue the next build
only after a documented correction or blocker.

## Handle a failed build

Record the build ID and terminal state. Read
[Build diagnostics](build-diagnostics.md). Apply its correction or manual
blocker. Before retrying, compare the source YAML with the server-stored
Pipeline YAML, reconcile any difference, and validate the result. Then queue
the next verification build.

Continue only when new evidence supports a correction. A successful probe or
child does not make a failed primary head green.
