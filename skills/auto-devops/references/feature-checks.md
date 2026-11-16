# Existing TeamCity optimizations

Assess these feature families before ranking proposals. Prefer a suitable existing TeamCity
feature over custom machinery when evidence supports it. A feature being enabled does not
prove it works well. Being disabled does not prove that enabling it will help.

## Read settings, then check behavior

For each selected job, attempt the relevant current settings reads below, alongside its
steps, history and statistics. These are CLI GETs; use the existing read-only environment,
local capture, secret omission and compact projections from [collection.md](collection.md).
Substitute literal job IDs safely. Runtime support still needs checking.

```sh
teamcity job settings list JOB_ID --json
teamcity api '/app/rest/buildTypes/id:JOB_ID/snapshot-dependencies?fields=count,snapshot-dependency(id,inherited,source-buildType(id),properties(property(name,value)))'
teamcity api '/app/rest/buildTypes/id:JOB_ID/triggers?fields=count,trigger(id,type,disabled,inherited,properties(property(name,value)))'
teamcity api '/app/rest/buildTypes/id:JOB_ID/vcs-root-entries?fields=count,vcs-root-entry(id,inherited,checkout-rules,vcs-root(id))'
teamcity api '/app/rest/buildTypes/id:JOB_ID/features?fields=count,feature(id,type,disabled,inherited,properties(property(name,value)))'
teamcity api '/app/rest/buildTypes/id:JOB_ID/agent-requirements?fields=count,agent-requirement(id,type,inherited,properties(property(name,value)))'
```

Preserve effective values and inherited/disabled flags. Check template or project settings
when they affect the result. Unresolved parameter references, incomplete inheritance and
missing properties remain unknown; do not assume defaults. Check each source's association
with historical runs. Trees show relationships, not dependency options or why reuse failed.

Use these families as an assessment checklist, not a requirement to recommend every feature:

| `feature` | Configuration and behavior to compare |
| --- | --- |
| `build-reuse` | Snapshot reuse, successful-only reuse, revision synchronization and same-agent constraints; artifact dependencies where relevant. Compare actual reused run IDs and repeated work across compatible revisions, settings and parameters. Investigate suitability before calling a rebuild unnecessary. |
| `triggers-and-queue` | Enabled triggers, branch/path filters, quiet periods, trigger placement and queue optimization settings. Compare recorded causes, revisions and queue reasons before claiming duplicate builds. Preserve required scheduled and release runs. |
| `checkout` | Checkout rules, checkout mode, clean-checkout policy and supported sparse-checkout settings. Compare checkout stages, changed paths and required build inputs. Exclusions can become stale; narrow rules only with evidence that required sources and tests remain covered. |
| `conditional-execution` | Supported job/step conditions and branch policies. Compare executed/skipped work with required outcomes. Do not remove required PR, test, security or deployment work merely because it is slow. |
| `caching` | TeamCity Build Cache and relevant runner/tool caches, their keys, paths and restore/publish behavior. Compare hits, misses, invalidation and transfer time with avoided work. An enabled cache or repeated package download alone does not establish a useful cache change. |
| `parallel-execution` | Unnecessary dependency ordering, supported parallel-test settings and runner concurrency. Compare the governing path, actual overlap, test distribution and available agents. Splitting work can add setup time, agent execution and cost. Verify runner/server support rather than assuming language support. |
| `agent-capacity` | Agent requirements, pools, concurrency constraints, relevant shared resources, and matching cloud profiles. Compare compatible capacity, startup/idle waits and observed utilization. Assess supported warm-up, agent lifetime and termination settings when relevant. |

Discover supported CLI reads for the matching VCS roots, pools, agents and cloud profiles
only when the initial evidence calls for them. Use PerfMon or equivalent resource evidence
when available for CPU/memory sizing; wall time alone does not show a hardware bottleneck.
Do not treat every queue reason as a capacity shortage or recommend raising limits from it.
Earlier startup or longer agent life may add paid idle time. Compare checkout/cache locality
with the scheduling cost of keeping work on the same agent.

Stay within the selected chain and existing job/run/log limits. Cross-project contention,
evicted-build history, missing profile/resource data or inaccessible settings may prevent
verification; record the next useful read instead of silently expanding collection.
Reuse collected settings and representative behavior only when their equivalence is supported.

## Report what was established

New reports include `featureAssessment` as described in [report.md](report.md). Cover every
family above for the selected scope. Split rows when jobs have different settings, behavior
or applicability; do not hide exceptions in a chain-wide verdict.

- `assessed`: settings and relevant behavior support the stated, limited finding. Describe
  whether existing settings appear useful or an evidence-backed change is worth testing;
  this state does not certify optimality or require numerical savings.
- `not-applicable`: explain why the feature is unsuitable for these jobs, citing evidence.
  For example, deployment side effects may require a new run even when compilation is reusable.
- `unverified`: say what settings or behavior are missing and give a concrete next check.
  Reading settings without enough behavior evidence leaves effectiveness unverified.

Denied/unsupported reads are gaps, not evidence that a feature is disabled or unsuitable.
Unverified relevant features make coverage partial (or blocked if no useful analysis remains).
They need not prevent another supported recommendation. Do not conclude `none` when a
material unexamined feature could change that conclusion. Cite separate setting and behavior
evidence from each assessment and from any resulting recommendation.

Preserve correctness, security updates, revision consistency and deployment semantics.
Recommendations remain proposals for separate review; the skill applies no changes.
Base images or third-party AMI builders require evidence of suitability and availability.
Billing arrangements, self-hosted agents or extra licenses are separate tradeoffs, requiring
actual prices, constraints and demand evidence. They are not default recommendations.
Future/dynamic/AI-driven conditions, matrix builds and test prioritization in product notes
are ideas to investigate, not assumed server capabilities or additions to this delivery.
