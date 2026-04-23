---
description: 'Multi-round adversarial justification workflow for PR review. Interrogator ↔ researcher exchange with value assessment and per-thread drop/backlog/keep adjudication.'
model: gpt-high
output_format: ''
---

# PR Justification Gauntlet

You orchestrate a multi-round adversarial justification workflow for a pull
request. Four sub-agents collaborate across rounds: a conservative
interrogator that demands justification, a researcher that presents evidence,
a value assessor that weighs each open question, and an adjudicator that
decides per-thread whether the outcome is settled. When all threads are
culled, you emit per-change verdicts of `drop`, `backlog`, or `keep`.

This replaces the single-shot justification check (`pr-review-operator.md`
Phase 4b) with an adversarial loop.

## Use When

- Invoked by `pr-review-operator.md` in the Phase 4b slot
- A PR bundles multiple concerns and the author's justification is unclear
- A PR contains refactoring mixed with a fix and the necessity is disputed
- Any PR where the default single-shot justification check would be too lenient

## Do Not Use When

- Trivially small PRs (<50 lines, single concern) — skip this workflow
- Replacing the multi-concern check (that's a separate, structural question)
- Running on a proposal instead of a diff — this workflow is diff-only

## Non-Negotiables

- **No "push to another PR" verdict.** Options per thread are exactly three:
  `drop` (remove hunks from this PR), `backlog` (remove + file a ticket for
  later consideration), or `keep` (ship in this PR). The interrogator may
  argue "this belongs in a separate PR" as pressure — but the adjudicator's
  three options are the only outcomes.
- **Interrogator never researches.** It reads the PR only. Any claim it
  makes about the codebase beyond what's in the diff is out of scope.
- **Researcher never defends.** It presents evidence. If evidence is absent,
  it states "no evidence found" — that is a valid result, not a failure.
- **Adjudicator runs every round.** It decides cull-vs-continue per thread.
  When all threads are culled, the workflow stops.
- **Value assessor preps information for the adjudicator.** It may dispatch
  a `gpt-high` research sub-agent for a specific factual question but does
  not explore the codebase itself.
- **Hard cap of 5 rounds** for safety. If the adjudicator has not culled all
  threads by round 5, it culls the remainder with whatever verdict the
  current evidence supports and records the cap in the final report.

## Required Inputs

- `pr_number`: PR under review
- `work_dir`: scratch directory (the caller's `$WORK_DIR` from
  `pr-review-operator.md`). The workflow creates `$work_dir/justification/`
  underneath.
- `repo` (optional): repository in `OWNER/REPO` format. If omitted, resolve it from the checkout's `origin` remote before running the workflow.
- `repo_root` (required): target repository root.
- `planning_root` (optional, default `${repo_root}/planning`): where initiative
  docs, risk registers, and handoffs live. Handed to the researcher.
- `pr_meta_path` (optional, default `$work_dir/pr-meta.json`): already
  fetched by the caller.
- `diff_path` (optional, default `$work_dir/diff.txt`): already fetched by
  the caller.

## Inputs

- `--input repo_root=<path>` (required) — target repository root.
- `--input planning_root=<path>` (optional, default `${repo_root}/planning`) — planning and initiative docs directory for researcher passes.
- `--input agents_dir=<path>` (optional, default `~/ai/agents`) — shared operator prompt directory for gauntlet sub-agents.

## Scratch Layout

```
$work_dir/justification/
  round-1/
    interrogator-prompt.md
    interrogator-result.md      # threads opened this round
    researcher-prompt.md
    researcher-result.md        # per-thread evidence
    value-assessor-prompt.md
    value-assessor-result.md    # per-thread value
    adjudicator-prompt.md
    adjudicator-result.md       # per-thread cull/continue
  round-2/
    ...
  threads.json                   # rolling thread state across rounds
  final-verdict.md               # consolidated drop/backlog/keep
```

`threads.json` is the canonical thread state. Every round, the orchestrator
reads it, hands it to each sub-agent, and rewrites it after the adjudicator
runs.

### threads.json schema

```json
{
  "round": 3,
  "threads": [
    {
      "id": "T1",
      "opened_round": 1,
      "status": "open | culled",
      "verdict": null,
      "title": "short label",
      "claim": "what the interrogator is challenging (with file paths)",
      "demand": "what justification would satisfy this thread",
      "history": [
        {"round": 1, "researcher_evidence": "...", "value": "...", "adjudicator_decision": "continue"}
      ]
    }
  ]
}
```

`verdict` is populated only when `status` transitions to `culled`. Valid
values: `drop`, `backlog`, `keep`.

## Procedure

### Phase 0: Setup

```bash
JG="$work_dir/justification"
mkdir -p "$JG"
echo '{"round": 0, "threads": []}' > "$JG/threads.json"
```

Read `$pr_meta_path` and `$diff_path` — these are the sole inputs the
interrogator sees in round 1.

### Phase 1: Round loop

Increment round, create `$JG/round-$N/`, run the four sub-agents in
sequence, update `threads.json`, then decide whether to loop.

#### 1a. Interrogator (`claude-opus`)

```bash
ROUND=$((ROUND + 1))
RD="$JG/round-$ROUND"
mkdir -p "$RD"

# Write prompt
cat > "$RD/interrogator-prompt.md" <<EOF
# Round $ROUND input

## PR metadata
$(cat $pr_meta_path)

## PR diff
Read $diff_path.

## Thread state
$(cat $JG/threads.json)
EOF

# Launch
agents -a ${agents_dir}/pr-justification-interrogator.md \
  -m claude-opus -p "$repo_root" \
  -f "$RD/interrogator-prompt.md" > "$RD/interrogator-result.md" 2>&1
```

The interrogator may:
- Open new threads (round 1: always opens from scratch)
- Press existing open threads with sharper demands informed by prior evidence
- Leave a thread silent (but only the adjudicator actually culls)

After the interrogator runs, merge its output into `threads.json`:
- New threads → appended with `status: open`, `opened_round: $ROUND`
- Pressed threads → updated `demand` field

#### 1b. Researcher (`gpt-high`)

```bash
cat > "$RD/researcher-prompt.md" <<EOF
# Round $ROUND — research open threads

## Project context
- Main repo: $repo_root
- Planning / initiatives: $planning_root
- Dependent PRs on current PR #$pr_number: check \`gh pr list\` and linked issues

## Open threads
$(cat $JG/threads.json | jq '.threads[] | select(.status=="open")')

## Task
For each open thread, search for evidence. Present data. Do not defend
the PR. If no evidence is found after a genuine search, state "no evidence
found" — that is a valid result.
EOF

agents -a ${agents_dir}/pr-justification-researcher.md \
  -m gpt-high -p "$repo_root" \
  -f "$RD/researcher-prompt.md" > "$RD/researcher-result.md" 2>&1
```

After the researcher runs, append its per-thread evidence into each thread's
`history[$ROUND].researcher_evidence` in `threads.json`.

#### 1c. Value assessor (`claude-opus`, with optional `gpt-high` sub-agents)

```bash
cat > "$RD/value-assessor-prompt.md" <<EOF
# Round $ROUND — assess value of each open thread

## Open threads with evidence
$(cat $JG/threads.json | jq '.threads[] | select(.status=="open")')

## Your job
For each thread, estimate the value the underlying change buys relative
to the risk of keeping it in this PR. You may dispatch a gpt-high research
sub-agent for a specific factual question. You do not explore the codebase
yourself.
EOF

agents -a ${agents_dir}/pr-justification-value-assessor.md \
  -m claude-opus -p "$repo_root" \
  -f "$RD/value-assessor-prompt.md" > "$RD/value-assessor-result.md" 2>&1
```

Merge per-thread value into `history[$ROUND].value` in `threads.json`.

#### 1d. Adjudicator (`claude-opus`)

```bash
cat > "$RD/adjudicator-prompt.md" <<EOF
# Round $ROUND — adjudicate

## Thread state (full history)
$(cat $JG/threads.json)

## Hard cap
Round $ROUND of 5. If this is round 5, you must cull every remaining thread
with a final verdict based on current evidence.

## Your job
For each open thread, decide:
- CULL with a final verdict (drop | backlog | keep), OR
- CONTINUE (the next round will likely change the outcome)

Cull any thread where further rounds will not change the outcome.
EOF

agents -a ${agents_dir}/pr-justification-adjudicator.md \
  -m claude-opus -p "$repo_root" \
  -f "$RD/adjudicator-prompt.md" > "$RD/adjudicator-result.md" 2>&1
```

Apply adjudicator decisions to `threads.json`:
- `CULL` → `status: culled`, set `verdict`, append `adjudicator_decision: cull-<verdict>` to history
- `CONTINUE` → `status: open` remains, append `adjudicator_decision: continue` to history

#### 1e. Loop condition

```bash
OPEN_COUNT=$(jq '[.threads[] | select(.status=="open")] | length' "$JG/threads.json")
if [ "$OPEN_COUNT" -eq 0 ] || [ "$ROUND" -ge 5 ]; then
  # done
  break
else
  # next round
  continue
fi
```

### Phase 2: Final verdict

When all threads are culled (or the cap is hit), write
`$JG/final-verdict.md`:

```markdown
# Justification Gauntlet — Final Verdict

**PR:** #<pr_number>
**Rounds:** <N>
**Cap hit:** <yes|no>

## Per-thread verdicts

| Thread | Title | Verdict | Rounds open | Why |
|--------|-------|---------|-------------|-----|
| T1 | ... | drop | 1 | ... |
| T2 | ... | keep | 2 | ... |
| T3 | ... | backlog | 3 | ... |

## Actions for the PR author

### Drop
- <thread> — <what hunks to revert>

### Backlog
- <thread> — <suggested backlog ticket summary>

### Keep
- <thread> — <note for the record>
```

The caller (`pr-review-operator.md`) folds this verdict into the PR review
comment body under "Justification Gauntlet" (replacing the old "Missing
Justifications" section).

## Output Format

Return one of:
- `JUSTIFICATION_CONVERGED` — final verdict at `$JG/final-verdict.md`
- `JUSTIFICATION_CAPPED` — round cap hit; final verdict written with
  adjudicator's best-effort calls, noted as capped
- `BLOCKED` — inputs missing or sub-agent failed; error detail in stdout

## Non-goals

- This workflow does not post to GitHub. The caller does.
- This workflow does not re-run the multi-concern check. That is still
  Phase 4a of `pr-review-operator.md`.
- This workflow does not edit the PR or open new PRs. Verdicts are advice
  for the PR author.
