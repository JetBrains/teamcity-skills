# Migrate remaining GitHub Actions workflows

Onboarding loads this hook after the user accepts migration of the remaining pipeline. Do not repeat the offer. Extend the existing TeamCity pipeline within the accepted scope.

## Shared guidance and continuation rules

Use onboarding's [Tool policy and secrets](teamcity-tool-policy.md), [Build-step selection](build-step-selection.md), and [Pipeline features](pipeline-features.md). Read [Agents and runtimes](agents-and-runtimes.md) when selecting or diagnosing agents. These references own CLI policy, native runners, runtime selection, test reporting, and artifact configuration; this hook adds migration and continuation rules.

For this follow-up, the rules below take precedence over onboarding's initial-build retry and cancellation instructions:

- Preserve existing core jobs and successful results. Do not recreate the pipeline, request dependency rebuilds, or start a full core chain merely for verification. Ask before a necessary full-chain run.
- Ask before canceling existing user runs unless already authorized. Diagnose queued runs before creating replacements.
- Keep automatic triggers inactive during validation. Their activation and live verification remain pending.
- Keep working YAML and local verification files outside the checkout. Do not modify or commit repository files.

## 1. Recover scope and assess coverage

Receive the project, pipeline, VCS root, branch, revision, existing job IDs, accepted scope, coverage assessment, proposed changes, and exclusions from onboarding. Obtain missing context before making changes.

On continuation, read the current hook from disk and recover every unresolved item from previous reports. Reconcile each with the current source workflows and server configuration. Show a worklist before execution:

`source workflow/job → variant or capability → existing TC job → gap → status → evidence → next action`

Compare behavior, not names or job counts. Inspect commands, relevant flags/environment, test scope, matrix, outputs, dependencies, execution conditions, and failure-time behavior. Different build flags can produce distinct deliverables: a production build and an E2E-specific build need separate coverage even when they share a job name. Reuse an existing job only when the required behavior matches.

Build the inventory from the source, not from the TeamCity jobs already created or the first-run subset. Read referenced reusable workflows and local actions where they define executable behavior. Assign every source job, expanded matrix combination, and required capability a coverage row or a reasoned scope exclusion. A workflow omitted by onboarding is still a migration candidate.

Inspect all source workflows for:

- build, packaging, lint, formatting, static analysis, and tests;
- runtime/OS/architecture/flag matrices and explicit shards;
- artifacts, reports, and `needs` dependencies;
- events, branches, paths, tags, schedules, and notifications;
- services, containers, reusable workflows, secrets, and GitHub-specific actions;
- deployment, publishing, and release operations to classify separately.

### Scope boundaries

Reproduce source behavior. Concurrency, caching, new performance optimizations, project-code fixes, and legacy-pipeline refactoring are outside this hook.

Classify individual operations by what they do, not by workflow names. Compiling documentation, building packages, generating reports, and storing downloadable artifacts are build/check work even when their workflow later deploys or publishes them. Keep those operations in scope and separate their downstream deployment or external publication. Exclude a whole mixed workflow only when separation is demonstrably impossible; explain the dependency that prevents it.

Do not migrate, configure, or run deployment operations. Mark them **Separate deploy hook**. For mixed jobs, separate the checks from deployment; if they cannot be separated, record the blocker. Resolve ownership of publishing/release operations before including them in the executable plan. Do not publish externally during validation.

Do not drop an accepted check because it seems low-value or difficult. Exclusion requires user agreement. Reproducing source shards is migration; introducing TeamCity automatic test splitting is a separate optimization.

### Coverage statuses

| Status | Meaning |
| --- | --- |
| Covered | All required applicable behavior has supporting configuration and verification evidence. |
| Partially covered | Implemented behavior has missing or unverified variants, steps, conditions, reports, or artifacts. |
| Not migrated | No equivalent has been implemented. |
| Separate deploy hook | Deployment operations excluded from this migration. |
| Unsupported or blocked by manual setup | A verified limitation or prerequisite prevents implementation. Record which, its evidence, and the next action. |

Track blockers and verification level separately from coverage. An implemented job remains **Partially covered** when runtime verification is blocked. A green run or unchanged configuration does not prove complete coverage. Close false positives with evidence rather than copying inherited statuses.

## 2. Implement accepted gaps

Acceptance covers routine configuration edits and targeted verification for that scope. Continue without repeated implementation questions. Broad acceptance of the remaining non-deploy pipeline includes newly discovered missing variants; a narrower acceptance keeps its boundary. Ask for material new choices, changes outside scope, or prerequisites only the user can provide.

Work through known actionable gaps before unrelated additions. Reuse jobs, artifacts, connections, and VCS roots. Add missing jobs/variants, repair partial jobs, and restore their dependencies and artifact transfers. Explain discoveries and update the worklist after each change. Apply supported services, containers, reusable workflows, conditions, and notifications; record unsupported behavior explicitly.

Use the source workflow, local actions, and test configuration to reproduce required setup. Complexity alone is not a blocker for VRT or desktop E2E. Preserve pinned rendering environments and baselines; do not accept new snapshots to obtain green. Check native-module rebuilds, browsers, fonts, containers, and display-server requirements against available agents.

### Matrices and shards

Preserve accepted source combinations, include/exclude rules, and explicit shards as separate jobs. Do not collapse, sample, or replace them without agreement. Running the whole suite in one job proves neither OS/runtime variants nor shard coverage.

Expand the source matrix using its actual axes, expressions, and include/exclude rules. Record the expected combinations before implementing them, then compare that set with mapped TeamCity combinations. Account for each missing combination individually. Coverage collection on one combination does not replace the ordinary test variants, and a passing test count does not justify dropping a build configuration or runtime axis.

Check each shard's command, index, total, execution, and test report. Compare combined test identities with the expected suite at the same revision, accounting for repeats and test projects. Counts alone do not prove completeness. Reuse shared build outputs where the source does.

### Execution conditions

Compare event, branch, path, tag, and schedule semantics independently from commands. A manual success does not verify triggering or eligibility. A missing YAML field does not prove that no supported equivalent exists: inspect effective server settings and documented capabilities through the CLI.

**PR-only checks.** Separate PR discovery, automatic triggers, and job/step eligibility. A trigger filter alone does not constrain manual or upstream execution. Verify trustworthy PR metadata and source base/head selection; do not infer PR status from a branch name or substitute equal base/head values.

Use a supported condition or guard to reproduce non-PR skips. Missing PR-trigger wiring does not itself rule out a guard. A PR-only command failing on master can be a migration eligibility defect rather than a project failure. If PR context is unknown, do not treat it as a valid PR; report the missing prerequisite. Evaluate shared VCS-root changes separately from job-local fixes and preserve settings outside the accepted scope.

Check positive PR and negative ordinary-branch cases using existing run metadata or extracted guard logic with representative non-secret inputs outside the checkout. Local logic checks do not prove live PR-event behavior.

**Path filters.** Preserve exact `paths`/`paths-ignore` semantics, exclusions, rule order, and event scope. A PR filter must not inadvertently filter source events that have no path restriction. Prefer a supported job-level equivalent; otherwise assess a shared changed-file decision using verified event/base/head metadata. Do not substitute `HEAD~1` for the PR comparison base or assume shell globs/Git pathspecs match GitHub patterns.

Check included, excluded, unrelated, mixed changes, and relevant events. All shards and report consumers must use the same decision; skipped producers must not strand consumers waiting for artifacts. If metadata or matching semantics cannot be reproduced, retain the exact gap.

### Failure-time diagnostics

Assess cleanup and `always()`/`failure()` report and artifact collection separately from successful execution. Check both whether collection runs after test failure and whether TeamCity publishes failed-build artifacts.

Use supported execution modes. If a later collection step is skipped, collect in the test step when appropriate: capture the test exit code, archive existing diagnostics in the same workspace/container, and exit with the original test failure. If tests passed but archiving failed, preserve that failure. Never use an unconditional success fallback.

Check control flow outside the checkout using a synthetic failing command and temporary diagnostic files. For live proof, inspect an existing failed test run under the updated configuration: the job must remain failed and the downloadable artifact must contain the expected diagnostics. Do not deliberately break user tests or create a probe pipeline. Without such a run, report **configured and locally checked; failure-time publication unverified**.

### Secrets and manual prerequisites

Never ask for, receive, read, or print secret values. Follow the shared secret policy. For each required secret, provide the exact verified pipeline secrets settings link, parameter name, what to store, and numbered setup steps immediately. Explain that TeamCity stores it as a secure parameter, outside the repository, logs, and agent-visible output. Wait for confirmation and verify availability without reading the value.

### Resolve prerequisites before declaring blockers

Before declaring a prerequisite blocked or unsupported, assess supported alternatives that preserve the source behavior: an eligible agent type, a compatible container, installation of the required runtime/tools within the job, or an equivalent supported runner/condition. Choose and verify a viable alternative within scope. A missing preinstalled SDK, unavailable dedicated runner, or missing YAML field alone is not a blocker. Do not silently substitute another OS/architecture, weaken assertions, or remove required output. Pin any introduced runtime/container to a concrete version or digest where supported; record floating references as such rather than calling them pinned.

For alternatives ruled out, record the relevant capability, permission, or failed-attempt evidence. Exhaust reasonable supported options; do not make speculative infrastructure changes or repeat the same failed approach. Continue independent work when no viable option is available.

Do supported configuration work yourself. Manual action requires a verified permission, UI-only setting, secret, or other user prerequisite. Provide the evidence, owner, exact verified settings link/steps, effect of leaving it unchanged, and verification needed afterward. If the setup path is unverified, say so; do not invent URLs. For unsupported behavior, explain the limitation and possible alternative.

## 3. Verify with minimal execution

Start with read-only evidence at the source/configuration revision being assessed:

1. Pull stored YAML and compare the affected source workflows.
2. Inspect effective steps, execution modes, publication policy, VCS/PR features, and triggers. Read only necessary fields; do not dump secret parameters. Use supported CLI/REST reads under the shared tool policy; UI-only work becomes a manual prerequisite.
3. Read affected runs, command logs, test reports, and artifact listings. Older runs do not verify new settings.
4. Apply supported fixes, validate, pull back, and compare. Record configuration checks, local logic checks, live verification, and missing evidence separately.

For new migration work, run the agreed jobs. For continuation, reuse existing evidence and in-flight chains first. If a targeted run is necessary, inspect dependencies and preview `run start <job-id> --dry-run` using flags verified against installed CLI help. Reuse compatible successful dependencies at the same revision.

A queued request or green status is not proof that commands executed. Check real step logs and outputs. If standalone job starts produce no-op runs on this server, stop using that path. Reuse an existing orchestrated chain; ask before a necessary new full-chain run. Do not claim reuse without checking which jobs actually ran or were reused.

Fix migration-caused failures. After two attempts fail with the same cause despite a targeted correction, stop that item with evidence and a next action. Do not repeat unchanged runs. Report verified project failures without hiding them or changing project code; offer code fixes through the separate follow-up.

### Queued jobs

Follow [Agents and runtimes](agents-and-runtimes.md) for pool/type discovery, selectors, installed software, and the `compatibleCloudImages` query. For each affected hosted run, record the count and names separately from connected-agent counts:

- **Zero compatible cloud images:** no eligible cloud match. Inspect selector, requirements, project/pool access, and image eligibility before attributing the cause specifically to `runs-on`.
- **Matching images but no dispatch:** inspect provisioning, enabled state, limits, and cloud errors where permission allows. Matching images do not prove provisionability.
- **Unavailable diagnostics:** record what was checked and what remains unknown. Zero connected agents or instances alone does not establish a capacity outage.

Schema validation, successful push, and actual compatibility are separate evidence. Use server-observed eligible types when correcting obsolete selectors. Preserve OS, architecture, toolchain, and artifact target.

Apply confirmed migration corrections within scope. For a verified provisioning/permission blocker, give evidence and an owner/action rather than repeatedly editing YAML. Do not infer a specific quota or outage from elapsed waiting alone.

A queue block affects only work needing those agents. Continue independent checks and fixes. Keep at most one monitor for the same run. After an unchanged diagnostic pass, record the runtime block and move to other actionable rows; resume when new evidence appears. Follow the continuation rules above for cancellation and replacement runs.

## 4. Reconcile and report

Before declaring completion, reread the source inventory and compare it with the stored TeamCity configuration and verification evidence. Compute the unmatched source items, including matrix combinations and operations inside mixed workflows. Add any omissions back to the worklist and continue actionable migration. Do not shrink accepted scope to the implemented subset, reinterpret an unresolved item as an optional follow-up, or equate all created jobs being green with full migration.

Account for every initial worklist row, including inherited gaps. Do not finish with a list containing only queued jobs. For each accepted item, finish with verified behavior, an agreed exclusion/deviation, a documented blocker with next action, or the retry-limit outcome. Unattempted or unverified work remains visible.

Check commands/test scope, variants, dependencies/artifacts, execution conditions, and failure-time behavior where applicable. Do not label a row **Covered** while describing a required gap elsewhere. Configuration validity is not a substitute for runtime proof. Triggers kept inactive remain pending activation and verification.

Use onboarding's run-link and user-facing report conventions. Include:

- what was added or corrected, with run and artifact links;
- evidence that existing core behavior was preserved;
- every worklist row's coverage status and verification level;
- remaining gaps, exclusions, blockers, owners, and verified next steps.

Report **Migration partially complete** while accepted items remain partial, not migrated, blocked, or unverified. Claim completion only for the verified accepted scope, with agreed exclusions and deviations stated explicitly.
