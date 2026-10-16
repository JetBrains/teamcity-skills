# TeamCity tool policy

Apply these rules to every TeamCity operation. Command syntax, flags, and
per-task workflows come from the `teamcity-cli` skill. Load it first.

- Use first-class `teamcity` commands for projects, VCS roots, pipelines,
  jobs, runs, queue, and agents. `teamcity api` is the last resort, only
  when no first-class command covers the operation. Its reads select named
  fields with `?fields=` and never a `properties` collection. Its writes
  never replace `pipeline validate` and `pipeline push`. `curl`, `wget`, and
  other HTTP clients are forbidden.
- Bind every command to the hand-over server with `TEAMCITY_URL=<server>`.
  The saved CLI default cannot select the target.
- This flow is CLI-only. The web step authenticates the CLI and nothing
  else; MCP tools are not set up for it. When neither a first-class command
  nor `teamcity api` covers an operation, use
  [Manual prerequisites](manual-prerequisites.md).
- Validate changed Pipeline YAML with `teamcity pipeline validate` before you
  push or queue. A local YAML parser proves syntax only. `pipeline push` does
  not validate.
- Use TeamCity service messages for a meaningful live build status.
- Keep server facts only while the server, project, repository, and TeamCity
  object stay unchanged.
