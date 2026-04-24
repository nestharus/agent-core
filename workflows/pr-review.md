# PR Review Gates

Step 8 of the implementation pipeline. Runs after CodeRabbit (`~/ai/workflows/coderabbit-loop.md`). Gates the draft PR before it is opened, or before it is promoted if it was opened already.

This phase is decomposition review plus supported-surface verification, test-coverage, and commit-organization checks.

Run on the **actual diff**, not the proposal. Proposals can look reasonable while the diff bundles too much.

## Gates

| Gate | Model | Purpose |
|---|---|---|
| Test audit | `gpt-high` | Do the tests actually cover the stated acceptance criteria? Checklist/presence check. |
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
- Keep the supported-surface termination signal separate from the LOW/MEDIUM/HIGH verdict in the review output.
- Rule: supported-surface termination is an orthogonal dimension from the LOW/MEDIUM/HIGH verdict. Evaluate it first and in this order: invalidated assumption that breaks the current problem framing -> return to research and resume at Phase 2.5; otherwise non-positive value on the current supported surface -> stop the PR and close it rather than parking it for later. A `LOW` supported-surface verdict with a non-positive value signal still means stop the PR and close it rather than parking it for later. Only when no termination signal fires does the LOW/MEDIUM/HIGH verdict control the next step.
- When no termination signal fires, record ordinary fix-pass findings from that verdict.

## Test Audit

Asks: do the tests cover what the acceptance criteria said they should cover?

Audit rules:

- Read the contract first: schemas, endpoint signatures, CLI definitions, public interfaces, and explicit acceptance criteria.
- Check each acceptance criterion against at least one test.
- Flag missing coverage.
- Flag over-assertion: tests that mirror the implementation rather than validate the contract.
- Flag weak tests that can pass while the implementation is wrong.
- Flag hidden coupling between fixtures and implementation details.
- If the same agent wrote both the implementation and the tests, flag it. Tests written by the implementer often mirror the code instead of the contract.

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

- Include each gate verdict.
- Include the specific findings needed for the next fix pass.
- Group findings by file or concern, not by gate.
- Tag each finding with severity so the fix pass has an execution order.
- Preserve decomposition recommendations exactly when multi-concern review calls for a split.
- Put any supported-surface mismatch, research re-entry trigger, or non-positive-value termination ahead of ordinary fix-pass findings.

## Fix Pass

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
