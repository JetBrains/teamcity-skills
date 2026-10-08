# Build Step Selection

Choose TeamCity build steps that match the project technology and the active
TeamCity server's supported capabilities.

## Rules

- Prefer dedicated TeamCity runner or pipeline step types for primary
  build/test/package work when they are available.
- Use a generic script step only for project-specific glue, unsupported
  operations, or shell logic that would be less clear as a dedicated runner.
- Validate runner names, fields, and pipeline schema against the active server
  or existing configuration when they are not already known.
- Preserve checked-in CI intent. If the repository already describes multiple
  jobs or container validation, do not collapse that shape without a reason.
- Prefer the smallest configuration that proves the build, tests, and expected
  packaging or container checks work.

## Technology Defaults

- Gradle: when the live Pipeline schema exposes `type: gradle`, use the Gradle
  runner for primary Gradle build, test, and package tasks. Set its `tasks`
  property from the repository's verified Gradle tasks. Do not substitute a
  generic script merely because schema validation does not validate every
  runner-specific property. When the repository declares an exact JDK, use a
  discovered server-managed installation and set job-level `env.JAVA_HOME`, or
  use a step-level official JDK container image pinned to that major version
  when the repository is container-safe and compatible Docker agents are
  programmatically confirmed. The container is the preferred fallback for an
  otherwise missing JDK on ephemeral Linux agents; do not mutate the host or
  rely on its default Java. Keep host-native macOS/iOS work outside that
  fallback. Use a script only for non-Gradle glue that the Gradle runner cannot
  express.
- Maven: when the live Pipeline schema exposes `type: maven`, use the Maven
  runner for the primary lifecycle work and put the repository's verified
  `verify`, `test`, or `package` invocation in its `goals` property. Preserve
  the repository-selected Maven version or wrapper through a runner selector
  supported by the target server. Use a script for that lifecycle work only
  when the dedicated runner is unavailable or cannot preserve a required
  wrapper/runtime, and report that concrete limitation.
- Node.js: prefer a Node.js or npm-capable runner when the schema exposes one.
- .NET: prefer a .NET runner when available.
- Docker: prefer a Docker runner when the schema exposes one; otherwise keep
  container validation as a clear script-based job instead of dropping it.
  Match the agent's CPU architecture to the images the build pulls, including
  Testcontainers images: an amd64-only image on an arm64 agent fails with
  `exec format error`.
- Python, Go, Rust, and other stacks: use dedicated runners when the active
  server exposes them; otherwise use the project's standard command in a script
  step.

## Script Parameter Gate

Pipeline schema validation can accept a step's `type` without checking its
runner-specific fields. For every `type: script` step, use **`script-content`**
for non-empty inline commands, or **`script-file`** for a non-empty script path;
do not use `script`, and do not supply both sources. For example:

```yaml
steps:
  - type: script
    name: Check Docker
    script-content: |-
      echo "##teamcity[progressMessage 'Checking Docker']"
      docker info
```

Check these fields in the actual file before upload, then in the server-stored
YAML before queueing or waiting. `pipeline validate` returning valid is not
proof that the script runner is usable; virtual job step listings may even be
empty while YAML-defined steps exist. A missing/blank content field produces
`Invalid step parameters: Script content must be specified`; correct the
configuration before assessing agent capacity. For a file source, separately
verify that checkout provides the file. This check does not prove shell syntax,
parameter resolution, or runtime compatibility.

## JVM Verification And Outputs

Before queueing, read back the stored Pipeline YAML and check each job against
the requested outcome, not only against the schema. Confirm native runner
types and their `goals`/`tasks`, explicit JDK selection, required agent
capabilities, and the publication rules on the job that produces each output.
Materialized Pipeline job settings can omit YAML-defined steps and artifacts;
use `teamcity pipeline pull` for this audit.

- Maven verification normally uses `verify` without skipping tests. A wrapper
  launcher is not sufficient if its supporting files are missing; use a
  supported installed Maven version when the repository permits it.
- Importing JUnit results and publishing raw XML as an artifact are separate
  operations. When both are requested, configure both; a green Tests tab or a
  published JAR does not prove that the XML is downloadable.
- Inspect Gradle generated-source dependencies before combining tasks. If a
  task-graph validation error proves that compilation consumes undeclared
  generator outputs and sources must stay unchanged, separate generation and
  compilation into successive native Gradle runner invocations. Do not disable
  validation or replace all Gradle runners with scripts as a workaround.
- Testcontainers may also be used by code generation. Any isolated job that
  needs containers, including packaging when applicable, needs a durable
  Docker-capable agent requirement and an explicit `docker info` preflight.
  Derive the selector from this server; an OS/JDK requirement alone is not
  Docker capability evidence. Keep tests out of a requested package-only job
  and run them in the test job, with its own report publication.

After the requested chain and outputs pass, finish with that evidence. Do not
start another build or continue discovery to polish an already complete result.

## Meaningful Build Status

Every generated or modified pipeline, build step, and build script must report
a live, meaningful status; a generic "Running" in the builds overview is
incomplete.

- Give every dedicated runner step an explicit, human-readable `name` —
  TeamCity shows the running step in the overview.
- In script steps, `echo` `##teamcity[progressMessage '<stage>']` at the start
  of each stage; when one stage wraps several commands, use
  `##teamcity[progressStart '<stage>']` / `progressFinish` with identical text.
- End the stage carrying the result worth seeing in the builds list with
  `##teamcity[buildStatus text='{build.status.text}, <summary>']`, keeping
  `{build.status.text}` so the text is appended, not replaced. One short line,
  no log excerpts.
- Service messages are only recognized at the start of a line on stdout, so
  `echo` them as their own command. Escape with `|`: `|'`, `|n`, `|r`, `||`,
  `|[`, `|]`.

On Windows use `Write-Host "##teamcity[...]"` (PowerShell) or
`echo ##teamcity[...]` (cmd).

## Output

When reporting the final setup, mention why each primary step type was chosen,
especially when a script step was used instead of a dedicated runner.
