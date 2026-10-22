# Project inspection

Inspect the project before you write CI, so the first pipeline is small,
follows the project's conventions, and is likely to build. Trust the build
files first.

## Read the repository

Record:

- the root and the primary modules; languages and frameworks;
- build files: `build.gradle(.kts)`, `pom.xml`, `package.json`,
  `pnpm-lock.yaml`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `.sln`,
  `Dockerfile`, `docker-compose.yml`;
- the required JDK or runtime, from build files, `setup-*` steps, and the
  README;
- test commands, test report paths, and the packaged output;
- services, environment variables, and credentials the build and tests
  cannot do without;
- checked-in TeamCity YAML or Kotlin DSL. CI already exists; reuse it.

Verify every command from a workflow against the build files. Do not run
`teamcity migrate`: it converts the whole workflow, and this skill builds the
basic build only.

## Read GitHub Actions as a signal

`.github/workflows/` shows the commands, tool versions, services, and job
order the team trusts. It is one signal next to the build files and the
README. The first pipeline is the basic build.

Take from it:

- the commands under `run:` and the tool versions from `setup-*` steps;
- `services:` and `container:` a test cannot run without;
- the artifacts it uploads;
- the `needs:` order between the kept jobs;

Leave for follow-ups: deploy, publish, and release jobs; tag-only, scheduled,
and release-only workflows; CodeQL and other GitHub-specific actions; matrix
combinations beyond the first Linux one; any job that needs a secret; `on:`
triggers, `if:` conditions, `concurrency:`, notifications.

## Translate what you keep

| GitHub Actions | TeamCity |
| --- | --- |
| `jobs.<id>` and `needs:` | Jobs and `dependencies:` |
| `runs-on: ubuntu-*` | A `runs-on` value from this server; see [Agents and JDK](agents-and-jdk.md) |
| `run:` | The matching dedicated runner; a script step when the schema has none |
| `env:` | Job or pipeline `parameters:` with the `env.` prefix |
| `actions/checkout` | Nothing. Checkout is automatic |
| `actions/setup-java`, `setup-node`, and similar | Nothing, or an explicit runtime selection when the version matters |
| `actions/cache`, `gradle/actions/setup-gradle` | Nothing. The first build runs without a cache |
| `actions/upload-artifact`, `download-artifact` | `files-publication` on the producer, shared with dependent jobs |
| `strategy.matrix` | One job for the first Linux combination |
| `services:` and `container:` | A step-level container image, or Docker Compose in a script |
| Other `uses:` actions | The shell commands from the action's `action.yml` |
