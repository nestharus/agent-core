---
eval_id: orchestrator-fanout-completion
behavior_class: ACR-203 implementation-pipeline fanout-completion contract
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - markdown-section-header
  - markdown-fenced-pseudocode
  - markdown-substring
  - filesystem-sentinel-presence
suggested_action_class: revise-orchestrator-docs-or-add-sentinel
---

# Orchestrator Fanout Completion

## Eval identity

This is a markdown behavior specification for `orchestrator-fanout-completion`, not runnable eval code. It names the WRITE-state Step 6b contract for future detectors that verify the ACR-203 implementation-pipeline fanout-completion documentation surfaces.

The eval guards the implementation-pipeline fanout joins and their mirrors. It expects Step 6c to revise the source docs. During ACR-203 development, the Step 6b artifact lives at `/home/nes/projects/ai/worktrees/acr-203-watcher-fragility/evals/orchestrator-fanout-completion/eval.md`. After merge to `master`, the file lands at `/home/nes/ai/evals/orchestrator-fanout-completion/eval.md` (its canonical post-merge home). Both paths are documented to make the alignment gate's path check unambiguous.

## Unwanted behavior

The unwanted behavior is a documented or reintroduced fanout join that can hang or falsely advance because it relies on brittle log scraping, idle-timeout-only waiting, unbounded orphan polling, or partial verdict acceptance.

The ACR-186 failure modes are in scope: a line-start `^WROTE:` matcher failed to observe wrapped child output, an `until ... sleep ... done` watcher leaked orphan polling after host timeout, and the main workflow could continue from direct report reads while the watcher residue kept the session alive. The eval also fires on residual-advance behavior where a bounded-failure path accepts partial fanout verdicts instead of blocking.

## Assumptions

- A1: This eval spec is in `WRITE` lifecycle state. It is a markdown behavior specification and does not require runnable detector code in this WU.
- A2: Future runnable detectors, fixtures, adapters, and CLI wiring are out of scope for ACR-203 Step 6b.
- A3: If a runnable detector lands later, assertion failures emit `FAIL <AC_ID>: <evidence>` and successes emit `PASS <test-id>: all ACs satisfied`.
- A4: Source line ranges cited here are anchors for Step 6c and future detectors. A future detector may report updated line ranges after Step 6c edits, but it must preserve the path, section header, AC ID, and evidence token.
- A5: Sentinel files are completion evidence only. Canonical report paths, stat fields, hashes, verdict lines, producing invocation UUIDs, and process-tree audit evidence remain the verdict evidence boundary.

## Taxonomy decomposition note

The Step 6a contract decomposed the approved proposal test-intent track's broader F1-F6 / N1-N4 acceptance criteria into this eval's more granular AC groups, and the orchestrator explicitly accepts the decomposed taxonomy as covering every proposal AC. This mapping is the orchestrator's accepted decomposition; future Phase 6 alignment dispatches reading the proposal first should use this mapping table to cross-check.

| Proposal AC | Eval coverage |
| --- | --- |
| Proposal F1 (operator fanout-completion at touched joins) | Eval M1-M5 (orchestrator mirror group) |
| Proposal F2 (no `^WROTE:` watcher pattern anywhere) | Eval M2 (no `^WROTE:` substring in Phase 4 / Phase 8 sections) |
| Proposal F3 (`agents-cli.md` carve-out for sentinel + bounded timeout + cleanup trap) | Eval F1-F6 (carve-out group) |
| Proposal F4 (canonical dispatch shape preserved) | Eval F7 |
| Proposal F5 (`implementation-pipeline.md` mirror sections) | Eval W1-W3 |
| Proposal F6 (sibling-workflow inheritance) | Eval S1, S2, S3 |
| Proposal N1 (bounded failure on missing/malformed/stale sentinel) | Eval N3 + V1 |
| Proposal N2 (cleanup-trap absence) | Eval N2 |
| Proposal N3 (alternate completion evidence cannot substitute for sentinel) | Eval N1 + N3 |
| Proposal N4 (stale sentinel reuse) | Eval N4 |

## Positive evidence

### agents_cli_carve_out

Target path: `/home/nes/ai/workflows/agents-cli.md`.

Source anchor before Step 6c: `## Long-running agents`, lines 97-117. The existing canonical dispatch pseudocode is at lines 101-109, and the existing forbidden-pattern list is at lines 110-117.

AC coverage: F1-F7.

- F1: The `## Long-running agents` section contains a sub-header naming the gated-fanout sentinel carve-out. The required structural anchor is `/home/nes/ai/workflows/agents-cli.md` `## Long-running agents` plus a descendant header whose text matches both `sentinel` and `gated fanout`.
  - Failure shape: `FAIL F1: /home/nes/ai/workflows/agents-cli.md ## Long-running agents missing sentinel gated fanout sub-header`
- F2: That sub-section contains the literal token `touch <log>.done` or an equivalent sentinel-write instruction that names terminal sentinel creation after the canonical report write.
  - Failure shape: `FAIL F2: /home/nes/ai/workflows/agents-cli.md sentinel carve-out missing touch <log>.done terminal-write token`
- F3: That sub-section contains the literal token `$SECONDS` or an equivalent Bash-builtin elapsed-time guard.
  - Failure shape: `FAIL F3: /home/nes/ai/workflows/agents-cli.md sentinel carve-out missing $SECONDS hard-timeout token`
- F4: That sub-section contains `trap` and `before the first`, proving cleanup ordering before the first background dispatch.
  - Failure shape: `FAIL F4: /home/nes/ai/workflows/agents-cli.md sentinel carve-out missing pre-dispatch cleanup-trap ordering`
- F5: That sub-section contains `defense-in-depth` or `backstop`, proving sentinels do not replace Bash tool task notifications.
  - Failure shape: `FAIL F5: /home/nes/ai/workflows/agents-cli.md sentinel carve-out does not preserve task notification as primary`
- F6: That sub-section contains `BLOCKED:fanout-completion-timeout` or an explicit bounded-failure-class identifier.
  - Failure shape: `FAIL F6: /home/nes/ai/workflows/agents-cli.md sentinel carve-out missing bounded-failure class`
- F7: The `## Long-running agents` section body preserves the canonical dispatch shape by containing the literal token `agents -m <model> -p <worktree-path> -f <prompt-file>`, the literal token `2>&1 | tee`, and a carve-out sentence containing `canonical dispatch shape`, `shape above remains unchanged`, or `canonical shape`.
  - Failure shape: `FAIL F7: /home/nes/ai/workflows/agents-cli.md ## Long-running agents missing agents -m <model> -p <worktree-path> -f <prompt-file>, 2>&1 | tee, or canonical dispatch shape preservation token`

Success shape: `PASS agents_cli_carve_out: all ACs satisfied`.

### orchestrator_fanout_join_citations

Target path: `/home/nes/ai/agents/implementation-pipeline-orchestrator.md`.

Source anchors before Step 6c: `### AGENT DISPATCH SHAPE` lines 101-109; `#### Phase 2.5 entry-mode audit dispatch` lines 178-185; `### Phase 4 — Risk Gates (parallel) + Process-tree Audit #1` lines 287-303; `#### Phase 4 code-quality gate` lines 305-313; `#### Per-component code-quality auditor fanout` lines 420-427; `### Phase 8 — Post-CodeRabbit Gates + Process-tree Audit #3` lines 509-519. PR-review gate identity is anchored at `/home/nes/ai/workflows/pr-review.md` `## Gates`, lines 67-76.

- M1: The `### AGENT DISPATCH SHAPE` section cites `agents-cli.md` section `Long-running agents` and references the ACR-203 carve-out with `sentinel`, `sentinel-marker`, or `fanout completion`.
  - Failure shape: `FAIL M1: /home/nes/ai/agents/implementation-pipeline-orchestrator.md AGENT DISPATCH SHAPE missing agents-cli fanout-completion citation`
- M2: The Phase 4 risk-gates section no longer contains the literal `^WROTE:` substring and no longer contains `Wait for all four.` as a standalone sentence.
  - Failure shape: `FAIL M2: /home/nes/ai/agents/implementation-pipeline-orchestrator.md Phase 4 retains forbidden ^WROTE: or Wait for all four. token`
- M3: The `#### Phase 4 code-quality gate` section cites the same completion contract with substring `agents-cli.md`.
  - Failure shape: `FAIL M3: /home/nes/ai/agents/implementation-pipeline-orchestrator.md Phase 4 code-quality gate missing agents-cli.md completion citation`
- M4: The `#### Per-component code-quality auditor fanout` section cites the same completion contract with substring `agents-cli.md`.
  - Failure shape: `FAIL M4: /home/nes/ai/agents/implementation-pipeline-orchestrator.md per-component code-quality fanout missing agents-cli.md completion citation`
- M5: The Phase 8 PR-review section enumerates the five PR-review gates `test-audit`, `multi-concern`, `justification`, `supported-surface verification`, and `commit-hygiene`, and cites `agents-cli.md`.
  - Failure shape: `FAIL M5: /home/nes/ai/agents/implementation-pipeline-orchestrator.md Phase 8 missing five-gate PR-review set or agents-cli.md completion citation`

Success shape: `PASS orchestrator_fanout_join_citations: all ACs satisfied`.

### workflow_mirror

Target path: `/home/nes/ai/workflows/implementation-pipeline.md`.

Source anchors before Step 6c: `### review_first` lines 131-139; `## Phase 4 - Risk Gates (required; parallel)` lines 336-355; Phase 6 per-component code-quality rules lines 462-463; `## Phase 8 - Post-CodeRabbit Review Gates` lines 494-502. PR-review gate identity is anchored at `/home/nes/ai/workflows/pr-review.md` `## Gates`, lines 67-76.

- W1: The `## Phase 4 - Risk Gates (required; parallel)` section cites `agents-cli.md`.
  - Failure shape: `FAIL W1: /home/nes/ai/workflows/implementation-pipeline.md Phase 4 missing agents-cli.md fanout-completion mirror`
- W2: The `## Phase 8 - Post-CodeRabbit Review Gates` section lists all five PR-review gates, including supported-surface verification.
  - Failure shape: `FAIL W2: /home/nes/ai/workflows/implementation-pipeline.md Phase 8 missing supported-surface verification in PR-review gate list`
- W3: The Phase 6 per-component code-quality rule region cites `agents-cli.md`.
  - Failure shape: `FAIL W3: /home/nes/ai/workflows/implementation-pipeline.md Phase 6 per-component code-quality missing agents-cli.md fanout-completion mirror`

Success shape: `PASS workflow_mirror: all ACs satisfied`.

### sibling_workflow_citations

Target paths: `/home/nes/ai/workflows/audit.md`, `/home/nes/ai/workflows/code-quality.md`, and `/home/nes/ai/workflows/pr-review.md`.

Source anchors before Step 6c: `/home/nes/ai/workflows/audit.md` `## Process-Tree Relationship` lines 187-193; `/home/nes/ai/workflows/code-quality.md` `## Process-Tree Relationship` lines 202-206; `/home/nes/ai/workflows/pr-review.md` `## Synthesize And Post` lines 219-225.

- S1: `/home/nes/ai/workflows/audit.md` contains a substring referencing `agents-cli.md` section `Long-running agents` for pipeline-callable fanout completion. The searched file body must contain both `agents-cli.md` and at least one of `Long-running agents`, `fanout completion`, or `sentinel`.
  - Failure shape: `FAIL S1: /home/nes/ai/workflows/audit.md missing agents-cli.md plus Long-running agents/fanout completion/sentinel citation`
- S2: `/home/nes/ai/workflows/code-quality.md` contains a substring referencing `agents-cli.md` section `Long-running agents` for pipeline-callable fanout completion. The searched file body must contain both `agents-cli.md` and at least one of `Long-running agents`, `fanout completion`, or `sentinel`.
  - Failure shape: `FAIL S2: /home/nes/ai/workflows/code-quality.md missing agents-cli.md plus Long-running agents/fanout completion/sentinel citation`
- S3: `/home/nes/ai/workflows/pr-review.md` contains a substring referencing `agents-cli.md` section `Long-running agents` for pipeline-callable fanout completion. The searched file body must contain both `agents-cli.md` and at least one of `Long-running agents`, `fanout completion`, or `sentinel`.
  - Failure shape: `FAIL S3: /home/nes/ai/workflows/pr-review.md missing agents-cli.md plus Long-running agents/fanout completion/sentinel citation`

Success shape: `PASS sibling_workflow_citations: all ACs satisfied`.

### violation_list

Target path: `/home/nes/ai/agents/implementation-pipeline-orchestrator.md`.

Source anchor before Step 6c: `## Violation Detection and Escalation`, lines 608-623.

- V1: The violation list contains a bullet for missing or stale completion sentinels, missing cleanup-trap evidence, missing hard-timeout evidence, or absent canonical artifact verification on touched fanout joins.
  - Failure shape: `FAIL V1: /home/nes/ai/agents/implementation-pipeline-orchestrator.md Violation Detection and Escalation missing fanout-completion violation bullet`

Success shape: `PASS violation_list: all ACs satisfied`.

## Non-fire cases

A future runnable detector must not fire only because:

- An unrelated workflow contains a well-formed cross-reference to `agents-cli.md` for non-fanout reasons.
- Another operator uses `sentinel` strings for non-fanout completion, such as syntax-error sentinels in `/home/nes/ai/agents/red-phase-gate.md`.
- `/home/nes/ai/agents/coderabbit-operator.md` documents a rate-limit `sleep`; that is not a fanout-completion watcher.
- The sibling workflow cross-references in `/home/nes/ai/workflows/audit.md` `## Process-Tree Relationship` lines 187-193, `/home/nes/ai/workflows/code-quality.md` `## Aggregate Verdict` lines 164-178, and `/home/nes/ai/workflows/pr-review.md` `## Synthesize And Post` lines 219-225 cite completion or process-tree handoff without duplicating the full carve-out.
- Planning artifacts, tickets, and historical forensic snippets mention `^WROTE:` as problem evidence outside the source paths under test.

## Negative case — orphan-sleep + idle-timeout-only

### negative_cases

Targets: `/home/nes/ai/workflows/agents-cli.md`, `/home/nes/ai/agents/implementation-pipeline-orchestrator.md`, `/home/nes/ai/workflows/implementation-pipeline.md`, and future pipeline-callable fanout callers. Context anchor for residual acceptance: `/home/nes/ai/conventions/workflow-execution-violations.md` `### Named anti-pattern: Non-LOW gate residual acceptance`, lines 120-134.

- N1: If a future caller documents a fanout join that uses `until grep ... 2>/dev/null; do sleep N; done` as the primary completion signal, the eval fires. The orchestrator must not allow log-scrape-as-primary.
  - Failure shape: `FAIL N1: <path + section range> documents until grep sleep loop as primary fanout completion signal`
- N2: If a future caller documents a fanout join without a cleanup trap installed before the first background dispatch, the eval fires.
  - Failure shape: `FAIL N2: <path + section range> documents fanout join without pre-dispatch cleanup trap`
- N3: If a future caller documents a fanout join whose bounded-failure path advances with partial verdicts, the eval fires. This is the fanout-completion form of `/home/nes/ai/conventions/workflow-execution-violations.md` `### Named anti-pattern: Non-LOW gate residual acceptance`, lines 120-134.
  - Failure shape: `FAIL N3: <path + section range> documents partial-verdict residual advance after fanout-completion timeout`
- N4: If a documented fanout join's carve-out, or any caller's documented fanout, fails to require pre-dispatch removal of stale `<log>.done` sentinels, the eval fires. The carve-out's sentinel-shape paragraph in `/home/nes/ai/workflows/agents-cli.md` `## Long-running agents` must contain a removal token, `remove`, `delete`, `unlink`, or `clear`, applied to stale `<log>.done` before dispatch.
  - Failure shape: `FAIL N4: /home/nes/ai/workflows/agents-cli.md stale <log>.done sentinel removal token absent`

Success shape: `PASS negative_cases: all ACs satisfied`.

## Required trace fields when a runnable detector lands

A future runnable detector must emit:

- One `FAIL <AC_ID>: <evidence>` line per failed assertion.
- `PASS <test-id>: all ACs satisfied` on success.
- Exit code 0 on success and non-0 on failure.
- Evidence path, section header or searched line range, expected token set, observed token or absence, and lifecycle state.
- Per `/home/nes/ai/conventions/evals.md` lines 17-18 and 50-59, `WRITE` lifecycle means no runnable detector is required for this WU.

## Finding shape

When this eval fires, the finding cites:

- `eval_id: orchestrator-fanout-completion`
- the AC ID that fired, such as `F1`, `M2`, or `N1`
- the logical test-id, such as `agents_cli_carve_out`, `orchestrator_fanout_join_citations`, `workflow_mirror`, `sibling_workflow_citations`, `violation_list`, or `negative_cases`
- the file path plus section header and line range where the missing or violating token was searched
- the expected token set and observed evidence

Minimum finding fields follow `/home/nes/ai/conventions/evals.md` lines 35-48: `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`.

## Suggested action class

`revise-orchestrator-docs-or-add-sentinel`.

The fix is to revise the doc surface that failed the AC, or to add the missing sentinel, timeout, cleanup-trap, and canonical artifact verification wording. Do not loosen the eval to make a drifted source pass.

## Lifecycle notes

This eval is `WRITE` state. No runnable detector ships in this WU, and no runnable detector is required before Step 6c edits the source docs.

Future runnable detectors must use the frontmatter evidence source kinds: `markdown-section-header`, `markdown-fenced-pseudocode`, `markdown-substring`, and `filesystem-sentinel-presence`. Future runnable detectors must avoid the prohibited ACR-174 / ACR-199 anti-pattern of pytest-on-markdown structural scrapers or per-WU verify subtrees, matching `/home/nes/ai/conventions/evals.md` lines 97-103 and the precedent lifecycle notes in `/home/nes/ai/evals/acr-186-refactoring-commit-history-structural-test/eval.md` lines 153-164 and 180-186.

The target source paths are absolute `/home/nes/ai/` paths because the canonical workflow library lives there. This eval path is the only new eval artifact for ACR-203 Step 6b.

## References

- ACR-203 ticket and ACR-186 forensic: `/home/nes/projects/ai/planning/acr-203-watcher-fragility/.scratch/ticket.md` lines 17-38 and 65-70.
- ACR-203 Step 6a contract: `/home/nes/projects/ai/planning/acr-203-watcher-fragility/.scratch/contracts/acr-203-watcher-fragility.md`.
- Approved proposal: `/home/nes/projects/ai/planning/acr-203-watcher-fragility/.scratch/proposals/acr-203-ACR-203.md`.
- Hookpoints: `/home/nes/projects/ai/planning/acr-203-watcher-fragility/.scratch/research/acr-203-hookpoints.md`.
- ACR-202 broader resume relationship: `/home/nes/projects/ai/planning/acr-203-watcher-fragility/.scratch/ticket.md` line 67.
- ACR-174 / ACR-199 pytest-scraper anti-pattern: `/home/nes/ai/conventions/evals.md` lines 97-103 and `/home/nes/ai/evals/acr-186-refactoring-commit-history-structural-test/eval.md` lines 153-164.
- ACR-162 residual-acceptance retraction context: `/home/nes/ai/conventions/workflow-execution-violations.md` lines 120-134 and `/home/nes/projects/ai/planning/acr-162-decisions-retractions/proposals/acr-162-ACR-162.md`.
- NES-254 canonical-stat join manifest: `/home/nes/projects/ai/planning/nes-254-orchestrator-canonical-stat/contracts/nes-254-join-manifest.md`.
- Canonical agents CLI source: `/home/nes/ai/workflows/agents-cli.md` `## Long-running agents`, lines 97-117.
- Implementation-pipeline orchestrator source: `/home/nes/ai/agents/implementation-pipeline-orchestrator.md` lines 101-109, 176-185, 287-303, 305-313, 420-427, 509-519, and 608-623.
- Implementation-pipeline workflow mirror: `/home/nes/ai/workflows/implementation-pipeline.md` lines 131-139, 336-355, 462-463, and 494-502.
- PR-review gate source: `/home/nes/ai/workflows/pr-review.md` `## Gates`, lines 67-76, and `## Synthesize And Post`, lines 219-225.
- Audit sibling source: `/home/nes/ai/workflows/audit.md` `## Process-Tree Relationship`, lines 187-193.
- Code-quality sibling source: `/home/nes/ai/workflows/code-quality.md` `## Aggregate Verdict`, lines 164-178, and `## Process-Tree Relationship`, lines 202-206.
