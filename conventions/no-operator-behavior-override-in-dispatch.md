# No Operator Behavior Override In Dispatch

Dispatch prompts to operators are transport for task context, not a second operator file.

## Rule

A dispatch prompt may provide:

- inputs such as paths, refs, branch names, issue keys, model/flavor facts, and credentials context;
- the task variant or stage the target operator already supports;
- boundary anti-scope, such as paths or repos not to touch;
- stop conditions and escalation outputs such as `BLOCKED:<reason>` or `NEEDS_INPUT:<artifact>`;
- evidence paths the operator must read before acting.

A dispatch prompt must not prescribe the target operator's mechanics, verdict handling, phase shape, conflict-resolution strategy, merge strategy, side-selection rule, file-level edit, or step ordering. The target operator file and any workflow it cites are the procedural authority.

This is a content rule. It does not change the `agents` CLI invocation shape and does not remove a caller's ability to pass inputs, task variant, boundary anti-scope, stop conditions, or evidence paths.

## Examples

| Allowed dispatch content | Forbidden dispatch override |
|---|---|
| `task=rebase`, `branch=feature/acr-195`, `target=origin/main`, `bundle=/tmp/verified-rebase/acr-195/` for `jj-operator`. | `Conflict investigation is in scope, but only investigate enough to RECORD the conflict shape; do not resolve in this batch.` |
| `Read /tmp/bundle/summary.md and return the verified-rebase verdict plus bundle path.` | `DIRTY-UNPROVENANCED -> do NOT push; record verdict + bundle path, continue to next branch.` when that replaces the operator/workflow's verdict procedure. |
| `Anti-scope: do not edit files outside agents/ and conventions/ for this WU.` | `Skip the divergent-revision cleanup step because this is just a report batch.` |
| `Stop with NEEDS_INPUT if the target branch is missing or the requested task variant is not supported by jj-operator.` | `Use union for additions in every conflict.` |
| `Evidence: read saved manager feedback at <path> as context for why the operator may need an update ticket.` | `Per saved manager feedback, delegate conflict investigation to jj-operator, but do not resolve.` when the saved feedback is used as quasi-policy. |
| `For implementation-pipeline-orchestrator, run Phase 2.5 with repo_root, worktree_path, scratch_dir, planning_dir, ticket_system, and issue key.` | `Do Phase 2.5 without the duplicates inventory because this ticket is small.` |
| `For roadmap-orchestrator, research Discord application bots and write findings to market-data/research-applications.md.` | `Use only Firecrawl search, do not scrape pages, and ignore the roadmap research procedure's source requirements.` |
| `For roadmap-orchestrator, pass risk report paths into the proposer revision prompt as evidence.` | `When a dependency risk is MEDIUM, treat it as LOW this time and continue without the full risk gate.` |
| `Manager flavor is manager-hackerman; preserve its risk posture in any NEEDS_INPUT answer.` | `Because hackerman permits minimal conflict resolution, take the dev side for cosmetic conflicts.` |
| `For a one-off variation, write a NEEDS_INPUT question artifact naming the requested procedural change and why it cannot be inferred from inputs.` | `As a special case, remove CLOUD-101's duplicate addition while resolving this branch.` |

## Corrective Path

If the target operator's documented procedure is wrong, stale, or missing a supported variant, do not work around it inline in the dispatch prompt.

1. File a ticket against the owning operator, workflow, or convention.
2. Dispatch `implementation-pipeline-orchestrator` for that ticket so the operator file changes through the normal review path.
3. Re-dispatch the original work only after the operator/convention change exists, or after the user explicitly accepts the residual risk through a recorded `NEEDS_INPUT` disposition.

If a genuine one-off variation is needed and it changes procedure, verdict handling, phase shape, or value/scope/trade-off, surface it as `NEEDS_INPUT:<absolute_question_artifact_path>`. Do not encode the variation as mechanics inside a child prompt.

## Operator Precedence

`agents/operator-file-format.md` defines the global precedence rule: the operator file's documented procedure is authoritative; caller prompt content adds inputs, scope, and stop conditions but does not override mechanics. When a caller prompt prescribes mechanics, the operator treats that prescription as a `NEEDS_INPUT`-shape signal and surfaces it back rather than complying.

## Eval Coverage

`evals/dispatch-prompt-operator-behavior-override/eval.md` defines the WRITE-state eval specification for detecting this behavior from dispatch prompts, agent logs, trace JSON, audit bundles, and process-tree audits. The eval is advisory behavior-spec coverage, not runtime rejection and not a pytest revival.
