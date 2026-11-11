# Show the value

Set up or show every feature below that applies. Tell the user about each in
one short line, at the moment it happens: what they get and where to look.
Only features you saw working.

| Feature | When | What to tell the user | Where to look |
| --- | --- | --- | --- |
| Remote run | A remote run starts | "Your local changes run on TeamCity; nothing is committed or pushed" | The run page |
| Build chains and files between jobs | Jobs fan out | "N jobs on N agents in parallel; build once, use the output in several jobs" | The run's chain |
| Build artifact | The run finishes | The built app or package, downloadable from every run: "app.zip, 4 MB" | The run's Artifacts tab, `run download <id>` |
| Typed build steps (Maven, Gradle, Node.js) | A job starts | Tools set up and tests reported, no scripts to maintain | The job's steps |
| Version matrix | The version jobs start | "Your tests on JDK 17, 21, and 25 at once" | The run's chain |
| On-the-fly test reporting | The first tests arrive | Tests appear while the build runs: "3,000 tests passed so far" | The run's Tests tab |
| Service messages | A job runs | Readable statuses and progress: "e2e on Redis + ES8: 181 passed" | The builds list |
| Custom report tab | The run finishes | The project's own report | The tab's link |
| Performance monitor | The run finishes | Agent-size advice from the peak: "E2E peaked at 11 GB, Large is right; Build would fit Medium" | The job's Performance Monitor tab |
| Job reuse | A rerun after a fix on an ordinary run, not a remote run | The jobs not run again and the time saved: "Build and Test reused, 40 s instead of 3 min" | The rerun's reused jobs |
| Flaky test detection | A test fails, then passes, on two ordinary runs of the default branch. Remote runs do not count | TeamCity marked it flaky; its history shows the flips; muting is the user's choice | The test's history |
| Agent terminal | A job needs debugging | Open a terminal on the agent | The agent page |
| Registry integration | The report | A next step; it needs credentials | |

Also name, in one line each, when they apply:

- what TeamCity shows that GitHub Actions hides: a failure, a test, or a
  check the workflow skips or does not report;
- the `free-disk-space` job feature, when the workflow frees disk space by
  hand (`sudo rm -rf`);
- a build cache shared between jobs: compiled once, 0 recompiles;
- `buildStatisticValue`: charts of the project's own numbers.

The performance data is also in the hidden artifact
`.teamcity/perfmon/perfmon.csv`. Resize from the peak, not ahead of it.
Test reporting, artifacts, and the report tab are set up as
[Pipeline features](pipeline-features.md) describes.

## Job reuse

Never queue a rerun with no change only to show reuse: it finishes in a
second, looks like a real run in the list, and confuses the user. Show reuse
only on a rerun after a fix, on the jobs that were green on the previous
ordinary run.

A red job is never reused, and neither is a personal build: after a remote
run, there is no reuse to show; name job reuse as a follow-up that shows
once the changes are pushed. When the first ordinary run is green, there is
no rerun either: name job reuse as a follow-up too.

Read the time saved from
`teamcity api '/app/pipeline/<pipeline-id>/<head-build-id>/optimizations'`:
the entry `{"name": "reusedJobs", "type": "duration", "value": <seconds>}`
in the `appliedOptimizations` array. An empty array means no job was reused.
Name the reused jobs and the time saved in one line. A change to `runs-on`
alone keeps the reuse; to measure again, change a step.

## Follow-ups

**Parallel tests.** Not part of the first pipeline. TeamCity splits tests
only after one finished run of the job. Each batch is a separate job with
its own agent, setup, and cost, so on a job with few or short tests the gain
is zero or negative. Offer it for a job where long tests take most of the
time; a workflow that already splits its tests is a good sign. After the
split, say the measured gain and the extra cost.

**The rest of the matrix.** The versions, OS entries, and axes the first
pipeline left out, as
[Project inspection](project-inspection.md#version-matrix) describes.

## The value summary

End the report with five lines from measured numbers: what ran; how many
tests are visible; what TeamCity did that GitHub Actions did not; the time
saved; the credits used. Compare speed with GitHub Actions only when its
durations are known. On Medium agents TeamCity can be slower: do not claim
it is faster without numbers.
