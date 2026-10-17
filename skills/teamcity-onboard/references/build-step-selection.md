# Build Step Selection

Choose TeamCity build steps that match the project technology and the active
TeamCity server's supported capabilities.

## Rules

- Prefer a dedicated TeamCity runner for the primary work when the schema
  exposes one.
- Use a generic script step only for project-specific glue, unsupported
  operations, or shell logic that would be less clear as a dedicated runner.
- Validate runner names, fields, and pipeline schema against the active
  server or existing configuration when they are not already known.
- Preserve checked-in CI intent. If the repository already describes
  multiple jobs or container validation, keep that structure unless you have
  a reason.
- Prefer the smallest configuration that proves the project's own build
  works.

## Technology Defaults

### Gradle

When the live Pipeline schema exposes `type: gradle`:

- Use the Gradle runner for the primary tasks.
- Set its `tasks` property from the repository's verified Gradle tasks.
- Schema validation does not check every runner-specific property. That is
  no reason for a script step.
- When the repository declares an exact JDK, use one of:
  - a discovered server-managed installation, with job-level `env.JAVA_HOME`;
  - a step-level official JDK container image pinned to that major version,
    when the repository is container-safe and the server confirms compatible
    Docker agents.
- The container is the preferred fallback for a missing JDK on ephemeral
  Linux agents. The host and its default Java stay untouched.
- Host-native macOS and iOS work stays outside that fallback.
- Use a script only for non-Gradle glue that the Gradle runner cannot
  express.

### Maven

When the live Pipeline schema exposes `type: maven`:

- Use the Maven runner for the primary lifecycle work.
- Put the repository's verified `verify`, `test`, or `package` invocation in
  its `goals` property.
- Preserve the Maven version or wrapper the repository selects, through a
  runner selector the target server supports.
- Use a script for that lifecycle work only when the dedicated runner is
  unavailable or cannot preserve a required wrapper or runtime. Report that
  concrete limitation.

### Other stacks

- Node.js: prefer a Node.js or npm-capable runner when the schema exposes one.
- .NET: prefer a .NET runner when available.
- Docker: prefer a Docker runner when the schema exposes one. Otherwise keep
  container validation as a clear script-based job. Match the agent's CPU
  architecture to the images; see
  [Agents, JDK, and compatibility](agents-and-jdk.md).
- Python, Go, Rust, and other stacks: use dedicated runners when the active
  server exposes them. Otherwise use the project's standard command in a
  script step.

## Script Parameter Gate

Pipeline schema validation can accept a step's `type` without checking its
runner-specific fields. Every `type: script` step has exactly one content
field: **`script-content`** with non-empty inline commands, or
**`script-file`** with a non-empty script path. The field `script` does not
exist. For example:

```yaml
steps:
  - type: script
    name: Check Docker
    script-content: |-
      echo "##teamcity[progressMessage 'Checking Docker']"
      docker info
```

Check these fields in the actual file before upload, then in the server-stored
YAML before you queue or wait. A valid result from `pipeline validate` does
not prove the script runner is usable. Virtual job step listings may be empty
while YAML-defined steps exist. A missing or blank content field produces
`Invalid step parameters: Script content must be specified`. Correct the
configuration before you check agent capacity. For a file source, verify
separately that checkout provides the file. This check does not prove shell
syntax, parameter resolution, or runtime compatibility.

## JVM Verification And Outputs

Before queueing, read back the stored Pipeline YAML with
`teamcity pipeline pull`. Check each job against the requested outcome, in
addition to the schema. Confirm:

- native runner types and their `goals` or `tasks`;
- explicit JDK selection;
- required agent capabilities;
- the publication rules on the job that produces each output.

The server's view of job settings can omit YAML-defined steps and artifacts,
so the pulled YAML is the source for this audit.

- Maven verification normally uses `verify` with tests enabled. A wrapper
  launcher alone is not enough if its supporting files are missing; use a
  supported installed Maven version when the repository permits it.
- Importing JUnit results and publishing raw XML as an artifact are separate
  operations. When both are requested, configure both. A green Tests tab or a
  published JAR does not prove that the XML is downloadable.
- Inspect Gradle generated-source dependencies before you combine tasks. When
  a task-graph validation error proves that compilation consumes undeclared
  generator outputs, and sources must stay unchanged, separate generation and
  compilation into successive native Gradle runner invocations. Validation
  stays enabled, and Gradle runners stay Gradle runners.
- Testcontainers may also run during code generation. Any isolated job that
  needs containers, including packaging when applicable, needs a durable
  Docker-capable agent requirement and an explicit `docker info` preflight.
  Derive the selector from this server. An OS or JDK requirement alone does
  not prove Docker capability. Keep tests out of a requested package-only
  job. Run them in the test job, with its own report publication.

After the requested chain and outputs pass, finish with that evidence. A
complete result needs no further build or discovery.

## Meaningful Build Status

Every generated or modified pipeline, build step, and build script must
report a live, meaningful status. A generic "Running" in the builds overview
is incomplete. Dedicated runners emit no service messages, so each job ends
with a script step named `Status` that echoes the `buildStatus` line below
with the job's summary.

- Give every dedicated runner step an explicit, human-readable `name`.
  TeamCity shows the running step in the overview.
- In script steps, `echo` `##teamcity[progressMessage '<stage>']` at the
  start of each stage. When one stage wraps several commands, use
  `##teamcity[progressStart '<stage>']` and `progressFinish` with identical
  text.
- End the stage that carries the result worth seeing in the builds list with
  `##teamcity[buildStatus text='{build.status.text}, <summary>']`. Keep
  `{build.status.text}` so TeamCity appends the text. One short line, no log
  excerpts.
- TeamCity recognizes service messages only at the start of a line on
  stdout, so `echo` each one as its own command. Escape with `|`: `|'`,
  `|n`, `|r`, `||`, `|[`, `|]`.

On Windows use `Write-Host "##teamcity[...]"` (PowerShell) or
`echo ##teamcity[...]` (cmd).

## Output

In the final report, say why you chose each primary step type. Give the
reason for every script step.
