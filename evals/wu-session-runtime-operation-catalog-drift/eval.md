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
| `wu-session-runtime-lifecycle-ownership-v1` | The closed operation/field/enforcement authority matrix below assigns each fact to one exact procedural owner context or executable enforcement context. Applicable implementation-pipeline/resumer workflow and optimized-contract occurrences are mandatory constraints/corroboration, while conditionally admitted feature/refactoring route owners may own only topology selection and normalized child/cohort/root binding. The detailed README is constraint/corroboration, never a competing owner. Writer comparison is limited to the activated implementation-pipeline/resumer child cohort. |
| `operation-catalog-claim-comparison-v1` | This accepted ACR-403 contract owns exact target admission, activation and polarity, completeness and command-domain classification, lossless target occurrence accounting, membership and conditional-wiring comparison, non-fire semantics, and safe document-only repair for one claim. |

Symbols, methods, fields, operations, sections, and evidence families subordinate
to those surfaces are not additional adapter contracts. The ACR-398 prerequisite
is external handoff context, not a fifth adapter surface, trace output, authority
surface, or result field of this eval.

## Conceptual boundary

The future conceptual interface is:

`evaluate(normalized_evidence: operation-catalog-drift-trace-v1) -> finding | None`

This signature is specification text only. It selects no language, parser,
fixture, resolver, runner, result serialization, report sink, schedule,
hookpoint, or caller.

Each call evaluates exactly one injectively admitted target claim at one
common repository identity. A finding represents the named documentation drift
or a cause-preserving inability to decide a comparison fact required for that
claim. `None` means only that this named behavior is sufficiently evidenced as
absent or non-applicable for that claim. It does not certify another claim, the
containing document, the repository, runtime safety, repository-wide consistency,
namespace consistency, helper authority, recovery, availability, merge state,
or external action.

The result alternatives for an actual call are exactly a structured `finding` or
`None`. Every required identity, selector, target-domain, classification,
raw-materiality admission, authority-query, support, assembly, accounting,
applicability, delegation,
discharge, source, parser, or adapter failure already represented inside the admitted
normalized bundle makes the dependent fact indeterminate and preserves a
cause-specific `LOW` gap severity and failure obligation. Its affected axis is
`indeterminate` only when no mismatch on that axis is independently established;
otherwise that axis retains `present` plus the separate obligation. The finding's
aggregate severity follows the closed per-axis aggregation contract below, so an
independent established drift is not downgraded by that gap.

Pre-input repository resolution, source reading, structural parsing, source
adapter execution, interruption, and inability to commit the normalized input
are outside `evaluate(normalized_evidence)`. They are future runner/adapter
failures: no eval call occurred, so they are neither an eval finding nor `None`.
The same is true after comparison for result serialization, delivery, sink
commit, acknowledgment, deduplication, retry, fallback publication, and consumer
terminal selection. This pure normalized-input eval does not claim to report a
call that never occurred or a result that was not externally committed.

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

The supported execution-caller domain is closed to the implementation-pipeline
and resumer partitions whose exact sources are named below. A feature-direct or
feature-routed-refactoring topology is additionally supported only when the
selected target activates it and the exact same-commit feature or refactoring
route-owner blob plus applicable optimized sidecar close the route-owner to
normalized implementation-caller/cohort/root binding. That route owner owns only
topology selection and authorization; the implementation operator remains the
sole procedural owner of child progression and operation requests. Other
parent-route cohorts and universal writer authority remain
`unsupported-caller-cohort` or
`repository-global-writer-claim-out-of-scope`, retain an exact obligation, and
cannot produce a clean or drift decision for that dimension. Conditional route
admission does not trigger wake/scheduler/recovery/helper or catch-all actor
discovery.

This eval does not claim complete discovery of repository claims or exhaustive
accounting of every actor that can affect, recover, observe, schedule, dispatch,
or judge manifest/index state. A repository-level consumer would need a separate
contract for identity-bound claim discovery, exclusions, per-claim fan-out,
completed-result equality, and aggregation.

## Positive evidence and required trace fields

`operation-catalog-drift-trace-v1` is a role-normalized evidence bundle for one
exact `evaluated_repository_identity` and one admitted
`target_claim_identity`. It represents these normalized records:

| Evidence role | Required semantic fields and decision use |
|---|---|
| Repository identity | One provider-issued `evaluated_repository_identity` with canonical repository object and full commit identity. Every repository-derived source and target record resolves from that identity. |
| Declaration authority | `authority_path`, `authority_symbol`, readable identity-bound source, and complete extracted `canonical_operations`. Declaration owns membership, not lifecycle order or functional support by itself. |
| Target-source closure | One identity-bound `enclosing_governing_context_inventory` precedes one deterministic `target_source_domain` derived from either exactly one complete Markdown structural block or exactly one of the two bounded composite forms defined below. Every potential structural governor is included or proved cosmetic/non-semantic before any activation, polarity, completeness, command-domain, sequence, delegation, domain, or scope classification. Every admitted component node, span, byte, and code point closes exactly; the governed catalog/sequence content retains its own distinct span. Before semantic extraction, every bounded target role also closes its independently derived raw-materiality inventory and disposition partition. |
| Comparison-authority discovery | A closed `comparison_authority_discovery_domain` of complete identity-bound blobs for the bounded runtime roles, the detailed-command role only when its target-grammar/delegation/transition use activates it, implementation/resumer roles only when supported caller-scoped membership or wiring activates them, and exactly one feature/refactoring route-owner role only when the selected topology activates it. Before semantic extraction or query, each complete role blob produces an independently derived raw-materiality inventory from its structural context and versioned syntax; complete per-role AST/Markdown/YAML semantic overlays then account for those raw identities before deterministic semantic queries produce spans. |
| Raw-materiality admission | One conservative `raw_materiality_candidate_inventory`, keyed separately for every bounded target and activated authority role, is derived before semantic extraction from complete admitted structural contexts and trace-declared versioned syntax. Every raw candidate partitions exactly to an admitted semantic fact/candidate, an independently checkable closed-grammar or closed-section exclusion, or an unsupported/ambiguous obligation. Raw identities close through overlays, queries, transition candidates, and dispositions; free-form mapper reasons cannot exclude potentially material text. |
| Executable operation support | One `operation_support` record per canonical operation, keyed exactly once, covering exact declaration-entry closure, parser/entrypoint and top-level `main()` reachability, closed exact operation/request validation, operation-specific projection or validator, every successful public CLI path, and successful transaction endpoints. Executable transition facts additionally require same-key `enforcement_path_witness` closure. Those facts close repository-global membership without README alignment or caller adoption. Separate caller-applicability records are required only for supported implementation-pipeline/resumer subsets and conditional wiring. |
| Detailed command evidence | Identity-bound detailed README occurrences only where that source owns an admitted full-command target grammar, resolves an exact delegation, or supplies a material transition constraint/corroboration. Missing or stale detailed prose outside an activated use is non-decisional provenance; a required occurrence may create its own exact obligation but cannot erase an executable membership result. |
| Readback materiality | Before any readback occurrence is admitted, every identity-bound supported caller/progression occurrence that gates continuation on validated readback creates one `readback_materiality_candidate`, keyed by transition, comparison dimension, caller occurrence, and common commit. Exact material/not-material partition closure controls the CLI-only live-readback obligation. |
| CLI-only live readback | For each material candidate, the top-level `validate-pre-pr-readback` CLI path entered through `__main__.py` and `main()` without `expected_manifest`, under its actual lock and completed recovery antecedents, is the only live-readback authority and must join the same operation support and enforcement-path witness. |
| Lifecycle authority facts | Typed partial fact occurrences from exact operation-specific caller procedure sections, operation-specific executable validators/projections, the shared transaction implementation, CLI-only live readback where material, conditionally admitted route topology owners, mandatory workflow/optimized-contract constraints, and detailed README constraint/corroboration. Every discovered field assertion joins the closed operation/field/enforcement matrix exactly as owner, constraint, corroboration, or non-decisional; every owned fact requires its exact typed enforcement-path witness, and executable facts additionally require same-support-key closure. |
| Transition assembly | Lossless overlay-candidate-to-fact/disposition n-way assembly records, repeated-operation scope admission, per-dimension field requirements/non-applicability, exact procedural-owner precedence, operation/field/enforcement ownership, constraint/corroboration comparisons, assembly conflicts, at-most-one canonical transition per canonical operation in one activated caller/cohort domain, `canonical_transition_ids`, `applicable_transition_ids`, and independent overlay/query/fact/path/assembly/comparison equalities. |
| Exact target claim | Structured target identity, enclosing-governor inventory, source domain, exact structural-block or bounded-composite component and role-overlay closure, distinct governed content span, activation and polarity, structured `claim_kind`, exact per-command claimed-domain/subset evidence, `target_scope_identity`, `delegate_resolution`, per-operation and per-transition applicability witnesses, command dispositions, interpreted operations, sequence-member versus non-sequence/corroboration assertions, assertion/group-member keys, and discharge witnesses. |
| Comparison | Deterministically sorted operation differences and domain contradictions plus aggregate `wiring_transition`, including lifecycle-sequence completeness, repeated-operation scope disposition, canonical transitions, target treatments, unique/group discharge, reciprocal transition-to-sequence-member multiplicity closure for each admitted single edge, reverse assertion/group-member closure, omissions, contradictions, multiplicity drift for duplicate restatements of that edge, unmatched assertions, and indeterminate mappings. |
| Axis derivation | Independent `operation_membership` and `conditional_wiring` records retain axis-local outcome, evidence/authority state, established-drift or gap severity, drift fields, failure obligations, and suggested action before aggregate severity/authority/action derivation. |
| Observation provenance | `evidence_paths`; source, trace, prompt, log, report, audit, and final changed-surface paths when available. Optional provenance does not replace authority. |
| Conflict and availability | Aggregate and per-axis `evidence_state`, per-axis and aggregate `authority_state`, `authority_conflicts`, exact `root_causes`, axis/fact-qualified injective `failure_obligations`, exact forward/reverse root-cause joins, the exact derived `missing_evidence_roles`, and obligations for every unresolved identity, selector, governor, target-domain, raw-materiality admission, claimed-domain, authority overlay/query, declaration closure, executable support/path witness, activated detailed-command use, caller/route applicability, readback materiality, delegation, ownership, repeated-operation scope, assembly, multiplicity, accounting, parser, or adapter fact already represented in the admitted normalized bundle. |
| Non-decisional context | Optional `non_decisional_provenance` and `residual_uncertainty` for adjacent capabilities or actors, or for bounded occurrences already excluded by the independent raw-materiality oracle. These records never independently produce a finding, change a drift outcome, or veto `None`; a potentially material bounded occurrence without an admitted semantic mapping or independently checkable exclusion is instead an obligation. |

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
- `enclosing_governing_context_inventory_identity`

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

Before target-envelope admission, the mapper derives one identity-bound
`enclosing_governing_context_inventory` from the complete parsed target blob.
Starting at every raw anchor resolution, it enumerates every structural ancestor,
governing section heading, list or definition-list container,
blockquote/container, and permitted immediately preceding lead-in that can
contribute activation, polarity, completeness, command domain, lifecycle domain,
scope, or delegation. Each potential governor retains its node identity,
complete source range, raw text, structural relationship to the proposed
content, and exact semantic roles it could affect. No useful context is selected
from a precomputed semantic span.

Every potential governor receives exactly one disposition:

- `included-semantic-governor`, requiring the complete governor node and its
  structurally governed domain to be inside the admitted envelope;
- `proven-cosmetic-or-non-semantic`, with exact syntax and source evidence that
  it contributes none of the closed semantic roles; or
- `semantic-ambiguous-or-unsupported`, which makes envelope admission
  indeterminate.

Inventory and envelope closure require these exact set equalities:

`potential_governor_node_ids == included_semantic_governor_node_ids + proven_cosmetic_or_non_semantic_governor_node_ids + semantic_ambiguous_or_unsupported_governor_node_ids`

`included_semantic_governor_node_ids == target_envelope_semantic_governor_node_ids`

`included_semantic_governor_code_point_ids == target_envelope_semantic_governor_code_point_ids`

`included_semantic_governor_byte_ids == target_envelope_semantic_governor_byte_ids`

Every `+` is a disjoint exact partition and every potential governor appears
once. Admission requires the ambiguous/unsupported partition to be empty. If an
excluded governor is semantic, ambiguous, unsupported, or cannot be source-map
proved cosmetic, the mapper must select the permitted envelope that completely
includes it or emit `target-governor-envelope-indeterminate`. It may not borrow
the governor only for classification or ignore it to obtain a partial non-fire.

After governor closure and before activation or any other semantic
classification, the mapper derives one `target_source_domain` by parsing the
exact target blob under the trace-declared
`markdown_structural_grammar_version`. The record contains:

- `evaluated_repository_identity`
- `catalog_path` and `source_blob_identity`
- `catalog_anchor` and every raw anchor resolution
- `markdown_structural_grammar_version`
- the complete `enclosing_governing_context_inventory`, disposition index, and
  governor-to-envelope closure records
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
  `unbounded-context`, or `governor-envelope-indeterminate`

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
`intervening-unowned-block`, `unbounded-context`, and
`governor-envelope-indeterminate` are structured target-domain gaps.

Component accounting is an injective exact partition. Empty component sets are
allowed only where the envelope kind makes that component structurally
inapplicable:

`target_source_domain_component_node_ids == target_heading_component_node_ids + target_introduction_component_node_ids + target_governed_content_component_node_ids + target_other_admitted_context_component_node_ids`

`target_source_domain_code_point_ids == target_heading_component_code_point_ids + target_introduction_component_code_point_ids + target_governed_content_component_code_point_ids + target_other_admitted_context_code_point_ids`

`target_source_domain_byte_ids == target_heading_component_byte_ids + target_introduction_component_byte_ids + target_governed_content_component_byte_ids + target_other_admitted_context_byte_ids`

Each `+` expression is a disjoint union, every component and source position
appears exactly once, and component byte/code-point source-map equality closes.

Before semantic field extraction, the mapper derives the target-role part of one
conservative `raw_materiality_candidate_inventory`. For every role `r` in the
closed target-role set below, the input is the complete admitted structural
context, all of its raw leaf-node/source occurrences, the complete governor and
component relationships, and the trace-declared
`markdown_structural_grammar_version`. Every raw leaf-node/source occurrence in
each complete role context enters the inventory before any exclusion; candidate
production is structural and syntax-versioned and cannot use a semantic overlay,
query result, canonical operation name, or mapper-authored semantic reason to
choose its universe.

Each raw target occurrence is therefore a materiality candidate, including an
occurrence that may later be proved a closed grammar boundary or section
exclusion. The inventory conservatively records whether its bounded structural
context and versioned syntax could supply or qualify activation, polarity,
completeness, command domain, operation/command identity, lifecycle condition or
order, delegation, authority, ownership/writer, effect, readback, scope, or
constraint evidence. Each candidate retains one injective
`raw_materiality_candidate_identity`, exact target-role key, source node and
byte/code-point ranges, raw text, structural ancestry, syntax-version key, and
the closed set of comparison-fact families it could affect.

After semantic mapping, every raw target candidate receives exactly one of these
dispositions:

- `admitted-semantic-fact-or-candidate`, retaining the same raw identity in every
  resulting overlay and downstream command or transition candidate;
- `independently-excluded-by-closed-grammar-or-section`, requiring a versioned
  closed grammar production or closed structural-section rule whose mechanically
  checkable premises prove the occurrence cannot supply any required comparison
  fact; or
- `unsupported-or-ambiguous-obligation`, naming each potentially affected axis
  and comparison fact.

The target-role closure is exact:

`target_raw_materiality_candidate_ids == target_admitted_semantic_raw_materiality_candidate_ids + target_independently_excluded_raw_materiality_candidate_ids + target_unsupported_or_ambiguous_raw_materiality_candidate_ids`

`target_raw_materiality_candidate_ids == target_raw_materiality_disposition_candidate_ids`

`target_raw_materiality_candidate_ids == target_role_overlay_raw_materiality_candidate_ids`

`target_admitted_semantic_raw_materiality_candidate_ids == target_role_overlay_admitted_raw_materiality_candidate_ids`

`target_command_capable_admitted_raw_materiality_candidate_ids == target_command_candidate_or_explicit_non_command_disposition_raw_materiality_candidate_ids`

`target_transition_capable_admitted_raw_materiality_candidate_ids == target_transition_candidate_or_explicit_non_transition_disposition_raw_materiality_candidate_ids`

Every `+` is a disjoint exact identity partition. An exclusion record must retain
its closed rule ID/version, all rule premises, exact structural context, and
source-map proof. A free-form reason, including a mapper-authored
`non-decisional-provenance` reason, is not an exclusion oracle. Any candidate not
admitted or independently excluded, any unclosed identity projection, or any
unsupported/ambiguous candidate creates the exact axis/fact-qualified
`raw-materiality-admission` obligation and prohibits `None`.

The normative harmful-neighbor expectation is fail-closed: material condition,
completeness, command, or constraint wording inside a bounded potentially
semantic context but outside the recognized versioned forms yields
`unsupported-or-ambiguous-obligation`. It never becomes
`non-decisional-provenance` and never permits a clean result.

The mapper then builds role-specific lossless overlays for `context`, `heading`,
`introduction`, `governed-content`, `presentation`, `command`, `transition`,
`delegation`, `activation`, `polarity`, `completeness`, `domain`, and `scope`.
Activation, polarity, completeness, delegation, and scope may use only admitted
component nodes; command and transition assertion interpretation may use only the
distinct governed content span. Each overlay retains every admitted parse node,
source position, and applicable raw-materiality identity. It may assign text a
grammar-boundary/residual or structurally-inapplicable disposition only through
the matching independently checkable exclusion record rather than by semantic
mapper judgment. For every role `r` in that closed set:

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

Governor semantics participate in the same activation, polarity, completeness,
domain, scope, and delegation overlays as every other admitted component. A
complete-heading governor followed by an admitted `Examples only:` lead-in and
list therefore contains conflicting completeness evidence. It is
`claim-classification-indeterminate`, not `partial-example`, and cannot return
`None`; dropping the heading fails governor-to-envelope closure.

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
complete comparison, while an unconflicted `Examples only:` in an admitted
introductory paragraph plus its immediately following list can resolve `partial-example` and
reach its classification non-fire when every other required equality closes.

## Comparison authority order

Disagreement is preserved with exact source identities. It is never settled by
prose majority, test count, or source deletion.

Transition authority is the closed
`transition_operation_field_enforcement_authority_matrix`. It is keyed by exact
operation, activated caller/cohort/lifecycle domain, canonical field, comparison
fact within that field, exact owner path and section, and enforcement-path
witness. There is no caller-role-wide or field-wide default.

### Procedural caller owner precedence

For implementation-pipeline operations, the one exact applicable section of
`agents/implementation-pipeline-orchestrator.md` is the procedural owner of the
caller facts it executes. Every corresponding occurrence discovered in
`workflows/implementation-pipeline.md`,
`contracts/workflows/implementation-pipeline.yaml`, and
`contracts/operators/implementation-pipeline-orchestrator.yaml` is retained and
is mandatory constraint/corroboration for only the fact it asserts. A complete
sidecar query may resolve to an empty asserted-field set; no occurrence may be
invented. For resumer operations, the one exact applicable `## Procedure` step
of `agents/wu-session-resumer.md` is procedural owner, and every corresponding
occurrence discovered in the already bounded
`workflows/implementation-pipeline.md`, its applicable optimized contract, and
`contracts/operators/wu-session-resumer.yaml` is retained as mandatory
constraint/corroboration under the same rule. This does not admit the wake
workflow or scheduler domain. Equal secondary values corroborate; any unequal
value is `authority-value-conflict`. A workflow or sidecar restatement is never
a second owner, and no occurrence is erased.

The exact operation-to-procedural-owner index is:

| Operation | Sole caller procedural owner context | Mandatory secondary comparison domain |
|---|---|---|
| `phase0-init` | `agents/implementation-pipeline-orchestrator.md` `### Phase 0 — Bootstrap`, step 10 | Applicable complete workflow and implementation operator/workflow sidecar occurrences. |
| `phase0-reresolve` | `agents/implementation-pipeline-orchestrator.md` `### Migration semantics for in-flight WUs`, the `ACR-310 estimate-disposition migration` paragraph | Applicable complete workflow and implementation operator/workflow sidecar occurrences, including every same-edge Phase 0 re-resolution restatement. |
| `cold-start-disposition-bind` | `agents/implementation-pipeline-orchestrator.md` `#### Phase 2.5 human gate`, step 4a | Applicable complete workflow and implementation operator/workflow sidecar occurrences. |
| `phase3-bind` | `agents/implementation-pipeline-orchestrator.md` `### Phase 3 — Proposal`, the estimate-artifact binding and closed-readback paragraph | Applicable complete workflow and implementation operator/workflow sidecar occurrences. |
| `phase7-upsert` | `agents/implementation-pipeline-orchestrator.md` `#### Draft PR acquisition and single CodeRabbit review`, step 4 | Applicable complete workflow and implementation operator/workflow sidecar occurrences. |
| `phase9-update` | `agents/implementation-pipeline-orchestrator.md` `### Phase 9 — Verified PR Outcome`, steps 1 and 2 | Applicable complete workflow and implementation operator/workflow sidecar occurrences. |
| `resumer-update` | `agents/wu-session-resumer.md` `## Procedure`, steps 2 through 6, with step 6 owning request progression | Applicable complete bounded workflow/contract and resumer sidecar occurrences. |
| `resumer-close` | `agents/wu-session-resumer.md` `## Procedure`, steps 14 and 15 | Applicable complete bounded workflow/contract and resumer sidecar occurrences. |

An owner context is identity-bound to the complete same-commit blob, exact
heading identity, procedure item identity, and asserted source span. Heading text
alone is not an owner selector. Zero, multiple, stale, overlapping, or
unresolvable applicable owner contexts create an exact
`caller-procedural-owner-precedence` obligation. The fixed index, not mapper
choice, establishes precedence.

### Operation/field/enforcement compound authority

Every canonical field is decomposed into the exact comparison facts the target
asserts. Each fact has one owner context and one exact typed enforcement-path
witness; executable facts additionally require same-operation support-key
closure:

| Comparison fact | Sole owner rule | Constraints/corroboration |
|---|---|---|
| `operation` membership | Exact `RUNTIME_OPERATIONS` entry joined to parser, entrypoint, and top-level `main()` dispatch, with that declaration-to-dispatch enforcement witness. | Operation-specific runtime code constrains support; caller and README occurrences corroborate. |
| Caller-authenticated `source_conditions`, review/currentness gates, policy prerequisites, and operation-selection condition | Exact operation-specific procedural owner context above, with a procedural enforcement witness from the authenticated premise through request authorization. | Runtime is compared only for a predicate it actually validates; workflow/sidecars and README constrain only their asserted premise. |
| Required request values, caller partition, `predecessor_or_order`, and `destination_or_successor` | Exact operation-specific procedural owner context above, with a procedural enforcement witness from value construction through exact operation invocation and guarded continuation. | Runtime constrains only values/order it validates; workflow/sidecars and README are fact-local comparisons. |
| Runtime admission predicate and `conditional` property actually enforced on every applicable successful CLI path | Operation-specific validator/projection with an exact enforcement-path witness. | Caller and README assertions constrain only that admitted predicate, never caller review/currentness authority. |
| Runtime allowlist and projected manifest/index effect actually checked | Operation-specific validator/projection with an exact enforcement-path witness. | Caller-required complete values constrain only the requested projection they name; README corroborates. |
| Commit/replacement outcome and cohort-scoped `sole_writer` | Shared transaction implementation with exact request-to-journal-to-replacement-to-success endpoint witness. | Operation-specific validator and caller constrain admitted inputs; neither owns commit merely because it precedes the writer. |
| Material `readback_authority` and `readback_mode` | Top-level CLI live-readback path with the closed materiality and lock/recovery/enforcement join. | Caller progression constrains why readback is required; README corroborates. |
| Activated route/cohort/root topology | The conditionally admitted exact feature/refactoring route-owner context and applicable sidecar, with the route-owner applicability witness as its selection/binding enforcement path. | Implementation caller and runtime root validation constrain the normalized binding. Route authority never owns child progression, operation selection inside the child, or request values. |

`source_conditions`, `conditional`, and `effects` are therefore compound records,
not values assigned to whichever source is closest to the write. For example,
`effects` may contain separately owned
`caller_required_replacement_values`, `runtime_allowed_projection`, and
`transaction_commit_outcome`; `source_conditions` may contain separately owned
`caller_prerequisites` and `runtime_admission_predicates`. Every target or
secondary assertion is compared only with the exact comparison fact it
constrains. No source may borrow enforcement, authorization, or completeness from
another fact.

Every required canonical field and every owned comparison fact names one exact
`owner_context_identity` and one typed `enforcement_path_witness_id`. Witness
types are `declaration-dispatch`, `caller-procedural`,
`runtime-admission-or-projection`, `transaction-commit`, `cli-live-readback`, or
`route-selection-binding`. A caller-procedural witness retains the exact
procedure premise, value construction, operation request, and guarded
continuation/progression edges; it does not claim Python validation. A runtime or
transaction witness retains the executable call/control-flow edges it actually
enforces. A route witness ends at normalized child/cohort/root authorization and
cannot cross into child progression. Missing or cross-context witnesses are
`enforcement-path-incomplete`.

For `phase9-update`, the implementation procedural owner retains the Phase 8
reviewed/currentness prerequisites, exact draft/reviewed identities, complete
required Phase 9 values, caller partition, and progression. The runtime validator
owns only the allowlist/subset admission and exact manifest/index projection it
checks. The shared transaction owns only commit/replacement outcome. A runtime
path that accepts any non-empty allowed subset cannot overrule or own the
caller's complete required-value fact.

Every discovered field assertion joins exactly one disposition: `owner`,
`constraint`, `corroboration`, or `non-decisional`, derived from the exact
operation, comparison fact, owner context, and enforcement witness. One owner is
required for each matrix-required comparison fact, with its exact owner context
and typed enforcement-path witness. Every constraint and
corroboration is compared with that fact's owner; inequality is
`authority-value-conflict`. A second source selected by the fixed precedence as
owner is `multiply-owned-field` even when equal. Detailed README transition prose
is always constraint/corroboration and never a competing owner. Tests, snapshots,
traces, reports, audits, and final diffs remain corroborating or observational
and cannot vote a member, transition, or field into authority.

Executable owner records are authoritative only with the same-operation
`enforcement_path_witness` defined below. A dead or bypassed validator/projection
is non-decisional source text or an authority gap, not an owner. Only top-level
`validate-pre-pr-readback` entered through `__main__.py` and `main()`, without
`expected_manifest`, under its actual lock after completed recovery, may own
post-write live acceptance for a material candidate. Direct/imported validation
does not borrow those antecedents.

## Comparison-authority discovery domain

`comparison_authority_discovery_domain` is the deterministic, identity-bound
whole-blob discovery oracle. It is fixed before semantic span selection and is
limited to these already bounded, comparison-scope-specific roles. Its core
executable-support domain always includes:

- complete `tools/wu-session-migration/wu_session_migration.py` runtime-module
  blob;
- complete `tools/wu-session-migration/__main__.py` entrypoint blob.

Its detailed-command subdomain includes the complete
`tools/wu-session-migration/README.md` blob only when the selected claim uses a
full-command grammar or detailed-authority delegation, or the wiring comparison
requires a material transition constraint/corroboration from that source.
Otherwise the README has state `structurally-not-applicable` for comparison and may be retained
only as non-decisional provenance. A missing or stale required occurrence creates
a detailed-command obligation for that exact activated use; it does not alter
any independently completed `operation_support` record or repository-global
membership difference.

Its execution-caller subdomain is activated only by a caller-scoped membership
subset or conditional-wiring comparison in the supported
implementation-pipeline/resumer execution cohort. When activated, it includes:

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

Its route-owner subdomain is activated only when the complete selected target
scope and execution-caller evidence name `feature-direct` or
`feature-routed-refactoring`. It is omitted, not queried, and not required for
every claim that does not activate one of those topologies. Exactly one of these
same-commit owner domains is admitted:

- `feature-direct`: complete `agents/feature-orchestrator.md` plus complete
  `contracts/operators/feature-orchestrator.yaml` candidate, with owner context
  `## Route Record Schema`, `### Route dispatch and merge ownership`, and
  `#### Direct implementation route`;
- `feature-routed-refactoring`: complete
  `agents/refactoring-orchestrator.md` plus complete
  `contracts/operators/refactoring-orchestrator.yaml` candidate, with owner
  context `## Canonical Invocation`, `## Non-Negotiables`, and
  `## Implementation Child Invocation Contract`. The upstream feature
  `#### Refactoring route` occurrence may be retained as a constraint on route
  selection, but it is not a second normalized-child/root owner.

The applicable route sidecar is included or excluded only after its complete
whole-candidate query closes. Every admitted route-owner blob and sidecar receives
the same full discovery coverage, complete semantic overlay, query occurrence,
source-map, and disposition closure as every other authority role. Route-owner
admission may establish only topology selection/authorization and the exact
normalized binding to `{implementation-caller, caller/cohort, planning root,
live runtime root, active-index owner}`. It cannot supply implementation child
phase order, progression, operation request contents, or readback decisions.

One `route_owner_binding` must join exactly one owner context to the normalized
implementation execution caller and target scope. It retains exact route owner,
route kind, child operator, caller/cohort identity, route planning/scratch roots,
canonical `R=F/routes`, exact active-index path, owner and sidecar occurrence IDs,
implementation caller occurrence IDs, and one
`route_owner_applicability_witness`. The witness proves same-commit target scope,
route selection, child dispatch, root normalization, and implementation-caller
acceptance. These equalities close before caller applicability:

`activated_route_topology_ids == route_owner_binding_topology_ids`

`route_owner_binding_ids == route_owner_applicability_witness_binding_ids`

`route_owner_binding_ids == normalized_implementation_caller_cohort_root_binding_ids`

Zero owners, multiple owners, a feature owner used as child-progression owner,
missing applicable sidecar closure, unequal root/cohort/caller values, or an
unwitnessed binding is `route-owner-binding-indeterminate`. Other parent routes
remain `unsupported-caller-cohort`: their caller-scoped fact is out of scope and
indeterminate with an exact obligation. This conditional expansion never admits
wake, scheduler, recovery, helper, alternate-namespace, universal-writer, or
global actor sources.

For repository-global membership with no wiring claim, the execution-caller and
route-owner subdomains have state `structurally-not-applicable`; none of their
blobs or optimized contracts is admitted, queried, or required, and their
availability cannot gate the membership axis. A direct implementation/resumer
claim likewise omits route-owner blobs. The detailed-command subdomain is
structurally non-applicable unless the target grammar or an exact delegation
activates it. Every core blob and every activated detailed-command, execution
caller, route owner, or optimized-contract candidate resolves from the common
repository identity. An
activated contract candidate is either included as one complete blob or excluded
with an identity-bound `authority-proven-contract-inapplicable` query result.
Zero/ambiguous matches, parse failure, or inability to prove the
inclusion/exclusion is an evidence gap; no useful semantic span may decide blob
admission. That gap applies only after its subdomain is activated and blocks only
the target-grammar, delegation, caller-scoped membership, or wiring fact that
depends on it; an independently closed repository-global membership axis and any
already established mismatch remain resolved.

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
and source position in every included blob before interpreting any fact:

`comparison_authority_discovery_blob_ids == comparison_authority_discovery_coverage_blob_ids`

`comparison_authority_discovery_code_point_ids == comparison_authority_raw_leaf_parse_node_code_point_ids + comparison_authority_grammar_boundary_code_point_ids`

`comparison_authority_discovery_byte_ids == comparison_authority_raw_leaf_parse_node_byte_ids + comparison_authority_grammar_boundary_byte_ids`

Each `+` expression is a disjoint exact partition. Semantic source spans are
projections of completed query occurrences and are never an input to discovery.
A stale list of previously useful spans cannot satisfy this domain.

Before any authority semantic extraction or query, each activated bounded source
role derives its authority-role records in the same
`raw_materiality_candidate_inventory` from the role's complete included blob,
complete raw parse/structural contexts, and trace-declared AST, Markdown, or YAML
grammar version. Every raw leaf-node/source occurrence in the complete role blob
enters the inventory before any exclusion. Its versioned context and possible
operation, command, completeness, lifecycle condition/order, authority,
ownership/writer, effect, readback, scope, route binding, progression, or
constraint fact families are retained conservatively. A later overlay, query,
known operation name, or semantic mapper reason cannot select or narrow that
universe.

Each authority raw candidate retains the same identity and evidence fields as a
target raw candidate plus its activated authority-role key and complete blob
identity. It receives exactly one
`admitted-semantic-fact-or-candidate`,
`independently-excluded-by-closed-grammar-or-section`, or
`unsupported-or-ambiguous-obligation` disposition under the same independent
exclusion rules. Authority closure requires:

`authority_raw_materiality_candidate_ids == authority_admitted_semantic_raw_materiality_candidate_ids + authority_independently_excluded_raw_materiality_candidate_ids + authority_unsupported_or_ambiguous_raw_materiality_candidate_ids`

`authority_raw_materiality_candidate_ids == authority_raw_materiality_disposition_candidate_ids`

`authority_raw_materiality_candidate_ids == authority_semantic_overlay_raw_materiality_candidate_ids`

`authority_admitted_semantic_raw_materiality_candidate_ids == authority_semantic_overlay_admitted_raw_materiality_candidate_ids`

`authority_admitted_semantic_raw_materiality_candidate_ids == completed_query_or_explicit_non_query_disposition_raw_materiality_candidate_ids`

`authority_transition_capable_admitted_raw_materiality_candidate_ids == independently_discovered_transition_candidate_or_explicit_non_transition_disposition_raw_materiality_candidate_ids`

Every `+` is a disjoint exact identity partition. Every overlay occurrence,
query occurrence, transition candidate, and explicit disposition retains its
originating raw identity; the forward and reverse projections must be equal. A
closed grammar/section exclusion retains a mechanically checkable versioned rule
and source-map proof. A comment label, prose rationale, free-form mapper reason,
query silence, or absence of a recognized form cannot independently exclude a
candidate. Any potentially material occurrence not admitted or independently
excluded, or any raw-to-overlay/query/transition/disposition identity mismatch,
creates an exact `raw-materiality-admission` obligation and prohibits `None`.

Only after this independent partition closes does each activated bounded source
role build one `authority_semantic_overlay` for every complete included AST,
Markdown, or YAML blob in that role. For each overlay, every parsed node, byte,
and code point is
assigned exactly once to `semantic-candidate`, `grammar-boundary`,
`comment-or-non-decisional-content`, or `unsupported-or-ambiguous-syntax`:

`authority_role_parse_node_ids == authority_role_semantic_candidate_node_ids + authority_role_grammar_boundary_node_ids + authority_role_comment_or_non_decisional_node_ids + authority_role_unsupported_or_ambiguous_node_ids`

`authority_role_code_point_ids == authority_role_semantic_candidate_code_point_ids + authority_role_grammar_boundary_code_point_ids + authority_role_comment_or_non_decisional_code_point_ids + authority_role_unsupported_or_ambiguous_code_point_ids`

`authority_role_byte_ids == authority_role_semantic_candidate_byte_ids + authority_role_grammar_boundary_byte_ids + authority_role_comment_or_non_decisional_byte_ids + authority_role_unsupported_or_ambiguous_byte_ids`

Every `+` is a disjoint exact partition, and node-to-byte/code-point source-map
equality closes. `grammar-boundary` and
`comment-or-non-decisional-content` require the matching independent raw
exclusion; otherwise the occurrence is `unsupported-or-ambiguous-syntax`. The
union of overlay blob/role keys equals the activated
authority source-role keys. Parsed-domain-to-overlay equality must close before
the first semantic query. Every unsupported/ambiguous overlay occurrence creates
an exact `parser-adapter-attribution` or authority-query obligation and prohibits
`None`; it is never dropped merely because a later query does not select it.

The exact resolved `RUNTIME_OPERATIONS` AST declaration node has an independent
entry oracle. Every direct declaration entry, including its literal node and
source range, equals exactly one canonical operation member record and every
canonical member record points to exactly one entry:

`runtime_operations_declaration_entry_node_ids == canonical_operation_member_record_source_node_ids`

`runtime_operations_declaration_entry_keys == canonical_operation_member_record_keys`

Duplicate, skipped, unsupported, computed, or ambiguously interpreted entries
are `declaration-entry-closure-mismatch`; they create a declaration-authority or
adapter obligation before operation support and prohibit `None`.

After overlay and declaration-entry closure extract revision-local
`canonical_operations`, the domain runs deterministic whole-blob
executable-support queries for every
canonical operation. It runs caller queries only for a caller-scoped applicable
subset or a conditional-wiring transition; repository-global membership gives
caller authority the explicit `structurally-not-applicable` disposition. The
query inventory enumerates:

- every exact operation-token occurrence;
- the declaration occurrence and parser-registration branch;
- top-level `main()` registration/routing and entrypoint reachability;
- exact operation/request validation and operation-specific validation;
- operation-specific projection/handler and successful transaction path;
- every detailed human command occurrence required by an activated target
  grammar, delegation, or material transition-semantic use;
- every overlay-derived conditional, predecessor/order, destination/successor,
  effects, owner/writer, caller, lifecycle-partition, and progression candidate;
- every caller/progression occurrence needed to close readback materiality
  before any readback occurrence is admitted;
- when feature-direct or feature-routed-refactoring is activated, every exact
  route-selection, child-operator, caller/cohort, route-root, runtime-root,
  active-index-owner, and implementation-caller binding occurrence needed to
  close the one route-owner applicability witness;
- only after materiality closure, every top-level CLI live-readback occurrence
  required by a material transition/dimension candidate; and
- every optimized-contract caller occurrence admitted by the contract
  applicability query.

Each query occurrence preserves its originating
`raw_materiality_candidate_identity`, raw text, source order, parent/container
links, exact blob/span/content identity, query ID, operation or caller key, and
source role. It receives exactly one disposition:

- `admitted-support-fact`
- `admitted-transition-fact`
- `admitted-authority-constraint`
- `non-decisional-provenance`
- `conflict`
- `unsupported-syntax-adapter-obligation`

Unsupported syntax is retained rather than skipped. `non-decisional-provenance`
requires the exact matching independently checkable raw-materiality exclusion;
an exact but free-form mapper reason is insufficient. It creates no drift
finding and does not prevent `None` only after that exclusion and every
applicable query closure has closed. A conflict or unsupported-syntax obligation
blocks only the dependent required fact. There is no majority vote, silent
occurrence omission, or canonical-name-seeded selector.

Independent query closure requires all of these exactly-once equalities:

`comparison_authority_query_occurrence_ids == comparison_authority_query_disposition_occurrence_ids`

`activated_authority_source_role_keys == completed_authority_semantic_overlay_keys`

`authority_semantic_candidate_occurrence_ids == completed_query_or_explicit_non_query_disposition_occurrence_ids`

`runtime_operations_declaration_entry_keys == canonical_operation_member_record_keys`

`canonical_operation_ids == operation_support_keys`

For every canonical operation `o` and executable support role `r` required in
all comparison scopes, where `r` is exactly `declaration`,
`parser-entrypoint-main`, `operation-request-validation`,
`operation-projection-or-validator`, or `successful-transaction-path`:

`required_support_query_occurrence_ids[o, r] == completed_support_fact_query_occurrence_ids[o, r]`

For every activated detailed-command use key `d` and its exact owned role `r`:

`required_detailed_command_query_occurrence_ids[d, r] == completed_detailed_command_fact_query_occurrence_ids[d, r]`

No detailed-command query key exists merely because an operation is a declared
repository-global member. A missing README occurrence for an otherwise
executable-supported operation therefore cannot make that member unresolved.

For every caller-scoped operation/caller key `k` and required caller role `r`:

`required_caller_query_occurrence_ids[k, r] == completed_caller_applicability_fact_query_occurrence_ids[k, r]`

For every activated route topology key `t` and required route-owner fact `r`:

`required_route_owner_query_occurrence_ids[t, r] == completed_route_owner_binding_fact_query_occurrence_ids[t, r]`

`activated_route_owner_source_role_keys == completed_route_owner_semantic_overlay_keys`

No caller-query key exists for repository-global membership. Its per-member
caller disposition is instead exactly `structurally-not-applicable`. No
route-owner query key exists for repository-global, direct implementation, or
direct resumer scope; its topology disposition is exactly
`structurally-not-applicable`.

`independently_discovered_transition_bearing_candidate_occurrence_ids == admitted_typed_transition_fact_occurrence_ids + explicitly_dispositioned_transition_candidate_occurrence_ids`

`independently_discovered_transition_candidate_keys == completed_transition_assembly_or_explicit_disposition_keys`

`independently_discovered_transition_candidate_keys == completed_target_comparison_or_explicit_disposition_keys`

`applicable_transition_query_keys == completed_transition_assembly_keys`

`applicable_transition_query_keys == completed_target_transition_comparison_or_disposition_keys`

The right side partitions every overlay-derived transition-bearing candidate into
an admitted typed fact or an explicit `non-decisional-provenance`, `conflict`, or
`unsupported-syntax-adapter-obligation` record. Each ID/key occurs exactly once;
the sets are not merely counts. Every admitted or explicitly dispositioned key
also appears exactly once in completed assembly and target-comparison key closure
where applicable. Overlay, declaration, query, selector, parse, source-map, or
equality failure emits a structured gap finding and prohibits `None`.

This whole-blob discovery remains bounded to the named comparison authorities.
It does not query wake/scheduler actors, generic helpers, alternate namespaces,
rollback, recovery, cleanup, or every source capable of affecting or judging
manifest/index state. Their exclusion is not evidence of runtime absence.

`authority_constraint_inventory` preserves a query-derived occurrence that the
closed matrix classifies as a bounded invocation, caller, route-topology,
side-effect, writer, or readback constraint.
It contributes only explicitly asserted comparison facts. Every asserted fact is
compared with the exact assembled owner fact it constrains; unstated facts are not
borrowed. Explicit inequality is a conflict. The constraint never becomes a
complete transition by decorating a separately discovered occurrence.

### Readback materiality closure

`readback_materiality` closes before any top-level or imported readback
occurrence is admitted. The complete caller/progression semantic overlays for
the supported implementation-pipeline and resumer partitions independently
enumerate every identity-bound applicable occurrence that can gate continuation
on validated readback. Each such occurrence creates one candidate keyed by:

`{evaluated_repository_identity, transition_assembly_key, comparison_dimension, caller_occurrence_identity}`

Each `readback_materiality_candidate` retains the common commit, exact caller
and progression occurrence, transition and operation support key, continuation
being gated, parsed polarity/condition, and all source evidence. Every candidate
is dispositioned exactly once as `material` or
`authority-proven-not-material`:

`readback_materiality_candidate_keys == material_readback_candidate_keys + authority_proven_not_material_readback_candidate_keys`

The `+` is a disjoint exact key partition. `material` requires affirmative
caller/progression authority that continuation depends on validated readback.
`authority-proven-not-material` requires exact affirmative authority proving
that the occurrence does not gate continuation on readback; query silence,
failure to parse progression, absence of a readback token, or a mapper default is
never sufficient. A missing, ambiguous, unsupported, stale, or uninterpretable
caller/progression occurrence creates a `lifecycle-authority-facts` or
`cli-live-readback` obligation and prohibits `None`.

Every material key then requires an exact join to the top-level CLI
readback/lock/completed-recovery route and the same-operation
`enforcement_path_witness`:

`material_readback_candidate_keys == completed_cli_live_readback_enforcement_join_keys`

The join preserves `__main__.py`, top-level `main()`, absence of
`expected_manifest`, lock acquisition, completed recovery, readback call and
validation edges, caller continuation edge, and common commit. Direct/imported
validation and expected-manifest projection cannot close it. Materiality is
therefore not inferred by querying only readback occurrences and cannot be made
non-applicable by query silence.

## Per-member executable support

Every canonical declaration receives one deterministic `operation_support`
record containing:

- `operation_support_key`, the exact canonical operation ID
- `operation`
- `declaration_occurrence_ids`
- `canonical_operation_member_record_key`
- `required_support_query_occurrence_ids_by_role`
- `completed_support_fact_query_occurrence_ids_by_role`
- `parser_exposure`
- `main_reachability`
- `command_request_equality`
- `closed_request_acceptance`
- `projection_or_handler_path`
- `successful_public_cli_path_ids`
- `successful_public_cli_path_endpoints`
- `transaction_completion_evidence`
- `enforcement_path_witness_ids`
- `support_fact_to_path_closure_state`
- `support_requirements_by_comparison_scope`
- `caller_authority_requirement`, either `required-by-caller-scope` or
  `structurally-not-applicable`
- `caller_applicability_record_ids`, empty for repository-global membership
- `support_fact_occurrence_ids`
- `executable_support_state`, one of `supported`, `conflict`, or `unresolved`
- `evidence_paths`

The operation-support map has exactly the revision-local canonical operation IDs
as keys, once each. For each key, every required declaration,
parser/entrypoint/main, exact operation/request validation,
operation-specific projection or validator, and successful transaction query
occurrence appears exactly once in the corresponding completed support-fact
records. Caller occurrences appear only in separately keyed
caller-applicability records when the comparison scope requires them. Detailed
README occurrences never appear as executable-support requirements. An absent or
extra key, missing required executable query occurrence, duplicated completion,
or cross-operation unkeyed fact reuse is a structured evidence gap. A generic
parser or `main()` branch may yield one distinct operation-keyed query occurrence
per canonical operation, with each projection retaining the same underlying
source occurrence; that is explicit query expansion, not fact reuse. Declaration
membership alone cannot close any other executable support role.

For each canonical operation, the complete parser/top-level-main control-flow
projection enumerates every applicable successful public CLI path exactly once.
Each path retains entrypoint, parser registration, top-level `main()` route,
dispatch and call edges, exact branch predicates, request validation,
operation-specific projection/validator calls, shared transaction call, and
successful transaction endpoint. An unclassified or bypass path makes operation
support unresolved; a dead validator occurrence cannot establish support.

Each admitted executable transition fact has one identity-bound
`enforcement_path_witness` keyed to the same `operation_support_key`. The witness
contains the transition fact ID, all applicable successful public CLI path IDs,
the exact parser/top-level-main route, dispatch/call edges, relevant branch
predicates, operation-specific validator/projection occurrence, shared writer
endpoint, material CLI readback route when required, successful transaction
endpoint, and a governance result proving the fact is evaluated on or dominates
every applicable successful path. Exact closure requires:

`admitted_executable_transition_fact_ids == enforcement_path_witness_transition_fact_ids`

`executable_transition_support_fact_keys == completed_enforcement_path_witness_support_fact_keys`

For each executable fact `f`:

`applicable_successful_public_cli_path_ids[f] == enforcement_path_witness_covered_successful_public_cli_path_ids[f]`

These are identity/key equalities, not counts. Eligibility, conditionality,
effects, cohort-scoped writer, or material readback facts are authoritative only
when their witness closes and proves governance over every applicable successful
public CLI path. A bypass, dead validator/projection, unclassified branch,
fact/path key mismatch, or success endpoint outside the witness is
`enforcement-path-incomplete`; the occurrence remains non-decisional/
corroborating or creates an authority gap and prohibits `None`.

`supported` means only that a detailed human command using exactly the raw
locator `tools/wu-session-migration` or `~/ai/tools/wu-session-migration` enters
through the same bounded logical entrypoint, `__main__.py`, is parser-exposed,
reaches top-level `main()`, closes exact operation/request validation, reaches
its operation-specific projection or handler, and exposes success only after the
transaction path returns. This is sufficient support for one declared member in
a repository-global catalog
comparison even if the detailed README omits or misstates that member. Caller
authority is structurally non-applicable to that membership decision and cannot
turn a supported global member into an evidence gap. This state makes no claim
that the detailed README or any generic catalog is aligned, and makes no workflow
adoption, automated-caller, lifecycle placement, global namespace, helper,
recovery, availability, latency, throughput, scale, or bounded-cost claim.

`detailed_command_evidence` is a separate deterministic map keyed by each
activated `{target_claim_identity, use_kind, source_occurrence_identity}`. Its
`use_kind` is exactly `target-full-command-grammar`,
`detailed-authority-delegation`, or `material-transition-semantic`. Each record
contains the required and completed query occurrence IDs, asserted semantic
fields with matrix dispositions `constraint | corroboration | non-decisional`,
exact source identity, state `aligned | conflict | unresolved`, affected axis,
and evidence paths. No record is created for an unactivated README occurrence.
An unresolved required record creates an exact failure obligation; an optional
missing or stale occurrence remains non-decisional provenance. Neither state
rewrites executable support, removes an executable member from the applicable
global set, closes another target claim, or demotes an already established
membership mismatch.

For a supported implementation-pipeline/resumer `named-domain` or
`selected-cohort` membership comparison, executable support remains necessary
and the separate caller-applicability record must also close the exact
applicable/inapplicable subset. Every conditional-wiring
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
| `runtime-only` | Exact target syntax asserts every recognized command occurrence belongs to one runtime-write subset. Compare every entry assigned to that subset; an authorized support/non-runtime command there is a domain contradiction and extra. |
| `non-runtime-only` | Exact target syntax assigns every recognized occurrence only to support/non-runtime domains and asserts no runtime subset. Membership is not applicable, and authorized commands remain valid in that domain. |
| `mixed` | Exact target syntax defines a runtime-write subset and separately partitions every support/non-runtime occurrence outside it. Compare the runtime subset and preserve the explicitly separate commands. Coexistence alone does not establish this value. |

Command-domain classification is occurrence-specific, not only claim-wide.
Every recognized command occurrence has one `command_claimed_domain_record`
containing its exact source occurrence, asserted subset identity, claimed domain
`runtime-write | support | non-runtime | ambiguous`, all target syntax
occurrences establishing that assignment, authoritative parser/domain
classification, and disposition `aligned-runtime-member`,
`aligned-support-or-non-runtime`, `unsupported-runtime-entry`,
`domain-contradiction`, or `indeterminate`. Closure requires:

`recognized_command_occurrence_ids == command_claimed_domain_record_occurrence_ids`

`recognized_command_occurrence_ids == runtime_subset_occurrence_ids + support_subset_occurrence_ids + non_runtime_subset_occurrence_ids + ambiguous_claimed_domain_occurrence_ids`

Every `+` is a disjoint exact occurrence partition. The runtime subset identity
and every outside-subset partition are established by exact admitted target
syntax; a claim-wide `mixed` label cannot substitute for these records.

For an `exact` or `complete-implied` runtime-write subset, an authorized support
or non-runtime command assigned to that subset is `domain-contradiction`. Its
exact token remains in `catalog_operations`, participates in `extra_operations`,
and is also retained in `domain_contradictions` with its true and claimed
domains. A broader mixed catalog is clean only when exact syntax assigns each
support/non-runtime command to a separately identified subset outside the
asserted runtime subset. If that relationship is uninterpretable it is a
claimed-domain gap; it is never accepted merely because runtime and support
commands coexist. A non-runtime-only claim retains authorized support and
non-runtime commands as aligned and does not fire.

| `lifecycle_sequence_completeness` | Meaning and disposition |
|---|---|
| `edge-membership` | The sequence claims the set and order of named lifecycle edges, but not complete transition semantics. A uniquely matching operation plus predecessor/order or destination/successor assertion may establish that one edge is named. It cannot establish condition, conditionality, effects, writer, caller, or readback semantics. |
| `transition-semantics` | The sequence claims complete transition semantics. Every applicable conditional edge must explicitly assert or validly delegate its condition and conditionality. Effects, owner/caller, and cohort-scoped writer are required when the claim expressly includes those semantic dimensions; readback authority/mode are required only where the closed transition/dimension materiality candidate partition requires them. |
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

For caller-scoped membership and all wiring, execution
`caller_identity`/`cohort_identity` values remain `implementation-pipeline`,
`resumer`, or their explicitly combined `implementation-pipeline-resumer`
cohort. `feature-direct` and `feature-routed-refactoring` are conditional topology
qualifiers, not replacement execution callers. They are resolvable only through
the exact route-owner binding and applicability witness above, after which the
normalized implementation child remains `implementation-pipeline`. All other
parent routes are unsupported target scopes.

### Target scope, delegation, and applicability closure

Every active-affirmative target that activates membership, delegation, or
lifecycle comparison has one structured `target_scope_identity` containing:

- `target_claim_identity`
- the exact admitted-envelope scope occurrence and disposition IDs
- `claim_scope`
- exact `caller_identity`, `cohort_identity`, and `lifecycle_domain_identity`
  where the claim names them
- `route_topology_identity`, exact `route_owner_identity`, and
  `route_owner_binding_id` when and only when feature-direct or
  feature-routed-refactoring is activated
- `global_domain_identity` when and only when the claim explicitly covers the
  repository-global supported domain
- authority-query occurrence IDs establishing each named identity
- `scope_resolution_state`: `resolved`, `missing`, `ambiguous`, `stale`,
  `sampled-only`, `unbound`, `route-owner-binding-indeterminate`, or
  `unsupported-caller-cohort`

A repository-global claim uses the explicit global domain; it cannot infer an
exclusion from one caller, cohort, WU, trace, or non-occurrence. A named-domain
or selected-cohort identity must resolve at the same repository/commit as the
target and authority. Occurrence-only and clearly partial claims may terminate
before activating a canonical comparison domain, but they may not use that
classification to make a clean statement about excluded canonical members.
An activated feature topology requires the one exact route-owner binding and
witness before it can use implementation caller applicability. An
`unsupported-caller-cohort` or `route-owner-binding-indeterminate` state may be
retained as out-of-scope/gap provenance, but an active completeness claim that
depends on it is indeterminate and cannot use a drift decision or `None`.

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

`{target_claim_identity, target_scope_identity, comparison_scope_identity, member_identity, caller_identity, cohort_identity, route_topology_identity, route_owner_binding_id, lifecycle_domain_identity}`

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

For supported `named-domain` or `selected-cohort` membership, the exact
implementation-pipeline/resumer caller/cohort authority queries are mandatory
and may prove a member applicable or inapplicable. An activated feature topology
additionally requires its exact route-owner binding/witness, but that witness
cannot replace the implementation caller queries. Every transition witness
likewise requires caller and lifecycle
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
  unsupported-operation tokens asserted in the runtime subset, plus exact
  authorized support/non-runtime tokens whose per-occurrence claimed-domain
  record contradictorily assigns them to that runtime subset. The latter remain
  typed `domain-contradiction`, not semantically reclassified runtime commands.
- `missing_operations = applicable_canonical_operations - catalog_operations`.
- `extra_operations = catalog_operations - applicable_canonical_operations`.
- `domain_contradictions` retains every wrong-domain occurrence, its true domain,
  claimed runtime subset, and exact target syntax evidence. Its tokens are the
  wrong-domain contribution already present in `extra_operations`, not a second
  set-comparison vote.
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
`RUNTIME_OPERATIONS`. A valid token proved absent from completed canonical
executable support remains `unsupported-operation` and participates as an exact
extra.

The exact detailed public target-command grammar is available for one complete
inline code span or one complete physical line of a fenced command catalog and
admits exactly these two raw tool-locator productions:

`python3 tools/wu-session-migration <exact-runtime-operation> --request <path>`

`python3 ~/ai/tools/wu-session-migration <exact-runtime-operation> --request <path>`

Each production has exactly five raw operands separated by one ASCII space.
`python3`, `--request`, and each shown tool locator are exact literals;
`<exact-runtime-operation>` uses the shorthand operation-token grammar; and
`<path>` denotes exactly one non-empty raw operand with no ASCII whitespace,
shell control operator, comment, or trailing syntax. The mapper performs no
shell expansion, unquoting, path normalization, environment substitution, or
working-directory inference.

The full raw line/span is one command-parent occurrence with exact child
occurrences for the entrypoint, raw tool locator, operation token, option, and
path operand. Every parent and child retains its originating
`raw_materiality_candidate_identity`. The raw tool-locator child retains its distinct occurrence
identity and receives exactly one locator-kind disposition:
`repository-relative-tools-wu-session-migration` for
`tools/wu-session-migration` or `home-ai-tools-wu-session-migration` for
`~/ai/tools/wu-session-migration`. An explicit contract rule maps both, and only
both, to the same bounded logical entrypoint identity
`wu-session-migration-detailed-cli`; the raw spelling is never replaced or
discarded. The rule performs no generic path resolution, tilde or shell
expansion, filesystem inspection, symlink handling, working-directory inference,
or alias admission.

For either exact locator, the operation child becomes `runtime-member` only when
its exact token joins the same completed executable operation support and the
same activated detailed README command-grammar evidence at the common repository
commit. Those query occurrence IDs and the raw-locator-to-logical-entrypoint
mapping are retained in the interpretation record. A syntactically valid
operation-shaped token absent from canonical executable support is
`unsupported-operation` and participates as an exact extra. A token with
completed executable support but missing, stale, or conflicting detailed grammar
evidence is `indeterminate`, with an exact `detailed-command-evidence`
obligation; it is never relabeled as an unsupported extra and does not remove the
member from canonical global membership or suppress another already established
missing operation.

The following full-command neighbors are retained losslessly and fail closed
rather than being normalized into the production:

- wrong or missing `python3` entrypoint;
- a missing tool locator or any locator other than the exact
  `tools/wu-session-migration` and `~/ai/tools/wu-session-migration` spellings;
- wrong, missing, duplicated, or repositioned `--request` option;
- missing or empty request path operand;
- any extra operand before or after the request operand;
- an authorized support command in the runtime-operation child position, which
  receives `support-command-wrong-runtime-production` and, when the complete
  parent is asserted inside an exact/complete-implied runtime subset, a
  `domain-contradiction` that contributes its token to `extra_operations`;
- an unsupported operation-shaped child, which receives
  `unsupported-operation` and remains an exact extra only when every other
  production operand closes; and
- a command terminator, comment, continuation, redirection, pipe, conjunction,
  prompt marker, or any other trailing syntax.

Structural malformed-neighbor dispositions are comparison-blocking when their
interpretation is required by an active complete claim. They produce a
cause-preserving target-command gap, not a guessed operation and not `None`,
without erasing a separately established mismatch.

`support-command-wrong-runtime-production` is the semantic exception to that
structural-gap rule when every parent/operand boundary otherwise closes and the
target explicitly assigns the command to the runtime subset. Its support domain
is known, so it is a resolved `domain-contradiction` and extra rather than an
indeterminate malformed command. Any unresolved operand or claimed-subset
relationship still produces the exact target-command or claimed-domain gap.

An admitted command-catalog claim may contain a bare code-span command matching
`[a-z][a-z0-9]*(?:-[a-z0-9]+)*`. Parser and detailed-command authority then
classify it as `runtime-member`, `authorized-support-command`,
`unsupported-operation`, `authorized-non-operation`, or `ambiguous`.
`capture-evidence`, `dry-run`, `apply`, and `validate-pre-pr-readback` are
support-command examples, not runtime extras. In a mixed claim they remain valid
content only when exact target syntax partitions their occurrences outside the
asserted runtime subset; they cannot hide a missing runtime operation. Inside an
asserted runtime subset they are domain contradictions and extras. In a
non-runtime-only claim they remain valid in their own domain.

For a bare token, `unsupported-operation` likewise requires absence from
completed canonical executable support. If the executable member is known but a
required detailed-command occurrence is unavailable, the token is
`indeterminate` under the separate detailed-command record rather than converted
to an extra or removed from the applicable canonical set.

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

`recognized_command_occurrence_ids == command_claimed_domain_record_occurrence_ids`

`command_claimed_domain_record_occurrence_ids == aligned_runtime_domain_occurrence_ids + aligned_support_or_non_runtime_domain_occurrence_ids + domain_contradiction_occurrence_ids + claimed_domain_indeterminate_occurrence_ids`

`recognized_full_command_parent_ids == completed_full_command_parent_ids`

`full_command_parent_operand_role_keys == completed_full_command_operand_role_keys`

`recognized_full_command_tool_locator_occurrence_ids == bounded_tool_locator_disposition_occurrence_ids`

`bounded_tool_locator_occurrence_ids == logical_wu_session_migration_entrypoint_mapping_occurrence_ids`

`runtime_member_full_command_operation_child_ids == executable_member_and_detailed_command_grammar_bound_operation_child_ids`

`runtime_or_unsupported_token_child_ids == raw_catalog_operation_source_candidate_ids`

`raw_catalog_operation_occurrence_ids == catalog_operation_interpretation_occurrence_ids`

`catalog_operation_interpretation_occurrence_ids == interpreted_operation_occurrence_ids`

`runtime_subset_catalog_operation_occurrence_ids == catalog_operations_source_occurrence_ids`

`domain_contradiction_occurrence_ids == domain_contradictions_source_occurrence_ids`

No canonical-name-seeded recognizer may define or narrow the raw target domain.

For the point-in-time `Exact operations are` target in
`conventions/wu-session-lifecycle.md`, the seven current shorthand occurrences
map to exact runtime tokens, `missing_operations` contains
`phase0-reresolve`, and `extra_operations` is empty, subject to all identity,
support, activation, classification, and accounting gates. This is a
specification-level expected mapping, not executed detector evidence.

A complete command catalog that renders the same operations as exact full
parents using either admitted raw locator produces the same operation set after
all five child operands, the explicit raw-locator-to-logical-entrypoint mapping,
and the executable/detailed-command joins for the target-present parents close.
The two raw locator spellings remain distinct evidence but cannot change the
operation comparison. Omitting `phase0-reresolve` from either form therefore
produces the same expected missing member rather than requiring a README
occurrence for the omitted operation or becoming a command-adapter gap.

## Lossless typed transition assembly

Wiring is independent from membership. An operation token in a membership list
does not establish a lifecycle edge, and a membership-only claim has
`lifecycle_sequence_completeness: not-claimed`.

`transition_authority_fact_inventory` contains every overlay-derived,
independently discovered transition-bearing candidate as one typed authority
fact or explicit disposition. Each admitted fact record preserves:

- `raw_materiality_candidate_identity`
- `source_occurrence_id`
- `authority_semantic_candidate_occurrence_id`
- `authority_query_id` and exact query occurrence identity
- exact source identity, span, raw text, and content identity
- `source_authority_role`
- exact typed `owner_context_identity`, or `null` when the
  occurrence is constraint/corroboration/non-decisional
- structured `transition_assembly_key`
- `operation_support_key`
- `asserted_comparison_facts`, an explicit operation/field/fact set with values
  only for those facts
- `operation_field_fact_dispositions`, assigning every asserted comparison fact
  exactly one `owner | constraint | corroboration | non-decisional` matrix
  disposition
- `owned_comparison_facts`, exactly the asserted facts whose matrix disposition is
  `owner`
- `enforcement_path_witness_id` for each owner fact, with witness type matching
  its owner context; `null` only for constraint/corroboration/non-decisional facts
- applicability and evidence paths

### Repeated-operation transition scope gate

This eval supports at most one canonical transition for each canonical operation
inside one activated `{caller_identity, cohort_identity,
route_topology_identity, lifecycle_domain_identity}`. Before canonical assembly,
applicability, target discharge, or drift comparison, complete authority and
target transition overlays independently inventory every sequence-edge candidate
and group candidates by exact canonical operation and activated domain.

If either inventory contains two materially distinct sequence edges for the same
operation, emit `repeated-operation-transition-unsupported` as a
`transition-scope` failure obligation on `conditional_wiring`. Material
distinction requires source syntax asserting unequal predecessor/order,
destination/successor, lifecycle partition, or two different positions in the
same asserted sequence. It is not inferred from separate source occurrences or
equal restatements of one position. The scope obligation is emitted
before canonical assembly or discharge, the wiring axis is indeterminate unless
an independent wiring mismatch was already established, and wiring drift or
`None` is prohibited. No per-edge projection, guessed edge identity, or
many-to-one reusable executable-fact projection is created.

Duplicate occurrences that assert the same single edge remain distinct source
occurrences. Exact structural syntax must classify each duplicate either as an
explicit non-sequence corroboration/explanatory restatement or as another
governed sequence member. The former is compared but cannot discharge; the
latter remains multiplicity drift under the existing reciprocal rules. Neither
form creates a second canonical transition.

The pre-assembly scope gate closes exactly:

`operation_domain_scope_keys == repeated_operation_scope_disposition_keys`

`repeated_operation_scope_disposition_keys == single_transition_supported_keys + repeated_operation_transition_unsupported_keys`

The `+` is a disjoint exact key partition. Only
`single_transition_supported_keys` may enter assembly.

`transition_assembly_key` is therefore the structured identity over the common
repository, exact operation, applicable caller/cohort/route topology, and
lifecycle partition. It contains no delimiter-joined string, edge ordinal, or
field value invented from another occurrence. The supported one-operation/one-
transition cardinality makes the key injective; complementary sources that
cannot join that key without guessing leave assembly unresolved.

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

`sole_writer` is a scoped record, not a universal negative. Its value is
`{caller_cohort_identity, writer_implementation_identity}` and its only supported
cohort is the closed implementation-pipeline/resumer cohort. This eval may prove
that every admitted write in that named cohort delegates to the shared Python
transaction writer. It does not discover every repository actor or capability
that could write manifest/index state.

Every target writer assertion has `writer_claim_scope` exactly
`implementation-pipeline-resumer-cohort`, `repository-global-universal`,
`other-caller-cohort`, or `ambiguous`. A repository-global/universal assertion
requires complete actor/capability discovery that this eval intentionally does
not perform. It becomes `repository-global-writer-claim-out-of-scope` with an
exact `writer-authority-scope` obligation, cannot receive clean global certification,
cannot produce writer-based `HIGH` drift, and prohibits `None` for an active
claim that depends on it. If universal certification is required, route it to a
separately authorized `wu-session-writer-authority` eval; do not expand this
domain into catch-all actor auditing. Other unsupported cohorts use the
`unsupported-caller-cohort` disposition above.

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
  the target explicitly claims completeness for those semantic dimensions and
  the writer assertion is scoped to the supported cohort. A universal or other
  unsupported writer scope is an out-of-scope obligation, not a canonical field
  value.
- `readback_authority` and `readback_mode` are required only when the closed
  `readback_materiality_candidate` partition proves that live readback is
  material to that transition and claimed dimension. The only live-readback
  authority remains the top-level CLI path and same-support-key enforcement join
  described above. Otherwise both fields are
  `structurally-not-applicable` for that matrix.
- Any non-readback field the target purports to assert is compared and therefore
  becomes required for that assertion even when the broader dimension did not
  require its restatement. A target readback assertion first joins the exact
  closed materiality candidate/disposition; when readback is authority-proven
  not material, the assertion is compared with that matrix disposition without
  inventing a canonical readback value.

Explicit non-applicability is a matrix fact bound to the exact transition,
comparison dimension, target occurrence, and materiality candidate/disposition
occurrences. It is never inferred from source silence and never stored as an
invented canonical field value.

Every overlay/query-derived authority occurrence contributes only comparison
facts it actually asserts and receives its deterministic
operation/field/enforcement disposition. The assembler preserves every
contributing occurrence and source identity. For each matrix-required comparison
fact it requires exactly one authoritative owner value, exact owner context, and
an exact typed enforcement-path witness. Caller facts additionally require exact
operation-to-procedural-owner precedence and a caller-procedural witness. Two
sources classified as owners for the same fact are `multiply-owned-field` even
when their values happen to be equal; unequal values are
`authority-value-conflict`. Every constraint and corroboration is compared only
against the exact owner fact it constrains; inequality is retained as
`authority-value-conflict` rather than downgraded or erased. Corroborating or
constraining occurrences remain separate records and cannot become second
owners. Missing required values, owner contexts, or witnesses are
`missing-authoritative-field`. Structurally non-applicable facts require no value
and receive none. There is no majority vote, first-source choice, unstated
default, mapper-selected role downgrade, field borrowing, or source erasure.

The exact matrix join closes independently:

`discovered_transition_comparison_fact_assertion_keys == completed_operation_field_enforcement_disposition_keys`

`matrix_required_transition_comparison_fact_keys == exactly_one_owner_context_transition_comparison_fact_keys`

`constraint_and_corroboration_comparison_fact_assertion_keys == completed_exact_owner_fact_comparison_assertion_keys`

`owner_comparison_fact_keys == completed_typed_enforcement_path_witness_comparison_fact_keys`

`caller_owner_comparison_fact_keys == completed_procedural_owner_precedence_comparison_fact_keys`

An exact current occurrence that asserts fewer fields simply contributes that
narrower asserted-field set; it does not alter the matrix owner for another
field. Any inability to classify an exact source authority role or asserted
comparison fact is an adapter or
ownership obligation and prohibits `None`.

Each completed `transition_assembly` contains the assembly key, matrix identity,
every source fact ID, an ownership map from each required comparison fact to
exactly one source fact and owner context, every structural non-applicability
basis, compound assembled values,
constraints/corroboration and comparisons, enforcement-path witnesses, materiality
records where applicable, and the resulting structured `transition_id`.
`transition_id` equals the supported `transition_assembly_key` identity over
operation and activated caller/cohort/route/lifecycle domain using typed
structural equality. It contains no edge ordinal or circular source-established
edge key. Dimension-specific required fields cannot silently split or merge it.
Canonical transition candidates are these assembled results, never impossible
uniformly complete records required from one source occurrence.

Source-fact completion and transition-assembly completion close independently:

`admitted_transition_fact_occurrence_ids == completed_transition_fact_occurrence_ids`

`independently_discovered_transition_bearing_candidate_occurrence_ids == completed_transition_fact_or_explicit_disposition_occurrence_ids`

`admitted_executable_transition_fact_ids == enforcement_path_witness_transition_fact_ids`

`discovered_transition_comparison_fact_assertion_keys == completed_operation_field_enforcement_disposition_keys`

`applicable_transition_query_keys == completed_transition_assembly_keys`

`transition_dimension_matrix_keys == completed_transition_dimension_assembly_keys`

`completed_transition_ids == canonical_transition_ids`

`canonical_transition_operation_domain_keys == single_transition_supported_keys`

Every applicable canonical transition then receives one target comparison:

`applicable_transition_ids == completed_transition_comparison_ids`

A missing fact disposition cannot be hidden by a completed assembly, and an
applicable query key cannot be hidden by complete source-fact accounting.
`enumeration_complete` is true only when whole-blob discovery, every authority
raw-materiality inventory/partition/downstream identity closure, semantic
overlay, declaration-entry closure, independent query/disposition equality,
route-owner binding where activated, repeated-operation scope
admission, exact procedural-owner precedence, operation/field/enforcement
disposition, owner/constraint/corroboration comparison, operation support,
enforcement-path witness, readback-materiality partition/join, transition fact,
dimension matrix, assembly,
scope/applicability witness, and target comparison plus both reverse and
reciprocal multiplicity closure below close with no required comparison conflict.

For the known recurrence, the supported point-in-time non-readback facts are:

- `operation`: `phase0-reresolve`
- `source_conditions`: eligible existing open pre-PR, pre-Phase-3 session with
  policy identities requiring re-resolution
- `predecessor_or_order`: after eligible Phase 0 contract/topology resolution
  and before `phase3-bind`
- `destination_or_successor`: later `phase3-bind` composition after the required
  pre-Phase-3 re-resolution order
- `conditional`: `true`
- `owning_caller_or_domain`: normalized implementation-pipeline execution
  partition, plus the exact route topology only when a feature route is activated
- `sole_writer`: `{caller_cohort_identity:
  implementation-pipeline-resumer, writer_implementation_identity:
  tools/wu-session-migration/wu_session_migration.py}`
- `effects`: manifest-only change, no active row, with cold-start disposition and
  phase history preserved
- `readback_authority`: unresolved for every comparison dimension in which the
  closed materiality partition makes live readback material
- `readback_mode`: unresolved for every such material dimension
- `completed_cli_live_readback_enforcement_join`: unresolved
- `required_readback_obligation`:
  `cli-live-readback-enforcement-join-mismatch` or the exact
  caller-progression obligation produced by the unresolved occurrence

The executable declaration/dispatch owns operation. The exact
`agents/implementation-pipeline-orchestrator.md` `### Migration semantics for
in-flight WUs` ACR-310 paragraph owns caller-authenticated eligibility,
required fresh Phase 0 values, the established pre-Phase-3 order, and the
normalized implementation caller. Every applicable
`workflows/implementation-pipeline.md` and optimized-contract occurrence is
retained and compared only as a constraint/corroboration; equal repeated
restatements do not become owners. The operation-specific validator/projection
owns the pre-PR admission predicates, required-change/allowlist projection, and
preservation effects it enforces on every successful path. The shared
transaction owns commit/replacement outcome and the cohort-scoped writer; the
top-level CLI can own material readback only after the exact join in
`Readback materiality closure` closes. The current point-in-time evidence
supplies a generic caller-owned validation/readback requirement, but it does not establish the
operation-specific caller-to-top-level-CLI invocation, lock/recovery/readback
path, result check, and guarded continuation edge required by that join. An
activated feature/refactoring route owner may add only the witnessed
route/cohort/root topology binding.

Therefore the supported operation, eligibility, order, projection, transaction,
and cohort-scoped writer evidence remains decidable, but this example does not
claim a completed material readback join, a fully assembled readback dimension,
or `enumeration_complete`. The existing exact
`cli-live-readback-enforcement-join-mismatch` or caller-progression obligation is
mandatory wherever readback is material. This does not erase a separately
decidable edge-membership omission whose dimension matrix makes readback
structurally not applicable.

## Target transition accounting and discharge

Before canonical matching, the mapper uses the complete `transition` overlay of
`target_source_domain` to build `target_transition_occurrence_inventory`. It
preserves every block/descendant node, list item, operation wording, condition,
conditionality, predecessor/order, destination, effect, caller, writer,
readback, delegation, grouped/alternative construct, and residual occurrence
with exact source identity, span, and originating
`raw_materiality_candidate_identity`. Every occurrence receives exactly one
disposition: `admitted-target-assertion`, `authorized-non-transition`,
`non-fire-context`, or `ambiguous/unsupported`.

Each admitted assertion has a `claimed_fields` presence map for all assembled
transition fields. It interprets only fields present in the target. An absent
field is `unasserted`; a purported but uninterpretable field is ambiguous and
comparison-blocking. Explicit inequality is never converted into absence. Each
assertion also receives one structural `target_assertion_key` from the exact
target identity, assertion occurrence identity, and explicit group/member
identity where present; no raw strings are delimiter-joined.

Before canonical discharge, every assertion also receives exactly one
`sequence_assertion_role`: `governed-sequence-member`,
`explicit-group-member`, `non-sequence-corroboration`, or
`non-sequence-explanatory-restatement`. The role is established by exact list,
table, prose-sequence, group/member, and governing-context syntax. A
non-sequence corroboration/restatement is retained and compared for
contradictions where material, but cannot discharge a canonical transition and
cannot be counted a second time as a sequence member. Ambiguous role assignment
is `target-transition-accounting` indeterminate.

Target accounting requires:

`target_transition_occurrence_ids == target_transition_disposition_occurrence_ids`

`admitted_target_assertion_ids == completed_target_assertion_ids`

`applicable_transition_ids == completed_transition_comparison_ids`

Reverse target closure independently requires:

`admitted_target_assertion_keys == completed_target_assertion_keys`

`admitted_target_assertion_keys == governed_sequence_member_assertion_keys + explicit_group_member_assertion_keys + non_sequence_corroboration_assertion_keys + non_sequence_explanatory_restatement_assertion_keys`

`completed_target_assertion_keys == completed_canonical_comparison_or_discharge_assertion_keys + authority_proven_non_applicable_assertion_keys + multiplicity_drift_assertion_keys + indeterminate_or_contradicted_or_unmatched_assertion_keys`

`explicit_target_group_member_keys == completed_target_group_member_keys`

`completed_target_group_member_keys == completed_canonical_comparison_or_discharge_group_member_keys + authority_proven_non_applicable_group_member_keys + indeterminate_or_contradicted_or_unmatched_group_member_keys`

Every `+` is a disjoint exact key-set partition. Duplicate assertion keys,
duplicate group-member keys, duplicate disposition, one key in multiple
partitions, or unequal left/right sets is
`target-assertion-reverse-closure-mismatch`. Each terminal assertion/member
record has exactly one outcome:
`completed-canonical-comparison`, `completed-delegated-discharge`,
`authority-proven-non-applicable`, `multiplicity-drift`, `indeterminate`,
`contradicted`, or `unmatched`, with exact evidence and candidate canonical IDs. `indeterminate`
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

Reciprocal sequence closure is independent from reverse assertion closure. For
an exact or complete-implied `edge-membership` or `transition-semantics`
sequence, each applicable canonical transition must be discharged by exactly one
governed sequence-member assertion or explicit group-member assertion:

`applicable_transition_ids == transition_to_governed_sequence_member_discharge_index_transition_ids + omitted_transition_ids`

`governed_sequence_member_and_group_member_assertion_keys == completed_sequence_member_to_transition_witness_assertion_keys`

The first `+` is a disjoint exact partition. A zero-member transition is the
resolved omission drift already defined. For each indexed transition `t`, clean
reciprocity requires:

`cardinality(transition_to_governed_sequence_member_discharge_index[t]) == 1`

A materially distinct repeated lifecycle edge for the same canonical operation
never reaches this rule: the pre-assembly scope gate emits
`repeated-operation-transition-unsupported`. Repeating one assertion or a
materially equivalent assertion for the admitted single edge never creates a new
canonical identity. It must already be an explicit non-sequence
corroboration/explanatory restatement or remain a duplicate governed-sequence
member for multiplicity-drift disposition.

After every assertion uniquely maps by typed identity, the lowest exact governed
sequence ordinal is retained as the primary discharge record solely so the
duplicate set is deterministic. Every later duplicate governed-sequence
assertion for that same admitted single edge is partitioned
exactly once:

`duplicate_governed_sequence_assertion_keys == multiplicity_drift_assertion_keys + contradicted_duplicate_assertion_keys + unmatched_duplicate_assertion_keys + indeterminate_duplicate_assertion_keys`

The `+` is a disjoint exact key partition. A duplicate equal assertion is
`multiplicity-drift` and establishes conditional-wiring drift; unequal,
nonmatching, or uninterpretable duplicate assertions retain their respective
outcomes and obligations. No duplicate assertion can be silently accepted as
corroboration after being classified as a governed sequence member. Explanatory
restatements must already be explicitly dispositioned non-sequence/corroboration
and therefore cannot count twice. These reciprocal equalities close before
`enumeration_complete` or `None`. The resulting
`reciprocal_sequence_multiplicity_closure_state` is `exact`, `drift`, or
`indeterminate`: a fully dispositioned duplicate produces resolved `drift`, while
an unclassified duplicate produces `indeterminate`. Only `exact` can support
`None`.

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
candidate partition closes as material. Thus exact cohort-scoped `sole_writer`
and CLI-only live readback are never lost, defaulted, invented for unrelated
edges, or imposed on a claim that did not make them material.

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

The at-most-one assertion-to-transition rule and the reciprocal exactly-one
transition-to-sequence-member rule both apply. Satisfying either direction does
not imply the other. Group records satisfy reciprocity through their distinct
explicit member keys, never through the group parent as a second discharge.

Every assertion-to-transition witness records asserted and canonical values,
per-field `equal`, `unequal`, `unasserted`, or
`structurally-not-applicable-by-dimension`, the sequence-completeness dimension,
matrix identity, candidate transition IDs, unique or grouped discharge decision,
and exact evidence. `observed_treatment` is one of
`included`, `delegated`, `omitted`, `contradicted`, `multiplicity-drift`,
`not-applicable`, or `indeterminate`.

The ticket-required `wiring_transition` is an aggregate record containing:

- `evaluated_repository_identity`
- `target_claim_identity`
- `enclosing_governing_context_inventory`
- `target_source_domain`
- `target_scope_identity`
- `route_owner_binding`
- `route_owner_applicability_witness`
- `delegate_resolution`
- `lifecycle_sequence_completeness`
- `comparison_authority_discovery_domain`
- `raw_materiality_candidate_inventory`
- `raw_materiality_candidate_disposition_index`
- `raw_materiality_candidate_closure`
- `authority_semantic_overlays`
- `comparison_authority_query_inventory`
- `transition_operation_field_enforcement_authority_matrix`
- `caller_procedural_owner_precedence_index`
- `readback_materiality_candidates`
- `readback_materiality_disposition_index`
- `transition_authority_fact_inventory`
- `repeated_operation_scope_disposition_index`
- `enforcement_path_witnesses`
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
- `sequence_assertion_role_index`
- `target_group_member_keys`
- `target_group_member_disposition_index`
- `target_assertion_reverse_closure`
- `transition_to_governed_sequence_member_discharge_index`
- `reciprocal_sequence_multiplicity_closure`
- `duplicate_sequence_member_assertion_dispositions`
- `transition_comparisons`
- `omitted_transition_ids`
- `contradicted_transition_ids`
- `multiplicity_drift_assertion_ids`
- `indeterminate_transition_ids`
- `enumeration_complete`
- `evidence_paths`

For the current `Manifest storage` target, the absence of
`phase0-reresolve` operation/order yields an omitted edge for an
edge-membership-complete sequence even though the point-in-time material
readback dimension above is unresolved: this matrix makes readback structurally
not applicable, and the supported operation plus edge/order evidence decides the
omission independently. If a neighboring transition-semantics-complete
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
governor and complete structural-block/composite target closure, per-command
claimed-domain partition, independent target/authority raw-materiality
admission, bounded whole-blob authority overlay/discovery,
declaration-entry and query closure, executable support, activation,
classification, supported scope/applicability, target accounting, and set
comparison complete. `domain_contradictions` are retained beside their
wrong-domain token contribution to `extra_operations`. Repository-global
membership never requires caller adoption; a supported caller-scoped applicable
subset does.

### Conditional-wiring drift

An active-affirmative generic lifecycle claim with `claim_completeness` `exact`
or `complete-implied` and lifecycle-sequence completeness `edge-membership` or
`transition-semantics` omits or contradicts an applicable canonical transition,
or maps duplicate governed sequence members to its admitted single transition as
multiplicity drift, in the dimension it claims complete. A
transition-semantics-complete conditional
edge also drifts when condition or conditionality is absent after complete target
accounting. Indeterminate raw-materiality admission, authority overlay,
comparison-fact ownership,
enforcement path,
readback materiality, assembly, target interpretation, or discharge is an
evidence gap, not drift and not `None`.

Two materially distinct sequence edges for one canonical operation are not a
supported drift case. They emit
`repeated-operation-transition-unsupported` before assembly/discharge and
prohibit a wiring drift or `None` decision.

These are documentation-contract drift behaviors. They are not runtime writer,
parser, request-validation, transaction, scheduler, recovery, namespace,
availability, protected-state, merge-verification, or external-action findings.

## Non-fire cases

A future `None` follows one of two closed paths:

- A classification non-fire requires exact identity, complete enclosing-governor
  inventory and governor-to-envelope closure, one complete
  `target_source_domain`, every component equality, complete independent target
  raw-materiality inventory/partition/downstream identity closure, every
  role-overlay equality, resolved activation and polarity, and every fact needed
  for that exact disposition.
  Clearly partial, non-runtime-only, non-active, and negative envelopes do not require
  unrelated operation support or transition assembly after making the canonical
  comparison domain inapplicable. Delegated and scoped-inapplicable paths also
  require exact `target_scope_identity`, same-commit `delegate_resolution`, and
  complete per-member applicability witnesses. A membership-only disposition
  bypasses only wiring, not an applicable complete membership comparison.
- An active complete-claim comparison non-fire additionally requires resolved
  supported scope and applicability, all governor/component/target-overlay
  equalities, per-command claimed-domain partition, complete independent
  target/authority raw-materiality inventories, partitions, exclusions, and
  downstream identity equalities, whole-blob authority semantic overlays,
  declaration-entry and independent query equalities, aligned
  per-member executable support, caller authority only for supported
  caller-scoped membership or wiring, exact route-owner binding only for an
  activated feature topology, repeated-operation scope admission, exact
  procedural-owner precedence, operation/field/enforcement ownership and every
  fact-local constraint/corroboration comparison, same-support-key enforcement witnesses,
  closed readback materiality and CLI enforcement joins where applicable,
  complete dimension-scoped typed transition assembly, complete applicability
  partitions, complete unique/group discharge, reciprocal exactly-one sequence
  multiplicity, and exact reverse assertion/group-member closure.

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
  included semantic governor or text inside its complete admitted envelope
  independently implies completeness, after every potentially material raw
  occurrence is admitted or independently excluded by closed grammar/section
  evidence.
  This includes an `Examples only:` introductory paragraph plus its immediately
  following governed list only after governor and composite/component closure
  succeeds. A completeness heading governing that neighbor is indeterminate,
  not this non-fire.
- A non-runtime-only claim lists support commands such as `capture-evidence`,
  `dry-run`, `apply`, or `validate-pre-pr-readback` and makes no runtime
  membership claim, with every occurrence assigned to its support/non-runtime
  domain by exact target syntax.
- A mixed claim explicitly partitions every support/non-operation occurrence
  outside the asserted runtime subset, while its runtime side has every
  applicable member and no unsupported or domain-contradicting extra.
- A membership-only claim differs only in ordering because membership authority
  is a set.
- A repository-global membership claim includes every executable-supported
  declared member even when no workflow caller has adopted one; the absent caller
  is structurally non-applicable, not a gap and not proof of workflow adoption.
- A membership-only claim has `lifecycle_sequence_completeness: not-claimed`, so
  conditional wiring is not applicable.
- An edge-membership-complete sequence uniquely names every applicable edge in
  order with exactly one governed sequence-member discharge per canonical
  operation/transition, no materially distinct repeated edge for one operation,
  and no duplicate governed-sequence surplus. This proves only edge
  membership and does not claim complete transition semantics.
- A transition-semantics-complete sequence includes or validly delegates every
  applicable conditional edge's condition and conditionality, and every other
  semantic dimension it expressly claims complete compares equal, with
  reciprocal exactly-one sequence multiplicity closure.
- An explicit identity-bound grouped/alternative construct covers every member
  it discharges.
- A supported implementation-pipeline/resumer lifecycle-partitioned caller omits
  operations or transitions it does not own
  and its identity-bound target scope plus authority-backed per-member witnesses
  prove the complete applicable/inapplicable partition.
- Historical, quoted, proposal-only, fixture, and negative-example occurrences
  receive their explicit non-fire activation/polarity disposition and are not
  active assertions.
- A selected ineligible implementation-pipeline/resumer cohort omits a transition
  that identity-bound authority proves inapplicable through its exact witness,
  or occurrence-only evidence
  makes no completeness claim. One sampled WU never proves cohort exclusion.
- A feature-direct or feature-routed-refactoring claim may reach this non-fire
  only after the exact same-commit route owner, applicable sidecar, normalized
  implementation-caller/cohort/root binding, route applicability witness, and
  implementation-owned progression facts all close. Another parent-route or
  universal writer claim is not converted into this non-fire and remains out of
  scope/indeterminate with an exact obligation.
- Wake/scheduler observers, generic helpers, alternate namespaces, rollback,
  recovery, cleanup, or other latent capabilities exist outside the required
  comparison facts. Their presence is not this eval's unwanted behavior.

Incomplete required comparison evidence is not a non-fire. A potentially
material occurrence in a bounded target or authority context that is neither
semantically admitted nor independently excluded is not optional adjacent
provenance. Optional adjacent
provenance may remain unavailable without preventing `None`; an exact observed
acting-context conflict blocks only the required comparison fact it directly
supplies or contradicts.

No `None` result says that another target, the document, repository, runtime,
merge, or external state is clean.

## Evidence-state contract

Evidence state is preserved per axis and then aggregated without erasing either
axis. In the table, a `LOW` gap is the affected axis's `gap_severity`; the
finding's aggregate `severity` may remain `MEDIUM` or `HIGH` when a mismatch is
independently established on that axis or the other axis.

| `evidence_state` | Minimum evidence | Permitted decision behavior |
|---|---|---|
| `complete` | Common identity, enclosing-governor closure, and one complete structural-block or bounded-composite target domain resolve. Either a classification non-fire closes every fact required for that exact disposition, including independent target raw-materiality admission, per-command claimed-domain, and delegate/scope witnesses where used, or an active-affirmative complete claim closes every governor/component, target/authority raw-materiality inventory/partition/downstream identity equality, target and authority semantic overlay, declaration-entry/query equality, per-member executable support/path inventory, each activated detailed-command use, supported scope-required caller applicability, activated route-owner binding, readback materiality, repeated-operation scope admission, exact procedural-owner precedence, operation/field/enforcement ownership and fact-local constraint/corroboration comparison, same-key enforcement witnesses, applicability partition, dimension matrix, transition fact/assembly, unique/group discharge, reciprocal sequence multiplicity for each admitted single edge, and reverse assertion/group-member closure required by the claimed dimensions. | Emit drift when present or `None` only when every axis is absent/inapplicable and obligation-free. Inapplicable comparison domains are not required merely to make a partial, non-runtime, non-active, or negative classification clean. |
| `degraded` | Every required comparison fact resolves but optional trace, report, audit, final-diff, or non-decisional provenance is unavailable. | A direct mismatch may emit reduced-confidence drift, and an obligation-free non-fire may emit `None`. Optional evidence loss cannot erase resolved comparison facts or create an unsupported repair. |
| `evidence-gap` | A required source role, governor disposition, raw-materiality candidate/disposition/exclusion/projection, claimed-domain record, authority overlay, declaration entry, support/path fact, activated detailed-command fact, route-owner binding, transition comparison-fact disposition, procedural-owner context, readback materiality candidate, enforcement witness, dimension fact, assembly, target assertion, reciprocal multiplicity closure, reverse assertion/group-member closure, classification, scope/applicability/delegation witness, or parser/adapter failure represented inside the admitted normalized bundle is unavailable or uninterpretable. | Give the unresolved fact `LOW` gap severity with at least one exact axis/fact-qualified `failure_obligation` joined to its root cause. Use axis outcome `indeterminate` only when no mismatch on that axis is independently established; otherwise retain `present`, its established severity and safe repair, plus the separate gap obligation. Preserve independent drift on either axis and derive aggregate severity by the closed rule below. Never repair from an unresolved fact or use `None`. |
| `identity-conflict` | Required evidence has mixed, unbound, unverifiable, absent-at-identity, or currentness-mismatched identity. | Emit the structured `LOW` gap finding, preserve every available identity, and stop dependent comparison. Never use `None`. |
| `selector-invalid` | Target path/anchor is noncanonical, escaping, absent, non-unique, is neither one complete block nor one valid bounded composite, or cannot produce a complete target source domain. | Emit the gap finding with the attempted selector, every resolution, component, and parse/source-map outcome; do not classify, compare, repair, or use `None`. |
| `target-domain-incomplete` | Any potential-governor inventory/disposition, governor-to-envelope equality, admitted component, component union, governed content span, parse node, byte/code-point source map, role overlay, occurrence, or disposition equality fails; a semantic/ambiguous excluded governor, multiple governors/content blocks, intervening unowned blocks, unbounded context, or required semantics outside the selected envelope exists. | Emit the gap finding with completed governor/component/overlay evidence preserved. Context outside the admitted envelope cannot be borrowed to repair the domain and `None` is prohibited. |
| `raw-materiality-admission-incomplete` | Any bounded target or activated authority role lacks a complete conservative pre-semantic candidate inventory; a candidate is not exactly partitioned; a claimed exclusion lacks an independently checkable closed grammar/section rule; a free-form reason performs exclusion; an unsupported/ambiguous candidate remains; or raw identities do not close through overlays, queries, transition/command candidates, and dispositions. | Emit the exact axis/fact-qualified `raw-materiality-admission` obligation with every raw occurrence and completed partition/projection retained. Potentially material text cannot become non-decisional by mapper choice, and `None` is prohibited. |
| `activation-polarity-indeterminate` | The complete admitted envelope cannot distinguish active/historical/quoted/proposal/fixture use or affirmative/negative polarity. | Emit the gap finding and preserve every admitted-envelope occurrence. Do not convert ambiguity to active or to a non-fire `None`. |
| `claim-classification-indeterminate` | Any required completeness, claim-wide or per-command claimed domain/subset, lifecycle-sequence, scope, writer scope, or membership-applicability dimension is ambiguous or conflicting. | Emit the gap finding, preserving independently resolved dimensions and the complete envelope. Do not compare the unresolved fact or use `None`. |
| `authority-query-incomplete` | A discovery blob, authority semantic overlay, declaration-entry oracle, contract-applicability query, operation/caller query, semantic projection, query disposition, support-key equality, independently discovered transition-candidate equality, or query-to-assembly/comparison equality fails after raw-materiality admission closes. | Emit the structured `LOW` gap finding with all completed raw identities, overlays, query IDs, and facts. A preselected semantic span cannot substitute and `None` is prohibited. |
| `delegate-scope-indeterminate` | A delegate or target scope/caller/cohort/lifecycle identity is missing, ambiguous, stale, sampled-only, unbound, `unsupported-caller-cohort`, or lacks the exact applicability partition; an activated feature topology lacks exactly one route owner, applicable sidecar closure, normalized implementation-caller/cohort/root binding, or route witness; a repository-global writer assertion is out of scope. | Emit the structured `LOW` gap finding with every candidate and witness. Do not infer exclusions, promote a route owner to child progression, certify a universal writer, or use `None`. |
| `transition-scope-unsupported` | Complete authority or target discovery contains two materially distinct sequence edges for the same canonical operation in one activated caller/cohort domain. | Emit `repeated-operation-transition-unsupported` with exact source occurrences before canonical assembly/discharge. Do not create per-edge projections, emit wiring drift, or use `None`; preserve an independently resolved membership axis. |
| `authority-conflict` | Required declaration, support, successful path, exact procedural-owner precedence, operation/field/enforcement ownership/value, route-owner binding, cohort-scoped `sole_writer`, readback materiality/CLI join, enforcement witness, caller/progression, fact-local constraint/corroboration, matrix, or assembly fact conflicts. | Emit the structured `LOW` gap finding and preserve every source occurrence/conflict. Never vote, default, downgrade, erase, repair from the conflicting fact, or use `None` for the dependent axis; retain any independently established mismatch and its supported repair. |
| `enforcement-path-incomplete` | Any required owner fact lacks its exact typed owner-context witness, a caller premise/value is not joined through request authorization and guarded progression, a route witness crosses into child progression, a required executable transition fact lacks exact same-support-key closure, a successful public CLI path bypasses its validator/projection/readback/writer fact, or a retained occurrence is dead or not governing. | Keep the occurrence non-decisional/corroborating or emit the exact authority gap. Preserve every procedure/control path and endpoint; do not promote the fact or use `None`. |
| `readback-materiality-incomplete` | An applicable caller/progression candidate is missing, uninterpretable, not exactly partitioned material/not-material, or a material candidate lacks the top-level CLI lock/recovery/readback enforcement join. | Emit the exact lifecycle-authority or CLI-live-readback obligation. Query silence cannot establish non-materiality and `None` is prohibited. |
| `target-discharge-indeterminate` | One assertion is compatible with multiple canonical transitions for different operations without an explicit complete group/alternative construct, sequence/non-sequence role is ambiguous, group membership is incomplete, reciprocal single-edge multiplicity is unresolved, a duplicate governed-sequence assertion is not dispositioned, or assertion/group-member reverse closure fails. Materially distinct repeated edges for one operation must already have stopped at `transition-scope-unsupported`. | Emit the gap finding unless a separate omission, contradiction, or multiplicity drift is already decidable. Mark none silently included, preserve every assertion/member and candidate, and never use `None` for the affected wiring axis. |

Each axis has one closed `authority_state`: `conflict`, `incomplete`, `aligned`,
or `not-applicable`, scoped only to facts required for that exact axis. Aggregate
`authority_state` is the first state present in this precedence:
`conflict > incomplete > aligned > not-applicable`. It preserves both per-axis
states and never describes all runtime actors or capabilities. A
repository-global membership axis cannot become `incomplete` merely because
caller authority is structurally non-applicable.

## Failure obligations

Failure identity has two levels. `root_causes` is a deterministic injective list
of actual source failures. `failure_obligations` is a deterministic injective
list of exact axis/fact duties blocked by those root causes. `evidence_role` is
exactly one of these closed role identifiers:

- `evaluated-repository-identity`
- `declaration-authority`
- `target-governing-context`
- `target-source-domain`
- `target-activation-polarity`
- `target-claim-classification`
- `target-command-claimed-domain`
- `comparison-authority-discovery`
- `raw-materiality-admission`
- `authority-semantic-overlay`
- `executable-operation-support`
- `enforcement-path-witness`
- `detailed-command-evidence`
- `target-scope-delegation-applicability`
- `route-owner-binding-applicability`
- `writer-authority-scope`
- `lifecycle-authority-facts`
- `caller-procedural-owner-precedence`
- `readback-materiality`
- `cli-live-readback`
- `transition-fact-ownership`
- `transition-scope`
- `transition-dimension-matrix`
- `transition-assembly`
- `target-command-accounting`
- `target-transition-accounting`
- `target-discharge`
- `parser-adapter-attribution`

Every `root_causes` record contains:

- `root_cause_identity`, structured from `evidence_role`, `source_identity`,
  `normalized_cause`, and `original_occurrence_identity`
- `evidence_role`
- `source_identity`
- `normalized_cause`
- `original_occurrence_identity`
- exact original occurrence and source evidence
- `original_error`, when applicable

Every `failure_obligations` record contains:

- `obligation_identity`, structured from `root_cause_identity`,
  `affected_axis`, and `required_comparison_fact`
- `root_cause_identity`
- `evidence_role`, exactly equal to its joined root cause's role
- `source_identity`, exactly equal to its joined root cause's source
- `normalized_cause`, exactly equal to its joined root cause's cause
- `original_occurrence_identity`, exactly equal to its joined root cause's
  original occurrence
- `affected_axis`
- `required_comparison_fact`

These are the complete eval-owned obligation fields. A failure obligation
preserves the exact cause, source role and occurrence, affected axis, blocked
fact, and identity joins; it contains no recovery disposition, recovery owner,
ordered recovery actions, or terminal condition.

One root cause may produce multiple obligations for different axes or required
comparison facts without collision. Every obligation identifies exactly one
blocked fact on exactly one activated axis. A shared source failure is recorded
once under its actual original occurrence; dependent obligations must reference
that root and may not synthesize another source occurrence. Distinct actual
failure occurrences remain distinct roots. Latent or adjacent capabilities with
no blocked fact do not receive roots or obligations; they remain non-decisional
provenance or residual uncertainty. A derived `failure_cause` summary may
describe unique roots but cannot replace, close, deduplicate, or authorize them.

Forward and reverse causal joins close before result construction:

`root_cause_ids == root_cause_to_obligation_index_root_cause_ids`

`failure_obligation_ids == obligation_to_root_cause_index_obligation_ids`

`failure_obligation_ids == union(root_cause_to_obligation_index.values)`

`root_cause_ids == unique(obligation_to_root_cause_index.values)`

`root_cause_to_obligation_pair_ids == inverted_obligation_to_root_cause_pair_ids`

For every root `r`, `root_cause_to_obligation_index[r]` is exact and non-empty.
For every obligation `o`, `obligation_to_root_cause_index[o]` equals exactly its
one `root_cause_identity`, and `o` appears exactly once in that root's forward
set. Missing, empty, extra, duplicate, or unequal joins make result construction
nonconforming.

Per-axis and per-fact projections also close exactly and remain non-empty for
every activated blocked projection:

`failure_obligation_ids == union(axis_to_obligation_index.values)`

`failure_obligation_ids == union(required_comparison_fact_to_obligation_index.values)`

`failure_obligation_ids == union(axis_fact_to_obligation_index.values)`

Every obligation appears exactly once in its `affected_axis` projection, exactly
once in its `required_comparison_fact` projection, and exactly once in the paired
axis/fact projection. Each projection value equals the IDs selected directly from
`failure_obligations`; no root-level deduplication may remove a qualified duty.

`missing_evidence_roles` is a closed derived field, never `null`. Its aggregate
value is exactly:

`lexicographically_sort(unique([joined_root_cause(o).evidence_role for o in failure_obligations if o.required_comparison_fact is blocked on o.affected_axis]))`

Every obligation in this eval blocks a required fact on its named activated
axis; optional and non-decisional evidence never creates an obligation.
Therefore the aggregate projection includes every qualified obligation's joined
root role and only those roles. A finding with no blocking obligation has
`root_causes: []`, `failure_obligations: []`, and
`missing_evidence_roles: []`, including a pure drift finding. Each axis and each
required comparison fact retains the same exact joined-role projection over its
obligation IDs. The aggregate value equals the lexicographically sorted unique
union of the axis lists and of the fact lists.

The producer must establish sequence equality, not merely set resemblance:

`missing_evidence_roles == lexicographically_sorted_unique_joined_root_cause_role_projection`

A `null`, missing, unknown, stale, duplicate, unsorted, omitted, or extra role
makes the conceptual result nonconforming. Original occurrence, exact error and
cause remain authoritative in `root_causes`; affected axis/fact and their exact
root/source identity joins remain authoritative in `failure_obligations`. The
summary cannot close, replace, deduplicate, or authorize either level.

For a pure drift finding, `root_causes`, `failure_obligations`, `failure_cause`,
all causal indexes, all axis/fact obligation projections, and
`missing_evidence_roles` are empty. The conceptual sets are also empty for
`None`, which carries no finding fields. Every non-clean required state already
represented in the normalized bundle has at least one root, at least one joined
qualified obligation, and at least one exactly projected missing role. One
blocked fact does not erase an independently completed mismatch on the same axis,
and one blocked axis does not erase a completed independent axis.

Every gap finding carries all available repository, target, scope, delegate,
governor, raw-materiality admission, authority-overlay/query, support/path,
applicability, readback materiality, route binding, ownership matrix,
repeated-operation scope, assembly,
target-accounting, root-cause/obligation joins, and independent-axis outcomes. A
value is `null` only when genuinely
unavailable, not merely unfinished. At least one exact cause-preserving
`root_cause` and one exact axis/fact-qualified `failure_obligation` are mandatory.

At `WRITE`, failure obligations authorize no action. Any retry, runner
reconciliation, external owner, or terminal state belongs to a separately
authorized rollout contract. A fresh result does not close a prior obligation,
and this eval neither assigns that rollout policy nor proves durable closure.

Cause-specific obligations include, where applicable:

- repository and target identity causes named above;
- `target-block-zero-match`, `target-block-multi-match`,
  `target-block-partial-node`, `target-parse-ambiguous`,
  `target-composite-multiple-governors`,
  `target-composite-multiple-content-blocks`,
  `target-composite-intervening-unowned-block`,
  `target-composite-unbounded-context`,
  `target-governor-inventory-mismatch`,
  `target-governor-disposition-mismatch`,
  `target-governor-envelope-indeterminate`,
  `target-governor-envelope-closure-mismatch`,
  `target-component-partition-mismatch`,
  `target-source-domain-incomplete`,
  `required-semantics-outside-target-domain`, and every role-overlay equality;
- `ambiguous-activation`, `ambiguous-polarity`,
  `ambiguous-claim-completeness`, `ambiguous-command-domain`,
  `ambiguous-command-claimed-domain`,
  `command-claimed-domain-partition-mismatch`,
  `command-subset-identity-unbound`,
  `ambiguous-lifecycle-sequence-completeness`, `ambiguous-scope`, and
  `ambiguous-membership-applicability`;
- `comparison-authority-discovery-coverage-mismatch`,
  `raw-materiality-candidate-inventory-mismatch`,
  `raw-materiality-candidate-partition-mismatch`,
  `raw-materiality-independent-exclusion-invalid`,
  `raw-materiality-downstream-identity-mismatch`,
  `raw-materiality-potential-fact-unadmitted`,
  `authority-semantic-overlay-key-mismatch`,
  `authority-semantic-overlay-partition-mismatch`,
  `authority-semantic-overlay-source-map-mismatch`,
  `authority-semantic-overlay-unsupported-or-ambiguous-syntax`,
  `declaration-entry-closure-mismatch`,
  `authority-query-selector-failure`, `authority-query-parse-failure`,
  `authority-query-occurrence-disposition-mismatch`,
  `operation-support-key-mismatch`, and
  `support-query-completion-mismatch`,
  `successful-public-cli-path-inventory-mismatch`,
  `support-fact-to-path-mismatch`, `enforcement-path-incomplete`,
  `enforcement-path-bypass`, `dead-validator-or-projection`,
  `comparison-scope-support-requirement-mismatch`, and
  `caller-authority-required-for-global-membership`;
- `delegate-resolution-missing`, `delegate-resolution-ambiguous`,
  `target-scope-unbound`, `target-scope-sampled-only`,
  `unsupported-caller-cohort`, `route-owner-zero-match`,
  `route-owner-multi-match`, `route-owner-sidecar-closure-mismatch`,
  `route-owner-binding-indeterminate`,
  `route-owner-applicability-witness-mismatch`,
  `repository-global-writer-claim-out-of-scope`,
  `operation-applicability-partition-mismatch`, and
  `transition-applicability-partition-mismatch`;
- `repeated-operation-transition-unsupported`,
  `transition-fact-accounting-mismatch`, `missing-authoritative-field`,
  `caller-procedural-owner-precedence-mismatch`,
  `operation-field-enforcement-disposition-mismatch`,
  `matrix-owner-cardinality-mismatch`,
  `constraint-corroboration-owner-fact-comparison-mismatch`,
  `multiply-owned-field`, `authority-value-conflict`,
  `readback-materiality-candidate-inventory-mismatch`,
  `readback-materiality-partition-mismatch`,
  `readback-materiality-progression-uninterpretable`,
  `cli-live-readback-enforcement-join-mismatch`, and
  `transition-dimension-matrix-mismatch`, `transition-assembly-mismatch`, and
  `transition-query-comparison-mismatch`;
- `target-presentation-accounting-mismatch`,
  `command-occurrence-accounting-mismatch`,
  `full-command-operand-closure-mismatch`,
  `malformed-full-target-command`, and
  `catalog-operation-token-ambiguous`;
- `target-transition-assertion-ambiguous`,
  `target-transition-accounting-mismatch`,
  `sequence-assertion-role-ambiguous`,
  `target-discharge-ambiguous`, `target-assertion-duplicate-key`,
  `target-assertion-reverse-closure-mismatch`,
  `reciprocal-sequence-discharge-mismatch`,
  `duplicate-sequence-member-disposition-mismatch`,
  `target-group-member-duplicate-key`,
  `target-group-member-equality-mismatch`, and
  `target-group-coverage-mismatch`;
- normalized-bundle `unresolved-source-or-adapter-attribution`,
  normalized-bundle `unsupported-adapter`, and
  `detailed-command-required-occurrence-missing-or-stale`.

At `WRITE`, a parser or adapter failure is eval-owned only when an upstream owner
already represented the original failure and source identity inside the admitted
normalized bundle. It then remains
`unresolved-source-or-adapter-attribution`; this eval does not let the failing
adapter assign source blame or terminal source invalidity to itself. A failure
before normalized-input commit is external and creates no eval root cause or
obligation because `evaluate` was not called.

### Result ownership boundary

This eval owns only comparison semantics over one admitted normalized bundle and
construction of the conceptual structured `finding | None`. It does not own
repository/source resolution, source reads, structural parsing, adapter
execution, interruption recovery, or normalized-input commit before the call. A
finding has no transport state, delivery state, receipt, fallback, attempt, or
terminal-publication field. This specification makes no claim that a normalized
input was committed or that a constructed result was serialized, delivered,
committed, read back, acknowledged, deduplicated, retried, reconciled, or
consumed.

Failure before the call or after result construction is external to both axes
and cannot become a failure obligation, a third eval result alternative, or
evidence that changes
`documentation_drift_outcome`, aggregate severity, authority, confidence, or
suggested action. A call that never occurred, a nonconforming future evaluator,
or an unavailable result is not `None`. The separately authorized runner
contract required before `ROLL_OUT` owns what happens outside this conceptual
boundary.

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
- `enclosing_governing_context_inventory`
- `target_governor_disposition_index`
- `target_governor_to_envelope_closure`
- `target_source_domain`
- `target_source_component_inventory`
- `target_source_role_overlays`
- `raw_materiality_candidate_inventory`
- `raw_materiality_candidate_disposition_index`
- `raw_materiality_candidate_closure`
- `target_context_source_span`
- `target_claim_content_source_span`
- `target_context_occurrence_inventory`
- `target_activation`
- `target_polarity`
- `target_activation_polarity`
- `claim_completeness`
- `command_domain`
- `command_claimed_domain_records`
- `claimed_command_domain_partition`
- `domain_contradictions`
- `lifecycle_sequence_completeness`
- `claim_scope`
- `target_scope_identity`
- `route_owner_binding`
- `route_owner_applicability_witness`
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
- `raw_tool_locator_occurrences`
- `tool_locator_dispositions`
- `bounded_logical_entrypoint_mappings`
- `raw_catalog_operation_occurrences`
- `catalog_operation_interpretations`
- `comparison_authority_discovery_domain`
- `comparison_authority_discovery_coverage`
- `authority_semantic_overlays`
- `authority_semantic_overlay_closure`
- `runtime_operations_declaration_entry_closure`
- `comparison_authority_query_inventory`
- `comparison_authority_query_results`
- `comparison_authority_raw_occurrence_inventory`
- `comparison_authority_raw_occurrence_dispositions`
- `derived_authority_semantic_spans`
- `authority_constraint_inventory`
- `operation_support`
- `successful_public_cli_path_inventory`
- `enforcement_path_witnesses`
- `detailed_command_evidence`
- `readback_materiality_candidates`
- `readback_materiality_disposition_index`
- `readback_materiality_cli_enforcement_joins`
- `transition_authority_fact_inventory`
- `caller_procedural_owner_precedence_index`
- `transition_operation_field_enforcement_authority_matrix`
- `transition_operation_field_enforcement_disposition_index`
- `repeated_operation_scope_disposition_index`
- `writer_claim_scope`
- `transition_dimension_matrix`
- `transition_assemblies`
- `target_transition_occurrence_inventory`
- `target_transition_occurrence_dispositions`
- `target_transition_assertions`
- `target_assertion_keys`
- `target_assertion_to_canonical_transition_witnesses`
- `target_discharge_records`
- `target_assertion_disposition_index`
- `sequence_assertion_role_index`
- `target_group_member_keys`
- `target_group_member_disposition_index`
- `target_assertion_reverse_closure`
- `transition_to_governed_sequence_member_discharge_index`
- `reciprocal_sequence_multiplicity_closure`
- `duplicate_sequence_member_assertion_dispositions`
- `documentation_drift_outcome`
- `authority_state`
- `authority_conflicts`
- `root_causes`
- `root_cause_to_obligation_index`
- `obligation_to_root_cause_index`
- `failure_obligations`
- `axis_to_obligation_index`
- `required_comparison_fact_to_obligation_index`
- `axis_fact_to_obligation_index`
- `failure_cause`
- `non_decisional_provenance`
- `residual_uncertainty`

No merge-verification or ACR-398 consumption field is part of the trace or
finding.

For resolved drift, `eval_id` is
`wu-session-runtime-operation-catalog-drift`, `authority_symbol` is
`RUNTIME_OPERATIONS`, all available collections are deterministic, and exact
target, activation, comparison-domain, source-fact, route binding when activated,
repeated-operation scope, assembly, target assertion, governor, claimed-domain,
raw-materiality inventory/partition/downstream identity closure,
authority-overlay, exact owner precedence/ownership/path/readback-materiality,
root-cause/obligation joins, reverse-closure, reciprocal multiplicity, and
discharge records remain present.

`documentation_drift_outcome` contains exactly two independently preserved
per-axis result records, `operation_membership` and `conditional_wiring`. Each
record contains:

- `outcome`: `present`, `absent`, `not-applicable`, or `indeterminate`
- `evidence_state`, retaining the exact axis-local evidence state from the table
- `authority_state`: `conflict`, `incomplete`, `aligned`, or `not-applicable`
- `established_drift_severity`: `MEDIUM`, `HIGH`, or `null`
- `gap_severity`: `LOW` or `null`
- `drift_fields`, the axis-owned resolved differences
- `root_cause_ids`, exactly the joined roots referenced by this axis's
  obligations, with no synthesized occurrence
- `failure_obligation_ids`, exactly the obligations whose `affected_axis`
  matches this axis
- `required_comparison_fact_obligation_index`, the exact non-empty per-fact
  projection for this axis
- `missing_evidence_roles`, exactly the lexicographically sorted unique
  joined root-cause `evidence_role` projection of those axis-local obligations
- `axis_suggested_action`, containing only repairs or evidence restoration
  supported by this axis

For `operation_membership`, `drift_fields` contains
`applicable_canonical_operations`, `catalog_operations`, `missing_operations`,
`extra_operations`, and `domain_contradictions`. For `conditional_wiring`, it
contains applicable, included/delegated, omitted, contradicted,
`multiplicity-drift`, indeterminate, and unmatched transition/assertion IDs plus
the completed discharge, reciprocal multiplicity, and reverse-closure records.
`present` requires non-empty established drift fields and
`established_drift_severity`; it may also retain `gap_severity: LOW`, obligations,
and missing roles for a separate required fact that does not invalidate the
established mismatch. `indeterminate` requires `gap_severity: LOW`, no
established drift severity, and at least one axis-local obligation with its
exactly equal non-empty root, per-fact, and role projections. `absent` and
`not-applicable` require both severity fields to be `null` and all axis-local
root, obligation, per-fact, and role-summary lists/maps to be empty. The aggregate
`missing_evidence_roles` must equal the sorted unique union of the two axis lists.
No aggregate field may replace either record.

For a gap finding, every field remains present. Unavailable scalar, record, or
collection values are `null`; independently resolved values remain intact;
empty lists mean resolved empty sets, never unknown evidence. Exact raw source
and target occurrences remain present even when interpretation is unavailable.
`missing_evidence_roles` is the exception to nullable unavailable collections:
it is always the exact derived list defined above. Every gap includes at least
one exact `root_cause`, one exact qualified `failure_obligation`, closed
forward/reverse and axis/fact joins, all available identity and independent-axis
outcomes, and the original normalized-bundle parser, adapter, query, or
comparison-authority error where applicable.

For a finding, aggregate `severity` is deterministic:

1. If one or both resolved axes have established drift, use the highest
   `established_drift_severity` among those axes (`HIGH` before `MEDIUM`).
2. Otherwise, if at least one axis is `indeterminate`, use `LOW`.
3. Otherwise no finding is permitted; return `None` only when both axes are
   `absent` or `not-applicable` and every failure-obligation set is empty.

Thus aggregate severity describes finding impact, not the ACR-403 planning risk,
and never implies that every axis resolved:

- `MEDIUM`: established generic operation-catalog or conditional-wiring drift.
- `HIGH`: established transition-semantics drift whose same active target claim
  explicitly contradicts the exact implementation-pipeline/resumer
  cohort-scoped `sole_writer`, CLI-only live readback, or a required eligibility
  condition, all with closed ownership and enforcement-path evidence, in a way
  that instructs an invalid lifecycle action. A repository-global/universal
  writer assertion is out of scope and can never establish this `HIGH` case.
- `LOW`: a distinct evidence, identity, selector, target-domain,
  activation/polarity, classification, scope/delegation/applicability,
  route-owner binding, raw-materiality admission, authority-overlay/query,
  support/path, readback materiality,
  procedural/enforcement ownership/matrix/assembly, repeated-operation scope,
  target-accounting, discharge, or normalized-bundle parser/adapter gap.

Aggregate `authority_state` follows the closed precedence defined above while
retaining both axis-local states. Aggregate `evidence_state` is the
first axis-local state present in this closed precedence:
`identity-conflict`, `selector-invalid`, `target-domain-incomplete`,
`raw-materiality-admission-incomplete`,
`activation-polarity-indeterminate`, `claim-classification-indeterminate`,
`authority-query-incomplete`, `delegate-scope-indeterminate`,
`transition-scope-unsupported`, `authority-conflict`, `enforcement-path-incomplete`,
`readback-materiality-incomplete`, `target-discharge-indeterminate`,
`evidence-gap`, `degraded`, then `complete`.

`confidence` reflects directness and completeness. It never conceals degraded or
missing required evidence.

## Suggested action

The finding-level `suggested_action` is a deterministic aggregate with separate
axis-labelled `established_drift_repairs` and `unresolved_axis_obligations`.
`established_drift_repairs` contains only the non-null `axis_suggested_action`
from axes whose outcome is `present`. `unresolved_axis_obligations` retains every
obligation and named comparison-evidence restoration from either axis whenever an
obligation exists, including a separate gap that coexists with established drift
on that axis. It never turns aggregate severity into repair authority for an
unresolved fact or axis. The complete finding-level action domain is document
repair or restoration of the exact named comparison evidence. It does not assign
retry, runner reconciliation, an external owner, or terminal state.

For established membership drift, direct the target owner to include the exact
applicable supported operation tokens and remove exact unsupported-operation
extras, or move an authorized support/non-runtime command outside the asserted
runtime subset with an explicit domain partition, or narrow/delegate the
completeness claim. Do not remove a valid support command merely because its
target occurrence asserted the wrong domain. A repository-global repair
uses executable-supported membership without inventing workflow adoption or an
automated caller. Preserve every authorized support/non-operation command in its
own explicitly partitioned domain.

If detailed README evidence is independently missing, stale, or conflicting,
retain that exact activated-use obligation and its separate evidence-restoration
suggestion alongside the generic target repair. Do not demote the executable
membership mismatch, make README repair a prerequisite for reporting it, or
imply that repairing either document makes every other generic claim clean.

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

For established multiplicity drift, direct the target owner to remove the
duplicate governed sequence step or disposition an actual explanatory
restatement explicitly as non-sequence corroboration. Never establish a second
canonical transition identity or relabel a governed duplicate merely to obtain
`None`.

For `repeated-operation-transition-unsupported`, retain the exact scope
obligation and narrow/delegate the target document so it no longer claims this
eval can decide those edges. Do not emit a different document drift repair from
the unsupported wiring comparison.

For a repository-global/universal writer assertion, do not certify, contradict,
or repair the assertion from this bounded cohort. Narrow it explicitly to the
implementation-pipeline/resumer cohort or delegate the unsupported universal
claim without asserting that this eval certified it.

Every document action preserves runtime behavior, exact
`RUNTIME_OPERATIONS`, closed request validation, applicable caller eligibility,
exact cohort-scoped `sole_writer`, and CLI-only live readback authority. It must
not add a writer, change runtime sequencing, authorize a helper or direct readback, infer
membership by majority, invent a transition field, default an absent target
field, erase a source occurrence, repair from an indeterminate comparison, or
claim runtime safety.

For a required evidence gap, suggest only restoration of the named comparison
evidence or correction of this document's comparison contract. Do not specify a
parser/adapter implementation, retry, rerun, reconciliation, external owner, or
terminal condition. Named evidence restoration may include a
complete structural-block/composite target envelope, component/source-map and
governed-content-span and enclosing-governor closure, complete independent
raw-materiality inventory/partition/exclusion/downstream identity closure, exact
command operand and claimed-domain mapping, same-commit supported
delegate/scope/applicability joins,
complete authority overlays/declaration entries/queries, executable support and
successful-path facts, enforcement witnesses, activated detailed-command
grammar/delegation/transition facts, activated route-owner binding, scope-required
caller facts, readback materiality and CLI joins, exact procedural-owner
precedence, operation/field/enforcement ownership and fact-local comparisons,
repeated-operation scope, dimension matrices, assemblies, reciprocal
multiplicity, root-cause/obligation joins, or reverse assertion/group-member
closure as named by the obligation. Do not edit the target
based on assumptions. Non-decisional provenance and residual uncertainty may be
reported without suggesting unrelated runtime, recovery, scheduler, namespace,
transport, or merge work through this finding.

## Consumers and supported-surface boundary

Current consumers are ACR-403 reviewers and maintainers or agents performing
separate exact-target review of complete-looking generic tool and lifecycle
claims. The supported operation surface is functional detailed CLI reachability
under the exact facts above; global membership does not imply caller adoption.
Supported execution-caller clean/drift claims are limited to the exact
implementation-pipeline and resumer partitions. Feature-direct and
feature-routed-refactoring topology claims are conditionally supported only by
the exact route-owner/sidecar binding and implementation-child applicability
closure above; their route owners do not become progression owners. Other parent
routes and repository-global writer authority are out of scope/indeterminate.
Wake/scheduler/recovery/global actor domains are not added to discovery.

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
- exact repository/target identity, complete potential-governor inventory and
  governor-to-envelope closure, one complete structural-block or permitted
  bounded-composite `target_source_domain`, distinct governed content span, and
  every component-union/role-overlay equality, including the complete-heading
  plus `Examples only:` conflicting neighbor;
- active-affirmative gating using only admitted components, without semantic
  borrowing outside the envelope;
- the exact full public command parent/children for only
  `tools/wu-session-migration` and `~/ai/tools/wu-session-migration`, their
  distinct raw locator identities/dispositions and common bounded logical
  entrypoint mapping, and malformed neighbors, while preserving
  repository-native shorthand, bare tokens, exact per-command
  claimed-domain/subset records, wrong-domain contradictions,
  non-runtime-only validity, and explicitly partitioned mixed-domain handling;
- the independent conservative `raw_materiality_candidate_inventory` derived
  before semantic extraction for every bounded target and activated authority
  role, exact admitted/excluded/unsupported partition, mechanically checkable
  closed grammar/section exclusions, and raw-identity equality through overlays,
  queries, command/transition candidates, and dispositions, including the
  harmful-neighbor expectation;
- the bounded whole-blob `comparison_authority_discovery_domain`, deterministic
  per-role full AST/Markdown/YAML semantic overlays, exact declaration-entry and
  independently discovered transition-candidate closure, per-operation/per-caller
  queries, conditionally activated exact feature/refactoring route-owner and
  sidecar overlays/queries, query-derived semantic spans, and every exactly-once
  overlay/query/disposition equality, without an all-effecting actor claim;
- per-member declaration, parser/main, request-validation, every successful
  public CLI path, transaction endpoint, operation-specific executable support,
  and same-support-key enforcement-path witnesses independently of README
  alignment; detailed-command evidence is required only for an activated target
  grammar, delegation, or material transition semantic; caller authority is
  structurally non-applicable for global membership and mandatory only for
  supported implementation-pipeline/resumer caller-scoped subsets and wiring;
- exact `target_scope_identity`, same-commit `delegate_resolution`, and complete
  supported operation/transition applicability witness partitions; exact one-
  owner route-to-normalized-implementation-caller/cohort/root binding for an
  activated feature topology; and other parent-route cohorts indeterminate/out
  of scope;
- closed caller-progression readback-materiality candidates and exact
  material/not-material partition before CLI occurrence admission, plus the
  top-level CLI lock/recovery/readback enforcement join for every material key;
  the point-in-time `phase0-reresolve` example keeps its supported non-readback
  facts but leaves material readback and its completed join unresolved, while an
  edge-membership omission remains separately decidable when readback is
  structurally not applicable;
- typed partial transition facts; the exact operation-to-procedural-owner
  precedence index; mandatory workflow/optimized-contract secondary occurrence
  comparisons; the closed operation/field/enforcement compound-authority matrix;
  fact-local owner/constraint/corroboration comparisons; per-dimension required-
  fact matrices; n-way assembly; exact owner context, enforcement witness, and
  non-applicability basis; query/completion equalities; cohort-scoped
  `sole_writer`; universal-writer out-of-scope handling; and conflicts without
  majority or source erasure;
- the pre-assembly at-most-one-transition-per-operation scope gate, exact
  `repeated-operation-transition-unsupported` obligation, and prohibition on
  wiring drift/`None` or per-edge projection for materially distinct repeats;
- edge-membership versus transition-semantics completeness;
- unique or explicit grouped/alternative target discharge plus reverse exact
  closure for every assertion and group member, and reciprocal exactly-one
  canonical-transition-to-sequence-member closure for each admitted single edge,
  with every duplicate sequence-member assertion dispositioned before `None`;
- per-axis outcome/evidence/authority/severity/drift/action records, aggregate
  severity and authority precedence, retained unresolved obligations, positive
  and non-fire paths, exact two-level root-cause/qualified-obligation identity,
  non-empty forward/reverse and axis/fact joins, exact joined-role
  `missing_evidence_roles` equality, exact structured `finding | None` for an
  admitted normalized input, and the explicit pre-input and post-result external
  runner boundaries, failure obligations without recovery-routing fields, and
  finding-level suggested actions limited to document repair or named
  comparison-evidence restoration; and
- the external ACR-398 prerequisite wording and anti-scope.

Step 6c must reject a noncanonical/multiply resolving or partial-block target, an
unclosed semantic/ambiguous governor, a complete-heading plus `Examples only:`
neighbor classified partial/clean, a composite with multiple
governors/content blocks, intervening unowned blocks, or unbounded context,
semantic borrowing outside admitted components, incomplete component or role-overlay
equality, a missing/incomplete raw-materiality inventory or partition, a
free-form mapper exclusion, a potentially material harmful neighbor classified
non-decisional, a raw identity lost between inventory and
overlay/query/command/transition/disposition, malformed full-command
normalization, treating either admitted exact locator as a wrong path, admitting
any third locator or generic locator resolution, a support/non-runtime command
accepted inside an asserted runtime subset, a mixed label without exact
per-command subset partition, preselected-span authority discovery, incomplete
authority semantic overlay/declaration-entry/transition-candidate equality,
incomplete query/support/path/applicability closure, a dead/bypassed validator
promoted to authority, caller adoption used to gate global membership, an
activated feature/refactoring topology lacking exactly one route owner, sidecar
closure, normalized implementation-caller/cohort/root binding, or applicability
witness, a route owner promoted to child progression/request owner, another
parent-route applicability treated as authority-proven, missing caller authority
for a supported scoped subset or transition,
stale/ambiguous delegation, sampled scope exclusion, a missing or duplicate
disposition, incomplete transition facts or dimension matrix, broad caller-role
ownership, wrong or ambiguous operation-specific procedural owner precedence,
mapper-selected owner downgrading, README/workflow/sidecar transition prose
promoted to owner, a secondary assertion not compared with its exact owner fact,
an unclassified constraint/corroboration conflict, invented readback
non-applicability, an
unclosed readback materiality candidate or CLI enforcement join, a completed
point-in-time `phase0-reresolve` material readback join inferred from generic
caller prose, loss of its independently decidable edge-membership omission,
missing or multiply owned required canonical fields, repository-global
`sole_writer` clean
certification or `HIGH` drift, a one-source-complete transition requirement,
unevidenced field borrowing/defaults, source erasure, unrestricted projected
compatibility, absent required conditional semantics classified as included,
direct-import live-readback authority, materially distinct repeated-operation
edges assembled or reported as drift/clean, a duplicate governed sequence step
accepted as clean, an explanatory restatement counted twice, missing reciprocal or reverse
assertion/group-member closure, mixed-axis severity or repair ambiguity, README
absence used to suppress executable global membership, a
null/unknown/stale/duplicate/unsorted/missing/extra
`missing_evidence_roles` value, a colliding obligation identity, synthesized
dependent-fact source occurrence, empty/unequal root-cause forward/reverse or
axis/fact projection, any eval-owned pre-input or delivery/fallback/terminal
transport state, a claim that this eval reported a call that never occurred, an
eval-owned recovery disposition/owner/ordered action/terminal condition, a
suggested action outside document repair or named comparison-evidence
restoration, an
unstructured indeterminate result, latent adjacent
capability obligations used to prevent `None`, or any eval-owned
merge-verification claim.

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
  unconflicted `Examples only:` plus list partial, complete-heading plus
  `Examples only:` classification conflict, delegated/scope/applicability,
  global membership without caller adoption, supported implementation-pipeline
  and resumer caller-scoped membership, conditionally activated feature-direct
  and feature-routed-refactoring route-owner/sidecar/binding cases, partial,
  non-runtime-only, explicitly
  partitioned mixed, support-command-in-runtime-subset domain contradiction,
  shorthand, bare-token, both exact bounded full-command locators and
  malformed-neighbor,
  edge-membership, transition-semantics, per-dimension matrix, typed n-way
  assembly, exact operation-specific procedural-owner precedence,
  operation/field/enforcement compound authority, mandatory workflow/sidecar and
  README constraint/corroboration agreement/conflict, missing/multiply owned
  fact, `phase9-update` split caller/runtime/transaction authority, unique/group
  discharge, repeated-operation-transition unsupported scope, duplicate
  sequence-member multiplicity drift, explicit non-sequence
  corroboration, reciprocal and reverse assertion/group-member closure, mixed
  drift/gap aggregation, executable member absent from both README and generic
  target, activated detailed-command gaps, two-level root-cause/obligation
  collision and exact forward/reverse/axis/fact/missing-role projection failures,
  identity, selector, whole-blob authority semantic-overlay,
  independent pre-semantic raw-materiality admission including harmful
  neighbors, declaration-entry, independently discovered transition-candidate,
  and structured gap cases; prove every target and authority raw identity and
  overlay/query/occurrence equality; distinguish a governing
  validator/projection from dead or bypassed neighbors with same-support-key
  enforcement witnesses; close material/not-material caller-progression
  candidates before demonstrating CLI-only live readback, without treating the
  point-in-time `phase0-reresolve` example as a completed material join; exercise
  exact cohort-scoped `sole_writer` plus repository-global writer out-of-scope handling;
  validate conceptual result construction only from admitted normalized inputs;
  observe advisory results; and review false positives and evidence drift.

  Before any `ROLL_OUT` call, a separately owned future invocation envelope must
  carry exact invocation/attempt identity, every selected source identity,
  normalized-input identity when commit succeeds, the original cause when
  pre-input construction fails, the retry/reconciliation owner, and an external
  terminal status. That owner must terminally distinguish committed normalized
  input from resolution/read/parse/adapter/interruption/input-commit failure so a
  call that never occurred cannot appear as `None` or as an eval finding. This
  specification does not select the envelope's transport, storage, serialization,
  channel, or implementation.

  Before any `ROLL_OUT` result can publish or expose a result, a separate future
  runner/rollout contract must also choose and verify invocation/attempt and
  result-envelope identity, serialization, channel and sink, idempotency,
  commit/readback receipt, acknowledgment-loss handling, retry and
  reconciliation, successful `None` completion evidence, fallback policy if any,
  and consumer terminal selection. Those are runner mechanisms and attempt
  identities, not finding fields or eval evidence. Until that contract exists, a
  pre-input or transport failure is an external runner failure, not an eval
  finding, not `None`, and not evidence that changes or demotes computed axis
  semantics. This `WRITE` artifact claims no external terminal outcome.
- `ENFORCE` additionally requires trusted findings, a named caller and
  hookpoint, severity policy, document-repair routing, fail-closed required
  evidence behavior, verified separately owned invocation/result contracts, and durable
  enforcement-readiness evidence.
- `MAINTAIN` tracks authority and target syntax, exact target selector
  uniqueness, enclosing-governor inventory/dispositions,
  complete-block/bounded-composite component and source-map closure, distinct
  governed content spans, activation/polarity overlays, per-command claimed-domain
  partitions, shorthand/two-locator-full-command/malformed-neighbor and
  command-domain grammar, independent target/authority raw-materiality
  inventories, exclusions, partitions, and downstream identity closure,
  whole-blob authority semantic overlays/discovery/query and exact
  declaration/transition-candidate closure, supported
  implementation-pipeline/resumer scope/delegate/applicability joins,
  conditionally activated route-owner binding/applicability joins,
  comparison-scope-specific support and successful paths, enforcement witnesses,
  readback-materiality partitions and CLI joins, exact procedural-owner
  precedence, operation/field/enforcement authority/dimension matrix/assembly,
  repeated-operation scope, cohort-scoped writer authority,
  lifecycle-sequence completeness, reciprocal single-edge multiplicity, target
  discharge and reverse assertion closure, two-level failure identity and
  per-axis/per-fact/missing-role derivation, conceptual finding comparability,
  and the versioned boundaries with separately owned invocation and result
  contracts. External invocation/result transport is maintained under those
  contracts, not by this eval.

No detector language, parser library, fixture serialization, runner mode,
invocation-envelope implementation, result-envelope identity, result
serialization, report path, channel, sink, receipt, acknowledgment, retry,
fallback, consumer terminal rule, CLI, CI,
scheduler, cron, scan cadence, hookpoint, or enforcing caller is selected.
Requesting runnable evaluation while lifecycle remains `WRITE` is an external
runner lifecycle failure and cannot produce a finding or `None`. Rollback of this
exact repository delta is deletion or reversion of this one Markdown
specification. It cannot reverse an external action, and this eval does not claim
external non-action.

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
bounded-composite target envelope after enclosing-governor closure, distinct
governed content span, per-command claimed-domain partition, independent
pre-semantic target/authority raw-materiality admission and harmful-neighbor
handling, the exact two bounded raw tool-locator productions, bounded whole-blob
authority semantic overlays and declaration/transition-candidate closure,
comparison-scope-specific support and enforcement paths, supported
implementation-pipeline/resumer applicability, conditional exact route-owner
binding, deterministic procedural-owner precedence and operation/field/
enforcement ownership, closed readback materiality, repeated-operation scope,
query/applicability/assembly, reciprocal single-edge multiplicity and reverse
target-discharge closure, including point-in-time `phase0-reresolve` readback
uncertainty without loss of independently decidable edge membership, per-axis
aggregation, two-level cause-preserving obligations without recovery routing and
with exact missing-role derivation through result construction, and
the external invocation/result anti-scope defined here. It does not permit
ACR-398 to substitute a selected target fragment, exclude a semantic governor,
accept a wrong-domain command, use unbounded context or preselected authority
spans, promote a dead/bypassed validator, use sampled or unsupported cohort
exclusion, certify a universal writer, use caller adoption or README alignment as
a global membership gate, drop or double-count a target assertion, or emit an
unstructured indeterminate outcome for its direct per-target inspection.

The external handoff does not copy this eval into ACR-398's diff, execute it,
establish `None`, replace ACR-398's direct inspection, change runtime membership
or sequencing, or advance this eval beyond `WRITE`.

## Anti-scope

This `WRITE` artifact does not define or authorize detector code, Python or Rust
implementation, fixtures, tests, pytest imports or assertions, a one-off
verifier, a resolver, parser, source-discovery adapter, eval-runner adapter,
invocation-envelope transport/implementation, result-envelope or attempt
implementation, result serialization, primary or fallback
delivery states, channel or sink behavior, idempotency, commit/readback receipt,
delivery acknowledgment, acknowledgment-loss handling, retry/reconciliation,
successful `None` completion evidence, fallback publication, consumer terminal
selection, CLI/CI/scheduler/cron wiring, runtime behavior, writer or namespace
changes, helper or direct-live-readback adapters, rollback/recovery/cleanup
execution, global locking, availability or cost claims, protected-state
mechanisms or writes, ACR-398 edits, merge verification, consumption records,
ticket actions, estimate mutation, external-action proof, or external
reconciliation.

It also defines no generic path resolution, shell or tilde expansion, filesystem
inspection, symlink handling, working-directory inference, arbitrary tool alias,
or eval-owned recovery disposition, recovery owner, ordered recovery action, or
terminal condition.

It does not audit every runtime capability, namespace, recovery path, scheduler,
observer, caller, or actor affecting or judging manifest/index state. Its
lossless authority discovery is bounded to the named complete comparison blobs,
and its lossless target accounting is bounded to one exact complete structural
block or one of the two exact composite forms. Whole-blob discovery does not
expand beyond the conditionally admitted exact feature/refactoring route owner
and sidecar into wake/scheduler/helper/recovery, universal writer-capability
discovery, or global actor auditing. A route owner never owns implementation
child progression or requests. Cohort-scoped `sole_writer` does not certify repository-global
exclusivity; that would require a separately authorized
`wu-session-writer-authority` eval. Bounded target parsing includes exact semantic
governors but does not become adjacent-claim borrowing or repository-wide claim
discovery. Per-axis aggregation and conceptual result construction do not
create a catch-all adjacent finding, runtime repair authority, deliverable
fallback, terminal transport outcome, or transport implementation.
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
- `agents/feature-orchestrator.md`
- `contracts/operators/feature-orchestrator.yaml`
- `agents/refactoring-orchestrator.md`
- `contracts/operators/refactoring-orchestrator.yaml`
- `~/projects/ai/planning/acr-403-operation-catalog-eval/proposals/acr-403-ACR-403.md`
- `~/projects/ai/planning/acr-403-operation-catalog-eval/contracts/acr-403-wu-session-runtime-operation-catalog-drift.md`
