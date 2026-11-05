# Agents and runtimes

Read this before you write YAML and again before you queue. A wrong
`runs-on` or JDK stops the onboarding: the build queues forever because no
agent matches. Every decision comes from the server's evidence.

## Read the server

```bash
teamcity api '/app/rest/agentPools?locator=project:(id:<project-id>)&fields=agentPool(name,agentTypes(agentType(id,name)))'
teamcity api '/app/rest/agentTypes/id:<type-id>?fields=availableParameters($locator(name:(value:JDK_,matchType:contains)),property(name,value))'
teamcity api '/app/rest/agentTypes/id:<type-id>?fields=availableParameters($locator(name:env.JDK_21_0),property(name,value))'
teamcity agent list --connected --enabled --authorized \
  --limit 0 --json=id,name,typeId,pool.name
teamcity agent jobs <agent-id> --incompatible --json
```

The pools give the agent types the project can use. A hosted agent connects
only when a job starts, so on a new server `agent list` is empty: take the
types from the pools. A type's parameters give the installed software, the
default `JAVA_HOME`, `teamcity.agent.hardware.cpuCount`,
`teamcity.agent.hardware.memorySizeMb`, and
`teamcity.agent.build.minute.cost`.

Read only the parameters you need. A type has hundreds of them. Read a family
with `contains`, one call per family: `JDK_`, `version`, `docker`, `os.`,
`teamcity.agent.hardware`, `minute.cost`. Read the exact name for each
requirement key and `%env.*%` parameter the YAML uses. A pattern with `|`
fails with HTTP 400. Dump all parameters,
`availableParameters(property(name,value))`, only as a last resort, when the
filtered reads cannot answer. Save the dump outside the checkout, search it,
and never print it.

The public "JetBrains-hosted agents" docs are outdated. Seen on TC Cloud
Linux: JDK 8 to 25 with the default `JAVA_HOME` on JDK 25; .NET 6, 8, 9,
10; Node 22 and 24; Python 3.8 to 3.14; Docker 29 and Compose; Chrome,
Firefox, xvfb.

## Choose `runs-on`

- Start from the bare selector the server is known to dispatch. Add one
  requirement only after a build failed without it. Each `os-family`,
  `arch`, Docker, or custom key risks zero matches.
- Take the name from the pools. The schema's `runs-on` enum does not match
  the server: the server also runs every type name from the pools, such as
  `Ubuntu-24.04-Large-Arm64`, and the form
  `jetbrains-hosted: [capacity, arch, os-family, os-version]`, which
  `pipeline validate` rejects. The enum names `Mac-Medium`, which matched no
  image. `pipeline push` accepts any name, so it proves nothing. GitHub
  labels and selectors from another server are invalid.
- Docker: Linux types have `docker.version` and `docker.server.osType=linux`.
  Windows types run only Windows containers; macOS types have no Docker.
  Run `docker info` as the first step of a job that needs it.
- Match the agent's CPU architecture to the images the build pulls,
  Testcontainers included. An amd64-only image on an arm64 agent fails with
  `exec format error`. For an architecture requirement use the type's exact
  `teamcity.agent.jvm.os.arch` value: hosted types say `amd64` and
  `aarch64`, while a workflow may say `x86_64` and `arm64`.

## Choose the size

Start on Medium. Take Large only with evidence: heap settings above about
6 GB (`org.gradle.jvmargs`, `-Xmx`), or services such as Elasticsearch.
After the run, resize from the performance monitor, as
[Show the value](show-the-value.md) describes. Seen on TC Cloud Linux, per
minute of build: Small 2 CPU, 4 GB, 10 credits; Medium 4 CPU, 8 GB, 20;
Large 8 CPU, 15 GB, 40; XLarge 16 CPU, 30 GB, 80. Windows costs twice as
much, macOS more than seven times. Read the real numbers from the type's
parameters.

## Select the JDK

Always pin the JDK: Gradle 8.x cannot run on the default JDK 25.

- Take the JDK that runs the build from `pom.xml`, the Gradle toolchain, the
  workflow's `setup-java`, and the README. Resolve a conflict before you
  write YAML. The bytecode target can be an older version than the JDK that
  runs the build.
- A key such as `env.JDK_21_0` shows an installed JDK on an agent. Take the
  real key from the agent type's parameters. Set the step's `jdk-home` or
  the job's `parameters.env.JAVA_HOME` to it, for example `%env.JDK_21_0%`.
  A step's `jdk-home` overrides `JAVA_HOME`: check both on every job in the
  stored YAML. A key no agent has blocks dispatch, and no build step can fix
  it: a hard-coded host path, a download script, or `setParameter` run too
  late.
- When no agent has the needed JDK, run the Maven or Gradle step in a pinned
  `docker-image` on a Linux agent with Docker. The job then needs Docker on
  the agent, not a host `env.JDK_*` key. The image must contain every tool
  the build runs: a bare `eclipse-temurin` image has no `git`, so a build
  with `git-commit-id` needs an image that ships git.
- macOS and iOS work needs a native runtime. Containers do not apply.
- Check the Java the build really uses: `"$JAVA_HOME/bin/java" -version` in
  a script step, or the version in the Maven or Gradle output, inside the
  container when there is one. A bare `java` follows `PATH` and can find
  another JDK. Report the observed version.

## Other runtimes

Take the version from `global.json`, `.nvmrc`, `engines`, or
`.python-version`, and find it in the type's parameters:
`dotnetcore.versions`, `node.22.version`, `python.312.version`. A version
no type has needs a pinned `docker-image`, as for the JDK.

## Check compatibility before queueing

1. `pipeline pull` the stored YAML. Verify that each `%name%` substitution is
   declared or inherited. Apply the script-step checks from
   [Build-step selection](build-step-selection.md).
2. Check every job, dependent jobs included, against the candidate types:
   each requirement key and each `%env.*%` parameter it uses must be in a
   type's parameters, with the exact value; a change of letter case does not
   create a key. `agent jobs --incompatible` works only for a connected
   agent and lists the unmet requirements.
3. Count the compatible types. Zero is a defect to fix now. A
   `permission_denied` on the check means unverified; record it and
   continue.
4. After every change of the stored YAML, repeat the check.

After queueing, TeamCity counts the matches itself. Read each queued job:
`teamcity api '/app/rest/buildQueue/id:<job-run-id>?fields=waitReason,compatibleCloudImages(count,cloudImage(name))'`.
A count of 0 is a wrong `runs-on`: fix it now. The wait reason "There are no
idle compatible agents" is the same for 0 matches and for busy agents, so
read the count. [Verify a build](verify-build.md) says what to do with a job
that stays queued.
