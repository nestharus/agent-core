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
enforcement, runtime behavior, or protected-state behavior.

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
| `wu-session-runtime-write-v1` | `tools/wu-session-migration/wu_session_migration.py` owns executable runtime-operation membership and closed request behavior; its detailed README owns the human command contract. |
| `wu-session-runtime-lifecycle-ownership-v1` | The detailed migration README, implementation workflow/operator, and resumer own transition eligibility, ordering, readback, caller partitions, and the sole-writer relationship. |
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
evaluated repository revision, WU, PR, session, or selected invocation subtree.
It must represent these semantic records:

| Evidence role | Required semantic fields and decision use |
|---|---|
| Executable authority | `authority_path`, `authority_symbol`, evaluated revision/content identity, readable source snapshot, and extracted `canonical_operations`. This is canonical membership evidence. |
| Parser exposure | Parser path and semantic anchor, set-derived runtime subcommands, and required `--request` relationship. This corroborates exposure only. |
| Request closure | Application, validation, and recovery semantic anchors; unsupported-operation refusal; command/request equality; and recovery closure. This corroborates closed membership and request behavior only. |
| Detailed command contract | Detailed README path, semantic anchors, command forms, operation semantics, lifecycle order, conditional transition, and readback semantics. This is detailed human command and transition authority. |
| Caller wiring | Implementation workflow/operator and resumer paths and semantic anchors, transition eligibility, successor order, closed-readback ownership, `owning_caller`, and `sole_writer`. |
| Generic claim | `catalog_path`, stable semantic `catalog_anchor`, evaluated revision/content identity, surrounding context, `claim_kind`, extracted `catalog_operations`, and any claimed sequence. This is the claim under comparison. |
| Comparison | Deterministically sorted `missing_operations` and `extra_operations`, plus structured `wiring_transition`. |
| Observation provenance | `evidence_paths`; revision, WU, PR, and session locators when available; source, trace, prompt, log, report, audit, and final changed-surface paths when available. |
| Evidence availability | `evidence_state` and `missing_evidence_roles`, with enough role-level detail to distinguish unavailable evidence from a resolved empty collection. |
| Downstream handoff | Verified ACR-403 merge identity and the ACR-398 inherited Step 6b intent boundary without broadening ACR-398's two-file repository scope. |

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
canonical operation authority. Conversely, readable executable authority and a
readable complete claim can establish the source relationship without a final
diff.

## Authority order

Disagreement is preserved with source paths and content identities. It is not
settled by prose majority.

1. `tools/wu-session-migration/wu_session_migration.py:RUNTIME_OPERATIONS` owns
   revision-local runtime-operation membership.
2. `_parser()`, `apply_runtime_request()`, `_validate_runtime_request()`, and
   recovery closure corroborate set-derived exposure, required `--request`,
   unsupported-operation refusal, and command/request equality. They consume or
   derive from the membership authority and are not independent votes.
3. `tools/wu-session-migration/README.md` owns the detailed human command,
   topology, transition, lifecycle sequencing, and readback contract.
4. `agents/implementation-pipeline-orchestrator.md`,
   `workflows/implementation-pipeline.md`, and
   `agents/wu-session-resumer.md` own caller eligibility, ordering, readback,
   and their lifecycle partitions while preserving the sole Python writer.
5. `tools/README.md`, `conventions/wu-session-lifecycle.md`, and other generic
   summaries are claims compared with higher authority only when their context
   explicitly asserts or strongly implies applicable completeness.
6. Tests, source snapshots, saved traces, reports, audit bundles, and final
   diffs are corroborating or observation evidence. They do not expand
   canonical membership.

At the revision inspected for ACR-403, the executable set contains these eight
members, shown as a deterministic point-in-time evidence list:

- `cold-start-disposition-bind`
- `phase0-init`
- `phase0-reresolve`
- `phase3-bind`
- `phase7-upsert`
- `phase9-update`
- `resumer-close`
- `resumer-update`

A future detector must extract members from `RUNTIME_OPERATIONS` at the
evaluated revision. This eight-member observation is not immutable detector
policy. The Python value is a set, so this display order has no lifecycle
meaning.

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
`catalog_operations` differs from revision-local `canonical_operations`. One or
both of `missing_operations` and `extra_operations` is non-empty.

### Conditional-wiring drift

An active generic lifecycle claim classified as `exact` or `complete-implied`
presents the writer sequence as complete, but omits or contradicts a supported
conditional transition established by detailed and caller authority. The known
recurrence is eligible existing open pre-PR, pre-Phase-3 policy re-entry through
`phase0-reresolve`, followed by caller-owned closed readback and later Phase 3
composition.

These are documentation-contract drift behaviors. They are not runtime writer
failure, parser failure, request-validation failure, transaction failure,
protected-state corruption, or evidence that a conditional transition is
mandatory for every normal WU.

## Claim taxonomy

The active target anchor is classified before any membership or wiring
comparison. Context supporting the classification remains in evidence.

| `claim_kind` | Meaning | Comparison disposition |
|---|---|---|
| `exact` | The prose explicitly says the applicable inventory or sequence is exact, exhaustive, or complete. | Compare every applicable membership and wiring obligation. |
| `complete-implied` | Wording and structure strongly present an applicable complete inventory or sequence without an explicit completeness token. | Compare while retaining the context that supports the completeness inference. |
| `delegated` | The prose unambiguously delegates exact membership or detailed sequencing to executable or detailed authority and does not restate an exhaustive set. | Non-fire unless surrounding context independently makes a complete claim. |
| `partial-example` | The prose clearly labels members as examples, selected cases, illustrative, or partial. | Non-fire unless surrounding context independently implies completeness. |
| `non-runtime` | The anchor lists top-level migration or support commands rather than members of `RUNTIME_OPERATIONS`. | Exclude those commands from runtime membership differences. |

Ambiguity remains visible in source context, `evidence_state`,
`missing_evidence_roles`, and `confidence`. Operation tokens alone do not make
an unresolved claim `exact`.

## Membership comparison contract

For a resolved `exact` or `complete-implied` membership claim:

- `canonical_operations` is the unique set extracted from revision-local
  `RUNTIME_OPERATIONS`.
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
- Ordering differences alone are inapplicable because executable membership is
  a set.

Parser registration, request closure, detailed Markdown, callers, tests, and
other claims cannot vote an operation into or out of canonical membership.

## Conditional-wiring comparison contract

Wiring is evaluated separately from membership. An operation name in a complete
membership list does not establish its supported lifecycle edge. A
membership-only claim does not acquire sequencing obligations.

Every resolved `wiring_transition` record contains:

- `transition_id`
- `operation`
- `source_conditions`
- `destination_or_successor`
- `conditional`
- `owning_caller`
- `sole_writer`
- `observed_treatment`, one of `included`, `delegated`, `omitted`,
  `contradicted`, or `not-applicable`
- `evidence_paths`

For the known recurrence, the transition record represents:

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

An applicable complete-sequence claim has conditional-wiring drift when
`observed_treatment` is `omitted` or `contradicted`. `included` and unambiguous
`delegated` treatment are aligned. `not-applicable` is used for a claim that has
no sequence obligation, including a membership-only claim or a lifecycle
partition that does not own the transition. When required wiring authority is
unavailable, the record is `null` under the evidence-gap rules rather than
inventing `not-applicable`.

## Non-fire cases

A future `None` outcome is permitted only with sufficient evidence for the
selected comparison. The named unwanted behavior is absent in each of these
cases:

- Generic prose explicitly delegates exact membership or detailed sequencing
  to executable or detailed authority and does not restate an exhaustive set.
- A list is clearly partial, illustrative, selected, or example-only and no
  surrounding context independently implies completeness.
- The anchor lists non-runtime commands such as `capture-evidence`, `dry-run`,
  `apply`, or `validate-pre-pr-readback`.
- A membership-only claim differs only in ordering because
  `RUNTIME_OPERATIONS` is a set.
- A membership-only claim does not describe a sequence, so conditional edge
  placement is not applicable.
- A complete generic claim contains every canonical member, contains no
  unsupported extra, and includes or unambiguously delegates every applicable
  conditional transition.
- A lifecycle-partitioned caller omits operations it does not own, including the
  resumer omitting pre-PR operations.
- Historical text, fixture text, proposal text, or a negative example identifies
  an omission as unwanted behavior rather than presenting an active supported
  catalog claim.
- The known conditional re-entry does not occur in a normal WU because its
  eligibility conditions are false.

Incomplete evidence is not a non-fire case.

## Evidence-state contract

Non-degradable roles depend on the selected comparison. Executable authority
and the active target claim are always non-degradable. Detailed transition and
caller authority are additionally non-degradable for a wiring determination.

| `evidence_state` | Minimum evidence | Permitted future decision behavior |
|---|---|---|
| `complete` | Executable authority and active claim are readable, classification resolves, and every membership or wiring role required for the selected comparison resolves. | A behavior finding is permitted when unwanted behavior is present. `None` is permitted only for a fully evidenced non-fire. |
| `degraded` | Executable authority and active claim remain readable and all non-degradable roles for the selected comparison resolve, but optional parser, request, trace/report, test, audit, final-diff, or detailed/caller corroboration not required by that selected comparison is unavailable. | A directly established mismatch may produce a reduced-confidence finding with named `missing_evidence_roles`. `None` is permitted only when the remaining evidence still resolves every fact required for that non-fire. Missing optional final-diff evidence alone does not erase a source-established mismatch. |
| `missing` | Executable authority, active target claim, claim classification, or another non-degradable role required by the selected comparison cannot be resolved. | Do not assert catalog or wiring drift and do not use `None`, `NO_FINDING`, or a PASS-like result. A future runtime may produce a distinct `LOW` evidence-gap finding with available paths and missing roles, or surface runner-level indeterminate, `NEEDS_INPUT`, or error behavior. |

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

Every such finding also contains all twelve operation/catalog extension fields
exactly:

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

For a resolved drift finding, `eval_id` is
`wu-session-runtime-operation-catalog-drift`, `authority_symbol` is
`RUNTIME_OPERATIONS`, operation collections are deterministic lists, and the
applicable wiring treatment is explicit. `evidence_paths` retains actual source
and corroboration locators.

For an evidence-gap finding, all fields remain present. Unavailable scalar or
record values are `null`; unavailable operation collections are `null`;
available collections remain deterministic lists; and
`missing_evidence_roles` names every source of indeterminacy. Empty lists always
mean resolved empty sets, never unknown evidence.

Severity describes finding impact, not the ACR-403 risk-profile verdict:

- `MEDIUM`: established generic operation-catalog or conditional-wiring drift.
- `HIGH`: established drift that also instructs an unsafe alternate writer,
  unsupported runtime behavior, or invalid lifecycle action.
- `LOW`: a distinct evidence-resolution, instrumentation, or adapter gap.

`confidence` reflects evidence completeness, directness, and claim-classification
certainty. It must not conceal degraded or missing evidence.

## Suggested action

For established operation-catalog or conditional-wiring drift,
`suggested_action` directs the owning document to do one or both of these:

- Include supported revision-local membership and applicable transition
  semantics consistently, and remove unsupported runtime-operation extras.
- Narrow the generic wording or explicitly delegate exact membership and
  detailed transition semantics to executable and detailed authority.

The action must preserve runtime behavior, the single writer, closed request
validation, caller eligibility, and lifecycle partitioning. It must not change
`RUNTIME_OPERATIONS`, add an alternate writer, weaken request closure, infer
membership from prose majority, invent runtime behavior, or repair a claim from
unresolved evidence.

For an evidence gap, the action is to restore or resolve the named evidence
roles, or repair the future adapter/specification before another execution
attempt. It is not to edit a catalog based on assumptions.

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
current authorities, current claims, and forbidden output absence. Step 6c
must reject a missing TI entry or any mapping whose proposal source, eval path,
eval identity, or required evidence does not match this specification and the
approved proposal.

Step 6c does not patch this file, add a repository path, implement a detector,
invoke the migration executable, or create behavior evidence. A specification
mismatch returns through explicit contract/spec revision and fresh Step 6b
authoring. Process evidence establishes authoring order and scope only.

## Lifecycle notes

ACR-403 ends at `WRITE`.

- `ROLL_OUT` requires a later separately authorized WU to select and implement
  a detector and semantic extraction approach, provide representative positive,
  non-fire, degraded, and missing-evidence fixtures, resolve evidence, validate
  reports, observe advisory executions, review false positives and evidence
  drift, and name downstream wiring.
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
authority-versus-final-claim and final-diff inspection.

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
