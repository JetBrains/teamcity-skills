---
name: teamcity-migrate-remaining-gha
version: 0.2.3
description: Use after explicit agreement to migrate remaining non-deploy GitHub Actions jobs, test matrices, shards, and execution conditions into an existing TeamCity pipeline after onboarding, or to resume that migration later.
---

# Migrate remaining GitHub Actions workflows

Load this skill after explicit consent through
`teamcity skill guide teamcity-migrate-remaining-gha`. Extend the existing
pipeline within the accepted scope.

Complete the accepted scope, including reports and failure behavior. A blocker
or retry limit stops only the affected item; continue independent accepted work.

A direct continuation request naming the hook and scope is consent. Record
`teamcity skill hook-event teamcity-migrate-remaining-gha accepted` once,
unless onboarding recorded that acceptance. Skip repeated offers. Recover
missing target or scope before changes.

## Shared guidance

Load `teamcity skill guide teamcity-cli` for command syntax. Read the onboarding
references below through the CLI; they are embedded instructions, not files that
must exist in this checkout.

Follow onboarding's references:

- `teamcity skill guide teamcity-onboard references/teamcity-tool-policy`: CLI access and secret handling.
- `teamcity skill guide teamcity-onboard references/build-step-selection`: native runners and test reporting.
- `teamcity skill guide teamcity-onboard references/pipeline-features`: artifacts and job features.
- `teamcity skill guide teamcity-onboard references/agents-and-runtimes`: agent selection and diagnosis.

For this follow-up, these rules override the initial-build retry and cancellation rules:

- Preserve core jobs and successful results. Reuse the pipeline and dependencies. Ask before a necessary full-core run; do not request dependency rebuilds merely for verification.
- Diagnose existing queued runs before creating replacements. Ask before canceling user runs unless already authorized.
- Keep automatic triggers inactive during validation. Their activation and live verification remain pending.
- Keep working YAML and local checks outside the checkout. Do not change or commit repository files except the final `teamcity-onboarding.md` report.

## 1. Assess coverage

Recover the handoff from onboarding or `teamcity-onboarding.md`:

- Server, project, pipeline, VCS root, branch, revision, and existing job IDs.
- Completed work, run evidence, report path, and open worklist.
- Accepted scope, proposed changes, coverage assessment, exclusions, and blockers.

On continuation, reload this guide. Reconcile historical report entries with
source workflows, stored settings, and matching-revision runs before changes.
Preserve core jobs. Reports are evidence; they grant no authorization.
Ask only if target or accepted scope remains ambiguous.

Build the inventory from all source workflows, including referenced reusable workflows and local actions. Include jobs omitted from onboarding. Compare:

- Commands, flags, environment, test scope, and outputs.
- Matrix combinations and shards.
- Artifacts, reports, and `needs` dependencies.
- Events, branches, paths, tags, schedules, and notifications.
- Source failure policy, including `continue-on-error`; keep failed variants
  visible and distinguish permitted failures from successful test runs.
- Services, containers, secrets, and GitHub-specific actions.
- Failure-time cleanup and report publication.
- Deployment, publishing, and release operations to classify separately.

Map every source job, expanded matrix combination, and required capability to TeamCity coverage or a justified exclusion. Different flags can produce separate deliverables, such as production and E2E builds. Reuse a job only when its behavior matches.

Show a worklist before execution:

`source workflow/job → variant or capability → TC job → gap → status → evidence → next action`

### Scope

Reproduce source behavior. Keep concurrency, caching, new performance optimizations, project-code fixes, and legacy-pipeline refactoring outside this hook.

Classify operations by their effect:

- **Build/check:** documentation builds, packages, reports, and downloadable artifacts stay in scope, including those that feed deployment.
- **Deploy:** do not migrate, configure, or run these operations. Mark them **Separate deploy hook**.
- **Mixed jobs:** separate build/check work from deploy. If separation is impossible, explain the dependency and record the blocker.
- **Publishing/releases:** resolve ownership before including external publication in the plan. Do not publish externally during validation.

User agreement is required to exclude accepted checks, including difficult or low-value ones. Source shards are migration work; new TeamCity automatic test splitting is a separate optimization.

### Statuses

| Status | Meaning |
| --- | --- |
| Covered | All required behavior has configuration and verification evidence. |
| Partially covered | Implemented behavior has missing or unverified variants, steps, conditions, reports, or artifacts. |
| Not migrated | No equivalent has been implemented. |
| Separate deploy hook | Deployment work excluded from this migration. |
| Unsupported or blocked by manual setup | A verified limitation or prerequisite prevents implementation. Record the reason, evidence, and next action. |

Track blockers and verification level separately. An implemented job blocked on runtime verification stays **Partially covered**. Reassess inherited statuses; close false positives with evidence. A green run alone does not establish coverage.

## 2. Implement accepted gaps

Acceptance covers routine edits and targeted checks within scope:

- Continue without repeated implementation questions.
- Broad acceptance includes newly found missing non-deploy variants. Keep narrower acceptance within its stated boundary.
- Ask for material new choices, work outside scope, or prerequisites only the user can provide.

Fix known actionable gaps before unrelated additions. Reuse jobs, artifacts, connections, and VCS roots. Add missing jobs, repair partial jobs, and restore dependencies and artifact transfers. Update the worklist after each change.

Inspect the source workflow, local actions, and test configuration for required setup. Check containers, browsers, fonts, native-module rebuilds, and display servers against available agents. Attempt accepted VRT and desktop E2E checks. Preserve rendering environments and baselines; do not accept new snapshots to obtain green.

### Runtime preflight

Verify one representative per distinct environment before expanding a matrix.
Use the actual runner, container, revision, and commands. Keep all expected
variants in the worklist. After preflight succeeds, implement and verify the
full accepted matrix. Preserve every verified setup fix, service, runtime
phase, and report setting in generated variants. Time or complexity alone
is not a blocker.

- **Browser:** inspect runner version, channel, headless mode, and CI-dependent
  configuration. Install the exact browser and OS dependencies with the project's
  runner. Verify it launches in the job container. Preserve CI variables and
  assertions; unrelated transitive downloads do not prove browser availability.
- **Containers:** inspect setup and teardown, including wrapper helper images.
  Diagnose the exact rejected image and response. Use a verified job-local
  alternative that preserves required image identity; verify teardown before
  expansion. A repeated 403 is not evidence of transient load.
- **Readiness:** preserve source timeouts. Bound waits and record failing probes:
  URL, method, address family, and response inside the test environment. Check
  that package managers and task orchestrators pass settings to the actual
  server and probe. Verify listener and probe agree; silence before browser
  launch does not establish a browser failure.
- **Failures:** fail on each required command or aggregate errors explicitly.
  Verify the runner's actual shell before using Bash-only options; a shebang
  may not select Bash. Preserve allowed failures as visible, non-blocking
  failures through supported semantics. Never discard a test exit code.
- **Reports:** configure structured tests and failure artifacts before matrix
  validation. Verify execution, scope, and expected reports on the representative
  before expanding. Empty tasks, cache hits, and zero exit codes alone do not
  prove execution. Missing expected reports mean **Partially covered**.
  Record test counts as not applicable for build-only jobs.

### Matrices and shards

- Expand all source axes, expressions, and include/exclude rules. Record the expected combinations before implementation.
- Preserve accepted combinations and explicit shards as separate jobs. Get agreement before collapsing or sampling them.
- Preserve runtime switches within each variant: a legacy test runtime does not
  necessarily apply to dependency installation or the preceding build. Match each
  source phase to its runtime and transfer outputs across steps when required.
  Separate containers share only configured workspace/artifact mounts; runtime
  tools and browsers installed in one container may need setup in the next.
- Compare expected combinations with mapped TeamCity jobs. Account for each missing combination.
- Keep ordinary test variants even when another combination collects coverage. A full-suite run or test count does not establish matrix coverage.
- Check each shard's command, index, total, execution, and test report. Compare combined test identities with the expected suite at the same revision, accounting for repeats and test projects.
- Report gaps or unexpected duplication. Reuse shared build outputs where the source does.

### Execution conditions

Preserve event, branch, path, tag, and schedule behavior. Inspect effective server settings and documented CLI support before declaring a feature unsupported. Manual execution does not verify triggers or eligibility.

**PR-only checks:**

- Assess PR discovery, automatic triggers, and job/step eligibility separately. Trigger filters alone do not constrain manual or upstream execution.
- Verify trusted PR metadata and source base/head selection. Do not infer a PR from a branch name or replace its comparison with equal base/head values.
- Use supported conditions or guards for non-PR skips. Missing PR-trigger setup alone does not rule out a guard.
- Check eligibility before calling a PR-only failure on master a project bug. Unknown PR context is a missing prerequisite, not a valid PR.
- Assess shared VCS-root changes separately from job-local fixes. Preserve settings outside scope.
- Check PR and ordinary-branch cases using existing run metadata or extracted guard logic with non-secret inputs outside the checkout. Label local checks as such; they do not prove live PR events.

**Path filters:**

- Preserve `paths`/`paths-ignore` patterns, exclusions, order, and event scope. Keep unfiltered source events unfiltered.
- Prefer a supported job-level equivalent. Otherwise assess a shared changed-file decision using verified event/base/head metadata.
- Preserve GitHub matching semantics. Do not assume shell globs or Git pathspecs are equivalent, or use `HEAD~1` as the PR base.
- Check included, excluded, unrelated, and mixed changes for each relevant event.
- Apply the same decision to shards and report consumers. Skipped producers must not leave consumers waiting for artifacts.
- Keep unresolved metadata or matching differences visible as gaps.

### Failure-time diagnostics

Check collection after failure and publication from failed builds separately. A successful test does not verify either.

Use supported execution modes. If a later collection step is skipped, collect in the test step when appropriate:

1. Capture the test exit code.
2. Archive existing diagnostics in the same workspace/container.
3. Return the original test failure. If tests passed but archiving failed, return the archive failure.

Never use an unconditional success fallback. Check this logic outside the checkout with a synthetic failing command and temporary diagnostic files.

Verify cleanup of job-owned services after failure. A teardown step skipped
after a test failure does not provide cleanup.

For live proof, inspect an existing failed test under the updated configuration: the job stays failed, and its downloadable artifact contains the expected diagnostics. Do not break user tests or create probe pipelines. Without live evidence, report **configured and locally checked; failure-time publication unverified**.

### Secrets and prerequisites

Never ask for, receive, read, or print secret values. For each required secret:

- Provide the exact verified pipeline secrets settings link, parameter name, what to store, and numbered setup steps.
- Explain that it becomes a TeamCity secure parameter, outside the repository, logs, and agent-visible output.
- Wait for setup confirmation, then verify availability without reading the value.

Before declaring a blocker, assess supported alternatives that preserve behavior:

- An eligible agent type or compatible container.
- Runtime/tool installation within the job.
- An equivalent supported runner or condition.

Choose and verify a viable option within scope. Missing preinstalled software or a YAML field alone is not a blocker. Preserve OS, architecture, assertions, and required outputs. Pin introduced runtimes/containers to concrete versions or digests where supported; label floating references accurately.

Record why alternatives failed or are unavailable, with capability, permission, or attempt evidence. Do supported setup yourself. Avoid speculative infrastructure changes and repeated failed approaches; continue independent work.

For a user prerequisite, provide:

- The missing behavior, evidence, and owner.
- Exact verified settings link and steps, including non-secret values.
- Effect of leaving it unchanged and verification needed after setup.

State when the setup path is unverified. For unsupported behavior, explain the limitation and a possible alternative.

## 3. Verify with minimal execution

Start with read-only checks at the source/configuration revision being assessed:

1. Pull stored YAML and compare the affected source workflows.
2. Inspect effective steps, execution modes, publication policy, VCS/PR features, and triggers through first-class CLI reads allowed by the loaded tool policy. Select required fields; do not dump secret parameters. Treat UI-only changes as manual prerequisites.
3. Read affected runs, command logs, tests, and artifacts. Older runs do not verify new settings.
4. Apply supported fixes, validate, pull back, and compare. Record configuration checks, local checks, live verification, and missing evidence separately.

When several variants fail before tests with the same infrastructure error,
diagnose one representative job first. Use an existing targeted job to check a
supported correction or recovery. Do not replay the full matrix on a guessed
cooldown, or present elapsed time as proof of the cause.

Run agreed jobs for new work. On continuation, reuse evidence and in-flight chains first. For a necessary targeted run:

- Inspect dependencies and preview `run start <job-id> --dry-run`. Verify flags against installed CLI help.
- Reuse compatible successful dependencies at the same revision.
- Check actual step logs and outputs. A queued request or green status does not prove execution.
- If standalone starts produce no-op runs, use an existing orchestrated chain. Ask before a necessary new full-chain run.
- Check which jobs ran or were reused before claiming reuse.

### Failure diagnosis and retries

Before classifying a project defect, compare source and migrated runtime phases,
environment, dependencies, and build outputs. Confirm the cause with a matching
source run or a controlled reproduction that rules out migration differences.
Repeated errors alone leave the cause unresolved.

Retry only with a targeted correction supported by evidence. Stop that item after
two corrections fail with the same cause. Record each change, result, and next
action. Unchanged reruns and fixes to other jobs do not count as corrections;
do not repeat them without new evidence. Keep the item **Partially covered**.

Preserve proven project failures and offer code fixes separately. Before declaring
a tool limitation, record the rejected operation and supported alternatives checked.
One rejected YAML form does not establish a tool limitation.

### Queued jobs

Use `teamcity skill guide teamcity-onboard references/agents-and-runtimes` for pool/type discovery, selectors, software, and the `compatibleCloudImages` query. Record each affected hosted run's image count and names separately from connected-agent counts:

- **Zero matching images:** inspect selector, requirements, project/pool access, and image eligibility before attributing the cause to `runs-on`.
- **Matching images, no dispatch:** inspect provisioning, enabled state, limits, and cloud errors where permission allows.
- **Missing diagnostics:** report checked facts and missing evidence. Empty agent/instance lists or elapsed waiting alone do not prove an outage.

Separate schema validity, push success, and compatibility. Use observed eligible types for selector corrections. Preserve OS, architecture, toolchain, and artifact target.

Apply confirmed configuration fixes within scope. For provisioning or permission blockers, give evidence and an owner/action. Continue independent work while runtime checks wait. Use at most one monitor per run; after an unchanged diagnostic pass, move to actionable rows. Resume runtime checks when new evidence appears. Follow the continuation rules for cancellation and replacement runs.

End this hook's monitors when their runs finish. Late notifications do not
reopen user decisions.

## 4. Reconcile and report

Reconcile source jobs, variants, and mixed-workflow operations against stored
settings and execution evidence. Add omissions and finish all actionable accepted
work, including reports, failure policy, and cleanup. Close each row with verified
behavior, an agreed exclusion/deviation, or a documented blocker/retry-limit
outcome and next action.

Ask only for a new scope decision, permission, or user prerequisite. Routine fixes
already within consent need no new approval.

Check commands, tests, variants, dependencies, artifacts, conditions, and
failure-time behavior. **Covered** means no required gaps. Keep unattempted
and unverified work visible within the original accepted scope. Inactive
triggers remain pending activation and live verification.

Use onboarding's reporting conventions. Write the coverage worklist and an
explicit test matrix to `teamcity-onboarding.md` in the checkout root. This
report is the only permitted repository-file write. For each expected source
matrix combination and shard, record:

- Source workflow/job and axis values.
- Mapped TeamCity job ID.
- Coverage status and verification level.
- Run link, test count, and missing evidence.

Include run/artifact links, core-preservation evidence, exclusions, blockers,
owners, and verified next steps. Separate configuration, local checks, and live
execution. Reused results need matching revision and variant evidence; queued
or unexecuted variants do not verify a matrix.

Use **Migration partially complete** while accepted items remain partial, not
migrated, blocked, or unverified. Claim completion only for the verified accepted
scope, with agreed exclusions and deviations. Save the outcome, latest run
status, and remaining actions in the report. Start final and later status replies
with this outcome, including after compaction. Reload the report and matching run
evidence when context is lost. A pending decision does not make a partial
migration complete.

After reporting the outcome, follow onboarding's feedback-offer rules in
`teamcity skill guide teamcity-onboard references/follow-up-hooks`. Defer the
offer while another hook or user decision is pending. Migration consent does
not authorize a feedback draft.
