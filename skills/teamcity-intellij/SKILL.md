---
name: teamcity-intellij
description: Use when working with TeamCity CI/CD from an IntelliJ-based IDE — inspecting builds and logs, investigating failures, triggering runs, or changing projects and pipelines — and when the user pastes a TeamCity build URL. Says where the IDE's bundled `teamcity` CLI is (it is not on PATH) and how to choose between it and the TeamCity MCP tools.
---

# TeamCity CI/CD from this IDE

## The CLI is bundled, not on PATH

The TeamCity IntelliJ plugin ships the `teamcity` CLI in its own plugin directory. Call it **by absolute path, quoted** — the path can contain spaces:

```bash
"{{TEAMCITY_CLI_PATH}}" auth status --no-input
```

When a prompt or another skill mentions `teamcity`, run this path instead.

The IDE fills in the path above. If you still see `{{TEAMCITY_CLI_PATH}}`, resolve the CLI yourself: look for
`teamcity-cli/teamcity` (`teamcity-cli/teamcity.exe` on Windows) in the `teamcity` plugin directory of the running
IDE, then for a `teamcity` on PATH.

Pass `--no-input` to every command: an agent terminal is a real terminal, where a prompt blocks the run and nobody can
answer it.

The plugin owns this binary and replaces it on update. If the output says that a newer CLI exists, ignore it: never run
`teamcity update` and never install a CLI yourself.

The CLI ships its own skills, bundled in this IDE next to this one: `teamcity-cli`, and any other skill the installed
CLI provides. Load the `teamcity-cli` skill (or another one that fits the task) and read its reference files instead of
guessing:

* `references/commands.md` — every command and flag.
* `references/workflows/` — one document per task, for example `investigate-failure.md`, `run-builds.md`,
  `pipelines.md`, `connections-and-vcs.md`. Open the document that fits your task before you plan the work, not after a
  command has failed.
* `references/output.md` — JSON and plain output for parsing.

## CLI first, MCP tools second

If the user approved it, the plugin also registers the MCP tools and guides of the connected TeamCity server. The
guides are MCP resources with documentation and tips. By default, the MCP server runs in safe mode: it allows reads and
queueing a build. A TeamCity administrator can enable brave mode, which also allows writes.

**The CLI is the primary tool.** It works whatever the MCP configuration of the server is, and it is the only side that
sees the local working copy: linking the repository, a personal build from uncommitted changes, local pipeline YAML,
downloading artifacts. MCP talks to the server only.

**If one side is missing:** no MCP server configured, do everything through the CLI. No usable CLI, you are limited to
MCP.

Use the MCP tools as the second path: when a single tool call is simpler than a CLI command, or when a feature exists
only in MCP. Read the matching MCP guide first, never guess the APIs.

**Denied with 403 or "Access denied"?** This is about permissions, and you cannot know them in advance. The CLI and the
MCP server are authorized separately and can hold different tokens with different rights, so a call denied through MCP
can still work through the CLI, and the other way round. Report what was denied, and suggest that the user gets a token
with more rights by running `"{{TEAMCITY_CLI_PATH}}" auth login -s <url>` in their own terminal.

## Before the first command

A machine can have several TeamCity servers configured, each with its own login and its own rights.
Settle which one you work with before the first command.

1. **Find the server.** `auth status --no-input` prints the servers the CLI knows, marks the default one and shows each
   token with its expiry. Prefer the server this repository is linked to (`teamcity.toml`). Ask the user if there is no
   link and no default. Say in your answer which server you used, and keep one task on one server.
2. **Not authorized, or token expired?** You cannot sign in for the user. Signing in needs a browser and a terminal
   that can answer questions: with `--no-input` the CLI takes only a token, which must not travel through the chat, or
   guest access, which is anonymous and usually disabled. Tell the user which server it is, and ask them to sign in
   themselves — by running `"{{TEAMCITY_CLI_PATH}}" auth login -s <url>` in their own terminal.

Build logs are large. Write them to a file and read the file, rather than printing a log into the conversation.

## Command syntax

`--help` is the source of truth and always matches the installed version — do not guess flags:

```bash
"{{TEAMCITY_CLI_PATH}}" --help
"{{TEAMCITY_CLI_PATH}}" run --help
```
