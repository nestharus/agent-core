# Risk Reduction Workflow

A general-development workflow that runs **between** implementation tickets to lower the project-level risk profile. The implementation pipeline produces per-WU risk profiles and aggregates them into the project profile (`<project>/planning/risk-profile.md` per `~/ai/conventions/risk-profile.md`). This workflow consumes that aggregate and picks the next risk-reduction unit.

The principle: when implementation work runs in lean mode, it is paying down speed-now against risk-later. Risk-reduction work pays that debt back. A project that runs only implementation pipelines without risk-reduction sweeps accumulates risk; eventually every new WU scores HIGH on the touched surface and the pipeline runs exhaustive every time, which is the same as not having lean mode at all.

This workflow is **not** part of the implementation pipeline. It produces its own small ticket per item. Items are typically smaller than implementation WUs because the change is focused: write tests for one uncovered surface, consolidate two duplicate scripts, document one undocumented contract, etc.

## When to use

- The project's `planning/risk-profile.md` has accumulated MEDIUM/HIGH entries the team has not addressed.
- A retrospective shows the implementation pipeline is running exhaustive mode on most WUs because the touched surfaces keep coming back HIGH.
- A new initiative is about to start on a surface scored HIGH; risk-reduction work as a precursor reduces the new initiative's pipeline cost.
- An operator notices a recurring failure pattern (the same axis scoring HIGH across multiple WUs in the same surface area).

## Do not use when

- The project has no aggregated risk profile yet. Risk-reduction work without a tracked profile is speculative and tends to bikeshed. Build the profile first via the implementation pipeline, then start reducing.
- A WU is in flight on the same surface. Risk-reduction work concurrent with a WU on the same surface creates merge conflicts and split attention. Run sequentially.

## Item types

Risk-reduction items map to specific axes from `~/ai/conventions/risk-profile.md`:

| Item type | Reduces axis | Typical effort | Output |
|---|---|---|---|
| **Characterization tests** | `coverage-gap`, `behavioral-ambiguity` | small to medium | new tests on the worktree branch; uncovered behaviors now have captured assertions |
| **Contract documentation** | `behavioral-ambiguity`, `language-fragmentation` (when contracts cross languages) | small | a markdown contract doc next to the surface; ambiguities resolved by writing them down |
| **Duplicate consolidation** | `duplicate-system-count`, `change-path-entropy` | medium to large | one implementation; the duplicate's callers re-pointed; deletion of the dead path |
| **Brittleness cleanup** | `brittleness-markers` | small to medium | TODO/FIXME/HACK addressed or converted to tracked tickets; xfail/skip resolved or tagged |
| **Lifecycle documentation** | `lifecycle-visibility` | small | a lifecycle map for the surface, lives next to the code or in `planning/` |
| **Cross-language schema unification** | `language-fragmentation`, `change-path-entropy` | medium | one schema definition; generated bindings across languages instead of mirrored hand-written types |
| **Entrypoint deprecation** | `blast-radius` | small to medium | an entrypoint with no callers or replaced callers gets deleted; the surface shrinks |

The list is not exhaustive. New item types appear as the project's risk-profile axes evolve.

## Procedure

### Step 1 — Pick the item

1. Read `<project>/planning/risk-profile.md`. Sort entries by severity (HIGH first), then by recency (entries surfaced by recent WUs first), then by surface activity (surfaces with active or upcoming work first).
2. Pick one entry. The item is **one axis × one surface**. "Reduce all the brittleness markers in the codebase" is not an item; "Resolve the three xfail markers in `update_manager/download_update.sh`" is.
3. Write a short ticket on the project's tracker (per the project's routing rules — for the rfqautomation umbrella, INFA for non-cloud infra, CLOUD for cloud-launch sub-projects, etc.). Use a `hardening` label so these are visible as a class. Some projects use `risk-reduction` instead; the label name is project-local — check `AGENTS.md`. The rfqautomation umbrella uses `hardening`.

### Step 2 — Decide the lever

For each item type, the lever is the same: narrow the work until it can be reviewed in isolation.

- **Characterization tests**: dispatch a `gpt-high` test-writer with the touched surface as input, the existing tests as reference, and instruction to capture **current** behavior (not intended). Bugs found during writing are filed as separate tickets per `~/ai/conventions/risk-profile.md` § Discoveries.
- **Contract documentation**: dispatch a `gpt-high` researcher with the surface and a request for a contract doc (parameters, expected output, side effects, error modes). The doc lives next to the code or in `planning/contracts/<surface>.md` per project convention.
- **Duplicate consolidation**: this is implementation work and goes through the full implementation pipeline (`~/ai/workflows/implementation-pipeline.md`) with a tight scope: keep one implementation, re-point callers, delete the other. Phase 2.5 verifies the duplicates are functionally equivalent first; if they are not, that is a separate bug (file a blocking ticket and halt).
- **Brittleness cleanup**: dispatch the appropriate tool for the marker. `xfail` resolution dispatches the test-writer + green-phase-gate; TODO conversion dispatches `jira-operator` to file follow-ups + edits the comment to reference the ticket. The orchestrator for this is the local agent acting as orchestrator.
- **Lifecycle documentation**: dispatch a `gpt-high` researcher to draw the lifecycle map for the surface. Use the `code-tracer` operator (`~/ai/agents/code-tracer.md`) when the lifecycle crosses languages.
- **Cross-language schema unification**: implementation work; goes through the full pipeline with scope = one schema and its mirrors.
- **Entrypoint deprecation**: implementation work if the entrypoint has callers (the work is re-pointing them); a trivial deletion if it doesn't.

### Step 3 — Verify the axis improves

After the work lands:

1. Re-score the affected axis on the surface per `~/ai/conventions/risk-profile.md`. Evidence-based: the previous evidence that justified the MEDIUM/HIGH score should no longer apply.
2. Update `<project>/planning/risk-profile.md`: either remove the entry (axis returned to LOW with evidence) or downgrade it (HIGH → MEDIUM).
3. If the axis did not improve, the work was not actually a risk-reduction item — it was unrelated work that happened to touch the surface. File the actual remaining axis problem as a follow-up risk-reduction ticket and do not claim the original was resolved.

## Cadence

Risk-reduction is a cadence, not a project. Run it:

- **Per-N-WUs**: every N implementation WUs, dispatch one risk-reduction item. N is a project decision; somewhere between 3 and 10 is typical.
- **Pre-initiative**: when an initiative is about to start on a HIGH surface, run risk-reduction items on that surface first.
- **Reactive**: when a WU's Phase 2.5 surfaces a HIGH surface that other WUs will keep hitting, file a risk-reduction ticket immediately even if the current WU proceeds.

## Anti-pattern

- **Risk-reduction work that grows scope**: an item is one axis × one surface. If the work expands to "while we're here, let's also...", that's a different item; file the expansion as a separate ticket.
- **Risk-reduction without re-scoring**: the axis must be measurably improved per the convention. "It feels less risky now" is not the verification.
- **Speculative risk-reduction**: only items that come from the project profile (which only contains evidence-backed entries from real WUs) are valid items. Items that come from "I think we should test X" without a profile entry belong on a backlog board, not the risk-reduction queue.
- **Risk-reduction as project housekeeping**: this is real work with risk and review. The implementation pipeline applies (with whatever mode the touched surface scores). Do not skip Phase 2.5 because "it's just cleanup."
