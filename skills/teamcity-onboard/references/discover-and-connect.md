# Discover and connect

Confirm the server, inspect it, and run the pipeline on the VCS root and the
branch from your task. Commands: the `teamcity-cli` skill's
`connections-and-vcs.md` and `pipelines.md` workflows.

## Confirm the server and the project

Confirm the login once with a bare `teamcity auth status`: the default server
is the target. The parent project is
the project ID from your task. Read its pipelines with
`pipeline list --project <project-id>`, and the schema with
`pipeline schema --refresh`. Agents: see
[Agents and runtimes](agents-and-runtimes.md).

## Use the VCS root

Your task says `VCS root: exists` or `VCS root: none`.

- `exists`: the flow created the root. Take it from
  `project vcs list --project <project-id>`: the one whose URL matches the
  repository. Do not create another one. `project vcs view <id>` shows its
  default branch as a full ref, such as `refs/heads/main`, and no branch
  specification. Run on it as below.
- `none`: do not create a root. Create the pipeline and run it as
  [No VCS root](#no-vcs-root) shows.

## Run on the root

- The checkout is on the default branch, its commit is pushed, and
  `git status` is clean: run on the root with
  `--revision <root-id>=<sha>@<default-ref> --branch '<default>'`. The
  `<default-ref>` is the root's full default ref, such as `refs/heads/main`;
  never put `<default>` after `@`. A guessed `--branch main` can leave the
  jobs green and the head red with `invalid_branch_name`. Without `--branch`
  the checkout fails with `couldn't find remote ref <unspecified>`.
- Another branch, unpushed commits, or uncommitted changes: use a
  [remote run](#remote-run). Never `git checkout` another branch.

After queueing, read back the run's branch and revision before you wait on
it: `teamcity api '/app/rest/builds/id:<id>?fields=branchName,personal,revisions(revision(version,vcsBranchName))'`.
`run view --json` has none of these. `version` is the pinned SHA,
`vcsBranchName` the full ref, and `personal: true` a remote run. No
`branchName` means the default branch. Branch errors:
[Verify a build](verify-build.md#decide-what-a-failure-means).

## No VCS root

For `VCS root: none`. Create the pipeline without `--vcs-root`. Every run is
a [remote run](#remote-run).

## Remote run

A personal build with the checkout sent as a patch. Write the patch outside
the checkout. **Always** pass `--personal --no-push`: without `--no-push` the
CLI pushes the branch. When the checkout has uncommitted changes, tell the
user in one line that the run includes them: a red run may come from
unfinished work.

With a root, base the patch on the default branch:

```bash
base=$(git merge-base HEAD origin/<default-branch>)
git diff --binary "$base" > <tmp>/branch.patch
teamcity run start <pipeline-id> --revision <root-id>="$base"@<default-ref> \
  --branch '<default>' --local-changes=<tmp>/branch.patch --personal --no-push
```

Without a root, send the whole repository:

```bash
git diff --binary $(git hash-object -t tree /dev/null) > <tmp>/full.patch
teamcity run start <pipeline-id> --local-changes=<tmp>/full.patch --personal --no-push
```

- Keep the `=` in `--local-changes=<file>`.
- The patch holds the tracked files as they are on disk. Untracked files are
  left out.
- TeamCity drops file modes from the patch: a script the patch adds fails
  with `Permission denied`. List the executable files with
  `git ls-files -s | awk '$1 == "100755" {print $4}'` and start each job
  with a script step that runs `chmod +x` on them.
- A missing custom-patch permission is a
  [manual prerequisite](manual-prerequisites.md).
