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
- Do not use plain REST with `curl`, ad hoc scripts, or generic REST escape
  hatches unless the user explicitly asks for that path, except for the
  direct patch-upload fallback documented in step 5.
- Confirm the exact TeamCity server before discovery or writes.
- If a callable tool, connection, or configured context points at a different
  TeamCity server, abort discovery and fix the attachment or login first.
- Whenever YAML or Kotlin DSL with TeamCity configuration are generated or modified,
  always perform a validation of it (See "Validate Configuration" step),
  before starting a run in TeamCity.
- At the start of every run, ask for or confirm the TeamCity server and target
  project before repository inspection, TeamCity discovery, or writes.
- This confirmation must be obvious in the assistant's first response for the
  task. Do not continue based on prior context, tool names, environment
  variables, command history, repository files, or cached assumptions.
- Keep a small in-memory cache of server facts learned during the task. Reuse
  it while the target server, parent project, repository, and TeamCity object
  have not changed.

## Recommended Workflow

### 1. Confirm TeamCity Server And Project

This is a hard stop gate. If the user's current request does not explicitly
include both values below, the assistant's next message must ask for them and do
nothing else:

- TeamCity server name or URL.
- Target parent project name or ID. `_Root` is valid.

The assistant must not treat environment context, previous tasks, command
history, repository files, MCP server names, or cached values as confirmation.

At the start of the task, ask for or confirm:

- TeamCity server name or URL.
- Target parent project name or ID. `_Root` is valid.

Do not continue to repository inspection, TeamCity discovery, connection
creation, or writes until both values are known from explicit user input in the
current request.

If the user provides a project name rather than an ID, resolve it to a concrete
TeamCity project ID after connecting, then confirm the exact ID before any write
operation.

Also ask for or discover:

- Authentication path. Try OAuth or existing interactive authentication first
  when the selected TeamCity surface supports it. Ask for a TeamCity token only
  when no safer existing authentication path is available.
- Object strategy: create a new pipeline or reuse/update an existing TeamCity
  object.
- Repository URL and default branch.

Handle tokens safely:

- Ask for tokens only in a secret-safe channel when available.
- Never print tokens, private keys, passwords, or authorization headers.
- Do not store tokens as plain TeamCity project parameters.

### 2. Inspect The Repository

Identify the smallest command set that should prove the project works:

- Build command.
- Test command.
- Required Java/JDK version, especially for Gradle or Maven projects.
- Test reports, coverage reports, and other artifact paths.
- Docker image build, push, compose, or container validation steps, if present.
- Required services, caches, environment variables, and credentials.
- Existing CI files and checked-in TeamCity YAML or Kotlin DSL.

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

### 4. Discover TeamCity State

Discover state only against the confirmed target server:

- Parent project details and inherited settings.
- Existing pipelines and build configurations.
- VCS roots and branch specifications.
- Project connections and inherited connections.
- Project features that may affect checkout, commit status publishing, Docker,
  or credentials.
- Recent failures and last successful baseline builds for related objects.
- Available build agents, compatible environments, and pipeline capabilities.

Avoid duplicate CI. Prefer reusing or updating an existing object when it
matches the repository and user intent.

### 5. Check Local Changes With Remote Run Fallback

For private repositories where TeamCity cannot collect changes, try a TeamCity
remote run or patch-based personal build before declaring the setup blocked,
when the selected TeamCity surface supports that operation.

This is a deferred VCS authorization fallback, not a replacement for a working
VCS root. TeamCity personal builds use current repository sources plus uploaded
local changes, so checkout or change collection can still fail if TeamCity
cannot read the base repository at all.

Use a first-class remote-run capability when available. Use direct patch upload
only as this specific documented exception to the no-plain-REST rule, and only
when credentials are supplied through protected configuration, secure secret
storage, or environment variables. Never log authorization headers or literal
tokens.

Direct patch upload works best for Git-generated unified diffs. If a binary
patch is rejected, retry with a plain unified diff for text-only changes or
report the binary patch as unsupported by this fallback.

If a patch-based personal build fails with the same VCS access error, stop and
report a durable VCS authorization blocker unless the selected TeamCity surface
can create a credentialed root with already-approved credentials. Do not create
additional credentialless VCS roots, repoint to unrelated or cross-project VCS
roots, or keep retrying builds. Personal builds still need TeamCity to read the
base repository.

### 6. Choose VCS Connection Strategy

Check VCS access before the first build. If the repository is private, do not
assume anonymous checkout will work.

Use the selected TeamCity surface to list project connections. Prefer existing
project or inherited connections when possible.

Connections in parent projects are inherited by subprojects. Do not recreate the
same connection in nested projects.

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

Prefer the smallest pipeline that can prove the repository. Preserve existing
multi-job topology when the repository already defines it.

### 8. Validate Configuration

If a TeamCity configuration was created or modified, perform the local verification of it.
The verification depends on the format of the configuration:
 - For Kotlin DSL, if you have the TeamCity CLI skill, then use the CLI to validate the configuration
   by running `teamcity project settings validate` (More information is available in the TeamCity CLI skill's "Validating Kotlin DSL Locally" section).
  
   Raw Maven command to validate in case when CLI is not available: `./mvnw teamcity-configs:generate -f .teamcity/pom.xml` (prefer wrapper),
   or `./mvnw teamcity-configs:generate -f .teamcity/pom.xml` (fallback, use when wrapper is not available). Successful build states that configuration is correct.
  
   If Maven is absent, notify the user and ask to install it.
 - For YAML, if you have the TeamCity CLI skill, then use the CLI to validate the pipeline
   by running `teamcity pipeline validate`. Otherwise, run
   `python3 -c "import yaml; yaml.safe_load(open('.teamcity.yml'))" && echo "Valid" || echo "Invalid"`.
   If the `Valid` value is printed, the configuration is correct. If the `python3` is not available, use `python` instead.
   For the fallback, when Python is not available, perform only basic syntax check and
   raise a warning, that deterministic validation was not performed.

### 9. Validate Compatibility

Before spending time debugging build failures, validate that the generated
pipeline and jobs are compatible with at least one TeamCity build agent or
build environment.

Check:

- Required JDK/runtime exists.
- Runner or pipeline step types are valid.
- Docker requirements match available agents, if Docker is used.
- Required parameters and credentials resolve.
- VCS connection can collect changes.

If no compatible agent exists, report this as an infrastructure blocker instead
of repeatedly queueing builds.

### 10. Queue The First Build

Queue the first verification build, preferably as a personal or isolated build
when the chosen TeamCity surface supports it.

Poll with bounded backoff. For example:

- 5 seconds
- 10 seconds
- 20 seconds
- 30 seconds

Stop polling early if:

- The build reaches a terminal state.
- The queue or build reason already explains a stable blocker.
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

### 12. Re-run And Confirm

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
- Build IDs for failed and successful verification runs, when observed.
- Root cause and fix for each investigated failure.
- Remaining manual prerequisites, if any.
