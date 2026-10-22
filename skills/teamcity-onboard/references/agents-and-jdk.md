# Agents and JDK

Read this before you write YAML and again before you queue. A wrong
`runs-on` or JDK freezes an onboarding: the build queues forever because no
agent matches. Every decision comes from the server's evidence.

## Read the server

```bash
teamcity pipeline schema --refresh
teamcity agent list --connected --enabled --authorized \
  --limit 0 --json=id,name,typeId,pool.id,pool.name
teamcity agent jobs <agent-id> --incompatible --json
```

The schema gives the `runs-on` enum. The agent list gives the connected
agents. The incompatibility query says why an agent rejects a job. These
reads are the only way to inspect agents. Probe pipelines are forbidden.

The public "JetBrains-hosted agents" docs are outdated. The installed
software, default `JAVA_HOME`, CPU, RAM, and cost of a hosted agent type are
in its parameters: `teamcity api '/app/rest/agentTypes/id:<typeId>'` with
`?fields=`. `typeId` comes from `agent list`. Seen on TC Cloud: JDK 8 to 25
with the default `JAVA_HOME` on JDK 25, Docker 29 and Compose, Node 22 and
24, xvfb, Chrome.

## Choose `runs-on`

- Start from the bare selector the server is known to dispatch. Add one
  requirement only after a build proved its absence. Each `os-family`,
  `arch`, Docker, or custom key risks zero matches.
- The schema's `runs-on` enum is incomplete. The server also accepts every
  hosted image name, for example `Ubuntu-24.04-Large-Arm64`, and the form
  `jetbrains-hosted: [capacity, arch, os-family, os-version]`.
  `pipeline validate` rejects both; `pipeline push` accepts them. Use a
  hosted name only when that agent type exists on this server. GitHub labels
  and selectors from another server are invalid.
- A requirement key must exist on an observed agent, with the exact value.
  Example: a Linux agent has `teamcity.agent.jvm.os.name=Linux` and no
  `teamcity.agent.jvm.os.family`, so `os-family=Linux` never schedules. A
  change of letter case does not create a key. A custom requirement in
  `self-hosted` uses `requirement`, `parameter`, and `value` from the schema.
- Docker: a job that needs it does not prove `docker.server.osType` exists.
  Use a confirmed Docker-capable selector, then run `docker info` as the
  job's first step.
- Match the agent's CPU architecture to the images the build pulls,
  Testcontainers included. An amd64-only image on an arm64 agent fails with
  `exec format error`. For an architecture requirement use the agent's exact
  `teamcity.agent.jvm.os.arch` value: an x86 agent may say `amd64` while the
  workflow says `x86_64`.
- Count the compatible agents for the exact job. A queued job with compatible
  but busy agents is a capacity wait.

## Select the JDK

Always pin the JDK. The hosted default `JAVA_HOME` is the newest JDK (25),
and Gradle 8.x cannot run on it.

- A key such as `env.JDK_21_0` advertises an installed JDK on an agent. Take
  the real key from the agent type's parameters. Set the step's `jdk-home` or
  the job's `parameters.env.JAVA_HOME` to it, for example `%env.JDK_21_0%`.
  A key no agent advertises blocks dispatch, and no build step can install
  the JDK because the build never starts. A hard-coded host path, a download
  script, or `setParameter` all run too late.
- When no agent advertises the needed JDK, run the Maven or Gradle step in a
  pinned `docker-image` on a Linux agent with Docker. The image must contain
  every tool the build invokes: a bare `eclipse-temurin` image has no `git`,
  so a build with `git-commit-id` needs an image that ships git.
- macOS and iOS work needs a native runtime. Containers do not apply.

The companion `teamcity-jdk-selection` skill, when installed, has the full
host-JDK and container decision.

## Check compatibility before queueing

1. `pipeline pull` the stored YAML. Verify that each `%name%` substitution is
   declared or inherited. Apply the script-step checks from
   [Build-step selection](build-step-selection.md).
2. Check the exact job against every candidate agent and cloud image. Read
   the unmet requirements and unresolved parameters for every job, dependent
   jobs included.
3. Count the compatible candidates. Zero is a defect to fix now, even when
   TeamCity says "no idle compatible agents": that message does not
   distinguish busy capacity from zero matches. A `permission_denied` on the
   check means unverified; record it and continue.
4. After every change of the stored YAML, repeat the check.

Dispatch is the final check. [Verify a build](verify-build.md) says what to
do with a job that stays queued.
