# Working in this repository

This file is for an AI agent and for a person. Read it before you change a skill.

A skill is plain Markdown in `skills/<name>/`. An agent reads these files as they are. Nothing is generated.
For how to write a skill, see [Contributing](README.md#contributing).

## Three versions, three consumers

A change does not reach a user when it is merged. Each consumer reads a different number, so update the numbers your
change affects.

| Number | Where | Update it when you |
| --- | --- | --- |
| Skill version | `version:` in `skills/<name>/SKILL.md` | change that skill |
| Claude plugin version | `metadata.version` in `.claude-plugin/marketplace.json` | change any skill, a prompt, or a plugin file |
| Git tag | a tag on `main`, for example `v0.2.0` | want a consumer to get the change |

The three numbers are independent. A skill version can follow the tool that the skill documents. For example,
`teamcity-cli` carries the version of the CLI it describes.

## The git tag is what reaches a user

A consumer pins a tag. It can bundle a copy of the skills, or get the Go package with `go get`. Either way it stays on
the tag it pins, so a merge to `main` reaches nobody. The change arrives when a new tag exists.

## Steps

In your pull request:

1. Bump `version:` of every skill you changed. Use semantic versioning. A correction is a patch. New guidance is a
   minor. A new file layout is a major.
2. Bump `metadata.version` in `.claude-plugin/marketplace.json`.

After the merge:

3. Tag `main` and push the tag.

   ```bash
   git switch main && git pull
   git tag -a v0.2.0 -m "Add the teamcity-intellij skill"
   git push origin v0.2.0
   ```

4. Tell the consumers about the new tag, so they can move to it.

Nothing here is checked by CI yet. The steps are yours to do.
