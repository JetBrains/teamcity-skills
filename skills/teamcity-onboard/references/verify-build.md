# Verify a build

Use this guide to queue the pipeline, drive it to green, and show the
parallel test speedup. Read [Agents, JDK, and compatibility](agents-and-jdk.md)
first.

The mechanics come from two `teamcity-cli` skill sections:

- "Start, monitor & personal builds": start a run, read back its branch and
  revision, report progress at 5, 10, 20, then 30 seconds.
- "Fix a failure & monitor until green": the loop and its stop conditions.

This guide adds what onboarding changes.

## Queue and watch

Queue on the branch chosen in [Discover and connect](discover-and-connect.md).
Each run starts without confirmation. On every start, say why this run
happens, say that it runs remotely and commits nothing, and give the run's
`webUrl` from `run start --json` or `run list --json=id,webUrl`.
The user is waiting, and a queued run has to be noticed early. 
Keep going until the head and every job are green, or a blocker is proven.

## Decide what a failure means

**A runnable job queued for two observations or 120 seconds**: read its
exact wait reason from `teamcity queue list --job <job-id>` and run the
candidate check in [Build diagnostics](build-diagnostics.md).

- Zero compatible candidates or unresolved parameters: make a supported
  correction.
- Compatible candidates confirmed but busy: capacity wait. Continue watching
  the accepted run.
- Compatibility cannot be verified: remove the sub-requirements down to the
  bare selector.
- Requeue only with a change. An added requirement or a branch switch only
  hides the error and is forbidden.
- Lower `parallelism` for a later run only when evidence shows the available
  capacity cannot provide the planned split.
- After any requirement change, start the run with `--rebuild-deps`.
  Otherwise, the head reuses the queued job build from before the change.

**A red head with green jobs** and the problem `invalid_branch_name` is a
branch binding error. Fix the branch selection as
[Discover and connect](discover-and-connect.md) describes. The steps stay
unchanged.

**A test that fails only in a batch**, while the same class is green when the
job runs unsplit or in a different batch, is a test isolation problem.
Usually shared state is the cause: a reused Testcontainers container or
static data. A retry proves nothing. Remove `parallelism` from that job,
push, requeue, and report the test and the reason the speedup is not
available for it.

**A test that fails on its own**, in every run and with no TeamCity cause in
the log, is a repository failure. Report the test, the assertion, and the
build ID, and stop. A job that failed only through its snapshot dependency
needs no diagnosis.

**Anything else**: read [Build diagnostics](build-diagnostics.md) to
interpret the evidence the CLI skill's investigation workflow collects. Of
the CLI skill's fix paths, only the pipeline YAML path applies: pull the
stored YAML, correct it, validate, push, and keep your working copy outside
the checkout identical to it. Code fixes and `--local-changes` verification
of source edits are out of scope.

Continue only when new evidence supports a correction. Stop after three
corrections. A successful child does not make a failed head green.

## Show the speedup

The first green run completes the deliverable and runs unsplit. Add
`parallelism` as [Pipeline features](pipeline-features.md) describes, push,
and run the pipeline two more times on the same revision only when both are
true:

- the test job took a minute or more;
- less than 40 minutes have passed since your first command.

When only time was short, give the user the YAML change and the command for
the two runs. The first run gave TeamCity the test history. The later runs
split the tests into batches. Compare them with
`teamcity run list --job <job-id> --json=id,status,startDate,finishDate`.

Report only what you observed. If the test job took under a minute, leave
`parallelism` out and say the suite is too short to split.
