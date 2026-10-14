# TeamCity tool policy

Apply these rules to every TeamCity operation. Command syntax, flags, and
per-task workflows come from the `teamcity-cli` skill. Load it first.

- Use first-class `teamcity` commands for projects, VCS roots, pipelines,
  jobs, runs, queue, and agents. `teamcity api`, `curl`, `wget`, and other
  HTTP clients are forbidden, even though the CLI skill lists `teamcity api`.
- Bind every command to the hand-over server with `TEAMCITY_URL=<server>`.
  The saved CLI default cannot select the target.
- When the CLI lacks an operation, inspect the MCP tools. Read their guide and
  schema. Confirm that the connection targets the requested server. An MCP
  create, update, or delete needs brave mode on that server. When neither the
  CLI nor MCP supports the operation, use
  [Manual prerequisites](manual-prerequisites.md).
- Validate changed Pipeline YAML with `teamcity pipeline validate` before you
  push or queue. A local YAML parser proves syntax only. `pipeline push` does
  not validate.
- Use TeamCity service messages for a meaningful live build status.
- Keep server facts only while the server, project, repository, and TeamCity
  object stay unchanged.
