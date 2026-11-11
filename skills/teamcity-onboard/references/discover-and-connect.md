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
  `<default-ref>` is the root's full default ref, such as `refs/heads/main`.
  `'<default>'` is not a placeholder: pass it as is, with the angle brackets
  and the quotes. It is TeamCity's name for the default branch. Never
  replace it with `main` or another branch name, and never put `<default>`
  after `@`. A guessed `--branch main` can leave the
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
  --branch '<default>' --local-changes=<tmp>/branch.patch --personal --no-push \
  --comment '<why this run>'
```

Here too, `'<default>'` is passed as is, not replaced with a branch name.

Without a root, send the whole repository:

```bash
git diff --binary $(git hash-object -t tree /dev/null) > <tmp>/full.patch
teamcity run start <pipeline-id> --local-changes=<tmp>/full.patch --personal --no-push \
  --comment '<why this run>'
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

### A patch over 64 MB

TeamCity does not take a patch over 64 MB for remote run. Check the size of the patch file
before `run start`. If it is bigger, stop and ask the user, in plain words.
Say that the limit is only technical, and give two choices, for example:

> Your repository is bigger than 64 MB, and TeamCity can't take that much
> in one upload. That's only a technical limit of uploading files from your
> computer. I can:
> 1. Run the build without some big files that the build doesn't use, such
>    as images or docs. Then those files are not in the build, and may be
>    missing from the packages.
> 2. Connect the repository to TeamCity. Then TeamCity gets all files
>    itself, with no limit.
> Which one do you prefer?

Wait for the answer.

- **Run without some files**: find the biggest tracked files with
  `git ls-files -z | xargs -0 du -k | sort -n | tail -20`. Leave out only
  files the build does not read, with `':(exclude)<path>'` after `--` in
  `git diff`, until the patch is under 64 MB. Tell the user which files are
  left out, and put the list in the report file.
- **Connect the repository**: it needs a remote on a Git host. Without one,
  the user pushes the repository first. Find the connection with
  `teamcity project connection list` (connections are in the root project), and let the user sign in with
  `teamcity project connection authorize <conn-id> -p <conn-project-id>`.
  Connections always exist. Then create the root with
  `teamcity project vcs create --url <https-url> -p <project-id> --auth token --connection-id <conn-id> --json`,
  create the pipeline again with `--vcs-root <root-id>`, and run on the
  root as [Run on the root](#run-on-the-root) says.
