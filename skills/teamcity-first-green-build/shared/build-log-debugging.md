# Build Log Debugging

Use TeamCity build status, problems, tests, changes, and logs to move from
symptoms to the smallest useful fix.

## Debugging Order

1. Get the build overview: status, status text, branch, build type, build
   environment, and whether the build failed to start.
2. Check build problems with details and log anchors.
3. Check failed tests with details and log anchors.
4. Read a focused error view of the log.
5. Use log anchors to read a small window before and after the failure.
6. Check recent changes and compare with the last successful build when
   available.
7. Decide whether the fix belongs in project code, build configuration,
   pipeline definition, parameters, credentials, or build environment
   requirements.

## Log Reading Rules

- Start narrow. Use `filter=errors` before reading large log ranges.
- Use pagination. Do not request huge logs in one call.
- If a log anchor is available, start slightly before it to capture context.
- Distinguish test failures from build step failures, failed-to-start builds,
  canceled builds, and dependency-chain failures.
- For private repositories, treat pre-checkout errors like `Repository not
  found`, authentication failed, 401, or 404 as VCS credential blockers when the
  VCS root lacks durable build-time credentials. A successful VCS connection
  test does not override an actual build-time change-collection failure.
- Do not hide uncertainty. If the logs do not identify a single cause, state
  the likely causes and the next verification step.

## Live-Agent Diagnostics

An agent process can redirect its own structured output to an artifact, so a
running TeamCity step with no new visible log line does not by itself prove it
is hung. First use normal build metadata, queue state, build problems, tests,
and artifacts. Do not read agent workspaces or trajectories unless that is
needed and allowed by the task's data handling rules.

If the diagnostic command `teamcity agent exec <agent-id> <read-only-command>`
returns HTTP 403, treat it as an optional-diagnostics permission gap, not as a
build failure and not as authorization to broaden the current token. Continue
to monitor through normal build APIs. If live runtime inspection is necessary,
give the project administrator this bounded handoff:

1. On the confirmed TeamCity server, open **Project Settings → Permissions**
   for the target project and grant the permission required by the **Agent
   Terminal** plugin / agent command execution to a diagnostic role only.
2. Limit that role to the target project and the current diagnostic user; it
   does not need global project-administration or token-management rights.
3. Verify the scope with one benign read-only command, such as `teamcity agent
   exec <agent-id> "echo agent-terminal-ok"`.
4. Revoke the temporary diagnostic grant when the investigation is complete,
   or return the permitted build log and artifact metadata to continue without
   granting terminal access.
