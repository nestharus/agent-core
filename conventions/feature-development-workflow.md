# Feature-development workflow

Canonical convention for shipping a feature that decomposes into 2+ tickets, has a user-facing surface, or ships behavioral change. Sits *above* manager flavors (max/pragmatic/hackerman), not as a replacement.

## When to use

Use feature-development by default when the work decomposes into 2+ tickets, has a user-facing surface, or ships behavioral change. Use the direct-to-trunk exception only for bounded single-ticket markdown, convention, or auditor refinement work with no user-facing prototype.

| Strategy | When | Flavor relationship | Evidence pack |
|---|---|---|---|
| max | Critical infrastructure, regression-prone work, or work where a defect cascades across other WUs. | `manager-max` remains the safest flavor inside each ticket and at final review; feature-development still controls branch and evidence topology when the work qualifies as a feature. | Full PR-body evidence for each ticket PR and the final feature PR. |
| pragmatic | Bounded single-ticket work with low blast radius and no user-facing surface. | `manager-pragmatic` may stay direct-to-trunk only while the work remains bounded to one ticket and has no feature-level integration need. | Minimal correct PR-body evidence for the bounded change. |
| feature-development | 2+ tickets, user-facing surface, or shipped behavioral change. | Strategy layer above the active manager flavor; the flavor decides risk posture, while this strategy decides branch topology, evidence expectations, prototype payload, and QA record. | Universal PR-body evidence on every ticket PR plus the final feature-to-trunk PR. |
| hackerman | Throwaway, internal-only, speed-biased work where the user explicitly accepts narrow proof and residual risk. | `manager-hackerman` does not waive feature-development when the result is a shipped multi-ticket feature. | Immediate functional proof for internal throwaway work; universal PR-body evidence for shipped feature work. |

## Refactoring out of scope

In this section, feature work owns new-code decomposition: a feature ticket may decompose, reorganize, or refactor its own new code when necessary to deliver accepted behavior.

An existing-code structural refactor discovered while reading context or satisfying auditors is not automatic feature scope unless the active manager flavor explicitly keeps a tiny directly-unblocking change in scope.

Broader existing-code refactor discovered by a feature WU becomes residual, follow-up, or pause/file/refactor under ACR-180 and ACR-179.

## The 12-step pipeline

1. Roadmap: start from a feature brief, market/product roadmap, or strategy record; output the feature problem, candidate shapes, acceptance criteria, and open questions; gate on whether the feature is clear enough to prototype, scope, or terminate.
2. Prototype: when feasibility, shape, or behavior is uncertain, build a small prototype to answer the open questions; output a prototype dossier with findings; gate on whether the result says pursue, change scope, or stop.
3. Scope: use roadmap and prototype evidence to choose the actual feature slice; output a scoped feature definition with explicit anti-scope; gate on whether the slice is coherent and reviewable.
4. Ticket decomposition: split the scoped feature into ticket-sized Work Units, one bounded surface or contract per ticket; assign each ticket exactly one supported owning route (`implementation-pipeline` or `refactoring`) and one existing backend issue key that is also immutable graph `ticket_id`; output the scoped ticket list, route, and dependencies; gate on whether every route has a complete contract. Brief-only ticket sources are standalone child cold-start inputs, not feature route records.
5. Feature branch: create or verify the feature branch from the repo integration trunk; output the feature branch and feature worktree; gate on branch baseline correctness and worktree isolation.
6. Route execution and PR target: treat a topological wave only as the set of currently eligible tickets. The feature owner dispatches one merge-owning route attempt at a time and waits for an accepted verified merge before selecting the next eligible route. Every `(ticket_id, attempt_number)` has immutable unique prompt, log, result, route evidence, route-discriminated pre-audit/final expected/dispatch/trace artifacts, independent auditor log/output/report/binding, common validation, route outcome, and one closed `feature-route-attempt-proof-v1`. The proof, common validation, outcome, attempt index, and route result all bind the exact normalized `feature_branch`; implementation base branch/fetched ref/reviewed-current provider names and refactoring integration/dispatched/observed/nested base names/ref must equal it even when another ref resolves to the same OID. A refactoring result also requires exact child/nested implementation PR/head/guard/base equality and one current closed auditor index bound to route UUID/feature/ticket/attempt; its exact five pre-merge and five post-merge rows equal the route arrays, every report is re-hashed and parsed as exact LOW, and report heads equal the reviewed child or final/refreshed integration SHA. The feature owner performs that semantic validation but never reruns child auditors. Route source selection is a production CLI xor between strict inline JSON and the successor path before parsing; both feed one closed ticket-source/backend/branch/protected-ref/canonical-path/payload/dependency/cycle/wave/output validator and emit the same `feature-route-manifest-v2` record graph. Every record contains exactly the existing `jira_issue_key` or `linear_issue_key` selected by `ticket_system`, its value equals `ticket_id`, and `wu_brief_path` fails before normalized output, directory creation, dispatch, or ticket side effects. The exact AGE-255 successor kind is Linear-bound; every present source backend indicator and recognized ticket URL host must agree with `ticket_system` before normalization output or route side effects. A refactoring route transports its normalized branch and unique route roots into exactly one implementation child and returns one route-level result.
7. Validate and merge by owner: each route attempt's implementation, test, review, and auditor evidence names one exact reviewed base/head identity. A direct implementation child returns `VERIFIED_DRAFT_PR` with exact `is_draft=true` and `phase_8_reviewed_is_draft=true`. The feature owner freezes route evidence without future hashes, independently audits that exact evidence, validates draft pre-ready currentness, and freezes a separate acceptance envelope that hashes those antecedents. It then promotes the exact repository/PR, immediately fetches both exact base/head refs, resolves both remote SHAs, re-queries OPEN non-draft provider identity, and requires provider/fetched/reviewed equality for both OIDs through production currentness before artifact-lineage merge authorization and the expected-head guarded merge. Every refusal after ready and before merge runs exact-repository ready undo plus fresh base/head fetch and provider re-query; only production validation of OPEN draft identity unchanged across undo permits `REPLAY_REQUIRED`. Restoration failure is `BLOCKED:ready-state-restoration-failed`. Merge invocation is irreversible for replay: no undo follows it and any merge/post-attempt refusal is `BLOCKED:merge-attempt-started`. Each ticket ends with exactly one selected `PASS` / `VERIFIED_MERGED` attempt; accepted direct rows bind the acceptance-envelope hash. Refactoring remains the sole owner of its child PR merge.
8. Dependency release: keep route work based on the feature branch and release a dependent only after `validate-route-attempts` re-hashes the prerequisite's proof envelope, re-runs the common route-process validator over every referenced artifact and child-owned companion, and confirms route-specific verified merge identity plus ancestry against the refreshed feature branch. A literal `PASS`, path-only placeholder, stale common result, or refactoring row without common proof is not completion. The append-only route-attempt index retains stale, replay-required, and accepted attempts without mutating their envelopes; the cumulative process manifest unions all attempt nodes and identifies one accepted attempt per ticket. The three real AGE-255 wave-zero refactoring routes integrate serially against successively refreshed feature bases before AGE-259 is released.
9. Final feature PR: after every scoped ticket has a verified merged route-level result, open the feature-branch-to-trunk PR; output the final PR; gate on all routes being represented and the final diff matching feature scope.
10. Final evidence pack: produce executable QA or an unavailable placeholder first, freshly pin trunk/feature/diff second, then freeze route/process/acceptance/QA evidence and a separate non-self-referential integrated-review input manifest. Bind reviewer, verdict, final evidence, handoff, and outcome to that exact input hash; output the reviewer-facing evidence pack sized to the PR type.
11. Prototype payload upload: when the feature has a runnable prototype, place the payload under `prototype/<feature-slug>/` and link it from the final PR; output the payload directory; gate on bring-up and smoke-test instructions being present.
12. QA evaluation: run the Playwright-driven QA agent against the prototype when operational and attach the verdict to the final PR; output the QA verdict, or a recorded placeholder gap when the agent is not yet operational; gate on the gap being explicit rather than hidden.

## Universal evidence-pack rule

Evidence packs live on PR bodies, not on branches. Size the PR-body evidence to the PR type:

- UI / user-facing: screenshots plus a text tour of the action and result.
- Service / API: API call examples such as curl or httpie, response snapshots, and relevant logs.
- Workflow / convention / Markdown: diff narrative, DECISIONS entry, and allowed command output; do not add markdown shape tests for this evidence.
- Test-only: test output plus failure-then-pass demonstration.

## Heterogeneous Route Cardinality

| Owning route | Ticket-level PR cardinality | Merge owner | Feature-level consumption |
|---|---:|---|---|
| `implementation-pipeline` | Exactly one direct ticket PR returned as `VERIFIED_DRAFT_PR`. | `feature-orchestrator` after caller-context-bound ticket validation, child-proof hash checks, directional evidence/process/acceptance construction, exact draft promotion, fresh OPEN/non-draft currentness, artifact-lineage authorization, and expected-head guard; every pre-merge refusal restores exact OPEN draft state before replay. | One verified merged direct-route row with acceptance-envelope hash. |
| `refactoring` | Exactly one implementation child and one ticket PR per refactoring WU. | `refactoring-orchestrator` only, with the same caller-context ticket validation, exact nested PR/head/guard/base identity, closed ten-report auditor-index validation, child-proof hash checks, restore-before-replay, and no-undo-after-merge-attempt boundary. | One complete singular-child `VERIFIED_MERGED` route result with current implementation/refactoring-owned proof hashes and exact current LOW auditor evidence; the feature owner re-hashes and semantically validates but never reruns auditors or re-merges the PR. |

Direct-route authorization consumes one exact closed `feature-route-evidence-v1` whose ticket-operation reference must equal the implementation result path/hash. It first requires the result's immutable `ticket-operation-expected-context-v1` path/hash to equal feature caller backend/site/ticket/route/attempt/PR/reviewed identity, then validates the producer-owned `ticket-operation-result-v1` against that required context, including URL-encoded backend site/ticket identity, exact readback, runtime producer identity, and current distinct producer operation-log/readback-output hashes. Unknown, omitted, malformed, stale, failed, or hash-consistent semantic falsehoods block ready and merge. Process authorization is split by node kind: test-audit keeps exact recursive leaf-only fanout membership, while feature-route validation checks only exact direct feature-root children, first one captured route-orchestrator and then that unchanged route plus one captured independent auditor. Arbitrary descendants beneath the route node are allowed because implementation/refactoring own and independently prove them; undeclared direct siblings, duplicates, reparented nested nodes, and wrong/failed/non-terminal direct nodes block. The route result's current implementation/refactoring-owned process-proof path/hashes are mandatory auditor companions but are not re-audited at feature level. Acceptance later binds the auditor's complete runner log, provider-only extracted output, byte-identical canonical report, and final topology, so no report contains circular or future hashes.

## Branch baseline

Feature branches start from the caller's explicit repository integration trunk. Both explicit branch inputs must be short GitHub branch names that pass `git check-ref-format --branch` without normalization; full refs, remote-tracking forms, whitespace-bearing names, invalid syntax, aliases, and trunk/feature equality are rejected before route derivation or output. Every absolute route input is exact canonical identity: reject `.` / `..`, symlinks, lexical-versus-`resolve(strict=False)` differences, wrong parent/basename relationships, or cross-root aliases. Derived worktree and artifact paths are pairwise unique direct canonical children of their declared roots. Project wrappers may declare a repository-specific value such as `master`; the base feature operator has no `main`, `master`, or ambient branch default. Every direct and nested implementation child receives the explicit feature branch as its PR base. The final feature PR alone targets the explicit trunk branch.

## Prototype payload

Runnable prototype payloads live under `prototype/<feature-slug>/` and include `docker-compose.yml` plus `README.md`. The README names prerequisites, environment variables, bring-up commands, a smoke-test command, and expected output screenshots when screenshots are applicable. Link the prototype directory from the final PR body.

## QA evaluation

The required end-to-end check is a Playwright-driven QA agent run against the prototype. If that agent is not yet operational, record the gap explicitly in the final PR body's evidence pack and continue under the active manager flavor's review policy. This WU only records the requirement; operational wiring belongs to a downstream ticket.

## Risk note (AI-execution inverts the divergence calculus)

Traditional feature branches can accumulate costly divergence. AI-driven tickets land quickly enough that the feature branch should stay close to trunk, while the integration benefit of ticket PRs targeting a shared feature branch outweighs the divergence cost and avoids cascading rebases across in-flight ticket work.

## Direct-to-trunk exception

Bypass the feature branch only for bounded single-ticket work with no feature-level integration need, such as:

- single-file convention or Markdown patches;
- single-ticket workflow document edits;
- single-ticket auditor refinements;
- small internal-only cleanup that does not ship a user-facing prototype or behavioral feature.

If the work grows into 2+ tickets, gains a user-facing surface, or ships behavioral change, return to feature-development.

## Cross-references

- `~/ai/conventions/worktree-isolation.md`
- `~/ai/conventions/workflow-aliases.md`
- `~/ai/agents/work-manager-operator-max.md`
- `~/ai/agents/work-manager-operator-pragmatic.md`
- `~/ai/agents/work-manager-operator-hackerman.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/workflows/build-prototype.md`
- `~/ai/workflows/feature-development.md`
- `~/ai/agents/feature-orchestrator.md`
- ACR-156
- ACR-157
- ACR-173
- ACR-175
