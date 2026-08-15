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
| `wu-session-runtime-write-v1` | `tools/wu-session-migration/wu_session_migration.py:RUNTIME_OPERATIONS` owns declared runtime-operation membership. Parser exposure, request equality, operation-specific projection or handler validation, recovery and closed-request acceptance, and the detailed README command form jointly establish whether each declaration is executable support. |
| `wu-session-runtime-lifecycle-ownership-v1` | Operation-specific executable validators own transition source-state eligibility and allowed effects, and the executable readback validator owns post-write acceptance. The detailed README owns human command forms; implementation workflow/operator and resumer documents own invocation partition, progression order, caller-owned closure, and the sole-writer relationship. |
| `operation-catalog-claim-comparison-v1` | This accepted ACR-403 contract owns claim classification, membership and wiring comparison, non-fire semantics, and safe repair direction. Generic document anchors are claim instances, not authorities. |
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

## Positive evidence and required trace fields

`operation-catalog-drift-trace-v1` is a role-normalized evidence bundle for one
exact `evaluated_repository_identity` and, when present, one WU, PR, session, or
selected invocation subtree observed against that identity. It must represent
these semantic records:

| Evidence role | Required semantic fields and decision use |
|---|---|
| Repository identity | One `evaluated_repository_identity` naming the exact repository and full evaluated commit identity selected by the caller. Every repository-derived record below binds to this same value and resolves its content from that commit. |
| Declaration authority | `authority_path`, `authority_symbol`, the common identity, a readable source snapshot, and extracted `canonical_operations`. This is declared membership evidence, not executable-support evidence by itself. |
| Per-member executable support | One deterministic `operation_support` record per canonical declaration, bound to the common identity, proving parser exposure, command/request equality, an operation-specific valid projection or handler path, recovery and closed-request acceptance, and the detailed command contract. |
| Transition enforcement | Operation-specific executable projection, source-state, eligibility, and effect validators plus the executable readback validator, all bound to the common identity. These sources own executable transition admission and post-write acceptance. |
| Detailed command contract | Detailed README path and semantic anchors, common identity, human command forms, operation semantics, and described lifecycle/readback semantics. This source does not override executable admission or caller ownership. |
| Caller wiring | Implementation workflow/operator and resumer paths and semantic anchors, common identity, invocation partition, progression order, caller-owned closure, `owning_caller`, and `sole_writer`. |
| Generic claim | `catalog_path`, stable semantic `catalog_anchor`, common identity, surrounding context, `claim_kind`, `claim_scope`, extracted `catalog_operations`, and any claimed sequence. This is the claim under comparison. |
| Comparison | Deterministically sorted `missing_operations` and `extra_operations`, per-member `operation_support`, and aggregate `wiring_transition` proving exhaustive transition enumeration and comparison. |
| Observation provenance | `evidence_paths`; revision, WU, PR, and session locators when available; source, trace, prompt, log, report, audit, and final changed-surface paths when available. |
| Conflict and availability | `evidence_state`, `authority_state`, `authority_conflicts`, `reconciliation_owner`, and `missing_evidence_roles`, with enough role-level detail to distinguish unavailable evidence, identity failure, authority disagreement, and ambiguous scope from a resolved empty collection. |
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

Missing, mixed, independently selected, unbound, or unverifiable source
identities produce `evidence_state: identity-conflict`. This is a named
non-clean identity/evidence finding or runner-level indeterminate result, never
catalog drift, conditional-wiring drift, or `None`. The attempted common
identity and every conflicting observed identity remain in the finding and
`evidence_paths`; if no common identity was supplied, the required
`evaluated_repository_identity` field is `null` rather than invented.

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
2. For each declared member, `_parser()`, `apply_runtime_request()`,
   `_validate_runtime_request()`, the operation-specific projection or handler,
   shared recovery and closed-request path, and the detailed README command form
   must jointly establish executable support at the common identity.
3. Operation-specific executable projection, source-state, eligibility, and
   effect validators own transition admission and effects. The executable
   readback validator owns post-write acceptance.
4. `tools/wu-session-migration/README.md` owns detailed human command forms and
   their described semantics; it does not override executable admission.
5. `agents/implementation-pipeline-orchestrator.md`,
   `workflows/implementation-pipeline.md`, and
   `agents/wu-session-resumer.md` own invocation partition, progression order,
   caller-owned closure, and their lifecycle partitions while preserving the
   sole Python writer.
6. `tools/README.md`, `conventions/wu-session-lifecycle.md`, and other generic
   summaries are claims compared with higher authority only when their context
   explicitly asserts or strongly implies applicable completeness.
7. Tests, source snapshots, saved traces, reports, audit bundles, and final
   diffs are corroborating or observation evidence. They do not expand
   declared membership or executable support.

Every canonical declaration receives one `operation_support` record. If the
declaration and any readable required acting context disagree, or readable
contexts cannot be reconciled, `authority_state` is `conflict` or `unresolved`
and `evidence_state` is `authority-conflict`. An unavailable required source is
instead `missing`. Neither state is catalog drift or `None`. The finding retains
each disagreeing source and assigns
reconciliation to the runtime-migration owner for declaration, executable
admission, effects, and readback; the detailed-README owner for human command
forms; and the owning caller document for invocation partition, progression,
and caller-owned closure. These owners reconcile their shared boundary before
any generic-claim repair is permitted.

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

Current claim instances include the implemented-tool summary in
`tools/README.md`, the `Exact operations are` claim in
`conventions/wu-session-lifecycle.md`, and that convention's `Manifest storage`
sequence. Direct source comparison is review evidence for the contract; these
anchors remain claims rather than co-equal membership or transition authority.

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
supported conditional transitions in that domain. Executable validators and
readback establish transition admission, source-state eligibility, effects,
and acceptance; detailed command and caller authorities must agree on human
command form, invocation partition, progression, and caller-owned closure. The
known `phase0-reresolve` recurrence is one member of the enumerated transition
domain, not evidence that the domain contains only one member.

These are documentation-contract drift behaviors. They are not runtime writer
failure, parser failure, request-validation failure, transaction failure,
protected-state corruption, or evidence that a conditional transition is
mandatory for every normal WU.

## Claim taxonomy

The active target anchor is classified before any membership or wiring
comparison. Context supporting the classification remains in evidence.

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

A repository-global or ambiguously broad complete generic sequence is
accountable for every supported conditional transition in its claimed domain,
whether or not one sampled WU was eligible or traversed the edge. A selected
session's non-occurrence can establish only occurrence evidence. Eligibility-
based non-fire is permitted when the claim is explicitly `selected-cohort` and
that cohort is ineligible, or when evidence is `occurrence-only` and makes no
repository-completeness claim. `claim_scope: ambiguous` produces
`evidence_state: scope-indeterminate`, never drift and never `None`.

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
- `parser_exposure`
- `command_request_equality`
- `projection_or_handler_path`
- `recovery_or_closed_request_acceptance`
- `detailed_command_contract`
- `support_state`, one of `supported`, `conflict`, or `unresolved`
- `evidence_paths`

Each support fact is resolved from the common repository identity. A record is
`supported` only when parser exposure, exact command/request equality, an
operation-specific valid projection or handler path, admission through shared
recovery and the closed request, and the detailed human command contract all
resolve and agree. Records are unique and sorted by `operation`. Parser
registration, request closure, detailed Markdown, callers, tests, and other
claims cannot vote an operation into or out of `canonical_operations`; they
instead establish support or expose a named authority/integration conflict.

## Conditional-wiring comparison contract

Wiring is evaluated separately from membership. An operation name in a complete
membership list does not establish its supported lifecycle edge. A
membership-only claim does not acquire sequencing obligations.

The ticket-required `wiring_transition` output remains one field, but it is an
aggregate record rather than one selected transition. Every resolved aggregate
contains:

- `evaluated_repository_identity`
- `enumeration_evidence_paths`
- `canonical_transition_ids`
- `applicable_transition_ids`
- `transition_comparisons`
- `omitted_transition_ids`
- `contradicted_transition_ids`
- `enumeration_complete`

Canonical transition enumeration examines every operation-specific executable
validator and executable readback path for every canonical operation at the
common identity and identifies every supported conditional transition. The
canonical and applicable identifiers are unique deterministic sorted lists.
`enumeration_evidence_paths` retains the complete executable discovery boundary
plus the detailed and caller sources joined for human command and ownership
semantics. `enumeration_complete` is true only when this full domain was
resolved and every applicable canonical transition has one comparison.

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
- `detailed_command_paths`
- `caller_paths`
- `authority_state`, one of `aligned`, `conflict`, or `unresolved`
- `observed_treatment`, one of `included`, `delegated`, `omitted`,
  `contradicted`, or `not-applicable`
- `evidence_paths`

The comparison list is sorted by `transition_id`; omitted and contradicted IDs
are derived from it and sorted deterministically. Any executable/detailed/caller
disagreement makes the aggregate non-clean with `authority-conflict`, preserves
the disagreement and reconciliation owners, and prevents generic-claim repair.

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
`not-applicable` or an empty transition domain. Repository- or claim-level
`None` requires `enumeration_complete: true` and comparison of every applicable
authoritative transition.

## Non-fire cases

A future `None` outcome is permitted only after common-identity admission,
aligned authorities, resolved claim scope, complete per-member support, and any
applicable exhaustive transition aggregation. The named unwanted behavior is
absent in each of these cases:

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
- A complete generic claim contains every canonical declaration, contains no
  unsupported extra, every per-member support record is aligned, and an
  exhaustively enumerated aggregate includes or unambiguously delegates every
  applicable conditional transition in the claim domain.
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

## Evidence-state contract

The common repository identity, declaration authority, active target claim,
claim scope, and every per-member executable-support role are non-degradable for
a membership determination. Operation-specific executable transition
validators, executable readback validation, exhaustive transition enumeration,
detailed command forms, and caller partition/progression/closure are additionally
non-degradable for a wiring determination.

| `evidence_state` | Minimum evidence | Permitted future decision behavior |
|---|---|---|
| `complete` | One common identity is admitted; declaration, per-member support, active claim, classification/scope, and every applicable transition-enumeration/comparison source resolve and agree. | A behavior finding is permitted when unwanted behavior is present. `None` is permitted only for a fully evidenced non-fire, including exhaustive transition aggregation for a repository- or claim-level sequence result. |
| `degraded` | All identity, authority, support, scope, and enumeration sources needed for the selected decision resolve and agree, but optional trace/report, test, audit, or final-diff observation evidence is unavailable. | A directly established mismatch may produce a reduced-confidence finding with named `missing_evidence_roles`. `None` is permitted only when optional loss does not leave any decision fact unresolved. Missing optional final-diff evidence alone does not erase a common-identity source-established mismatch. |
| `missing` | A required source is unavailable at the common identity or a non-degradable role cannot be resolved without presenting a contradictory value. | Do not assert catalog or wiring drift and do not use `None`, `NO_FINDING`, or a PASS-like result. Produce a distinct `LOW` evidence-gap finding or runner-level indeterminate, `NEEDS_INPUT`, or error behavior. |
| `identity-conflict` | The common identity is absent, mixed, unbound, differs from caller currentness, or any repository-derived source cannot be verified at it. | Preserve the expected and observed identities in a named non-clean identity finding. Never compare into drift and never use `None`. Re-resolve all sources at one exact identity. |
| `authority-conflict` | Declaration and required acting contexts disagree, or executable transition/readback, detailed command, and caller partition/progression/closure authorities disagree. | Preserve all sides, `authority_conflicts`, and `reconciliation_owner`. Never emit catalog/wiring drift, generic-claim repair, or `None` until the named owners reconcile the source contracts. |
| `scope-indeterminate` | Completeness wording is active but its repository, domain, cohort, or occurrence scope cannot be resolved. | Preserve context and return a named non-clean scope finding or indeterminate result. Never let sampled eligibility choose the scope, and never emit drift or `None`. |

Identity admission precedes authority reconciliation, which precedes scope and
catalog/wiring comparison. A bundle with more than one failure retains every
observed conflict even when the first non-clean state prevents later comparison.

While lifecycle remains `WRITE`, unavailable runnable code is not a clean
behavior outcome. A future execution request must stop outside the conceptual
comparison rather than treating specification presence as `None`. Invalid
finding shape, failed result validation, or material adapter drift is a
validation or maintenance error, not a behavior finding and not a clean result.

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

For a resolved drift finding, `eval_id` is
`wu-session-runtime-operation-catalog-drift`, `authority_symbol` is
`RUNTIME_OPERATIONS`, `evaluated_repository_identity` is the admitted common
identity, operation collections and `operation_support` are deterministic, and
the aggregate wiring treatment is complete and explicit. `evidence_paths`
retains actual source and corroboration locators.

For an evidence-gap finding, all fields remain present. Unavailable scalar or
record values are `null`; unavailable operation collections are `null`;
available collections remain deterministic lists; and
`missing_evidence_roles` names every source of indeterminacy. Empty lists always
mean resolved empty sets, never unknown evidence. The selected
`evaluated_repository_identity` remains present when known, including in
identity, authority, or scope findings; it is `null` only when no common identity
was supplied. Conflicting observed identities and authorities remain in
`authority_conflicts` and `evidence_paths`. `reconciliation_owner` is a
deterministic list when multiple source owners must act.

Severity describes finding impact, not the ACR-403 risk-profile verdict:

- `MEDIUM`: established generic operation-catalog or conditional-wiring drift.
- `HIGH`: established drift that also instructs an unsafe alternate writer,
  unsupported runtime behavior, or invalid lifecycle action.
- `LOW`: a distinct identity, authority, scope, evidence-resolution,
  instrumentation, or adapter gap.

`confidence` reflects evidence completeness, directness, and claim-classification
certainty. It must not conceal degraded or missing evidence.

## Suggested action

For established operation-catalog or conditional-wiring drift,
`suggested_action` directs the owning document to do one or both of these:

- Include revision-local declarations only after per-member executable support
  is established, include every applicable exhaustively enumerated transition
  consistently, and remove unsupported runtime-operation extras.
- Narrow the generic wording or explicitly delegate exact membership and
  detailed transition semantics to the applicable declaration, executable,
  detailed-command, and caller authorities.

The action must preserve runtime behavior, the single writer, closed request
validation, caller eligibility, and lifecycle partitioning. It must not change
`RUNTIME_OPERATIONS`, add an alternate writer, weaken request closure, infer
membership from prose majority, invent runtime behavior, or repair a claim from
unresolved evidence.

For an identity gap, re-resolve every repository-derived source at one exact
identity. For an authority conflict, the named runtime, detailed-command, and
caller owners reconcile declaration/admission/effects/readback and
partition/progression/closure before the generic-document owner acts. For
ambiguous scope, clarify the claim domain. For another evidence gap, restore or
resolve the named evidence roles or repair the future adapter/specification
before another execution attempt. None of these non-clean states permits a
generic-claim edit based on assumptions.

## Consumers and supported-surface boundary

Current consumers are ACR-403 reviewers, future ACR-398 reviewers after the
qualified handoff, and maintainers or agents reviewing complete-looking generic
tool and lifecycle claims. Direct standalone WUs using planning root `P` and
feature direct/refactoring routes using `F/routes` remain unchanged runtime
cohorts behind the same Python writer and closed request contract.

Future consumers may include a separately authorized detector, evidence
resolver, eval runner, advisory report reader, or caller-owned rollout or
enforcement integration. There is no customer runtime, public API, persisted
format, deployment, data migration, session migration, cutover, or consumer
opt-in introduced by this specification.

## Step 6b and Step 6c boundary

Step 6b owns this sole repository specification and the canonical machine-local
output index at `${scratch_dir}/phase6/step6b-output-index.md`. The index maps
each of `TI-01` through `TI-08` to its proposal test-intent source, the emitted
eval path and identity `wu-session-runtime-operation-catalog-drift:<TI-ID>`, and
the required evidence application point for that item. Step 6c is a fresh
inspection-only invocation. It consumes the indexed eval identity, path,
proposal mappings, required evidence, and orchestrator-owned side-channel
evidence, then inspects the complete repository state, this specification,
current authorities, current claims, and forbidden output absence. Its source
inspection binds declaration, executable-support, transition, detailed-command,
caller, and target-claim content to one exact repository identity and checks the
authority, scope, and exhaustive aggregation rules above. Step 6c must reject a
missing TI entry or any mapping whose proposal source, eval path, eval identity,
or required evidence does not match this specification and the approved
proposal.

Step 6c does not patch this file, add a repository path, implement a detector,
invoke the migration executable, or create behavior evidence. A specification
mismatch returns through explicit contract/spec revision and fresh Step 6b
authoring. Process evidence establishes authoring order and scope only.

## Lifecycle notes

ACR-403 ends at `WRITE`.

- `ROLL_OUT` requires a later separately authorized WU to select and implement
  a detector and semantic extraction approach, provide representative positive,
  non-fire, degraded, missing-evidence, identity-conflict, authority-conflict,
  and scope-indeterminate fixtures, prove exhaustive transition enumeration,
  resolve evidence, validate reports, observe advisory executions, review false
  positives and evidence drift, and name downstream wiring.
- `ENFORCE` additionally requires trusted findings, a named caller and
  hookpoint, severity policy, repair routing, fail-closed evidence behavior, and
  durable enforcement-readiness evidence.
- `MAINTAIN` tracks authority syntax, semantic claim anchors, evidence adapters,
  finding comparability, classifier false positives, downstream currentness,
  and lifecycle regression when reliability no longer supports enforcement.

No detector language, parser library, fixture serialization, runner mode,
report path, CLI, CI, scheduler, cron, scan cadence, hookpoint, or enforcing
caller is selected here. Rollback of this WU is deletion or reversion of this
one Markdown specification; no runtime, schema, data, session/index,
deployment, protected-state, or ticket-estimate rollback exists.

## Merge-qualified ACR-398 handoff

Only after ACR-403 is verified merged may ACR-398 cite the merged specification
as inherited Step 6b structural-verification intent. ACR-398 retains its exact
two-file repair scope, `tools/README.md` and
`conventions/wu-session-lifecycle.md`, and retains direct point-in-time
authority-versus-final-claim and final-diff inspection. That inspection must use
one exact repository identity, treat declaration support and authority conflicts
as non-clean, and compare every authoritative transition applicable to each
complete claim's resolved scope; the merged `WRITE` specification supplies
intent, not a detector result.

The handoff does not copy this eval into ACR-398's diff, execute it, establish a
clean result, replace ACR-398's direct inspection, change runtime membership or
sequencing, or advance this eval beyond `WRITE`. ACR-398 remains the owner of
the generic claim repair and its separately verified outcome.

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
