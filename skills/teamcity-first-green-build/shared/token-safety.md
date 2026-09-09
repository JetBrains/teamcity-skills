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
- If a tool returns a response containing secrets, redact them before showing
  output to the user.

## When Credentials Are Missing

If credentials or permissions are missing:

1. State the exact operation that is blocked.
2. Name the TeamCity permission, token scope, or VCS permission that appears
   required, if known.
3. Provide the next safe action the user can take.
4. Do not work around permission failures by using unrelated CI systems.
