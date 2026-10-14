# Agents, JDK, and compatibility

Use this guide before you write the pipeline YAML, and again before you
queue. A wrong `runs-on` or JDK selection freezes an onboarding: the build
queues forever because no agent matches. Every decision below comes from the
server's evidence.

## Read the server

```bash
TEAMCITY_URL=<server> teamcity pipeline schema --refresh
TEAMCITY_URL=<server> teamcity agent list --connected --enabled --authorized \
  --limit 0 --json=id,name,typeId,pool.id,pool.name
TEAMCITY_URL=<server> teamcity agent jobs <agent-id> --incompatible --json
```

The schema gives the `runs-on` enum. The agent list gives the connected
agents. The incompatibility query explains why an agent rejects a job (the
CLI skill's agents workflow has the fields). For generated jobs absent from
the CLI compatibility lists, use the permitted Pipeline compatibility helper
described in [Build diagnostics](build-diagnostics.md). These reads are the
only way to inspect agents; the deliverable rule in the skill applies.

## Choose `runs-on`

- Least requirement first: the bare selector the server is known to dispatch,
  with no sub-requirement. Add one requirement only after a build proved its
  absence. Each `os-family`, `arch`, Docker, or custom key risks zero matches.
- Use a hosted selector from the schema's `runs-on` enum only when TeamCity
  confirms a compatible image, or a capability observed on a connected agent.
  GitHub labels, selectors from another server, and temporary VM names are
  invalid.
- Add only the OS, JDK, Docker, and parameter requirements the workflow
  needed. Each one shrinks the set of compatible agents.
- An `os-family` or similar key must exist on an observed agent. A change of
  letter case does not create a key.
- A custom requirement in `self-hosted` uses `requirement`, `parameter`, and
  `value` from the schema. A bare parameter name is invalid.
- Match the agents' CPU architecture to the images the build pulls, including
  Testcontainers images. An amd64-only image on an arm64 agent fails with
  `exec format error`. Select a verified x86-capable agent for such an image.
  If you add an architecture requirement, use the agent's exact
  `teamcity.agent.jvm.os.arch` value. An x86 agent may advertise `amd64`
  while the workflow says `x86_64`.
- Count compatible agents and cloud images for the exact job. Each parallel
  test batch needs one agent at the same time to achieve a speedup. A queued
  batch with compatible but busy agents is a capacity wait.

For every custom requirement, check both its parameter name and its value on
the candidate set. Example: a Linux agent advertises
`teamcity.agent.jvm.os.name=Linux` but has no `teamcity.agent.jvm.os.family`
parameter, so an `os-family=Linux` requirement cannot schedule. The same
applies to `docker.server.osType`: a job that needs Docker does not prove the
key exists. Use a confirmed Docker-capable selector or parameter, then run
`docker info` in the job. Treat the compatibility helper's unresolved
parameters as dispatch blockers.

## Select the JDK

A key such as `env.JDK_21_0` advertises an installed JDK path on an agent.
The name is an example. Take the actual key from the agent's parameters or an
available TeamCity tool. The incompatibility query confirms an unmet
requirement only; it does not list the agent's parameters.

- Set the job's `parameters.env.JAVA_HOME` to the observed key, for example
  `%env.JDK_21_0%`. This selects that installation for Maven or Gradle. A key
  no agent advertises blocks dispatch, and no build step can install the JDK
  because the build never starts.
- `JAVA_HOME` always points at an observed agent key. A hard-coded host path
  may not exist on the chosen agent. A script that downloads a JDK, or that
  searches host paths and calls `setParameter`, runs too late to select an
  agent.
- When no agent advertises the needed JDK, run the Maven or Gradle step in a
  pinned `docker-image` on a Linux agent with Docker. The image must contain
  every tool the build invokes. Example: a bare `eclipse-temurin` image has
  no `git`, so a build with `git-commit-id` or a similar plugin needs an
  image that ships git, or a script step that installs it first. Check the
  build's plugins before you choose the image.
- macOS and iOS work needs a native compatible runtime. Containers do not
  apply.

For the full host-JDK and container decision, read the companion
[TeamCity JDK Selection](../../teamcity-jdk-selection/SKILL.md) skill when it
is installed. This guide stays usable without it.

## Validate the saved configuration

Validate the file that becomes the source of truth with
`teamcity pipeline validate <file>`; see the validation rule in
[TeamCity tool policy](teamcity-tool-policy.md). Apply the Script Parameter
Gate from [Build-step selection](build-step-selection.md) to local and
stored YAML. After a server-side correction, reconcile the checkout's
`.teamcity.yml` with the stored configuration and validate again.

## Check compatibility before queueing

1. Pull the stored YAML. Verify that each `%name%` substitution is declared
   or inherited.
2. Check the exact job against every candidate agent and cloud image. Use
   the permitted Pipeline helper when the CLI does not include generated
   jobs. Read the unmet requirements and unresolved parameters for every
   job, including jobs with dependencies.
3. Count the compatible candidates. Zero is a defect to fix now, even when
   TeamCity says "no idle compatible agents". That message does not
   distinguish busy capacity from zero matches. A generated job absent from
   both CLI lists has unverified compatibility; so has a `permission_denied`
   on the check.
4. After you change the stored YAML, repeat the check before queueing.
5. Dispatch is the final check. If the job is still queued after two
   minutes, strip it to the bare selector, push, and requeue with
   `--rebuild-deps`. Ten minutes in the queue is the maximum.

When compatibility access is denied, record it as unverified. Use
[Manual prerequisites](manual-prerequisites.md) if no other read works.

Confirm the final JDK inside the build with `"$JAVA_HOME/bin/java" -version`.
