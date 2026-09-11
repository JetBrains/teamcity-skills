# teamcity-skills

A library of reusable **agent skills** for working with [TeamCity](https://www.jetbrains.com/teamcity/):
investigating build failures, driving a repository to its first green build,
using the `teamcity` CLI, and so on.

A skill is plain Markdown that tells a coding agent how to do a job properly —
which commands to run, in what order, and what to watch out for. What you see in
this repository is exactly what an agent reads. Nothing is generated.

## Using a skill

**With the `teamcity` CLI.** The CLI bundles the `teamcity-cli` skill and
installs it for you:

```bash
teamcity skill install          # installs into the agents it detects
teamcity skill list             # shows what is bundled
```

**By hand.** Copy the skill folder into wherever your agent looks for skills,
for example `.claude/skills/`:

```bash
cp -r skills/teamcity-first-green-build ~/.claude/skills/
```

**From Go.** Skills with an `embed.go` are published as Go packages, so a
program can depend on a specific, checksummed revision instead of vendoring a
copy:

```bash
go get github.com/JetBrains/teamcity-skills/skills/teamcity-cli@latest
```

```go
import teamcitycli "github.com/JetBrains/teamcity-skills/skills/teamcity-cli"

// teamcitycli.FS is an fs.FS rooted at the skill: SKILL.md, references/, _agents/
```

Each package embeds only its own skill, so importing one does not carry the
others.

## What is here

| Skill | Purpose |
| --- | --- |
| [`teamcity-cli`](skills/teamcity-cli/) | Drive the `teamcity` CLI: builds, logs, jobs, queues, agents, projects, pipelines. |
| [`teamcity-first-green-build`](skills/teamcity-first-green-build/) | Set up CI for a repository and get it to its first successful build. |
| [`teamcity-intellij`](skills/teamcity-intellij/) | Work with TeamCity from an IntelliJ-based IDE: where the bundled CLI is, and when to use it or the MCP tools. |

Also: [`prompts/`](prompts/) for reusable prompts, and [`examples/`](examples/)
for a small project you can try the skills against.

## Anatomy of a skill

```text
skills/<skill-name>/
├── SKILL.md              Entry point: name + description frontmatter, then the essentials
├── embed.go              Optional — publishes this skill as a Go package
├── references/           Loaded only when the task needs them
│   ├── <topic>.md
│   └── workflows/<task>.md
└── _agents/<agent>.md    Optional — background sub-agents
```

`SKILL.md` is read every time the skill triggers, so keep it short and put the
detail in `references/`. Prefer several small, single-purpose documents over one
long file: an agent loads only the file it needs, so a 900-line reference costs
every task while a short index plus one focused document does not.

## Contributing

Pull requests are welcome, including new skills.

- Keep each skill self-contained in one folder under `skills/`.
- Write for an agent, not a person: concrete commands, exact flags, and the
  gotchas that cause wrong answers.
- Prefer many focused documents over one large one.
- Do not commit generated or copied artifacts.
- Make it possible to review what a skill does from the layout alone.

Please open an issue first if you are planning something large, so we can agree
on the shape before you write it.
