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

The result alternatives are exactly a structured `finding` or `None`. Every
required identity, selector, target-domain, classification, authority-query,
support, assembly, accounting, applicability, delegation, discharge, parser, or
adapter failure makes its affected axis `indeterminate` and preserves a
cause-specific `LOW` gap severity and failure obligation. The finding's aggregate
severity follows the closed per-axis aggregation contract below, so an
independent established drift is not downgraded by that gap. Primary result
construction, serialization, or delivery failure instead enters the mandatory
fallback-gap contract. A future runner that cannot deliver that envelope has not
produced an eval result: it must terminate with the separate
`terminal-transport-failure` boundary defined under Failure obligations. Such a
failure is never `None`, an empty finding, or a third conceptual result
alternative.

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
| Target-source closure | One deterministic `target_source_domain` derived from either exactly one complete Markdown structural block or exactly one of the two bounded composite forms defined below in the exact target blob, before any activation, polarity, completeness, command-domain, sequence, delegation, domain, or scope classification. Every admitted component node, span, byte, and code point and every role overlay closes exactly; the governed catalog/sequence content retains its own distinct span. |
| Comparison-authority discovery | A closed `comparison_authority_discovery_domain` of complete identity-bound blobs for the bounded runtime and detailed-command roles plus implementation/resumer roles only when caller-scoped membership or wiring activates them; whole-blob deterministic queries precede and produce semantic spans. |
| Detailed CLI support | One `operation_support` record per canonical operation, keyed exactly once, covering query-derived declaration, parser and top-level `main()` reachability, closed operation/request validation, successful operation-specific transaction path, and detailed command semantics. This executable support closes repository-global membership without caller adoption. Separate caller-applicability records are required only for caller-scoped subsets and conditional wiring. |
| CLI-only live readback | Where a transition comparison materially requires post-write live acceptance, the top-level `validate-pre-pr-readback` CLI path entered through `__main__.py` and `main()` without `expected_manifest`, under its actual lock and completed recovery antecedents, is the only live-readback authority. |
| Lifecycle authority facts | Typed partial fact occurrences from operation-specific executable validators, detailed command semantics, CLI-only live readback where material, and applicable implementation/resumer caller and progression authority. Each occurrence contributes only fields it owns. |
| Transition assembly | Lossless query-to-fact n-way assembly records, per-dimension field requirements/non-applicability, exact field ownership, assembly conflicts, `canonical_transition_ids`, `applicable_transition_ids`, and independent query/completion equalities. |
| Exact target claim | Structured target identity and source domain, exact structural-block or bounded-composite component and role-overlay closure, distinct governed content span, activation and polarity, structured `claim_kind`, `target_scope_identity`, `delegate_resolution`, per-operation and per-transition applicability witnesses, command dispositions, interpreted operations, sequence assertions, assertion/group-member keys, and discharge witnesses. |
| Comparison | Deterministically sorted operation differences and aggregate `wiring_transition`, including lifecycle-sequence completeness, canonical transitions, target treatments, unique/group discharge, reverse assertion/group-member closure, omissions, contradictions, unmatched assertions, and indeterminate mappings. |
| Axis derivation | Independent `operation_membership` and `conditional_wiring` records retain axis-local outcome, evidence/authority state, established-drift or gap severity, drift fields, failure obligations, and suggested action before aggregate severity/authority/action derivation. |
| Observation provenance | `evidence_paths`; source, trace, prompt, log, report, audit, and final changed-surface paths when available. Optional provenance does not replace authority. |
| Conflict and availability | Aggregate and per-axis `evidence_state`, per-axis and aggregate `authority_state`, `authority_conflicts`, `missing_evidence_roles`, and injective `failure_obligations` for every unresolved identity, selector, target-domain, query, support, applicability, delegation, assembly, accounting, parser, adapter, or transport fact required by the selected comparison. |
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

## Exact target identity, source domain, and activation

`target_claim_identity` is the injective structured record:

- `canonical_repository_id`
- `evaluated_commit`
- `catalog_path`
- `catalog_anchor`
- `source_blob_identity`
- `resolved_source_span`
- `resolved_claim_content_span`
- `resolved_claim_content_identity`

`catalog_path` is a canonical repository-relative POSIX path naming one regular
Git blob at the evaluated commit. It has no empty, `.`, `..`, repeated,
backslash, absolute, symlink, alias, or escaping form.

`catalog_anchor` is
`{anchor_kind: exact-claim-source, anchor_text}`. `anchor_text` is the exact raw
source of one complete admitted claim envelope: one complete structural block or
one complete bounded composite defined below. It is not a heading-only locator,
substring, abbreviation, ordinal, normalized alternate spelling, or a fragment
whose semantics depend on a node outside that envelope. Path, anchor, blob,
envelope span, component spans, content span, parse-node identities, and content
identities remain separate fields and are never delimiter-concatenated.

Before activation or any other semantic classification, the mapper derives one
`target_source_domain` by parsing the exact target blob under the trace-declared
`markdown_structural_grammar_version`. The record contains:

- `evaluated_repository_identity`
- `catalog_path` and `source_blob_identity`
- `catalog_anchor` and every raw anchor resolution
- `markdown_structural_grammar_version`
- `target_envelope_kind`: `complete-structural-block`,
  `heading-governed-composite`, or `introduction-content-composite`
- every `target_component_node_id`, structural block kind, parent/child edge,
  complete byte range, complete code-point range, raw source, and content
  identity
- the envelope's complete byte/code-point range, raw source, and content identity
- one distinct `target_claim_content_source_span` and governed content identity,
  even when the complete structural-block form makes that span equal to the
  envelope range
- the complete descendant parse-node inventory and parent/child edges wholly
  inside every component
- `target_source_domain_state`: `complete`, `zero-match`, `multi-match`,
  `partial-node`, `parse-ambiguous`, `unparsed`, `multiple-governors`,
  `multiple-content-blocks`, `intervening-unowned-block`, or
  `unbounded-context`

The first and default form is exactly one complete structural block node. A
paragraph block and a complete list-item block with its descendants are
supported kinds, as are a complete list container, complete table, and complete
fenced-code block. The current `Exact operations are` paragraph and `Manifest
storage` list item therefore remain representable, while inline and fenced
command catalogs have explicit block forms.

Exactly two additional composite forms are permitted:

1. A `heading-governed-composite` contains one complete heading and every
   contiguous following descendant block through, but excluding, the next
   heading of equal or higher level. Those admitted descendants must contain
   exactly one unambiguous catalog/sequence-bearing governed block, which is the
   distinct claim content span. A lower-level heading and its descendants remain
   bounded admitted context; a second possible governor or second possible
   catalog/sequence-bearing block is non-clean.
2. An `introduction-content-composite` contains one complete introductory
   paragraph whose final syntactic sentence or clause ends in an unambiguous
   catalog/sequence lead-in, plus exactly the immediately following complete
   list, table, paragraph, or fenced block. The following block is the distinct
   claim content span. Any intervening block, multiple possible introductory
   governors, multiple possible content blocks, or context beyond those two
   components is non-clean.

The anchor equals the complete contiguous byte/code-point range of the selected
form. It may never select only inline content, a heading without its bounded
governed domain, a lead-in without its immediately governed block, partial
nodes, or unbounded context. The mapper may not widen, trim, merge, skip an
intervening block, or borrow context outside the admitted components to repair
selection. `multiple-governors`, `multiple-content-blocks`,
`intervening-unowned-block`, and `unbounded-context` are structured target-domain
gaps.

Component accounting is an injective exact partition. Empty component sets are
allowed only where the envelope kind makes that component structurally
inapplicable:

`target_source_domain_component_node_ids == target_heading_component_node_ids + target_introduction_component_node_ids + target_governed_content_component_node_ids + target_other_admitted_context_component_node_ids`

`target_source_domain_code_point_ids == target_heading_component_code_point_ids + target_introduction_component_code_point_ids + target_governed_content_component_code_point_ids + target_other_admitted_context_code_point_ids`

`target_source_domain_byte_ids == target_heading_component_byte_ids + target_introduction_component_byte_ids + target_governed_content_component_byte_ids + target_other_admitted_context_byte_ids`

Each `+` expression is a disjoint union, every component and source position
appears exactly once, and component byte/code-point source-map equality closes.
The mapper then builds role-specific lossless overlays for `context`, `heading`,
`introduction`, `governed-content`, `presentation`, `command`, `transition`,
`delegation`, `activation`, `polarity`, `completeness`, `domain`, and `scope`.
Activation, polarity, completeness, delegation, and scope may use only admitted
component nodes; command and transition assertion interpretation may use only the
distinct governed content span. Each overlay retains every admitted parse node
and source position, assigning non-semantic text an explicit
grammar-boundary/residual or structurally-inapplicable disposition rather than
omitting it. For every role `r` in that closed set:

`target_source_domain_parse_node_ids == target_r_covered_parse_node_ids`

`target_source_domain_code_point_ids == target_r_semantic_occurrence_code_point_ids + target_r_boundary_or_residual_code_point_ids`

`target_source_domain_byte_ids == target_r_semantic_occurrence_byte_ids + target_r_boundary_or_residual_byte_ids`

`target_r_occurrence_ids == target_r_disposition_occurrence_ids`

Each `+` expression is a disjoint exact partition, and each ID occurs exactly
once on the right. Byte/code-point source-map equality must also close. Any
component-union, parser, source-map, node, byte, code-point, or disposition
inequality yields `target-source-domain-incomplete`. Required semantics outside
the admitted envelope yield `required-semantics-outside-target-domain`. Both
produce a cause-preserving gap finding and prohibit classification, comparison,
repair, and `None`.

The retained `target_context_source_span` equals the complete envelope byte and
code-point range from `target_source_domain`; it is not a second selectable span.
`target_claim_content_source_span` remains a separate identity-bound field for
the governed catalog/sequence block and is never enlarged by heading,
introduction, or other bounded context. Presentation, command, transition,
delegation, classification, domain, and scope records are overlays of admitted
components, not independently admitted fragments.

The target has two independently evidenced classifications:

| Field | Values and meaning |
|---|---|
| `target_activation` | `active`, `historical`, `quoted`, `proposal-only`, `fixture`, or `ambiguous`. The complete admitted envelope must establish the source use without inference outside its component nodes. |
| `target_polarity` | `affirmative`, `negative-example`, or `ambiguous`. Negative examples describe text that must not be treated as current authority. |

Only a complete `target_source_domain` with
`{target_activation: active, target_polarity: affirmative}` yields
`target_activation_polarity: active-affirmative` and permits membership or
wiring comparison. Historical, quoted, proposal-only, fixture, and
negative-example occurrences receive explicit `non-fire-non-active` or
`non-fire-negative` dispositions while preserving their complete raw source and
context overlay. Ambiguous activation or polarity yields
`activation-polarity-indeterminate`; it cannot compare, drive repair, or become
`None` until the ambiguity is resolved. Token presence, completeness wording,
or a current file path cannot override the admitted envelope context or polarity.

A resolved non-active or negative disposition is itself a sufficiently evidenced
non-fire path after exact identity and every component/overlay equality closes.
It does not require operation support or transition assembly for comparisons
that its classification prevents. Only the active-affirmative path proceeds to
membership or wiring comparison.

Non-active and negative occurrences still participate in every component and
role overlay. Their non-fire disposition is not source erasure. A heading such
as `Complete runtime operations` plus one governed list can therefore activate a
complete comparison, while `Examples only:` in an admitted introductory
paragraph plus its immediately following list can resolve `partial-example` and
reach its classification non-fire when every other required equality closes.

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
6. Query-derived occurrences from the complete identity-bound
   `agents/implementation-pipeline-orchestrator.md`,
   `workflows/implementation-pipeline.md`, and
   `agents/wu-session-resumer.md` blobs, plus complete optimized-contract blobs
   only where a closed applicability query proves that they express a required
   caller fact, own caller partition, progression, and caller-owned closure while
   preserving the sole Python writer.
7. One active-affirmative generic target occurrence is compared with those
   authorities only when it asserts or strongly implies applicable completeness.
8. Tests, snapshots, traces, reports, audits, and final diffs are corroborating
   or observational. They do not vote a member or transition into authority.

## Comparison-authority discovery domain

`comparison_authority_discovery_domain` is the deterministic, identity-bound
whole-blob discovery oracle. It is fixed before semantic span selection and is
limited to these already bounded, comparison-scope-specific roles. Its core
executable-support domain always includes:

- complete `tools/wu-session-migration/wu_session_migration.py` runtime-module
  blob;
- complete `tools/wu-session-migration/__main__.py` entrypoint blob;
- complete `tools/wu-session-migration/README.md` detailed-command blob.

Its caller-authority subdomain is activated only by a caller-scoped membership
subset or conditional-wiring comparison. When activated, it includes:

- complete `workflows/implementation-pipeline.md` implementation-workflow blob;
- complete `agents/implementation-pipeline-orchestrator.md`
  implementation-operator blob;
- complete `agents/wu-session-resumer.md` resumer blob; and
- the complete blobs at
  `contracts/workflows/implementation-pipeline.yaml`,
  `contracts/operators/implementation-pipeline-orchestrator.yaml`, and
  `contracts/operators/wu-session-resumer.yaml` only when a whole-candidate
  contract applicability query proves that the contract expresses a required
  caller fact for the selected target scope.

For repository-global membership with no wiring claim, the caller-authority
subdomain has state `structurally-not-applicable`; none of its blobs or optimized
contracts is admitted, queried, or required, and their availability cannot gate
the membership axis. Every core blob and every activated caller/optimized-contract
candidate resolves from the common repository identity. An activated contract
candidate is either included as one complete blob or excluded with an identity-bound
`authority-proven-contract-inapplicable` query result. Zero/ambiguous matches,
parse failure, or inability to prove the inclusion/exclusion is an evidence gap;
no useful semantic span may decide blob admission. That gap applies only after
the caller-authority subdomain is activated and blocks only the caller-scoped
membership or wiring axis that depends on it; an independently closed
repository-global membership axis remains resolved.

Each optimized-contract candidate is itself parsed and traversed in full before
that applicability result:

`optimized_contract_candidate_blob_ids == optimized_contract_applicability_query_coverage_blob_ids`

`optimized_contract_candidate_code_point_ids == optimized_contract_query_leaf_node_code_point_ids + optimized_contract_query_grammar_boundary_code_point_ids`

The `+` expression is a disjoint exact partition. Thus an excluded contract has
an authority-proven complete-query result rather than an absence inferred from a
sampled span.

`comparison_authority_discovery_domain` records the common repository identity,
exact blob identities and complete byte/code-point ranges, parser/grammar
versions, fixed query versions, contract-candidate results, and authorization
boundary. `comparison_authority_discovery_coverage` traverses every parse node
and code point in every included blob before interpreting any fact:

`comparison_authority_discovery_blob_ids == comparison_authority_discovery_coverage_blob_ids`

`comparison_authority_discovery_code_point_ids == comparison_authority_raw_leaf_parse_node_code_point_ids + comparison_authority_grammar_boundary_code_point_ids`

`comparison_authority_discovery_byte_ids == comparison_authority_raw_leaf_parse_node_byte_ids + comparison_authority_grammar_boundary_byte_ids`

Each `+` expression is a disjoint exact partition. Semantic source spans are
projections of completed query occurrences and are never an input to discovery.
A stale list of previously useful spans cannot satisfy this domain.

After the declaration query extracts revision-local `canonical_operations`, the
domain runs deterministic whole-blob executable-support queries for every
canonical operation. It runs caller queries only for a caller-scoped applicable
subset or a conditional-wiring transition; repository-global membership gives
caller authority the explicit `structurally-not-applicable` disposition. The
query inventory enumerates:

- every exact operation-token occurrence;
- the declaration occurrence and parser-registration branch;
- top-level `main()` registration/routing and entrypoint reachability;
- exact operation/request validation and operation-specific validation;
- operation-specific projection/handler and successful transaction path;
- every detailed human command occurrence;
- every conditional, predecessor/order, destination/successor, effects,
  owner/writer, caller, lifecycle-partition, and progression occurrence;
- every top-level CLI live-readback occurrence where the transition/dimension
  materiality query requires live acceptance; and
- every optimized-contract caller occurrence admitted by the contract
  applicability query.

Each query occurrence preserves raw text, source order, parent/container links,
exact blob/span/content identity, query ID, operation or caller key, and source
role. It receives exactly one disposition:

- `admitted-support-fact`
- `admitted-transition-fact`
- `admitted-authority-constraint`
- `non-decisional-provenance`
- `conflict`
- `unsupported-syntax-adapter-obligation`

Unsupported syntax is retained rather than skipped. `non-decisional-provenance`
requires the exact reason the occurrence supplies no required comparison fact.
It creates no drift finding and does not prevent `None` after all applicable
query closure. A conflict or unsupported-syntax obligation blocks only the
dependent required fact. There is no majority vote, silent occurrence omission,
or canonical-name-seeded selector.

Independent query closure requires all of these exactly-once equalities:

`comparison_authority_query_occurrence_ids == comparison_authority_query_disposition_occurrence_ids`

`canonical_operation_ids == operation_support_keys`

For every canonical operation `o` and executable support role `r` required in
all comparison scopes:

`required_support_query_occurrence_ids[o, r] == completed_support_fact_query_occurrence_ids[o, r]`

For every caller-scoped operation/caller key `k` and required caller role `r`:

`required_caller_query_occurrence_ids[k, r] == completed_caller_applicability_fact_query_occurrence_ids[k, r]`

No caller-query key exists for repository-global membership. Its per-member
caller disposition is instead exactly `structurally-not-applicable`.

`discovered_transition_candidate_occurrence_ids == admitted_transition_fact_occurrence_ids + explicitly_dispositioned_transition_candidate_occurrence_ids`

`applicable_transition_query_keys == completed_transition_assembly_keys`

`applicable_transition_query_keys == completed_target_transition_comparison_or_disposition_keys`

The right side partitions every discovered transition candidate into an admitted
typed fact or an explicit `non-decisional-provenance`, `conflict`, or
`unsupported-syntax-adapter-obligation` record. Each ID/key occurs exactly once;
the sets are not merely counts. Query, selector, parse, source-map, or equality
failure emits a structured gap finding and prohibits `None`.

This whole-blob discovery remains bounded to the named comparison authorities.
It does not query wake/scheduler actors, generic helpers, alternate namespaces,
rollback, recovery, cleanup, or every source capable of affecting or judging
manifest/index state. Their exclusion is not evidence of runtime absence.

`authority_constraint_inventory` preserves a query-derived occurrence that owns
only a bounded invocation, caller, side-effect, writer, or readback constraint.
It contributes only explicitly asserted fields. Every asserted field is compared
with the assembled authority fact it constrains; unstated fields are not
borrowed. Explicit inequality is a conflict. The constraint never becomes a
complete transition by decorating a separately discovered occurrence.

## Per-member executable support

Every canonical declaration receives one deterministic `operation_support`
record containing:

- `operation_support_key`, the exact canonical operation ID
- `operation`
- `declaration_occurrence_ids`
- `required_support_query_occurrence_ids_by_role`
- `completed_support_fact_query_occurrence_ids_by_role`
- `parser_exposure`
- `main_reachability`
- `command_request_equality`
- `closed_request_acceptance`
- `projection_or_handler_path`
- `transaction_completion_evidence`
- `detailed_command_contract`
- `support_requirements_by_comparison_scope`
- `caller_authority_requirement`, either `required-by-caller-scope` or
  `structurally-not-applicable`
- `caller_applicability_record_ids`, empty for repository-global membership
- `support_fact_occurrence_ids`
- `executable_support_state`, one of `supported`, `conflict`, or `unresolved`
- `evidence_paths`

The operation-support map has exactly the revision-local canonical operation IDs
as keys, once each. For each key, every required declaration, parser, main,
validation, transaction, and command query occurrence appears exactly once in
the corresponding completed support-fact records. Caller occurrences appear
only in separately keyed caller-applicability records when the comparison scope
requires them. An absent or extra key, missing required query occurrence,
duplicated completion, or cross-operation unkeyed fact reuse is a structured
evidence gap. A generic parser or `main()` branch may yield one distinct
operation-keyed query occurrence per canonical operation, with each projection
retaining the same underlying source occurrence; that is explicit query
expansion, not fact reuse. Declaration membership alone cannot close any other
executable support role.

`supported` means only that the detailed human command
`python3 tools/wu-session-migration <operation> --request <path>` enters through
`__main__.py`, is parser-exposed, reaches top-level `main()`, closes exact
operation/request validation, reaches its operation-specific projection or
handler, and exposes success only after the transaction path returns, with
detailed command semantics aligned. This is sufficient support for one declared
member in a repository-global catalog comparison. Caller authority is
structurally non-applicable to that membership decision and cannot turn a
supported global member into an evidence gap. This state makes no workflow
adoption, automated-caller, lifecycle placement, global namespace, helper,
recovery, availability, latency, throughput, scale, or bounded-cost claim.

For a `named-domain` or `selected-cohort` membership comparison, executable
support remains necessary and the separate caller-applicability record must also
close the exact applicable/inapplicable subset. Every conditional-wiring
transition independently requires its applicable caller/lifecycle authority.
Neither use rewrites `executable_support_state`; caller conflict or absence
blocks only the caller-scoped membership or wiring fact that depends on it.

Importable helper modes do not establish this detailed CLI support and do not
borrow `main()` antecedents. Their latent presence does not change
`executable_support_state` and does not prevent `None`. If exact observed acting-context
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

Each dimension is orthogonal and retains exact admitted-envelope occurrences
supporting it.

| `claim_completeness` | Meaning and disposition |
|---|---|
| `exact` | Explicitly exact, exhaustive, or complete in resolved scope. Compare every applicable fact in the dimensions it claims complete. |
| `complete-implied` | Wording and structure strongly present completeness without an explicit token. Compare while retaining every admitted-envelope inference occurrence. |
| `delegated` | Exact membership or sequence semantics are unambiguously delegated to applicable authority without an exhaustive restatement. Non-fire only when no other occurrence in the complete active-affirmative envelope independently claims completeness and exact delegate closure succeeds. |
| `partial-example` | Explicit example, selected case, illustration, or partial list. Non-fire only when no other occurrence in the complete active-affirmative envelope independently implies completeness. |

| `command_domain` | Meaning and disposition |
|---|---|
| `runtime-only` | The complete claim's recognized commands are runtime operations or exact unsupported operation-shaped commands. Compare runtime membership. |
| `non-runtime-only` | The claim contains only parser-authorized support or identity-bound non-operation commands. Membership is not applicable. |
| `mixed` | Runtime/unsupported-operation occurrences and authorized support/non-operation commands coexist. Compare only the runtime side and preserve every other command. |

| `lifecycle_sequence_completeness` | Meaning and disposition |
|---|---|
| `edge-membership` | The sequence claims the set and order of named lifecycle edges, but not complete transition semantics. A uniquely matching operation plus predecessor/order or destination/successor assertion may establish that one edge is named. It cannot establish condition, conditionality, effects, writer, caller, or readback semantics. |
| `transition-semantics` | The sequence claims complete transition semantics. Every applicable conditional edge must explicitly assert or validly delegate its condition and conditionality. Effects, owner/caller, and writer are required when the claim expressly includes those semantic dimensions; readback authority/mode are required only where the exact transition/dimension materiality query requires them. |
| `not-claimed` | The target makes no complete sequence claim, including membership-only catalogs. Wiring comparison is not applicable. |

Ambiguous activation, polarity, completeness, command domain, lifecycle-sequence
completeness, or scope is fail-closed. The ambiguous dimension is `null`, exact
admitted-envelope evidence remains present, and neither drift nor `None` is permitted
until it resolves. Operation tokens or canonical-name matches cannot coerce a
value.

`claim_scope` is `repository-global`, `named-domain`, `selected-cohort`,
`occurrence-only`, or `ambiguous`. Membership applicability is independently
`applicable`, `not-applicable`, or `ambiguous`. A selected cohort may omit a
transition only when identity-bound authority proves it inapplicable. One
sampled WU's non-occurrence cannot narrow a complete global claim.

### Target scope, delegation, and applicability closure

Every active-affirmative target that activates membership, delegation, or
lifecycle comparison has one structured `target_scope_identity` containing:

- `target_claim_identity`
- the exact admitted-envelope scope occurrence and disposition IDs
- `claim_scope`
- exact `caller_identity`, `cohort_identity`, and `lifecycle_domain_identity`
  where the claim names them
- `global_domain_identity` when and only when the claim explicitly covers the
  repository-global supported domain
- authority-query occurrence IDs establishing each named identity
- `scope_resolution_state`: `resolved`, `missing`, `ambiguous`, `stale`,
  `sampled-only`, or `unbound`

A repository-global claim uses the explicit global domain; it cannot infer an
exclusion from one caller, cohort, WU, trace, or non-occurrence. A named-domain
or selected-cohort identity must resolve at the same repository/commit as the
target and authority. Occurrence-only and clearly partial claims may terminate
before activating a canonical comparison domain, but they may not use that
classification to make a clean statement about excluded canonical members.

Every exact delegation occurrence has one `delegate_resolution` record with the
target/source occurrence identity, exact raw delegated locator, locator kind
`canonical-path | symbol | heading | detailed-authority`, common repository and
commit, resolved canonical path/blob and symbol/heading identity, resolved
authority role, all resolution candidates, and
`delegate_resolution_state: resolved | missing | ambiguous | stale | unbound`.
`resolved` requires exactly one same-commit canonical authority named by the
admitted envelope. A nearby, historically correct, alias-only, or sampled authority cannot
close delegation.

For every canonical operation and every canonical transition in each activated
comparison domain, the trace contains exactly one applicability witness keyed
structurally by:

`{target_claim_identity, target_scope_identity, comparison_scope_identity, member_identity, caller_identity, cohort_identity, lifecycle_domain_identity}`

Each `operation_applicability_witness` or
`transition_applicability_witness` retains the exact authority query occurrence
IDs, an exact `caller_authority_disposition`, and one member disposition:
`applicable` or `authority-proven-inapplicable`. Source silence and sampled
non-occurrence are not proof.

For `repository-global` membership, every canonical operation witness binds the
declaration and completed executable-support record, uses
`caller_authority_disposition: structurally-not-applicable`, contains no caller
query occurrence, and is `applicable`. The operation partition therefore equals
the full canonical set after executable support closes. This proves catalog
membership only; it does not prove workflow adoption or an automated caller.

For `named-domain` or `selected-cohort` membership, the exact caller/cohort
authority queries are mandatory and may prove a member applicable or
inapplicable. Every transition witness likewise requires caller and lifecycle
authority because conditional wiring is caller-scoped even when its containing
catalog uses global operation membership. Closure requires disjoint exact
partitions:

`canonical_operation_ids == operation_applicability_witness_member_ids`

`canonical_operation_ids == applicable_operation_ids + authority_proven_inapplicable_operation_ids`

`canonical_transition_ids == transition_applicability_witness_member_ids`

`canonical_transition_ids == applicable_transition_ids + authority_proven_inapplicable_transition_ids`

Every member key occurs exactly once in its witness and partition. A missing,
ambiguous, stale, sampled-only, unbound, duplicate, or unequal scope, delegate,
cohort, caller, lifecycle, or authority join is a cause-preserving evidence gap,
not `None`, except that a caller join is structurally non-applicable and cannot
be queried or gate repository-global membership. A delegated non-fire
additionally requires every delegation occurrence to resolve and every
applicable canonical member to be covered by the resolved delegated authority.

## Membership comparison contract

For an active-affirmative, membership-applicable `exact` or `complete-implied`
claim whose command domain is `runtime-only` or `mixed`:

- `canonical_operations` is the unique set extracted from revision-local
  `RUNTIME_OPERATIONS`.
- `applicable_canonical_operations` is the identity-bound subset assigned to the
  resolved caller, lifecycle domain, or cohort. A repository-global claim uses
  every executable-supported canonical member, with caller authority
  structurally non-applicable.
- `catalog_operations` is the unique set of exact runtime-member and exact
  unsupported-operation tokens interpreted from the complete target source
  domain.
- `missing_operations = applicable_canonical_operations - catalog_operations`.
- `extra_operations = catalog_operations - applicable_canonical_operations`.
- Resolved collections are deterministically sorted. Empty lists mean resolved
  empty sets; unavailable collections are `null`.
- Set ordering differences alone do not fire.

### Target command and shorthand grammar

Before command recognition, the `presentation` and `command` overlays map every
parse node and code point of the complete `target_source_domain` to one candidate
or exact boundary/residual disposition. Every list item, inline code span,
physical fenced-code line, command parent, entrypoint/tool/operation/option/path
child, and residual prose fragment receives one injective source occurrence and
exactly one disposition. Command candidates originate only in the distinct
`target_claim_content_source_span`; heading, introduction, and other admitted
context remain explicitly covered boundary/residual evidence.

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

The exact detailed public target-command production is available for one
complete inline code span or one complete physical line of a fenced command
catalog:

`python3 tools/wu-session-migration <exact-runtime-operation> --request <path>`

It has exactly five raw operands separated by one ASCII space. `python3`,
`tools/wu-session-migration`, and `--request` are exact literals;
`<exact-runtime-operation>` uses the shorthand operation-token grammar; and
`<path>` denotes exactly one non-empty raw operand with no ASCII whitespace,
shell control operator, comment, or trailing syntax. The mapper performs no
shell expansion, unquoting, path normalization, environment substitution, or
working-directory inference.

The full raw line/span is one command-parent occurrence with exact child
occurrences for the entrypoint, tool path, operation token, option, and path
operand. The operation child becomes `runtime-member` only when its exact token
joins both the whole-blob parser-registration query and the detailed README
command-occurrence query at the common repository commit. Those query occurrence
IDs are retained in the interpretation record. A syntactically valid
operation-shaped token absent from canonical/parser/detailed support is
`unsupported-operation` and participates as an exact extra; it is never silently
accepted as support.

The following full-command neighbors are retained losslessly and fail closed
rather than being normalized into the production:

- wrong or missing `python3` entrypoint;
- wrong or missing `tools/wu-session-migration` tool path;
- wrong, missing, duplicated, or repositioned `--request` option;
- missing or empty request path operand;
- any extra operand before or after the request operand;
- an authorized support command in the runtime-operation child position, which
  receives `support-command-wrong-runtime-production` rather than becoming a
  runtime extra;
- an unsupported operation-shaped child, which receives
  `unsupported-operation` and remains an exact extra only when every other
  production operand closes; and
- a command terminator, comment, continuation, redirection, pipe, conjunction,
  prompt marker, or any other trailing syntax.

Structural malformed-neighbor dispositions are comparison-blocking when their
interpretation is required by an active complete claim. They produce a
cause-preserving target-command gap, not a guessed operation and not `None`.

An admitted command-catalog claim may contain a bare code-span command matching
`[a-z][a-z0-9]*(?:-[a-z0-9]+)*`. Parser and detailed-command authority then
classify it as `runtime-member`, `authorized-support-command`,
`unsupported-operation`, `authorized-non-operation`, or `ambiguous`.
`capture-evidence`, `dry-run`, `apply`, and `validate-pre-pr-readback` are
support-command examples, not runtime extras. In a mixed claim they remain valid
content and cannot hide a missing runtime operation.

For the shorthand, bare-token, and full-command productions, wrong options,
malformed or different operands, missing or extra operands, unclosed delimiters,
unsupported punctuation, case folding, Unicode folding, underscore/hyphen
rewriting, whitespace rewriting, and unfamiliar syntax are ambiguous rather
than normalized. Raw parents, every operand/suffix child, and exact source spans
remain preserved.

Membership comparison requires these exact equalities:

`target_presentation_candidate_ids == target_presentation_disposition_candidate_ids`

`recognized_command_candidate_ids == raw_command_occurrence_source_candidate_ids`

`raw_command_occurrence_ids == command_occurrence_disposition_occurrence_ids`

`recognized_full_command_parent_ids == completed_full_command_parent_ids`

`full_command_parent_operand_role_keys == completed_full_command_operand_role_keys`

`runtime_member_full_command_operation_child_ids == parser_and_detailed_command_bound_operation_child_ids`

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

A complete command catalog that renders the same operations as exact full
`python3 tools/wu-session-migration <exact-runtime-operation> --request <path>`
parents produces the same operation set after all five child operands and the
parser/detailed-command joins close. Omitting `phase0-reresolve` from that form
therefore produces the same expected missing member rather than a command-adapter
gap.

## Lossless typed transition assembly

Wiring is independent from membership. An operation token in a membership list
does not establish a lifecycle edge, and a membership-only claim has
`lifecycle_sequence_completeness: not-claimed`.

`transition_authority_fact_inventory` contains every query-derived typed
authority fact occurrence. Each fact record preserves:

- `source_occurrence_id`
- `authority_query_id` and exact query occurrence identity
- exact source identity, span, raw text, and content identity
- `source_authority_role`
- structured `transition_assembly_key`
- `owned_fields`, an explicit set
- values only for those owned fields
- applicability and evidence paths

`transition_assembly_key` is a structured identity over the common repository,
exact operation, applicable lifecycle partition, and identity-bound edge key
established by the discovered sources. It contains no delimiter-joined string
and no field value invented from another occurrence. If complementary sources
cannot be joined to one key without guessing, the assembly is unresolved.

The canonical transition field universe is:

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

Required-field closure is defined per claimed comparison dimension by one
`transition_dimension_matrix` record for each
`{transition_assembly_key, lifecycle_sequence_completeness,
claimed_semantic_dimensions}`. The matrix stores every field with disposition
`required` or `structurally-not-applicable` and the exact target and authority
occurrence IDs that justify that disposition:

- `edge-membership` requires exact `operation` plus an authority-owned edge
  locator consisting of `predecessor_or_order`, `destination_or_successor`, or
  both. It does not require condition, conditionality, effects, caller/owner,
  writer, or readback semantics merely to establish edge membership.
- `transition-semantics` requires the edge-membership fields. For a conditional
  edge it additionally requires `source_conditions` and `conditional`. It also
  requires `effects`, `owning_caller_or_domain`, and `sole_writer` exactly when
  the target explicitly claims completeness for those semantic dimensions.
- `readback_authority` and `readback_mode` are required only when the bounded
  authority materiality query proves that live readback is material to that
  transition and claimed dimension. The only live-readback authority remains
  the top-level CLI path described above. Otherwise both fields are
  `structurally-not-applicable` for that matrix.
- Any non-readback field the target purports to assert is compared and therefore
  becomes required for that assertion even when the broader dimension did not
  require its restatement. A target readback assertion first runs the exact
  materiality query; when readback is structurally non-applicable, the assertion
  is compared with that matrix disposition without inventing a canonical
  readback value.

Explicit non-applicability is a matrix fact bound to the exact transition,
comparison dimension, target occurrence, and materiality-query occurrences. It
is never inferred from source silence and never stored as an invented canonical
field value.

Every query-derived authority occurrence contributes only fields its source
owns. The assembler preserves every contributing occurrence and source
identity. For each matrix-required field it requires exactly one authoritative
value. Two sources claiming ownership of the same required field are
`multiply-owned-field` even when their values happen to be equal; unequal values
are `authority-value-conflict`. Corroborating or constraining occurrences remain
separate records and cannot become second owners. Missing required values are
`missing-authoritative-field`. Structurally non-applicable fields require no
value and receive none. There is no majority vote, first-source choice, unstated
default, field borrowing, or source erasure.

Each completed `transition_assembly` contains the assembly key, matrix identity,
every source fact ID, an ownership map from each required field to exactly one
source fact, every structural non-applicability basis, assembled values,
constraints and comparisons, and the resulting structured `transition_id`.
`transition_id` is built from the source-established operation, lifecycle
partition, and edge identity using typed structural equality; dimension-specific
required fields cannot silently split or merge it. Canonical transition
candidates are these assembled results, never impossible uniformly complete
records required from one source occurrence.

Source-fact completion and transition-assembly completion close independently:

`admitted_transition_fact_occurrence_ids == completed_transition_fact_occurrence_ids`

`applicable_transition_query_keys == completed_transition_assembly_keys`

`transition_dimension_matrix_keys == completed_transition_dimension_assembly_keys`

`completed_transition_ids == canonical_transition_ids`

Every applicable canonical transition then receives one target comparison:

`applicable_transition_ids == completed_transition_comparison_ids`

A missing fact disposition cannot be hidden by a completed assembly, and an
applicable query key cannot be hidden by complete source-fact accounting.
`enumeration_complete` is true only when whole-blob discovery, every independent
query/disposition equality, authority constraints, operation support, transition
facts, dimension matrices, assemblies, scope/applicability witnesses, and target
comparisons plus the reverse assertion/group-member closure below close with no
required comparison conflict.

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

Before canonical matching, the mapper uses the complete `transition` overlay of
`target_source_domain` to build `target_transition_occurrence_inventory`. It
preserves every block/descendant node, list item, operation wording, condition,
conditionality, predecessor/order, destination, effect, caller, writer,
readback, delegation, grouped/alternative construct, and residual occurrence
with exact source identity and span. Every occurrence receives exactly one
disposition: `admitted-target-assertion`, `authorized-non-transition`,
`non-fire-context`, or `ambiguous/unsupported`.

Each admitted assertion has a `claimed_fields` presence map for all assembled
transition fields. It interprets only fields present in the target. An absent
field is `unasserted`; a purported but uninterpretable field is ambiguous and
comparison-blocking. Explicit inequality is never converted into absence. Each
assertion also receives one structural `target_assertion_key` from the exact
target identity, assertion occurrence identity, and explicit group/member
identity where present; no raw strings are delimiter-joined.

Target accounting requires:

`target_transition_occurrence_ids == target_transition_disposition_occurrence_ids`

`admitted_target_assertion_ids == completed_target_assertion_ids`

`applicable_transition_ids == completed_transition_comparison_ids`

Reverse target closure independently requires:

`admitted_target_assertion_keys == completed_target_assertion_keys`

`completed_target_assertion_keys == completed_canonical_comparison_or_discharge_assertion_keys + authority_proven_non_applicable_assertion_keys + indeterminate_or_contradicted_or_unmatched_assertion_keys`

`explicit_target_group_member_keys == completed_target_group_member_keys`

`completed_target_group_member_keys == completed_canonical_comparison_or_discharge_group_member_keys + authority_proven_non_applicable_group_member_keys + indeterminate_or_contradicted_or_unmatched_group_member_keys`

Every `+` is a disjoint exact key-set partition. Duplicate assertion keys,
duplicate group-member keys, duplicate disposition, one key in multiple
partitions, or unequal left/right sets is
`target-assertion-reverse-closure-mismatch`. Each terminal assertion/member
record has exactly one outcome:
`completed-canonical-comparison`, `completed-delegated-discharge`,
`authority-proven-non-applicable`, `indeterminate`, `contradicted`, or
`unmatched`, with exact evidence and candidate canonical IDs. `indeterminate`
and `unmatched` retain the cause that prevented canonical discharge;
`contradicted` retains the unequal fields and establishes drift when authority
and comparison otherwise resolve.

For every explicit group, exact source group-member keys must equal the member
keys in its completed group-discharge record, and the discharge's canonical
transition IDs must equal the canonical IDs reached by those member records.
Missing, extra, or duplicate group members are
`target-group-member-equality-mismatch`. These equalities close before
`enumeration_complete` or `None`. No assertion or group member may disappear
merely because each canonical transition already has another valid covering
assertion.

### Lifecycle-sequence completeness oracle

For `edge-membership`, a uniquely matching active-affirmative operation and
predecessor/order or destination/successor assertion can establish only that one
edge is named. Its result is `included` for edge membership. Condition,
conditionality, effects, caller, writer, and readback are
`structurally-not-applicable` under that dimension's matrix unless the target
purports to assert one. It may not be reported as complete transition semantics.

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
remain exact in discovered authority and are compared when the target asserts
them. Effects, caller/owner, and writer become required target assertions only
when the target expressly claims semantic completeness for those dimensions.
Readback becomes required only when its exact transition/dimension materiality
query closes. Thus exact `sole_writer` and CLI-only live readback are never lost,
defaulted, invented for unrelated edges, or imposed on a claim that did not make
them material.

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
- proves exact source group-member keys equal completed group-member keys and
  their reached canonical transition IDs equal the discharged canonical IDs.

If two or more canonical transition IDs remain compatible only because the
target leaves distinguishing fields unasserted, the mapping is
`target-discharge-ambiguous`. The assertion marks none of them included. The
affected mapping is non-clean, or additional unmatched transitions remain
`omitted` when the target's complete inventory and dimension make omission
decidable. The evaluator may not silently mark all compatible transitions
included, choose one by source order, or use majority vote.

Every assertion-to-transition witness records asserted and canonical values,
per-field `equal`, `unequal`, `unasserted`, or
`structurally-not-applicable-by-dimension`, the sequence-completeness dimension,
matrix identity, candidate transition IDs, unique or grouped discharge decision,
and exact evidence. `observed_treatment` is one of
`included`, `delegated`, `omitted`, `contradicted`, `not-applicable`, or
`indeterminate`.

The ticket-required `wiring_transition` is an aggregate record containing:

- `evaluated_repository_identity`
- `target_claim_identity`
- `target_source_domain`
- `target_scope_identity`
- `delegate_resolution`
- `lifecycle_sequence_completeness`
- `comparison_authority_discovery_domain`
- `comparison_authority_query_inventory`
- `transition_authority_fact_inventory`
- `transition_dimension_matrix`
- `transition_assemblies`
- `canonical_transition_ids`
- `transition_applicability_witnesses`
- `applicable_transition_ids`
- `target_transition_occurrence_inventory`
- `target_transition_occurrence_dispositions`
- `target_transition_assertions`
- `target_assertion_keys`
- `target_assertion_to_canonical_transition_witnesses`
- `target_discharge_records`
- `target_assertion_disposition_index`
- `target_group_member_keys`
- `target_group_member_disposition_index`
- `target_assertion_reverse_closure`
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
included. Its edge-membership matrix does not require readback values for
unrelated transitions. This preserves the named current missing-operation case
and the round-seven missing-condition neighbor without inventing canonical
fields.

## Unwanted behaviors

The two documentation behaviors are independent:

### Operation-membership drift

An active-affirmative generic claim with `claim_completeness` `exact` or
`complete-implied`, command domain `runtime-only` or `mixed`, and applicable
membership presents a complete operation inventory, but one or both of
`missing_operations` and `extra_operations` is non-empty after identity,
complete structural-block/composite target closure, bounded whole-blob authority
discovery, independent query closure, executable support, activation,
classification, scope/applicability, target accounting, and set comparison
complete. Repository-global membership never requires caller adoption; a
caller-scoped applicable subset does.

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

- A classification non-fire requires exact identity, one complete
  `target_source_domain`, every component and role-overlay equality, resolved
  activation and polarity, and every fact needed for that exact disposition.
  Clearly partial, non-runtime-only, non-active, and negative envelopes do not require
  unrelated operation support or transition assembly after making the canonical
  comparison domain inapplicable. Delegated and scoped-inapplicable paths also
  require exact `target_scope_identity`, same-commit `delegate_resolution`, and
  complete per-member applicability witnesses. A membership-only disposition
  bypasses only wiring, not an applicable complete membership comparison.
- An active complete-claim comparison non-fire additionally requires resolved
  scope and applicability, all target component/overlay equalities, whole-blob
  discovery and independent query equalities, aligned per-member executable
  support, caller authority only for caller-scoped membership or wiring,
  complete dimension-scoped typed transition assembly for each applicable wiring
  dimension, complete applicability partitions, complete unique/group discharge,
  and exact reverse assertion/group-member closure.

On either path, `None` is allowed only when both axis records are `absent` or
`not-applicable` and no blocking `failure_obligation` exists. One absent axis
cannot erase an indeterminate axis, and one inapplicable axis cannot make an
independent drift clean.

Optional adjacent provenance is not a prerequisite on either path.

The named behavior does not fire when:

- Exact membership or sequence semantics are unambiguously delegated without an
  exhaustive restatement, every delegation occurrence resolves to exactly one
  same-commit canonical authority, and applicable-member witness closure is
  complete.
- A list is clearly partial, illustrative, selected, or example-only and no
  text inside its complete admitted envelope independently implies completeness.
  This includes an `Examples only:` introductory paragraph plus its immediately
  following governed list after composite/component closure succeeds.
- A non-runtime-only claim lists support commands such as `capture-evidence`,
  `dry-run`, `apply`, or `validate-pre-pr-readback` and makes no runtime
  membership claim.
- A mixed claim preserves support/non-operation commands while its runtime side
  has every applicable member and no unsupported extra.
- A membership-only claim differs only in ordering because membership authority
  is a set.
- A repository-global membership claim includes every executable-supported
  declared member even when no workflow caller has adopted one; the absent caller
  is structurally non-applicable, not a gap and not proof of workflow adoption.
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
  and its identity-bound target scope plus authority-backed per-member witnesses
  prove the complete applicable/inapplicable partition.
- Historical, quoted, proposal-only, fixture, and negative-example occurrences
  receive their explicit non-fire activation/polarity disposition and are not
  active assertions.
- A selected ineligible cohort omits a transition that identity-bound authority
  proves inapplicable through its exact witness, or occurrence-only evidence
  makes no completeness claim. One sampled WU never proves cohort exclusion.
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

Evidence state is preserved per axis and then aggregated without erasing either
axis. In the table, a `LOW` gap is the affected axis's `gap_severity`; the
finding's aggregate `severity` may remain `MEDIUM` or `HIGH` when another axis
has independently established drift.

| `evidence_state` | Minimum evidence | Permitted decision behavior |
|---|---|---|
| `complete` | Common identity and one complete structural-block or bounded-composite target domain resolve. Either a classification non-fire closes every fact required for that exact disposition, including delegate/scope witnesses where used, or an active-affirmative complete claim closes every component/overlay, whole-blob authority discovery/query equality, per-member executable support, scope-required caller applicability, applicability partition, dimension matrix, transition fact/assembly, unique/group discharge, and reverse assertion/group-member closure required by the claimed dimensions. | Emit drift when present or `None` only when every axis is absent/inapplicable and obligation-free. Inapplicable comparison domains are not required merely to make a partial, non-runtime, non-active, or negative classification clean. |
| `degraded` | In an ordinary primary result, every required comparison fact resolves but optional trace, report, audit, final-diff, or non-decisional provenance is unavailable. In a fallback gap result, primary result construction, serialization, or delivery failed and that exact failure obligation is preserved. | An ordinary direct mismatch may emit reduced-confidence drift, and an ordinary obligation-free non-fire may emit `None`. A fallback gap is always a `finding`, never `None`, and authorizes no repair from an unavailable primary result. |
| `evidence-gap` | A required source role, raw occurrence disposition, support fact, transition fact, dimension field, assembly, target assertion, reverse assertion/group-member closure, classification, scope/applicability/delegation witness, parser/adapter fact, or accounting equality is unavailable or uninterpretable. | Give the affected axis `indeterminate` outcome and `LOW` gap severity with at least one exact `failure_obligation`. Preserve any independent established drift and derive aggregate severity by the closed rule below. Never repair from the affected axis or use `None`. |
| `identity-conflict` | Required evidence has mixed, unbound, unverifiable, absent-at-identity, or currentness-mismatched identity. | Emit the structured `LOW` gap finding, preserve every available identity, and stop dependent comparison. Never use `None`. |
| `selector-invalid` | Target path/anchor is noncanonical, escaping, absent, non-unique, is neither one complete block nor one valid bounded composite, or cannot produce a complete target source domain. | Emit the gap finding with the attempted selector, every resolution, component, and parse/source-map outcome; do not classify, compare, repair, or use `None`. |
| `target-domain-incomplete` | Any admitted component, component union, governed content span, parse node, byte/code-point source map, role overlay, occurrence, or disposition equality fails; multiple governors/content blocks, intervening unowned blocks, unbounded context, or required semantics outside the selected envelope exist. | Emit the gap finding with completed components/overlays preserved. Context outside the admitted envelope cannot repair the domain and `None` is prohibited. |
| `activation-polarity-indeterminate` | The complete admitted envelope cannot distinguish active/historical/quoted/proposal/fixture use or affirmative/negative polarity. | Emit the gap finding and preserve every admitted-envelope occurrence. Do not convert ambiguity to active or to a non-fire `None`. |
| `claim-classification-indeterminate` | Any required completeness, command-domain, lifecycle-sequence, scope, or membership-applicability dimension is ambiguous. | Emit the gap finding, preserving independently resolved dimensions and the complete envelope. Do not compare or use `None`. |
| `authority-query-incomplete` | A discovery blob, contract-applicability query, operation/caller query, semantic projection, query disposition, support-key equality, transition-candidate equality, or query-to-assembly/comparison equality fails. | Emit the structured `LOW` gap finding with all completed query IDs/facts. A preselected semantic span cannot substitute and `None` is prohibited. |
| `delegate-scope-indeterminate` | A delegate or target scope/caller/cohort/lifecycle identity is missing, ambiguous, stale, sampled-only, unbound, or lacks the exact applicability partition. | Emit the structured `LOW` gap finding with every candidate and witness. Do not infer exclusions or use `None`. |
| `authority-conflict` | Required declaration, support, transition fact ownership/value, exact `sole_writer`, CLI-only readback where material, caller/progression, constraint, matrix, or assembly fact conflicts. | Emit the structured `LOW` gap finding and preserve every source occurrence/conflict. Never vote, default, erase, repair the target, or use `None` for the dependent axis. |
| `target-discharge-indeterminate` | One assertion is compatible with multiple materially distinct transitions without an explicit complete group/alternative construct, group membership is incomplete, or assertion/group-member reverse closure fails. | Emit the gap finding unless a separate omission or contradiction is already decidable. Mark none silently included, preserve every assertion/member and candidate, and never use `None` for the affected wiring axis. |
| `result-transport-failure` | Primary result construction, schema validation, serialization, or delivery fails. | Deliver the runner-owned cause-preserving fallback gap envelope with `result_transport_state: fallback-gap-delivered`, `evidence_state: degraded`, the exact primary failure obligation, and no unsupported repair. If that envelope cannot be delivered, use only the separately specified terminal transport failure below, never `None`. |
| `lifecycle-prohibited` | Runnable evaluation is requested while lifecycle remains `WRITE`. | Stop without executing the behavior comparison and emit the structured `LOW` lifecycle gap envelope if a result boundary has been entered. Specification presence is not `None` or a detector result. |

Each axis has one closed `authority_state`: `conflict`, `incomplete`, `aligned`,
or `not-applicable`, scoped only to facts required for that exact axis. Aggregate
`authority_state` is the first state present in this precedence:
`conflict > incomplete > aligned > not-applicable`. It preserves both per-axis
states and never describes all runtime actors or capabilities. A
repository-global membership axis cannot become `incomplete` merely because
caller authority is structurally non-applicable.

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

Every gap finding carries all available repository, target, scope, delegate,
authority-query, support, applicability, matrix, assembly, target-accounting,
and independent-axis outcomes. A value is `null` only when genuinely
unavailable, not merely unfinished. At least one exact cause-preserving
`failure_obligation` is mandatory.

At `WRITE`, routes and terminal conditions are descriptive only. A fresh result
does not close a prior obligation, and no retry, document repair,
reconciliation, escalation, lifecycle transition, or runtime action is
authorized. Later rollout work must bind acting authority, authorization,
attempt lineage, and durable closure evidence before enforcing any action.

Cause-specific obligations include, where applicable:

- repository and target identity causes named above;
- `target-block-zero-match`, `target-block-multi-match`,
  `target-block-partial-node`, `target-parse-ambiguous`,
  `target-composite-multiple-governors`,
  `target-composite-multiple-content-blocks`,
  `target-composite-intervening-unowned-block`,
  `target-composite-unbounded-context`,
  `target-component-partition-mismatch`,
  `target-source-domain-incomplete`,
  `required-semantics-outside-target-domain`, and every role-overlay equality;
- `ambiguous-activation`, `ambiguous-polarity`,
  `ambiguous-claim-completeness`, `ambiguous-command-domain`,
  `ambiguous-lifecycle-sequence-completeness`, `ambiguous-scope`, and
  `ambiguous-membership-applicability`;
- `comparison-authority-discovery-coverage-mismatch`,
  `authority-query-selector-failure`, `authority-query-parse-failure`,
  `authority-query-occurrence-disposition-mismatch`,
  `operation-support-key-mismatch`, and
  `support-query-completion-mismatch`,
  `comparison-scope-support-requirement-mismatch`, and
  `caller-authority-required-for-global-membership`;
- `delegate-resolution-missing`, `delegate-resolution-ambiguous`,
  `target-scope-unbound`, `target-scope-sampled-only`,
  `operation-applicability-partition-mismatch`, and
  `transition-applicability-partition-mismatch`;
- `transition-fact-accounting-mismatch`, `missing-authoritative-field`,
  `multiply-owned-field`, `authority-value-conflict`, and
  `transition-dimension-matrix-mismatch`, `transition-assembly-mismatch`, and
  `transition-query-comparison-mismatch`;
- `target-presentation-accounting-mismatch`,
  `command-occurrence-accounting-mismatch`,
  `full-command-operand-closure-mismatch`,
  `malformed-full-target-command`, and
  `catalog-operation-token-ambiguous`;
- `target-transition-assertion-ambiguous`,
  `target-transition-accounting-mismatch`,
  `target-discharge-ambiguous`, `target-assertion-duplicate-key`,
  `target-assertion-reverse-closure-mismatch`,
  `target-group-member-duplicate-key`,
  `target-group-member-equality-mismatch`, and
  `target-group-coverage-mismatch`;
- `unresolved-source-or-adapter-attribution`, `unsupported-adapter`,
  `result-construction-failure`, `result-schema-validation-failure`,
  `result-serialization-failure`, `result-delivery-failure`,
  `result-transport-state-unknown`, `result-transport-state-contradiction`, and
  `lifecycle-prohibited-execution`.

At `WRITE`, parser or adapter failure remains
`unresolved-source-or-adapter-attribution`; the failing adapter cannot assign
source blame or terminal source invalidity to itself.

### Result transport contract

`result_transport_state` is a mandatory, runner-owned closed enum on every
emitted finding:

- `primary-delivered`: the runner's primary result constructor, schema
  validator, serializer, and delivery path successfully emitted an ordinary
  drift or gap finding. Every ordinary finding has exactly this value.
- `fallback-gap-delivered`: primary construction, validation, serialization, or
  delivery failed, and the runner successfully emitted the cause-preserving
  fallback gap envelope.

A `fallback-gap-delivered` finding always has aggregate `severity: LOW`,
`evidence_state: degraded`, at least the exact primary-failure
`failure_obligation`, and any independently available candidate fields whose
integrity is known. Both axis outcomes are `indeterminate`; candidate primary
axis fields, even if construction reached them before serialization or delivery
failed, remain non-decisional provenance rather than established drift in the
fallback envelope. Each axis has `evidence_state: degraded`, `gap_severity` set
to `LOW`, and its own occurrence of the primary-failure obligation keyed to that
axis. Its `suggested_action` may restore the failed
producer/transport fact and retain other unresolved obligations, but it contains
no target-document or runtime repair unsupported by a valid primary result. It
can never carry or imply `None`.

The runner producer sets this state; the schema validator and consumer require
it to agree with the observed delivery path, evidence state, obligations, and
finding kind. Unknown values are `result-transport-state-unknown` and a known
value inconsistent with those records is
`result-transport-state-contradiction`; either invalidates the primary envelope
and requires a valid fallback gap. The fallback itself must carry the truthful
`fallback-gap-delivered` value. `None` is not a finding and has no finding field;
successful transport of `None` remains runner-owned invocation evidence outside
this schema.

`terminal-transport-failure` is a separately specified runner transport
boundary, not an eval result. It is permitted only after primary result failure
when the runner cannot construct, validate, serialize, or deliver the mandatory
fallback gap envelope. The future runner must terminate
non-successfully and expose through its runner-owned terminal channel every
available value of `eval_id`, invocation/attempt identity,
`evaluated_repository_identity`, attempted target selector, transport stage,
original error, and unavailable envelope fields. Consumers must treat the
absence of a valid `finding | None` envelope as a failed invocation. The terminal
signal cannot be read as `None`, drift absence, a completed axis, or authorization
to repair. Because no eval finding exists, it has no
`result_transport_state`. ACR-403 selects no channel or implementation; a future
rollout must bind and verify it before execution.

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
- `target_source_domain`
- `target_source_component_inventory`
- `target_source_role_overlays`
- `target_context_source_span`
- `target_claim_content_source_span`
- `target_context_occurrence_inventory`
- `target_activation`
- `target_polarity`
- `target_activation_polarity`
- `claim_completeness`
- `command_domain`
- `lifecycle_sequence_completeness`
- `claim_scope`
- `target_scope_identity`
- `delegate_resolution`
- `membership_applicability`
- `applicable_canonical_operations`
- `operation_applicability_witnesses`
- `transition_applicability_witnesses`
- `target_presentation_source_coverage`
- `target_presentation_candidate_inventory`
- `target_presentation_candidate_dispositions`
- `raw_command_occurrences`
- `command_occurrence_dispositions`
- `full_command_parent_occurrences`
- `full_command_operand_occurrences`
- `raw_catalog_operation_occurrences`
- `catalog_operation_interpretations`
- `comparison_authority_discovery_domain`
- `comparison_authority_discovery_coverage`
- `comparison_authority_query_inventory`
- `comparison_authority_query_results`
- `comparison_authority_raw_occurrence_inventory`
- `comparison_authority_raw_occurrence_dispositions`
- `derived_authority_semantic_spans`
- `authority_constraint_inventory`
- `operation_support`
- `transition_authority_fact_inventory`
- `transition_dimension_matrix`
- `transition_assemblies`
- `target_transition_occurrence_inventory`
- `target_transition_occurrence_dispositions`
- `target_transition_assertions`
- `target_assertion_keys`
- `target_assertion_to_canonical_transition_witnesses`
- `target_discharge_records`
- `target_assertion_disposition_index`
- `target_group_member_keys`
- `target_group_member_disposition_index`
- `target_assertion_reverse_closure`
- `documentation_drift_outcome`
- `authority_state`
- `authority_conflicts`
- `failure_obligations`
- `failure_cause`
- `result_transport_state`
- `non_decisional_provenance`
- `residual_uncertainty`

No merge-verification or ACR-398 consumption field is part of the trace or
finding.

For resolved drift, `eval_id` is
`wu-session-runtime-operation-catalog-drift`, `authority_symbol` is
`RUNTIME_OPERATIONS`, all available collections are deterministic, and exact
target, activation, comparison-domain, source-fact, assembly, target assertion,
reverse-closure, and discharge records remain present.

`documentation_drift_outcome` contains exactly two independently preserved
per-axis result records, `operation_membership` and `conditional_wiring`. Each
record contains:

- `outcome`: `present`, `absent`, `not-applicable`, or `indeterminate`
- `evidence_state`, retaining the exact axis-local evidence state from the table
- `authority_state`: `conflict`, `incomplete`, `aligned`, or `not-applicable`
- `established_drift_severity`: `MEDIUM`, `HIGH`, or `null`
- `gap_severity`: `LOW` or `null`
- `drift_fields`, the axis-owned resolved differences
- `failure_obligation_ids`, exactly the obligations whose `affected_axis`
  matches this axis
- `axis_suggested_action`, containing only repairs or evidence restoration
  supported by this axis

For `operation_membership`, `drift_fields` contains
`applicable_canonical_operations`, `catalog_operations`, `missing_operations`,
and `extra_operations`. For `conditional_wiring`, it contains applicable,
included/delegated, omitted, contradicted, indeterminate, and unmatched
transition/assertion IDs plus the completed discharge and reverse-closure
records. `present` requires non-empty established drift fields and
`established_drift_severity`; `indeterminate` requires `gap_severity: LOW` and at
least one axis-local obligation. `absent` and `not-applicable` require both
severity fields and axis-local obligations to be `null`/empty. No aggregate
field may replace either record.

For a gap finding, every field remains present. Unavailable scalar, record, or
collection values are `null`; independently resolved values remain intact;
empty lists mean resolved empty sets, never unknown evidence. Exact raw source
and target occurrences remain present even when interpretation is unavailable.
Every gap includes at least one exact `failure_obligation`, all available
identity and independent-axis outcomes, and the original parser, adapter, query,
or transport error where applicable.

For an ordinary primary finding, aggregate `severity` is deterministic:

1. If one or both resolved axes have established drift, use the highest
   `established_drift_severity` among those axes (`HIGH` before `MEDIUM`).
2. Otherwise, if at least one axis is `indeterminate`, use `LOW`.
3. Otherwise no finding is permitted; return `None` only when both axes are
   `absent` or `not-applicable` and every failure-obligation set is empty.

Thus aggregate severity describes finding impact, not the ACR-403 planning risk,
and never implies that every axis resolved:

- `MEDIUM`: established generic operation-catalog or conditional-wiring drift.
- `HIGH`: established transition-semantics drift whose same active target claim
  explicitly contradicts exact `sole_writer`, CLI-only live readback, or a
  required eligibility condition in a way that instructs an invalid lifecycle
  action.
- `LOW`: a distinct evidence, identity, selector, target-domain,
  activation/polarity, classification, scope/delegation/applicability,
  authority-query, support, matrix/assembly, target-accounting, discharge,
  parser/adapter, or result-transport gap.

Aggregate `authority_state` follows the closed precedence defined above while
retaining both axis-local states. Aggregate ordinary `evidence_state` is the
first axis-local state present in this closed precedence:
`identity-conflict`, `selector-invalid`, `target-domain-incomplete`,
`activation-polarity-indeterminate`, `claim-classification-indeterminate`,
`authority-query-incomplete`, `delegate-scope-indeterminate`,
`authority-conflict`, `target-discharge-indeterminate`, `evidence-gap`,
`degraded`, then `complete`. A fallback envelope instead has the mandated
top-level `degraded` state and transport contract above.

`confidence` reflects directness and completeness. It never conceals degraded or
missing required evidence.

## Suggested action

The finding-level `suggested_action` is a deterministic aggregate with separate
axis-labelled `established_drift_repairs` and `unresolved_axis_obligations`.
`established_drift_repairs` contains only the non-null `axis_suggested_action`
from axes whose outcome is `present`. `unresolved_axis_obligations` retains every
obligation and evidence-restoration action from axes whose outcome is
`indeterminate`, even when aggregate severity is `MEDIUM` or `HIGH`. It never
turns aggregate severity into repair authority for an unresolved axis.

For established membership drift, direct the target owner to include the exact
applicable supported operation tokens and remove only exact unsupported-operation
extras, or narrow/delegate the completeness claim. A repository-global repair
uses executable-supported membership without inventing workflow adoption or an
automated caller. Preserve every authorized support/non-operation command in a
mixed claim.

For established edge-membership wiring drift, direct the owner to include the
missing applicable edge in the claimed order, explicitly group complete
alternatives, or narrow/delegate the edge inventory. For established
transition-semantics drift, direct the owner to assert or validly delegate the
required condition and conditionality and any other semantic dimension it
expressly claims complete. Do not require generic prose to restate unrelated
effects, caller, or writer facts when it does not claim semantic completeness for
them, or readback facts when the exact transition/dimension matrix makes live
readback structurally non-applicable.

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
repair the future parser/adapter/spec before rerunning. This includes restoring a
complete structural-block/composite target envelope, component/source-map and
governed-content-span closure, exact command operand mapping, same-commit
delegate/scope/applicability joins, complete authority queries, executable
support facts, scope-required caller facts, dimension matrices, assemblies,
reverse assertion/group-member closure, or result transport as named by the
obligation. Do not edit the target based on assumptions. Non-decisional
provenance and residual uncertainty may be reported without suggesting unrelated
runtime, recovery, scheduler, namespace, or merge work through this finding.

## Consumers and supported-surface boundary

Current consumers are ACR-403 reviewers and maintainers or agents performing
separate exact-target review of complete-looking generic tool and lifecycle
claims. The supported operation surface is functional detailed CLI reachability
under the exact facts above; global membership does not imply caller adoption.
Direct standalone WUs using planning root `P` and feature direct/refactoring
routes using `F/routes` remain request-topology cohorts behind the same sole
writer; this specification changes neither cohort.

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
- exact repository/target identity and one complete structural-block or permitted
  bounded-composite `target_source_domain`, distinct governed content span, and
  every component-union/role-overlay equality;
- active-affirmative gating using only admitted components, without semantic
  borrowing outside the envelope;
- the exact full public command parent/children and malformed neighbors, while
  preserving repository-native shorthand, bare tokens, and mixed command-domain
  handling;
- the bounded whole-blob `comparison_authority_discovery_domain`, deterministic
  per-operation/per-caller queries, query-derived semantic spans, and every
  exactly-once query/disposition equality, without an all-effecting actor claim;
- per-member declaration, parser/main, request-validation, successful
  transaction, and detailed-command executable support; caller authority is
  structurally non-applicable for global membership and mandatory for
  caller-scoped subsets and wiring;
- exact `target_scope_identity`, same-commit `delegate_resolution`, and complete
  operation/transition applicability witness partitions;
- CLI-only live readback where compared;
- typed partial transition facts, per-dimension required-field matrices, n-way
  assembly, exact field ownership/non-applicability basis, query/completion
  equalities, exact `sole_writer`, and conflicts without majority or source
  erasure;
- edge-membership versus transition-semantics completeness;
- unique or explicit grouped/alternative target discharge plus reverse exact
  closure for every assertion and group member;
- per-axis outcome/evidence/authority/severity/drift/action records, aggregate
  severity and authority precedence, retained unresolved obligations, positive
  and non-fire paths, exact `finding | None`, closed primary/fallback transport,
  terminal transport, finding, and suggested-action contracts; and
- the external ACR-398 prerequisite wording and anti-scope.

Step 6c must reject a noncanonical/multiply resolving or partial-block target, a
composite with multiple governors/content blocks, intervening unowned blocks, or
unbounded context, semantic borrowing outside admitted components, incomplete
component or role-overlay equality, malformed full-command normalization,
preselected-span authority discovery, incomplete query/support/applicability
closure, caller adoption used to gate global membership, missing caller authority
for a scoped subset or transition, stale/ambiguous delegation, sampled scope
exclusion, a missing or duplicate disposition, incomplete transition facts or
dimension matrix, invented readback non-applicability, missing or multiply owned
required canonical fields, a one-source-complete transition requirement,
unevidenced field borrowing/defaults, source erasure, unrestricted projected
compatibility, absent required conditional semantics classified as included,
direct-import live-readback authority, support commands treated as runtime
extras, missing reverse assertion/group-member closure, mixed-axis severity or
repair ambiguity, an unknown/contradictory transport state, an unstructured
indeterminate result, latent adjacent capability obligations used to prevent
`None`, or any eval-owned merge-verification claim.

Step 6c does not patch this file, implement or run a detector, invoke the
migration executable, add a repository path, or create behavior evidence. A
specification mismatch returns through explicit revision and fresh authoring.
One inspection cannot claim another target or repository cleanliness.

## Lifecycle notes

ACR-403 ends at `WRITE`.

- `ROLL_OUT` requires a separately authorized WU to select and implement a
  detector and extraction approach; add representative positive, activation,
  polarity, complete-block and both bounded-composite domains, multiple-governor,
  multiple-content/intervening/unbounded gaps, heading-plus-list complete,
  `Examples only:` plus list partial, delegated/scope/applicability, global
  membership without caller adoption, caller-scoped membership, partial, mixed,
  shorthand, bare-token, exact full-command and malformed-neighbor,
  edge-membership, transition-semantics, per-dimension matrix, typed n-way
  assembly, missing/multiply owned field, unique/group discharge, reverse
  assertion/group-member closure, mixed drift/gap aggregation, identity,
  selector, whole-blob authority-query, structured gap, primary-delivered,
  fallback-gap-delivered, unknown/contradictory transport, and terminal-transport
  cases; prove every target and authority query/occurrence equality; demonstrate
  CLI-only live readback where material and exact `sole_writer`; validate
  reports; observe advisory results; and review false positives and evidence
  drift.
- `ENFORCE` additionally requires trusted findings, a named caller and
  hookpoint, severity policy, document-repair routing, fail-closed required
  evidence behavior, and durable enforcement-readiness evidence.
- `MAINTAIN` tracks authority and target syntax, exact target selector
  uniqueness, complete-block/bounded-composite component and source-map closure,
  distinct governed content spans, activation/polarity overlays,
  shorthand/full-command/malformed-neighbor and command-domain grammar,
  whole-blob authority discovery/query closure, scope/delegate/applicability
  joins, comparison-scope-specific support, transition fact ownership/dimension
  matrix/assembly, lifecycle-sequence completeness, target discharge and reverse
  assertion closure, per-axis aggregation, CLI-only readback where material,
  exact `sole_writer`, result transport, finding comparability, and lifecycle
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

The inherited Step 6b intent is the exact complete-block or permitted
bounded-composite target envelope, distinct governed content span, bounded
whole-blob authority discovery, comparison-scope-specific support,
query/applicability/assembly and reverse target-discharge closure, per-axis
aggregation, and cause-preserving transport contract defined here. It does not
permit ACR-398 to substitute a selected target fragment, unbounded context,
preselected authority spans, sampled cohort exclusion, caller adoption as a
global membership gate, a dropped target assertion, or an unstructured
indeterminate outcome for its direct per-target inspection.

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
lossless authority discovery is bounded to the named complete comparison blobs,
and its lossless target accounting is bounded to one exact complete structural
block or one of the two exact composite forms. Whole-blob discovery does not
expand into wake/scheduler/helper/recovery or global actor auditing, and bounded
target parsing does not become adjacent-context borrowing or repository-wide
claim discovery. Per-axis aggregation and fallback transport do not create a
catch-all adjacent finding, runtime repair authority, or transport
implementation.
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
