# Agents, JDK, and compatibility

Use this guide before writing the pipeline YAML and again before queueing. A
wrong `runs-on` or JDK selection is how an onboarding freezes: the build
queues forever because no agent matches. Every decision below comes from the
server's evidence, never from a guess.

## Read the server

```bash
TEAMCITY_URL=<server> teamcity pipeline schema --refresh
TEAMCITY_URL=<server> teamcity agent list --connected --enabled --authorized \
  --limit 0 --json=id,name,typeId,pool.id,pool.name
TEAMCITY_URL=<server> teamcity agent jobs <agent-id> --incompatible --json
```

The schema gives the `runs-on` enum; the agent list gives the connected
agents; the incompatibility query explains why an agent rejects a job (the
CLI skill's agents workflow has the fields). For generated jobs absent from
the CLI compatibility lists, use the permitted Pipeline compatibility helper
described in [Build diagnostics](build-diagnostics.md). Do not create a probe
or diagnostic pipeline, job, or script to inspect agents: every pipeline you
create is a deliverable the user will see in their project.

## Choose `runs-on`

- Use a hosted selector from the schema's `runs-on` enum only when TeamCity
  confirms a compatible image, or a capability observed on a connected agent.
  Never use a GitHub label, a selector from another server, or a transient VM
  name.
- Add no OS, JDK, Docker, or parameter requirement the workflow did not need.
  Each one shrinks the set of compatible agents. An `os-family` or similar
  key must exist on an observed agent; changing a value's case cannot make a
  key exist. A bare parameter name in `self-hosted` is not a custom
  requirement: use `requirement`, `parameter`, and `value` from the schema.
- Match the agents' CPU architecture to the images the build pulls, including
  Testcontainers images. An amd64-only image on an arm64 agent fails with
  `exec format error`. Pin `x86_64` when the images are not multi-arch.
- Count compatible agents and cloud images for the exact job. Each parallel
  test batch needs one agent at the same time to achieve a speedup. A queued
  batch with compatible but busy agents is a capacity wait, not proof of an
  invalid requirement.

## Select the JDK

A key such as `env.JDK_21_0` advertises an installed JDK path on an agent; its
name is an example, not a TeamCity constant. Take the actual key from the
agent's parameters or an available TeamCity tool. The incompatibility query
confirms an unmet requirement but does not list the agent's parameters.

- Set the job's `parameters.env.JAVA_HOME` to the observed key, for example
  `%env.JDK_21_0%`. This selects that installation for Maven or Gradle. A
  key no agent advertises blocks dispatch, and no build step can install the
  JDK because the build never starts.
- Never point `JAVA_HOME` at a hard-coded host path, and never download a JDK
  into the checkout with a script. A script that searches host paths and
  calls `setParameter` runs too late to select an agent.
- When no agent advertises the needed JDK, run the Maven or Gradle step in a
  pinned `docker-image` on a Linux agent with Docker. The image must also
  contain every tool the build invokes: a bare `eclipse-temurin` image has no
  `git`, so a build with `git-commit-id` or a similar plugin needs an image
  that ships git, or a script step that installs it first. Check the build's
  plugins before choosing the image.
- macOS and iOS work needs a native compatible runtime, not a container.

For the full host-JDK and container decision, read the companion
[TeamCity JDK Selection](../../teamcity-jdk-selection/SKILL.md) skill when it
is installed. This guide stays usable without it.

## Validate the saved configuration

Validate the file that becomes the source of truth with
`teamcity pipeline validate <file>`. A local YAML parser proves syntax only,
and `pipeline push` does not validate. Apply the Script Parameter Gate from
[Build-step selection](build-step-selection.md) to local and stored YAML.
After a server-side correction, reconcile the checkout's `.teamcity.yml` with
the stored configuration and validate again.

## Check compatibility before queueing

Pull the stored YAML and verify that each `%name%` substitution is declared
or inherited. Check the exact job against every candidate agent and cloud
image. A generated job absent from the CLI's compatible and incompatible
lists has unverified compatibility; use the permitted Pipeline helper. Zero
compatible candidates is a defect to fix now, not to wait out.
When compatibility access is denied, record it as unverified and use
[Manual prerequisites](manual-prerequisites.md) if no other read works.

Confirm the final JDK inside the build with `"$JAVA_HOME/bin/java" -version`.
