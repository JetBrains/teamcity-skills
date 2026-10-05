# TeamCity tool policy

Apply these rules to every TeamCity operation.

- Use the TeamCity CLI or MCP tools. No shell REST calls through `teamcity api`,
  `curl`, `wget`, or another HTTP client.
- With the CLI, read `teamcity --version` and the relevant command help. Use
  first-class commands for projects, connections, VCS roots, pipelines, jobs,
  runs, and agents.
- When the CLI lacks an operation, inspect MCP tools and read their guide and
  schema. Confirm that the connection targets the requested server. Prefer a
  dedicated operation. Use a generic read only when its schema permits the
  exact request.
- When neither surface supports an operation, use
  [Manual prerequisites](manual-prerequisites.md). Keep permissions scoped.
- Confirm the TeamCity server before discovery or writes. Repair a mismatched
  tool, connection, or authenticated context first.
- An MCP create, update, or delete needs **brave mode** on that server. Safe
  mode allows reads and build queueing only. Brave mode does not grant project
  permissions.
- Validate changed TeamCity YAML or Kotlin DSL before queueing. A syntax-only
  YAML parse is not TeamCity validation.
- Use TeamCity service messages for meaningful live build status.
- Keep server facts only while the server, project, repository, and TeamCity
  object stay unchanged.

For configuration writes, prefer the CLI. Use MCP reads for discovery, logs,
tests, or personal-build queueing when the operation exists. Read
[VCS connections and authentication](vcs-connections-and-auth.md) before work
on connections or VCS roots.
