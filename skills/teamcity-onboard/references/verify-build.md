# Verify a build

Use this guide to queue the pipeline, drive it to green, and show the parallel
test speedup. Read [Agents, JDK, and compatibility](agents-and-jdk.md) first.

The mechanics come from the `teamcity-cli` skill: "Start, monitor & personal
builds" for starting a run, reading back its branch and revision, and
reporting progress at 5, 10, 20, then 30 seconds; "Fix a failure & monitor
until green" for the loop and its stop conditions. This guide adds what
onboarding changes.

## Queue and watch

Queue on the branch chosen in [Discover and connect](discover-and-connect.md).
Poll rather than `--watch`: the user is waiting, and a queued run has to be
noticed early. Keep going until the head and every job are green or a blocker
is proven.

## Decide what a failure means

**A runnable job queued for two observations or 120 seconds** needs its exact
wait reason from `teamcity queue list --job <job-id>` and the candidate check
in [Build diagnostics](build-diagnostics.md). Zero compatible candidates or
unresolved parameters need a supported correction. "No idle compatible
agents" with compatible candidates confirmed means busy capacity; continue
watching the accepted run. Do not requeue unchanged, add a requirement, or
switch branches to hide an error. Lower `parallelism` for a later run only
when evidence shows the available capacity cannot provide the planned split.
When compatibility cannot be verified, remove the sub-requirements down to
the bare selector. After any requirement change start the run with
`--rebuild-deps`; otherwise the head reuses the stale queued job build.

**A red head with green jobs** and the problem `invalid_branch_name` is a
branch binding error. Fix the branch selection as
[Discover and connect](discover-and-connect.md) describes; do not touch the
steps.

**A test that fails only in a batch**, while the same class is green when the
job runs unsplit or in a different batch, is a test isolation problem, usually
shared state such as a reused Testcontainers container or static data. Do not
retry it. Remove `parallelism` from that job, push, requeue, and report the
test and the reason the speedup is not available for it.

**A test that fails on its own**, in every run and with no TeamCity cause in
the log, is a repository failure. Report the test, the assertion, and the
build ID, and stop. A job that failed only through its snapshot dependency
needs no diagnosis.

**Anything else**: read [Build diagnostics](build-diagnostics.md) to interpret
the evidence the CLI skill's investigation workflow collects. Of the CLI
skill's fix paths, only the pipeline YAML path applies: pull the stored YAML,
correct it, validate, push, and keep the checkout's `.teamcity.yml` identical
to it. Code fixes and `--local-changes` verification of source edits are out
of scope.

Continue only when new evidence supports a correction, and stop after three
corrections. A successful child does not make a failed head green.

## Show the speedup

The first green run completes the deliverable. Run the pipeline two more
times on the same revision only when the test job took a minute or more and
less than 40 minutes have passed since your first command; otherwise give the
user the command for the two runs. The first run gives TeamCity the test
history; the later runs split the tests into batches. Compare them with
`teamcity run list --job <job-id> --json=id,status,startDate,finishDate`.

Report only what you observed. If the test job takes under a minute, say that
parallel tests do not pay off yet.
