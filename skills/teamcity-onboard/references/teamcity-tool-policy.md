# Tool policy and secrets

Rules for every TeamCity operation. Command syntax comes from the
`teamcity-cli` skill.

## Tools

- First-class `teamcity` commands for projects, VCS roots, pipelines, jobs,
  runs, queue, and agents. `teamcity api` is the last resort, when no
  first-class command covers the operation. Its reads select named fields
  with `?fields=`, never a `properties` collection. Its writes never replace
  `pipeline validate` and `pipeline push`. `curl`, `wget`, and other HTTP
  clients are forbidden.
- The flow is CLI-only. The web step authenticates the CLI and nothing else.
  MCP tools are not set up. When neither a first-class command nor
  `teamcity api` covers an operation, write a
  [manual prerequisite](manual-prerequisites.md).
- Validate changed YAML with `teamcity pipeline validate` before you push or
  queue. `validate` is weaker than the server's parser: it rejects hosted
  `runs-on` names the server accepts and misses what the server rejects. A
  push error is the real validation.
- Write YAML the server accepts: no anchors, no `=>` in `files-publication`,
  `#!/bin/bash` at the top of every bash script. `execution-timeout-minutes`
  and `enable-dependency-cache` are behind server toggles and may do nothing.

## Secrets

- Never print tokens, secrets, passwords, private keys, or authorization
  headers.
- Never ask the user for a secret value. Never accept one in chat. When a job
  needs a secret, give the link to the pipeline's secrets settings page, name
  the parameter, and say what to store there. A basic build usually needs
  none.
- Do not dump a full object or its `properties` collection. It can hold
  inherited parameters, and a server may return a value that should be
  masked.
- When a response contains a secret, do not repeat it anywhere. Tell the user
  it was exposed: revoke or rotate it at the issuer, replace it in TeamCity
  secure storage, retry with the replacement.
- When a permission is missing, name the blocked operation and the permission
  that appears required, and give the user the next safe action. Do not work
  around it with another CI system.
