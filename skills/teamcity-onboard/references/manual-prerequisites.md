# Manual prerequisites

Write one when the CLI cannot complete a required operation safely. Be
specific. "Configure the connection" and "grant access" are too vague.

For each prerequisite give:

1. **Owner**: the role or team with the required permission.
2. **Scope**: the exact TeamCity server and the project, by ID.
3. **Action**: the TeamCity UI path or the CLI command. Use known labels.
   When a label is unknown, name the setting and the object. Do not invent a
   field name.
4. **Values**: known IDs, URLs, branch, connection, agent image, parameter
   name. Mark a secret that must come from secure storage.
5. **Proof**: the saved object, test, or build state that shows it is done.
6. **Resume signal**: an object ID, a redacted error, or a build URL.

When the operation is unknown, name the missing capability and ask for a
narrow operation. Unrestricted REST writes are out of scope.
