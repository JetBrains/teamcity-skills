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
- A hosted type name such as `Linux-Medium` or `Mac-Medium` compiles to
  `system.agent.name starts with <name>` plus
  `teamcity.agent.jbHosted equals true`. It dispatches only when the
  project's pools contain a JetBrains-hosted type, one whose parameters
  include `teamcity.agent.jbHosted`. On a server with only self-hosted
  agents every hosted name matches nothing. Take the name from the pools,
  never from the schema's enum or from another server: the enum names
  `Mac-Medium` on servers that have no such image, and the server runs
  names the enum lacks, such as `Ubuntu-24.04-Large-Arm64`. `pipeline push`
  accepts any name, so it proves nothing.
- `os-family: Linux` compiles to `teamcity.agent.jvm.os.family equals
  Linux`. Use it only when that parameter is in the type's parameters; many
  agents publish only `teamcity.agent.jvm.os.name`. For such agents write
  the object form,
  `- requirement: equals / parameter: teamcity.agent.jvm.os.name / value: Linux / name: Linux agent`,
  or `arch: <teamcity.agent.jvm.os.arch value>`.
- `self-hosted` takes only `arch`, `os-family`, `os-version`, `cpu`, `ram`,
  or an object with `requirement`, `parameter`, `name`, and `value`. The
  shorthand `- teamcity.agent.jvm.os.name: Linux` passes `pipeline push` and
  even builds, but fails `pipeline validate`. Use the object form.
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
  stored YAML. A key no agent has blocks dispatch, and no build step can
  make the key appear: a hard-coded host path, a download script, or
  `setParameter` run too late. Do not refer to a key no agent has.
- When no agent has the needed JDK, install the JDK inside the build as
  [Other runtimes](#other-runtimes) recommends. Set `env.JAVA_HOME` to it
  with `setParameter` and the Maven or Gradle step's `jdk-home` to
  `%env.JAVA_HOME%`; the job then has no `env.JDK_*` requirement.
- macOS and iOS work needs a native runtime. Containers do not apply.
- Check the Java the build really uses: `"$JAVA_HOME/bin/java" -version` in
  a script step, or the version in the Maven or Gradle output, inside the
  container when there is one. A bare `java` follows `PATH` and can find
  another JDK. Report the observed version.

## Other runtimes

Take the version from `go.mod` (`go` and `toolchain`), `global.json`,
`.nvmrc`, `engines`, or `.python-version`, and find it in the type's
parameters: `dotnetcore.versions`, `node.22.version`, `python.312.version`.
For a version no type has, compare two ways and take the faster one:

- **Install it in the job.** The first script step downloads the runtime
  into `%system.teamcity.build.tempDir%` and puts it first on `PATH` for the
  next steps:
  `##teamcity[setParameter name='env.PATH' value='<dir>/bin:%env.PATH%']`
  (`;` instead of `:` on Windows). Point the runtime's home variable at the
  new folder too: hosted agents set `GOROOT` to their old Go, and a new Go
  then uses the old standard library, so set
  `##teamcity[setParameter name='env.GOROOT' value='<dir>']`. Each job that
  needs the runtime installs it. Fast when the runtime is one archive or one install script, for
  example Go (`https://go.dev/dl/go<version>.<os>-<arch>.tar.gz`), .NET
  (`dotnet-install.sh --version <version>`), Node.js, or a JDK.
- **Run the steps in a pinned `docker-image`.** Linux agents only: macOS
  agents have no Docker, and Windows containers are slow and limited. Good
  when the repository already has a Dockerfile with the right image, or the
  runtime needs many system packages.

To compare, count what each run downloads: a clean hosted agent pulls the
image on every run (often 300 MB or more, 20–60 s), while a Go archive is
about 70 MB and 5–15 s. On macOS and Windows agents, install in the job.

## Check compatibility before queueing

1. `pipeline pull` the stored YAML. Verify that each `%name%` substitution is
   declared or inherited. Apply the script-step checks from
   [Build-step selection](build-step-selection.md).
2. Check every job, dependent jobs included, against the candidate types:
   each requirement key and each `%env.*%` parameter it uses must be in a
   type's parameters, with the exact value; a change of letter case does not
   create a key. No command reports the compatibility of a job that is not
   queued yet, so this comparison is yours to make.
3. Count the compatible types. Zero is a defect to fix now.
4. After every change of the stored YAML, repeat the check.

The server's own verdict comes with the first queued run. Right after
queueing, read each job run with `teamcity run view <job-run-id>`: it prints
the wait reason, the compatible agents and cloud images, and the
incompatible ones grouped by pool with the unmet requirement. `--json` lists
every entry under `compatibility` (CLI 1.6 or later). The wait reason
"There are no idle compatible agents" is the same for 0 matches and for
busy agents, so read the list, not the reason. Do not run
`agent jobs --incompatible` per agent: a large server returns thousands of
build types per agent.

Zero compatible entries names the cause. Read the incompatibility reasons
and act on the cause, not on the count:

| Reason in `run view` | Cause | Action |
| --- | --- | --- |
| `teamcity.agent.jbHosted equals true`, `system.agent.name starts with <name>` | `runs-on` is a hosted type name; the project has no JetBrains-hosted agents | Replace the name with `self-hosted` requirements built from a type the pools list |
| `teamcity.agent.jvm.os.family equals <os>` | `os-family`; these agents do not publish that parameter | `arch: <os.arch value>` or the object form on `teamcity.agent.jvm.os.name` |
| `Parameter '<key>' ...` for `env.JDK_*`, `docker.*`, or another key | no agent has the key | Install the runtime in the job or run the step in a container; drop the key |
| `Agent belongs to the pool not associated with the project` | the matching agents are in a pool the project cannot use | Not fixable in YAML: a [manual prerequisite](manual-prerequisites.md) to attach the pool |
| `Restricted by agent policy` | the agent runs only selected configurations | Not fixable in YAML: a manual prerequisite, or drop the target and say so |
| compatible entries > 0, all busy | capacity | Wait; change nothing |

Then `teamcity run cancel <head-run-id> --yes`, push the correction, and
queue again. Never leave a run in the queue, and never create probe
pipelines to test selectors: the first queued run of the real pipeline is
the probe. Delete any pipeline you created and no longer need with
`teamcity pipeline delete <id> --yes`. [Verify a build](verify-build.md)
says what to do with a job that stays queued.
