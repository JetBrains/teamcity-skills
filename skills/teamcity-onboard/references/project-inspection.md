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

## Inspect GitHub Actions Workflows

When `.github/workflows/` exists, read every workflow before you design the
pipeline. The workflows record the exact commands, tool versions, secrets,
services, and job order the team already trusts. Reuse that knowledge.

For each workflow, record:

- Triggers under `on:`: push, pull request, schedule, manual dispatch, tags.
- Jobs, their `needs:` graph, and their `runs-on` operating systems.
- Each step: shell commands under `run:`, actions under `uses:` with their
  inputs, working directories, and conditions under `if:`.
- Matrix strategies and which combinations matter.
- Secrets, environment variables, services, containers, caches, and uploaded
  or downloaded artifacts.
- Reusable workflows and composite actions the workflow calls, and workflows
  that call this one.

### Choose The Workflow To Reuse

Migrate one workflow first. A small green pipeline proves more than a large
red one. Add the rest after the first build is green.

- One workflow: use it.
- Several workflows, one of them a classic build, test, and publish or package
  flow that runs on push or pull request: use that one by default and say why.
- Several workflows, none classic: propose one and give the reason. Prefer a
  workflow that other workflows call or depend on, that runs most often, or
  that suits TeamCity best because it has a real build, tests, artifacts, and
  a job graph that becomes a chain.
- No workflows: design the pipeline from the local inspection alone.

Skip workflows that are specific to GitHub, and list them in the report:
CodeQL and other security scanning actions, Dependabot, GitHub Pages
deployment, release-only or tag-only workflows, and labeler or stale bots.

### Translate The Workflow Into A Pipeline

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
verification build must not change anything outside TeamCity. Report them as
follow-up work.

Read [Build-step selection](build-step-selection.md) to choose the runner for
each translated step and to add meaningful build status. The TeamCity side
of the inspection, including existing pipelines for the same repository, is
in [Discover and connect](discover-and-connect.md).
