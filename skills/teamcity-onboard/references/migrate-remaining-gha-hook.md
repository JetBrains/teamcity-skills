# Migrate remaining GitHub Actions workflows

Onboarding loads this hook after the user accepts migration. Extend the existing pipeline within the accepted scope. Do not repeat the offer.

## Shared guidance

Follow onboarding's references:

- [Tool policy and secrets](teamcity-tool-policy.md): CLI access and secret handling.
- [Build-step selection](build-step-selection.md): native runners and test reporting.
- [Pipeline features](pipeline-features.md): artifacts and job features.
- [Agents and runtimes](agents-and-runtimes.md): agent selection and diagnosis.

For this follow-up, these rules override the initial-build retry and cancellation rules:

- Preserve core jobs and successful results. Reuse the pipeline and dependencies. Ask before a necessary full-core run; do not request dependency rebuilds merely for verification.
- Diagnose existing queued runs before creating replacements. Ask before canceling user runs unless already authorized.
- Keep automatic triggers inactive during validation. Their activation and live verification remain pending.
- Keep working YAML and local checks outside the checkout. Do not change or commit repository files.

## 1. Assess coverage

Receive this context from onboarding:

- Project, pipeline, VCS root, branch, revision, and existing job IDs.
- Accepted scope, coverage assessment, proposed changes, and exclusions.

Obtain missing context before making changes. On continuation, read the current hook from disk and recover all open items from earlier reports. Check them against the source workflows and current server settings.

Build the inventory from all source workflows, including referenced reusable workflows and local actions. Include jobs omitted from onboarding. Compare:

- Commands, flags, environment, test scope, and outputs.
- Matrix combinations and shards.
- Artifacts, reports, and `needs` dependencies.
- Events, branches, paths, tags, schedules, and notifications.
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

### Matrices and shards

- Expand all source axes, expressions, and include/exclude rules. Record the expected combinations before implementation.
- Preserve accepted combinations and explicit shards as separate jobs. Get agreement before collapsing or sampling them.
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
2. Inspect effective steps, execution modes, publication policy, VCS/PR features, and triggers through supported CLI/REST reads. Select required fields; do not dump secret parameters. Treat UI-only changes as manual prerequisites.
3. Read affected runs, command logs, tests, and artifacts. Older runs do not verify new settings.
4. Apply supported fixes, validate, pull back, and compare. Record configuration checks, local checks, live verification, and missing evidence separately.

Run agreed jobs for new work. On continuation, reuse evidence and in-flight chains first. For a necessary targeted run:

- Inspect dependencies and preview `run start <job-id> --dry-run`. Verify flags against installed CLI help.
- Reuse compatible successful dependencies at the same revision.
- Check actual step logs and outputs. A queued request or green status does not prove execution.
- If standalone starts produce no-op runs, use an existing orchestrated chain. Ask before a necessary new full-chain run.
- Check which jobs ran or were reused before claiming reuse.

Fix migration failures. Stop an item after two attempts fail with the same cause despite a targeted correction; report evidence and the next action. Report verified project failures without hiding them or changing project code. Offer code fixes through the separate follow-up.

### Queued jobs

Use [Agents and runtimes](agents-and-runtimes.md) for pool/type discovery, selectors, software, and the `compatibleCloudImages` query. Record each affected hosted run's image count and names separately from connected-agent counts:

- **Zero matching images:** inspect selector, requirements, project/pool access, and image eligibility before attributing the cause to `runs-on`.
- **Matching images, no dispatch:** inspect provisioning, enabled state, limits, and cloud errors where permission allows.
- **Missing diagnostics:** report checked facts and missing evidence. Empty agent/instance lists or elapsed waiting alone do not prove an outage.

Separate schema validity, push success, and compatibility. Use observed eligible types for selector corrections. Preserve OS, architecture, toolchain, and artifact target.

Apply confirmed configuration fixes within scope. For provisioning or permission blockers, give evidence and an owner/action. Continue independent work while runtime checks wait. Use at most one monitor per run; after an unchanged diagnostic pass, move to actionable rows. Resume runtime checks when new evidence appears. Follow the continuation rules for cancellation and replacement runs.

## 4. Reconcile and report

Before declaring completion:

- Compare the source inventory with stored TeamCity settings and verification evidence.
- Find unmatched jobs, matrix combinations, and operations in mixed workflows. Add omissions to the worklist and continue actionable work.
- Account for every original row, including inherited gaps. Finish each with verified behavior, an agreed exclusion/deviation, a documented blocker and next action, or the retry-limit outcome.
- Keep unattempted and unverified work visible. Do not shrink accepted scope to the implemented subset or turn open gaps into optional follow-ups.
- Check commands/tests, variants, dependencies/artifacts, conditions, and failure-time behavior. **Covered** rows must have no required gaps. Configuration validity is not runtime proof.
- Keep trigger activation and live verification pending while triggers are inactive.

Use onboarding's reporting conventions. Include:

- Added or corrected behavior, with run and artifact links.
- Evidence that core behavior was preserved.
- Every row's coverage status and verification level.
- Gaps, exclusions, blockers, owners, and verified next steps.

Report **Migration partially complete** while accepted items remain partial, not migrated, blocked, or unverified. Claim completion only for the verified accepted scope, with agreed exclusions and deviations stated.
