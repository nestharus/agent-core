# Gate Ownership

Every phase in every workflow has a gate.

Gate ownership defines who or what validates that the phase is
complete, and therefore whether the user is asked at that boundary.

Getting this wrong burns cycles and erodes trust.

Overasking at model-owned gates is a common failure mode.

Rule of thumb:

- **Phases that set scope** -> user-owned gate.

- **Phases that validate design or code** -> model-owned gate.

- **Phases that generate artifacts** -> model-owned gate
  with continuous validation.

Model-role rationale for named gates lives in
`~/ai/models/roles.md`.

Tier-3 action approval rules live in
`~/ai/workflows/tiered-approval.md`.

## Declared roles

This file's classifications under `~/ai/conventions/code-quality.md` § Declared roles:

- `mapper` — Maps workflow phases and gates to their owning validator or human decision point.
- `validator` — Defines ask and do-not-ask rules that validate whether a gate should involve the user.

## Gate-owner table

This table is cited by
`~/ai/workflows/implementation-pipeline.md`,
`~/ai/workflows/roadmap.md`, and
`~/ai/workflows/research.md`.

| Phase | Gate owner | What the gate does |
|---|---|---|
| **Implementation pipeline** | | |
| RCA (bugs) | Model - orchestrator advances when each named root cause has a newly created reproduction test, an existing failing test accepted as the reproduction signal, or documented `Hypothesis (unreproduced)` | No default human gate. Surface a NEEDS_INPUT new-value-question only if the reproduced or accepted cause invalidates the original framing. |
| Problem research (optional) | Model - orchestrator advances when framing artifact is non-empty and free of unresolved new-value questions | No default human gate. |
| Synthesize user needs (optional) | Model - orchestrator advances when synthesis artifact is non-empty and free of unresolved new-value questions | No default human gate. |
| Existing-state risk profile (Phase 2.5) | **Human** | User confirms the `problem map` names the right current terrain. **First of the two surviving human gates** in the implementation pipeline. |
| Proposal | Model - audit (`gpt-high`) + scope (`claude-opus`) + shortcut (`claude-opus`) + supported-surface (`claude-opus`) in parallel | The risk assessment is the review. No human gate. |
| Alignment (optional) | Model - `claude-opus` | Direction check. Returns `ALIGNED`, `MISALIGNED`, or `NEEDS_REVISION`. |
| Hookpoint research | Model - orchestrator advances when artifact is non-empty, contains the four required sections, and does not invalidate the approved problem map | No default human gate. Returning to Phase 2.5 re-engages the problem-map human gate. |
| Implementation | Continuous (test suite, CI, smoke, tests-first encoding artifacts) | No explicit gate. Failures block the pipeline, and Step 6b must produce risk-annotated tests plus any required residual-risk artifact before Step 6c writes code. |
| CodeRabbit | Model - loop owner agent | Rerun until per-pass value drops to zero. |
| Test audit | Model - `gpt-high` | Validate that tests encode intended behavior first, reduce named risks, preserve fixture externality, keep explicit levels, and do not weaken ground-truth tests to match implementation. Checklist gate. |
| Multi-concern | Model - `claude-opus` | Decide whether the PR should be split. |
| Justification | Model - `claude-opus` | Decide whether every change justifies its presence. |
| Supported-surface verification | Model - supported-surface verification role (see `~/ai/models/roles.md`) | Validate that the actual diff still reduces risk on the approved supported surface; return to research on invalidated assumptions and stop the PR on non-positive value. |
| Commit hygiene | Model - `gpt-high` | Validate small, testable, single-concern commits. |
| Draft PR open | Automated (orchestrator) | Routine pipeline output. |
| Promote to ready-for-review | Automated (orchestrator runs `gh pr ready` after Phase 8 process-tree audit clears) | No human gate. |
| **NEEDS_INPUT new-value question** | **Human** | The orchestrator surfaces sub-agent NEEDS_INPUT artifacts to the root only when they carry a previously-unevaluated value, scope, or trade-off question. **Second of the two surviving human gates.** Procedural NEEDS_INPUT is resolved by the orchestrator without bothering the user. |
| **Roadmap pipeline** | | |
| Market research | Human | User approves the market framing. |
| Executive roadmap | Model - 3x risk (market-misread / dependency / completeness) | All risks must be `LOW`, or revise. |
| Executive approval | Human | User approves strategic ordering. |
| Engineering roadmap | Model - 3x risk (feasibility / integration / drift) | All risks must be `LOW`, or revise. |
| Engineering approval | Human | User resolves ordering disagreements. |
| AI roadmap | Model - 3x risk (decomposition / coverage / dependency) | All risks must be `LOW`, or revise. |
| AI approval | Model - orchestrator validates completeness | Human only on divergence. |
| Ticket generation | Human | User reviews generated tickets. |
| **Research workflow** | | |
| Scope | Human | User confirms the question. |
| Research (per researcher) | Model - coordinator | Each returned finding is accepted by the coordinator. No human gate per report unless the project opts in. |
| Synthesis | Model - coordinator | Integrates findings into the deliverable. |
| Decision | Human | User decides next steps based on the synthesized report. |

For research-heavy pipelines, a project may opt into
human-gating each researcher report.

That is a project-level override stated in the project's
`AGENTS.md`, not the `~/ai/` default.

## When to ask the user

Ask at phase boundaries where the table assigns the gate to the
user.

Ask before any Tier-3 action.

That is per action, not per workflow boundary.

See `~/ai/workflows/tiered-approval.md`.

Ask when blocked on credentials, external access, or something
only the user can physically do.

Examples:

- Logging into a site.

- Paying a bill.

- Approving a third-party dialog.

- Creating access that only the user controls.

Ask when two clearly-defined paths have different irreversible
consequences.

Present both paths and let the user choose.

Do not flood them with six variants.

## When NOT to ask the user

Do not ask to review a proposal.

The proposal gate is the risk gate.

Do not ask to review a PR.

The review gates already validated it.

Do not ask things you can verify yourself.

Read the file.

Search the code.

Run the command.

Do not ask things already recorded in
the caller-supplied project decisions path, `NOTES.md`, or the project equivalent.

Do not ask "is this OK?" on every action.

Overasking erodes trust faster than occasional mistakes.

Do not ask at model-owned gates.

If the model gate returned `LOW`, proceed.

Do not double-check it with the user.

Model-owned gates are not followed by human local-review approval before automated draft PR opening.

Minor design decisions that fit within a phase's scope are not
user gates.

Make the call.

Document it in `${worktree_path}/DECISIONS.md` when running inside a WU, or in the caller-supplied project decisions path otherwise.

Keep moving.

## Research-heavy and artifact-heavy variants

Some projects opt into stricter gates.

- **Per-report research gate**: human reviews each researcher's
  findings before the coordinator synthesizes.

- **Per-artefact plan/review gate**: every generated artifact
  goes through its own 3x risk gate.

Use the per-report research gate when each researcher's context
matters directly to the user.

Typical cases:

- Product strategy.

- Design research.

- Sensitive exploratory work where the user wants to steer
  interpretation early.

Use the per-artefact plan/review gate when artifacts are
user-visible or contractually binding.

Typical cases:

- Tickets handed to other teams.

- Reports sent outside the project.

- Writeups that become the system of record.

Projects declare these variants in their own `AGENTS.md`.

`~/ai/` defaults remain the table above.
