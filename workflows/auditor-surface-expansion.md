---
workflow:
  id: auditor-surface-expansion
workflow_dispatch_contract:
  orchestrator: "source A1 auditor"
  inputs:
    - "source auditor report context, bounded question, repo_root, scratch_dir, planning_dir, and evidence paths"
  expectations:
    - "collects bounded context for the source auditor without changing the review target"
  outputs:
    - "context artifact consumed by the source auditor"
  non_goals:
    - "does not implement a concrete research operator"
    - "does not own final auditor verdicts"
---
# Auditor Surface Expansion Workflow

## Purpose

Provide a bounded context-expansion workflow for an A1 auditor that needs more evidence before deciding whether a finding is owned by the current review surface.

## Use When

- Use when the source auditor has one bounded context question that affects ownership, boundary, topology, or interface understanding.
- Use when existing artifacts do not answer the question and the auditor cannot classify the finding without a narrow evidence expansion.
- Use when the caller can name the source auditor, the unresolved question, and the evidence path that should receive the answer.

## Do Not Use When

- Do not use for curiosity, broad whole-system cleanup, shortcut justification, scope expansion, or commit-hygiene review.
- Do not use to implement a new research agent or redefine any A1 threshold.
- Do not use when the source auditor already has enough evidence to decide its own verdict.

## Inputs

- Source auditor name and current report or prompt context.
- One bounded question.
- `repo_root`, `scratch_dir`, and `planning_dir`.
- Evidence paths already read by the source auditor.
- Output path for the returned context artifact.

## Outputs

- One context artifact answering the bounded question or explaining why it remains unresolved.
- A short evidence list naming paths, anchors, traces, or commands consulted.
- A terminal disposition: `context-sufficient`, `existing-residual-identified`, `NEEDS_INPUT:<question_artifact>`, or `BLOCKED:<reason>`.

## Procedure

1. The source auditor writes one bounded prompt file that names the source verdict question and the evidence gap.
2. Dispatch child work only with `agents -m <model> -f <prompt-file>`.
3. Do not run bare `agents`, and do not use the host Task tool or any host sub-agent dispatch.
4. Consume the returned context artifact and decide whether a single bounded follow-up is necessary.
5. Return the context artifact to the source auditor; the source auditor resumes and owns the final verdict.

## Stop Conditions

- Stop when context is sufficient for the source auditor to decide ownership or boundary.
- Stop when the evidence identifies an existing residual rather than a current finding.
- Stop with `NEEDS_INPUT:<question_artifact>` when a genuine new value, scope, or trade-off question remains.
- Stop with `BLOCKED:<reason>` when required evidence cannot be read or the bounded question cannot be answered from available sources.

## Non-Negotiables

- For this workflow, expanded context is evidence, not the review target.
- The source auditor owns the final verdict.
- Do not redesign A1 thresholds, terminal vocabulary, or failure modes.
- Do not implement a concrete research operator in this workflow.
