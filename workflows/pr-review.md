---
workflow:
  id: pr-review
workflow_dispatch_contract:
  orchestrator: "pr-review-operator"
  inputs:
    - "actual branch diff or PR, approved proposal package, test evidence, and audit-history context"
    - "base branch or true stacked parent for comparison"
  expectations:
    - "gates the implementation diff against the proposal through test audit, decomposition, justification, supported-surface, and commit-hygiene checks"
    - "runs on the actual diff after CodeRabbit rather than judging the proposal alone"
    - "routes repeated fix or gate loops through audit-history and process-tree review"
  outputs:
    - "gate verdicts and actionable findings for the next fix pass or decomposition"
    - "synthesized PR-review comment when posting is in scope"
    - "process-tree-auditor evidence before synthesis or downstream PR movement"
  non_goals:
    - "does not review prototype work that lacks a proposal contract"
    - "does not treat human review as a substitute for model-owned gates"
    - "does not allow findings to remain optional commentary before the PR advances"
---
# PR Review Gates

**This is the implementation-presentation workflow.** It is Phase 8 of `~/ai/workflows/implementation-pipeline.md` — the step that makes implementation work consumable for review by gating the diff against the proposal that scoped it. It runs after CodeRabbit (`~/ai/workflows/coderabbit-loop.md`). Gates the draft PR before it is opened, or before it is promoted if it was opened already.

This phase is decomposition review plus supported-surface verification, test-coverage, and commit-organization checks. Each gate presupposes a **proposal** as the contract being enforced — the gates are not directly applicable to work without a proposal (e.g. prototypes).

For prototype presentation — work that arrived at an answer without a proposal — see `~/ai/workflows/build-prototype.md` § Phase P3, which runs the **functional analogs** of these gates (proof-test audit, one-question check, answer-trace, commit-hygiene) without requiring a proposal contract. The two workflows share `commit-hygiene-operator` but are otherwise distinct: PR-review presents *implementation*, P3 presents *prototypes*.

Run on the **actual diff**, not the proposal. Proposals can look reasonable while the diff bundles too much.

When PR review enters a repeated fix/gate loop, follow `~/ai/conventions/audit-history.md` for audit-history schema, oscillation classification, and decision-agent dispatch.

Delegated user questions follow `~/ai/conventions/agent-questions-and-session-graph.md`.

Process-tree review uses `~/ai/agents/process-tree-auditor.md` and the violation taxonomy in `~/ai/conventions/workflow-execution-violations.md`.

## Gates

| Gate | Model | Purpose |
|---|---|---|
| Test audit | `gpt-high` | Check intent-first tests, risk reduction, acceptance criteria, and fixture externality. |
| Multi-concern review | `claude-opus` | Should this PR be split? Intent: does everything in this diff belong together? |
| Justification review | `claude-opus` | Does every change justify its presence? Intent: is anything here for a reason other than the stated purpose? |
| Supported-Surface Verification | `claude-opus` | Does the actual diff still reduce risk on the approved supported surface, including adjacent paths, migration/rollback, and observability? |
| Commit-hygiene check | `gpt-high` | Are commits small, testable, single-concern, and well-described? Checklist. |
| Synthesize and post | `gpt-high` | Collect all gate outputs into one PR comment that reviewers can act on. |

See `~/ai/models/roles.md` for the model-role rationale. Do not restate the matrix here.

## Operating Rules

- Run on the actual diff. Default comparison is `git diff main..HEAD`; if the branch is stacked, compare against its true parent.
- A PR that touches N independent concerns should be split into N PRs.
- A large deletion is its own PR, separate from the addition that replaces it.
- Additive changes go before behavioral changes.
- If the diff cannot be decomposed further without creating more churn than clarity, the PR is ready to advance.
- Gate findings are review inputs, not optional commentary. Fixes happen before the PR moves forward.

## Multi-concern Review

Asks: can this PR be decomposed into N smaller PRs that each carry a single concern?

Output exactly one verdict:

- `SINGLE_CONCERN` — the PR is cohesive and ready to advance.
- `MULTI_CONCERN_RECOMMEND_SPLIT` — the diff should be decomposed. Identify each concern, the files or lines involved, and the dependency order.
- `MULTI_CONCERN_ACCEPTABLE` — the diff spans multiple concerns, but decomposition would create more churn than value because the edits are tightly interleaved.

Review rules:

- A PR that touches N independent concerns should be split into N PRs.
- File overlap alone does not make a PR single-concern.
- Shared refactors only belong with behavior changes when the refactor is strictly required for that behavior.
- A large deletion stands alone, even when the replacement lands immediately after it.
- Additive groundwork lands before behavioral swaps.
- "Cannot decompose further" means the PR is ready to advance.

## Justification Review

Asks: does every change in the diff serve its stated purpose?

Review rules:

- Every meaningful decision should trace to AC, a decision record, a prior slice, or an explicit revision rationale.
- Flag drift, drive-by cleanup, speculative abstractions, and unrelated fixes.
- Flag behavior changes that are not required for the stated purpose.
- Flag cleanup that should ship separately even if it is "good cleanup."
- Minor polish items can be folded into the next CodeRabbit fix pass when they do not change the PR's concern.

Typical verdict: `LOW_CONCERN` with specific findings, or a stronger escalation if the diff is materially off-purpose.

## Supported-Surface Verification

Asks: does this diff still reduce risk on the current supported surface it claims to target?

Review rules:

- Read the approved proposal package before judging the diff: `research/NN-problem-map.md`, the approved `proposals/NN-*.md`, and `risk/NN-supported-surface.md`.
- Check the exact supported deployment or customer path, not a hypothetical one.
- Check which adjacent public or user-reachable paths remain unchanged after the patch.
- Check what migration path, rollback path, and observability obligations the diff adds or changes.
- Flag symbolic hardening: a diff that matches a finding label but leaves the supported surface materially unchanged.
- Check any `risk/NN-test-residuals.md` artifact. If an unverified residual means the diff no longer clearly reduces risk on the approved supported surface, apply the existing supported-surface termination order: invalidated assumption -> return to research and resume at Phase 2.5; otherwise non-positive value -> stop the PR and close it.
- Consume any `Supported-Surface Verification finding` sent by Test Audit for firstness or residual evidence that collapses the approved net-value case.
- Keep the supported-surface termination signal separate from the LOW/MEDIUM/HIGH verdict in the review output.
- Rule: supported-surface termination is an orthogonal dimension from the LOW/MEDIUM/HIGH verdict. Evaluate it first and in this order: invalidated assumption that breaks the current problem framing -> return to research and resume at Phase 2.5; otherwise non-positive value on the current supported surface -> stop the PR and close it rather than parking it for later. A `LOW` supported-surface verdict with a non-positive value signal still means stop the PR and close it rather than parking it for later. Only when no termination signal fires does the LOW/MEDIUM/HIGH verdict control the next step.
- When no termination signal fires, record ordinary fix-pass findings from that verdict.

## Test Audit

Asks: do the tests encode intended behavior first, reduce named risks, and cover the stated acceptance criteria?

Audit rules:

- Read the approved proposal package before judging the tests: `research/NN-problem-map.md`, the approved `proposals/NN-*.md`, `risk/NN-supported-surface.md`, and `risk/NN-test-residuals.md` if it exists.
- When a test report bundle exists or is required, read `reports/report-index.md` first and record the canonical PDF path, canonical S3 URL when present, Actions-artifact fallback URL otherwise, screenshot paths, and non-UI evidence paths.
- Apply `~/ai/conventions/test-reports.md`: PDFs are canonical, PR comments are pointers, UI-touching tests need screenshots, non-UI tests need artifact evidence, and every code claim needs `file_path:line_number` plus an exact fenced code block.
- Read the contract next: schemas, endpoint signatures, CLI definitions, public interfaces, explicit acceptance criteria, fixture application points, and test-intent handoff.
- Check each acceptance criterion and each proposal test-intent item against a test, a deliberate residual entry, or a documented non-applicability reason.
- Check Phase 6 firstness evidence before accepting tests as intent-first: the Phase 6 process-tree report, expected-process manifest, Step 6b prompt/log, Step 6c prompt/log, Step 6b output index, Step 6b output paths, and Step 6c consumption evidence.
- Missing or contradicted required firstness evidence is `blocking`; surface `NEEDS_INPUT:<question_artifact>` only when the missing artifact can still be supplied before downstream consumption.
- A commit marker, commit order, or risk annotation may support review, but none replaces the Phase 6 process-tree review plus companion artifacts.
- Apply firstness per named risk, selected level, and test group, not at whole-suite or whole-PR level.
- Route firstness gaps per risk, selected level, and test group. Complete cells continue to ordinary Test Audit checks. Missing, contradicted, stale, or post-code cells are `blocking`; repairable semantic test defects are `ordinary fix-pass findings`; invalidated framing routes to `return to research`; value collapse routes through a `Supported-Surface Verification finding`.
- Do not treat process-provenance uncertainty as a new residual class. If the uncertainty is truly unverifiable and does not collapse the approved net-value case, it can only be recorded through Decision Recording as `accepted with a named unverifiable residual risk`.
- Do not require retroactive firstness for pre-existing code without prior tests. Require mapping to existing-state risk or supported-surface context, and require current-work firstness for current-work behavior changes.
- For test-infrastructure-only changes, apply fixture externality, assertion-weakening, captured-behavior, baseline-update, and documented-reason checks. If the same diff changes product behavior, firstness applies to the behavior tests for that product change.

Firstness routing cases:

| R2 case | Test Audit routing |
|---|---|
| Entirely absent tests | `blocking`; if the gap exposes wrong framing, `return to research`; if value collapses, `terminate the work` or `stop the PR and close it`. |
| Existing coverage sufficient, documented | No firstness-gap route; any unrelated test issue is `ordinary fix-pass findings`. |
| Existing coverage claimed but unmapped | `blocking`; repairable mapping issues become `ordinary fix-pass findings` only after required evidence exists. |
| Structurally absent firstness, same commit | `blocking`. |
| Temporally absent firstness, after implementation before PR | `blocking`. |
| Artifact-present but process-after | `blocking`. |
| Process-present but artifact-absent | `blocking` only if a required companion artifact is absent; otherwise no firstness-gap route. |
| Both process and artifact absent | `blocking`. |
| Partial by evidence form: marker only | `blocking`; a marker is not the companion artifact. |
| Partial by evidence form: artifact only | `blocking`; artifact-only evidence does not replace process-tree verification. |
| Partial by scope/risk area | Compose per named risk; missing cells are `blocking`, value-collapse cells are `terminate the work` or `stop the PR and close it`, and non-collapsing unverifiable cells may be `accepted with a named unverifiable residual risk`. |
| Partial by level | Compose per selected level; same routing as partial scope/risk area. |
| Partial by test group | `blocking` until the group is split or mapped; remaining semantic defects are `ordinary fix-pass findings`. |
| Stale pre-existing tests edited during implementation | `blocking`; if the edit reflects changed intent or an invalidated assumption, `return to research`; if value collapses, `terminate the work` or `stop the PR and close it`. |
| Stale fixture or baseline update | `blocking`; if fixture truth changed, `return to research`. |
| Valid test correction/invalidation | `return to research` when framing or assumptions changed; otherwise `ordinary fix-pass findings` after the contract and affected tests are corrected. |
| Contract revised because implementation failed | `blocking`; if the failure exposes invalidated framing, `return to research`. |
| Same-agent authorship | `blocking`. |
| Test writer saw implementation | `blocking`. |
| Bug reproduction after defect, before fix | No firstness-gap route; any unrelated test issue is `ordinary fix-pass findings`. |
| Bug reproduction after fix | `blocking`; if verified value cannot be recovered, `terminate the work` or `stop the PR and close it`. |
| Refactor with no behavior change | No firstness-gap route when existing tests are mapped; missing mapping is `blocking`. |
| Refactor coverage ritual | `ordinary fix-pass findings` when tests lack a named risk; if the broader change has `non-positive value`, `terminate the work` or `stop the PR and close it`. |
| Fixture-first loophole | `blocking`; fixture order does not prove behavior-test firstness. |
| Fixture-in-test-body loophole | `blocking` under fixture externality; if fixture truth is unclear, `return to research`. |
| Residual-risk artifact absent when required | `blocking`; first check invalidated assumption -> `return to research`; otherwise if the unverified risk collapses value, `terminate the work` or `stop the PR and close it`. |
| Residual-risk artifact present but stale | `blocking`; if invalidating inputs changed framing, `return to research`. |
| Level selected after tests | `blocking`; if level selection is unclear, `return to research`. |
| Non-applicability asserted after code | `blocking`; if applicability changed, `return to research`. |

- Check that every test or test group names the risk it reduces, names the proposal or assumption-register source, and uses one explicit level: `unit`, `component`, `particular-integration`, or `end-to-end`.
- Check that the selected level is the cheapest reliable validator for the named risk.
- Check that fixtures are externally applied. Flag durable or shared fixture state, dependency substitutions, seed data, shared mocks, baselines, service setup, or environment setup edited into the test body or declared as same-file fixtures unless project convention names that file pattern as the dedicated fixture file pattern.
- Flag hidden coupling between fixtures and implementation details.
- Block any test change that relaxes an assertion, regenerates a baseline, deletes coverage, narrows input space, removes a risk annotation, or turns a red test green without a corresponding product-code fix.
- Allow test renames, typo fixes, and risk-annotation strengthening only when they are net non-assertion-weakening edits.
- A test edit is not accepted as a review-time justification. It is accepted only as the consequence of changed intended behavior, corrected fixture truth, an explicit invalidation condition, or a documented test bug in the upstream verification artifact. Implementation failure is not a valid reason to edit the test.
- Treat this as the PR-review counterpart to `~/ai/agents/test-writer.md`'s rule that tests are not changed to match current behavior.
- Flag over-assertion, weak tests, and same-agent authorship: tests must validate the contract, fail when implementation is wrong, and be written by a separate test writer from the implementation writer.
- If `risk/NN-test-residuals.md` lists an unverified risk that collapses the approved net-value case, record a Supported-Surface Verification finding for the Synthesize And Post gate instead of treating the missing coverage as an ordinary fix-pass item.

## Commit Hygiene

Asks: are commits small, single-concern, testable on their own, and well-described?

Check for:

- Each commit builds and passes tests on its own.
- Each commit carries one concern.
- Each commit message explains why that specific change exists.
- Fixup noise is removed before review.
- The visible history supports incremental review instead of one opaque dump.

Reference `~/ai/conventions/git.md` for the commit contract.

## Synthesize And Post

One `gpt-high` agent collects the gate outputs and posts one synthesized PR comment.

Synthesis rules:

- Process-tree review: before synthesis consumes or posts gate outputs, run `process-tree-auditor` on the PR-review gate fanout. The expected process includes test audit, multi-concern review, justification review, supported-surface verification, commit hygiene, and each gate output consumed by synthesis. A blocking process violation prevents synthesis/posting.
- Include the canonical test-report S3 PDF URL when Test Audit produced or consumed one. Fall back to the uploaded Actions-artifact URL only when the S3 URL is absent. The PR comment remains a pointer; do not paste the full report.
- Include each gate verdict.
- Include the specific findings needed for the next fix pass.
- Group findings by file or concern, not by gate.
- Tag each finding with severity so the fix pass has an execution order.
- Preserve decomposition recommendations exactly when multi-concern review calls for a split.
- Put any supported-surface mismatch, research re-entry trigger, or non-positive-value termination ahead of ordinary fix-pass findings.
- Surface and apply any `NEEDS_INPUT:<question_artifact>` returned for user-owned evidence, missing gate inputs, unclear test intent, justification ambiguity, or pre-posting loop decisions before posting. A synthesized PR comment cannot consume unanswered or unapplied question-dependent gate output.

## Fix Pass

When fix passes repeat, maintain audit history under `~/ai/conventions/audit-history.md`. A recurring same-family finding, a prior finding that weakens or regresses, or a two-generation oscillation is not ordinary fix-pass work; classify it before continuing.

If hard triggers do not decide the next action and the choice is `apply` versus another narrow fix pass, dispatch per-role decision agents under `~/ai/conventions/audit-history.md` before acting. Record the reconciled determination in the audit history.

When a fix pass reruns gates, run `process-tree-auditor` on the rerun subtree before the next synthesis or loop decision. If the loop is using audit history, the process-tree audit report is a role output for `decision-encoder`.

If a delegated gate or operator returns `NEEDS_INPUT:<question_artifact>`, the root handles it through `~/ai/conventions/agent-questions-and-session-graph.md`. Gate-affecting answers are recorded in audit history as deciding inputs before the loop continues, applies fixes, decomposes, posts, or opens a PR.

If any gate surfaces findings that require code changes:

1. A `gpt-high` agent applies the fixes, combined with any remaining useful CodeRabbit findings.
2. Amend the commit.
3. Re-run CodeRabbit using `~/ai/workflows/coderabbit-loop.md`.
4. Re-run only the gates that flagged findings, unless the fix touched another gate's area.

## Decomposition

If multi-concern review recommends a split:

- Decompose into N PRs using the file or line allocation from the review.
- Merge sequentially.
- Rebase each later PR onto `main` after the earlier PR lands, or onto the current parent while the stack is still in flight.
- Follow the stack conventions in `~/ai/conventions/git.md`.

## Gate Ownership Recap

- These gates are model-owned.
- A human does not re-run or re-validate what the gates already validated.
- Human ownership starts at promotion: deciding whether a draft PR becomes ready for review.
