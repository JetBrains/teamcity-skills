# First Green Build

Use this workflow to create, reuse, or repair TeamCity CI for a repository and
iterate until the first successful verification build or a proven external
blocker.

## Goal

Get one green TeamCity build for the repository with the smallest useful
pipeline, or stop with clear evidence that something outside the CI definition
blocks progress.

Do not claim success after only creating a project, creating a pipeline, or
queueing a build.

## Tool Policy

- Use a specific TeamCity tool surface selected by the current environment.
  Adapters should map this workflow to the concrete tools available in their
  environment.
- Apply a first-class CLI gate before any TeamCity shell command when the
  `teamcity` CLI is available:
  1. Check `teamcity --version` and the relevant `<area> --help` output.
  2. Use the matching first-class command for the whole operation. In
     particular, use `teamcity project`, `teamcity project connection`,
     `teamcity vcs-root`, `teamcity pipeline`, `teamcity job`, `teamcity run`,
     and `teamcity agent` for those objects. Use `teamcity agent list`, `view`,
     and `jobs` for agent discovery and compatibility; use `teamcity job list`
     or `view` for build configurations; use `teamcity pipeline validate` for
     Pipeline YAML.
  3. If the first-class command lacks a required capability, inventory the MCP
     tools exposed in the current environment. Read the relevant MCP guide and
     tool schema, confirm the connection targets the requested TeamCity server,
     and use a matching dedicated operation. If only a generic MCP read tool is
     exposed, use it only when its schema explicitly permits the exact narrow
     read. Never infer its allowlist from another TeamCity server.
  4. If no matching MCP operation exists, stop that operation and give the
     concrete manual completion checklist from step 12.
  5. Before reporting completion, audit the TeamCity-related tool calls made
     during the task. If a forbidden fallback was used, treat the run as
     non-compliant and do not claim success. A later compliant call does not
     erase the forbidden call.
- Prefer TeamCity CLI for configuration writes and a matching TeamCity MCP
  connection for read-only discovery, logs, and personal-build queueing when
  it exposes those operations. Read `shared/vcs-connections-and-auth.md`
  before using either surface for project connections or VCS roots.
- Confirm the exact TeamCity server before discovery or writes.
- If a callable tool, connection, or configured context points at a different
  TeamCity server, abort discovery and fix the attachment or login first.
- Whenever YAML or Kotlin DSL with TeamCity configuration are generated or modified,
  always perform a validation of it (See "Validate Configuration" step),
  before starting a run in TeamCity.
- Follow `SKILL.md` to resolve the TeamCity server and named target parent.
- Keep a small in-memory cache of server facts learned during the task. Reuse
  it while the target server, parent project, repository, and TeamCity object
  have not changed.
- Do not use plain REST with `curl`, ad hoc scripts, or generic REST escape
  hatches unless the user explicitly asks for that path, except for the direct
  patch-upload fallback in step 5.
- After authenticating to a TeamCity server, discover its version and the
  capabilities exposed by the selected TeamCity surface.
- Before queueing a build, validate every generated or modified TeamCity YAML
  or Kotlin DSL configuration with the strongest validator available for that
  format (see the "Validate Configuration" step). A syntax-only YAML parse
  does not establish that TeamCity can use the configuration.
- Whenever a pipeline, build step, or build script is generated or modified, it
  must report meaningful live status through TeamCity service messages (See
  "Report Meaningful Build Status" in step 7).
- At the start of every run, ask for or confirm the TeamCity server and target
  project before repository inspection, TeamCity discovery, or writes.
- This confirmation must be obvious in the assistant's first response for the
  task. Do not continue based on prior context, tool names, environment
  variables, command history, repository files, or cached assumptions.

## Recommended Workflow

### 1. Identify TeamCity Server And Project

Resolve these values before TeamCity discovery or writes:

- TeamCity server name or URL.
- Named target parent project name or ID.

Use the target-selection rule in `SKILL.md`; it never selects `_Root`.

If the user provides a project name rather than an ID, resolve it to a concrete
TeamCity project ID after connecting. Report the resolved ID and continue; ask
only when zero or multiple candidate projects match.

Also discover:

- Authentication path. Try OAuth or existing interactive authentication first
  when the selected TeamCity surface supports it. Ask for a TeamCity token only
  when no safer existing authentication path is available.
- Whether a matching TeamCity object should be reused or a new named pipeline
  created.
- Repository URL and default branch.

Handle tokens safely:

- Ask for tokens only in a secret-safe channel when available.
- Never print tokens, private keys, passwords, or authorization headers.
- Do not store tokens as plain TeamCity project parameters.

### 2. Inspect The Repository

Identify the smallest command set that should prove the project works:

- Build command.
- Test command.
- Required Java/JDK version, especially for Gradle or Maven projects. Read
  build configuration, version files, repository setup documentation, and
  existing CI together. If the repository declares an exact version but the
  build tool does not enforce it, the pipeline must still select and later
  verify that version; a successful build on an older agent default is not
  equivalent.
- Test reports, coverage reports, and other artifact paths.
- Docker image build, push, compose, or container validation steps, if present.
- Required services, caches, environment variables, and credentials.
- Existing CI files and checked-in TeamCity YAML or Kotlin DSL.

For Kotlin Multiplatform, Compose Multiplatform, Android, or iOS projects,
also read `shared/kmp-mobile.md`. When the repository declares mobile targets,
the first useful pipeline must build those targets, not only a JVM module.

For Gradle/JVM projects, a common starting point is:

```bash
./gradlew --no-daemon clean test build
```

Verify this against the repository before using it. Do not assume it is correct.

### 3. Connect To TeamCity

Authenticate against the confirmed TeamCity server using the selected TeamCity
surface.

Preferred order:

1. Existing authenticated session for the confirmed server.
2. OAuth or interactive authentication, if supported by the tool surface.
3. TeamCity token supplied safely by the user.

Before continuing, verify the authenticated identity and server. If the tool is
attached to another server, stop and repair the connection before discovery.

With TeamCity CLI, check the server-specific session with
`TEAMCITY_URL=<server> teamcity auth status`. If it is missing or expired, use
`teamcity auth login --server <server>` and request only the permissions needed
for the planned operation. Never let the CLI's persisted default server choose
the target implicitly.

### 4. Discover TeamCity State

Discover state only against the confirmed target server:

- Parent project details and inherited settings.
- Existing pipelines and build configurations.
- VCS roots and branch specifications.
- Project connections and inherited connections.
- Project features that may affect checkout, commit status publishing, Docker,
  or credentials.
- Recent failures and last successful baseline builds for related objects.
- Available build agents, cloud images, compatible environments, and pipeline
  capabilities. Query those from the target server before choosing `runs-on`.
- TeamCity version, Pipelines YAML schema/version, and support for pipeline
  validation, VCS roots, Remote Run, and agent compatibility discovery.

Avoid duplicate CI. Prefer reusing or updating an existing object when it
matches the repository and user intent.

For project connections, do not treat an empty
`teamcity project connection list --project <target>` result as proof that no
connection exists. That command may list only connections owned directly by the
project. Walk the target project's `parentProjectId` chain through its ancestors
to `_Root`, listing and viewing connections at each owning project. Record both
the connection ID and its owner project. Do not modify the owner project;
attempt a connection-backed VCS root in the target project first.

For a selected existing pipeline, inspect its primary VCS-root attachment and
its head job's VCS-root entries when available. A root merely visible in the
target project is not evidence that the pipeline can check out the repository.

When a matching TeamCity configuration exists, reuse its configuration format
and update it rather than generating a parallel pipeline. Otherwise, if the
repository contains GitHub Actions workflows, attempt to convert the relevant
workflow to TeamCity Pipelines YAML before generating a configuration from
scratch. With the TeamCity CLI, use `teamcity migrate --from github-actions`.
Review the converted YAML and its reported manual setup before treating it as
generated configuration.

### 5. Check Local Changes With Remote Run Fallback

For an IDE-led KMP onboarding flow, when the user provides a local repository
clone and its path, use that working tree first for Remote Run when the selected
surface supports it. This gives the initial verification build the actual source
code before a durable VCS root is configured. Use a VCS root for durable CI.

For private repositories where TeamCity cannot collect changes, try a TeamCity
remote run or patch-based personal build before declaring the setup blocked,
when the selected TeamCity surface supports that operation.

This is a deferred VCS authorization fallback, not a replacement for a working
VCS root. TeamCity personal builds use current repository sources plus uploaded
local changes, so checkout or change collection can still fail if TeamCity
cannot read the base repository at all.

Use only a first-class remote-run or patch capability exposed by the selected
CLI or MCP surface. If neither surface supports patch upload, give the manual
permission/capability handoff below. Never log authorization headers or literal
tokens.

With the TeamCity CLI, request that fallback as a personal run without pushing
the local branch:

```bash
TEAMCITY_URL=<server> teamcity run start <job-id> --branch <branch> \
  --local-changes=git --no-push --personal
```

If TeamCity rejects it with `missing "Change build source code with a custom
patch" permission` (also surfaced as `PATCH_BUILD_SOURCES`), do not retry it
or push the local work as an implicit workaround. This permission is separate
from ordinary build-start permission. Hand off the exact repair:

1. The administrator of the named target project opens **Project Settings →
   Permissions** on the confirmed server and grants the TeamCity permission
   **Change build source code with a custom patch** to the user or token role,
   scoped to that project and its required child build configurations.
2. The user obtains a replacement CLI session for that server with
   `TEAMCITY_URL=<server> teamcity auth login`; do not paste the replacement
   token into a command or chat.
3. Re-run the same personal command with `--local-changes=git --no-push` and
   confirm that TeamCity accepted a personal build.

If the project owner instead wants a normal VCS-triggered run, obtain explicit
approval to commit and push first. State which branch and triggers the push
will affect; it is a different action from a patch-based personal build.

If that build fails with a VCS access error, continue to step 6: reuse or create
a target-project GitHub connection, then create a connection-backed VCS root.
Report a blocker only if that cannot be completed or a later checkout still
fails. Do not retry unchanged, create credentialless roots, or repoint to
unrelated or cross-project roots.

### 6. Choose VCS Connection Strategy

Check VCS access before the first build. If the repository is private, do not
assume anonymous checkout will work.

Use the selected TeamCity surface to list project connections. Prefer existing
project or inherited connections when possible.

Connections in parent projects are inherited by subprojects. Do not recreate the
same connection in nested projects.

When CLI connection listing does not include inherited objects, follow the
owner-aware procedure in `shared/vcs-connections-and-auth.md`; do not silently
fall back to anonymous checkout or a personal access token.

#### GitHub Repositories

For GitHub, prefer a GitHub App connection. Do not create a Git VCS root with a
personal access token via password authentication unless there is no usable
connection path and the user explicitly accepts that tradeoff.

Why: PATs tie infrastructure to one person, are harder to revoke centrally, and
are easier to leak in build logs. A GitHub App connection produces a
non-personal refreshable access token tied to a service identity.

Interactive GitHub App flow:

First check whether a usable GitHub App connection already exists and whether
the App is already installed on the target repository. The following actions are
needed only for the missing parts:

1. If no suitable connection exists, create a GitHub App project connection for
   the target project. Follow the browser flow on GitHub and click **Create**.
   Capture the connection ID and the install link returned by the selected
   TeamCity surface.

2. If the connection is not authorized for the current TeamCity user, authorize
   it.

3. If the GitHub App is not installed on the target repository, install it using
   the returned install link. The App may already be installed on the target
   organization or staging environment.

Steps 2 and 3 are independent, but both must be complete before creating the VCS
root. Authorization gives TeamCity a user token for API calls; installation
grants the App repository access. Without either one, VCS root creation or clone
can fail, often as a 404.

For a GitHub OAuth App rather than a GitHub App, authorize the current user
through the connection's owner project before creating or testing a VCS root.
With CLI, that is `teamcity project connection authorize <connection-id>
--project <owner-project-id>`. A GitHub App authenticates as the application,
so verify its installation and repository access instead; do not substitute a
user OAuth login for a missing App installation.

Non-interactive GitHub App variant:

- Use pre-registered GitHub App credentials from a vault or secure secret
  store.
- Keep App ID, client ID, client secret, private key, and webhook secrets out of
  command history and logs.
- Use a TeamCity connection creation capability that accepts explicit GitHub App
  credentials.

#### Docker Registries

For GHCR, Docker Hub, or private registries, create or reuse a Docker registry
connection with a service account or robot user. Do not use a personal
password.

When using an interactive flow, enter the registry password through a secret
prompt or equivalent protected input only; it must never be echoed or written
into generated configuration.

Reference the connection ID from Docker image build/push steps or Docker
support features. For AWS-managed ECR, prefer an AWS connection with
role-based federation over static Docker credentials.

#### VCS Roots

For questions like "which repository URL and default branch does this project
use", discover attached VCS roots first, then inspect a concrete root.

Required sequence:

1. List valid VCS root IDs in the project.
2. View the chosen root details.
3. Read URL, default branch, branch specification, auth method, and properties.

Do not guess VCS root IDs. Do not use broad project views as a substitute for
VCS root details.

Use the selected TeamCity surface to list and view VCS roots.

When creating a VCS root for GitHub, prefer the GitHub App connection path and
create the root with connection-backed authentication. Use password or PAT auth
only as a last resort.

The preferred GitHub shape is a Git VCS root that uses connection-backed token
authentication with the selected connection ID, rather than password
authentication with a personal access token.

With CLI, create it with `teamcity project vcs create --project <target> --url
<url> --branch <branch> --auth token --connection-id <id>`.

For an existing pipeline, attach the selected root before pushing configuration
or queueing a build. Follow the narrowly scoped procedure in
`shared/vcs-connections-and-auth.md`; do not ask the user to perform this
ordinary attachment merely because the root was created successfully.

#### Branch Specification Is A Build Gate

Before queueing the first build, identify the repository's default branch and
read the new VCS root back. Its branch specification must monitor the branch
that will be queued. For example, a repository whose default branch is
`master` needs a matching rule such as `+:refs/heads/master` when the root has
an explicit branch specification.

If TeamCity reports that the selected branch is closed, excluded, or not
monitored, that build is failed even when its build steps and tests passed:
TeamCity may substitute a default revision. Update the VCS root/pipeline and
rerun it on a monitored branch; do not report the result as the first green
build.

#### Build-Time VCS Credential Stop Rule

Stop and ask the user to fix repository access manually in TeamCity or GitHub
when all of these are true:

- A build or child build fails before checkout/change collection with a VCS
  access error such as `Repository not found`, authentication failed, 401, or
  404.
- The VCS root properties do not show durable build-time credentials, for
  example no stored username/password, SSH key, token, or usable app-backed
  secret is attached.
- A supported remote-run or uploaded-patch personal build either fails the same
  way or would still require TeamCity to read the same private base repository.

A VCS root connection test is not enough to continue if the actual build-time
change collection fails. Treat that mismatch as evidence that the interactive
user connection can test the repository but the build configuration lacks
durable checkout credentials.

The final report should name the exact failing build ID, VCS root ID, repository
URL, and the manual prerequisite: install/authorize the TeamCity GitHub App for
the repository, attach a project-scoped GitHub App/service connection that
stores build-time credentials, or configure an approved service SSH key/token in
the VCS root. Do not ask for or invent a PAT unless the user explicitly chooses
that fallback.

### 7. Create Or Update The TeamCity Pipeline

Create or update the selected TeamCity pipeline using the confirmed VCS root and
the repository commands discovered in step 2.

Pipeline contents should include:

- Checkout from the selected VCS root.
- Build and test jobs.
- Required JDK or runtime selection.
- Test report and artifact publishing.
- Docker build/push steps only when the repository requires them.
- Parameters and secrets referenced through TeamCity credentials or project
  connections, not hardcoded values.

When the repository declares an exact JDK, configure both sides of runtime
selection:

- a scheduling requirement or image selector proving the chosen agent offers
  that JDK; and
- job-level `env.JAVA_HOME` (or the runner's equivalent runtime selector)
  pointing to the same server-managed installation.

Discover the parameter, tool, or image name on the active server. Do not copy a
name such as `env.JDK_25_0` from an example or another server. Do not add an
ad hoc JDK download merely to bypass missing agent infrastructure unless that
bootstrap mechanism is already part of the repository's intended toolchain.

When mobile targets are present, use the mobile job topology and artifact rules
in `shared/kmp-mobile.md`. Do not silently reduce a KMP application to JVM-only
validation.

For an iOS script that builds an Xcode scheme embedding a KMP framework, add
the architecture arguments selected under `shared/kmp-mobile.md` to the
generated `xcodebuild` command. For example, an `iosSimulatorArm64`-only
project on an Arm64 macOS agent needs `ARCHS=arm64 ONLY_ACTIVE_ARCH=YES` before
the `build` action.

Prefer the smallest pipeline that can prove the repository. Preserve existing
multi-job topology when the repository already defines it.

#### Report Meaningful Build Status

Annotate the main stages of whatever pipeline is produced (build, test,
package, publish, per stack) so the builds overview shows what the build is
doing rather than a generic running state. This is a requirement, not a
refinement: a generated config without it is incomplete. See
`shared/build-step-selection.md` ("Meaningful Build Status") for how.

### 8. Validate Configuration

Validate generated or modified configuration before queueing a build. Use the
configuration file that will be committed or otherwise become the source of
truth; do not validate a separately reconstructed copy.

#### Kotlin DSL

Use a deterministic Kotlin DSL validator available in the selected TeamCity
surface. The TeamCity CLI command is:

```bash
teamcity project settings validate path/to/.teamcity
```

An MCP validation operation is equally valid when exposed. If neither is
available, run the TeamCity Configs Maven goal from the DSL directory. Prefer
its wrapper; use `mvn` only when the wrapper is absent and Maven is installed:

```bash
./mvnw teamcity-configs:generate -f path/to/.teamcity/pom.xml
mvn teamcity-configs:generate -f path/to/.teamcity/pom.xml
```

Do not queue a build if no deterministic Kotlin DSL validation is available.
Report the missing validation capability instead.

#### Pipeline YAML

Use a server-backed YAML schema validator available in the selected TeamCity
surface. The TeamCity CLI command is:

```bash
teamcity pipeline validate path/to/pipeline.yml
```

An MCP schema-validation operation is equally valid when exposed. If neither
is available, a local YAML parser may establish only syntax, for example:

```bash
python3 -c "import yaml, sys; yaml.safe_load(open(sys.argv[1])); print('YAML syntax is valid')" path/to/pipeline.yml
```

Do not describe a successful syntax parse as successful TeamCity validation.
Stop before queueing the build and report that semantic YAML validation is
missing.

Keep validation and diagnostic files outside the repository checkout. For
example, pull a saved Pipeline to a path under `/tmp` (or the platform's
temporary directory), not to a hidden file in the repository. A CI setup task
must leave the checkout unchanged except for the explicitly requested
configuration source path and changes the user authorized; an untracked probe
file is still a source mutation.

### 9. Validate Compatibility

Before spending time debugging build failures, validate that the generated
pipeline and jobs are compatible with at least one TeamCity build agent or
build environment.

### 9a. Resolve Pipeline Parameters Before Agent Diagnosis

Server-backed YAML validation checks Pipeline shape but does not prove that all
`%name%` substitutions resolve. After saving a Pipeline, pull back the exact
server-stored YAML and inspect substitutions in script content before calling a
queued job an agent problem:

```bash
TEAMCITY_URL=<server> teamcity pipeline pull <pipeline-id> --output /tmp/pipeline.yml
rg -n '%[^%]+%' /tmp/pipeline.yml
```

For each match, verify that it is a declared pipeline/job parameter or a known
inherited TeamCity parameter. Do not put shell-specific environment-variable
syntax using `%...%` in Pipeline YAML merely because it is in a Windows-only
branch: TeamCity resolves it as a configuration parameter before the script is
sent to any agent. Use an equivalent command with no `%...%` substitution
instead; for example, `exit /b` preserves the previous batch command's exit
code without referencing `%ERRORLEVEL%`.

When a queued job reports a generic `waitReason`, use the detailed queue or
compatibility diagnostics exposed by the selected CLI or MCP surface too. If
that surface only returns the generic reason, the saved-YAML substitution check
above is mandatory; do not report a capacity blocker while TeamCity reports
**Unresolved parameters**. Report the exact parameter name and script line,
then fix or declare the parameter and validate again.

Check:

- The live pipeline schema for the target server, including the permitted
  `runs-on` selectors. With TeamCity CLI, refresh it rather than relying on a
  cached or another server's schema:

  ```bash
  TEAMCITY_URL=<server> teamcity pipeline schema --refresh
  ```

- The target server's enabled, connected agents and their stable properties:

  ```bash
  TEAMCITY_URL=<server> teamcity agent list --connected --enabled --authorized \
    --limit 0 --json=id,name,typeId,pool.id,pool.name
  TEAMCITY_URL=<server> teamcity agent view <agent-id> --json
  ```

  If a pipeline job already exists, confirm the result against that job rather
  than guessing from an agent name:

  ```bash
  TEAMCITY_URL=<server> teamcity agent jobs <agent-id> --json
  TEAMCITY_URL=<server> teamcity agent jobs <agent-id> --incompatible --json
  ```

  Use matching MCP agent/compatibility tools when they are exposed. If MCP does
  not expose them, use the CLI; an MCP connection that can only read builds and
  logs is not evidence that the server has no agents.
- Cloud images and the job compatibility view, when the server or tool surface
  exposes them. A selector can be schema-valid while no configured image
  satisfies it. Conversely, an empty connected-agent list does not disprove a
  hosted selector: cloud agents can be provisioned on demand.
- Required JDK/runtime exists.
- Runner or pipeline step types are valid.
- Docker requirements match available agents, if Docker is used.
- Required parameters and credentials resolve.
- VCS connection can collect changes.

Choose `jobs.<job-id>.runs-on` from the target server's live schema and agent
evidence:

- For a hosted selector, choose a tier offered by that server only when its
  cloud profile or compatibility result supports it.
- For self-hosted execution, derive a `self-hosted` requirement from properties
  shared by eligible agents (for example `os-family: Linux`, architecture, CPU,
  RAM, or a durable custom agent parameter). When those capability properties
  are absent or inaccurate, `agent list` may instead show a server-managed
  agent family. A custom `system.agent.name` `starts-with` requirement for its
  common prefix is acceptable only after confirming it against multiple eligible
  agents or configured cloud images **and** after the actual pipeline upload
  accepts it. Never use the full name of one transient VM.

Validate the resulting YAML against the live server, then use job compatibility
output to verify it. Schema validation does not prove that every server's
pipeline parser supports the selector: if `pipeline push` rejects a
schema-valid custom selector, keep the server configuration unchanged, record
the parser error, and use a less-specific supported selector only when the
remaining job requirements have demonstrated compatible agents. Otherwise use
the manual handoff below. Do not retain `Linux-Medium`, `Linux-Small`, or any
other tier just because it was valid on a different TeamCity server.

For an exact repository-declared JVM version, agent compatibility alone is not
enough. Discover a server-managed JDK installation from the selected agent or
image and verify the completed build's effective `JAVA_HOME` and Java version.
Prefer first-class CLI fields. If the CLI omits agent parameters or resulting
runtime properties, discover the current environment's TeamCity MCP tools,
read their guide and schemas, confirm the server, and use a dedicated agent or
build-property read. A generic MCP read is acceptable only when its schema
explicitly permits a narrow projection of the named runtime properties. If no
such operation is exposed, use the manual infrastructure handoff below. A green
build whose effective runtime is older than the declared version remains a
failed verification.

If the required JDK is unavailable, do not queue repeated builds and do not
weaken the repository requirement. Hand off this exact infrastructure work:

1. **Owner:** the TeamCity agent or cloud-image administrator.
2. **Scope:** an agent pool or cloud image available to the target project;
   keep the change out of an ancestor or `_Root` unless its owner explicitly
   chooses organization-wide scope.
3. **Action:** install the required JDK and expose it as a stable agent
   parameter, TeamCity-managed tool, or image capability that a Pipeline can
   select.
4. **Verification:** show that the job's runtime requirement is compatible and
   that its effective `JAVA_HOME` and Java version resolve to the required JDK.
5. **Resume signal:** return the discovered parameter/tool name, selector, and
   compatibility evidence so the Pipeline can be validated and queued.

If no compatible agent/image exists, do not repeatedly queue builds or silently
fall back to `self-hosted`. Give this manual checklist instead:

1. The target project's TeamCity administrator opens the job's **Agents**
   compatibility view or **Project Settings → Cloud Profiles**.
2. They either enable a hosted tier that the live pipeline schema offers, or
   identify an enabled self-hosted agent and its stable OS/runtime/Docker
   properties. If the server does not publish those properties, they identify
   the durable cloud-agent family prefix instead; they must not send a single
   temporary cloud-VM hostname.
3. They make the job compatible by enabling/provisioning the matching cloud
   image or authorizing the relevant self-hosted agent/pool for the project.
4. They return the compatible selector or stable self-hosted properties. The
   agent updates the YAML, validates it against the live server, and queues a
   new personal build.
For a platform-specific job, use the exact durable macOS/Xcode, Android, or
other agent/image value offered by the confirmed server whenever its schema
supports it. Read the saved YAML back and verify the selected value; do not use
a generic OS requirement or a transient cloud VM name.

### 10. Queue The First Build

Queue the first verification build, preferably as a personal or isolated build
when the chosen TeamCity surface supports it.

Poll the pipeline head and every generated job with bounded backoff. For
example:

- 5 seconds
- 10 seconds
- 20 seconds
- 30 seconds

Treat 60--120 seconds in the queue as a diagnostic deadline, not another
reason to extend the watch. No later than the second observation that the run
is still queued, pause all waiting and perform this compatibility checkpoint:

1. Read the run and queue details, including the specific wait reason.
2. List enabled, authorized agents and any applicable cloud images or hosted
   selectors.
3. Query the job against candidate agents with incompatible-job diagnostics so
   TeamCity reports unmet requirements, missing versions, pool restrictions,
   or unresolved parameters.
4. Pull the server-stored Pipeline YAML and verify every `%name%` substitution
   is declared or inherited.

If the wait reason already says **no compatible agents** or **unresolved
parameters**, perform the checkpoint immediately; do not spend the full minute
first. If it confirms zero compatible agents or images, stop polling. Do not
queue a duplicate, restart the same run, change an agent selector speculatively,
or keep waiting for capacity: capacity cannot make an incompatible job
compatible. Apply at most one correction that follows directly from the
diagnostics, validate the updated configuration, and requeue once only after
the compatibility result changes. If diagnostics do not prove incompatibility
or unresolved parameters, continue monitoring the accepted build at a maximum
60-second interval for at least 10 minutes from queueing. Inspect both the job
queue reason and agent availability, and give the user a short progress update
at least once a minute.

Stop polling early if:

- The build reaches a terminal state.
- A documented queue grace period has elapsed and the queue or build reason
  proves a stable blocker.
- The same failure repeats twice with no new signal.

### 11. Investigate The First Failure

If the build fails, diagnose one real blocker at a time:

- Read targeted build metadata: status, status text, branch, build type,
  trigger, agent, and failed-to-start state.
- Use build problems, especially `problemOccurrences`, for failure type,
  details, and log anchors.
- Read failed tests with details, new-failure status, and log anchors.
- Read focused or filtered build logs rather than full logs first.
- Check changes and compare with a last successful baseline when useful.

Apply the smallest safe fix. Decide whether the fix belongs in repository code,
pipeline YAML, TeamCity parameters, credentials, VCS connection, runner
selection, or build-agent requirements.

If the smallest safe fix is missing durable VCS credentials for a private
repository, stop after one confirming failure or, at most, one remote-run
fallback that fails the same way. Report the manual credential repair instead
of trying speculative VCS-root rewrites.

### 12. Hand Off Every Manual Prerequisite

Do not end with a generic statement such as "configure the connection" or
"grant access". For every operation the selected tool surface cannot complete,
provide a manual completion checklist containing:

1. **Owner:** the role or team that has the required permission.
2. **Scope:** the exact TeamCity server and project; say explicitly when the
   action must stay in the target child project and must not modify an ancestor
   or `_Root`.
3. **Action:** a precise TeamCity UI path or a supported CLI/MCP command. Use
   the current server's labels when known; otherwise name the settings page and
   object to create or edit without inventing a field name.
4. **Values:** every already-known ID, URL, branch, connection, agent image,
   or parameter name, and which secret must be selected from secure storage
   rather than pasted into a repository or chat.
5. **Verification:** the test, saved object, or build state that proves the
   action succeeded.
6. **Resume signal:** the object ID, redacted error, or build URL/ID that the
   user should provide to let the agent continue.

If the required manual operation itself is unknown, say what capability is
missing and give the administrator a narrowly scoped request. For example,
request a dedicated MCP operation to create a VCS root with an inherited
connection in a named child project; do not ask for unrestricted REST writes.

### 13. Re-run And Confirm

Re-run after each concrete fix. Continue only while each rerun has new evidence
or a plausible fix.

The task is complete only when one of these is true:

- The first verification build is green.
- A stable external blocker is proven with evidence and reported clearly.

## Success Criteria

Do not stop after "project created" or "pipeline queued".

A successful report includes:

- TeamCity server URL and parent project ID.
- Final TeamCity object name and ID.
- Repository URL and branch.
- VCS root and connection strategy used.
- Configuration format, validation method, and validation result.
- Build IDs for failed and successful verification runs, when observed.
- Root cause and fix for each investigated failure.
- A concrete manual completion checklist for every remaining prerequisite.
