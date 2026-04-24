# Audit History

Use audit history for multi-round revise/review cycles where a writer, reviewer, gate, or loop may need to decide `continue`, `apply`, or `decompose` from prior rounds.

This convention gives each role visibility into its own prior decisions while preserving one canonical history file for the loop.

## Applicability

Create or update an audit-history file when a workflow enters a second revise/review round, a pass loop has produced findings that may repeat, or a process-review round hands off to another role.

An inline history block is acceptable for a single prompt, but it is not the canonical state for shared `~/ai/` multi-round workflows. Shared workflows use `audit_history_path?` when they support this convention.

Domain-specific rolling state, such as `threads.json`, can remain the operational state for that workflow. It counts as audit-history input only when the next prompt or the `decision-encoder` projects the required fields below into the canonical audit-history file.

## File Structure

Use one audit-history file per revise/review loop. Do not create one file per role by default.

The file contains shared round summaries plus role-tagged sections:

```md
# Audit history — <initiative or workflow name>

## Purpose
## Artifact lineage
## Round summaries
## Role histories
### Writer
### Reviewer
### Interrogator
### Researcher
### Value assessor
### Adjudicator
### CodeRabbit operator
## Decision register
## User Q&A Inputs
## Watch signals
## Summarization tail
## Final state
```

Only include role subsections that exist in the loop. A role consumes its own role subsection, the shared round summaries, the decision register, and active watch signals.

## Required Schema

Each round summary must record:

- `round`: round number.
- `artifact_under_review`: path or identifier for the artifact reviewed in that round.
- `round_artifacts`: paths to proposal/review/result files created in the round.
- `prior_finding_counters`: closure, regression, weakened, not-closed, and intact counts for prior findings.
- `new_findings`: stable finding IDs for this round.
- `oscillation`: classification and ancestor chain for same-label, same-family, fix-created, two-generation, or named three-generation recurrence.
- `decompose_trigger`: `fired` or `not fired`, with trigger reason.
- `watch_signals`: named areas or chains to inspect in the next round.
- `verdict_or_determination`: `continue`, `apply`, `decompose`, or the loop-specific equivalent.
- `role_outputs`: role-tagged outputs and determinations that fed the round.
- `next_handoff`: what the next writer, reviewer, or operator must read first.

Each finding must record:

- `id`: collision-safe round finding ID.
- `severity`: blocking, non-blocking, cosmetic, or loop-specific severity.
- `status`: new, closed, intact, weakened, regressed, not closed, carried, or deferred.
- `summary`: one-sentence finding statement.
- `artifact_location`: file, section, path, or thread location.
- `ancestor_chain`: prior finding IDs when this finding continues a chain.
- `oscillation_classification`: none, same-label, same-family, fix-created, two-generation, named three-generation.
- `closure_expectation`: what would count as closed next round.

## Round Entry Template

```md
### Round <N> — <artifact> reviewed

- Artifact under review: `<path>`
- Round artifacts: `<path>`, `<path>`
- Prior finding counters:
  - closed: <n>
  - intact: <n>
  - weakened: <n>
  - regressed: <n>
  - not closed: <n>
- New findings:
  - `R<N>-F01` — <severity>; <summary>; ancestor chain: <none or IDs>; oscillation: <classification>
- Oscillation:
  - same-label: <n>
  - same-family: <n>
  - fix-created: <n>
  - two-generation: <n>
  - named three-generation: <n>
- Decompose trigger: <fired | not fired>; reason: <reason>
- Watch signals for next round:
  - <chain or area>
- Verdict or determination: <continue | apply | decompose>
- Role outputs:
  - <role>: <determination and artifact path>
- Next handoff: <what the next role reads first>
```

## Role Histories

Each role subsection records only that role's prior decisions, self-oscillation signals, and current determination. Shared facts stay in `Round summaries`.

Role-history entries use this shape:

```md
### <Role>

#### Round <N>
- Input read: <audit sections and artifacts>
- Role decision: <continue | apply | decompose | loop-specific equivalent>
- Reason: <short evidence-backed reason>
- Self-oscillation signal: <none | same issue | same family | fix-created | two-generation | named three-generation>
- Next role-local watch: <watch item or none>
```

## Decision Register

The decision register is not a substitute for review verdicts. It records what the loop decided after reading review verdicts and role determinations.

Each entry records:

- round
- decision: `continue`, `apply`, or `decompose`
- deciding inputs: review verdicts, role determinations, hard triggers, and watch signals
- reason
- dissent or ambiguity, if any
- next action

## User Q&A Inputs

Q&A turns from `~/ai/conventions/agent-questions-and-session-graph.md` are not audit-history rounds by themselves. They become audit-history inputs only when the answer affects a revise/review loop, gate, verdict, or `continue` / `apply` / `decompose` decision.

When a Q&A turn affects a loop decision, record:

- `question_id`
- question artifact path
- answer artifact path
- originating invocation UUID and session ID when known
- continuation method: `resume-by-session-id` or `session-files-fallback`
- deciding input summary
- applied-to artifact, phase, gate, or finding chain
- continuation evidence path

The decision register should cite the answer as a deciding input, not as a replacement for role verdicts or gate outputs.

## Summarization Tail

The `decision-encoder` keeps the current round and two prior rounds in full.

After round 4, it summarizes older closed rounds into the summarization tail before handing off to the next role. It must summarize earlier if the audit-history file is `≥ 12,000 words`.

Never summarize away:

- active watch signals
- unresolved prior-finding closure, weakening, regression, or not-closed state
- active ancestor chains
- decompose-trigger status and trigger reason
- the latest decision-register entry
- any role determination that is still part of the current `continue` / `apply` / `decompose` decision
- Q&A inputs that remain active deciding inputs, unresolved blockers, or cited evidence for the latest decision-register entry

Summaries must preserve trend lines, final disposition of old findings, and any chain that later findings cite.

## Revise/Review Rule Set

Track round-over-round finding counts, prior-finding closure, oscillation classification, decompose-trigger status, watch signals, and determinations.

`low` is qualitative, not a fixed count. A round is low when the review is clean or only cosmetic/documented debt remains, and no hard trigger fires. Judge low against artifact size and stakes.

Classify oscillation when:

- the same issue or same label returns
- the same family, same section, or sibling-site variant appears
- reverting the prior fix would remove the finding
- a two-generation sibling-of-sibling chain appears
- a named three-generation watch area recurs after being declared

Final-pass trigger: a prior-round finding returning in the next round after a targeted fix is a final-pass trigger and escalates classification by one generation.

Hard decompose triggers:

- any prior finding is weakened, regressed, or not closed
- any two-generation oscillation in normal iteration
- any strict area-based two-generation recurrence when the chain has been named
- any named three-generation recurrence when the prompt or audit history declared that watch area
- any narrow-scope compliance violation in a narrow repair round
- same-family issue production at or above the prior same-family production rate, unless the audit history records a different denominator before the round starts
- decompose did not stick: remnants, named three-generation recurrence in the removed chain, or seam-wrong evidence

If no hard trigger fires and findings are low, the loop may `apply`.

If no hard trigger fires but the remaining call depends on role-local self-assessment, dispatch decision agents under `Decision-agent dispatch`.

## Decision-Agent Dispatch

Dispatch separate per-role decision agents only at ambiguous Phase-4-style decision points where hard triggers do not decide `apply`, `continue`, or `decompose`.

Role-local determinations emitted by existing operators are the default. Gauntlet roles already emit their determinations through their normal outputs; do not dispatch separate decision-agent operators for those roles. Dispatch separate decision agents only for the writer+reviewer reconciliation pattern at Phase-4-style gates.

The dispatch boundary still leaves residual judgment with the orchestrator. That residual judgment is inherited from R3's evidence base, where the exact requiredness boundary remains qualitative.

Do not dispatch decision agents every round. Do dispatch them when the orchestrator is about to call the loop despite residual findings, accept non-blocking findings, or choose one more narrow pass without a hard trigger.

Each decision agent receives the audit history and returns exactly one determination:

- `apply`
- `continue`
- `decompose`

The orchestrator reconciles determinations and records the outcome in the decision register.

## Naming Convention

Reserve problem-gap prefixes for problem definitions and synthesis gaps. For this initiative, audit-history gaps use `AG<N>`.

Round findings use:

```text
R<round>-F<NN>
```

Examples:

- `R1-F01`
- `R2-F03`
- `R3-F01`

Ancestor chains use the full IDs:

```text
R1-F04 -> R2-F01 -> R3-F01
```

Do not use bare round-letter finding prefixes such as `F`, `G`, `H`, or `I` in shared revise/review loops. They can collide with problem-definition gap IDs.

Pre-convention artifacts (commits before Init 05 lands) are grandfathered; this convention applies to new revise/review loops starting from this file's merge.
