# Build Diagnostics (Draft)

This guide investigates an existing TeamCity run. It does not create or
redesign CI configuration.

Use this guide with the `teamcity-cli` skill, loaded at the start of the
onboarding. It supplies the command syntax and the basic failure workflow;
this guide supplies the investigation order, special cases, and boundaries for
optional live-agent access. Do not duplicate or replace its command reference.

## Work With `teamcity-cli`

Read its "Investigate a build failure" workflow first for:

- locating the failed run and reading its overview, logs, tests, and changes;
- finding the deepest failing build in a dependency chain;
- separating a transient failure from a persistent code, configuration, or
  server problem.

Then use this guide to interpret that evidence. If the workflow's command
syntax conflicts with remembered syntax, the `teamcity-cli` reference wins.
Use a matching first-class CLI or MCP operation; do not bypass a missing
capability with direct TeamCity REST calls.

## Investigation Order

Establish the build overview: status, status text, branch, build type, build
environment, selected agent, and whether the build failed to start. Then work
from the most structured evidence to the least:

1. Build problems, including their details and log anchors.
2. Failed tests, including their details and log anchors.
3. A focused error view of the log.
4. A small log window before and after each useful anchor.
5. Recent changes and, when useful, the last successful build.

Decide whether the evidence places the correction in project code, build
configuration, pipeline definition, parameters, credentials, or build-agent
requirements. If the evidence does not establish one cause, report the likely
causes and the next bounded check rather than guessing.

## Investigate The Pipeline Head

An unsuccessful pipeline head needs an explanation even if every child job
succeeded. With the TeamCity CLI, read its structured failure summary:

```bash
TEAMCITY_URL=<confirmed-server> teamcity run log <head-id> --failed --json
```

Inspect the `problems` array. Missing `problemOccurrences` in `run view --json`
does not mean that no failure evidence exists. For `invalid_branch_name`,
inspect the requested branch and attached VCS roots before changing build steps
or application code.

Report the head ID, problem type, concise cause, and supporting evidence. A
pipeline is successful only when the head and all required jobs finish
successfully on the intended sources.

## Read Logs Carefully

- Start narrow: use an error filter before reading large log ranges.
- Paginate instead of requesting a huge log in one call.
- When an anchor is available, read slightly before it for context.
- Distinguish test failures from build-step failures, failed-to-start builds,
  cancelled builds, and dependency-chain failures.
- For private repositories, treat pre-checkout `Repository not found`,
  authentication failed, 401, and 404 errors as VCS credential blockers when
  the VCS root lacks durable build-time credentials. A successful VCS
  connection test does not override an actual build-time change-collection
  failure.

## Diagnose A Build That Remains Queued

After two observations or 120 seconds in the queue, find the runnable queued
job in the chain (a waiting head is not the cause) and read its wait reason.
Then, before another poll:

1. List the enabled, authorized agents in the target pool and the applicable
   cloud images or hosted selectors.
2. Check the exact job against each candidate with
   `teamcity agent jobs <agent-id> --incompatible --json`, or with an MCP
   Pipeline compatibility check when one exists. Count compatible candidates
   and group the unmet requirements and unresolved parameters. Do not infer
   compatibility from an agent's name or from the queue message.
3. Pull the stored Pipeline YAML and match its `runs-on` requirements and
   every `%name%` substitution to the reported reasons.

Treat **no idle compatible agents** like **no compatible agents**: it does not
distinguish busy capacity from zero matches. A generated job absent from both
CLI lists, or a `permission_denied` on the check, is unverified, not
compatible; see "Check compatibility before queueing" in
[Agents, JDK, and compatibility](agents-and-jdk.md).

Typical causes: a requirement key no agent has (`os-family`), an architecture
label that differs from the agent's `teamcity.agent.jvm.os.arch` value
(`x86_64` versus `amd64`), or an unresolved host-JDK parameter such as
`env.JDK_25`, which no build step can install because the build never
starts; run such a job in a pinned JDK container instead.

Make at most one correction the evidence supports, validate, and requeue; no
duplicate runs and no unchanged retries. Without a proven blocker, keep
watching the accepted run at most every 60 seconds and report progress.

## When The Log Is Not Readable

A denied `run log` or `run download` is not a reason to create a probe
pipeline. Read `run view <id>`, `run tests <id> --failed`, and
`run log <head-id> --failed --json`; for the rest, add a first script step to
the deliverable job that prints `"$JAVA_HOME/bin/java" -version` and ends with
a `##teamcity[buildStatus ...]` message, which `run view` shows.

## Diagnose Branch And VCS Access Failures

For `invalid_branch_name`, or when TeamCity substitutes default-branch
revisions, inspect the VCS roots attached to the pipeline, their default
branches and branch specifications, and the mapping from the requested Git
branch to TeamCity's logical branch. The usual cause is naming the default
branch explicitly (`--branch main`) when the specification does not list it;
queue with the logical `--branch '<default>'`, particularly when pinning a
revision. A red head with this problem and
green jobs is a branch binding error, not a step failure, and is not a green
build. Do not switch to `main`/`master` or widen
branch filters merely to suppress the error. Retry only after correcting a
demonstrated mismatch.

If TeamCity reports `Build was detected as untrusted` because the pull request
feature was not set, inspect the Pipeline's **Repository → Pull requests**
setting. A branch specification or **On New Changes → Pull requests** trigger
is not a substitute.
Configure the repository's PR handling through a supported operation or the
Pipeline UI, verify the saved setting, then retry the PR build.

For a private repository, treat build-time change collection as a separate
test from a VCS-root connection test. Stop with a VCS credential blocker when
all of the following are true:

- a build fails before checkout or change collection with `Repository not
  found`, authentication failed, 401, or 404;
- the VCS root has no durable build-time credential; and
- a supported personal build or uploaded patch fails the same way or still
  requires TeamCity to read the private base repository.

Report the failing build ID, VCS root ID, repository URL, and the needed repair:
install or authorize the repository App, attach a project-scoped service
connection, or configure an approved service SSH key or token in the VCS root.
Do not invent a personal access token as a workaround.

### Explicit PAT Fallback

Use a GitHub personal access token only when the user explicitly chooses that
test instead of an App-backed credential. In the existing target-project VCS
root, choose **Password / personal access token**, set the username to
`x-access-token`, and enter the token only in the protected password field.
For a fine-grained token, select the target repository and grant read-only
contents access; for a classic token, grant repository-read scope. Complete any
required organization SSO authorization, then run the root's connection test.

If the test succeeds, replace the personal credential with a least-privilege
App or service credential when one is available. If TeamCity says that the
root failed to authorize with the selected token, inspect the existing
refreshable-token reference, its connection, project scope, and repository
scope. Repair that reference in place and run the connection test again; do
not create a duplicate root or paste a static token into a command or chat.

## Optional Live-Agent Inspection

A running step with no new visible log line is not by itself evidence that the
agent is hung: the process may be writing structured output to an artifact.
Before requesting terminal access, use build metadata, queue state, problems,
tests, logs, and artifacts.

If a read-only `teamcity agent exec <agent-id> <command>` request returns HTTP
403, treat it as a missing optional diagnostic permission, not as a build
failure and not as permission to broaden the current token. Continue with the
normal build information.

When live inspection is necessary, grant the diagnostic user a temporary,
project-scoped Agent Terminal permission through the available TeamCity
surface. It must not require global project-administration or token-management
rights. Verify it with one harmless read-only command and remove the temporary
permission when the investigation is complete. If the current credentials
cannot manage that project permission, report that exact access blocker and
continue with the available build information.

## Report The Next Step

State the concrete cause or unresolved alternatives, the evidence, and the
smallest safe next action. For a configuration or infrastructure blocker,
identify the owner, the required change, and the proof needed before retrying.
