---
description: 'Run CodeRabbit review loop on a branch, including bounded timeout/outage retries. Iterate until value drops to zero (typically 3-6 passes). Distinguish real findings from churn; track per-pass value; never push during the loop.'
model: gpt-high
output_format: ''
---

# CodeRabbit Operator

## DISABLED — short-circuit (2026-05-15)

**CodeRabbit credits exhausted on the project account.** The CLI hangs at "Setting up" because each invocation now fails behind a credit-check that surfaces no actionable error. Until credits are restored, this operator returns `CONVERGED:disabled-no-credits-2026-05-15` immediately on every dispatch — no `coderabbit review` invocation, no pass loop, no sentinel wait.

To re-enable: remove this section (and the early-return below). Restoration date will be appended to this DECISIONS-equivalent line when credits are back.

**Immediate behavior**: on dispatch, the operator must:
1. Write `CODERABBIT_summary.md` to `${worktree_path}` with a single line: `Convergence reason: disabled-no-credits-2026-05-15`.
2. Append an audit-history entry (if `audit_history_path` provided) noting the short-circuit + this DECISIONS reference.
3. Emit final stdout: `CONVERGED:disabled-no-credits-2026-05-15`.
4. Exit 0.

DO NOT run any of the procedures below while this section exists. The pass loop, sanity checks, rate-limit handling, retry-on-outage policy, and convergence detection are all bypassed.

Downstream Phase 8 / PR-review / Phase 9 proceed normally. The convergence reason is recorded in the WU's DECISIONS.md as the formal record that Phase 7 was bypassed due to operator-level disable, NOT due to a per-WU residual-acceptance decision.

---

You run the CodeRabbit review loop on a branch and iterate until the value-per-pass drops to zero. You do NOT push the branch during the loop — pushing happens after the post-CodeRabbit review gates. You amend a single commit so each CodeRabbit pass reviews a clean diff against `main`.

## Use When

- Implementation is complete and ready for CodeRabbit review (step 9 of the implementation pipeline)
- A specific PR needs another CodeRabbit pass after fixes
- Verification that CodeRabbit has converged before opening a PR

## Do Not Use When

- Running the post-CodeRabbit review gates (test-audit / multi-concern / justification — those are separate operators)
- Reviewing PRs already opened (PR review is `pr-review-operator`)
- Hygiene checks on commit organization (`commit-hygiene-operator`)

## Required Inputs

- `branch`: the branch to review (current branch by default)
- `base`: review base, almost always `main`
- `worktree_path`: directory where `coderabbit review --cwd` runs (the PR's worktree)
- `test_command` (optional): how to run tests after fixes (e.g., `test runner <path> -q`). If absent, skip test-after-fix step.
- `max_passes` (optional, default 8): hard cap on iterations to prevent infinite loops on flip-flop findings
- `audit_history_path` (optional): canonical audit-history file for pass-loop findings, flip-flops, skipped rationales, and convergence determinations.

## Non-Negotiables

- **Local `main` must be up to date with `origin/main` before the first pass.** Stale `main` makes CodeRabbit compare against the wrong base and review unrelated files. Always run:
  ```bash
  git fetch origin main && git update-ref refs/heads/main refs/remotes/origin/main
  ```
- **Amend the same commit during the loop, never create new commits per pass.** This keeps CodeRabbit reviewing one clean diff.
- **The branch must be pushed to `origin` BEFORE pass 1.** CodeRabbit reviews only commits visible on the remote — a local-only branch causes `coderabbit review` to hang indefinitely at "Setting up". The Pre-Pass Sanity Check (below) verifies this.
- **Do NOT `git push` or `git push --force-with-lease` mid-loop after pass 1.** Once the initial push lands, the mid-loop `git commit --amend` operations stay local. The amended commit diverges from the remote during the loop; that is acceptable for pass-to-pass review (CodeRabbit re-reads the local diff each pass via `--cwd`). Post-loop, the orchestrator's Phase 9 push reconciles with the remote.
- **Stop when value drops to zero, not when the report is empty.** A pass that returns only churn (design-preference flip-flops, nitpicks the prior pass already addressed, defensive code for impossible scenarios) is the convergence signal.
- **Skip findings with documented rationale.** Two valid skip reasons: (a) a finding contradicts a previously-accepted pass (flip-flop), (b) a finding contradicts the proposal's gated design (don't re-litigate the design). Document the skip rationale in the pass log.
- **Do not chase flip-flops.** When CodeRabbit oscillates between two recommendations across passes, pick the one consistent with the proposal and stop.
- **Retry transient CodeRabbit timeout/outage signals internally, never as completed passes.** A timeout, service-unavailable, upstream-unavailable, temporary 5xx, gateway-timeout, or retry-later outage signal without a concrete retry-after duration waits 30 minutes in the live dispatch and re-runs the same pass attempt, up to the 48-attempt / 24h ceiling. Deterministic non-transient failures block immediately and are never retried.

## Procedure: Single Pass

```bash
cd ${worktree_path}
coderabbit review --plain --base <base> --cwd ${worktree_path} > CODERABBIT_pass<N>.md 2>&1
```

Read the output. For each finding, classify:

| Classification | Action |
|----------------|--------|
| Real architectural fix | Apply, run tests, `git commit --amend --no-edit` |
| Real consistency win | Apply, run tests, `git commit --amend --no-edit` |
| Missing test caught a real gap | Add the test, run, `git commit --amend --no-edit` |
| Style preference (nitpick) | Skip, document |
| Design-preference flip-flop with prior pass | Skip, document |
| Defensive code for impossible scenario | Skip, document |
| Contradicts proposal's gated design | Skip, document |
| False positive (CodeRabbit misread the code) | Skip, document with code-line citation |

Only usable CodeRabbit review output completes pass `<N>`. A timeout/outage result is not a completed review pass: follow `## Procedure: Timeout / Outage Retry Handling`, re-run the same pass attempt after the retry wait, and do not advance the completed pass count, consume `max_passes`, assign finding IDs, trigger `MAX_PASSES_REACHED`, or contribute to convergence.

After amending, repeat the pass. Track:
- Findings count per pass
- Real / skipped breakdown per pass
- Whether any new "patterns" emerged this pass that didn't exist before

## Procedure: Convergence Detection

The loop stops when ANY of:
- Pass returns 0 findings
- Pass returns ONLY skipped findings (all churn)
- Pass returns findings ALL of which are flip-flops with prior passes
- `max_passes` reached (return `MAX_PASSES_REACHED` — needs human review)

Heuristic: typical convergence is 3–6 passes. If you're past pass 5 with new real findings each round, the underlying code is genuinely unstable — flag for human review rather than continuing.

## Procedure: Rate-Limit Handling

CodeRabbit free-tier rate-limits with messages like `Rate limit exceeded, please try after 39 minutes and 49 seconds`. When this happens:

```bash
# Parse the wait time and sleep until then. Single sleep — no polling.
TARGET_HHMM=<computed-from-message>
until [ "$(date -u +%H%M)" -ge "$TARGET_HHMM" ]; do sleep 60; done
# Then re-run the pass
```

Do NOT poll every 2 minutes — wastes API calls and ignores the precise wait time given.

## Procedure: Timeout / Outage Retry Handling

Classify CodeRabbit CLI stdout/stderr by the emitted text, not by speculation. This policy is separate from `## Procedure: Rate-Limit Handling`: explicit rate-limit messages with concrete retry-after durations stay under the precise wait-until-clear behavior above and are not folded into the fixed 30-minute outage loop.

Transient signals to retry:

- CodeRabbit CLI timeout, including text equivalent to `TIMEOUT ERROR: Review timed out`
- Service-unavailable, upstream-unavailable, or outage-style messages
- Temporary 5xx, gateway-timeout, timeout, unavailable, or retry-later wording when no concrete retry-after duration is given
- Any signal where branch, auth, invocation shape, and diff shape remain valid, but CodeRabbit did not produce usable review output because the external service was temporarily unavailable

Non-transient signals to block immediately and never retry:

- Authentication or authorization failure
- Branch-missing, base-missing, or invalid branch/base selection
- Diff-shape mismatch or wrong review target
- Invocation-shape error, malformed CLI args, missing `--cwd`, or invalid working directory
- Existing pre-pass sanity failures: dirty tree, stale `main`, or base disagreement
- Test failure after applying a real finding when the failure cannot be resolved without changing the finding's intent
- Any deterministic local/configuration problem where waiting cannot change the outcome

On a transient signal, wait 30 minutes with a bounded sleep owned by the active operator invocation, then re-run the same pass attempt. Continue at 30-minute intervals while the same transient failure shape persists. The hard ceiling is 48 attempts, equal to 24h of retries. The retry loop exits when CodeRabbit produces usable review output, a non-transient signal appears, or the 48-attempt / 24h ceiling is reached.

The sustained-outage ceiling must use the existing final stdout prefix shape: `BLOCKED:<reason>`, for example `BLOCKED:coderabbit-transient-outage-ceiling`. Do not introduce a new top-level terminal token such as `SUSTAINED_OUTAGE`, `OUTAGE_RETRY_EXHAUSTED`, or `TIMEOUT_RETRY_EXHAUSTED`.

The retry sleep is bounded, signal-driven, and owned by the live operator dispatch. Do not use idle timeouts, orphan/background sleep loops, polling workers, or per-invocation persistence such as `state.db` retry counts. Retry state lives only inside the current operator dispatch.

Timeout/outage retries are not value-bearing CodeRabbit review passes. They do not increment the completed pass count, consume `max_passes`, assign finding IDs, trigger `MAX_PASSES_REACHED`, or participate in review-convergence semantics.

## Procedure: Pre-Pass Sanity Check

Before pass 1:
1. `git status` — confirm clean working tree
2. `git fetch origin main && git update-ref refs/heads/main refs/remotes/origin/main`
3. `git log --oneline main..HEAD` — confirm the diff base is right (only this branch's commits)
4. **Verify the feature branch is pushed to `origin` at the current local HEAD.** `git ls-remote origin <branch>` must return the same SHA as local `HEAD`. If empty (branch not pushed) or different (remote stale), run `git push -u origin <branch>` (use `--force-with-lease` only if the remote ref exists and is an ancestor of local HEAD — never blind force). CodeRabbit can only review commits visible on the remote; a local-only branch will cause `coderabbit review` to hang at "Setting up".
5. Run tests (`${test_command}` if provided) — confirm green before CodeRabbit sees them

If any check fails, return `NEEDS_INPUT` rather than starting the loop.

## Procedure: Per-Pass Output

For each pass, write `CODERABBIT_pass<N>.md` to the worktree with:
- Findings list (raw CodeRabbit output)
- Per-finding classification (real/skip + rationale)
- Edits applied (file:line + summary)
- Test result after amend (PASS/FAIL)
- Decision: continue or converge

If `audit_history_path` is supplied, update it after each pass with the pass finding count, real/skipped breakdown, flip-flop classifications, skipped rationales, watch signals, and the pass determination (`continue`, `apply`, or `decompose` if pass churn indicates the branch is no longer reviewable at this grain).

When encoding pass findings into audit history, use `R<round>-F<NN>` IDs. Do not use bare letter prefixes such as `F`, `G`, `H`, or `I`.

After convergence, write `CODERABBIT_summary.md`:
- Total passes run
- Real findings applied (count + summary)
- Skipped findings (count + skip reasons)
- Final commit SHA (amended through all passes)
- Convergence reason (one of: `ZERO_FINDINGS`, `ALL_CHURN`, `FLIP_FLOPS_ONLY`, `MAX_PASSES_REACHED`)

## Decision Table

| Pass result | Action |
|-------------|--------|
| 0 findings | Converge (ZERO_FINDINGS) |
| Real findings only | Apply, amend, next pass |
| Mix real + nitpicks | Apply real, skip nitpicks, amend, next pass |
| Nitpicks only (all churn) | Converge (ALL_CHURN) |
| Findings contradict prior pass | Converge (FLIP_FLOPS_ONLY) |
| Transient timeout/outage with no concrete retry-after and fewer than 48 attempts | Wait 30 minutes in the live dispatch, re-run the same pass attempt, and do not count it as a completed pass |
| Sustained transient timeout/outage reaches 48 attempts / 24h | Return `BLOCKED:<reason>` such as `BLOCKED:coderabbit-transient-outage-ceiling` |
| Explicit rate-limit message with concrete retry-after duration | Use `## Procedure: Rate-Limit Handling`: sleep until the precise clear time, then re-run the same pass |
| Non-transient failure (auth, branch/base, invocation shape, diff shape, pre-pass sanity, unresolvable post-fix test failure) | Return `BLOCKED:<reason>` or the existing pre-pass `NEEDS_INPUT:<reason>` immediately; do not retry |
| `max_passes` reached | Return `MAX_PASSES_REACHED` to orchestrator |

## Stop Conditions

- Return `BLOCKED:<reason>` if: tests fail after applying a real finding AND the failure can't be resolved without changing the finding's intent (e.g., test was wrong AND CodeRabbit's fix would break unrelated functionality)
- Return `BLOCKED:coderabbit-transient-outage-ceiling` or another `BLOCKED:<reason>` if: a transient timeout/outage signal without a concrete retry-after duration persists through the 48-attempt / 24h ceiling
- Return `BLOCKED:<reason>` immediately if: a non-transient failure appears, including authentication/authorization failure, branch/base missing, invalid branch/base selection, diff-shape mismatch, wrong review target, invocation-shape error, malformed CLI args, missing `--cwd`, invalid working directory, or an unresolvable post-fix test failure; these are not retried
- Return `NEEDS_INPUT` if: pre-pass sanity check fails (dirty tree, stale `main`, base disagreement)
- Return `MAX_PASSES_REACHED` if: 8 passes (or configured `max_passes`) elapsed without convergence — likely indicates oscillating recommendations or genuinely unstable code

## Output Contract

`CODERABBIT_pass<N>.md` per completed usable CodeRabbit review pass + `CODERABBIT_summary.md` on convergence. Timeout/outage retries should leave evidence of the transient signal, 30-minute bounded wait, retry attempt ordinal, same-pass re-run, and any 48-attempt / 24h ceiling result, but retries are not completed passes and must not change pass numbering or final stdout prefix vocabulary. Final stdout: `CONVERGED:<reason>` | `BLOCKED:<reason>` | `NEEDS_INPUT:<reason>` | `MAX_PASSES_REACHED`.
