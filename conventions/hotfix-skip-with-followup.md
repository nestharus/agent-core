# Hotfix Skip With Follow-up

This convention defines the canonical evidence artifact for a hotfix path that skips or defers required gates without treating urgency as an implicit waiver. It owns the seven-field `hotfix-skip-with-followup` schema, the blocking semantics for missing or unresolved evidence, and the post-push / pre-merge satisfaction rule for gates that must still run before merge.

## Declared roles

`parser`, `validator`, `mapper`, `formatter`.

This file-local declaration overrides the documented path default per `~/ai/conventions/code-quality.md` § `Declared roles`. The role set covers parsing the canonical skip row, validating required evidence fields, mapping prototype-era names and inherited proof into the canonical schema, and formatting auditor-readable file-first evidence.

## Use When

Use this convention when a hotfix path skips or defers one or more required gates and the workflow needs a controlled, evidence-bearing record of the skipped gates, accepted risk, already-run evidence, owner, follow-up vehicle, due window, and any post-push / pre-merge gate requirement.

Use it for file-first planning artifacts and for durable manifest rows that embed every required field directly.

## Do Not Use When

Do not use this convention to convert a non-LOW gate verdict into a LOW verdict, to approve an undocumented skip, to replace a required human answer, to justify stale evidence, or to make a Linear/Jira comment the load-bearing evidence.

Do not use it for prototype-pending test markers, bootstrap exceptions, decomposition follow-up tickets, whole-phase skip decisions, RCA wiring, apply-gate-set operator behavior, or currentness invalidation algorithms owned by other WUs.

## Required fields

All seven fields below are required. Missing, empty, placeholder, stale, unreadable, untraceable, or unresolved required values are blocking according to the field-specific rule.

| Field | Type | Semantics | Blocking rule |
|---|---|---|---|
| `skipped_gates` | non-empty list of gate names | Names every gate skipped or deferred by the hotfix path. Values should match the gate names used by the caller's manifest or expected-process surface. | Missing, empty, unresolved gate names, or gate names that cannot be matched to skipped or expected gates block satisfaction. |
| `accepted_risk` | non-empty string | States the risk accepted during the hotfix window. This does not rewrite a non-LOW verdict as LOW. | Missing, empty, placeholder, unresolved, or internally conflicting rationale blocks satisfaction. |
| `owner` | non-empty string naming a human or team | Names the human or team accountable for the skip and follow-up obligation. | Missing, empty, generic, or unresolved owner blocks satisfaction. |
| `evidence_already_run` | non-empty list of artifact paths or stable evidence refs | Points to file-backed artifacts showing checks or gates that did run before the skip. | Missing, empty, unreadable, stale, or untraceable evidence blocks satisfaction. Backend comments alone do not satisfy this field. |
| `follow_up_issue_or_pr` | non-empty Linear/Jira key, issue URL, or PR URL | Names the closure vehicle for the skipped or deferred gate obligation. This is the canonical replacement for prototype-era `followup_ticket` and `followup_pr`. | Missing, empty, unresolved, closed-without-evidence, or missing referenced issue/PR blocks satisfaction. |
| `due_date_or_release_window` | non-empty ISO date, release tag, release train, or bounded release window | Makes the follow-up obligation time-bound. This is the canonical replacement for prototype-era `due_date`. | Missing, empty, unbounded, stale, or unresolved timing blocks satisfaction. |
| `post_push_pre_merge_required` | boolean | When `true`, the skipped gate must run after the hotfix push and before merge. When `false`, the skip may proceed with a valid open follow-up obligation if every other required field is satisfied. | Missing or non-boolean values block satisfaction. When `true`, absence of post-push / pre-merge gate evidence blocks satisfaction even when all other fields are populated. |

Consumer rows may carry enclosing fields such as `convention_ref`, `approval_ref`, `satisfaction_status`, `row_kind`, or `skip_metadata`; those fields are not part of this convention's required seven-field schema unless a future convention revision explicitly promotes them.

## Post-push / pre-merge gating sub-rule

When `post_push_pre_merge_required=true`, the skip row is only provisionally complete until post-push / pre-merge evidence exists for the skipped gate. The satisfying evidence must name or trace to the skipped gate and the `follow_up_issue_or_pr` closure vehicle.

A row with `post_push_pre_merge_required=true` remains blocking if the post-push gate evidence is absent, untraceable, stale, or disconnected from the skipped gate. This preserves the inherited `APPLY-GATE-SET-004` scenario in `evals/acr-277-apply-gate-set-survives/eval.md` lines 269-303 on `prototype-acr-277-clarify`, including the post-push evidence checks described at lines 301-304 and the non-fire cases at lines 306-311.

## Allowed skip vs. workflow violation

A hotfix skip is allowed only when a canonical file-first artifact, or a durable manifest row embedding every required field, satisfies the full seven-field schema and any `post_push_pre_merge_required=true` evidence requirement.

Hotfix urgency is not an implicit gate waiver. If a required gate is absent and no valid `hotfix-skip-with-followup` artifact or manifest row covers it, the omission remains a workflow violation under `~/ai/conventions/workflow-execution-violations.md` § `Procedure-step violation`.

A malformed, incomplete, stale, unresolved, or comment-only skip record is not a partial pass state. It blocks the same as the omitted gate it attempted to cover.

## Canonical artifact location

The recommended canonical file path for a WU-specific hotfix skip artifact is:

```text
${planning_dir}/risk/${wu_lower}-hotfix-skip-with-followup.md
```

The file-first artifact is canonical. Linear/Jira comments may mirror or link the artifact, but comments are not load-bearing evidence. A manifest-row reproduction is also allowed when the apply-gate-set caller embeds every required field directly in a durable manifest row under the relevant planning evidence surface.

## Field-name canonicalization

| Prototype-era name | Canonical name | Rule |
|---|---|---|
| `followup_ticket` | `follow_up_issue_or_pr` | Normalize ticket keys and issue URLs into the single canonical closure-vehicle field. |
| `followup_pr` | `follow_up_issue_or_pr` | Normalize PR URLs into the same canonical closure-vehicle field. |
| `due_date` | `due_date_or_release_window` | Normalize fixed dates and bounded release timing into the canonical time-bound field. |

ACR-293 does not edit ACR-291. ACR-291 must update any placeholder, manifest-row wording, or generated documentation that still carries prototype-era names so it consumes `follow_up_issue_or_pr` and `due_date_or_release_window` from this convention.

## Cross-references (CONTRAST)

- `~/ai/conventions/workflow-execution-violations.md` § `Procedure-step violation` and § `Named anti-pattern: Non-LOW gate residual acceptance`: this convention supplies a valid-skip evidence schema for an omitted hotfix gate; it is not residual acceptance and never rewrites a non-LOW gate verdict as LOW.
- `~/ai/conventions/code-quality.md` § `Bootstrap exception`: hotfix skip evidence is not the bootstrap exception. The bootstrap exception is the narrow code-quality metric carve-out with its own Phase 3, DECISIONS, and Phase 4 manifest requirements.
- `~/ai/conventions/decomposition-strategies.md` § `Follow-up ticket`: `follow_up_issue_or_pr` is the closure vehicle for a time-bound skipped-gate obligation, not a decomposition follow-up ticket and not a pass-state for same-domain debt or artifact repair.
- `~/ai/conventions/agent-questions-and-session-graph.md` § `Question Emission Rule`: this convention is not a `NEEDS_INPUT` path. If approval, owner, accepted risk, due window, or another human-owned value is unresolved, the workflow routes to the question protocol instead of fabricating skip evidence.
- `~/ai/conventions/prototype-pending-tests.md` § `Boundary vs. Other Marker Conventions`: hotfix skip evidence is distinct from `prototype-pending:` markers. It does not make generic skips, fixmes, xfails, or pending tests count as passing production behavior.
- `~/ai/conventions/audit-history.md` § `Decision Register`: audit history may record decisions that consume hotfix skip evidence, but the skip schema lives here and is not redefined by audit-history rows.

## Inherited prototype evidence supersession

This convention is the strictly stronger supersession for inherited scenario `APPLY-GATE-SET-004` in `evals/acr-277-apply-gate-set-survives/eval.md` lines 269-303 on prototype branch `prototype-acr-277-clarify`.

Per `~/ai/conventions/prototype-pending-tests.md` § `Carry-forward to implementation` and § `Supersession-entry schema`, the convention preserves and strengthens the inherited scenario by defining the canonical seven-field schema, the missing/empty/unresolved blocking semantics, and the `post_push_pre_merge_required=true` post-push / pre-merge evidence rule as normative authority. ACR-291 and ACR-292 own downstream runtime and eval-spec proof; ACR-293 does not edit the inherited eval-spec.

## Anti-scope

This convention does not define `apply-gate-set` operator behavior; ACR-291 owns that consumer implementation.

This convention does not define RCA wiring, implementation-pipeline wiring, or eval-spec rollout; ACR-287, ACR-288, and ACR-292 own those surfaces.

This convention does not define stale-row currentness invalidation rules beyond requiring evidence to be non-stale and traceable; ACR-294 owns any fuller currentness algorithm.

This convention does not cover the broader generic-skip taxonomy, does not change `workflow-execution-violations.md`, does not author tests or verifier shims, and does not remove or edit prototype-pending markers.
