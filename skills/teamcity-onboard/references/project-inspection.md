# Project Inspection

Before you create or change TeamCity CI, inspect the project so the first
configuration is small, follows the project's conventions, and is likely to
build. Trust the build files first. Existing CI shows how the team already
runs them.

## Inspect Locally

Identify:

- Repository root and primary modules.
- Languages and frameworks.
- Build files such as `build.gradle`, `build.gradle.kts`, `pom.xml`,
  `package.json`, `pnpm-lock.yaml`, `pyproject.toml`, `go.mod`, `Cargo.toml`,
  `.sln`, `Dockerfile`, and `docker-compose.yml`.
- Existing CI files: `.github/workflows/`, checked-in TeamCity YAML or Kotlin
  DSL, and other CI definitions.
- Test commands and artifact outputs.
- Required services, environment variables, caches, and credentials.

## Read GitHub Actions As A Signal

When `.github/workflows/` exists, read it for the commands, tool versions,
services, and job order the team already trusts. It is a signal next to the
build files and the README, not the source to translate. The first pipeline
is the basic build, not the workflow.

Take from it:

- the commands under `run:`, and the tool versions from `setup-*` steps;
- `services:` and `container:` a test cannot run without;
- the artifacts it uploads;
- the `needs:` order between the kept jobs.

Leave for follow-ups: deploy, publish, and release jobs; tag-only, scheduled,
and release-only workflows; CodeQL and other GitHub-specific actions; matrix
combinations beyond the first Linux one; and any job that needs a secret.

### Translate What You Keep

Keep the job graph, the shell commands, the tool versions, and the artifact
paths. Replace what GitHub provides with the TeamCity equivalent. TeamCity
does not run GitHub Actions.

| GitHub Actions | TeamCity |
| --- | --- |
| `jobs.<id>` and `needs:` | Pipeline jobs and `dependencies:` |
| `runs-on: ubuntu-*`, `macos-*`, `windows-*` | A `runs-on` selector observed on the target server |
| `run:` | The matching dedicated runner, or a script step for glue |
| `env:` | Job or pipeline `parameters:` with the `env.` prefix |
| `${{ secrets.X }}` | A `secrets:` reference to a stored TeamCity credential |
| `actions/checkout` | Nothing; checkout is automatic |
| `actions/setup-java`, `setup-node`, and similar | Nothing, or an explicit runtime selection when the version matters |
| `actions/cache`, `gradle/actions/setup-gradle` | Nothing; TeamCity manages dependency caches |
| `actions/upload-artifact` and `download-artifact` | `files-publication` on the producer, shared with dependent jobs |
| `strategy.matrix` | One job per kept combination, Linux first |
| `services:` and `container:` | A step-level container image, or Docker Compose in a script |
| Other `uses:` actions | The shell commands from the action's `action.yml` |

Some workflow settings have no place in Pipeline YAML. Record them as manual
follow-up: `on:` triggers and branch filters, `if:` conditions,
`concurrency:`, `timeout-minutes:`, and notifications.

Leave deploy, publish, and release steps out of the first pipeline. A first
verification build must not change anything outside TeamCity. Offer them as
follow-ups in the report.

Read [Build-step selection](build-step-selection.md) to choose the runner for
each translated step and to add meaningful build status. The TeamCity side
of the inspection, including existing pipelines for the same repository, is
in [Discover and connect](discover-and-connect.md).
