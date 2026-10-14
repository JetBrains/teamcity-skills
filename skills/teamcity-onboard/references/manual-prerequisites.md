# Manual prerequisites

Use this guide when the available CLI and MCP tools cannot complete a
required operation safely. Give a specific request. "Configure the
connection" and "grant access" are too vague.

For each prerequisite, give:

1. **Owner**: role or team with the required permission.
2. **Scope**: exact TeamCity server and project. State the exact project
   level. The change usually belongs in the child project.
3. **Action**: TeamCity UI path or supported CLI or MCP command. Use known
   labels. When a label is unknown, name the setting and the object. Do not
   invent a field name.
4. **Values**: known IDs, URLs, branch, connection, agent image, and parameter
   name. Mark a secret that must come from secure storage.
5. **Proof**: saved object, test, or build state.
6. **Resume signal**: object ID, redacted error, or build URL or ID.

When the manual operation is unknown, name the missing capability and ask for
a narrow operation. Example: create a VCS root with an inherited connection
in a named child project. Unrestricted REST writes are out of scope.
