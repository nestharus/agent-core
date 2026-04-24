# Initiative 03 — Process-tree review of workflow execution

**Status:** landed (this commit creates `process-tree-auditor` operator + `workflow-execution-violations.md` convention)
**Depends on:** —
**Blocks:** 04 (soft — Q&A resumption is cleaner to design once the process-tree + orchestrator split is explicit)

## Problem (user framing, verbatim)

> Our agents binary has the capability to research what an agent does and see the entire agent process tree. We have a process reviewer agent. So we can expand our workflow steps to utilize an agent to review the process for any violations within a given tree. A root orchestrator would execute another orchestrator, which would then produce a tree. Orchestrators are operators and root orchestrators interact directly with the user. So this allows us to reduce how much context the root orchestrator needs to deal with and give us a way to validate that the process ran correctly.

## Firm constraints

1. **Root orchestrator = the one that talks to the user.** Sub-orchestrators are operators invoked by the root; they do not talk to the user directly.
2. **Delegation produces a tree.** Every root-delegated sub-orchestrator run produces a full process tree that the `agents` binary can expose (see `agents trace` in the CLI help and `/home/nes/projects/agent-runner/README.md`).
3. **A process-review agent inspects the tree.** The existing `workflow-reviewer` operator (`~/ai/agents/workflow-reviewer.md`, `claude-opus`, inputs: `operator_file`, `step_log`, `expected_outputs?`, `mode?`) is the candidate starting point. It may need to grow a tree-inspection mode.
4. **Context reduction is a first-class goal.** The reason to delegate is to keep the root orchestrator's context small. Any design that leaks sub-tree details back up defeats the purpose.
5. **Review verifies execution, not design correctness.** This initiative is about "did the workflow run the way it was supposed to run"; it is not the risk/value gate from Initiative 01.

## Scope

**In scope:**
- Workflow edits to insert a process-tree review step at the right point in each pipeline. Candidates:
  - `~/ai/workflows/implementation-pipeline.md`
  - `~/ai/workflows/pr-review.md`
  - `~/ai/workflows/research.md` (synthesis handoff)
- `~/ai/agents/workflow-reviewer.md` — update or extend to consume a process tree (not just a linear step-log).
- Possibly new operator: `process-tree-auditor` if `workflow-reviewer` is too narrow.
- A convention documenting the root-orchestrator / sub-orchestrator split and the tree-handoff contract.
- Reference to `agents trace` in `/home/nes/projects/agent-runner/README.md` as the ground-truth source for what the tree contains.

**Out of scope:**
- Changing what `agents trace` produces.
- Replacing existing per-phase gates with tree review; tree review is additive.

## Expected research tracks (sketch — to scope when opened)

- **`agents trace` capability audit.** What the binary actually exposes per node of the tree: model used, prompt, output, tool calls, children. Decide what a reviewer needs vs. what leaks context.
- **Workflow-reviewer operator audit.** Current inputs, mode, and output. Can it ingest a tree? If not, what extension is cheapest?
- **Placement study.** For each target workflow, where in the phase list does tree review belong? Before or after the existing human gate? Blocking or advisory?
- **Violation taxonomy.** What counts as a "violation" — skipped phase, wrong model, missing artifact, unexpected parallelism, misrouted operator? The taxonomy determines whether a violation is hard-fail or flag-and-continue.

## Artifacts (empty until unblocked)

- `.build/A<NN>-process-tree-review-*-prompt.md`
- `.build/A<NN>-process-tree-review-*-findings.md`
- Proposal target: workflow edits + workflow-reviewer extension.

## Log

- **2026-04-23** — Initiative queued. Captured framing + firm constraints.
- **2026-04-23** — Research fan-out: R1 agent-runner tree capability (with real `agents trace` sample), R2 workflow-reviewer audit, R3 placement analysis, R4 violation taxonomy. Synthesis produced 12 PG-gaps and 6 options (A-F).
- **2026-04-23** — Proposal cycle: v0 (7 non-blocking P-findings) → v2 (1 cosmetic Q1 style mismatch) → apply with Q1 folded in. Convergence in one revision round. All 6 options resolved (no deferrals): new `process-tree-auditor` operator (not a workflow-reviewer mode), input contract includes `process_tree_path` + `expected_process` + optional `subtree_root_uuid`, violation taxonomy landed as new convention, tree-review emits report (not audit-history entries — Init 05 split preserved), per-site gate ownership mix of human/model/advisory.
- **2026-04-23** — Applied: new `~/ai/agents/process-tree-auditor.md`, new `~/ai/conventions/workflow-execution-violations.md`, references added to implementation-pipeline / pr-review / research / coderabbit-loop / roadmap workflows, AGENTS.md routing updated, agentsmd-maintenance-orchestrator gets optional tree-review sub-step.
