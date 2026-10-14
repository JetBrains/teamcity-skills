# Token Safety

TeamCity actions use the permissions of the configured credential. Handle that
credential as production infrastructure access.

## Rules

- Never print full tokens, secrets, passwords, private keys, or authorization
  headers.
- Prefer least-privilege TeamCity tokens or credentials scoped to the task.
- Use personal builds for validation when possible.
- Do not switch from a restricted token to an admin token unless the user
  explicitly asks and understands the impact.
- Avoid storing tokens in repository files.
- Use first-class CLI fields for build and queue reads. When they are
  insufficient, discover the current environment's TeamCity MCP tools, read
  the relevant guide and schemas, verify the target server, and use a dedicated
  read operation. A generic MCP read is acceptable only when its schema
  explicitly permits a narrow field projection for one known object. Do not
  dump a full object or request its `properties` collection: it can contain
  inherited parameters, and a server may return a value that was expected to
  be masked.

- If a tool returns a response containing a secret, do not repeat it in
  commentary, reports, commits, or issue text. Tell the user that the secret
  was exposed and give the concrete recovery: revoke/rotate it at its issuer,
  replace it in TeamCity secure storage, and retry only with the replacement.

## When Credentials Are Missing

If credentials or permissions are missing:

1. State the exact operation that is blocked.
2. Name the TeamCity permission, token scope, or VCS permission that appears
   required, if known.
3. Provide the next safe action the user can take.
4. Do not work around permission failures by using unrelated CI systems.
