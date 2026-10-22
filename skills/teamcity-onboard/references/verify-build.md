# Verify a build

Queue the pipeline and drive it to green. The `teamcity-cli` skill's "Start,
monitor & personal builds" and "Fix a failure & monitor until green" sections
give the commands and the polling cadence (5, 10, 20, then 30 seconds). This
guide adds what onboarding changes.

## Start and poll

Queue on the branch from [Discover and connect](discover-and-connect.md).
Each run starts without confirmation. On every start:

- say why this run happens;
- say that it runs remotely and commits nothing;
- give the run's `webUrl` from `run start --json` or
  `run list --json=id,webUrl`: "here it is, if you want to watch";
- note the run's `queuedDate` for the cancel guard below.

Poll `run tree <id>` and `run view <id> --json`; never `run watch`. A queued
run has to be noticed early. After each poll that shows a change, one line:
a job queued and its wait reason, a job started, a job finished with its
state and test count, the head finished. After five minutes with no change,
one line with the time elapsed and what you wait for. Keep going until the
head and every job are green, or a blocker is proven. A green run is
checked: read every test job's test count. A test job with 0 tests is a
silent failure. Fix the filter as
[Build-step selection](build-step-selection.md) describes and run again.

`execution-timeout-minutes` is behind a server toggle and may do nothing. Put
the limit in the steps as [Build-step selection](build-step-selection.md)
describes, and `run cancel <id>` when `queuedDate` plus the expected duration
from [Project inspection](project-inspection.md) plus a margin has passed.

## Decide what a failure means

Read the evidence from the most structured to the least: build problems,
failed tests, a filtered error view of the log, a small log window around
each anchor. Then:

**A job queued for 120 seconds.** Read its wait reason with
`queue list --job <job-id> --json=id,waitReason,queuedDate` and run the
candidate check from [Agents and JDK](agents-and-jdk.md). A waiting head is
never the cause.

- Zero compatible candidates or unresolved parameters: one supported
  correction, then requeue with `--rebuild-deps`. Typical causes: a key no
  agent has (`os-family`), an architecture label that differs from the
  agent's value (`x86_64` versus `amd64`), a host-JDK parameter no agent
  advertises.
- Compatible candidates, all busy: a capacity wait. Keep polling.
- Compatibility cannot be verified: strip the job to the bare selector, push,
  requeue with `--rebuild-deps`.
- Ten minutes in the queue is the maximum. An added requirement or a branch
  switch hides the error and is forbidden.

**A red head with green jobs.** Read `run log <head-id> --failed --json` and
its `problems` array; `run view --json` can show none. `invalid_branch_name`
is a branch binding error: fix the branch selection as
[Discover and connect](discover-and-connect.md) describes. The steps stay
unchanged.

**A job restarted after its agent disappeared**, seen in builds of about 40
minutes on hosted agents. TeamCity restarts it with no visible cap. Stop
after the second identical loss: cancel the run, report it, shorten the job
before another run.

**A failure before checkout** with `Repository not found`, authentication
failed, 401, or 404, on a private repository whose root has no durable
credential: a VCS credential blocker. A passing VCS connection test does not
override it. Report the build ID, the root ID, and the repository URL, and
write a [manual prerequisite](manual-prerequisites.md) for the repository
App or a project-scoped connection. Do not invent a personal access token.

**A test that fails on its own**, in every run with no TeamCity cause in the
log: a repository failure. Report the test, the assertion, and the build ID,
and stop. A job that failed only through its dependency needs no diagnosis.

**Anything else**: only the pipeline YAML path applies. `pipeline pull` the
stored YAML into your working file outside the repository, correct it,
validate, push, requeue. Code fixes are out of scope. When `run log` is
denied, read `run view <id>` and `run tests <id> --failed`; the `Status`
line shows in `run view`.

One correction per run; an unchanged retry is wasted. Stop after three
corrections. A successful child does not make a failed head green. When the
evidence does not establish one cause, report the likely causes, the
evidence, and the next small check.
