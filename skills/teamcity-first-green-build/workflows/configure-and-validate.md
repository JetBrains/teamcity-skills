# Configure and validate CI

Read [Discover and connect](discover-and-connect.md) first. This workflow
creates or updates the pipeline and proves its saved configuration before a
verification build.

## Configure the pipeline

Use the confirmed VCS root and repository commands. Read
[Build-step selection](../shared/build-step-selection.md) for Maven or Gradle,
and [KMP and mobile](../shared/kmp-mobile.md) for mobile targets.

Include checkout, build and test jobs, the required runtime, test and artifact
publication, and repository-required container work. Reference TeamCity
credentials and connections; never hardcode secrets.

If the requested CI must build pull requests, or the planned verification uses
a PR ref, first ensure that the Pipeline's Repository tracks the provider's PR
branches. Then enable **Repository → Pull requests** on the selected Pipeline
before queueing that branch. Use a dedicated CLI command when the installed
version provides one. CLI 1.5.0 has no command for this setting, and
`pipeline push` cannot change it because repository settings live outside
Pipeline YAML.
Check for a dedicated MCP write next. Use the Pipeline settings UI only as a
fallback; if that is unavailable, give the exact
[manual prerequisite](../shared/manual-prerequisites.md). Verify the saved
setting before claiming PR CI works. **On New Changes → Pull requests** controls
automatic queueing; a trigger or branch specification alone does not enable
PR handling. A successful ordinary-branch build is not proof that a
`refs/pull/...` build is trusted.
For a branch-only pipeline, do not enable PR triggers as incidental setup.

When a job requires a specific JDK, read [JDK selection](../shared/jdk-selection.md)
before configuring its agent requirement, runner, or container.

Keep independent jobs from the repository. Keep mobile work in a KMP pipeline.
Use meaningful TeamCity status messages.

## Validate the saved configuration

Validate the source file that will become the source of truth:

```bash
teamcity project settings validate path/to/.teamcity
teamcity pipeline validate path/to/pipeline.yml
```

An exposed MCP validator also works. A local YAML parser proves syntax only.
Report a missing semantic validator before queueing.

After a server-side correction, reconcile the source file with the stored
configuration and validate again. Keep temporary validation copies outside the
checkout. Apply the Script Parameter Gate from
[Build-step selection](../shared/build-step-selection.md) to local and stored
Pipeline YAML.

## Check compatibility before queueing

Inspect the live schema, enabled and authorized agents, cloud images, runtime
availability, runner types, Docker, parameters, credentials, and VCS change
collection. Pull saved Pipeline YAML and verify that each `%name%` substitution
is declared or inherited.

For a Pipeline job, use TeamCity's compatibility result. With the CLI:

```bash
TEAMCITY_URL=<server> teamcity pipeline schema --refresh
TEAMCITY_URL=<server> teamcity agent list --connected --enabled --authorized \
  --limit 0 --json=id,name,typeId,pool.id,pool.name
TEAMCITY_URL=<server> teamcity agent jobs <agent-id> --incompatible --json
```

When compatibility access is denied, record it as unverified. Use another
permitted machine-readable operation. If none exists, use
[Manual prerequisites](../shared/manual-prerequisites.md).

Choose `runs-on` from target-server evidence. Use an observed stable
self-hosted capability or a server-provided hosted selector. Never use a
transient VM name or a selector copied from another server.

Check each job's requirements against compatible agents. If none match, report
the missing capability and the evidence needed before retrying.

For configuration-only work, stop after the saved-YAML audit, one inventory
query, and one compatibility query. A missing or denied query is a blocker.
