# Verify a build

Queue the pipeline and drive it to green. The `teamcity-cli` skill's "Start,
monitor & personal builds" (`run-builds.md`) and "Fix a failure & monitor
until green" (`fix-and-verify.md`) workflows give the commands and the poll
intervals (5, 10, 20, then 30 seconds). This guide adds what onboarding
changes.

## Start and poll

Queue on the branch from [Discover and connect](discover-and-connect.md).
Each run starts without confirmation. On every start:

- say why this run happens;
- say that nothing is committed or pushed;
- give the run's `webUrl` from `run start --json` or
  `run list --json=id,webUrl`: "here it is, if you want to watch";
- note the run's `queuedDate` for the cancel guard below.

Only after the first run is queued tell the user in their language:

> Your first build is running on TeamCity. It takes a few minutes.
> You have a couple of options:
> * Watch it live and explore TeamCity UI: <run webUrl>
> * or grab a coffee and relax while I'm setting the things up. TeamCity will notify you when it's done.

Your own words are fine. The message must have the full `webUrl`, on its
own line, so the user can click it at once and watch the run in the UI.
Never write "the link" without the URL. The link is the run page, not the
pipeline or the project.

Poll `run tree <id>` and `run view <id> --json`. A queued run has to be
noticed early. After each poll that shows a change, one line: a job queued
and its wait reason, a job started, a job finished with its state and test
count, the head finished. After five minutes with no change, one line with
the time elapsed and what you wait for. Keep going until the head and every
job are green, or a blocker is proven.

A green run is checked:

- Every test job's `count`, `passed`, `failed`, and `ignored`, from
  `run tests <id> --json --limit 1`; `run view --json` has none. Without the
  limit it lists every test. A missing field is 0. 0 tests in a job that
  should report them is a silent failure: fix the filter as
  [Build-step selection](build-step-selection.md) describes and run again.
  A count a bit lower than the runner's comes from duplicate test names, not
  missing tests.
- `run artifacts <id>` on every job with `files-publication`. No `publish/`
  folder is also a silent failure: fix the path as
  [Pipeline features](pipeline-features.md) describes.

Run `run cancel <id> --yes` when `queuedDate` plus the expected duration from
[Project inspection](project-inspection.md) plus a margin has passed.

## Decide what a failure means

Read the evidence from the most structured to the least: build problems,
failed tests, a filtered error view of the log, a small log window around
each error. Then:

**A job queued for 120 seconds.** Read its wait reason with
`queue list --job <job-id> --json=id,waitReason,queuedDate` and the
compatible image count, as [Agents and runtimes](agents-and-runtimes.md)
describes. A waiting head is never the cause.

- 0 compatible images or unresolved parameters: one supported correction,
  then requeue with `--rebuild-deps`. Typical causes: a `runs-on` name the
  server has no type for, a key no agent type has, an architecture label
  that differs from the agent's value (the workflow says `x86_64`, the agent
  `amd64`), a host-JDK parameter no agent has.
- Compatible images, all busy: a capacity wait. Keep polling.
- Ten minutes in the queue is the maximum. An added requirement or a branch
  switch hides the error and is forbidden.
- No agent started in ten minutes, and the job is compatible: TeamCity could
  not start an agent. Cancel the run and stop. It is not a manual
  prerequisite. Tell the user in plain words:
  "TeamCity couldn't start a `Linux-Medium` agent in 10 minutes. The
  pipeline is ready: run it again later from <pipeline link>."

**A branch binding error**: a red head with green jobs and
`invalid_branch_name` in the `problems` array of
`run log <head-id> --failed --json` (`run view --json` can show none); or
every job failing at checkout with "Missing VCS reference",
`couldn't find remote ref <unspecified>`, or "Error while applying patch" on
a run without a patch. Not the code: fix the `--revision` and `--branch`
pair as [Discover and connect](discover-and-connect.md) describes. The steps
stay unchanged.

**"Not enough trial license credits"** on a job: the server can run nothing
more. Stop: no retry, no smaller pipeline. Tell the user the pipeline is
ready and the trial is out of credits, with the run link and the credits
used.

**A job restarted after its agent disappeared**, seen in builds of about 40
minutes on hosted agents. TeamCity restarts it with no visible cap. Stop
after the second identical loss: cancel the run, report it, shorten the job
before another run.

**A failure before checkout** with `Repository not found`, authentication
failed, 401, or 404, on a private repository whose root has no stored
credential: a VCS credential blocker. A passing VCS connection test does not
change this. Report the run number and link, the root ID, and the repository URL, and
write a [manual prerequisite](manual-prerequisites.md) for the repository
App or a project-scoped connection. Do not invent a personal access token.

**A test that fails on its own**, in every run with no TeamCity cause in the
log: a repository failure. Report the test, the assertion, and the run number and link,
and stop. A job that failed only through its dependency needs no diagnosis.

**Anything else**: only the pipeline YAML path applies. `pipeline pull` the
stored YAML into your working file outside the repository, correct it,
validate, push, requeue. Code fixes are out of scope. When `run log` is
denied, read `run view <id>` and `run tests <id> --failed`; the `Status`
line shows in `run view`.

One correction per run; an unchanged retry is wasted. Stop after three
corrections. A successful child does not make a failed head green. When the
evidence does not show one cause, report the likely causes, the
evidence, and the next small check.
