# Token Safety

TeamCity actions use the permissions of the configured credential. Handle
that credential as access to production infrastructure.

## Rules

- Never print full tokens, secrets, passwords, private keys, or authorization
  headers.
- Prefer least-privilege TeamCity tokens or credentials scoped to the task.
- Use personal builds for validation when possible.
- Switch from a restricted token to an admin token only when the user
  explicitly asks and understands the impact.
- Keep tokens out of repository files.
- Use first-class CLI fields for build and queue reads. When they are not
  enough:
  1. Find the TeamCity MCP tools in the current environment.
  2. Read their guide and schemas.
  3. Verify the target server.
  4. Use a dedicated read operation.
- A generic MCP read is acceptable only when its schema explicitly permits a
  selection of a few named fields for one known object. Do not dump a full
  object or request its `properties` collection. It can contain inherited
  parameters, and a server may return a value that should be masked.
- If a tool returns a response that contains a secret, do not repeat it in
  commentary, reports, commits, or issue text. Tell the user that the secret
  was exposed and give the concrete recovery: revoke or rotate it at its
  issuer, replace it in TeamCity secure storage, and retry only with the
  replacement.

## When Credentials Are Missing

If credentials or permissions are missing:

1. State the exact operation that is blocked.
2. Name the TeamCity permission, token scope, or VCS permission that appears
   required, if known.
3. Give the next safe action the user can take.
4. Do not work around a permission failure with another CI system.
