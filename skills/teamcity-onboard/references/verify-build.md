# Verify a build

Use this guide to queue a verification build and drive it to a result. Read
[Validate and check compatibility](validate-and-check-compatibility.md) first.

The mechanics come from the `teamcity-cli` skill: "Start, monitor & personal
builds" for starting a run, reading back its branch and revision, and
reporting progress at 5, 10, 20, then 30 seconds; "Fix a failure & monitor
until green" for the loop and its stop conditions. This guide adds what
onboarding changes.

## Queue and watch

Queue on the branch chosen in [Discover and connect](discover-and-connect.md).
Poll rather than `--watch`: the user is waiting, and a queued run has to be
noticed early.

After two observations or 60–120 seconds in the queue, record the ID and the
wait reason and read [Build diagnostics](build-diagnostics.md). Queue the next
build only after a documented correction or blocker.

## Handle a failed build

Record the build ID and terminal state. Read
[Build diagnostics](build-diagnostics.md) to interpret the evidence that the
CLI skill's investigation workflow collects. Of the CLI skill's fix paths,
only the pipeline YAML path applies: pull the stored YAML, correct it, validate,
push, and keep the checkout's `.teamcity.yml` identical to it. Code fixes and
`--local-changes` verification of source edits are out of scope.

Continue only when new evidence supports a correction, and stop after three
corrections. A successful child does not make a failed head green.
