# TeamCity tool policy

Apply these rules to every TeamCity operation. Command syntax, flags, and
per-task workflows come from the `teamcity-cli` skill; load it first.

- Use first-class `teamcity` commands for projects, VCS roots, pipelines,
  jobs, runs, queue, and agents. No `teamcity api`, `curl`, `wget`, or another
  HTTP client, even though the CLI skill lists `teamcity api` as an escape
  hatch.
- Bind every command to the hand-over server with `TEAMCITY_URL=<server>`.
  The saved CLI default cannot select the target.
- When the CLI lacks an operation, inspect MCP tools and read their guide and
  schema. Confirm that the connection targets the requested server. An MCP
  create, update, or delete needs brave mode on that server. When neither
  surface supports the operation, use
  [Manual prerequisites](manual-prerequisites.md).
- Validate changed Pipeline YAML with `teamcity pipeline validate` before
  pushing or queueing. A syntax-only YAML parse is not TeamCity validation,
  and `pipeline push` does not validate.
- Use TeamCity service messages for meaningful live build status.
- Keep server facts only while the server, project, repository, and TeamCity
  object stay unchanged.
