# Discover and connect

Read [TeamCity tool policy](../shared/teamcity-tool-policy.md) first. This
workflow establishes the target, repository facts, and VCS access.

## Identify the target

Resolve the TeamCity server and named parent project before discovery or
writes. `_Root` is never the target parent.

Resolve a supplied project name to an ID after connecting. Ask only when no
project or several projects match. Confirm the authenticated identity and server
before continuing. For the CLI:

```bash
TEAMCITY_URL=<server> teamcity auth status
```

The saved CLI default cannot select the target. Keep tokens, keys, passwords,
and authorization headers out of commands, logs, configuration, and reports.

## Inspect the repository

Find the smallest build and test commands that prove the project works. Record:

- required JDK or runtime from build files and repository documentation;
- test reports, coverage reports, and artifacts;
- required services, caches, environment variables, and credentials; and
- checked-in CI, TeamCity YAML, or Kotlin DSL.

Read [KMP and mobile](../shared/kmp-mobile.md) for Kotlin Multiplatform,
Compose, Android, or iOS. Treat `./gradlew --no-daemon clean test build` only
as a candidate command; verify it against the repository.

## Inspect TeamCity

On the confirmed server, inspect the parent project and inherited settings,
existing pipelines and VCS roots, connections, agents or images, and Pipeline
schema. Reuse a matching configuration when possible.

List connections through the parent chain to `_Root`; a child-project listing
can omit inherited connections. Record each connection ID and owner project.
For an existing pipeline, inspect its VCS-root attachment. A visible project
root does not prove that the pipeline uses it.

When GitHub Actions exist without matching TeamCity CI, run
`teamcity migrate --from github-actions`, then review its output and manual
setup before using it.

## Use Remote Run only as a VCS fallback

For an IDE-led KMP flow with a local clone, use Remote Run when available. It
provides early evidence; durable CI still needs a VCS root.

For a private repository that TeamCity cannot read, use an exposed Remote Run
or patch-based personal build. The CLI fallback is:

```bash
TEAMCITY_URL=<server> teamcity run start <job-id> --branch <branch> \
  --local-changes=git --no-push --personal
```

For missing custom-patch permission, use
[Manual prerequisites](../shared/manual-prerequisites.md). For failed change
collection, read [Build diagnostics](../shared/build-diagnostics.md).

## Establish VCS access

Read [VCS connections and authentication](../shared/vcs-connections-and-auth.md).

- Reuse an existing project or inherited connection.
- For GitHub, use an App-backed connection and root. Use PAT/password auth only
  when the user explicitly accepts it.
- Use a service account, robot user, or managed connection for registries.
- Inspect each VCS root before using it. Do not guess its ID.
- Attach the selected root before pushing configuration or queueing a run.

Before queueing, inspect the attached roots' default branches and branch
specifications. Map the requested Git branch to the accepted TeamCity value.
Do not switch to `main`/`master` or widen a branch filter only to hide an error.
