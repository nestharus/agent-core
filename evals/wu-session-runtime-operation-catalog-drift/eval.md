---
eval_id: wu-session-runtime-operation-catalog-drift
behavior_class: WU-session runtime operation catalog and lifecycle-wiring drift
lifecycle_state: WRITE
owner_wu: ACR-403
parent_handoff: ACR-398
selected_verification_level: particular-integration
artifact: evals/wu-session-runtime-operation-catalog-drift/eval.md
declared_roles:
  - validator
  - mapper
---

# Eval: wu-session-runtime-operation-catalog-drift

## Declared roles

`validator`, `mapper`

The `validator` role owns claim classification, comparison, unwanted-behavior,
non-fire, and evidence-state decisions. The `mapper` role maps semantic source,
trace, report, and handoff evidence into the normalized trace and future finding
contracts. Neither role makes this Markdown specification executable.

## Identity and lifecycle

- `eval_id`: `wu-session-runtime-operation-catalog-drift`
- `owner_wu`: `ACR-403`
- `parent_handoff`: `ACR-398`
- `behavior_class`: generic WU-session runtime operation-catalog membership drift
  and conditional lifecycle-wiring drift
- `artifact`: `evals/wu-session-runtime-operation-catalog-drift/eval.md`
- `selected_verification_level`: `particular-integration`
- `lifecycle_state`: `WRITE`

`WRITE` means that this reviewable behavior specification exists. Runnable
detector code, fixtures, evidence adapters, invocation wiring, and enforcement
are not part of this lifecycle state. The presence or review of this file is not
an eval result and does not establish a finding, a clean result, rollout,
enforcement, runtime behavior, or whether an external or protected-state
mutation occurred during the WU. The exact repository delta introduces no such
mechanism; repository evidence alone cannot prove external non-action.

## Adapter declarations

```yaml
adapter_declarations:
  - component: evals/wu-session-runtime-operation-catalog-drift/eval.md
    role: adapter
    Translates:
      - eval-spec-lifecycle-finding-and-evidence-v1
      - wu-session-runtime-write-v1
      - wu-session-runtime-lifecycle-ownership-v1
      - operation-catalog-claim-comparison-v1
      - acr-398-merged-step6b-inheritance-v1
```

This file translates exactly five stable external contract surfaces into one
operation-catalog-drift behavior contract:

| Contract surface | External owner and translated boundary |
|---|---|
| `eval-spec-lifecycle-finding-and-evidence-v1` | `conventions/evals.md` owns eval placement, lifecycle, semantic evidence roles, the conceptual `trace -> finding \| None` boundary, and the six base finding fields. |
| `wu-session-runtime-write-v1` | `tools/wu-session-migration/wu_session_migration.py:RUNTIME_OPERATIONS` owns declared runtime-operation membership. For this eval, supported execution is the detailed human runtime-operation command admitted by `_parser()` and entered through `main()`, which acquires the global lock, completes pending-journal recovery, validates the closed operation-matched request, and exposes success only after transaction completion. Importable helper modes are separate capabilities and cannot borrow those antecedents. |
| `wu-session-runtime-lifecycle-ownership-v1` | Operation-specific executable validators own transition source-state eligibility and allowed effects. Only the live-storage CLI readback mode that reads and identity-checks `manifest_path` owns post-write live acceptance. The `expected_manifest` mode is Phase 3 projection or historical validation with exact antecedents, never live acceptance by itself. The detailed README owns human command forms; implementation workflow/operator and resumer documents own invocation partition, progression order, caller-owned closure, and the sole-writer relationship. |
| `operation-catalog-claim-comparison-v1` | This accepted ACR-403 contract owns classification, membership and wiring comparison, non-fire semantics, and safe repair direction for one exact target claim identified jointly by `catalog_path` and `catalog_anchor`. Generic document anchors are claim instances, not authorities. |
| `acr-398-merged-step6b-inheritance-v1` | ACR-403 authorization and the ACR-398 prerequisite own the verified-merge-qualified handoff while ACR-398 retains its exact two-file repair and direct final inspection. |

Symbols, methods, operations, sections, fields, evidence families, and handoff
conditions subordinate to those surfaces are not additional adapter contracts.
This adapter does not own or reproduce their source contracts.

## Conceptual boundary

The future conceptual interface is:

`evaluate(normalized_evidence: operation-catalog-drift-trace-v1) -> finding | None`

This signature is specification text only. It selects no implementation
language, source parser, Markdown parser, serialization, fixture format,
resolver, runner mode, report sink, schedule, hookpoint, or caller.

In a future implementation, `finding` represents sufficiently evidenced named
unwanted behavior or a supported evidence-gap report. `None` is reserved for a
sufficiently evidenced non-fire. Runner-level input, availability, validation,
and maintenance failures remain outside a clean `None` outcome.

Each invocation evaluates exactly one target claim identified jointly by the
non-null `catalog_path` and stable semantic `catalog_anchor` at the admitted
repository identity. A `finding` or `None` applies only to that exact claim.
`None` means only that the named unwanted behavior is a sufficiently evidenced
non-fire for that claim; it cannot mean that the repository, a document, or all
current claims are clean. One selected claim or invocation never supplies claim
discovery or repository completeness.

A future repository-level consumer would require a separate, later contract
that makes the caller own identity-bound candidate discovery, an exact claim
inventory, an exclusion reason for every rejected candidate, per-claim fan-out,
equality between admitted inventory and completed per-claim results, and
explicit aggregation. This eval selects, implements, and claims none of those
repository-level mechanisms.

## Positive evidence and required trace fields

`operation-catalog-drift-trace-v1` is a role-normalized evidence bundle for one
exact `evaluated_repository_identity`, one exact target claim identified by
`catalog_path` plus `catalog_anchor`, and, when present, one WU, PR, session, or
selected invocation subtree observed against that identity. It must represent
these semantic records:

| Evidence role | Required semantic fields and decision use |
|---|---|
| Repository identity | One `evaluated_repository_identity` naming the exact repository and full evaluated commit identity selected by the caller. Every repository-derived record below binds to this same value and resolves its content from that commit. |
| Declaration authority | `authority_path`, `authority_symbol`, the common identity, a readable source snapshot, and extracted `canonical_operations`. This is declared membership evidence, not executable-support evidence by itself. |
| Per-member executable support | One deterministic `operation_support` record per canonical declaration, bound to the common identity, with an exact capability, entrypoint, and invocation-mode inventory. Support proves the detailed human CLI command enters through `_parser()` and `main()`, holds the global lock, completes pending-journal recovery, validates the closed operation-matched request, reaches the operation-specific valid projection or handler, and returns only after transaction completion. Any readback evidence records its exact mode and enforcing antecedents. |
| Transition enforcement | Operation-specific executable projection, source-state, eligibility, and effect validators, all bound to the common identity, own transition admission and effects. Readback evidence is mode-bound: live-storage CLI mode owns post-write live acceptance; `expected_manifest` mode is admissible only with its exact Phase 3 antecedents and cannot satisfy live acceptance. |
| Detailed command contract | Detailed README path and semantic anchors, common identity, human command forms, operation semantics, and described lifecycle/readback semantics. This source does not override executable admission or caller ownership. |
| Caller wiring | Implementation workflow/operator and resumer paths and semantic anchors, common identity, invocation partition, progression order, caller-owned closure, `owning_caller`, and `sole_writer`. |
| Exact target claim | Non-null `catalog_path`, stable semantic `catalog_anchor`, common identity, surrounding context, `claim_kind`, `claim_scope`, extracted `catalog_operations`, and any claimed sequence. This pair identifies the sole claim under comparison. |
| Comparison | Deterministically sorted `missing_operations` and `extra_operations`, per-member `operation_support`, and aggregate `wiring_transition` proving exhaustive transition enumeration and comparison inside the exact target claim's resolved domain. |
| Observation provenance | `evidence_paths`; revision, WU, PR, and session locators when available; source, trace, prompt, log, report, audit, and final changed-surface paths when available. |
| Conflict and availability | `evidence_state`, `authority_state`, `authority_conflicts`, `reconciliation_owner`, and `missing_evidence_roles`, with enough role-level detail to distinguish unavailable evidence, identity failure, authority disagreement, and ambiguous scope from a resolved empty collection. |
| Cause-preserving recovery | `failure_cause`, `recovery_disposition`, `recovery_owner`, and `terminal_condition`. Every non-clean evidence, identity, authority, or scope cause remains distinct and bound to the actor and condition that can end its obligation. |
| Downstream handoff | Verified ACR-403 merge identity and the ACR-398 inherited Step 6b intent boundary without broadening ACR-398's two-file repository scope. |

### Common repository identity admission

`evaluated_repository_identity` is one semantic identity for the canonical
repository and one exact full commit selected for evaluation. It is not an
independent timestamp or label on each source. Declaration membership,
per-member executable support, transition enforcement, detailed command,
caller, and target-claim records are admitted only when each source path
resolves at that commit and its observed content identity equals the content at
that path in the same commit. A currentness claim additionally requires the
caller's expected repository identity to equal this selected identity; ambient
working-tree or cached-report state cannot silently redefine it.

Identity failures retain their material cause rather than collapsing into one
missing result. A required path absent at the selected immutable identity uses
`failure_cause: absent-at-identity`; caller expected/selected identity mismatch
uses `caller-currentness-mismatch`; mixed identities use
`mixed-source-identities`; a source without a commit binding uses
`unbound-source-identity`; and a supplied identity that cannot be authenticated
uses `unverifiable-source-identity`. These are named non-clean identity or
evidence findings, never catalog drift, conditional-wiring drift, or `None`.
The attempted common identity and every conflicting observed identity remain in
the finding and `evidence_paths`; if no common identity was supplied, the
required `evaluated_repository_identity` field is `null` rather than invented.

Evidence is resolved by semantic role rather than a fixed source line, brittle
substring, one transient filename, one producer-private schema, or one raw
SQLite location. Normalizable evidence families include repository and runtime
test source snapshots, saved `agents trace --json`, planning artifacts, prompts
and logs, process-tree and workflow-process reports, expected-process manifests,
audit bundles, and final diffs. Invocation evidence can be joined by invocation
UUID, parent invocation ID, root invocation UUID, prompt path, and session-graph
semantics. Raw state database evidence is best effort behind a separately
authorized verified adapter.

The final diff is useful observation evidence for a selected WU, and the final
ACR-403 diff is required scope evidence for this WU. A final diff is not
declaration, executable-support, or transition authority. Common-identity source
snapshots can establish the source relationship without a final diff, but
readability without the identity equality and authority-admission rules cannot.

## Authority order

Disagreement is preserved with source paths and content identities. It is not
settled by prose majority.

1. `tools/wu-session-migration/wu_session_migration.py:RUNTIME_OPERATIONS` owns
   revision-local declared runtime-operation membership. Declaration alone does
   not establish executable support.
2. For each declared member, the supported surface is the detailed human
   `python3 tools/wu-session-migration <operation> --request <path>` command.
   `_parser()` must expose it and `main()` must acquire `_cutover_lock()`, finish
   `recover_incomplete_transaction()`, invoke the operation with the lock-held
   antecedent, close operation/request equality through
   `_validate_runtime_request()`, reach the operation-specific projection or
   handler and `_execute_transaction()`, and expose success only after the
   transaction returns. Every capability, entrypoint, and invocation mode
   observed for that member remains inventoried even when it is outside this
   supported CLI surface.
3. Operation-specific executable projection, source-state, eligibility, and
   effect validators own transition admission and effects. Only
   `validate-pre-pr-readback` entered through `main()` without
   `expected_manifest`, while the top-level lock is held and recovery has
   completed, reads and identity-checks `manifest_path` and can own post-write
   live acceptance. `validate_pre_pr_readback(..., expected_manifest=...)` is
   projection or historical validation admissible only from its exact Phase 3
   request-validation antecedent; it cannot establish live acceptance alone.
4. `tools/wu-session-migration/README.md` owns detailed human command forms and
   their described semantics; it does not override executable admission.
5. `agents/implementation-pipeline-orchestrator.md`,
   `workflows/implementation-pipeline.md`, and
   `agents/wu-session-resumer.md` own invocation partition, progression order,
   caller-owned closure, and their lifecycle partitions while preserving the
   sole Python writer.
6. One exact anchor in `tools/README.md`,
   `conventions/wu-session-lifecycle.md`, or another generic summary is the
   target claim compared with higher authority only when its context explicitly
   asserts or strongly implies applicable completeness. Other anchors are not
   evaluated by the same invocation.
7. Tests, source snapshots, saved traces, reports, audit bundles, and final
   diffs are corroborating or observation evidence. They do not expand
   declared membership or executable support.

Every canonical declaration receives one `operation_support` record. Importable
helper modes, including independent calls with `lock_already_held=True`, cannot
borrow lock ownership or completed recovery from `main()`. They remain outside
this generic CLI-claim comparison unless a named authoritative caller and the
exact acting antecedents prove lock ownership and completed pending-journal
recovery for that invocation. Self-locking helper mode
`lock_already_held=False` is likewise a separately inventoried non-CLI
capability, not evidence that the detailed human CLI entrypoint was exercised.
An omitted reachable mode or an accepted helper mode without its own bound
authority and antecedents is `authority-conflict`, never executable support,
catalog drift, conditional-wiring drift, or `None`. This specification records
the adjacent helper boundary; it does not change or claim to repair runtime
code.

If the declaration and any readable required acting context disagree, or
readable contexts cannot be reconciled, `authority_state` is `conflict` or
`unresolved` and `evidence_state` is `authority-conflict`. An unavailable
required source instead uses the cause-specific evidence state and recovery
contract below. Neither state is catalog drift or `None`. The finding retains
each disagreeing source and assigns reconciliation to the runtime-migration
owner for declaration, executable admission, effects, lock/recovery context,
transaction completion, and readback mode; the detailed-README owner for human
command forms; and the owning caller document for invocation partition,
progression, and caller-owned closure. These owners reconcile their shared
boundary before any generic-claim repair is permitted.

Top-level `authority_state` is one of `aligned`, `conflict`, or `unresolved`.
It is `aligned` only when every per-member support record and every applicable
transition comparison agrees across its required executable, detailed-command,
and caller sources. `authority_conflicts` retains each source, disputed semantic
fact, and observed value; `reconciliation_owner` retains every source owner that
must resolve it.

At the revision inspected for ACR-403, `RUNTIME_OPERATIONS` declares these eight
members, shown as a deterministic point-in-time evidence list:

- `cold-start-disposition-bind`
- `phase0-init`
- `phase0-reresolve`
- `phase3-bind`
- `phase7-upsert`
- `phase9-update`
- `resumer-close`
- `resumer-update`

A future detector must extract declarations from `RUNTIME_OPERATIONS` at the
evaluated revision and resolve a support record for every member before using a
declaration as supported-operation repair guidance. This eight-member
observation is not immutable detector policy. The Python value is a set, so this
display order has no lifecycle meaning.

Known target-claim candidates include the implemented-tool summary in
`tools/README.md`, the `Exact operations are` claim in
`conventions/wu-session-lifecycle.md`, and that convention's `Manifest storage`
sequence. Each candidate requires a separate exact `catalog_path` plus
`catalog_anchor` invocation. This point-in-time candidate list is review context,
not identity-bound claim discovery or a complete inventory. Direct source
comparison is review evidence for the contract; these anchors remain claims
rather than co-equal membership or transition authority.

## Unwanted behaviors

The two behaviors are related but evaluated independently.

### Operation-membership drift

An active generic claim classified as `exact` or `complete-implied` presents the
`wu-session-runtime-write-v1` operation inventory as complete, but its resolved
`catalog_operations` differs from revision-local declared
`canonical_operations`. One or both of `missing_operations` and
`extra_operations` is non-empty. The common repository identity must be
admitted and every canonical declaration must have an aligned, resolved
`operation_support` record before this mismatch can become catalog drift or
drive supported-operation repair guidance. Declaration/acting-context
disagreement is `authority-conflict`, not operation-membership drift.

### Conditional-wiring drift

An active generic lifecycle claim classified as `exact` or `complete-implied`
presents the writer sequence as complete in a resolved claim domain, but the
exhaustive revision-bound transition aggregate omits or contradicts one or more
supported conditional transitions in that domain. Executable validators
establish transition admission, source-state eligibility, and effects; only
mode-bound live-storage readback establishes post-write live acceptance.
Detailed command and caller authorities must agree on human command form,
invocation partition, progression, and caller-owned closure. The known
`phase0-reresolve` recurrence is one member of the enumerated transition domain,
not evidence that the domain contains only one member.

These are documentation-contract drift behaviors. They are not runtime writer
failure, parser failure, request-validation failure, transaction failure,
protected-state corruption, or evidence that a conditional transition is
mandatory for every normal WU.

## Claim taxonomy

The exact target anchor identified by `catalog_path` plus `catalog_anchor` is
classified before any membership or wiring comparison. Context supporting the
classification remains in evidence. Classification never discovers or decides
the status of another anchor.

| `claim_kind` | Meaning | Comparison disposition |
|---|---|---|
| `exact` | The prose explicitly says the inventory or sequence is exact, exhaustive, or complete in its claimed scope. | Compare every applicable membership and wiring obligation in the resolved scope. |
| `complete-implied` | Wording and structure strongly present a complete inventory or sequence in its claimed scope without an explicit completeness token. | Compare while retaining the context that supports the completeness and scope inference. |
| `delegated` | The prose unambiguously delegates exact membership or detailed sequencing to the applicable declaration, executable, detailed-command, and caller authorities and does not restate an exhaustive set. | Non-fire unless surrounding context independently makes a complete claim. |
| `partial-example` | The prose clearly labels members as examples, selected cases, illustrative, or partial. | Non-fire unless surrounding context independently implies completeness. |
| `non-runtime` | The anchor lists top-level migration or support commands rather than members of `RUNTIME_OPERATIONS`. | Exclude those commands from runtime membership differences. |

Ambiguity remains visible in source context, `evidence_state`,
`missing_evidence_roles`, and `confidence`. Operation tokens alone do not make
an unresolved claim `exact`.

### Claim scope and occurrence evidence

Every claim record has `claim_scope`, classified as one of:

- `repository-global`: unqualified completeness across the supported runtime.
- `named-domain`: completeness for an explicitly named lifecycle or caller
  domain.
- `selected-cohort`: completeness explicitly limited to a stated cohort whose
  eligibility predicates are retained.
- `occurrence-only`: an event or session trace that reports what occurred and
  makes no repository-completeness claim.
- `ambiguous`: the evidence cannot determine which domain the completeness
  wording covers.

`repository-global` describes the semantic promise made by this exact target
claim; it does not broaden the evaluator result to other claims. A
repository-global or ambiguously broad complete generic sequence is accountable
for every supported conditional transition in its own claimed domain, whether
or not one sampled WU was eligible or traversed the edge. A selected session's
non-occurrence can establish only occurrence evidence. Eligibility-based
non-fire is permitted when the claim is explicitly `selected-cohort` and that
cohort is ineligible, or when evidence is `occurrence-only` and makes no
repository-completeness claim. `claim_scope: ambiguous` produces
`evidence_state: scope-indeterminate` with
`failure_cause: ambiguous-scope`, never drift and never `None`.

## Membership comparison contract

For a resolved `exact` or `complete-implied` membership claim:

- `canonical_operations` is the unique set extracted from revision-local
  `RUNTIME_OPERATIONS`; it means canonical declarations, not declaration-only
  proof of executable support.
- `catalog_operations` is the unique runtime-operation set semantically
  extracted from the active claim.
- `missing_operations = canonical_operations - catalog_operations`.
- `extra_operations = catalog_operations - canonical_operations`.
- All resolved operation collections are deterministic sorted lists.
- Both difference fields remain present when empty. An empty list means the
  comparison resolved to an empty set.
- An unavailable collection is `null`, not an empty list. Unknown evidence must
  not masquerade as a completed comparison.
- A membership-drift candidate exists only when the claim is applicable and at
  least one resolved difference is non-empty.
- Ordering differences alone are inapplicable because declared membership is
  a set.

Every canonical operation has exactly one deterministic `operation_support`
record containing:

- `operation`
- `capability_inventory`
- `entrypoint_inventory`
- `invocation_mode_inventory`
- `parser_exposure`
- `command_request_equality`
- `projection_or_handler_path`
- `lock_and_recovery_antecedents`
- `closed_request_acceptance`
- `transaction_completion_evidence`
- `readback_mode`
- `readback_enforcing_antecedents`
- `detailed_command_contract`
- `support_state`, one of `supported`, `conflict`, or `unresolved`
- `evidence_paths`

Each inventory is exact for the operation and common repository identity.
`capability_inventory` names the detailed human CLI capability and every
observed importable write or readback capability. `entrypoint_inventory` binds
each capability to its actual parser, `main()`, public helper, or private helper
entry chain. `invocation_mode_inventory` records the exact mode, named acting
caller, support/exclusion disposition, and mode-local lock-ownership and
completed-recovery evidence. At the inspected source this includes the
top-level CLI path, imported `apply_runtime_request()` with
`lock_already_held=False`, the `main()`-owned nested call with
`lock_already_held=True`, and an independent imported call with
`lock_already_held=True`; another observed reachable mode must be added rather
than silently excluded.

A record is `supported` only when the detailed human operation command is
parser-exposed and enters `main()`; `main()`'s own acting context proves the
global lock is held and pending-journal recovery completed before its nested
runtime helper call; exact command/request equality and the closed request
resolve; an operation-specific projection or handler resolves; and transaction
completion returns before the CLI success result. Importable modes remain
outside support unless a named authoritative caller supplies its own enforcing
antecedents as described above. Omitting a reachable mode or admitting an
unbound mode makes the record `conflict`.

For pre-PR readback, `readback_mode` is the deterministic list of applicable
mode records, and each record's `readback_enforcing_antecedents` distinguishes:

- `live-storage-cli`: top-level `validate-pre-pr-readback` enters `main()` under
  the lock after recovery, omits `expected_manifest`, reads `manifest_path`, and
  identity-checks that live manifest plus the other required effects. Only this
  mode can establish post-write live acceptance.
- `phase3-expected-manifest`: the exact Phase 3 request-validation path has
  already bound the live Phase 3 source manifest and historical
  operator/contract identities, requires the canonical authenticated
  `phase0-reresolve` readback after the historical-blob mismatch, and calls
  `validate_pre_pr_readback(..., expected_manifest=manifest)`. This is
  projection/historical validation and cannot populate live acceptance by
  itself.
- `not-applicable`: the operation has no applicable pre-PR readback obligation,
  with the operation-specific reason retained rather than borrowing another
  mode's evidence.

Records are unique and sorted by `operation`. Parser registration, request
closure, detailed Markdown, callers, tests, and other claims cannot vote an
operation into or out of `canonical_operations`; they instead establish
support or expose a named authority/integration conflict.

## Conditional-wiring comparison contract

Wiring is evaluated separately from membership. An operation name in a complete
membership list does not establish its supported lifecycle edge. A
membership-only claim does not acquire sequencing obligations.

The ticket-required `wiring_transition` output remains one field, but it is an
aggregate record rather than one selected transition. Every resolved aggregate
contains:

- `evaluated_repository_identity`
- `catalog_path`
- `catalog_anchor`
- `enumeration_evidence_paths`
- `canonical_transition_ids`
- `applicable_transition_ids`
- `transition_comparisons`
- `omitted_transition_ids`
- `contradicted_transition_ids`
- `enumeration_complete`

Canonical transition enumeration examines every operation-specific executable
validator and every mode-bound readback path for every canonical operation at
the common identity and identifies every supported conditional transition in
the exact target claim's resolved domain. The canonical and applicable
identifiers are unique deterministic sorted lists.
`enumeration_evidence_paths` retains the complete executable discovery boundary
plus the detailed and caller sources joined for human command and ownership
semantics. `enumeration_complete` is true only when this full per-claim domain
was resolved and every applicable canonical transition has one comparison. It
says nothing about another `catalog_path` or `catalog_anchor`.

Every member of `transition_comparisons` contains:

- `transition_id`
- `operation`
- `source_conditions`
- `destination_or_successor`
- `conditional`
- `owning_caller`
- `sole_writer`
- `executable_validator_paths`
- `readback_validator_paths`
- `readback_mode`
- `readback_enforcing_antecedents`
- `readback_authority_disposition`
- `detailed_command_paths`
- `caller_paths`
- `authority_state`, one of `aligned`, `conflict`, or `unresolved`
- `observed_treatment`, one of `included`, `delegated`, `omitted`,
  `contradicted`, or `not-applicable`
- `evidence_paths`

The comparison list is sorted by `transition_id`; omitted and contradicted IDs
are derived from it and sorted deterministically. A readback symbol or path
without its mode and enforcing antecedents is unresolved. The
`phase3-expected-manifest` mode may corroborate its exact historical/projection
antecedent but has `readback_authority_disposition: projection-only` and cannot
satisfy a live-acceptance obligation. Any executable, mode, detailed-command,
or caller disagreement makes the aggregate non-clean with
`authority-conflict`, preserves the disagreement and reconciliation owners, and
prevents generic-claim repair.

For the known recurrence, one aggregate member represents:

- `transition_id`: `phase0-reresolve-pre-phase3-policy-reentry`
- `operation`: `phase0-reresolve`
- `source_conditions`: an eligible existing open pre-PR, pre-Phase-3 session
  with policy identities requiring re-resolution
- `destination_or_successor`: caller-owned closed pre-PR readback, then later
  `phase3-bind` composition
- `conditional`: `true`
- `owning_caller`: the implementation pipeline workflow/operator partition
- `sole_writer`: `tools/wu-session-migration/wu_session_migration.py`
- read-only evidence roles: `phase-0-contract-resolution`,
  `phase-0-ticket-snapshot`, `phase-0-topology-revalidation`,
  `resolved-ticket-contract`, and `resolved-ticket-operator`
- semantic effects: manifest-only change, no active row, preserved cold-start
  disposition and phase history

An applicable complete-sequence claim has conditional-wiring drift when the
complete aggregate has a non-empty `omitted_transition_ids` or
`contradicted_transition_ids`. `included` and unambiguous `delegated` treatment
are aligned. `not-applicable` is used only for an individual comparison outside
the resolved claim scope, including a membership-only claim or explicitly named
lifecycle partition that does not own it. It cannot stand for an unexamined
transition. When required authority or exhaustive enumeration is unavailable,
the aggregate is `null` under the evidence-gap rules rather than inventing
`not-applicable` or an empty transition domain. `None` for this one exact target
claim requires `enumeration_complete: true` and comparison of every applicable
authoritative transition in that claim's resolved domain. It cannot establish
repository-level or all-claims cleanliness.

## Non-fire cases

A future `None` outcome for the exact `catalog_path` plus `catalog_anchor` is
permitted only after common-identity admission, aligned authorities, resolved
claim scope, complete per-member support, and any applicable exhaustive
transition aggregation. The named unwanted behavior is absent from that exact
claim in each of these cases:

- Generic prose explicitly delegates exact membership or detailed sequencing
  to the applicable declaration, executable, detailed-command, and caller
  authorities and does not restate an exhaustive set.
- A list is clearly partial, illustrative, selected, or example-only and no
  surrounding context independently implies completeness.
- The anchor lists non-runtime commands such as `capture-evidence`, `dry-run`,
  `apply`, or `validate-pre-pr-readback`.
- A membership-only claim differs only in ordering because
  `RUNTIME_OPERATIONS` is a set.
- A membership-only claim does not describe a sequence, so conditional edge
  placement is not applicable.
- The exact complete generic claim contains every canonical declaration,
  contains no unsupported extra, every per-member support record has aligned
  capability, entrypoint, invocation-mode, lock/recovery, closed-request,
  transaction-completion, and mode-bound readback evidence, and an exhaustively
  enumerated aggregate includes or unambiguously delegates every applicable
  conditional transition in the claim domain.
- A lifecycle-partitioned caller omits operations it does not own, including the
  resumer omitting pre-PR operations.
- Historical text, fixture text, proposal text, or a negative example identifies
  an omission as unwanted behavior rather than presenting an active supported
  catalog claim.
- A claim explicitly limited to a selected ineligible cohort omits a transition
  that cannot apply to that cohort, or occurrence-only evidence records no event
  without making a repository-completeness claim.

False eligibility in one sampled WU does not excuse an omission from a
repository-global, named-domain, or ambiguously scoped complete generic claim.
Incomplete, identity-conflicted, authority-conflicted, or scope-indeterminate
evidence is not a non-fire case.

No non-fire case and no `None` result says that another anchor, the containing
document, or the repository is clean. Multi-claim or repository conclusions
require the separate caller-owned discovery, inventory, exclusion, fan-out,
completeness-equality, and aggregation contract that is explicitly outside this
eval.

## Evidence-state contract

The common repository identity, declaration authority, exact target claim,
claim scope, and every per-member executable-support role are non-degradable for
a membership determination. Operation-specific executable transition
validators, mode-bound live readback where applicable, exhaustive per-claim
transition enumeration, detailed command forms, and caller
partition/progression/closure are additionally non-degradable for a wiring
determination.

The normalized trace always carries these cause-preserving fields:

- `failure_cause`: a deterministic list of normalized causes.
- `recovery_disposition`: a cause-keyed ordered sequence containing only
  `retry`, `repair`, `reconcile`, `escalate`, or `terminate`, without erasing
  another required step.
- `recovery_owner`: the cause-keyed layer or named source owner authorized for
  each ordered disposition.
- `terminal_condition`: the cause-keyed observable condition that ends the
  current obligation or records it as explicitly terminal and unresolved.

For a resolved behavior finding or non-fire these values are respectively an
empty list and empty cause maps. Every evidence, identity, authority, scope, or
lifecycle gap has at least one non-empty cause and matching entries in all three
maps. Multiple causes remain independently keyed; precedence may prevent
comparison but cannot discard a later cause.

| `evidence_state` | Minimum evidence | Permitted future decision behavior |
|---|---|---|
| `complete` | One common identity is admitted; declaration, per-member support, exact target claim, classification/scope, and every applicable per-claim transition-enumeration/comparison source resolve and agree. | A behavior finding is permitted when unwanted behavior is present. `None` is permitted only for a fully evidenced non-fire for the exact target claim. |
| `degraded` | All identity, authority, support, scope, and enumeration sources needed for the selected decision resolve and agree, but optional trace/report, test, audit, or final-diff observation evidence is unavailable. | A directly established mismatch may produce a reduced-confidence finding with named `missing_evidence_roles`. `None` is permitted only when optional loss does not leave any decision fact unresolved. Missing optional final-diff evidence alone does not erase a common-identity source-established mismatch. |
| `evidence-gap` | A required role has cause `absent-at-identity`, `access-denied`, `transiently-unavailable`, `invalid-or-unparseable-source`, `unsupported-adapter`, or `parse-only-evidence`. | Emit a cause-preserving `LOW` gap finding or cause-preserving runner result. Never assert drift or use `None`, `NO_FINDING`, a PASS-like result, or generic `missing`. |
| `identity-conflict` | Identities have cause `mixed-source-identities`, `unbound-source-identity`, `unverifiable-source-identity`, or `caller-currentness-mismatch`. | Preserve expected and observed identities and the precise cause. Never compare into drift or use `None`; only the assigned caller or identity resolver may reconcile or terminate it. |
| `authority-conflict` | Declaration and acting contexts disagree; a reachable capability or invocation mode is omitted or admitted without its own authority and lock/recovery antecedents; readback mode/antecedents disagree; or detailed-command and caller authorities disagree. | Use `failure_cause: authority-disagreement`, preserve all sides, `authority_conflicts`, and `reconciliation_owner`, and never emit drift, generic-claim repair, or `None` before owner reconciliation. |
| `scope-indeterminate` | The exact target has active completeness wording but its repository, domain, cohort, or occurrence scope cannot be resolved. | Use `failure_cause: ambiguous-scope`, preserve context, and never let sampled eligibility choose scope or emit drift or `None`. |
| `lifecycle-prohibited` | Runnable evaluation is requested while lifecycle remains `WRITE`, or another selected lifecycle forbids the requested execution. | Use `failure_cause: lifecycle-prohibited-execution`; the runner terminates rather than executing or retrying, and only the lifecycle owner may authorize a later state transition. |

The required recovery assignments are:

| `failure_cause` | Authorized recovery and terminal condition |
|---|---|
| `absent-at-identity` | The validator terminates comparison at the immutable identity; the named source owner may repair only in a later repository identity, and the caller may select that new identity. The obligation ends with a successful fresh comparison or an explicit terminal absence finding that does not claim cleanliness. |
| `access-denied` | The resolver does not retry unchanged credentials. The caller or access authority escalates and repairs authorization; the runner may retry only after evidence of changed access. The attempt terminates with authorized resolution or an explicit denied finding. |
| `transiently-unavailable` | The resolver or runner may perform caller-bounded retries. On exhaustion the caller escalates and terminates with the transient cause preserved; success requires the same identity-bound role to resolve. |
| `invalid-or-unparseable-source` | The mapper terminates parsing and the named source owner repairs invalid source semantics; unchanged-input retries are prohibited. The obligation ends after a fresh valid parse or an explicit terminal invalid-source finding. |
| `unsupported-adapter` | The runner terminates the attempt and the adapter owner repairs or upgrades the adapter before retry. A generic-document or runtime owner cannot absorb this defect. |
| `parse-only-evidence` | The validator rejects parse output as executable, identity, lock/recovery, transaction, or live-readback authority. The resolver/caller must obtain the direct identity-bound source and acting antecedents or terminate with an insufficient-evidence finding. |
| `mixed-source-identities` | The validator terminates comparison; the identity resolver reconciles every repository-derived role to one caller-selected commit before retry. The obligation ends with one admitted identity or a terminal mixed-identity finding. |
| `unbound-source-identity` | The mapper terminates admission; the evidence producer repairs the missing commit/content binding and the identity resolver verifies it before retry. The obligation ends with a verified binding or a terminal unbound finding. |
| `unverifiable-source-identity` | The identity resolver terminates admission and escalates authentication or source-integrity failure to the caller; retry requires changed verification evidence. The attempt ends with authenticated identity or a terminal unverifiable finding. |
| `caller-currentness-mismatch` | The validator terminates the stale comparison; the caller reconciles expected versus selected identity and starts a fresh invocation. The mapper cannot silently reselect currentness. |
| `authority-disagreement` | The validator terminates comparison and the named runtime, readback, detailed-command, or caller source owners reconcile their shared contract. Only aligned identity-bound sources permit a fresh comparison. |
| `ambiguous-scope` | The validator terminates comparison; the exact target's document owner repairs the wording or the caller escalates for scope clarification. The obligation ends only with resolved scope or an explicit terminal scope finding. |
| `lifecycle-prohibited-execution` | The runner terminates without executing or retrying. Only the lifecycle owner may authorize later `ROLL_OUT` work; remaining in `WRITE` is the terminal condition for the current execution request. |

Identity admission precedes authority reconciliation, which precedes scope and
catalog/wiring comparison. A bundle with more than one failure retains every
observed conflict even when the first non-clean state prevents later comparison.

While lifecycle remains `WRITE`, unavailable runnable code is not a clean
behavior outcome. A future execution request terminates with
`lifecycle-prohibited-execution` rather than treating specification presence as
`None`. Invalid finding shape, failed result validation, or material adapter
drift is a cause-preserving validation or maintenance result owned by the runner
or adapter layer, not a behavior finding and not a clean result.

## Finding contract

Every future behavior finding or supported evidence-gap finding preserves the
six base fields from `conventions/evals.md` exactly:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Every such finding also contains the twelve ticket-required operation/catalog
extension fields exactly:

- `authority_path`
- `authority_symbol`
- `canonical_operations`
- `catalog_path`
- `catalog_anchor`
- `claim_kind`
- `catalog_operations`
- `missing_operations`
- `extra_operations`
- `wiring_transition`
- `evidence_state`
- `missing_evidence_roles`

It also contains these risk-review extension fields:

- `evaluated_repository_identity`
- `operation_support`
- `claim_scope`
- `authority_state`
- `authority_conflicts`
- `reconciliation_owner`
- `failure_cause`
- `recovery_disposition`
- `recovery_owner`
- `terminal_condition`

For a resolved drift finding, `eval_id` is
`wu-session-runtime-operation-catalog-drift`, `authority_symbol` is
`RUNTIME_OPERATIONS`, `evaluated_repository_identity` is the admitted common
identity, operation collections and `operation_support` are deterministic, and
the aggregate wiring treatment is complete and explicit. `evidence_paths`
retains actual source and corroboration locators. The exact `catalog_path` and
`catalog_anchor` remain the sole target identity. A resolved behavior finding
uses an empty `failure_cause` list and empty cause maps for the three recovery
fields.

For an evidence, identity, authority, scope, or lifecycle gap finding, all
fields remain present. Unavailable scalar or record values are `null`;
unavailable operation collections are `null`;
available collections remain deterministic lists; and
`missing_evidence_roles` names every source of indeterminacy. Empty lists always
mean resolved empty sets, never unknown evidence. The caller-supplied
`catalog_path` and `catalog_anchor` remain non-null even when their selected
source is absent or inaccessible because they identify the exact attempted
claim. The selected
`evaluated_repository_identity` remains present when known, including in
identity, authority, or scope findings; it is `null` only when no common identity
was supplied. Conflicting observed identities and authorities remain in
`authority_conflicts` and `evidence_paths`. `reconciliation_owner` is a
deterministic list when multiple source owners must act. `failure_cause` is
non-empty, and `recovery_disposition`, `recovery_owner`, and
`terminal_condition` contain a matching entry for every cause. No generic
`missing` cause or unowned retry is valid.

Severity describes finding impact, not the ACR-403 risk-profile verdict:

- `MEDIUM`: established generic operation-catalog or conditional-wiring drift.
- `HIGH`: established drift that also instructs an unsafe alternate writer,
  unsupported runtime behavior, or invalid lifecycle action.
- `LOW`: a distinct identity, authority, scope, evidence-resolution,
  instrumentation, or adapter gap.

`confidence` reflects evidence completeness, directness, and claim-classification
certainty. It must not conceal degraded evidence or a cause-specific gap.

## Suggested action

For established operation-catalog or conditional-wiring drift,
`suggested_action` directs the owning document to do one or both of these:

- Include revision-local declarations only after per-member executable support
  is established for the exact detailed human CLI entrypoint and its
  lock/recovery/request/transaction antecedents, include every applicable
  exhaustively enumerated transition consistently, and remove unsupported
  runtime-operation extras.
- Narrow the generic wording or explicitly delegate exact membership and
  detailed transition semantics to the applicable declaration, executable,
  detailed-command, and caller authorities.

The action must preserve runtime behavior, the single writer, closed request
validation, caller eligibility, and lifecycle partitioning. It must not change
`RUNTIME_OPERATIONS`, add an alternate writer, weaken request closure, infer
membership from prose majority, invent runtime behavior, or repair a claim from
unresolved evidence. It also must not advertise an importable helper by
borrowing `main()`'s lock/recovery context or treat `expected_manifest`
projection validation as live readback.

For every non-clean gap, `suggested_action` follows the cause-specific recovery
assignment above. It must name the authorized retry, repair, reconciliation,
escalation, or termination layer and its terminal condition. In particular,
runtime, readback, detailed-command, and caller owners reconcile authority;
source owners do not absorb adapter defects; and the runner cannot retry denied,
invalid, stale-currentness, ambiguous-scope, or lifecycle-prohibited inputs as
though they were transient. None of these non-clean states permits a generic-
claim edit based on assumptions.

## Consumers and supported-surface boundary

Current consumers are ACR-403 reviewers, future ACR-398 reviewers after the
qualified handoff, and maintainers or agents reviewing complete-looking generic
tool and lifecycle claims through separate exact-target comparisons. The
supported runtime-operation surface for this eval is the detailed human CLI
entered through `_parser()` and top-level `main()` with its lock, recovery,
closed-request, transaction-completion, and applicable live-readback
antecedents. Direct standalone WUs using planning root `P` and feature
direct/refactoring routes using `F/routes` are request-topology cohorts behind
that surface, not alternate invocation modes. Importable helpers remain outside
the generic CLI comparison unless a named authoritative caller proves the
mode-local acting antecedents; an unbound accepted mode is an authority
conflict.

Future consumers may include a separately authorized detector, evidence
resolver, eval runner, advisory report reader, or caller-owned rollout or
enforcement integration. There is no customer runtime, public API, persisted
format, deployment, data migration, session migration, cutover, or consumer
opt-in introduced by this specification.

No current or future consumer may aggregate these per-claim results into a
repository result without the separately authorized discovery, identity-bound
inventory, exclusion, fan-out, completeness-equality, and aggregation contract
defined as out of scope above.

## Step 6b and Step 6c boundary

Step 6b owns this sole repository specification and the canonical machine-local
output index at `${scratch_dir}/phase6/step6b-output-index.md`. The index maps
each of `TI-01` through `TI-08` to its proposal test-intent source, the emitted
eval path and identity `wu-session-runtime-operation-catalog-drift:<TI-ID>`, and
the required evidence application point for that item. Step 6c is a fresh
inspection-only invocation. It consumes the indexed eval identity, path,
proposal mappings, required evidence, and orchestrator-owned side-channel
evidence, then inspects the complete repository state, this specification,
current authorities, the one indexed exact target claim, and forbidden output
absence. Its source inspection binds `catalog_path`, `catalog_anchor`,
declaration, capability/entrypoint/invocation-mode support, transition,
mode-bound readback, detailed-command, caller, and target-claim content to one
exact repository identity and checks the authority, scope, and exhaustive
per-claim aggregation rules above. Step 6c must reject a missing TI entry, a
missing or non-unique exact target pair, or any mapping whose proposal source,
eval path, eval identity, or required evidence does not match this specification
and the approved proposal.

Step 6c does not patch this file, add a repository path, implement a detector,
invoke the migration executable, or create behavior evidence. A specification
mismatch returns through explicit contract/spec revision and fresh Step 6b
authoring. Process evidence establishes authoring order and scope only. One
Step 6c inspection cannot claim repository or all-current-claims cleanliness;
multiple target claims require separate caller-owned inspections, and no
repository aggregation contract is selected here.

## Lifecycle notes

ACR-403 ends at `WRITE`.

- `ROLL_OUT` requires a later separately authorized WU to select and implement
  a detector and semantic extraction approach, provide representative positive,
  per-exact-claim non-fire, degraded, cause-specific evidence/identity/authority/
  scope gap, and lifecycle-prohibited fixtures; exercise every required
  `failure_cause` and recovery disposition; inventory capability, entrypoint,
  and invocation modes; distinguish live-storage from
  `phase3-expected-manifest` readback; prove exhaustive per-claim transition
  enumeration; resolve evidence; validate reports; observe advisory executions;
  review false positives and evidence drift; and name downstream wiring.
- `ENFORCE` additionally requires trusted findings, a named caller and
  hookpoint, severity policy, repair routing, fail-closed evidence behavior, and
  durable enforcement-readiness evidence.
- `MAINTAIN` tracks authority syntax, semantic claim anchors, evidence adapters,
  finding comparability, classifier false positives, downstream currentness,
  and lifecycle regression when reliability no longer supports enforcement.

No eval detector language, parser library, fixture serialization, eval-runner
mode, report path, eval CLI, CI, scheduler, cron, scan cadence, hookpoint, or
enforcing caller is selected here. Rollback of state introduced by the exact
repository delta is deletion or reversion of this one Markdown specification;
that delta introduces no runtime, schema, data, session/index, or deployment
state.
External or protected-state rollback is non-applicable only when exact-WU
process evidence and authoritative target-state readback establish non-action.
Without both, external and protected-state action remains unestablished, a
separate reconciliation obligation remains open, and repository reversion does
not retire it.

## Merge-qualified ACR-398 handoff

Only after ACR-403 is verified merged may ACR-398 cite the merged specification
as inherited Step 6b structural-verification intent. ACR-398 retains its exact
two-file repair scope, `tools/README.md` and
`conventions/wu-session-lifecycle.md`, and retains direct point-in-time
authority-versus-final-claim and final-diff inspection. That inspection must use
one exact repository identity, treat declaration support and authority conflicts
as non-clean, select each exact target with its own `catalog_path` plus
`catalog_anchor`, and compare every authoritative transition applicable to that
target's resolved scope. ACR-398 owns any target selection across its exact
two-file scope; this eval supplies no claim-discovery completeness and no
repository aggregate. The merged `WRITE` specification supplies intent, not a
detector result.

The handoff does not copy this eval into ACR-398's diff, execute it, establish a
clean result for any unselected claim or the repository, replace ACR-398's
direct inspection, change runtime membership or sequencing, or advance this
eval beyond `WRITE`. ACR-398 remains the owner of the generic claim repair and
its separately verified per-target outcome.

## Anti-scope

This `WRITE` artifact does not define or authorize detector code, Python or Rust
implementation, fixtures, tests, pytest imports or assertions, a one-off
verifier, a resolver, an eval-runner adapter, CLI/CI/scheduler/cron wiring,
runtime writer changes, protected-state mechanisms or writes, ACR-398 edits,
ticket actions, or estimate mutation.

## References

- `conventions/evals.md`
- `tools/wu-session-migration/wu_session_migration.py`
- `tools/wu-session-migration/README.md`
- `tools/README.md`
- `conventions/wu-session-lifecycle.md`
- `agents/implementation-pipeline-orchestrator.md`
- `workflows/implementation-pipeline.md`
- `agents/wu-session-resumer.md`
- `~/projects/ai/planning/acr-403-operation-catalog-eval/proposals/acr-403-ACR-403.md`
- `~/projects/ai/planning/acr-403-operation-catalog-eval/contracts/acr-403-wu-session-runtime-operation-catalog-drift.md`
