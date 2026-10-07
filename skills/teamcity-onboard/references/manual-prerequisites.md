# Manual prerequisites

Use this guide when available CLI and MCP tools cannot complete a required
operation safely. Give a specific request, not “configure the connection” or
“grant access”.

For each prerequisite, provide:

1. **Owner** — role or team with the required permission.
2. **Scope** — exact TeamCity server and project. State when the change belongs
   in the child project, not an ancestor or `_Root`.
3. **Action** — TeamCity UI path or supported CLI/MCP command. Use known labels;
   otherwise name the setting and object without inventing a field name.
4. **Values** — known IDs, URLs, branch, connection, agent image, and parameter
   name. Identify a secret that must come from secure storage.
5. **Proof** — saved object, test, or build state.
6. **Resume signal** — object ID, redacted error, or build URL/ID.

When the manual operation is unknown, name the missing capability and ask for a
narrow operation. Example: create a VCS root with an inherited connection in a
named child project. Do not request unrestricted REST writes.
