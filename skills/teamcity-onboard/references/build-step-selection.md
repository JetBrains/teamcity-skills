# Build-step selection

- A dedicated runner for each build, test, and package command. A script
  step only when the schema has no runner, for glue, and for the `Status`
  step. Validate runner names and fields against the server's schema.
- Every test visible: a runner that reports tests, or JUnit XML with
  `xml-report`, as [Pipeline features](pipeline-features.md) describes.
- A new job when it runs in parallel with another, or uses another job's
  output. Every job pays its own agent start, checkout, and setup, so short
  work stays as steps in one job. Add `dependencies:` only when the job reads
  the other job's files; otherwise run the jobs in parallel.
- No parallel tests on the first run, as
  [Show the value](show-the-value.md#follow-ups) describes.
- A build status that shows what happens, as
  [Meaningful build status](#meaningful-build-status) describes.

## Gradle

- The Gradle runner with `tasks` from the repository's verified tasks.
- Pin the JDK as [Agents and runtimes](agents-and-runtimes.md) describes.
- Settings the sources must not carry go into an init script: a test
  timeout, or `ignoreFailures` so report steps still run after failed tests.
  A script step writes the init script on the agent; the runner passes it
  with `--init-script`. The build still fails on the failed tests.
- A task-graph error that says compilation consumes undeclared generator
  outputs: run generation and compilation as two Gradle runner steps.

## Maven

- The Maven runner with the repository's verified `verify`, `test`, or
  `package` goals. `verify` runs the tests.
- Keep the repository's Maven version with `maven-version`: the schema has
  `auto`, `bundled-3-0` to `bundled-3-9`, and `custom`, and no wrapper
  option. Take the version from `.mvn/wrapper/maven-wrapper.properties`.
- Runner arguments reach Maven without a shell, so quotes stay in the value.
  `-Dtest='!*IntegrationTest'` matched no class and left the job green with
  0 tests. Define a test subset with surefire `<excludes>`, added to
  `pom.xml` by a step on the agent, not with `-Dtest`: it also overrides
  TeamCity's parallel-test split.
- The runner passes `-B` itself. Do not repeat it in the arguments.
- A test timeout: `-Dsurefire.timeout=<seconds>`.

## Other stacks

- Node.js: the `node-js` runner, the schema's only Node runner. The npm,
  pnpm, or yarn commands go in `shell-script`. The step runs in the
  `docker-image` `node:lts` by default, not on the agent's Node: pin
  `docker-image: node:<version>` from `.nvmrc` or `engines`. For pnpm,
  `corepack enable` provides the version pinned in `package.json`. Set the
  job parameter `env.COREPACK_ENABLE_DOWNLOAD_PROMPT: '0'`, or Corepack's
  download notice on stderr becomes the job's failure text and hides the real
  error.
- .NET: the `dotnet-*` runners, one per command: `dotnet-build`,
  `dotnet-test`, `dotnet-publish`. `dotnet-test` runs VSTest. A project on
  Microsoft.Testing.Platform needs a script step that writes TRX or JUnit
  XML, and `xml-report`.
- Docker: the schema has no Docker runner. Docker commands go in a script
  step; any step can run inside a `docker-image`. When a build moves out of
  a Dockerfile onto the agent, carry over every build arg and build
  property: a server did not start without
  `-PindexingBackend=elasticsearch8`. Match the CPU architecture as
  [Agents and runtimes](agents-and-runtimes.md) describes.
- Python, Go, Rust, and others: the schema has no runner. Use the project's
  standard command in a script step, with JUnit XML as
  [Pipeline features](pipeline-features.md) describes.

## Script steps

- Every `type: script` step needs `script-content`. The schema has no
  `script` or `script-file` field.
- A script without a shebang runs under `/bin/sh`, dash on Ubuntu agents.
  Start every bash script with `#!/bin/bash`, or `set -o pipefail`, `[[ ]]`,
  and arrays fail. The failure can be silent: `[[: not found`, and the step
  still exits 0.
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

A generic "Running" in the builds list is not enough.

- Give every runner step a human-readable `name`. TeamCity shows the running
  step.
- In script steps, `echo "##teamcity[progressMessage '<stage>']"` at the
  start of each stage.
- Dedicated runners send no service messages, so each job ends with a script
  step named `Status`:
  `echo "##teamcity[buildStatus text='{build.status.text}, <summary>']"`.
  Keep `{build.status.text}` so TeamCity appends its own text. One short
  line.
- There is no run-always step. After a failing step, the later steps,
  `Status` included, are skipped, and TeamCity's own failure text stands.
