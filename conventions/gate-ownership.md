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

## Gate-owner table

This table is cited by
`~/ai/workflows/implementation-pipeline.md`,
`~/ai/workflows/roadmap.md`, and
`~/ai/workflows/research.md`.

| Phase | Gate owner | What the gate does |
|---|---|---|
| **Implementation pipeline** | | |
| RCA (bugs) | Human | User decides if the bug is worth fixing at all. |
| Problem research (optional) | Human | User confirms scope framing. |
| Synthesize user needs (optional) | Human | User confirms the mapping and answers open questions. |
| Proposal | Model - audit (`gpt-high`) + scope (`claude-opus`) + shortcut (`claude-opus`) in parallel | The risk assessment is the review. No human gate. |
| Alignment (optional) | Model - `claude-opus` | Direction check. Returns `ALIGNED`, `MISALIGNED`, or `NEEDS_REVISION`. |
| Hookpoint research | Human | User confirms which pre-existing code survives. |
| Implementation | Continuous (test suite, CI, smoke) | No explicit gate. Failures block the pipeline. |
| CodeRabbit | Model - loop owner agent | Rerun until per-pass value drops to zero. |
| Test audit | Model - `gpt-high` | Tests cover the stated acceptance criteria. Checklist gate. |
| Multi-concern | Model - `claude-opus` | Decide whether the PR should be split. |
| Justification | Model - `claude-opus` | Decide whether every change justifies its presence. |
| Commit hygiene | Model - `gpt-high` | Validate small, testable, single-concern commits. |
| Draft PR open | Automated (no gate) | Routine pipeline output. |
| Promote to ready-for-review | Human | User decides when the PR is ready for external eyes. |
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
`DECISIONS.md`, `NOTES.md`, or the project equivalent.

Do not ask "is this OK?" on every action.

Overasking erodes trust faster than occasional mistakes.

Do not ask at model-owned gates.

If the model gate returned `LOW`, proceed.

Do not double-check it with the user.

Minor design decisions that fit within a phase's scope are not
user gates.

Make the call.

Document it in `DECISIONS.md`.

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
