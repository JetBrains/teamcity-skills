# Tool policy and secrets

Rules for every TeamCity operation. Command syntax comes from the
`teamcity-cli` skill's command reference (`references/commands.md`).

## Tools

- Run `teamcity` as configured, with no server environment variables or
  flags, as [the skill](../SKILL.md#before-the-first-command) says. This
  overrides the `teamcity-cli` skill's advice to pick a server per command
  with `TEAMCITY_URL`.
- Use first-class `teamcity` commands. Use `teamcity api` only when no
  command covers the operation: read named fields with `?fields=`, and never
  change a pipeline with it; use `pipeline validate` and `pipeline push`.
- Every HTTP call to TeamCity goes through the CLI: no `curl`, `wget`, or
  other HTTP clients. `gh` reads of GitHub Actions runs are allowed, as
  [Project inspection](project-inspection.md) describes.
- The flow is CLI-only. MCP tools are not set up. When neither a first-class
  command nor `teamcity api` covers an operation, write a
  [manual prerequisite](manual-prerequisites.md).

## Secrets

- Never print tokens, secrets, passwords, private keys, or authorization
  headers.
- Never ask the user for a secret value. Never accept one in chat. When a job
  needs a secret, give the link to the pipeline's secrets settings page, name
  the parameter, and say what to store there. Build, test, and package
  usually need none.
- When a response contains a secret, do not repeat it anywhere. Tell the user
  it was exposed: revoke or rotate it at the issuer, replace it in TeamCity
  secure storage, retry with the replacement.
- When a permission is missing, name the blocked operation and the permission
  that appears required, and give the user the next safe action.
