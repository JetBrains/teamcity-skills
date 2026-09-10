# TeamCity CLI And MCP

Use this reference when TeamCity CLI or MCP is available. It avoids a common
mistake: a child project can display an inherited connection in the UI while a
CLI list command reports no connection because it lists only objects owned by
that child.

## Select The Matching Server

Every CLI command must be bound to the TeamCity URL from the current user
request. Do not use the persisted default server as an implicit target:

```bash
TEAMCITY_URL=<server> teamcity auth status
```

If that session is unavailable or expired, authenticate interactively:

```bash
teamcity auth login --server <server>
```

Request only the permissions required for the planned work. Do not pass an
access token on a command line or print the CLI configuration, because it can
contain credential metadata.

For MCP, first verify that the connection targets the same server. Discover its
actual tools and resources before relying on it: one MCP connection may expose
only read operations and personal-build queueing, while another can expose more.
Do not infer a capability from an endpoint-looking URL or from a different
server's MCP configuration.

When a first-class CLI command lacks a capability, perform MCP discovery before
declaring a blocker:

1. Inventory the MCP tools available in the current environment; do not assume
   a fixed TeamCity MCP tool set.
2. Read the guide and schema for every plausible TeamCity operation.
3. Confirm that the MCP connection targets the exact server from the request.
4. Prefer a dedicated project, connection, VCS-root, Pipeline, build, agent, or
   artifact operation. Use a generic MCP read only when its schema explicitly
   permits the exact narrow read. Use a write operation only when its schema
   explicitly permits that object and scope.
5. If no matching operation exists, provide the manual checklist for the exact
   missing capability.

An MCP tool named `teamcity_rest_post` is not necessarily a general REST write
proxy. The server's MCP policy determines its allowed paths and any forced
behaviour, so read the guide and tool schema and, where safe, make a harmless
request to a read-only endpoint to confirm the allowlist. A deployment with
only `teamcity_rest_get`, `teamcity_build_log`, and a `teamcity_rest_post` tool
restricted to build queueing cannot create project connections, VCS roots, or
pipelines. Do not extrapolate that limitation to a differently configured MCP
server.

## Find An Inherited Connection

1. Read the target project and note its `parentProjectId`.
2. At the target and then at each parent up to `_Root`, run
   `teamcity project connection list --project <project-id>`.
3. For every candidate, verify its type and details in the same project scope:
   `teamcity project connection view <connection-id> --project <owner-project-id>`.
4. Keep the connection ID together with the project that owns it. A connection
   displayed as inherited by the UI belongs to an ancestor, not to the target.

Use matching MCP read tools to corroborate project ancestry or connection
details when available. The MCP result is evidence for discovery; do not assume
it can create a VCS root or pipeline.

## Authenticate The VCS Connection

Use the connection type to choose the authentication path:

- **GitHub App:** it authenticates as the app. Verify that its installation has
  access to the target repository. It does not become usable merely because a
  user authenticated TeamCity CLI.
- **GitHub OAuth App:** authorize the current TeamCity user through the project
  that owns the connection:

  ```bash
  TEAMCITY_URL=<server> teamcity project connection authorize <connection-id> \
    --project <owner-project-id>
  ```

  This may open the provider's OAuth flow. Do not replace it with a copied
  personal access token unless the user explicitly chooses that trade-off.

## Create Or Reuse The VCS Root

First list and inspect VCS roots in the target project and every ancestor. If a
suitable inherited root already exists, reuse it rather than creating another.

With CLI, create a connection-backed target-project root with
`teamcity project vcs create --project <target> --url <url> --branch <branch>
--auth token --connection-id <id>`.

Some TeamCity CLI/server combinations reject a connection ID inherited from an
ancestor when a new VCS root is created directly in the target project. Attempt
the connection-backed root creation there first; only treat the exact error
`connection <id> not found in project <child>` as this capability gap. It is
not evidence that the inherited connection is absent. In that case:

1. Do not retry anonymously and do not duplicate the connection in the child.
2. Create the root through the connection's owner project, using its
   connection-backed authentication, only when the user has approved that
   shared placement and the root's reuse scope is appropriate.
3. Use that inherited VCS root when creating the pipeline in the target child
   project.

Creating a root in `_Root` is globally visible. Never do that just to work
around a client limitation without explicit user approval. If no suitable owner
scope is approved, report the CLI limitation with the connection ID, owner
project, repository URL, and exact error.

When neither CLI nor the target server's MCP can create the child-project root,
give the user this manual handoff rather than stopping at the limitation:

1. In the **target child project** (not the connection owner), open **Project
   Settings → VCS Roots** and create a Git VCS root.
2. Enter the already-discovered repository URL, root name, default branch, and
   branch specification. Choose **Refreshable access token**, not a password,
   personal access token, or SSH key.
3. Click **Generate new** next to the token selector. Give the token a
   descriptive name and select the existing inherited GitHub App connection in
   the token dialog. Keep the project scope limited to the target child project
   and its subprojects. For a GitHub App, restrict repository scope to the
   required repository (for example, enter `teamcity-skills`, without the
   organization name); do not request global repository access.
4. Save the token, select it for the VCS root, run TeamCity's connection test,
   and save the root only after the test succeeds.
5. Return the saved VCS root ID to the agent. The agent must read that root via
   CLI/MCP, confirm its URL, branch, and authentication strategy, then continue
   with pipeline creation.

The **Refreshable access token** selector stores a TeamCity VCS Auth Token
reference. Its **Enter** control accepts that TeamCity token ID, not a raw
GitHub personal access token (PAT). Do not paste a provider PAT there: it is a
different authentication mode and can produce a misleading GitHub 403.

If the Generate-token dialog does not offer the inherited connection, do not
assume that it can issue a token in the child project. Hand off to the
connection owner instead:

1. The administrator of the project that owns the connection opens **Project
   Settings → VCS Auth Tokens → Generate new** there.
2. They select the connection, restrict the token's project scope to the named
   target child project and its subprojects, and restrict a GitHub App token to
   the required repository. They copy the resulting token ID.
3. In the target VCS root's **Refreshable access token** selector, a project
   administrator clicks **Enter** (or the adjacent edit control) and enters
   that token ID, then tests and saves the root.

Treat the token ID as a credential reference: do not ask the user to paste it
into chat. Ask them only to return the saved VCS root ID. If the owner cannot
issue a child-scoped token and no direct connection is available in the target
project, the remaining manual alternative is a new project-scoped GitHub App
connection, with its own approved GitHub App registration or credentials. Do
not ask the user to create a VCS root in an ancestor or `_Root` merely to work
around a CLI limitation.

## Attach A VCS Root To An Existing Pipeline

Before pushing YAML or queuing a run, verify the selected pipeline itself is
attached to the chosen root. A root that is visible in the target project, or
that merely passed a connection test, does not attach it to an existing
pipeline.

Use a first-class CLI or matching MCP attachment operation when one exists. If
neither surface exposes one, give the manual attachment checklist.

Do not ask the user to attach a root that the selected surface can attach safely.

### Explicit PAT Diagnostic Fallback

Use this only when the user explicitly chooses to test a GitHub PAT rather than
the preferred App-backed token. In the existing target-project VCS root:

1. Select **Password / personal access token**, not **Refreshable access
   token**.
2. Use the username `x-access-token` and enter the PAT only in the protected
   password field; never in a repository URL, command line, or chat.
3. For a fine-grained GitHub PAT, select the `JetBrains/teamcity-skills`
   repository and grant **Contents: Read-only**. For a classic PAT, grant its
   repository read scope. Complete any organization SSO authorization required
   by GitHub.
4. Run the root's connection test. `git ls-remote` needs only read access; a
   GitHub 403 saying "Write access ... not granted" still means the presented
   credential cannot read that repository.

This is a diagnostic or explicitly accepted personal-credential fallback. Once
it works, replace it with a least-privilege GitHub App/service token where one
is available.

If TeamCity reports that a root "failed to authorize using the specified token"
or Git reports invalid credentials, do not diagnose an agent, YAML, or network
failure. The selected refreshable-token reference is unusable for that root.
Leave the root in the target project and perform this recovery:

1. A project administrator opens **Project Settings → VCS Auth Tokens** in the
   scope that owns the token, finds the token by its ID, and verifies that its
   connection, project scope, and GitHub App repository scope include the
   target project, its pipeline-created subprojects, and the repository.
2. If the token is absent, out of scope, or cannot resolve the repository, the
   connection owner issues a replacement token with those least-privilege
   scopes. Do not create or paste a static PAT.
3. A target-project administrator replaces the token reference on the existing
   VCS root, runs its connection test, and saves only after it succeeds.
4. The user returns the VCS root ID and successful test result. The agent then
   requeues a personal build; it does not rerun against the known-invalid
   credential.

## Pipelines, Builds, And MCP

After a usable root is known, use the CLI rather than a browser for the normal
lifecycle:

```bash
TEAMCITY_URL=<server> teamcity pipeline validate <pipeline.yml>
TEAMCITY_URL=<server> teamcity pipeline create <name> --project <target-project> \
  --vcs-root <vcs-root-id> --file <pipeline.yml>
TEAMCITY_URL=<server> teamcity pipeline push <pipeline-id> <pipeline.yml>
TEAMCITY_URL=<server> teamcity run start <job-id> --branch <branch> --personal
```

Use a matching MCP connection for build logs, build metadata, tests, problems,
and artifacts. If its write capability is restricted to the build queue, use it
to start a personal build on the explicit branch, then use its read tools to
monitor and analyse that build. Use CLI for pipeline and VCS-root writes unless
the matching MCP exposes a dedicated equivalent operation.

Do not invent pipeline-YAML syntax for a TeamCity build feature. When a plugin
can only be configured in the UI and neither CLI nor the matching MCP exposes a
dedicated feature operation, report that as a concrete capability gap rather
than bypassing it with ad-hoc REST calls. Name the administrator action needed:
add a narrowly scoped MCP operation for that feature or configure it in the
target project's UI, then return the pipeline/build-feature ID for verification.
