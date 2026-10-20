# Show the value

Set up every feature below that applies. Tell the user about each in one
short line: what they get and where to look. Only features you saw working.
The dependency cache and the execution timeouts are behind server toggles.

| Feature | What to tell the user | Where to look |
| --- | --- | --- |
| Typed build steps (Maven, Gradle, Node.js) | Tools set up and tests reported, no scripts to maintain | The job's steps |
| On-the-fly test reporting | Tests appear while the build runs: "3,000 tests passed so far" | The run's Tests tab |
| Build chains and files between jobs | Build once, use the output in several jobs | The run's chain |
| Parallel tests | The suite split over agents, from the second run on | The test job's batches |
| Remote run | "Nothing is committed to your repo", said every time | The run page |
| Job reuse | On a no-change rerun, the time saved: "13 min became 5 s" | The rerun's reused jobs |
| Performance monitor | Agent-size advice: "E2E peaked at 11 GB, Large is right; Build would fit Medium" | The job's Performance Monitor tab |
| Service messages | Readable statuses and progress: "e2e on Redis + ES8: 181 passed" | The builds list |
| Custom report tab | The HTML report | The tab's link |
| Flaky test detection, agent terminal | For a test that flips or a job that needs debugging | The test's history, the agent page |
| Registry integration | A next step; it needs credentials | |

## The value summary

End the report with four lines from measured numbers: what ran; how many
tests are visible; what TeamCity did that GitHub Actions did not; the time
saved.
