# Project inspection

Inspect the project before you write YAML, so the first pipeline is small,
follows the project's conventions, and is likely to build. The workflow
shows how the team builds; the build files are the truth when they differ.

## 1. Choose one workflow

`.github/workflows/` shows the commands, tool versions, services, and job
order the team trusts. Choose one workflow: the one that builds and tests the
code on push or pull request. It is a guideline, not a spec to copy. Without
workflows, go to [Read the repository](#2-read-the-repository) and build the
pipeline from the build files: build, test, package.

Take from it:

- the commands under `run:` and the tool versions from `setup-*` steps;
- `services:` and `container:` the tests need;
- the artifacts it uploads;
- the `needs:` order between the jobs;
- hand-made test sharding (`partition.sh`, `shard: [1..N]`): a sign of a
  big suite.

## 2. Read the repository

Record:

- the root and the primary modules; languages and frameworks;
- build files: `build.gradle(.kts)`, `pom.xml`, `package.json`,
  `pnpm-lock.yaml`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `.sln`,
  `Dockerfile`, `docker-compose.yml`;
- the required JDK or runtime, from build files, `setup-*` steps, and the
  README;
- test commands, test report paths, and the packaged output;
- services, environment variables, and credentials the build and tests
  need;
- checked-in TeamCity YAML or Kotlin DSL. If CI already exists – reuse it.

Verify every command from the workflow against the build files.
**Do not run** `teamcity migrate`: it converts the whole workflow, and this skill onboards
build, test, and package only.

## 3. Read GitHub run history when you can

When the `gh` CLI is logged in, real GitHub Actions runs give job durations
and whether this revision is green there. Use them for the time estimate,
for "red caused by the project", and for the speed comparison in the report.
Never block on it, never ask for a token.

## 4. Decide the scope

Leave for follow-ups: deploy, publish, and release jobs; tag-only, scheduled,
and release-only workflows; CodeQL and other GitHub-specific actions; matrix
entries beyond the [version matrix rule](#version-matrix); any job that
needs a secret; `on:` triggers, `if:` conditions, `concurrency:`,
notifications.

A job that runs only on path filters (`paths:`, a `detect-changes` job,
`dorny/paths-filter`) stays when it builds or tests: drop the filter and run
the job every time.

A suite is too big for the first run when the workflow shards it by hand or
it does not fit the time budget. Run a fast subset, for example without
integration tests, and offer the full suite as a follow-up. In Maven, define
it as [Build-step selection](build-step-selection.md#maven) says.

### Version matrix

When the workflow tests several runtime versions (JDK, .NET, Node), run the
test job once per version, in parallel, for up to 4 versions the agents
have, on Linux. Each version costs one more agent: for a long test job, run
the default version only. The rest of the matrix is a follow-up.

## 5. Translate what you keep

| GitHub Actions | TeamCity |
| --- | --- |
| `jobs.<id>` and `needs:` | Jobs and `dependencies:` |
| `runs-on: ubuntu-*` | A `runs-on` value from this server; see [Agents and runtimes](agents-and-runtimes.md) |
| `run:` | The matching dedicated runner; a script step when the schema has none |
| `env:` | Job or pipeline `parameters:` with the `env.` prefix |
| `actions/checkout` | Nothing. Checkout is automatic |
| `actions/setup-java`, `setup-node`, and similar | Nothing, or an explicit runtime selection when the version matters |
| `actions/cache`, `gradle/actions/setup-gradle` | Nothing. The first build runs without a cache. `enable-dependency-cache` does nothing |
| `actions/upload-artifact`, `download-artifact` | `files-publication` on the producer, `files:` on the consumer's dependency; see [Pipeline features](pipeline-features.md#artifacts) |
| `strategy.matrix` | See [Version matrix](#version-matrix) |
| `services:` and `container:` | A step-level container image, or Docker Compose in a script |
| Other `uses:` actions | The shell commands from the action's `action.yml` |
