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

The `validator` classifies one exact target claim, compares it with the bounded
comparison authority, and decides the named unwanted behavior, non-fire, and
evidence state. The `mapper` losslessly maps admitted source and target
occurrences into the normalized trace records below. Neither role makes this
Markdown specification executable.

## Identity and lifecycle

- `eval_id`: `wu-session-runtime-operation-catalog-drift`
- `owner_wu`: `ACR-403`
- `parent_handoff`: `ACR-398`
- `behavior_class`: generic WU-session runtime operation-catalog membership
  drift and conditional lifecycle-wiring drift
- `artifact`: `evals/wu-session-runtime-operation-catalog-drift/eval.md`
- `selected_verification_level`: `particular-integration`
- `lifecycle_state`: `WRITE`

`WRITE` means this reviewable behavior specification exists. It does not mean a
detector, fixture, evidence adapter, invocation, finding, `None`, rollout,
enforcement, runtime change, merge verification, or external action exists.
Repository evidence for this file cannot prove an external or protected-state
action or non-action.

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
```

This file translates exactly four stable contract surfaces:

| Contract surface | External owner and translated boundary |
|---|---|
| `eval-spec-lifecycle-finding-and-evidence-v1` | `conventions/evals.md` owns eval placement, lifecycle, semantic evidence roles, `trace -> finding | None`, and the six base finding fields. |
| `wu-session-runtime-write-v1` | `tools/wu-session-migration/wu_session_migration.py:RUNTIME_OPERATIONS` owns revision-local declared membership. The detailed human CLI entered through `tools/wu-session-migration/__main__.py`, `_parser()`, and top-level `main()` supplies parser/main reachability, closed operation/request validation, and successful transaction-path support. |
| `wu-session-runtime-lifecycle-ownership-v1` | Operation validators own eligibility and effects; the top-level CLI-only live readback owns post-write live acceptance where material; the detailed README owns human command and transition semantics; and applicable implementation/resumer sources own caller partition and progression while preserving exact `sole_writer`. |
| `operation-catalog-claim-comparison-v1` | This accepted ACR-403 contract owns exact target admission, activation and polarity, completeness and command-domain classification, lossless target occurrence accounting, membership and conditional-wiring comparison, non-fire semantics, and safe document-only repair for one claim. |

Symbols, methods, fields, operations, sections, and evidence families subordinate
to those surfaces are not additional adapter contracts. The ACR-398 prerequisite
is external handoff context, not a fifth adapter surface, trace output, authority
surface, or result field of this eval.

## Conceptual boundary

The future conceptual interface is:

`evaluate(normalized_evidence: operation-catalog-drift-trace-v1) -> finding | None`

This signature is specification text only. It selects no language, parser,
serialization, fixture, resolver, runner, report sink, schedule, hookpoint, or
caller.

Each invocation evaluates exactly one injectively admitted target claim at one
common repository identity. A finding represents the named documentation drift
or a cause-preserving inability to decide a comparison fact required for that
claim. `None` means only that this named behavior is sufficiently evidenced as
absent or non-applicable for that claim. It does not certify another claim, the
containing document, the repository, runtime safety, global serialization,
namespace consistency, helper authority, recovery, availability, merge state,
or external action.

This is an operation-catalog and conditional-wiring documentation-drift eval.
Wake and scheduler observers, generic public helpers, alternate namespaces,
rollback, recovery, cleanup, and other latent runtime capabilities are outside
its comparison domain. If supplied, they may remain as non-decisional provenance
or residual uncertainty. Their mere presence, reachability, absence, or
unresolved authority does not create this eval's finding and does not prevent an
otherwise valid `None`. An exact observed acting-context occurrence becomes
decisional only when it directly supplies or conflicts with a required
membership or transition comparison fact for the selected claim. The trace must
name that fact and preserve the exact source occurrence; it may not promote an
adjacent capability merely because the capability can affect or observe runtime
state.

This eval does not claim complete discovery of repository claims or exhaustive
accounting of every actor that can affect, recover, observe, schedule, dispatch,
or judge manifest/index state. A repository-level consumer would need a separate
contract for identity-bound claim discovery, exclusions, per-claim fan-out,
completed-result equality, and aggregation.

## Positive evidence and required trace fields

`operation-catalog-drift-trace-v1` is a role-normalized evidence bundle for one
exact `evaluated_repository_identity` and one admitted
`target_claim_identity`. It represents these semantic records:

| Evidence role | Required semantic fields and decision use |
|---|---|
| Repository identity | One provider-issued `evaluated_repository_identity` with canonical repository object and full commit identity. Every repository-derived source and target record resolves from that identity. |
| Declaration authority | `authority_path`, `authority_symbol`, readable identity-bound source, and complete extracted `canonical_operations`. Declaration owns membership, not lifecycle order or functional support by itself. |
| Comparison-authority closure | A closed `comparison_authority_source_domain`, admitted span inventory, lossless raw source coverage, raw occurrence inventory, and exactly-once dispositions for only the revision-bound facts required by this comparison. |
| Detailed CLI support | One `operation_support` record per canonical operation covering declaration, parser and top-level `main()` reachability, closed operation/request validation, successful operation-specific transaction path, detailed command semantics, and applicable caller authority. |
| CLI-only live readback | Where a transition comparison materially requires post-write live acceptance, the top-level `validate-pre-pr-readback` CLI path entered through `__main__.py` and `main()` without `expected_manifest`, under its actual lock and completed recovery antecedents, is the only live-readback authority. |
| Lifecycle authority facts | Typed partial fact occurrences from operation-specific executable validators, detailed command semantics, CLI-only live readback where material, and applicable implementation/resumer caller and progression authority. Each occurrence contributes only fields it owns. |
| Transition assembly | Lossless n-way assembly records, exact field ownership, assembly conflicts, `canonical_transition_ids`, `applicable_transition_ids`, and independent admitted/completed equalities for source facts and assembled transitions. |
| Exact target claim | Structured target identity, exact context and source spans, lossless presentation and transition occurrence inventories, activation and polarity, structured `claim_kind`, scope and applicability, command dispositions, interpreted operations, sequence assertions, and discharge witnesses. |
| Comparison | Deterministically sorted operation differences and aggregate `wiring_transition`, including lifecycle-sequence completeness, canonical transitions, target treatments, unique/group discharge, omissions, contradictions, and indeterminate mappings. |
| Observation provenance | `evidence_paths`; source, trace, prompt, log, report, audit, and final changed-surface paths when available. Optional provenance does not replace authority. |
| Conflict and availability | `evidence_state`, `authority_state`, `authority_conflicts`, `missing_evidence_roles`, and injective `failure_obligations` for unresolved facts required by the selected comparison. |
| Non-decisional context | Optional `non_decisional_provenance` and `residual_uncertainty` for adjacent capabilities or actors. These records never independently produce a finding, change a drift outcome, or veto `None`. |

The required ticket fields `authority_path`, `authority_symbol`,
`canonical_operations`, `catalog_path`, `catalog_anchor`, `claim_kind`,
`catalog_operations`, `missing_operations`, `extra_operations`,
`wiring_transition`, `evidence_paths`, and degraded or missing evidence state are
retained throughout.

## Common repository identity admission

`evaluated_repository_identity` is the structured record
`{canonical_repository_id, evaluated_commit}`. `canonical_repository_id` is
`{provider, repository_object_id}` using the provider's immutable repository
object identity. Slugs, remote URLs, redirects, and checkout paths are locators,
not alternate identities.

Every admitted authority source, target source, observed acting context, and
corroborating repository record must resolve its path and content from the same
full commit. A required path absent at that identity is
`absent-at-identity`; expected/selected mismatch is
`caller-currentness-mismatch`; mixed identities are
`mixed-source-identities`; a source without a commit binding is
`unbound-source-identity`; and an unauthenticated supplied identity is
`unverifiable-source-identity`. Each is non-clean for facts that depend on it.
None of these is silently repaired by ambient worktree or cached report state.

## Exact target identity and activation

`target_claim_identity` is the injective structured record:

- `canonical_repository_id`
- `evaluated_commit`
- `catalog_path`
- `catalog_anchor`
- `source_blob_identity`
- `resolved_source_span`
- `resolved_claim_content_identity`

`catalog_path` is a canonical repository-relative POSIX path naming one regular
Git blob at the evaluated commit. It has no empty, `.`, `..`, repeated,
backslash, absolute, symlink, alias, or escaping form.

`catalog_anchor` is
`{anchor_kind: exact-claim-source, anchor_text}`. `anchor_text` is the complete
source text of the selected semantic claim, not a heading, abbreviation,
ordinal, or normalized alternate spelling. It must resolve to exactly one
occurrence in the admitted blob. Zero, repeated, or overlapping resolutions are
non-clean. Path, anchor, blob, span, and content identities remain separate
fields and are never delimiter-concatenated.

Before classification or comparison, the mapper admits the complete
`target_context_source_span` needed to determine source use, temporal status,
quotation, and assertion polarity. It then builds a lossless
`target_context_occurrence_inventory`. Every code point in that span maps to an
occurrence or explicit grammar boundary, and every occurrence receives exactly
one disposition.

The target has two independently evidenced classifications:

| Field | Values and meaning |
|---|---|
| `target_activation` | `active`, `historical`, `quoted`, `proposal-only`, `fixture`, or `ambiguous`. The exact context span must establish the source use. |
| `target_polarity` | `affirmative`, `negative-example`, or `ambiguous`. Negative examples describe text that must not be treated as current authority. |

Only `{target_activation: active, target_polarity: affirmative}` yields
`target_activation_polarity: active-affirmative` and permits membership or
wiring comparison. Historical, quoted, proposal-only, fixture, and
negative-example occurrences receive explicit `non-fire-non-active` or
`non-fire-negative` dispositions while preserving their complete raw source and
context. Ambiguous activation or polarity yields
`activation-polarity-indeterminate`; it cannot compare, drive repair, or become
`None` until the ambiguity is resolved. Token presence, completeness wording,
or a current file path cannot override context or polarity.

A resolved non-active or negative disposition is itself a sufficiently evidenced
non-fire path after exact identity and lossless context accounting close. It does
not require operation support or transition assembly for comparisons that its
classification prevents. Only the active-affirmative path proceeds to membership
or wiring comparison.

The target-side accounting equalities are:

`target_context_code_points == target_context_occurrence_code_points + target_context_grammar_boundary_code_points`

`target_context_occurrence_ids == target_context_disposition_occurrence_ids`

The `+` expression is a disjoint exact partition. Non-active and negative
occurrences still participate in raw occurrence accounting; their non-fire
disposition is not source erasure.

## Comparison authority order

Disagreement is preserved with exact source identities. It is never settled by
prose majority, test count, or source deletion.

1. `tools/wu-session-migration/wu_session_migration.py:RUNTIME_OPERATIONS` owns
   revision-local declared membership. Its set order has no lifecycle meaning.
2. `tools/wu-session-migration/__main__.py`, `_parser()`, and top-level `main()`;
   exact operation/request validation; the operation-specific projection or
   handler; and successful transaction return establish functional detailed CLI
   support. Declaration alone is not support.
3. Operation-specific executable validators own source-state eligibility,
   conditionality when explicitly enforced, allowed effects, and exact writer
   facts they state.
4. Only top-level `validate-pre-pr-readback` entered through `__main__.py` and
   `main()`, without `expected_manifest`, under its actual lock after completed
   recovery, may own post-write live-acceptance facts where material.
   `expected_manifest` validation and direct imported calls are projection or
   non-decisional provenance; they do not establish live acceptance and do not
   prevent `None` unless an exact active target assertion or observed acting
   context directly makes their semantics a required comparison fact.
5. `tools/wu-session-migration/README.md` owns detailed human command forms and
   described transition semantics. It cannot override executable admission.
6. Applicable spans in `agents/implementation-pipeline-orchestrator.md`,
   `workflows/implementation-pipeline.md`, and
   `agents/wu-session-resumer.md`, plus their applicable optimized contract
   fields, own caller partition, progression, and caller-owned closure while
   preserving the sole Python writer.
7. One active-affirmative generic target occurrence is compared with those
   authorities only when it asserts or strongly implies applicable completeness.
8. Tests, snapshots, traces, reports, audits, and final diffs are corroborating
   or observational. They do not vote a member or transition into authority.

## Comparison-authority source domain

`comparison_authority_source_domain` is the closed, identity-bound registry of
only the source spans needed to decide operation membership and conditional
wiring for the selected target. Its role schema is fixed before extraction:

- declaration spans for `RUNTIME_OPERATIONS`;
- `__main__.py`, parser, and top-level `main()` spans establishing detailed CLI
  reachability;
- exact operation/request and operation-specific validation spans;
- successful transaction-path spans;
- detailed README command and transition-semantics spans;
- top-level CLI-only live-readback spans where live acceptance is material; and
- applicable implementation/resumer caller, lifecycle-partition, progression,
  and `sole_writer` authority spans.

The domain record contains the common repository identity, this specification
as `domain_authority`, exact authorization evidence, canonical source path and
span identities, required role for each span, raw grammar version, and closure
rule. Source readability or recognized semantics cannot add or remove a member.
If the selected target or applicable transition requires a fact from an exact
observed acting context, that identity-bound context and required fact are named
in the domain before extraction; it is not discovered by an all-capability scan.

For each admitted span, `comparison_authority_source_coverage` maps every code
point to one raw leaf occurrence or explicit grammar boundary before semantic
extraction. `comparison_authority_raw_occurrence_inventory` retains raw text,
source order, parent/container links, exact span and content identity, and role.
Every occurrence receives exactly one disposition:

- `admitted-support-fact`
- `admitted-transition-fact`
- `admitted-authority-constraint`
- `non-decisional-provenance`
- `conflict`
- `unsupported-syntax-adapter-obligation`

`non-decisional-provenance` requires the exact reason the occurrence supplies no
required comparison fact. It remains losslessly present but creates no finding
and does not prevent `None`. `conflict` and adapter obligation are
comparison-blocking only when the occurrence purports to supply a required fact.
There is no source disposition based on majority vote or silent omission.

The bounded-domain equalities are:

`comparison_authority_domain_span_ids == comparison_authority_source_coverage_span_ids`

`comparison_authority_source_code_points == comparison_authority_raw_occurrence_code_points + comparison_authority_grammar_boundary_code_points`

`comparison_authority_raw_occurrence_ids == comparison_authority_disposition_occurrence_ids`

`admitted_support_fact_occurrence_ids == completed_support_fact_occurrence_ids`

`admitted_transition_fact_occurrence_ids == completed_transition_fact_occurrence_ids`

Each ID occurs exactly once on its completed or disposition side. The equality
does not range over wake/scheduler actors, generic helpers, alternate namespaces,
rollback, recovery, cleanup, or every source capable of affecting or judging
manifest/index state. Their absence from this bounded domain is not evidence of
their runtime absence.

`authority_constraint_inventory` preserves an admitted occurrence that owns
only a bounded invocation, caller, side-effect, writer, or readback constraint.
It contributes only explicitly asserted fields. Every asserted field is compared
with the assembled authority fact it constrains; unstated fields are not
borrowed. Explicit inequality is a conflict. The constraint never becomes a
complete transition by decorating a separately discovered occurrence.

## Per-member executable support

Every canonical declaration receives one deterministic `operation_support`
record containing:

- `operation`
- `declaration_occurrence_ids`
- `parser_exposure`
- `main_reachability`
- `command_request_equality`
- `closed_request_acceptance`
- `projection_or_handler_path`
- `transaction_completion_evidence`
- `detailed_command_contract`
- `applicable_caller_authority`
- `support_fact_occurrence_ids`
- `support_state`, one of `supported`, `conflict`, or `unresolved`
- `evidence_paths`

`supported` means only that the detailed human command
`python3 tools/wu-session-migration <operation> --request <path>` enters through
`__main__.py`, is parser-exposed, reaches top-level `main()`, closes exact
operation/request validation, reaches its operation-specific projection or
handler, and exposes success only after the transaction path returns, with
detailed command semantics and applicable caller authority aligned. It makes no
global namespace, helper, recovery, availability, latency, throughput, scale,
or bounded-cost claim.

Importable helper modes do not establish this detailed CLI support and do not
borrow `main()` antecedents. Their latent presence does not change
`support_state` and does not prevent `None`. If exact observed acting-context
evidence directly asserts a required support fact from such a mode, that fact is
either reconciled under its exact authority or becomes a comparison-blocking
conflict; the mode is never silently promoted into CLI support.

At the revision inspected for ACR-403, `RUNTIME_OPERATIONS` declares these eight
point-in-time members:

- `cold-start-disposition-bind`
- `phase0-init`
- `phase0-reresolve`
- `phase3-bind`
- `phase7-upsert`
- `phase9-update`
- `resumer-close`
- `resumer-update`

A future detector must extract the revision-local set and complete one support
record per member. This list is review evidence, not immutable detector policy.

## Claim taxonomy

Classification occurs only after target identity and active-affirmative status
resolve. `claim_kind` is the structured record:

```yaml
claim_kind:
  claim_completeness: exact | complete-implied | delegated | partial-example
  command_domain: runtime-only | non-runtime-only | mixed
  lifecycle_sequence_completeness: edge-membership | transition-semantics | not-claimed
```

Each dimension is orthogonal and retains the exact context supporting it.

| `claim_completeness` | Meaning and disposition |
|---|---|
| `exact` | Explicitly exact, exhaustive, or complete in resolved scope. Compare every applicable fact in the dimensions it claims complete. |
| `complete-implied` | Wording and structure strongly present completeness without an explicit token. Compare while retaining the inference context. |
| `delegated` | Exact membership or sequence semantics are unambiguously delegated to applicable authority without an exhaustive restatement. Non-fire unless surrounding active-affirmative context independently claims completeness. |
| `partial-example` | Explicit example, selected case, illustration, or partial list. Non-fire unless surrounding active-affirmative context independently implies completeness. |

| `command_domain` | Meaning and disposition |
|---|---|
| `runtime-only` | The complete claim's recognized commands are runtime operations or exact unsupported operation-shaped commands. Compare runtime membership. |
| `non-runtime-only` | The claim contains only parser-authorized support or identity-bound non-operation commands. Membership is not applicable. |
| `mixed` | Runtime/unsupported-operation occurrences and authorized support/non-operation commands coexist. Compare only the runtime side and preserve every other command. |

| `lifecycle_sequence_completeness` | Meaning and disposition |
|---|---|
| `edge-membership` | The sequence claims the set and order of named lifecycle edges, but not complete transition semantics. A uniquely matching operation/order assertion may establish that one edge is named. It cannot establish condition, conditionality, effects, writer, caller, or readback semantics. |
| `transition-semantics` | The sequence claims complete transition semantics. Every applicable conditional edge must explicitly assert or validly delegate its condition and conditionality. Other fields are required only when the claim expressly includes those semantic dimensions. |
| `not-claimed` | The target makes no complete sequence claim, including membership-only catalogs. Wiring comparison is not applicable. |

Ambiguous activation, polarity, completeness, command domain, lifecycle-sequence
completeness, or scope is fail-closed. The ambiguous dimension is `null`, exact
context remains in evidence, and neither drift nor `None` is permitted until it
resolves. Operation tokens or canonical-name matches cannot coerce a value.

`claim_scope` is `repository-global`, `named-domain`, `selected-cohort`,
`occurrence-only`, or `ambiguous`. Membership applicability is independently
`applicable`, `not-applicable`, or `ambiguous`. A selected cohort may omit a
transition only when identity-bound authority proves it inapplicable. One
sampled WU's non-occurrence cannot narrow a complete global claim.

## Membership comparison contract

For an active-affirmative, membership-applicable `exact` or `complete-implied`
claim whose command domain is `runtime-only` or `mixed`:

- `canonical_operations` is the unique set extracted from revision-local
  `RUNTIME_OPERATIONS`.
- `applicable_canonical_operations` is the identity-bound subset assigned to the
  resolved caller, lifecycle domain, or cohort. A global claim uses the full set.
- `catalog_operations` is the unique set of exact runtime-member and exact
  unsupported-operation tokens interpreted from the complete target span.
- `missing_operations = applicable_canonical_operations - catalog_operations`.
- `extra_operations = catalog_operations - applicable_canonical_operations`.
- Resolved collections are deterministically sorted. Empty lists mean resolved
  empty sets; unavailable collections are `null`.
- Set ordering differences alone do not fire.

### Target command and shorthand grammar

Before command recognition, `target_presentation_source_coverage` maps every
code point of `resolved_catalog_bearing_source_span` to one presentation
candidate or exact grammar boundary. Every list item, code span, fenced-code
content span, command parent, operation-token child, and bounded residual prose
fragment receives one injective source occurrence and exactly one disposition.

The repository-native bounded shorthand is available only inside an admitted
operation-catalog claim:

`<exact-runtime-operation> --request <path>`

`<exact-runtime-operation>` matches
`[a-z0-9]+(?:-[a-z0-9]+)+`; each shown space is one ASCII space;
`--request` and `<path>` are exact literals; no leading, trailing, or extra
operand is allowed. The complete code span is one command parent. Exactly one
child spans the operation token, and the exact ` --request <path>` suffix remains
parent evidence. Recognition is syntactic and does not consult
`RUNTIME_OPERATIONS`. A valid unknown token remains
`unsupported-operation` and participates as an exact extra.

An admitted command-catalog claim may contain a bare code-span command matching
`[a-z][a-z0-9]*(?:-[a-z0-9]+)*`. Parser and detailed-command authority then
classify it as `runtime-member`, `authorized-support-command`,
`unsupported-operation`, `authorized-non-operation`, or `ambiguous`.
`capture-evidence`, `dry-run`, `apply`, and `validate-pre-pr-readback` are
support-command examples, not runtime extras. In a mixed claim they remain valid
content and cannot hide a missing runtime operation.

Wrong options, malformed or different operands, missing or extra operands,
unclosed delimiters, unsupported punctuation, case folding, Unicode folding,
underscore/hyphen rewriting, whitespace rewriting, and unfamiliar syntax are
ambiguous rather than normalized. Raw commands, suffixes, token children, and
source spans remain preserved.

Membership comparison requires these exact equalities:

`target_presentation_candidate_ids == target_presentation_disposition_candidate_ids`

`recognized_command_candidate_ids == raw_command_occurrence_source_candidate_ids`

`raw_command_occurrence_ids == command_occurrence_disposition_occurrence_ids`

`runtime_or_unsupported_token_child_ids == raw_catalog_operation_source_candidate_ids`

`raw_catalog_operation_occurrence_ids == catalog_operation_interpretation_occurrence_ids`

`catalog_operation_interpretation_occurrence_ids == interpreted_operation_occurrence_ids`

No canonical-name-seeded recognizer may define or narrow the raw target domain.

For the point-in-time `Exact operations are` target in
`conventions/wu-session-lifecycle.md`, the seven current shorthand occurrences
map to exact runtime tokens, `missing_operations` contains
`phase0-reresolve`, and `extra_operations` is empty, subject to all identity,
support, activation, classification, and accounting gates. This is a
specification-level expected mapping, not executed detector evidence.

## Lossless typed transition assembly

Wiring is independent from membership. An operation token in a membership list
does not establish a lifecycle edge, and a membership-only claim has
`lifecycle_sequence_completeness: not-claimed`.

`transition_authority_fact_inventory` contains every admitted typed authority
fact occurrence. Each fact record preserves:

- `source_occurrence_id`
- exact source identity, span, raw text, and content identity
- `source_authority_role`
- structured `transition_assembly_key`
- `owned_fields`, an explicit set
- values only for those owned fields
- applicability and evidence paths

`transition_assembly_key` is a structured identity over the common repository,
exact operation, applicable lifecycle partition, and identity-bound edge key
established by the admitted sources. It contains no delimiter-joined string and
no field value invented from another occurrence. If complementary sources cannot
be joined to one key without guessing, the assembly is unresolved.

The required assembled transition fields are:

- `operation`
- `source_conditions`
- `predecessor_or_order`
- `destination_or_successor`
- `conditional`
- `owning_caller_or_domain`
- `sole_writer`
- `effects`
- `readback_authority`
- `readback_mode`

Every admitted authority occurrence contributes only fields its source owns.
The assembler preserves every contributing occurrence and source identity. For
each required field it requires exactly one authoritative value. Two sources
claiming ownership of the same field are `multiply-owned-field` even when their
values happen to be equal; unequal values are `authority-value-conflict`.
Corroborating or constraining occurrences remain separate records and cannot
become second owners. Missing values are `missing-authoritative-field`. There is
no majority vote, first-source choice, unstated default, field borrowing, or
source erasure.

Each completed `transition_assembly` contains the assembly key, every source
fact ID, an ownership map from each required field to exactly one source fact,
all assembled values, all constraints and their comparisons, and the resulting
structured `transition_id`. `transition_id` is built from all assembled material
fields using typed structural equality. Canonical transition candidates are
these assembled results, never impossible complete records required from one
source occurrence.

Source-fact completion and transition-assembly completion close independently:

`admitted_transition_fact_occurrence_ids == completed_transition_fact_occurrence_ids`

`admitted_transition_assembly_keys == completed_transition_assembly_keys`

`completed_transition_ids == canonical_transition_ids`

Every applicable canonical transition then receives one target comparison:

`applicable_transition_ids == completed_transition_comparison_ids`

A missing fact disposition cannot be hidden by a completed assembly, and an
admitted assembly cannot be hidden by complete source-fact accounting.
`enumeration_complete` is true only when the bounded comparison-authority source
coverage, occurrence dispositions, authority constraints, support facts,
transition facts, assemblies, applicability, and all four equalities close with
no required comparison conflict.

For the known recurrence, one assembled transition has:

- `operation`: `phase0-reresolve`
- `source_conditions`: eligible existing open pre-PR, pre-Phase-3 session with
  policy identities requiring re-resolution
- `predecessor_or_order`: after eligible Phase 0 contract/topology resolution
  and before `phase3-bind`
- `destination_or_successor`: caller-owned closed pre-PR readback, then later
  `phase3-bind` composition
- `conditional`: `true`
- `owning_caller_or_domain`: implementation pipeline workflow/operator partition
- `sole_writer`: `tools/wu-session-migration/wu_session_migration.py`
- `effects`: manifest-only change, no active row, with cold-start disposition and
  phase history preserved
- `readback_authority`: live-storage CLI readback authority
- `readback_mode`: `live-storage-cli`

The executable validator, detailed README, CLI readback, and implementation
caller sources contribute complementary fields to this assembly. No one source
is required to restate the complete record.

## Target transition accounting and discharge

Before canonical matching, the mapper builds a lossless
`target_transition_occurrence_inventory` over the complete sequence-bearing
source span. It preserves every list item, operation wording, condition,
conditionality, predecessor/order, destination, effect, caller, writer,
readback, delegation, grouped/alternative construct, and residual occurrence
with exact source identity and span. Every occurrence receives exactly one
disposition: `admitted-target-assertion`, `authorized-non-transition`,
`non-fire-context`, or `ambiguous/unsupported`.

Each admitted assertion has a `claimed_fields` presence map for all assembled
transition fields. It interprets only fields present in the target. An absent
field is `unasserted`; a purported but uninterpretable field is ambiguous and
comparison-blocking. Explicit inequality is never converted into absence.

Target accounting requires:

`target_transition_occurrence_ids == target_transition_disposition_occurrence_ids`

`admitted_target_assertion_ids == completed_target_assertion_ids`

`applicable_transition_ids == completed_transition_comparison_ids`

### Lifecycle-sequence completeness oracle

For `edge-membership`, a uniquely matching active-affirmative operation and
order assertion can establish only that one edge is named. Its result is
`included` for edge membership, with condition, conditionality, effects, caller,
writer, and readback explicitly `not-claimed-by-this-dimension`. It may not be
reported as complete transition semantics.

For `transition-semantics`, every applicable conditional edge must explicitly
assert or validly delegate both `source_conditions` and `conditional`. If the
complete lossless target inventory contains no required condition or
conditionality assertion, treatment is `omitted`. If wording purports to supply
them but cannot be interpreted, treatment is `indeterminate`. If an asserted
value is unequal, treatment is `contradicted`. If both values are equal, or an
unambiguous identity-bound delegation covers them, that semantic obligation is
`included` or `delegated`.

Generic prose does not have to restate unrelated `effects`,
`owning_caller_or_domain`, `sole_writer`, `readback_authority`, or
`readback_mode` merely to make an edge-membership-complete sequence. Those fields
remain exact in canonical authority and are compared when the target asserts
them. They become required target assertions only when the target expressly
claims semantic completeness for those dimensions. Thus exact `sole_writer` and
CLI-only live readback are never lost, defaulted, or imposed on a claim that did
not promise to restate them.

### Target-discharge cardinality oracle

One target assertion may mark at most one materially distinct canonical
transition `included`. A single assertion may discharge multiple transitions
only when the target explicitly contains an identity-bound grouped or
alternative construct whose group occurrence:

- has one exact group identity and source span;
- names or uniquely identifies every member transition;
- preserves every alternative/member occurrence;
- has a completed member-to-canonical witness for every discharged transition;
  and
- proves group member IDs equal the discharged canonical transition IDs.

If two or more canonical transition IDs remain compatible only because the
target leaves distinguishing fields unasserted, the mapping is
`target-discharge-ambiguous`. The assertion marks none of them included. The
affected mapping is non-clean, or additional unmatched transitions remain
`omitted` when the target's complete inventory and dimension make omission
decidable. The evaluator may not silently mark all compatible transitions
included, choose one by source order, or use majority vote.

Every assertion-to-transition witness records asserted and canonical values,
per-field `equal`, `unequal`, `unasserted`, or `not-required-by-dimension`, the
sequence-completeness dimension, candidate transition IDs, unique or grouped
discharge decision, and exact evidence. `observed_treatment` is one of
`included`, `delegated`, `omitted`, `contradicted`, `not-applicable`, or
`indeterminate`.

The ticket-required `wiring_transition` is an aggregate record containing:

- `evaluated_repository_identity`
- `target_claim_identity`
- `lifecycle_sequence_completeness`
- `comparison_authority_source_domain`
- `transition_authority_fact_inventory`
- `transition_assemblies`
- `canonical_transition_ids`
- `applicable_transition_ids`
- `target_transition_occurrence_inventory`
- `target_transition_occurrence_dispositions`
- `target_transition_assertions`
- `target_assertion_to_canonical_transition_witnesses`
- `target_discharge_records`
- `transition_comparisons`
- `omitted_transition_ids`
- `contradicted_transition_ids`
- `indeterminate_transition_ids`
- `enumeration_complete`
- `evidence_paths`

For the current `Manifest storage` target, the absence of
`phase0-reresolve` operation/order yields an omitted edge for an
edge-membership-complete sequence. If a neighboring transition-semantics-complete
sequence names `phase0-reresolve` in the right order but omits its eligibility
condition or conditionality, its semantic treatment is also omitted rather than
included. This preserves the named current missing-operation case and the
round-seven missing-condition neighbor.

## Unwanted behaviors

The two documentation behaviors are independent:

### Operation-membership drift

An active-affirmative generic claim with `claim_completeness` `exact` or
`complete-implied`, command domain `runtime-only` or `mixed`, and applicable
membership presents a complete operation inventory, but one or both of
`missing_operations` and `extra_operations` is non-empty after identity,
bounded comparison-authority closure, support, activation, classification,
target accounting, and set comparison complete.

### Conditional-wiring drift

An active-affirmative generic lifecycle claim with `claim_completeness` `exact`
or `complete-implied` and lifecycle-sequence completeness `edge-membership` or
`transition-semantics` omits or contradicts an applicable canonical transition
in the dimension it claims complete. A transition-semantics-complete conditional
edge also drifts when condition or conditionality is absent after complete target
accounting. Indeterminate authority, assembly, target interpretation, or
discharge is an evidence gap, not drift and not `None`.

These are documentation-contract drift behaviors. They are not runtime writer,
parser, request-validation, transaction, scheduler, recovery, namespace,
availability, protected-state, merge-verification, or external-action findings.

## Non-fire cases

A future `None` follows one of two closed paths:

- A classification non-fire requires exact identity and target admission,
  lossless context accounting, resolved activation and polarity, and every fact
  needed for its specific delegated, partial, non-runtime, non-active, negative,
  scoped-inapplicable, or membership-only disposition. It does not require
  unrelated operation support or transition assembly after that disposition has
  made those comparisons inapplicable.
- An active complete-claim comparison non-fire additionally requires resolved
  scope and applicability, all bounded source and target accounting equalities,
  aligned per-member support, complete typed transition assembly for each
  applicable wiring dimension, and complete unique/group discharge.

Optional adjacent provenance is not a prerequisite on either path.

The named behavior does not fire when:

- Exact membership or sequence semantics are unambiguously delegated without an
  exhaustive restatement.
- A list is clearly partial, illustrative, selected, or example-only and no
  active-affirmative surrounding context independently implies completeness.
- A non-runtime-only claim lists support commands such as `capture-evidence`,
  `dry-run`, `apply`, or `validate-pre-pr-readback` and makes no runtime
  membership claim.
- A mixed claim preserves support/non-operation commands while its runtime side
  has every applicable member and no unsupported extra.
- A membership-only claim differs only in ordering because membership authority
  is a set.
- A membership-only claim has `lifecycle_sequence_completeness: not-claimed`, so
  conditional wiring is not applicable.
- An edge-membership-complete sequence uniquely names every applicable edge in
  order. This proves only edge membership and does not claim complete transition
  semantics.
- A transition-semantics-complete sequence includes or validly delegates every
  applicable conditional edge's condition and conditionality, and every other
  semantic dimension it expressly claims complete compares equal.
- An explicit identity-bound grouped/alternative construct covers every member
  it discharges.
- A lifecycle-partitioned caller omits operations or transitions it does not own
  and its identity-bound applicable subsets resolve accordingly.
- Historical, quoted, proposal-only, fixture, and negative-example occurrences
  receive their explicit non-fire activation/polarity disposition and are not
  active assertions.
- A selected ineligible cohort omits a transition that identity-bound authority
  proves inapplicable, or occurrence-only evidence makes no completeness claim.
- Wake/scheduler observers, generic helpers, alternate namespaces, rollback,
  recovery, cleanup, or other latent capabilities exist outside the required
  comparison facts. Their presence is not this eval's unwanted behavior.

Incomplete required comparison evidence is not a non-fire. Optional adjacent
provenance may remain unavailable without preventing `None`; an exact observed
acting-context conflict blocks only the required comparison fact it directly
supplies or contradicts.

No `None` result says that another target, the document, repository, runtime,
merge, or external state is clean.

## Evidence-state contract

| `evidence_state` | Minimum evidence | Permitted decision behavior |
|---|---|---|
| `complete` | Common identity and target resolve. Either a classification non-fire closes every fact required for that exact disposition, or an active-affirmative complete claim closes classification, scope, applicability, target command/transition coverage, bounded comparison-authority coverage, per-member support, transition facts, typed assemblies, field ownership, and unique/group discharge for every applicable dimension. | Emit drift when present or `None` for the closed, sufficiently evidenced path. Inapplicable comparison domains are not required merely to make an explicit non-fire clean. |
| `degraded` | Every fact required for the selected comparison resolves, but optional trace, report, audit, final-diff, or non-decisional provenance is unavailable. | A direct mismatch may emit reduced-confidence drift. `None` is permitted because optional adjacent loss is not a comparison fact; name it in `missing_evidence_roles` or `residual_uncertainty` without creating a failure obligation. |
| `evidence-gap` | A required source role, raw occurrence disposition, support fact, transition fact, authoritative field, assembly, target assertion, classification, activation/polarity fact, scope, applicability, or discharge witness is unavailable or uninterpretable. | Emit a cause-preserving `LOW` gap finding or runner indeterminate result. Never assert the affected drift axis, repair from it, or use `None`. |
| `identity-conflict` | Required evidence has mixed, unbound, unverifiable, absent-at-identity, or currentness-mismatched identity. | Preserve every identity and stop dependent comparison. Never use `None`. |
| `selector-invalid` | Target path/anchor is noncanonical, escaping, absent, or non-unique. | Preserve attempted selector and resolutions; do not classify, compare, repair, or use `None`. |
| `activation-polarity-indeterminate` | Exact context cannot distinguish active/historical/quoted/proposal/fixture use or affirmative/negative polarity. | Preserve every context occurrence and fail closed. Do not convert ambiguity to active or to a non-fire `None`. |
| `claim-classification-indeterminate` | Any required completeness, command-domain, lifecycle-sequence, scope, or membership-applicability dimension is ambiguous. | Preserve independently resolved dimensions and exact context. Do not compare or use `None`. |
| `authority-conflict` | Required declaration, support, transition fact ownership/value, exact `sole_writer`, CLI-only readback, caller/progression, constraint, or assembly fact conflicts. | Preserve every source occurrence and conflict. Never vote, default, erase, repair the target, or use `None` for the dependent axis. |
| `target-discharge-indeterminate` | One assertion is compatible with multiple materially distinct transitions without an explicit complete group/alternative construct, or group membership is incomplete. | Mark none silently included. Preserve candidates and use a non-clean mapping or decidable omissions; never use `None` for the affected wiring axis. |
| `lifecycle-prohibited` | Runnable evaluation is requested while lifecycle remains `WRITE`. | Stop without execution. Specification presence is not `None` or a detector result. |

`authority_state` is `aligned`, `conflict`, or `unresolved`, scoped only to
facts required for this exact comparison. It does not describe all runtime
actors or capabilities.

## Failure obligations

`failure_obligations` is a deterministic injective list for non-clean required
comparison facts. Every record contains:

- `obligation_identity`, structured from `evidence_role`, `source_identity`,
  `normalized_cause`, and occurrence
- `evidence_role`
- `source_identity`
- `normalized_cause`
- `occurrence`
- `affected_axis`
- `required_comparison_fact`
- `original_error`, when applicable
- `recovery_disposition`: `retry`, `repair`, `reconcile`, `escalate`, or
  `terminate`, advisory at `WRITE`
- `recovery_owner`, advisory at `WRITE`
- `ordered_next_actions`
- `terminal_condition`, proposed rather than proved at `WRITE`

Every obligation must identify the exact required comparison fact it blocks.
Latent or adjacent capabilities with no such fact do not receive failure
obligations; they remain non-decisional provenance or residual uncertainty.
Repeated causes remain distinct occurrences. A derived `failure_cause` list may
summarize unique causes but cannot replace, close, or authorize an obligation.

For a pure drift finding or `None`, `failure_obligations` and `failure_cause` are
empty. Every non-clean required state has at least one obligation. One blocked
axis does not erase a completed independent axis.

At `WRITE`, routes and terminal conditions are descriptive only. A fresh result
does not close a prior obligation, and no retry, document repair,
reconciliation, escalation, lifecycle transition, or runtime action is
authorized. Later rollout work must bind acting authority, authorization,
attempt lineage, and durable closure evidence before enforcing any action.

Cause-specific obligations include, where applicable:

- repository and target identity causes named above;
- `ambiguous-activation`, `ambiguous-polarity`,
  `ambiguous-claim-completeness`, `ambiguous-command-domain`,
  `ambiguous-lifecycle-sequence-completeness`, `ambiguous-scope`, and
  `ambiguous-membership-applicability`;
- `comparison-authority-source-coverage-mismatch` and
  `comparison-authority-occurrence-accounting-mismatch`;
- `support-fact-comparison-mismatch`;
- `transition-fact-accounting-mismatch`, `missing-authoritative-field`,
  `multiply-owned-field`, `authority-value-conflict`, and
  `transition-assembly-mismatch`;
- `target-presentation-accounting-mismatch`,
  `command-occurrence-accounting-mismatch`, and
  `catalog-operation-token-ambiguous`;
- `target-transition-assertion-ambiguous`,
  `target-transition-accounting-mismatch`,
  `target-discharge-ambiguous`, and `target-group-coverage-mismatch`;
- `unresolved-source-or-adapter-attribution`, `unsupported-adapter`, and
  `lifecycle-prohibited-execution`.

At `WRITE`, parser or adapter failure remains
`unresolved-source-or-adapter-attribution`; the failing adapter cannot assign
source blame or terminal source invalidity to itself.

## Finding contract

Every future behavior or supported evidence-gap finding preserves the six fields
from `conventions/evals.md` exactly:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Every finding also contains the twelve ticket-required extension fields exactly:

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

It also contains these comparison extensions:

- `evaluated_repository_identity`
- `target_claim_identity`
- `attempted_target_selector`
- `target_context_source_span`
- `target_context_occurrence_inventory`
- `target_activation`
- `target_polarity`
- `target_activation_polarity`
- `claim_completeness`
- `command_domain`
- `lifecycle_sequence_completeness`
- `claim_scope`
- `membership_applicability`
- `applicable_canonical_operations`
- `target_presentation_source_coverage`
- `target_presentation_candidate_inventory`
- `target_presentation_candidate_dispositions`
- `raw_command_occurrences`
- `command_occurrence_dispositions`
- `raw_catalog_operation_occurrences`
- `catalog_operation_interpretations`
- `comparison_authority_source_domain`
- `comparison_authority_source_coverage`
- `comparison_authority_raw_occurrence_inventory`
- `comparison_authority_raw_occurrence_dispositions`
- `authority_constraint_inventory`
- `operation_support`
- `transition_authority_fact_inventory`
- `transition_assemblies`
- `target_transition_occurrence_inventory`
- `target_transition_occurrence_dispositions`
- `target_transition_assertions`
- `target_assertion_to_canonical_transition_witnesses`
- `target_discharge_records`
- `documentation_drift_outcome`
- `authority_state`
- `authority_conflicts`
- `failure_obligations`
- `failure_cause`
- `non_decisional_provenance`
- `residual_uncertainty`

No merge-verification or ACR-398 consumption field is part of the trace or
finding.

For resolved drift, `eval_id` is
`wu-session-runtime-operation-catalog-drift`, `authority_symbol` is
`RUNTIME_OPERATIONS`, all available collections are deterministic, and exact
target, activation, comparison-domain, source-fact, assembly, target assertion,
and discharge records remain present. `documentation_drift_outcome` contains
independent `operation_membership` and `conditional_wiring` values, each
`present`, `absent`, `not-applicable`, or `indeterminate`.

For a gap finding, every field remains present. Unavailable scalar, record, or
collection values are `null`; independently resolved values remain intact;
empty lists mean resolved empty sets, never unknown evidence. Exact raw source
and target occurrences remain present even when interpretation is unavailable.

Severity describes finding impact, not the ACR-403 planning risk:

- `MEDIUM`: established generic operation-catalog or conditional-wiring drift.
- `HIGH`: established transition-semantics drift whose same active target claim
  explicitly contradicts exact `sole_writer`, CLI-only live readback, or a
  required eligibility condition in a way that instructs an invalid lifecycle
  action.
- `LOW`: a distinct evidence, identity, selector, activation/polarity,
  classification, authority, assembly, target-accounting, or discharge gap.

`confidence` reflects directness and completeness. It never conceals degraded or
missing required evidence.

## Suggested action

For established membership drift, direct the target owner to include the exact
applicable supported operation tokens and remove only exact unsupported-operation
extras, or narrow/delegate the completeness claim. Preserve every authorized
support/non-operation command in a mixed claim.

For established edge-membership wiring drift, direct the owner to include the
missing applicable edge in the claimed order, explicitly group complete
alternatives, or narrow/delegate the edge inventory. For established
transition-semantics drift, direct the owner to assert or validly delegate the
required condition and conditionality and any other semantic dimension it
expressly claims complete. Do not require generic prose to restate unrelated
effects, caller, writer, or readback facts when it does not claim semantic
completeness for them.

For ambiguous multi-transition discharge, direct the target owner to identify
one transition uniquely or add an identity-bound grouped/alternative construct
that names every intended member. Never choose or include all compatible
transitions based on unasserted discriminators.

Every document action preserves runtime behavior, exact
`RUNTIME_OPERATIONS`, closed request validation, applicable caller eligibility,
exact `sole_writer`, and CLI-only live readback authority. It must not add a
writer, change runtime sequencing, authorize a helper or direct readback, infer
membership by majority, invent a transition field, default an absent target
field, erase a source occurrence, repair from an indeterminate comparison, or
claim runtime safety.

For a required evidence gap, restore or reconcile the named comparison fact or
repair the future adapter/spec before rerunning. Do not edit the target based on
assumptions. Non-decisional provenance and residual uncertainty may be reported
without suggesting unrelated runtime, recovery, scheduler, namespace, or merge
work through this finding.

## Consumers and supported-surface boundary

Current consumers are ACR-403 reviewers and maintainers or agents performing
separate exact-target review of complete-looking generic tool and lifecycle
claims. The supported operation surface is functional detailed CLI reachability
under the exact facts above. Direct standalone WUs using planning root `P` and
feature direct/refactoring routes using `F/routes` remain request-topology
cohorts behind the same sole writer; this specification changes neither cohort.

Future consumers may include a separately authorized detector, evidence
resolver, eval runner, advisory report reader, or caller-owned rollout. There is
no customer runtime, public API, persisted format, deployment, data migration,
session migration, cutover, or consumer opt-in introduced here.

No consumer may aggregate per-claim results into a repository result without a
separate discovery and aggregation contract.

## Step 6b and Step 6c boundary

Step 6b owns this sole repository specification and the canonical machine-local
output index at `${scratch_dir}/phase6/step6b-output-index.md`. The index maps
`TI-01` through `TI-08` to this eval identity, selected level
`particular-integration`, and each evidence application point. It creates no
runnable or test-shaped output.

Step 6c is a fresh inspection-only invocation. It consumes the indexed eval
identity/path, proposal mappings, required evidence, and caller-owned side
channel, then inspects:

- exact one-file repository scope and lifecycle `WRITE`;
- exact repository and target identity;
- active-affirmative gating with lossless context occurrence accounting;
- the repository-native shorthand and mixed command-domain handling;
- the bounded `comparison_authority_source_domain`, raw coverage, and
  exactly-once dispositions, without an all-effecting actor claim;
- per-member declaration, parser/main, request-validation, successful
  transaction, detailed-command, and applicable caller support;
- CLI-only live readback where compared;
- typed partial transition facts, n-way assembly, exact field ownership,
  admitted/completed equalities, exact `sole_writer`, and conflicts without
  majority or source erasure;
- edge-membership versus transition-semantics completeness;
- unique or explicit grouped/alternative target discharge;
- positive, non-fire, evidence-state, failure-obligation, finding, and suggested
  action contracts; and
- the external ACR-398 prerequisite wording and anti-scope.

Step 6c must reject a noncanonical/multiply resolving target, ambiguous
activation or polarity, incomplete bounded source/target coverage, a missing or
duplicate disposition, incomplete support or transition facts, missing or
multiply owned canonical fields, a one-source-complete transition requirement,
unevidenced field borrowing/defaults, source erasure, unrestricted projected
compatibility, absent required conditional semantics classified as included,
direct-import live-readback authority, support commands treated as runtime
extras, latent adjacent capability obligations used to prevent `None`, or any
eval-owned merge-verification claim.

Step 6c does not patch this file, implement or run a detector, invoke the
migration executable, add a repository path, or create behavior evidence. A
specification mismatch returns through explicit revision and fresh authoring.
One inspection cannot claim another target or repository cleanliness.

## Lifecycle notes

ACR-403 ends at `WRITE`.

- `ROLL_OUT` requires a separately authorized WU to select and implement a
  detector and extraction approach; add representative positive, activation,
  polarity, delegated, partial, mixed, edge-membership,
  transition-semantics, typed n-way assembly, missing/multiply owned field,
  unique/group discharge, identity, selector, and evidence-gap cases; prove the
  bounded source and target occurrence equalities; demonstrate CLI-only live
  readback and exact `sole_writer`; validate reports; observe advisory results;
  and review false positives and evidence drift.
- `ENFORCE` additionally requires trusted findings, a named caller and
  hookpoint, severity policy, document-repair routing, fail-closed required
  evidence behavior, and durable enforcement-readiness evidence.
- `MAINTAIN` tracks authority and target syntax, exact target selector
  uniqueness, activation/polarity context, shorthand and command-domain grammar,
  comparison-authority span coverage, per-member support, transition fact
  ownership and assembly, lifecycle-sequence completeness, target discharge,
  CLI-only readback, exact `sole_writer`, finding comparability, and lifecycle
  regression.

No detector language, parser library, fixture serialization, runner mode,
report path, CLI, CI, scheduler, cron, scan cadence, hookpoint, or enforcing
caller is selected. Rollback of this exact repository delta is deletion or
reversion of this one Markdown specification. It cannot reverse an external
action, and this eval does not claim external non-action.

## External ACR-398 prerequisite and context

ACR-398 consumption is prohibited until the external owning WU/ticket workflow
supplies its separately verified merge prerequisite. This eval neither encodes,
executes, validates, nor proves that merge or any consumption record. A local
head, open PR, repository occurrence, or this `WRITE` document is not merge
evidence under this contract.

After that external gate is satisfied, ACR-398 retains its exact two-file scope:
`tools/README.md` and `conventions/wu-session-lifecycle.md`. It also retains
direct, separate inspection of each exact target against current authority and
of its final diff. That two-file scope and direct per-target inspection are
external handoff context only. They are not trace fields, finding fields,
authority sources, adapter surfaces, detector outputs, or merge/consumption
proof produced by this eval.

The external handoff does not copy this eval into ACR-398's diff, execute it,
establish `None`, replace ACR-398's direct inspection, change runtime membership
or sequencing, or advance this eval beyond `WRITE`.

## Anti-scope

This `WRITE` artifact does not define or authorize detector code, Python or Rust
implementation, fixtures, tests, pytest imports or assertions, a one-off
verifier, a resolver, parser, source-discovery adapter, eval-runner adapter,
CLI/CI/scheduler/cron wiring, runtime behavior, writer or namespace changes,
helper or direct-live-readback adapters, rollback/recovery/cleanup execution,
global locking, availability or cost claims, protected-state mechanisms or
writes, ACR-398 edits, merge verification, consumption records, ticket actions,
estimate mutation, external-action proof, or external reconciliation.

It does not audit every runtime capability, namespace, recovery path, scheduler,
observer, caller, or actor affecting or judging manifest/index state. Its
lossless source accounting is bounded to admitted comparison-authority spans and
its lossless target accounting is bounded to the one exact claim and context.
The schemas and grammars above are specification obligations, not runnable
implementations. Lifecycle remains `WRITE`.

## References

- `conventions/evals.md`
- `tools/wu-session-migration/__main__.py`
- `tools/wu-session-migration/wu_session_migration.py`
- `tools/wu-session-migration/README.md`
- `tools/README.md`
- `conventions/wu-session-lifecycle.md`
- `agents/implementation-pipeline-orchestrator.md`
- `contracts/operators/implementation-pipeline-orchestrator.yaml`
- `workflows/implementation-pipeline.md`
- `contracts/workflows/implementation-pipeline.yaml`
- `agents/wu-session-resumer.md`
- `contracts/operators/wu-session-resumer.yaml`
- `~/projects/ai/planning/acr-403-operation-catalog-eval/proposals/acr-403-ACR-403.md`
- `~/projects/ai/planning/acr-403-operation-catalog-eval/contracts/acr-403-wu-session-runtime-operation-catalog-drift.md`
