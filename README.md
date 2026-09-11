# TeamCitySkills

This repository stores reusable skills, prompts, and supporting assets for TeamCity-related work and for other engineering workflows when they are useful to keep together.

The repository is not limited to one stack, tool, or runtime. A skill can target any technology or workflow as long as it is useful and reviewable by humans.

## Organization

Group reusable workflows under `skills/`, one folder per skill. Keep reusable
prompts under `prompts/`.

Example:

```text
.
├── README.md
├── docs/
│   └── evaluation-cases-proposal.md
├── evals/
│   ├── schema.json
│   ├── validate.py
│   ├── first-green-build/
│   └── teamcity-access-preflight/
├── examples/
│   └── <example-project>/
├── prompts/
│   └── <prompt-name>.md
└── skills/
    └── <skill-name>/
        └── SKILL.md
```

This keeps each workflow self-contained and easy to reuse across different tools.

## What Can Live Here

- reusable skills
- reusable prompts or runbooks
- supporting reference material bundled with a skill
- small helper assets that belong to a skill

The repository can contain TeamCity setup skills, debugging skills, CI/CD runbooks, repository onboarding flows, or other operational skills that help agents work more reliably.

## Suggested Conventions

- Keep each skill self-contained.
- Prefer one folder per skill.
- Keep generated or copied artifacts out unless they are intentional parts of the skill.
- Make it easy to review what a skill does from the repository layout alone.

## Current Contents

- `skills/teamcity-first-green-build/`
  - Skill for creating, reusing, or repairing TeamCity CI and driving it to the first successful verification build or a proven external blocker.
- `prompts/build-on-teamcity.md`
  - Prompt for building the current project on a TeamCity server with the first green build workflow.
- `examples/Test_TC_2/`
  - Example Gradle/Kotlin project with TeamCity pipeline configuration.
- `evals/`
  - Versioned JSON evaluation contracts for TeamCity skills. See
    [`docs/evaluation-cases-proposal.md`](docs/evaluation-cases-proposal.md).
    Validate them with `uv run evals/validate.py` (or `pipx run
    evals/validate.py`); the `validate` job in `.teamcity.yml` runs the same
    check in CI.
