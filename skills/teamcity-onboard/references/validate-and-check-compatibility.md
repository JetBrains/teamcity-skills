# Validate and check compatibility

Use this guide after the pipeline YAML is written and before any build is
queued. It proves the JDK selection, the saved configuration, and agent
compatibility.

## Select the JDK

For an exact host JDK, inspect parameters reported by compatible agents or
images on this server. A key such as `env.JDK_21_0` advertises an installed JDK
path; its name is an example, not a TeamCity constant. Use the actual key from
the agent's Parameters view or an available TeamCity tool. The CLI's
`teamcity agent jobs <agent-id> --incompatible --json` can confirm an unmet
requirement but does not list the agent's parameters. Treat a conventional key
inferred from the requested Java version as a candidate until agent parameters
or job compatibility confirm it.

For the full host-JDK and container decision, read the companion
[TeamCity JDK Selection](../../teamcity-jdk-selection/SKILL.md) skill when it is
installed. The checks below remain usable without it.

The two settings have different jobs:

- An agent requirement that the observed JDK key exists limits scheduling to
  agents that advertise it. Check the job's compatibility result. A reference
  to `%env.JDK_21_0%` may already provide that requirement implicitly; add an
  explicit `exists` requirement when it does not.
- Set the job's `parameters.env.JAVA_HOME` to the observed key, for example
  `%env.JDK_21_0%`. This selects that installation for Maven or Gradle; the
  requirement alone does not change the Java used by the build.

TeamCity checks agent compatibility before dispatch. A script that searches
host paths and calls `setParameter` runs too late to select an agent. Pull the
saved Pipeline YAML and check both scheduling and JDK selection on every
affected job before queueing; confirm the runtime with
`"$JAVA_HOME/bin/java" -version` in the build. A Linux container-safe job
without a matching host JDK needs Docker capability and a pinned JDK image,
not a host-JDK requirement. macOS and iOS work needs a native compatible
runtime.

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
[Build-step selection](build-step-selection.md) to local and stored Pipeline
YAML.

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
[Manual prerequisites](manual-prerequisites.md).

Choose `runs-on` from target-server evidence. Use an observed stable
self-hosted capability or a server-provided hosted selector. Never use a
transient VM name or a selector copied from another server. Confirm the final
JDK through the build's `JAVA_HOME` and Java version.

Check each host-JDK requirement against compatible agents. An unresolved JDK
parameter is a pre-dispatch blocker. For a Linux container-safe job, replace
the host-JDK requirement with Docker capability and run the job in the pinned
JDK image. For native work, the infrastructure owner must provide the required
JDK, image, or agent capability and return its selector and compatibility
evidence.
