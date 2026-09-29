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

- Gradle: prefer a Gradle runner for Gradle tasks.
- Maven: prefer a Maven runner for Maven goals.
- Node.js: prefer a Node.js or npm-capable runner when the schema exposes one.
- .NET: prefer a .NET runner when available.
- Docker: prefer a Docker runner when the schema exposes one; otherwise keep
  container validation as a clear script-based job instead of dropping it.
- Python, Go, Rust, and other stacks: use dedicated runners when the active
  server exposes them; otherwise use the project's standard command in a script
  step.

## Meaningful Build Status

Every generated pipeline must report a live, meaningful status; a generic
"Running" in the builds overview is incomplete.

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
