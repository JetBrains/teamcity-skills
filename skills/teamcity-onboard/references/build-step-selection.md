# Build-step selection

Dedicated runners for the primary work when the schema exposes one. A script
step only for glue and the `Status` step. Validate runner names and fields
against the server's schema.

## Gradle

- The Gradle runner with `tasks` from the repository's verified tasks.
- Pin the JDK as [Agents and JDK](agents-and-jdk.md) describes.
- Settings the sources must not carry, such as a test timeout or
  `ignoreFailures` so report steps still run after failed tests, go into an
  init script. A script step writes it on the agent; the runner passes it
  with `--init-script`. The build still fails on the failed tests.
- A task-graph error that says compilation consumes undeclared generator
  outputs: run generation and compilation as two Gradle runner steps.

## Maven

- The Maven runner with the repository's verified `verify`, `test`, or
  `package` goals. `verify` runs the tests.
- Keep the repository's Maven version or wrapper through a runner selector
  the server supports. When the wrapper's supporting files are missing, use
  an installed Maven version.
- Runner arguments reach Maven without a shell, so quotes stay in the value.
  `-Dtest='!*IntegrationTest'` matched no class and left the job green with
  0 tests. Write `-Dtest=!*IntegrationTest`.
- `-Dtest` overrides surefire's includes and excludes. Parallel tests hand
  each batch its share through those excludes, so with `-Dtest` every batch
  runs nearly the whole suite while TeamCity still shows the batches. Define
  a subset with surefire `<excludes>`: a script step before Maven adds
  `<excludes><exclude>**/*IntegrationTest.java</exclude></excludes>` to the
  surefire configuration in the agent's copy of `pom.xml`. Nothing is
  committed. A test timeout: `-Dsurefire.timeout=<seconds>`.

## Other stacks

- Node.js: the Node.js or npm runner. Hosted agents have no pnpm;
  `corepack enable` provides the version pinned in `package.json`. Set the
  job parameter `env.COREPACK_ENABLE_DOWNLOAD_PROMPT: '0'`, or Corepack's
  download notice on stderr becomes the job's failure text and hides the real
  error.
- .NET: the .NET runner.
- Docker: the Docker runner when the schema exposes one. When a build moves
  out of a Dockerfile onto the agent, carry over every build arg and build
  property: a server did not start without
  `-PindexingBackend=elasticsearch8`. Match the CPU architecture as
  [Agents and JDK](agents-and-jdk.md) describes.
- Python, Go, Rust, and others: a dedicated runner when the server exposes
  one. Otherwise the project's standard command in a script step, with JUnit
  XML as [Pipeline features](pipeline-features.md) describes.

## Script steps

- Every `type: script` step has exactly one content field: `script-content`
  with inline commands, or `script-file` with a path. The field `script` does
  not exist. Schema validation does not check this; the run fails with
  `Invalid step parameters: Script content must be specified`. Check the
  field in your file and in the stored YAML before you queue.
- A script without a shebang runs under `/bin/sh`, dash on Ubuntu agents.
  Start every bash script with `#!/bin/bash`, or `set -o pipefail`, `[[ ]]`,
  and arrays fail.
- A long command gets `timeout <seconds> <command>`.
- Service messages are recognized only at the start of a line on stdout.
  `echo` each one as its own command. Escape with `|`: `|'`, `|n`, `|r`,
  `||`, `|[`, `|]`.

```yaml
steps:
  - type: script
    name: Check Docker
    script-content: |-
      #!/bin/bash
      echo "##teamcity[progressMessage 'Checking Docker']"
      docker info
```

## Meaningful build status

A generic "Running" in the builds list is incomplete.

- Give every runner step a human-readable `name`. TeamCity shows the running
  step.
- In script steps, `echo "##teamcity[progressMessage '<stage>']"` at the
  start of each stage.
- Dedicated runners emit no service messages, so each job ends with a script
  step named `Status`:
  `echo "##teamcity[buildStatus text='{build.status.text}, <summary>']"`.
  Keep `{build.status.text}` so TeamCity appends its own text. One short
  line.
- There is no run-always step. After a failing step, the later steps,
  `Status` included, are skipped, and TeamCity's own failure text stands.
