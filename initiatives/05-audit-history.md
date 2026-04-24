# Initiative 05 — Audit history for revise/review cycles

**Status:** landed (convention + decision-encoder operator + operator-input propagation landed in this commit)
**Depends on:** — (orthogonal to 01-04; can run any time)
**Blocks:** — (soft: improves the quality of any multi-round cycle, including 02/03/04)

## Problem (user framing, verbatim)

> You can do is include an audit history. An audit history is actually generally important to improve the workflow. You pass the audit history for a particular LLM to that LLM. So every LLM has a history of the decisions it has made for a particular set of cycles, that way it can see that it itself is oscillating. As part of that it can recognize if the task is too complex or not (update the agent to understand this recognition) or come to its own determination. After process review for violations, another reviewer (also gpt-high) can encode decisions that were made. It can read through the history file and update decisions. It can also summarize older less relevant things in the history file. This is an important extension, I think, to our workflows.

## Firm constraints

1. **Per-role audit history, not global.** Each LLM in a cycle gets the history of **its own role's prior decisions** passed to it. Writers see the writer history; reviewers see the reviewer history.
2. **Self-oscillation visibility.** The history makes the LLM's own repetition visible — same fix applied at N sites over rounds, same finding family returning, same area re-opened.
3. **Self-determination.** The LLM uses the history to make its own call (`continue` / `apply` / `decompose`) rather than the orchestrator making it for them.
4. **Agent operators must learn to read history.** Operator files for roles that participate in multi-round cycles need to be updated so the agent knows to consume the history, recognize oscillation, and emit an explicit determination.
5. **Decision-encoder reviewer.** After each process-review round, a `gpt-high` decision-encoder reads the history file and: (a) encodes the decisions that were just made, (b) updates prior decisions if new evidence changes them, (c) summarizes older, less relevant entries to keep context size manageable.
6. **History lives next to the artifact** it describes, using the same scratch-artifact conventions (`.build/` for `~/ai/` workflow authoring; project-local equivalents elsewhere).

## Scope

**In scope:**
- New convention under `~/ai/conventions/` describing the audit-history schema: round number, proposal/review version, findings with oscillation classification, trend counters, decompose-trigger status.
- Updates to multi-round workflows (`~/ai/workflows/implementation-pipeline.md` §Risk Gates; `~/ai/workflows/pr-review.md` revise loops; `~/ai/workflows/coderabbit-loop.md`; the research workflow's re-synthesis path) so each round appends to the audit history before handing off.
- New operator: `decision-encoder` (`gpt-high`) that owns the history-maintenance cycle after each process-review pass.
- Updates to existing multi-round operators (`commit-hygiene-operator`, `coderabbit-operator`, `pr-review-operator`, `pr-justification-gauntlet`, `pr-justification-adjudicator`, `workflow-reviewer`) so they consume their role's history and emit explicit oscillation-aware determinations.
- Update the methodology doc (either a new `~/ai/conventions/revise-review-loops.md` or an extension of `gate-ownership.md`) to formalize the `low` / `oscillation` / `decompose` decision framework from Initiative 01's methodology.

**Out of scope:**
- Any single-pass workflow that does not iterate across rounds.
- Cross-role history merging (each role sees its own history; decision-encoder can maintain the union but roles do not see each other's raw history).
- Persistent cross-initiative histories (each initiative has its own history; reuse across initiatives is not required).

## Shape of the audit history file

Conceptual schema (finalized in the convention during proposal phase):

- **Methodology header** — the `terminate on low` / `decompose on oscillation` rules, so every agent reads them.
- **Artifact lineage table** — per-round proposal and review file paths.
- **Per-round summary** — verdict, findings (with kind / oscillation / echoes), closures of prior-round findings, reference-case behavior if applicable.
- **Round-over-round trend table** — findings count, blocking count, oscillation single-gen count, two-gen count, regression count, decompose-trigger status.
- **Decision register** — what was decided at each round and why; maintained by the decision-encoder.
- **Summarization tail** — older rounds compressed to trend-lines once they stop being load-bearing.

A prototype file was written inline for Initiative 01's round-3 decision at `.build/A17-risk-axes-audit-history.md`. Use that as the starting reference shape, not the final schema.

## Expected research tracks (sketch — to open when initiative starts)

- **Convention-shape study.** Compare the prototype history against what `coderabbit-loop.md` and `pr-justification-gauntlet.md` would need for their own multi-round loops. Land a single schema that covers all three.
- **Operator-update audit.** Which existing operators already consume a step_log (`workflow-reviewer` does per AGENTS.md) vs. which need to grow history-aware inputs.
- **Decision-encoder design.** Is it its own operator, or a mode of `workflow-reviewer`? Ownership lives in the proposal phase; this initiative just proposes.
- **Summarization trigger.** When does the encoder compress older rounds — after N rounds, on size threshold, or on trend-flattening?

## First use (inline, Initiative 01)

Used as a one-shot test of the pattern during Initiative 01's round-3 decision:
- Audit history compiled at `~/ai/.build/A17-risk-axes-audit-history.md`.
- Writer-perspective decision agent (`gpt-high`) and reviewer-perspective decision agent (`claude-opus`) dispatched independently with the history as primary input.
- Each returned its own `apply` / `round 3 H1 only` / `decompose` determination.
- Orchestrator (me) reconciles the two determinations before acting.

This experience should inform the schema and the operator design when the initiative is formally opened.

## Artifacts (empty until unblocked)

- `.build/A<NN>-audit-history-*-prompt.md`
- `.build/A<NN>-audit-history-*-findings.md`
- Proposal targets: new convention file; `decision-encoder` operator; workflow edits.

## Log

- **2026-04-23** — Initiative queued. Captured framing + firm constraints. Prototype history applied inline to Initiative 01's round-3 decision; results feed the formal schema later.
- **2026-04-23** — Research fan-out (4 tracks: R1 schema, R2 operator audit, R3 methodology, R4 encoder placement). Synthesis produced problem-def with 10 AG-gaps and 6 options (A-F). All options A-F moved to proposal.
- **2026-04-23** — Proposal cycle: v0 (9 non-blocking N-findings) → v2 (1 documented residual O1, no oscillation; ready to apply). Convergence in one round. Encoder placement resolved as new `decision-encoder` operator; summarization policy `≥12000 words`; single role-tagged history file.
- **2026-04-23** — Applied: new `~/ai/conventions/audit-history.md`, new `~/ai/agents/decision-encoder.md`, `audit_history_path?` input propagated across 7 operators (coderabbit-operator, pr-review-operator, pr-justification-gauntlet/interrogator/researcher/value-assessor/adjudicator), workflow references added to all 4 revise/review workflows (implementation-pipeline, pr-review, coderabbit-loop, research), AGENTS.md routing updated.
