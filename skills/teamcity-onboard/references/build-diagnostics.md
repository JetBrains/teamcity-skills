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

For a run that stays queued after two observations or 60--120 seconds, stop
waiting and read the run and queue details, including the specific wait reason.
If the request already reports that duration, treat the threshold as reached:
run these checks before another status poll.
Then:

1. List enabled, authorized agents and applicable cloud images or hosted
   selectors.
2. Query the job against candidate agents so TeamCity reports unmet
   requirements, missing versions, pool restrictions, or unresolved
   parameters.
3. Pull the server-stored Pipeline YAML and verify that every `%name%`
   substitution is declared or inherited.

Perform these checks immediately when the reason says **no compatible agents**
or **unresolved parameters**. Treat **no idle compatible agents** as ambiguous
until the job result distinguishes busy capacity from zero compatible agents.
If an unmet `os-family teamcity.agent.jvm.os.family equals Linux` requirement
uses a key absent from the candidate agent, replace it with an observed,
relevant parameter; changing the value's case cannot make the key exist.

For an unresolved host-JDK parameter such as `env.JDK_25`, report a
pre-dispatch blocker. A build step cannot download JDK 25 because it has not
started. For a Linux container-safe job, replace the host-JDK requirement with
Docker capability and run the job in a pinned JDK 25 image. Native work needs
an agent or image that already provides JDK 25.

If the evidence proves zero compatible agents or images, stop polling. Do not
queue a duplicate or retry unchanged. Make at most one correction directly
supported by the evidence, validate it, and retry only after the compatibility
result changes. If the evidence does not prove a stable blocker, continue
monitoring the accepted run at a maximum 60-second interval for at least ten
minutes from queueing and report progress at least once a minute.

If a compatibility operation returns `permission_denied`, record compatibility
as unverified. Do not infer it from a generic wait reason, agent inventory, or
manual UI confirmation. Use another permitted machine-readable TeamCity
operation when available; otherwise report the missing permission as the
blocker.

## Diagnose Branch And VCS Access Failures

For `invalid_branch_name`, or when TeamCity substitutes default-branch
revisions, inspect the VCS roots attached to the pipeline, their default
branches and branch specifications, and the mapping from the requested Git
branch to TeamCity's logical branch. The usual cause is naming the default
branch explicitly (`--branch main`) when the specification does not list it;
queue the default branch without `--branch`. A red head with this problem and
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
