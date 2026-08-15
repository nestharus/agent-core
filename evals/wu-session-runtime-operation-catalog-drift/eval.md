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
| `wu-session-runtime-write-v1` | `tools/wu-session-migration/wu_session_migration.py:RUNTIME_OPERATIONS` owns declared runtime-operation membership. For this eval, `supported` means only functional reachability of the detailed human runtime-operation CLI command entered through `tools/wu-session-migration/__main__.py`, admitted by `_parser()` and top-level `main()`, closed by exact operation/request validation, and successful only after the operation-specific transaction path returns. Environment-selected or alternate namespaces, importable helper modes, and other capabilities remain separately inventoried authority obligations; they cannot borrow CLI antecedents, but they also cannot erase an otherwise established documentation-membership comparison. |
| `wu-session-runtime-lifecycle-ownership-v1` | Operation-specific executable validators own transition source-state eligibility and allowed effects. Only `validate-pre-pr-readback` entered through `tools/wu-session-migration/__main__.py` and top-level `main()` with its exact lock, completed-recovery, and namespace antecedents can own post-write live acceptance. Direct imported calls, with or without `expected_manifest`, remain distinct inventoried occurrences but cannot establish live acceptance at `WRITE`; authorizing a direct-live integration requires later contract work. The detailed README owns human command forms and described transition semantics; implementation workflow/operator and resumer documents own invocation partition, progression order, caller-owned closure, and exact `sole_writer` authority. An independently closed, identity-bound authority source and partition-span domain is established before raw candidate coverage or semantic extraction. Every raw candidate and every resulting semantic occurrence receives exactly one fail-closed disposition. Rollback, recovery, cleanup, and corrective modes remain independently accounted obligations even when they do not supply a documentation-comparison field. |
| `operation-catalog-claim-comparison-v1` | This accepted ACR-403 contract owns injective target admission, lossless pre-recognition target-presentation accounting, orthogonal claim-completeness and command-domain classification, per-command disposition, lossless target-transition occurrence and claimed-field assertion accounting, membership and wiring comparison, non-fire semantics, and safe repair direction for one exact target claim. `catalog_path` and `catalog_anchor` remain ticket-required fields inside the structured target identity. Generic document anchors are claim instances, not authorities. |
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
unwanted behavior, a supported evidence-gap report, or documentation drift plus
one or more separately preserved adjacent-authority obligations. Membership and
wiring decisions are independent of unrelated global-serialization, alternate-
namespace, imported-helper, capability-authority, or availability obligations.
Rollback, recovery, cleanup, and corrective obligations are likewise independent
unless they directly supply an asserted comparison field, but they always remain
in closed-domain accounting. An obligation blocks only the comparison fact that
depends on it; it does not erase an already completed missing/extra or wiring
comparison. Any observed independent obligation prevents a bare `None`. `None` is
reserved for a sufficiently evidenced absence of the named documentation drift
with no observed non-clean obligation requiring a finding. It does not certify
adjacent runtime safety, global serialization, capability availability, or an
unobserved surface. Runner-level input, validation, and maintenance failures
remain outside a clean `None` outcome.

Each invocation evaluates exactly one target claim admitted through the
structured `target_claim_identity` defined below. Its ticket-required
`catalog_path` and `catalog_anchor` fields are necessary but are not, by
themselves, an exact identity. A `finding` or `None` applies only to the one
admitted claim occurrence.
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
exact `evaluated_repository_identity`, one admitted `target_claim_identity`,
and, when present, one WU, PR, session, or selected invocation subtree observed
against that identity. It must represent these semantic records:

| Evidence role | Required semantic fields and decision use |
|---|---|
| Repository identity | One `evaluated_repository_identity` containing the canonical provider-issued repository identifier and full evaluated commit identity selected by the caller. Every repository-derived record below binds to this same value and resolves its content from that commit. |
| Declaration authority | `authority_path`, `authority_symbol`, the common identity, a readable source snapshot, and extracted full `canonical_operations`. This is declared membership evidence, not executable-support or target-scope applicability evidence by itself. |
| Membership applicability | Identity-bound caller, lifecycle-domain, and cohort authority; `membership_applicability`; `applicability_authority`; and `applicable_canonical_operations`, the claim-local subset derived from the full declarations. Ambiguous applicability is non-clean. Occurrence-only evidence is membership-inapplicable unless it independently claims complete support for a named domain. |
| Authority source closure | An independently authorized `authority_source_domain`, `authority_source_blob_inventory`, and `authority_partition_span_inventory` bind every accepted source blob and complete raw partition span before semantic occurrence extraction. Per-blob `authority_source_coverage`, lossless `authority_raw_candidate_inventory`, and `authority_raw_candidate_dispositions` cover every code point and raw candidate exactly once. `accepted_capability_inventory` and one `accepted_capability_accounting` record per capability then account for every callable/entrypoint, invocation mode, environment or other namespace selector, lock path, direct caller or `null` caller, writer/readback path, rollback, recovery, cleanup, and corrective path capable of affecting or judging the manifest/index outcome. Unsupported or dynamic source shape creates a comparison-blocking adapter obligation rather than a missing candidate. |
| Authority source occurrences | `authority_source_occurrence_inventory` is derived only after source closure and covers every admitted support, transition, bounded authority constraint, namespace, direct-caller, writer/readback, rollback, recovery, cleanup, and corrective semantic occurrence at the common identity. A separate disposition map accounts for every occurrence exactly once before support or transition comparison. `authority_constraint_inventory` preserves partial fields explicitly asserted by optimized contracts, manifests, and other authority sources; every constraint is compared exactly. Each obligation is labeled `comparison-blocking` or `independent-adjacent`. `corrective_capability_records` bind the exact acting caller or `null`, authorization and lock antecedents, state/journal namespace and alias evidence, attempt/journal identity, phase-dependent intended disposition, affected targets/effects, and completion evidence. |
| Per-member executable support | One deterministic `operation_support` record per canonical declaration, bound to the common identity, with exact source-domain, capability, entrypoint, invocation-mode, source-occurrence, and support-candidate inventories. Functional CLI reachability proves only that the detailed human command enters through `tools/wu-session-migration/__main__.py`, `_parser()`, and top-level `main()`, resolves the exact operation/request equality and closed operation-specific validation, reaches the valid projection or handler, and exposes success only after the transaction path returns. The CLI mode's actual lock, recovery, and namespace antecedents are retained as evidence, but global namespace equality across alternate capabilities is not a prerequisite to this documentation comparison. Every helper, override, alternate namespace, direct caller, and corrective capability remains inventoried with a separate authority disposition. |
| Executable and readback transition candidates | Operation-specific executable projection, source-state, eligibility, and effect validators, all bound to the common identity, independently contribute candidates for the transition admission/effects they own. Only the top-level `validate-pre-pr-readback` CLI occurrence contributes post-write live-acceptance semantics. `expected_manifest` and both direct-import modes remain inventoried candidates or independent adjacent obligations for the semantics they actually own, but none can satisfy live acceptance. Every candidate carries exact `sole_writer`. |
| Detailed-command transition candidates | Detailed README path and semantic occurrences, common identity, human command forms, operation semantics, and described lifecycle/readback semantics. This source independently contributes candidates for the semantics it owns; it does not override executable admission or caller ownership. |
| Caller transition candidates | Implementation workflow/operator and resumer prose paths, optimized contract paths, workflow-contract manifest occurrences, common identity, invocation partition, progression order, caller-owned closure, `owning_caller_or_domain`, effects, readback authority/mode, and `sole_writer`. Every owning caller partition/progression source independently contributes only the semantics it asserts rather than annotating executable-discovered transitions or borrowing unstated fields from prose. |
| Exact target claim | Structured `target_claim_identity`, admitted canonical `catalog_path`, canonical `catalog_anchor`, resolved unique occurrence and content/location identity, common identity, surrounding context, structured `claim_kind` containing separate `claim_completeness` and `command_domain` classifications, `claim_scope`, the complete `resolved_catalog_bearing_source_span`, `target_presentation_source_coverage`, lossless `target_presentation_candidate_inventory` and dispositions before command recognition, every raw command occurrence and exact command disposition, every raw and interpreted operation occurrence, `catalog_operations`, `target_transition_source_coverage`, lossless `target_transition_occurrence_inventory`, one structured target assertion with explicit `claimed_fields` per transition occurrence, and every claimed sequence. The target identity, not a delimiter-joined pair, identifies the sole claim under comparison. |
| Comparison | Deterministically sorted `applicable_canonical_operations`, `missing_operations`, and `extra_operations`; per-member `operation_support`; complete target-presentation candidate/disposition/raw-command/command-disposition/raw-operation/interpreted-operation equalities; complete authority source-domain/blob/span/coverage/raw-candidate/capability/occurrence, bounded authority-constraint, and admitted-support-to-completed-support equalities; and aggregate `wiring_transition` containing injective structured authority transition identities, exact authority-side `sole_writer`, conditions, effects, owner, and readback fields, lossless target occurrence/assertion dispositions, claimed-field target-to-canonical witnesses, and authority/target occurrence/candidate/comparison equality inside the exact target claim's resolved domain. |
| Observation provenance | `evidence_paths`; revision, WU, PR, and session locators when available; source, trace, prompt, log, report, audit, and final changed-surface paths when available. |
| Conflict and availability | `evidence_state`, comparison-scoped `authority_state`, `adjacent_authority_state`, `authority_conflicts`, `adjacent_authority_obligations`, `reconciliation_owner`, and `missing_evidence_roles`, with enough role-level detail to distinguish unavailable evidence, identity failure, selector failure, authority-domain or source-coverage loss, authority disagreement, target-presentation loss, ambiguous completeness, ambiguous command domain, command disposition, membership applicability, operation interpretation, corrective-capability accounting, namespace binding, target-transition assertion loss, transition equivalence, and ambiguous scope from a resolved empty collection. |
| Cause-preserving recovery | Injective `failure_obligations`, plus a derived `failure_cause` summary. Every non-clean evidence, identity, selector, completeness, command-domain, applicability, presentation, command-disposition, interpretation, authority-source/blob/span/coverage/raw-candidate/capability/source-occurrence, namespace/lock, rollback/recovery/cleanup/corrective, target-assertion, comparison, scope, or lifecycle obligation remains distinct; carries `decision_relation: comparison-blocking | independent-adjacent`; and retains an advisory disposition, recommended owner, ordered next actions, original error when applicable, and proposed closure condition. A completed documentation-drift finding may therefore carry independent adjacent obligations without losing the drift result. At `WRITE` these fields neither authorize action nor prove durable closure. |
| Downstream handoff | Verified ACR-403 merge identity and the ACR-398 inherited Step 6b intent boundary without broadening ACR-398's two-file repository scope. |

### Common repository identity admission

`evaluated_repository_identity` is one semantic identity containing
`canonical_repository_id` and one exact full commit selected for evaluation.
`canonical_repository_id` is the structured provider identity
`{provider, repository_object_id}`: `provider` is the canonical forge host and
`repository_object_id` is that provider's immutable repository object ID.
Owner/name slugs, SSH or HTTPS remote spellings, redirects, and local checkout
paths are locators only and must resolve to that object; none is accepted as an
alternate repository identity. The identity fields are never joined with a
delimiter. The evaluated identity is not an independent timestamp or label on
each source. Declaration membership,
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

### Exact target identity admission

`target_claim_identity` is an injective structured record with these semantic
fields:

- `canonical_repository_id`
- `evaluated_commit`, the full commit identity
- `catalog_path`
- `catalog_anchor`
- `source_blob_identity`
- `resolved_source_span`
- `resolved_claim_content_identity`

`catalog_path` is admitted only in canonical repository-relative POSIX form. It
is one or more non-empty path segments separated by exactly one `/`; it has no
leading or trailing separator, empty segment, `.` segment, `..` segment,
repeated separator, backslash spelling, or absolute form. Its exact spelling
must name one regular Git tree blob at the selected commit. Case, Unicode,
transport, filesystem, shortened, or other spellings that merely normalize to
that blob are aliases and are rejected rather than canonicalized. No component
may be a symlink, and resolution may not traverse or escape the selected
repository tree.

`catalog_anchor` is the canonical structured selector
`{anchor_kind: exact-claim-source, anchor_text}`. `anchor_text` is the complete
source text of the selected semantic claim, not a heading-only label, shortened
phrase, occurrence ordinal, alternate normalized spelling, or another selector
kind. At the selected commit and admitted `catalog_path`, it must resolve to
exactly one source occurrence. Zero occurrences do not resolve; repeated text,
overlapping matches, or any selector that can resolve to more than one
occurrence is non-clean. The resolved occurrence is then bound to the immutable
source blob, an unambiguous source span within that blob, and the identity of
the complete claim content. These are separate fields; no path, anchor, span,
or content identity is concatenated into a compound string.

The semantic fields and admission rules are fixed at `WRITE`; a later lifecycle
WU may choose the Markdown parser, byte/span representation, digest algorithm,
and serialization. Those choices may not admit a second spelling for the same
target or weaken unique occurrence. A raw/normalized selector mismatch or an
alternate selector for the same blob/occurrence uses
`noncanonical-selector-alias`; repeated or multiply resolving anchors use
`non-unique-anchor-resolution`; other grammar, symlink, or escape violations use
`invalid-target-selector`. These are distinct non-clean selector obligations,
never target aliases, drift, or `None`. The attempted selector remains in
provenance, while `target_claim_identity`, `catalog_path`, or `catalog_anchor`
is `null` wherever canonical admission did not complete.

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
   `__main__.py` must enter `main()`, `_parser()` must expose it, and `main()`
   must acquire `_cutover_lock()`, finish
   `recover_incomplete_transaction()`, invoke the operation with the lock-held
   antecedent, close operation/request equality through
   `_validate_runtime_request()`, reach the operation-specific projection or
   handler and `_execute_transaction()`, and expose success only after the
   transaction returns. These are the exact detailed CLI support facts used by
   membership comparison. The acting command's state root, lock inode, journal
   namespace, and target identities remain recorded, but equality of those
   namespace values across alternate capabilities is not a support prerequisite
   and entering `_cutover_lock()` is not evidence of global serialization.
   Every capability, entrypoint, invocation mode, and namespace choice observed
   for that member remains inventoried even when outside this supported CLI
   surface and receives a separate obligation disposition when its authority or
   antecedents are unsafe, alternate, missing, or unresolved.
3. Operation-specific executable projection, source-state, eligibility, and
   effect validators own their transition admission and effects. They are one
   independently inventoried transition authority partition, not the seed or
   boundary of the complete transition domain. Only
   `validate-pre-pr-readback` entered through `__main__.py` and `main()` without
   `expected_manifest`, while the top-level lock is held and recovery has
   completed, reads and identity-checks `manifest_path` and can own post-write
   live acceptance. `validate_pre_pr_readback(..., expected_manifest=...)` is
   projection or historical validation admissible only from its exact Phase 3
   request-validation antecedent; it cannot establish live acceptance alone.
   Direct imported `validate_pre_pr_readback` calls without
   `expected_manifest` and direct imported calls with `expected_manifest` are
   distinct modes. Each occurrence records its named authoritative caller or
   `null`, mode-local namespace, lock ownership, completed recovery, and live-
   acceptance disposition; neither direct mode borrows `main()` antecedents,
   neither direct mode can establish live acceptance at `WRITE`, and an unnamed,
   unbound, or purported direct-live mode is a separate non-clean obligation.
   A later contract may separately authorize direct-live integration; this eval
   does not contain an alternate admission rule.
4. `tools/wu-session-migration/README.md` owns detailed human command forms and
   their described transition semantics; it does not override executable
   admission and is independently inventoried for transition candidates.
5. `agents/implementation-pipeline-orchestrator.md`,
   `workflows/implementation-pipeline.md`, and
   `agents/wu-session-resumer.md` own detailed invocation partition, progression
   order, caller-owned closure, and their lifecycle partitions while preserving
   the sole Python writer. Their optimized contracts under `contracts/operators/`
   and `contracts/workflows/` are invocation-authority surfaces and
   `workflows/index.json` is the accepted workflow-contract manifest; their exact
   caller, side-effect, and expectation fields are independently inventoried and
   must reconcile without borrowing unstated transition details from the prose.
6. One injectively admitted target occurrence in `tools/README.md`,
   `conventions/wu-session-lifecycle.md`, or another generic summary is the
   target claim compared with higher authority only when its context explicitly
   asserts or strongly implies applicable completeness. Other occurrences are
   not evaluated by the same invocation.
7. Tests, source snapshots, saved traces, reports, audit bundles, and final
   diffs are corroborating or observation evidence. They do not expand
   declared membership or executable support.

For support and transition discovery, the detailed CLI portions of items 2
through 5 are co-required comparison-authority partitions with distinct semantic
ownership. Their other reachable capability modes remain required inventory
sources but are independent adjacent obligations unless a documented comparison
fact actually depends on them. Authority discovery is independently closed
before semantic occurrence extraction; an extractor's recognized occurrence set
can never define the authority domain over which its own completeness is judged.

`authority_source_domain` is the exact identity-bound source registry authorized
for this comparison. At the inspected contract it contains these complete Git
blobs at the common commit, with no path alias or ambient-worktree substitution:

- `tools/wu-session-migration/__main__.py`, the complete executable module
  entrypoint blob;
- `tools/wu-session-migration/wu_session_migration.py`, the complete parser,
  callable, environment-selector, lock, writer, readback, transaction, rollback,
  recovery, cleanup, and corrective source blob;
- `tools/wu-session-migration/README.md`, the complete detailed command,
  transition, lock/recovery, and readback contract blob;
- `workflows/implementation-pipeline.md` and
  `agents/implementation-pipeline-orchestrator.md`, the complete accepted
  implementation caller/progression authority blobs;
- `agents/wu-session-resumer.md`, the complete accepted resumer
  caller/progression authority blob;
- `contracts/workflows/implementation-pipeline.yaml`,
  `contracts/operators/implementation-pipeline-orchestrator.yaml`, and
  `contracts/operators/wu-session-resumer.yaml`, the complete accepted optimized
  workflow/operator invocation-contract blobs; and
- `workflows/index.json`, the complete accepted workflow-contract manifest blob
  whose implementation-pipeline entry must reconcile with its source contract.

The domain record contains the common repository identity, this contract as
`domain_authority`, its exact authorization evidence, the canonical source-path
set, required authority role for each path, complete-blob requirement, partition
grammar, and closure rule. The source-path set is fixed before any source is
parsed and its identity is computed from those structured fields without
delimiter concatenation. Source readability or semantic recognition cannot add,
remove, or substitute a domain member.

The Python blobs are admitted as complete sources before the mapper enumerates
all imports and executable entry calls, module-level declarations, callable
definitions, nested control-flow spans, parser registrations, environment reads,
call sites, state-path constructors, lock paths, read/write/readback sinks,
transaction phases, exception-driven corrective paths, rollback, recovery, and
cleanup paths. The Markdown, YAML, and JSON blobs are likewise admitted whole
before the mapper enumerates every block or structured node, inline span, command
occurrence, caller/progression assertion, side effect, delegation, and residual
text.
Tests and generic target claims remain corroboration or targets, not authority;
an external or dynamically reached caller that is not bound by an accepted
caller authority is represented as acting caller `null`, never presumed absent.
A future change to the accepted registry is a source-contract change requiring a
fresh identity-bound invocation; the mapper may not add or drop a blob in order
to make a comparison close.

`authority_source_blob_inventory` binds each registry member to its complete
blob identity. `authority_partition_span_inventory` is derived from the registry,
not from recognized transition names, and partitions each complete blob into
identity-bound raw spans. Python coverage uses its complete lexical token stream,
comments and whitespace as explicit grammar boundaries, with AST/control-flow
nodes linked to the raw token spans they cover. Markdown coverage uses complete
block and inline leaf spans plus explicit delimiter/whitespace boundaries. YAML
and JSON coverage uses every structured key/value/list node plus exact raw scalar,
delimiter, comment where supported, and whitespace spans. The partition record
retains source order, parent/container links, exact raw text and content identity,
and the adapter grammar version. Overlapping structural parents may describe
containment, but leaf content coverage is exact and non-overlapping. Unknown
language, dynamic dispatch or import, generated source, unresolved alias,
unparseable control flow, malformed Markdown/YAML/JSON, or any source shape whose
complete effect boundary cannot be represented becomes a comparison-blocking
`unsupported-source-shape-adapter-obligation`; it is not omitted from the domain
and cannot become an absent candidate.

`authority_source_coverage` maps every source code point to one raw leaf candidate
or an exact grammar boundary before semantic extraction.
`authority_raw_candidate_inventory` then contains every raw declaration,
callable, branch, parser registration, namespace selector, call site, command,
caller assertion, write/readback/effect path, lock path, rollback, recovery,
cleanup, and corrective fragment exposed by those partitions. Every raw candidate
receives exactly one `authority_raw_candidate_dispositions` record:
`admitted-semantic-occurrence`, `authorized-inert`, `conflict`, or
`unsupported-source-shape-adapter-obligation`. `authorized-inert` requires closed
identity-bound reachability evidence that the candidate cannot read, write,
judge, namespace, lock, reverse, recover, or clean up the manifest, active index,
journal, transaction artifacts, or evidence used to accept that valuable
outcome. A reachable or accepted effecting capability cannot be clean-excluded.
If inertness cannot be proved, the candidate is admitted or remains a
comparison-blocking obligation.

`accepted_capability_inventory` is independently derived from the complete raw
candidate/control-flow domain and covers every accepted callable or entrypoint,
invocation mode, environment or other namespace selector, lock path, direct
caller or `null` caller, writer/readback path, rollback, recovery, cleanup, and
corrective path capable of affecting or judging the valuable outcome. Each
capability record binds all raw candidate IDs that establish its reachability,
entry chain, mode, caller, effects, and decision relation. Public
`apply_runtime_request()` and `apply_plan()` lock modes, direct
`validate_pre_pr_readback()` modes, `WU_SESSION_MIGRATION_STATE_DIR`,
`_state_root()`, `_journal_path()`, `_cutover_lock()`, transaction exception
recovery, `recover_incomplete_transaction()`, `_rollback_recovery_target()`,
transaction cleanup, target-artifact cleanup, and journal removal are required
point-in-time examples, not an exhaustive name-seeded filter. Another reachable
mode enters the same inventory. Public helper and recovery modes outside the
detailed CLI comparison remain independent adjacent obligations; they do not
borrow CLI authority and cannot disappear from accounting.

Every accepted capability has exactly one `accepted_capability_accounting`
record containing its capability ID, all source occurrence IDs, all support or
transition candidate IDs, all authority-constraint candidate IDs, all corrective
record IDs, and all comparison-blocking or independent-adjacent obligation IDs.
Each listed collection is deterministic;
an unavailable relation is represented by its exact obligation rather than an
empty collection. A capability may validly have both semantic occurrences and an
adjacent obligation, so capability closure is measured through this one record
rather than forcing those two sets to be disjoint.

Only after those domains close does the mapper build the identity-bound
`authority_source_occurrence_inventory`. It contains every admitted semantic
occurrence for every accepted capability, entrypoint, invocation mode, namespace
choice, readback mode and direct caller, operation-specific executable validator,
detailed command/transition description, caller partition, and rollback,
recovery, cleanup, or corrective path. Candidate construction cannot define this
inventory's domain.

Each inventory member contains an injective structured `source_occurrence_id`
made from the common repository identity, authority source-blob and partition
identities, raw candidate ID, authority partition identity, source path and
content identity, exact source span and occurrence content identity, authority
role, occurrence kind, and occurrence ordinal within that exact span only when
the source itself contains repeated semantic records. None of these fields is
delimiter-concatenated, and no normalized candidate semantics appears in the
occurrence identity.

Every source occurrence receives exactly one record in
`authority_source_occurrence_dispositions`. Each record contains the single
`source_occurrence_id`; a disposition of `admitted-support-candidate`,
`admitted-transition-candidate`, `admitted-authority-constraint-candidate`,
`independent-adjacent-obligation`, `conflict`, or `unsupported-syntax-adapter-
obligation`; exactly one candidate ID for an admitted disposition and `null`
otherwise; conflict details for `conflict`; or one exact `failure_obligation`
identity for either obligation disposition. There is no clean `excluded`
disposition for a source occurrence derived from an accepted effecting
capability. Every conflict or obligation records `decision_relation` as
`comparison-blocking` or `independent-adjacent`.

`authority_constraint_inventory` preserves an effecting authority occurrence
that explicitly owns only a bounded caller, authorization, invocation-mode,
side-effect, namespace, lock, rollback/recovery, or readback constraint and does
not purport to define a complete support path or transition. Each candidate has
one source occurrence, exact applicable capability/operation/transition IDs,
explicit `asserted_authority_fields`, exact values, and evidence. It cannot
establish support or transition completeness by itself, borrow an unstated
field, or decorate a candidate discovered elsewhere. Every asserted field is
compared exactly with the corresponding complete authority fact; explicit
inequality is a comparison-blocking authority conflict and an unasserted field
is not defaulted. This allows optimized caller contracts and manifests to retain
the exact invocation semantics they own without pretending to restate a full
edge.

Every rollback, recovery, cleanup, and corrective raw occurrence additionally
maps one-to-one to a `corrective_capability_record` containing:

- its source occurrence and accepted capability IDs;
- exact acting caller or `null`;
- authorization antecedents and evidence;
- lock acquisition/ownership antecedents and evidence;
- structured state-root, lock, journal, and target namespace identities plus
  environment, path, inode, or other alias evidence;
- transaction attempt identity and journal identity, each exact or `null` with a
  cause-preserving obligation rather than an invented value;
- journal phase and phase-dependent intended disposition, including rollback,
  preserve, complete-commit, artifact cleanup, journal removal, or refuse;
- exact affected targets, read/write/reverse/cleanup effects, and read-only
  judgment effects; and
- completion evidence, including target, parent-fsync, cleanup, and journal
  disposition evidence or the exact incomplete cause.

These records remain independent from documentation-drift comparison unless the
occurrence directly supplies an asserted support or transition field. They are
nevertheless mandatory obligation accounting and prevent a bare `None` when
non-clean; acting caller, authorization, lock, namespace, attempt, journal,
phase, target, effect, or completion evidence is never collapsed to a bare
unexplained `null`.

The closed domain requires all of these exact equalities before support,
`enumeration_complete`, repair, or `None`:

`authority_source_domain_blob_ids == authority_source_blob_inventory_blob_ids`

`authority_source_blob_ids == authority_partition_span_inventory_blob_ids`

`authority_source_code_points == authority_raw_candidate_covered_code_points + explicit_grammar_boundary_code_points`

`authority_raw_candidate_ids == authority_raw_candidate_disposition_candidate_ids`

`admitted_semantic_raw_candidate_ids == authority_source_occurrence_raw_candidate_ids`

`accepted_capability_ids == accepted_capability_accounting_capability_ids`

`accepted_capability_accounting_occurrence_ids == authority_source_occurrence_ids_by_capability`

`accepted_capability_accounting_obligation_ids == capability_failure_obligation_ids`

`admitted_authority_constraint_candidate_ids == completed_authority_constraint_candidate_ids`

`authority_source_occurrence_ids == authority_source_disposition_occurrence_ids`

`corrective_source_occurrence_ids == corrective_capability_record_source_occurrence_ids`

The `+` expression denotes a disjoint exact partition, not a numeric-only count
check. Every ID occurs exactly once on its disposition side. Inapplicable fields
are `null` only with the required cause and obligation. Every admitted support or
applicable transition candidate must then appear in exactly one completed
comparison. Conflicts and adapter obligations remain non-clean. A comparison-
blocking obligation prevents only its affected membership or wiring
determination. An independent-adjacent obligation remains reportable alongside a
completed drift determination and cannot erase it. Only after all applicable
equalities close may reconciliation map authority candidates to support or
transition comparisons.
No source may merely decorate another source's domain, and no parser may silently
filter a raw candidate, capability, or source occurrence before accounting.

Every canonical declaration receives one `operation_support` record. Importable
helper modes, including independent calls with `lock_already_held=True`, cannot
borrow lock ownership or completed recovery from `main()` and remain outside
this generic detailed-CLI claim comparison. Self-locking helper mode
`lock_already_held=False` is likewise a separately inventoried non-CLI
capability, not evidence that the detailed human CLI entrypoint was exercised.
An environment override, alternate state root, different lock inode or journal
namespace over the same targets, unbound target-to-namespace relationship,
omitted reachable mode, or accepted helper mode without its own authority and
antecedents produces an `independent-adjacent` authority obligation. It is never
detailed CLI support and cannot establish live acceptance, but it also cannot
erase membership or wiring drift established from the exact detailed CLI and
applicable detailed/caller authorities. This specification records the adjacent
runtime boundary; it does not change the override, namespace selection, helper
authority, or any runtime code and does not claim that the current runtime is
globally locked, safe, or available. Rollback, recovery, cleanup, and corrective
modes receive the complete `corrective_capability_record` above even when they
are independent adjacent; no helper or corrective occurrence can be reduced to
an unexplained caller `null` or omitted because it is outside CLI support.

If the declaration and a required detailed CLI, detailed-command, or applicable
caller comparison source disagree, or those required sources cannot be
reconciled, `authority_state` is `conflict` or `unresolved` and
`evidence_state` is `authority-conflict` for the affected comparison. An
unavailable required source instead uses the cause-specific evidence state and
recovery contract below. That comparison-blocking state is neither drift nor
`None` for the affected axis. In contrast, alternate namespace, imported-helper,
direct-readback, unrelated capability, or global-serialization disagreement is
recorded under `adjacent_authority_state` and `adjacent_authority_obligations` as
`independent-adjacent`. It remains non-clean and reportable, including beside a
documentation-drift result, but does not prohibit narrowly scoped generic-claim
repair guidance. The finding retains each disagreeing source and records
recommended reconciliation routes to the runtime-migration owner for
declaration, executable admission, effects, lock/recovery context, transaction
completion, namespace binding, and readback mode; the detailed-README owner for
human command forms; and the owning caller document for invocation partition,
progression, and caller-owned closure. These owner labels are advisory routing
recommendations at `WRITE`; they do not authorize an actor or prove
reconciliation.

Top-level `authority_state` is one of `aligned`, `conflict`, or `unresolved`.
It is comparison-scoped and is `aligned` only when every per-member detailed CLI
support record and every applicable transition-candidate partition and
comparison agrees across its required executable, exclusive CLI readback,
detailed-command, and caller sources; every source occurrence has exactly one
permitted disposition; the source-domain/blob/span/coverage/raw-candidate/
capability/occurrence and corrective-record equalities all close; and the support
and transition comparison equalities below pass. `adjacent_authority_state` is
independently `no-obligation`, `non-clean`, or `unresolved`; `no-obligation`
means only that the independently closed accepted source and capability domain
produced no adjacent obligation, not that global runtime safety or external
caller absence was proved. `authority_conflicts` retains each source, disputed
semantic fact, decision relation, and observed value; `reconciliation_owner`
retains recommended source-owner routing, not an enforced authority decision.

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
`catalog_anchor` occurrence inside its admitted structured
`target_claim_identity`; those two fields alone are not the identity. This point-
in-time candidate list is review context, not identity-bound claim discovery or
a complete inventory. Direct source comparison is review evidence for the
contract; these anchors remain claims rather than co-equal membership or
transition authority.

## Unwanted behaviors

The two behaviors are related but evaluated independently from each other and
from adjacent runtime authority obligations. A result records
`documentation_drift_outcome` for each applicable axis and may carry a drift
finding together with independent alternate-namespace, helper, capability, or
global-serialization obligations. No such obligation may overwrite a completed
documentation comparison.

`documentation_drift_outcome` is a structured record with
`operation_membership` and `conditional_wiring`, each exactly `present`,
`absent`, `not-applicable`, or `indeterminate`. `present` and `absent` derive
only from the completed target comparison for that axis; `not-applicable`
requires resolved claim scope; and `indeterminate` names a comparison-blocking
obligation. An independent adjacent obligation does not change either completed
axis value.

### Operation-membership drift

An active generic claim whose `claim_completeness` is `exact` or
`complete-implied` and whose `command_domain` is `runtime-only` or `mixed`
presents the `wu-session-runtime-write-v1` operation inventory as complete for
its resolved caller, lifecycle, or cohort domain, but its exact-token runtime and
unsupported-operation `catalog_operations` differ from the identity-bound
`applicable_canonical_operations` subset. Authorized support commands and
authorized non-operation commands are preserved target content but do not enter
either set difference. One or both of `missing_operations` and
`extra_operations` is non-empty. The full
`canonical_operations` remains present as ticket-required declaration evidence.
The common repository identity, membership applicability, lossless target-
presentation candidate/raw-command/command-disposition/raw-operation/interpreted
equalities, independently closed authority source/capability equalities, detailed
CLI source-occurrence and support-comparison equalities, and every applicable
canonical declaration's `operation_support` record must resolve and align before
this mismatch can become catalog drift or drive repair guidance. Disagreement in
one of those comparison facts blocks the affected membership result. Alternate
namespace, imported-helper, rollback, recovery, cleanup, corrective, unrelated-
capability, or global-serialization gaps remain fully accounted simultaneous
`independent-adjacent` obligations and do not erase a resolved missing or extra
operation.

### Conditional-wiring drift

An active generic lifecycle claim whose `claim_completeness` is `exact` or
`complete-implied` presents the writer sequence as complete in a resolved claim
domain, but the
exhaustive revision-bound transition aggregate omits or contradicts one or more
supported conditional transitions in that domain. Operation-specific
executable validators, the exclusive live-storage CLI readback mode, detailed
command semantics, and every applicable owning caller partition/progression
source independently contribute comparison candidates at the common identity.
Other readback, helper, namespace, rollback, recovery, cleanup, and corrective
modes remain separately inventoried occurrences with complete mode-specific
records.
Reconciliation preserves the comparison authorities' distinct ownership:
executable validators establish transition admission, source-state eligibility,
effects, and exact `sole_writer`; only top-level mode-bound live-storage CLI
readback establishes post-write live acceptance; and detailed command and caller
authorities own human command form, invocation partition, progression, caller-
owned closure, and their exact writer authority. Target-side treatment is
derived only from a lossless target transition occurrence inventory, one
structured assertion with explicit claimed-field presence per occurrence, and
completed claimed-field witnesses that retain every canonical authority field.
Operation-token presence alone cannot mean `included`. The known
`phase0-reresolve` recurrence is one member of the admitted transition domain,
not evidence that the domain contains only one member.

These are documentation-contract drift behaviors. They are not runtime writer
failure, parser failure, request-validation failure, transaction failure,
protected-state corruption, or evidence that a conditional transition is
mandatory for every normal WU.

## Claim taxonomy

The exact admitted target occurrence receives two orthogonal deterministic
classifications before any membership or wiring comparison. Context supporting
each classification remains in evidence. Classification never discovers or
decides the status of another occurrence. The ticket-required `claim_kind` is no
longer an overloaded scalar; it is the structured record
`{claim_completeness, command_domain}` and preserves both independent values.

| `claim_completeness` | Meaning | Comparison disposition |
|---|---|---|
| `exact` | The prose explicitly says the inventory or sequence is exact, exhaustive, or complete in its claimed scope. | Compare every applicable membership and wiring obligation in the resolved scope. |
| `complete-implied` | Wording and structure strongly present a complete inventory or sequence in its claimed scope without an explicit completeness token. | Compare while retaining the context that supports the completeness and scope inference. |
| `delegated` | The prose unambiguously delegates exact membership or detailed sequencing to the applicable declaration, executable, detailed-command, and caller authorities and does not restate an exhaustive set. | Non-fire unless surrounding context independently makes a complete claim. |
| `partial-example` | The prose clearly labels members as examples, selected cases, illustrative, or partial. | Non-fire unless surrounding context independently implies completeness. |

| `command_domain` | Meaning | Comparison disposition |
|---|---|---|
| `runtime-only` | The complete claim scope is runtime-operation commands; every recognized command occurrence is runtime-operation-shaped or an exact unsupported operation, with no authorized support or other non-operation command occurrence. | Compare runtime-member and unsupported-operation occurrences only. |
| `non-runtime-only` | The claim contains only parser-registered support commands or other commands with identity-bound evidence that they do not assert runtime-operation membership. | Membership is not applicable; preserve the commands as valid content. |
| `mixed` | One complete claim intentionally co-locates at least one runtime/unsupported-operation occurrence and at least one authorized support or other non-operation command occurrence. | Compare only the runtime and unsupported-operation occurrences. Support and authorized non-operation commands remain valid content and cannot hide a runtime omission. |

Command-domain classification is based on complete lossless raw-command
accounting, exact target wording, parser registration, and the detailed command
contract. It is not inferred from canonical-name membership. An exact
operation-shaped value absent from runtime authority is an
`unsupported-operation`, remains exact target evidence, and participates on the
runtime side of the domain classification rather than being recast as support.

For example, a complete claim containing exact `dry-run`, `apply`, or
`validate-pre-pr-readback` command occurrences together with one or more runtime
operation commands is `mixed`: those parser/detail-bound support commands remain
valid and are never extras, while the runtime side still compares against every
applicable canonical operation. A runtime omission therefore fires even when
all support commands are valid; a non-fire requires the runtime side to be
complete. Repair preserves the support commands.

When the target is readable and identity-bound and its `claim_scope` is clear,
but completeness wording cannot resolve among `complete-implied`, `delegated`,
`partial-example`, or another allowed value, the result uses
`evidence_state: claim-classification-indeterminate`,
`failure_cause: ambiguous-claim-completeness`, and
`claim_kind: {claim_completeness: null, command_domain: <resolved-or-null>}`.
When complete raw-command accounting cannot resolve the domain, it uses
`evidence_state: command-domain-indeterminate`,
`failure_cause: ambiguous-command-domain`, and
`claim_kind: {claim_completeness: <resolved-or-null>, command_domain: null}`.
Both causes and both `null` values remain when both dimensions are ambiguous.
The exact target-document owner and exact selecting caller are advisory
clarification and escalation routes at `WRITE`; those labels do not authorize
action. No operation token, canonical-name match, confidence score, support
command, or default may coerce completeness to `exact` or command domain to
`runtime-only`, and no affected drift or `None` is permitted until a fresh
invocation binds the clarified content at one repository identity and both
applicable classifications resolve.

When a prior identity, selector, availability, or lifecycle failure prevents
classification, `claim_kind` is the non-semantic control record
`{claim_completeness: unavailable, command_domain: unavailable}`. It never
permits comparison or non-fire. Thus unavailable evidence is not confused with a
successful classifier decision, while ambiguity remains explicitly nullable per
dimension.

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

Membership applicability is a separate resolved field:

- `applicable`: common-identity caller, lifecycle, or cohort authority defines
  the complete runtime-operation domain for this exact claim. Both
  `runtime-only` and `mixed` command domains can be applicable.
- `not-applicable`: the occurrence makes no membership-completeness claim, or a
  resolved `non-runtime-only` command domain contains no runtime-operation side.
- `ambiguous`: the evidence cannot determine whether, or to which named domain,
  membership completeness applies.

Occurrence-only evidence is `not-applicable` to membership unless its own
identity-bound wording independently claims complete support for an explicitly
named domain; in that case it is `applicable` only to that domain. Applicability
cannot be inferred from operations that happened to occur. `ambiguous` produces
`evidence_state: membership-applicability-indeterminate` and
`failure_cause: ambiguous-membership-applicability`; it never permits set
comparison, drift, repair, or `None`.

Command-domain applicability never substitutes for completeness. A
`runtime-only` or `mixed` partial example remains a non-fire for completeness;
an exact or complete-implied mixed claim remains accountable for every applicable
runtime member even when support commands are present. A resolved
`non-runtime-only` claim can be membership-inapplicable without treating its
support commands as missing, extras, or evidence that another axis is clean.

## Membership comparison contract

For a membership-applicable claim with `claim_completeness` `exact` or
`complete-implied` and `command_domain` `runtime-only` or `mixed`:

- `canonical_operations` is the unique set extracted from revision-local
  `RUNTIME_OPERATIONS`; it is always the full ticket-required declaration set,
  not declaration-only proof of executable support and not the expected set for
  every scoped claim.
- `applicable_canonical_operations` is the unique subset of
  `canonical_operations` derived from common-identity caller, lifecycle-domain,
  or cohort authority for the exact target. A repository-global claim uses the
  full set. A named-domain or selected-cohort claim uses only members that the
  bound authority assigns to that domain or cohort.
- `resolved_catalog_bearing_source_span` is the complete exact source span inside
  the admitted claim that presents the purported catalog. It is selected before
  command or operation recognition and retains its raw text and content identity.
- `target_presentation_candidate_inventory` is a lossless pre-recognition scan
  of that complete span. Every syntactic Markdown list item, backtick code span
  or fenced-code content span, exact command/shorthand parent and operation-token
  child, detailed-command operand, and explicitly bounded residual prose fragment
  receives one injective candidate record with exact source span, raw text
  identity, presentation kind, parent/container candidate IDs, and source-order
  ordinal.
- `target_presentation_candidate_dispositions` accounts for every presentation
  candidate exactly once as `recognized-command`, `operation-token-child`,
  `authorized-non-command`, or `ambiguous/unsupported`. Only a complete command
  parent may be `recognized-command`; only its one exact token child may be
  `operation-token-child`. A structural parent may be `authorized-non-command`
  only when its complete non-boundary content is covered by child candidates and
  exact grammar boundaries and the disposition cites that coverage. Every other
  non-command requires an identity-bound semantic reason. An unfamiliar,
  malformed, misspelled, or operation-shaped candidate cannot be authorized
  merely because it is absent from `RUNTIME_OPERATIONS`.
- `target_presentation_source_coverage` maps every code point in the resolved
  span to candidate content or an exact grammar boundary before any disposition.
- `raw_command_occurrences` contains exactly one raw occurrence for every
  `recognized-command` parent and preserves that parent, its operation-token
  child when present, complete raw text, exact option/suffix text, source span,
  enclosing presentation syntax, and occurrence identity.
- `command_occurrence_dispositions` gives every raw command occurrence exactly
  one disposition: `runtime-member`, `authorized-support-command`,
  `unsupported-operation`, `authorized-non-operation`, or `ambiguous`.
  `runtime-member` requires the exact operation-token child to bind to parser
  registration and the detailed command contract at the common identity.
  `authorized-support-command` requires exact parser registration plus the
  detailed support-command contract and never enters runtime membership.
  `unsupported-operation` preserves an exact operation-shaped token and command
  form that lacks applicable runtime registration; it is retained as an extra.
  `authorized-non-operation` requires identity-bound command/domain evidence that
  the occurrence does not purport to be a runtime operation. `ambiguous` binds a
  comparison-blocking obligation and can never be silently recast.
- `raw_catalog_operation_occurrences` contains exactly one raw operation
  occurrence for every `runtime-member` or `unsupported-operation` command. It
  preserves the command occurrence ID, operation-token child candidate ID, exact
  raw token, complete parent command and suffix, source span, enclosing syntax,
  and occurrence identity. Support and authorized non-operation commands remain
  in their own deterministic lists and do not enter this collection.
  `catalog_operation_interpretations` and
  `interpreted_operation_occurrences` each account for every raw operation
  occurrence exactly once as an exact parser token, an explicitly authorized
  presentation translation, an exact unsupported operation-shaped string, or an
  ambiguity obligation.
- `catalog_operations` is the unique set of exact interpreted token strings from
  runtime-member and unsupported-operation raw occurrences; unsupported values
  remain their exact strings. `authorized_support_commands`,
  `authorized_non_operation_commands`, `unsupported_operation_occurrences`, and
  `ambiguous_command_occurrences` remain separate deterministic projections.
- `missing_operations = applicable_canonical_operations - catalog_operations`.
- `extra_operations = catalog_operations - applicable_canonical_operations`.
- All resolved operation and command collections are deterministic sorted lists.
- Both difference fields remain present when empty. An empty list means the
  comparison resolved to an empty set.
- An unavailable or membership-inapplicable collection is `null`, not an empty
  list. `membership_applicability` and its evidence distinguish a resolved
  inapplicable comparison from unknown evidence; neither masquerades as a
  completed set comparison.
- A membership-drift candidate exists only when the claim is applicable and at
  least one resolved difference is non-empty.
- Ordering differences alone are inapplicable because declared membership is a
  set.

The supported target-presentation grammar is fixed at `WRITE`. It scans the
resolved source span in source order and records overlapping structural parents
plus non-overlapping semantic leaves with this precedence: an exact complete
detailed command beginning with literal source text
`python3 tools/wu-session-migration`; the exact bounded shorthand production
below inside an admitted operation-catalog claim; otherwise the complete code-
span content; otherwise maximal residual prose fragments outside code. Markdown
list-item containers include their marker and continuation lines through the
next sibling item or end of the catalog-bearing span. Backtick spans use the
exact opening delimiter length and the next equal closing delimiter. Residual
prose leaves are maximal non-whitespace runs split by ASCII comma, semicolon,
colon, sentence-terminal period, parentheses, brackets, braces, and line
boundaries; delimiters and whitespace are retained in the source-coverage map.
Unclosed delimiters, multiline constructs that cannot satisfy these rules,
overlapping semantic leaves, uncovered non-boundary text, and any syntax outside
this grammar receive `ambiguous/unsupported`, never silent exclusion.

The exact bounded shorthand production is available only inside the complete
resolved span of an admitted operation-catalog claim:

`<exact-runtime-operation> --request <path>`

`<exact-runtime-operation>` is one literal code-point sequence matching
`[a-z0-9]+(?:-[a-z0-9]+)+`; each shown space is exactly one ASCII space;
`--request` and `<path>` are exact literals; and no leading, trailing, or extra
operand is allowed. The complete raw code-span content is retained as one parent
command candidate, including the exact ` --request <path>` suffix. Exactly one
covered `operation-token-child` candidate spans only the
`<exact-runtime-operation>` token; the suffix remains exact parent evidence and
explicit grammar-boundary coverage. Recognition of this production does not
consult `RUNTIME_OPERATIONS`. The child becomes
`runtime-member` only after exact parser-registration and detailed-command
contract binding; an unknown or misspelled but otherwise exact operation token
becomes `unsupported-operation` and remains an exact extra.

An admitted command-catalog claim may also contain one bare code-span command
whose complete content matches `[a-z][a-z0-9]*(?:-[a-z0-9]+)*`. The complete
code span is the command parent and one exact child covers the token; recognition
is syntactic and does not consult parser or canonical names. Semantic disposition
then binds a runtime token to runtime parser/detail authority, a support token to
support parser/detail authority, an operation-shaped unsupported token to
`unsupported-operation`, and any other value to identity-bound
`authorized-non-operation` or fail-closed `ambiguous`. This bounded bare-token
production permits exact support-command accounting without treating arbitrary
prose as a command or seeding discovery from known command names.

The nearest inverse dispositions are fixed. A wrong option, malformed or
different placeholder/path operand in the shorthand form, missing operand, or
extra operand produces an `ambiguous` command occurrence and a comparison-
blocking obligation. An exact unsupported operation in the otherwise valid
production remains `unsupported-operation`, not ambiguity. An exact parser-
registered support command with its detailed command form is
`authorized-support-command`, including in a mixed claim. Other exact command
content may be `authorized-non-operation` only with identity-bound evidence that
it makes no runtime-operation assertion. Non-command prose or structure is
`authorized-non-command` only with complete child/boundary coverage and its exact
semantic reason. Unsupported punctuation, escaping, case, Unicode, or boundaries
is ambiguous rather than normalized.

At the point-in-time known target in `conventions/wu-session-lifecycle.md`, each
of the seven complete code spans under `Exact operations are` matches the bounded
shorthand production, retains its full parent and suffix, produces exactly one
token child, and binds to parser registration plus the detailed command contract
as `runtime-member`. Subject to all other identity, authority, and accounting
gates, the deterministic target set is those seven exact tokens,
`missing_operations` contains `phase0-reresolve`, and `extra_operations` is
empty. This is a specification-level expected mapping for the named source, not
an executed detector result at `WRITE`.

The accepted operation-token interpretation is otherwise exact parser-token
grammar. Case folding, Unicode normalization, underscore/hyphen substitution,
leading or trailing whitespace removal, internal whitespace rewriting,
delimiter rewriting, escape interpretation, abbreviation, broad command
rewriting, canonical-name-seeded filtering, or any other semantic folding is
prohibited. An explicit presentation translation outside the bounded shorthand
is allowed only when an identity-bound declaration/detailed-command authority
record names the exact source syntax, exact input and output strings, target
scope, and authorization evidence; the raw command and operation occurrences
still remain preserved.

Membership comparison and `None` require all six lossless equalities, with
exactly one record at each mapping step:

`target_presentation_candidate_ids == target_presentation_disposition_candidate_ids`

`recognized_command_candidate_ids == raw_command_occurrence_source_candidate_ids`

`raw_command_occurrence_ids == command_occurrence_disposition_occurrence_ids`

`runtime_or_unsupported_operation_token_child_ids == raw_catalog_operation_source_candidate_ids`

`raw_catalog_operation_occurrence_ids == catalog_operation_interpretation_occurrence_ids`

`catalog_operation_interpretation_occurrence_ids == interpreted_operation_occurrence_ids`

The source-coverage map must also cover every code point in the resolved span as
candidate content or an explicit grammar boundary. Duplicate dispositions,
missing candidates, missing raw command or operation occurrences, missing
command dispositions, missing interpretations, missing interpreted occurrences,
uncovered text, or ambiguous syntax creates a cause-preserving target-
presentation obligation and prohibits the affected membership comparison,
repair, or `None`. No recognizer seeded by canonical operation names can define
or narrow this pre-recognition domain. Support-command presence never satisfies,
defaults, or suppresses a missing runtime member.

Every canonical operation has exactly one deterministic `operation_support`
record containing:

- `operation`
- `authority_source_blob_ids`
- `authority_raw_candidate_ids`
- `accepted_capability_ids`
- `capability_inventory`
- `entrypoint_inventory`
- `invocation_mode_inventory`
- `authority_source_occurrence_ids`
- `corrective_capability_record_ids`
- `authority_constraint_candidate_ids`
- `support_candidate_inventory`
- `admitted_support_candidate_ids`
- `completed_support_candidate_ids`
- `parser_exposure`
- `command_request_equality`
- `projection_or_handler_path`
- `lock_and_recovery_antecedents`
- `canonical_state_namespace`
- `target_namespace_binding`
- `closed_request_acceptance`
- `transaction_completion_evidence`
- `readback_mode`
- `readback_enforcing_antecedents`
- `adjacent_authority_obligation_ids`
- `detailed_command_contract`
- `support_state`, one of `supported`, `conflict`, or `unresolved`
- `evidence_paths`

Each inventory is exact for the operation, common repository identity, and
independently closed authority source/capability domain. `capability_inventory`
names the detailed human CLI capability and every accepted importable write,
readback, rollback, recovery, cleanup, or corrective capability.
`entrypoint_inventory` binds
each capability to its actual parser, `main()`, public helper, or private helper
entry chain. `invocation_mode_inventory` records the exact mode, named acting
caller or `null`, support/obligation disposition, mode-local namespace, lock
ownership, completed-recovery evidence, attempt/journal identity when applicable,
live-acceptance or corrective disposition, and `decision_relation`. At the
inspected source this includes the
top-level CLI path, imported `apply_runtime_request()` with
`lock_already_held=False`, the `main()`-owned nested call with
`lock_already_held=True`, and an independent imported call with
`lock_already_held=True`; another observed reachable mode must be added rather
than silently excluded.

`canonical_state_namespace` is one structured observation of the state-root,
lock-inode, and journal namespace selected by the exact top-level CLI mode.
`target_namespace_binding` records whether and how that CLI observation binds to
the exact planning-root, manifest, and active-index target identities. These
fields preserve the prior support scope and prevent the CLI mode from borrowing
another mode's antecedents; they do not assert that the runtime enforces one
global namespace. An environment-selected override, alternate root, different
lock inode or journal namespace, or missing target binding in another reachable
capability produces an `independent-adjacent` obligation even when that
capability successfully acquires its own lock and sees no pending journal.

Every identity-bound support occurrence is named by
`authority_source_occurrence_ids` and maps through exactly one occurrence
disposition to either one `support_candidate_inventory` member, one bounded
`authority_constraint_inventory` member, an evidence-backed independent-
adjacent obligation, a comparison-blocking conflict, or an unsupported-syntax/
adapter obligation. An accepted effecting occurrence cannot be clean-excluded;
only a raw candidate proven inert under the closed exclusion rule may stop
before semantic occurrence construction.
Every support candidate contains an injective structured `candidate_id`, its
single `source_occurrence_id`, operation, capability, entrypoint, invocation
mode, named caller or `null`, parser/request/projection/transaction facts,
canonical namespace and target binding, readback mode and disposition, and
evidence paths. No support candidate can combine multiple source occurrences.
`support_state: supported` requires the complete source-domain/blob/span/
coverage/raw-candidate/capability/occurrence and corrective-record equalities for
the support facts on which it depends, completed exact comparisons for every
applicable authority constraint, plus this exact admitted/completed equality:

`admitted_support_candidate_ids == completed_support_candidate_ids`

Every admitted support candidate has one completed field-by-field support
comparison. A source-domain mismatch, uncovered source span or raw candidate,
unaccounted accepted capability or corrective occurrence, silent pre-candidate
omission, comparison-blocking conflict, unresolved comparison adapter obligation,
duplicate disposition, or incomplete comparison prevents support. An
independently dispositioned helper, namespace, or corrective capability
obligation remains non-clean in
`adjacent_authority_obligation_ids` but does not change the detailed CLI
`support_state`.

A record is `supported` only as a functional CLI-reachability claim: the
detailed human operation command enters through `__main__.py`, is parser-exposed,
and enters `main()`;
`main()`'s exact acting context records its selected lock and proves recovery for
its selected journal namespace completed before its nested runtime helper call;
exact command/request equality and closed operation-specific request validation
resolve; an operation-specific projection or handler resolves; transaction
completion returns before the CLI success result; detailed command semantics
agree; and all source-closure, comparison-occurrence, and support-candidate
equalities pass.
Importable modes always remain outside this generic CLI support decision.
Omitting a reachable mode, using an override or alternate namespace, or finding
an unbound mode creates an independent adjacent obligation rather than changing
the already established detailed CLI support state.

`support_state: supported` makes no availability, latency, throughput,
bounded-wait, bounded-lock-acquisition, bounded-lock-hold, scale, state-size, or
mature-state-cost claim. Those dimensions are outside this eval's support and
generic-document repair semantics and belong to separately authorized later
lifecycle work. Neither a non-fire nor repair guidance may strengthen
`supported` into one of those claims or imply that global exclusion has an
accepted bound.

For pre-PR readback, `readback_mode` is the deterministic list of applicable
mode records, and each record's `readback_enforcing_antecedents` distinguishes:

- `live-storage-cli`: top-level `validate-pre-pr-readback` enters through
  `__main__.py` and `main()` under the lock after recovery, omits
  `expected_manifest`, reads `manifest_path`, and identity-checks that live
  manifest plus the other required effects. Only this mode can establish post-
  write live acceptance.
- `phase3-expected-manifest`: the exact Phase 3 request-validation path has
  already bound the live Phase 3 source manifest and historical
  operator/contract identities, requires the canonical authenticated
  `phase0-reresolve` readback after the historical-blob mismatch, and calls
  `validate_pre_pr_readback(..., expected_manifest=manifest)`. This is
  projection/historical validation and cannot populate live acceptance by
  itself.
- `direct-import-live-without-expected-manifest`: every direct imported call
  that omits `expected_manifest`, with the exact caller identity or `null`,
  namespace, lock/recovery evidence, and live-acceptance disposition. It cannot
  borrow `main()` antecedents and always has
  `live-acceptance-disposition: unauthorized-at-WRITE`. A named direct caller
  remains an observed occurrence but cannot establish live acceptance; an
  unnamed, unbound, or purported direct-live call is a separate adjacent
  authority obligation. Authorizing it requires later contract work.
- `direct-import-projection-with-expected-manifest`: every direct imported call
  that supplies `expected_manifest`, with the exact caller identity or `null`,
  namespace, lock/recovery evidence, and `projection-only` live-acceptance
  disposition. It cannot establish live acceptance even if its projection
  comparison succeeds and remains distinct from the CLI live mode.
- `not-applicable`: the operation has no applicable pre-PR readback obligation,
  with the operation-specific reason retained rather than borrowing another
  mode's evidence.

Records are unique and sorted by `operation`. Parser registration, request
closure, detailed Markdown, callers, tests, and other claims cannot vote an
operation into or out of `canonical_operations`; they instead establish
documented CLI support or expose a named comparison-blocking or independent
adjacent authority/integration obligation.

## Conditional-wiring comparison contract

Wiring is evaluated separately from membership. An operation name in a complete
membership list does not establish its supported lifecycle edge. A
membership-only claim does not acquire sequencing obligations.

The ticket-required `wiring_transition` output remains one field, but it is an
aggregate record rather than one selected transition. Every resolved aggregate
contains:

- `evaluated_repository_identity`
- `target_claim_identity`
- `catalog_path`
- `catalog_anchor`
- `enumeration_evidence_paths`
- `authority_source_domain`
- `authority_source_blob_inventory`
- `authority_partition_span_inventory`
- `authority_source_coverage`
- `authority_raw_candidate_inventory`
- `authority_raw_candidate_dispositions`
- `accepted_capability_inventory`
- `accepted_capability_accounting`
- `authority_partition_inventory`
- `authority_source_occurrence_ids`
- `authority_source_occurrence_dispositions`
- `authority_constraint_inventory`
- `admitted_authority_constraint_candidate_ids`
- `completed_authority_constraint_candidate_ids`
- `corrective_capability_records`
- `transition_candidate_inventory`
- `admitted_applicable_candidate_ids`
- `completed_transition_candidate_ids`
- `canonical_transition_ids`
- `applicable_transition_ids`
- `semantic_equivalence_witnesses`
- `target_transition_source_coverage`
- `target_transition_occurrence_inventory`
- `target_transition_occurrence_dispositions`
- `target_transition_assertions`
- `target_assertion_to_canonical_transition_witnesses`
- `admitted_target_assertion_ids`
- `completed_target_assertion_comparison_ids`
- `transition_comparisons`
- `omitted_transition_ids`
- `contradicted_transition_ids`
- `enumeration_complete`

`authority_partition_inventory` names, at the common identity, every required
executable-validator partition, every distinct readback-mode partition, the
detailed command/transition-semantics partition, and each implementation
workflow, operator, and resumer partition/progression source applicable to the
resolved domain. Its source-blob and exact raw partition spans must equal the
corresponding independently admitted `authority_source_domain` entries before
semantic extraction. Each partition independently discovers candidates from its
own authority only after complete source coverage, raw-candidate disposition,
accepted-capability accounting, and identity-bound source occurrences have
closed. A missing source blob or partition span, uncovered code point, missing or
duplicate raw-candidate disposition, unaccounted effecting or corrective
capability, silent pre-candidate occurrence omission, duplicate occurrence
disposition, or source used only to decorate candidates discovered elsewhere
leaves its accounting incomplete. Only the top-level live-storage CLI readback
partition contributes live-acceptance comparison candidates;
`expected_manifest`, direct-import, rollback, recovery, cleanup, and corrective
partitions receive exact dispositions for their actual projection, reversal,
completion, cleanup, or adjacent semantics and cannot supply live acceptance.

Every `transition_candidate_inventory` member is admitted by exactly one
`admitted-transition-candidate` source-occurrence disposition and contains:

- `candidate_id`, an injective structured record containing the common
  repository identity, source-authority role, source path and content identity,
  semantic source occurrence, and candidate occurrence
- `source_authority`
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
- `applicability` and its target-scope evidence
- `resulting_transition_id`
- `disposition_evidence`

Candidate ID fields are never delimiter-concatenated. `transition_id` is an
injective structured identity over every material edge semantic:

- exact `operation`;
- structured `source_conditions`;
- structured `predecessor_or_order`;
- structured `destination_or_successor`;
- `conditional`;
- exact `owning_caller_or_domain`;
- exact `sole_writer`;
- structured `effects`;
- exact `readback_authority`; and
- exact `readback_mode`.

The accepted normalization rules are typed structural equality; deterministic
sorting of explicitly unordered exact-value sets; canonical repository paths
under the target-path rules above; and structured predicate/effect records that
preserve operators, values, ordering semantics, and absence. Operation, caller,
domain, `sole_writer`, and readback identities use exact values. No missing field
is defaulted, no prose is weakened, and no case, Unicode, whitespace, delimiter,
alias, or semantic folding is accepted.

Two or more authorities' candidates may share one `resulting_transition_id` only
when an identity-bound `semantic_equivalence_witness` records all candidate IDs,
every raw material field from every source, the accepted normalization rule
applied field by field, the equal normalized value for every field, and evidence
paths. This field-by-field witness always includes exact `sole_writer` authority.
Unequal, missing, alternate, ambiguous, or uninterpretable writer authority or
any other material field produces a comparison-blocking conflict or cause-
preserving adapter obligation before transition identity deduplication and
cannot share a transition identity or comparison. Reconciliation must not erase
any raw candidate, accepted capability, or source occurrence. A candidate proven
inert may stop only at the raw-candidate closed exclusion rule; an occurrence
from an accepted effecting capability has no clean exclusion disposition. A
conflict cannot be relabeled as inert or adjacent.
`canonical_transition_ids` is the unique deterministic list of transition IDs
resulting from all admitted authority candidates. `applicable_transition_ids`
is the subset applicable to the resolved target scope.

`admitted_applicable_candidate_ids` is the deterministic set of transition
candidate IDs whose source-occurrence disposition is
`admitted-transition-candidate` and whose scope is applicable.
`completed_transition_candidate_ids` is the deterministic union of
`candidate_ids` carried by completed applicable transition comparisons.
`enumeration_complete` is true only when the independently authorized source-
domain/blob/partition-span sets and per-blob source coverage close; every raw
candidate, accepted capability, semantic occurrence, and corrective capability
record satisfies its exact equality; every admitted authority constraint has one
completed exact comparison; every named comparison-authority partition resolved
independently; every admitted comparison candidate has all material
authority transition fields including exact `sole_writer`, conditions, effects,
owner, and readback fields; every coalescence has a complete accepted equivalence
witness; no comparison-blocking source shape, occurrence, candidate, authority,
or adapter obligation is conflicted or unresolved; and this set is exactly equal:

`admitted_applicable_candidate_ids == completed_transition_candidate_ids`

The gate also requires one completed comparison for every applicable canonical
transition ID. `enumeration_evidence_paths` retains every source-domain entry,
blob, partition span, coverage record, raw candidate and disposition, accepted
capability, source occurrence and disposition, corrective record, transition
candidate, authority constraint and comparison, equivalence witness, adapter
obligation, and comparison witness.
Fully accounted independent adjacent obligations remain in that evidence and in
the finding but do not make comparison enumeration false. Support,
`enumeration_complete`, repair, and `None` are prohibited until all source-
closure and comparison occurrence-to-disposition and admitted-to-completed
equalities close. The result says nothing about another `target_claim_identity`.

Target-side wiring interpretation is independently lossless. Before looking for
a canonical operation or transition, the mapper builds
`target_transition_occurrence_inventory` over the complete resolved catalog-
bearing source span of a sequence claim. Its deterministic grammar projects
every source-ordered list-item container and every leaf from
`target_presentation_candidate_inventory` into one occurrence record; adjacent
leaves joined by an exact arrow (`->`), the words `before`, `after`, `then`, or
`followed by`, or one sentence boundary remain separate occurrences linked by
raw predecessor/order references. A delegation sentence is also an occurrence.
Unknown operation names, malformed arrows, unmatched conditions, unfamiliar
readback wording, and unsupported prose remain occurrences rather than being
filtered by canonical transition knowledge.

`target_transition_source_coverage` maps every target-presentation candidate in
that sequence span to exactly one target transition occurrence and records the
shared exact source span and raw text identity. It is complete before an
occurrence is classified as a transition, delegation, non-transition, or
ambiguity.

Every target transition occurrence preserves:

- injective `target_transition_occurrence_id` over target identity, exact source
  span, raw text identity, presentation candidate ID, and source-order ordinal;
- exact source span and raw text;
- raw operation wording;
- raw source conditions;
- raw predecessor/order wording;
- raw destination/successor wording;
- raw conditionality wording;
- raw effects wording;
- raw owning caller/domain wording;
- raw `sole_writer` wording;
- raw readback wording and mode;
- parent/container and adjacent occurrence IDs; and
- source coverage evidence.

`target_transition_occurrence_dispositions` gives every occurrence exactly one
disposition: `admitted-target-assertion`, `authorized-non-transition`, or
`ambiguous/unsupported`. Every occurrence also has exactly one structured member
of `target_transition_assertions`. An admitted member preserves all raw fields
above and contains an explicit `claimed_fields` presence map with exactly these
boolean keys:

- `operation`
- `source_conditions`
- `predecessor_or_order`
- `destination_or_successor`
- `conditional`
- `effects`
- `owning_caller_or_domain`
- `sole_writer`
- `readback_authority`
- `readback_mode`

It then interprets only the material fields whose presence value is `true`,
without defaulting:

- `target_assertion_id` and its single source occurrence ID;
- `assertion_kind`, `transition` or `delegation`;
- the complete `claimed_fields` map;
- exact `operation` when claimed, otherwise `null`;
- structured `source_conditions` when claimed, otherwise `null`;
- structured `predecessor_or_order` when claimed, otherwise `null`;
- structured `destination_or_successor` when claimed, otherwise `null`;
- exact `conditional` when claimed, otherwise `null`;
- structured `effects` when claimed, otherwise `null`;
- exact `owning_caller_or_domain` when claimed, otherwise `null`;
- exact `sole_writer` when claimed, otherwise `null`;
- exact `readback_authority` when claimed, otherwise `null`;
- exact `readback_mode` when claimed, otherwise `null`; and
- evidence paths.

An absent target field has presence `false`, an interpreted value of `null`, and
comparison result `unasserted`. It is not defaulted from canonical authority,
treated as equal, treated as contradictory, or made comparison-blocking. A
source-ordered complete sequence may explicitly assert operation and order
through its losslessly linked occurrence order without asserting conditions,
effects, owner, `sole_writer`, or readback details. Wording that purports to
assert a field has presence `true`; if its value cannot be interpreted exactly,
the assertion is `ambiguous/unsupported` and comparison-blocking rather than
silently changed to presence `false`.

An `authorized-non-transition` assertion retains the raw fields, uses `null` for
inapplicable interpreted fields, and cites the identity-bound reason and child
coverage proving that it contributes no transition assertion. An
`ambiguous/unsupported` assertion also retains every raw field, uses `null` only
for absent or uninterpretable material fields, preserves `claimed_fields: true`
for every purported but uninterpretable assertion, and binds one exact
comparison-blocking failure obligation. Token presence cannot change either
disposition to `admitted-target-assertion` or fill an unasserted field.

The target inventory must satisfy these exactly-once equalities before wiring
comparison or `None`:

`target_transition_occurrence_ids == target_transition_disposition_occurrence_ids`

`target_transition_occurrence_ids == target_transition_assertion_occurrence_ids`

`admitted_target_assertion_ids == completed_target_assertion_comparison_ids`

Every admitted assertion receives one field-by-field
`target_assertion_to_canonical_transition_witness`. The witness records the
assertion ID, every compared canonical transition ID, every raw and interpreted
material value on both sides, the complete claimed-field presence map, exact
normalization applied to each asserted field, and one per-field result of
`equal`, `unequal`, or `unasserted` for operation, conditions, predecessor/order
and destination/successor, conditionality, effects, owner/domain, exact
`sole_writer`, readback authority, and readback mode. The authority side always
retains every canonical field exactly, including conditions, effects, owner,
`sole_writer`, readback authority, and readback mode, even when the target leaves
that field unasserted. An alternate or unequal asserted writer value conflicts
exactly like any other explicitly asserted mismatch; an unasserted writer value
does not. A purported but uninterpretable value blocks before a completed
witness. No value can be deduplicated or ignored.

`observed_treatment` is derived only from completed target witnesses. It is
`included` when a scope-matched target assertion claims the operation and
sequence order needed to address the canonical edge and every field it actually
claims compares `equal`; canonical fields marked `unasserted` do not prevent
inclusion. It is `delegated` only for an unambiguous scope-matched delegation
assertion. It is `contradicted` only when a scope-matched assertion explicitly
claims at least one field whose comparison is `unequal`; absence never means
contradiction. It is `omitted` for an applicable transition only when
`claim_completeness` is `exact` or `complete-implied`, complete lossless target
occurrence/assertion accounting has closed, and the target contains neither a
scope-matched compatible operation/order assertion nor a valid delegation. It is
`not-applicable` only from resolved target scope. Consequently
`omitted_transition_ids` and `contradicted_transition_ids` are deterministic
projections of completed comparisons, never token-presence, defaulted-field, or
absent-field judgments. A membership-only token remains insufficient for
`included` because it asserts no sequence order.

Every member of `transition_comparisons` contains:

- `transition_id`
- `candidate_ids`
- `operation`
- `source_conditions`
- `predecessor_or_order`
- `destination_or_successor`
- `conditional`
- `owning_caller_or_domain`
- `effects`
- `readback_authority`
- `sole_writer`
- `executable_validator_paths`
- `readback_validator_paths`
- `readback_mode`
- `readback_enforcing_antecedents`
- `readback_authority_disposition`
- `detailed_command_paths`
- `caller_paths`
- `semantic_equivalence_witness_ids`
- `target_transition_occurrence_ids`
- `target_assertion_ids`
- `target_claimed_field_presence`
- `target_assertion_to_canonical_transition_witness_ids`
- `authority_state`, one of `aligned`, `conflict`, or `unresolved`
- `observed_treatment`, one of `included`, `delegated`, `omitted`,
  `contradicted`, or `not-applicable`
- `evidence_paths`

The comparison list is sorted by `transition_id`; candidate, occurrence,
assertion, and witness IDs are unique and sorted within each comparison, and
omitted and contradicted IDs are derived only from completed target comparisons
and sorted deterministically. A readback symbol or path
without its mode and enforcing antecedents is unresolved. The
`phase3-expected-manifest` mode may corroborate its exact historical/projection
antecedent but has `readback_authority_disposition: projection-only` and cannot
satisfy a live-acceptance obligation. Both direct-import modes have
`readback_authority_disposition: unauthorized-at-WRITE` for live acceptance,
even when a caller is named or their local comparison succeeds. Any comparison
candidate, executable, required mode, detailed-command, caller, material
authority transition field, authority equivalence witness, purported but
uninterpretable target field, explicitly unequal target field, target assertion
or witness, or comparison source-occurrence disagreement makes the affected
aggregate non-clean with `authority-conflict` or a cause-preserving adapter
obligation, preserves the disagreement and advisory reconciliation routing, and
prevents repair from that affected comparison. An absent target field with
`claimed_fields: false` is only `unasserted`, not such a disagreement. An
independent adjacent disagreement is reported with the completed wiring result
and does not erase it.

For the known recurrence, one aggregate member represents:

- `transition_id`: the structured identity whose `operation` is
  `phase0-reresolve` and whose remaining material fields are listed below
- `operation`: `phase0-reresolve`
- `source_conditions`: an eligible existing open pre-PR, pre-Phase-3 session
  with policy identities requiring re-resolution
- `predecessor_or_order`: after eligible Phase 0 contract/topology resolution
  and before `phase3-bind`
- `destination_or_successor`: caller-owned closed pre-PR readback, then later
  `phase3-bind` composition
- `conditional`: `true`
- `owning_caller_or_domain`: the implementation pipeline workflow/operator
  partition
- `sole_writer`: `tools/wu-session-migration/wu_session_migration.py`
- read-only evidence roles: `phase-0-contract-resolution`,
  `phase-0-ticket-snapshot`, `phase-0-topology-revalidation`,
  `resolved-ticket-contract`, and `resolved-ticket-operator`
- `effects`: manifest-only change, no active row, preserved cold-start
  disposition and phase history
- `readback_authority`: live-storage CLI readback authority
- `readback_mode`: `live-storage-cli`

At the point-in-time `Manifest storage` target in
`conventions/wu-session-lifecycle.md`, the source-ordered operation occurrences
claim operation and predecessor/order placement. They do not claim canonical
conditions, effects, owner, `sole_writer`, readback authority, or readback mode,
so those target presence values are `false` and their witness results are
`unasserted`; the exact authority values remain intact. Subject to all other
identity, source-closure, authority, and target-accounting gates, compatible
listed operations are `included`, while the absent scope-matched
`phase0-reresolve` operation/order assertion and absence of a valid delegation
derive `omitted`. This is a specification-level expected mapping, not executed
behavior evidence at `WRITE`.

An applicable claim with `claim_completeness` `exact` or `complete-implied` has
conditional-wiring drift when the
complete aggregate has a non-empty `omitted_transition_ids` or
`contradicted_transition_ids`. `included` and unambiguous `delegated` treatment
are aligned. `not-applicable` is used only for an individual comparison outside
the resolved claim scope, including a membership-only claim or explicitly named
lifecycle partition that does not own it. It cannot stand for an unexamined
transition. When required authority source closure, a candidate disposition,
corrective-capability record, source-occurrence/disposition equality,
candidate/comparison equality, equivalence witness, target
occurrence/assertion disposition, target claimed-field interpretation, target
assertion comparison, or exhaustive enumeration is unavailable, the
aggregate is `null` under the evidence-gap rules rather than inventing
`not-applicable` or an empty transition domain. `None` for this one exact target
claim requires `enumeration_complete: true`, complete occurrence accounting,
exact equality of admitted applicable and completed candidate IDs, valid
equivalence witnesses for every coalesced candidate, exact target occurrence/
disposition/assertion equality, exact admitted-target/completed-target equality,
and claimed-field comparison of every applicable authoritative transition while
retaining every canonical authority field in that claim's resolved domain. It
cannot establish repository-level,
all-claims, global-serialization, helper-authority, or runtime-safety
cleanliness.

## Non-fire cases

A future `None` outcome for one admitted `target_claim_identity` is permitted
only after canonical selector and common-identity admission, resolved
`claim_completeness`, `command_domain`, claim scope, and membership
applicability; complete target-presentation source coverage and candidate/raw-
command/command-disposition/raw-operation/interpreted equalities; the complete
authority source domain, blob, partition-span, source-coverage, raw-candidate,
accepted-capability, semantic-occurrence, bounded authority-constraint, and
corrective-capability equalities; aligned comparison authorities; complete per-
member detailed CLI support; and any applicable authority and target transition
occurrence, claimed-field assertion, equivalence-witness, and comparison-equality
gates.
The named unwanted behavior is absent from that exact claim in each of these
cases:

- Generic prose explicitly delegates exact membership or detailed sequencing
  to the applicable declaration, executable, detailed-command, and caller
  authorities and does not restate an exhaustive set.
- A list is clearly partial, illustrative, selected, or example-only and no
  surrounding context independently implies completeness.
- A resolved `non-runtime-only` anchor lists parser-authorized support commands
  such as `capture-evidence`, `dry-run`, `apply`, or
  `validate-pre-pr-readback`, or other identity-bound authorized non-operation
  commands, and makes no runtime-membership claim.
- A resolved mixed claim preserves every `authorized-support-command` and
  `authorized-non-operation` occurrence as valid content while its runtime side
  contains every applicable runtime member and no unsupported-operation extra.
  This is a non-fire only after the runtime comparison completes; support
  commands neither count as extras nor hide a missing runtime member.
- A membership-only claim differs only in ordering because
  `RUNTIME_OPERATIONS` is a set.
- A membership-only claim does not describe a sequence, so conditional edge
  placement is not applicable.
- The exact complete generic claim contains every applicable canonical
  declaration for its identity-bound domain, contains no exact-token extra,
  every target presentation candidate has exactly one disposition, every
  recognized command has one raw command occurrence and command disposition,
  and every runtime-member or unsupported-operation token child has exactly one
  raw operation occurrence, interpretation, and interpreted occurrence; every
  per-member support record has complete
  comparison source-occurrence and support-candidate equality plus aligned exact
  CLI entrypoint, parser/main reachability, closed operation/request validation,
  transaction completion, detailed command, and applicable caller evidence; the
  closed authority source and capability domain accounts for every effecting and
  corrective path; and common-identity authority and target occurrence
  inventories independently cover every transition source, prove all authority
  and target equalities, preserve every canonical condition, effect, owner,
  exact `sole_writer`, and readback field, and include or unambiguously delegate
  every applicable conditional transition through completed claimed-field
  witnesses. A terse target may leave authority-only fields unasserted when its
  compatible operation/order assertion covers the edge.
- A lifecycle-partitioned caller omits operations it does not own, including the
  resumer omitting pre-PR operations, because its
  `applicable_canonical_operations` contains only the operations assigned to
  that identity-bound lifecycle partition and both difference equations resolve
  against that subset.
- Historical text, fixture text, proposal text, or a negative example identifies
  an omission as unwanted behavior rather than presenting an active supported
  catalog claim.
- A claim explicitly limited to a selected ineligible cohort omits a transition
  that cannot apply to that cohort, or occurrence-only evidence records no event
  without making a repository-completeness claim and is explicitly
  membership-inapplicable.

False eligibility in one sampled WU does not excuse an omission from a
repository-global, named-domain, or ambiguously scoped complete generic claim.
Incomplete, identity-conflicted, selector-invalid, claim-completeness-
indeterminate, command-domain-indeterminate, membership-applicability-
indeterminate, target-presentation-ambiguous, command-disposition-ambiguous,
token-ambiguous, authority-source-domain-incomplete, authority-source-coverage-
mismatched, corrective-capability-accounting-incomplete, comparison-authority-
conflicted, target-transition-ambiguous, comparison-incomplete, or scope-
indeterminate evidence is not a non-fire case for the affected axis. An observed
independent adjacent helper, namespace, rollback, recovery, cleanup, or
corrective obligation does not erase an established absence or presence of
documentation drift, but it remains non-clean and requires a finding rather than
a bare `None`. When no such obligation is observed, `None` still says only that
the named documentation drift is absent under the completed comparison. Neither
functional CLI support nor a non-fire implies availability, latency, throughput,
bounded waiting or lock hold, global serialization, helper safety, scale, state-
size, or mature-state-cost properties.

No non-fire case and no `None` result says that another target occurrence, the
containing document, or the repository is clean. Multi-claim or repository
conclusions require the separate caller-owned discovery, inventory, exclusion,
fan-out, completeness-equality, and aggregation contract that is explicitly
outside this eval.

## Evidence-state contract

The common repository identity, injective target identity, declaration
authority, orthogonal completeness/domain classification and scope, membership
applicability, complete resolved catalog-bearing source span, target-presentation
source coverage, candidate/raw-command/command-disposition/raw-operation/
interpreted equalities, the closed authority source-domain/blob/partition-span/
coverage/raw-candidate/capability/occurrence equalities, complete comparison-
authority source-occurrence and authority-constraint accounting, and every per-
member detailed CLI support role are non-degradable for a membership
determination. Every
executable-validator, exclusive live CLI readback, detailed-command, and owning-
caller transition-authority partition; exact canonical conditions, effects,
owner, `sole_writer`, and readback fields; the complete authority candidate
inventory; injective transition identity and equivalence witnesses; the admitted-
applicable/completed-candidate equality; the lossless target-transition
occurrence/disposition/assertion equalities; and every claimed-field target
assertion-to-canonical witness are additionally non-degradable for a wiring
determination. Alternate namespace, helper, direct-import, rollback, recovery,
cleanup, and other corrective capability evidence is non-degradable for its own
independent obligation accounting but not a veto on a documentation comparison
whose asserted fields do not depend on it.

The normalized trace always carries `failure_obligations`, a deterministic list
of injective per-obligation records. Every record contains:

- `obligation_identity`, the structured fields `evidence_role`,
  `source_identity`, `normalized_cause`, and `occurrence`
- `evidence_role`
- `source_identity`
- `normalized_cause`
- `occurrence`
- `decision_relation`, `comparison-blocking` or `independent-adjacent`
- `original_error`, required for parser, adapter, and translated source errors
  and otherwise `null`
- `recovery_disposition`, one of `retry`, `repair`, `reconcile`, `escalate`, or
  `terminate`, as an advisory routing recommendation at `WRITE`
- `recovery_owner`, a recommended route rather than an authorized actor
- `ordered_next_actions`, advisory until later authority binding
- `terminal_condition`, a proposed closure observation rather than durable
  closure evidence

The obligation identity fields are never delimiter-concatenated. Occurrence
distinguishes repeated failures at the same role/source/cause without replacing
either record. `source_identity` is the structured admitted source identity or,
when admission itself failed, the exact attempted source locator and available
identity evidence; it is never omitted from the obligation identity. A
deterministic `failure_cause` list may summarize unique causes
derived from `failure_obligations`, but it cannot close, overwrite, own, or
supply a terminal condition for an obligation. For a pure resolved behavior
finding or `None`, `failure_obligations` and `failure_cause` are both empty
lists. A combined documentation-drift and adjacent-authority finding preserves
the established drift fields and carries every `independent-adjacent`
obligation; it never rewrites the drift axis as indeterminate. Every non-clean
state has at least one obligation; precedence may prevent only a dependent
comparison and cannot discard another observed obligation, even when both have
the same normalized cause.

At lifecycle `WRITE`, obligation routing is descriptive only. A fresh result
does not close a prior obligation, an owner label does not authorize an actor,
and a proposed terminal condition is not a durable closure record. Before
enforcing any retry, reselection, repair, reconciliation, escalation,
termination, or lifecycle action, later `ROLL_OUT` work must select and bind a
structured acting authority, authorization evidence, attempt identity, parent-
obligation lineage, and durable closure evidence.

`source_validity_authority_record` is reserved as that later `ROLL_OUT`
prerequisite for source-versus-adapter attribution. It contains the exact source
identity, source contract, authorized independent actor and execution context,
authorization evidence, independence witness from the failing adapter, observed
verdict, and evidence paths. No such authority or context is selected at
`WRITE`; the field is `null`. Until one is selected and bound, parser or adapter
failure uses `unresolved-source-or-adapter-attribution`, preserves the original
error, and remains advisably routed to the adapter/runner boundary. It cannot
assign source-owner repair or terminal source invalidity.

| `evidence_state` | Minimum evidence | Permitted future decision behavior |
|---|---|---|
| `complete` | One common identity and injective target identity are admitted; declaration and applicability resolve; the complete catalog-bearing source span and target-presentation coverage plus candidate/raw-command/command-disposition/raw-operation/interpreted equalities close; the authority source domain, blobs, partition spans, per-blob coverage, raw candidates, accepted capabilities, semantic occurrences, authority constraints, and corrective records satisfy every exact equality; per-member detailed CLI support and support-comparison equality resolve; exact completeness/domain classification and scope resolve; and every comparison-authority transition partition, exact canonical condition/effect/owner/`sole_writer`/readback field, authority equivalence witness, target occurrence/assertion disposition, claimed-field target-to-canonical witness, and authority/target comparison equality resolves. | A behavior finding is permitted when unwanted behavior is present. A behavior finding may carry fully accounted independent adjacent obligations without losing the drift outcome. `None` is permitted only for a fully evidenced non-fire for the exact target claim and does not claim adjacent runtime safety. |
| `degraded` | All repository/target identity, completeness/domain classification, applicability, presentation, command disposition, interpretation, closed authority source/capability accounting, comparison authority, occurrence, authority constraint, corrective record, detailed CLI support, scope, authority candidate/equivalence, target claimed-field assertion/witness, and equality sources needed for the selected decision resolve and agree, but optional trace/report, test, audit, or final-diff observation evidence is unavailable. | A directly established mismatch may produce a reduced-confidence finding with named `missing_evidence_roles`. `None` is permitted only when optional loss does not leave any documentation decision fact unresolved and no observed independent obligation requires a finding. Missing optional final-diff evidence alone does not erase a common-identity source-established mismatch. |
| `evidence-gap` | A required comparison role has cause `absent-at-identity`, `access-denied`, `transiently-unavailable`, `authority-source-domain-incomplete`, `authority-source-coverage-mismatch`, `authority-raw-candidate-ambiguous`, `accepted-capability-accounting-mismatch`, `authority-constraint-comparison-mismatch`, `corrective-capability-accounting-mismatch`, `target-presentation-candidate-ambiguous`, `target-presentation-accounting-mismatch`, `command-occurrence-accounting-mismatch`, `catalog-operation-token-ambiguous`, `target-transition-assertion-ambiguous`, `target-transition-comparison-mismatch`, `unresolved-source-or-adapter-attribution`, `unsupported-adapter`, or `parse-only-evidence`. Source-versus-adapter-specific labels such as `invalid-source-semantics`, `valid-source-unsupported-syntax`, `parser-inability`, `adapter-defect`, and `material-adapter-drift` are unavailable at `WRITE` and require a later bound `source_validity_authority_record`. | Emit a per-obligation cause-preserving `LOW` gap finding or runner result. Never assert the affected drift axis or use `None`, `NO_FINDING`, a PASS-like result, or generic `missing`. A completed independent drift axis remains reportable in the same finding. Dynamic or unsupported source shape remains a comparison-blocking adapter obligation, never a missing candidate. |
| `identity-conflict` | Identities have cause `mixed-source-identities`, `unbound-source-identity`, `unverifiable-source-identity`, or `caller-currentness-mismatch`. | Preserve expected and observed identities and the precise cause. Never compare into drift or use `None`; at `WRITE`, caller or identity-resolver labels are advisory routes only. |
| `selector-invalid` | The target selector has cause `noncanonical-selector-alias`, `non-unique-anchor-resolution`, or `invalid-target-selector`. | Preserve the attempted selector and every resolution, leave canonical target fields unavailable where admission failed, and never classify, compare, repair, or use `None`. Only a fresh canonical uniquely resolving selector at the selected identity can proceed. |
| `claim-classification-indeterminate` | The target is readable, identity-bound, and has clear scope, but wording cannot resolve `claim_completeness`. | Use `failure_cause: ambiguous-claim-completeness` and `claim_kind.claim_completeness: null`; preserve an independently resolved command domain or its own null state. Target-document and caller labels are advisory clarification routes. Drift and `None` remain prohibited until fresh identity-bound completeness classification resolves. |
| `command-domain-indeterminate` | The target is readable and identity-bound, but complete raw-command accounting, exact wording, parser registration, and detailed command authority cannot resolve runtime-only, non-runtime-only, or mixed. | Use `failure_cause: ambiguous-command-domain` and `claim_kind.command_domain: null`; preserve independently resolved completeness or its own null state and every command occurrence/disposition candidate. Membership drift, repair, and `None` remain prohibited until fresh identity-bound domain classification resolves. |
| `membership-applicability-indeterminate` | Completeness, command domain, and scope resolve, but identity-bound caller/lifecycle/cohort authority cannot determine whether runtime membership applies or which canonical subset applies. | Use `failure_cause: ambiguous-membership-applicability`, preserve every candidate domain and authority, leave `applicable_canonical_operations` and differences `null`, and never emit drift, repair, or `None`. |
| `authority-conflict` | A required declaration, detailed CLI, executable transition, exclusive CLI readback, detailed-command, applicable caller, exact canonical condition/effect/owner/`sole_writer`/readback field, or comparison equivalence fact disagrees or is unresolved. | Use a distinct `authority-disagreement` obligation with `decision_relation: comparison-blocking` per source occurrence, preserve all sides, `authority_conflicts`, and advisory `reconciliation_owner` routes, and never emit the dependent drift axis, repair from that axis, or `None` before identity-bound alignment. Another independently completed drift axis remains reportable. |
| `adjacent-authority-obligation` | A reachable alternate namespace, imported helper, direct readback mode, rollback, recovery, cleanup, corrective path, unrelated capability, global-serialization premise, or availability premise is unsafe, alternate, missing, or unresolved but is not a required fact for the detailed CLI documentation comparison. | Preserve its complete source occurrence and corrective capability record plus a distinct obligation with `decision_relation: independent-adjacent`, set `adjacent_authority_state: non-clean`, and report it alongside any completed drift or absence outcome. It cannot establish CLI support or live acceptance and cannot erase completed documentation drift. It prevents a bare `None` while observed, but generic-claim repair guidance may remain narrowly available and must disclaim runtime safety. |
| `comparison-incomplete` | Required comparison-authority partitions resolve, but command occurrence dispositions, authority or target source-occurrence dispositions, authority-constraint comparisons, corrective records, or claimed-field witnesses are incomplete; admitted support candidates differ from completed support candidates; admitted applicable transition candidates differ from completed transition candidates; admitted target assertions differ from completed target assertion comparisons; a target occurrence lacks its assertion; or a required authority/target equivalence witness is incomplete. | Use `transition-candidate-comparison-mismatch`, `authority-constraint-comparison-mismatch`, `target-presentation-accounting-mismatch`, `command-occurrence-accounting-mismatch`, `target-transition-comparison-mismatch`, or the cause-specific support/occurrence/corrective obligation, preserve all sets and incomplete comparisons, and never mark affected support, set `enumeration_complete`, emit affected drift, repair from that comparison, or use `None`. |
| `scope-indeterminate` | The exact target has active completeness wording but its repository, domain, cohort, or occurrence scope cannot be resolved. | Use `failure_cause: ambiguous-scope`, preserve context, and never let sampled eligibility choose scope or emit drift or `None`. |
| `lifecycle-prohibited` | Runnable evaluation is requested while lifecycle remains `WRITE`, or another selected lifecycle forbids the requested execution. | Use `failure_cause: lifecycle-prohibited-execution`; the specification recommends termination rather than execution or retry. A later lifecycle transition requires separately bound authority and is not granted here. |

The advisory recovery route is recorded independently for every matching
`failure_obligations` record; this table is not a cause-keyed result map and
does not authorize an actor or close an obligation at `WRITE`:

| `failure_cause` | Advisory route and proposed closure observation |
|---|---|
| `absent-at-identity` | Recommend stopping comparison at the immutable identity and routing later-identity source repair to the named source boundary. A fresh comparison or explicit absence finding is a proposed observation only, not durable closure. |
| `access-denied` | Recommend no unchanged-credential retry and route authorization repair to the caller/access boundary. Changed-access evidence or an explicit denied finding remains proposed evidence pending later authority and lineage binding. |
| `transiently-unavailable` | Recommend caller-bounded retry at a later lifecycle and preserve exhaustion as the same cause. A later resolved role does not close this occurrence without attempt and parent-obligation lineage. |
| `unresolved-source-or-adapter-attribution` | Route advisably to the adapter/runner boundary, preserve the exact source, source contract, and original error, and do not assign source-owner repair or terminal source invalidity while `source_validity_authority_record` is `null`. |
| `invalid-source-semantics` | Reserved for later `ROLL_OUT` use only after a bound independent `source_validity_authority_record` establishes the verdict. Even then, source-owner routing and closure require acting-authority, authorization, attempt-lineage, and durable-closure evidence. |
| `valid-source-unsupported-syntax` | When later independent source-validity evidence exists, recommend adapter-bound syntax support work while preserving source identity and the original error. No such authoritative attribution is available at `WRITE`. |
| `parser-inability` | Recommend adapter/runner-bound investigation with the original error preserved. Do not assign source repair; later retry or closure requires changed implementation evidence plus bound attempt lineage. |
| `unsupported-adapter` | Recommend stopping the attempt and routing adapter capability work to the adapter/runner boundary before a later identity-bound attempt. |
| `adapter-defect` | Recommend adapter-bound repair only when the defect is independently demonstrated; preserve the original error and do not treat a source edit or fresh result as closure. |
| `material-adapter-drift` | Recommend adapter/runner reconciliation with the current identity-bound source contract and comparability boundary. Source attribution remains unresolved unless the later source-validity prerequisite is satisfied. |
| `authority-source-domain-incomplete` | Recommend stopping support, enumeration, repair, and `None`; preserve the authorized registry, admitted/missing blob identities, and partition spans, then route closed-domain reconciliation to the caller and adapter boundaries. The mapper cannot shrink the registry to close the result. |
| `authority-source-coverage-mismatch` | Recommend preserving the complete blob, code-point coverage, raw candidate and boundary sets, and stopping semantic comparison until exact lossless coverage closes. Uncovered source is not evidence that no capability exists. |
| `authority-raw-candidate-ambiguous` | Recommend preserving the exact raw candidate, parent spans, original parser/adapter error, and potential read/write/judge/namespace/lock/reverse/recover/cleanup effects. Route adapter support without clean-excluding or inventing a semantic occurrence. |
| `accepted-capability-accounting-mismatch` | Recommend stopping the affected comparison and reconciling every accepted callable/entrypoint, mode, namespace selector, lock path, caller or null caller, writer/readback, rollback, recovery, cleanup, and corrective capability against its occurrence or obligation. |
| `authority-constraint-comparison-mismatch` | Recommend preserving the exact optimized-contract, manifest, executable, README, or caller occurrence, every authority field it explicitly asserts, and the corresponding complete authority value. Reconcile only asserted unequal fields; do not borrow unstated transition details or drop the partial authority occurrence. |
| `corrective-capability-accounting-mismatch` | Recommend preserving each corrective raw occurrence and filling its acting caller or null, authorization/lock antecedents, namespace aliases, attempt/journal identity, phase-dependent disposition, target/effects, and completion evidence. Do not replace the record with a bare `None` or let it close as clean. |
| `target-presentation-candidate-ambiguous` | Recommend preserving the complete source span, candidate, exact raw text and source span, grammar conflict, and coverage evidence; route grammar support to the adapter/runner boundary and do not recognize, discard, compare, or edit from the ambiguous candidate. |
| `target-presentation-accounting-mismatch` | Recommend stopping the affected membership comparison and reconciling source coverage plus candidate/raw-command/command-disposition/raw-operation/interpreted ID equalities at the mapper/validator boundary. Preserve complete parent commands, exact suffixes, operation-token children, unknown and misspelled syntax; do not seed recovery from canonical operation names. |
| `command-occurrence-accounting-mismatch` | Recommend preserving every raw command and assigning exactly one runtime-member, authorized-support-command, unsupported-operation, authorized-non-operation, or ambiguous disposition. Support commands stay valid; unsupported exact operation tokens stay extras; ambiguity remains blocking. |
| `catalog-operation-token-ambiguous` | Recommend preserving every raw occurrence and routing exact boundary/grammar interpretation to the adapter/runner boundary; do not normalize, compare, or edit the target claim from this state. |
| `target-transition-assertion-ambiguous` | Recommend preserving the target occurrence, exact raw conditions/order/destination/conditionality/effects/owner/`sole_writer`/readback wording, complete claimed-field presence, and null uninterpretable fields; route interpretation to the mapper/validator boundary without assigning `included`. An absent unasserted field remains distinct from purported but uninterpretable wording. |
| `target-transition-comparison-mismatch` | Recommend stopping the affected wiring comparison and reconciling occurrence/disposition/assertion and admitted-target/completed-target equalities plus claimed-field target-to-canonical witnesses. Do not derive treatment from operation-token presence, default absent target fields, or compare unasserted fields as contradictions. |
| `direct-live-readback-unauthorized` | Preserve the exact direct caller and mode as an independent adjacent obligation. Do not borrow `main()` antecedents or establish live acceptance; later direct-live integration requires a separately authorized contract. |
| `parse-only-evidence` | Recommend rejecting parse output as executable, identity, namespace, transaction, or live-readback authority and obtaining direct identity-bound source/antecedent evidence in a later authorized attempt. |
| `mixed-source-identities` | Recommend stopping comparison and routing common-identity reconciliation to the identity/caller boundary. A later admitted identity is not closure without bound lineage. |
| `unbound-source-identity` | Recommend stopping admission and routing commit/content binding to the evidence-producer and identity-resolver boundaries. |
| `unverifiable-source-identity` | Recommend stopping admission and routing authentication/source-integrity investigation to the identity/caller boundary. |
| `caller-currentness-mismatch` | Recommend stopping stale comparison; a later caller may select a fresh identity only under separately bound authority, and the mapper cannot silently reselect currentness. |
| `noncanonical-selector-alias` | Recommend stopping target admission and routing a canonical selector request to the caller boundary; a fresh selector does not erase this occurrence. |
| `non-unique-anchor-resolution` | Recommend stopping target admission and routing unique-claim clarification to the target-document/caller boundary; ordinals or resolver choice remain invalid. |
| `invalid-target-selector` | Recommend stopping target admission and routing canonical grammar, symlink, or escape repair to the caller boundary; normalization-in-place and alias acceptance remain prohibited. |
| `ambiguous-claim-completeness` | Recommend stopping completeness-dependent comparison and routing exact/complete-implied/delegated/partial wording clarification to the target-document/caller boundary. Preserve independently resolved command domain. A later classification requires bound attempt lineage before it can close the prior obligation. |
| `ambiguous-command-domain` | Recommend stopping membership comparison and routing runtime-only/non-runtime-only/mixed clarification plus command-disposition evidence to the target-document/caller and mapper boundaries. Preserve independently resolved completeness and every support/runtime/unsupported occurrence. |
| `ambiguous-membership-applicability` | Recommend stopping membership comparison and routing named caller/lifecycle/cohort authority clarification to the target-document and caller boundaries. Do not derive applicability from observed operations. |
| `authority-disagreement` | For `comparison-blocking`, recommend stopping only the dependent comparison and routing the shared boundary to every implicated executable, CLI-readback, detailed-command, caller, or writer-authority owner. For `independent-adjacent`, preserve and route the obligation separately without erasing completed documentation comparison or narrowly scoped repair guidance. Identity-bound resolution is not itself durable closure. |
| `transition-candidate-comparison-mismatch` | Recommend stopping wiring comparison and routing occurrence disposition, equivalence-witness, and completed-comparison work to the mapper/validator boundary. No document repair may be recommended from this state. |
| `ambiguous-scope` | Recommend stopping comparison and routing wording/scope clarification to the target-document/caller boundary. |
| `lifecycle-prohibited-execution` | Recommend termination without execution or retry. Later `ROLL_OUT` work requires separately selected and bound lifecycle authority; this specification grants none. |

Repository identity admission precedes target-selector admission. Complete
target-presentation inventory precedes command recognition and disposition;
orthogonal completeness/domain classification, scope, and applicability precede
membership comparison; independently closed authority source/blob/partition
coverage and raw-candidate/capability accounting precede semantic occurrences;
authority occurrence and candidate accounting precedes authority reconciliation;
corrective-capability accounting remains mandatory whether adjacent or directly
compared; and complete target-transition occurrence/assertion/claimed-field
accounting precedes target treatment. All steps retain failures already observed.
A comparison-blocking obligation prevents only its dependent decision, while an
independent adjacent obligation remains reportable beside any completed
membership or wiring decision. Authoritative source-validity attribution is
deferred until the later structured authority prerequisite is selected and bound.

While lifecycle remains `WRITE`, unavailable runnable code is not a clean
behavior outcome. A future execution request terminates with
`lifecycle-prohibited-execution` rather than treating specification presence as
`None`. Invalid finding shape or failed result validation is a per-obligation
runner/adapter result, not a behavior finding or clean result. A parser or
adapter failure against source uses `unresolved-source-or-adapter-attribution`
and is advisably routed to the runner/adapter boundary with the original error
preserved. At `WRITE`, no independent authorized source-validity context is
selected, so no failing adapter may translate its own failure into source blame,
source-owner repair, or terminal source invalidity.

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
- `target_claim_identity`
- `attempted_target_selector`
- `claim_completeness`
- `command_domain`
- `membership_applicability`
- `applicability_authority`
- `applicable_canonical_operations`
- `resolved_catalog_bearing_source_span`
- `target_presentation_source_coverage`
- `target_presentation_candidate_inventory`
- `target_presentation_candidate_dispositions`
- `raw_command_occurrences`
- `command_occurrence_dispositions`
- `authorized_support_commands`
- `authorized_non_operation_commands`
- `unsupported_operation_occurrences`
- `ambiguous_command_occurrences`
- `raw_catalog_operation_occurrences`
- `catalog_operation_interpretations`
- `interpreted_operation_occurrences`
- `authority_source_domain`
- `authority_source_blob_inventory`
- `authority_partition_span_inventory`
- `authority_source_coverage`
- `authority_raw_candidate_inventory`
- `authority_raw_candidate_dispositions`
- `accepted_capability_inventory`
- `accepted_capability_accounting`
- `authority_partition_inventory`
- `authority_source_occurrence_inventory`
- `authority_source_occurrence_dispositions`
- `authority_constraint_inventory`
- `corrective_capability_records`
- `operation_support`
- `target_transition_occurrence_inventory`
- `target_transition_occurrence_dispositions`
- `target_transition_source_coverage`
- `target_transition_assertions`
- `target_assertion_to_canonical_transition_witnesses`
- `claim_scope`
- `documentation_drift_outcome`
- `authority_state`
- `adjacent_authority_state`
- `adjacent_authority_obligations`
- `authority_conflicts`
- `reconciliation_owner`
- `source_validity_authority_record`
- `failure_obligations`
- `failure_cause`

For a resolved drift finding, `eval_id` is
`wu-session-runtime-operation-catalog-drift`, `authority_symbol` is
`RUNTIME_OPERATIONS`, `evaluated_repository_identity` is the admitted common
identity, `claim_kind` is the exact structured projection of the separate
completeness and command-domain classifications, full and applicable operation
collections, raw commands and per-command dispositions, raw exact-token
occurrences, complete target-presentation inventories and equalities, the closed
authority source/capability domain and all of its equalities, source-occurrence
dispositions, bounded authority constraints, corrective-capability records, and
`operation_support` are deterministic. The aggregate wiring treatment is
complete, claimed-field target-witnessed, and retains exact canonical conditions,
effects, owner,
`sole_writer`, and readback semantics.
`evidence_paths`
retains actual source and corroboration locators. The admitted structured
`target_claim_identity` is the sole target identity; `catalog_path` and
`catalog_anchor` retain their ticket-required canonical components. A resolved
drift finding records each axis in `documentation_drift_outcome`. A pure
behavior finding uses empty `failure_obligations` and `failure_cause` lists. A
combined finding preserves the same completed drift fields and carries every
independent adjacent obligation, with `adjacent_authority_state: non-clean`; an
adjacent obligation never changes the resolved drift outcome to unavailable.

For an evidence, identity, selector, completeness, command-domain,
applicability, presentation, command-disposition, token, authority-source,
corrective-capability, authority, target-assertion, comparison, scope, or
lifecycle gap finding, all fields remain
present. Unavailable scalar or record values are `null`, except that `claim_kind`
follows its stricter structured contract: an ambiguous classified dimension is
`null` while the other dimension retains its independently resolved value; both
dimensions use the non-semantic value `unavailable` when an earlier non-clean
state prevents classification. The top-level `claim_completeness` and
`command_domain` fields exactly equal their `claim_kind` members. Canonically
admitted `catalog_path` and `catalog_anchor` remain
present; either is `null` when its selector admission failed, while
`attempted_target_selector` preserves the exact supplied fields and resolution
evidence. `target_claim_identity` is present only after complete target
admission;
unavailable operation collections are `null`; a resolved membership-
inapplicable occurrence also uses `null` applicable/difference collections with
`membership_applicability: not-applicable` and an explicit reason;
available collections remain deterministic lists; and
`missing_evidence_roles` names every source of indeterminacy. Empty lists always
mean resolved empty sets, never unknown evidence. The selected
`evaluated_repository_identity` remains present when known, including in
identity, selector, classification, authority, comparison, or scope findings;
it is `null` only when no common identity was supplied. Conflicting observed
identities and authorities remain in `authority_conflicts` and
`evidence_paths`. `reconciliation_owner` is a deterministic advisory route when
multiple source boundaries are implicated; it is not authorization. At `WRITE`,
`source_validity_authority_record` is `null`. An absent acting caller, attempt,
journal identity, or completion fact in a corrective record is `null` only with
its exact cause-preserving obligation; the corrective record itself is never a
bare `null` after its raw occurrence is admitted. `failure_obligations` is non-
empty and each occurrence contains its own cause, `decision_relation`, advisory
disposition and owner, ordered next actions, and proposed terminal condition.
Presentation, command, authority, corrective, and transition records retain
exact raw text/span even when their interpreted fields are `null`. Target
assertions retain claimed-field presence so unasserted and uninterpretable remain
distinct. `failure_cause` is only its derived summary. No
generic `missing` cause, cause-keyed recovery map, collapsed repeated cause,
unauthorized retry, or fresh-result closure is valid.

Severity describes finding impact, not the ACR-403 risk-profile verdict:

- `MEDIUM`: established generic operation-catalog or conditional-wiring drift.
- `HIGH`: established drift that also instructs an unsafe alternate writer,
  unsupported runtime behavior, or invalid lifecycle action.
- `LOW`: a distinct identity, selector, completeness, command-domain,
  membership-applicability, presentation, command-disposition, token, authority-
  source/capability/corrective, target-assertion, comparison, scope, evidence-
  resolution, instrumentation, or adapter gap.

`confidence` reflects evidence completeness, directness, completeness/domain
classification certainty, and closure of source/command/occurrence equalities.
It must not conceal degraded evidence or a cause-specific gap.

## Suggested action

For established operation-catalog or conditional-wiring drift,
`suggested_action` directs the owning document to do one or both of these:

- Include only the `applicable_canonical_operations` derived for the exact
  identity-bound claim domain, spelled as exact parser tokens, after every
  target presentation candidate, raw command, command disposition, operation-
  token child, and interpretation has been accounted losslessly; after the
  independently closed authority source/capability domain, bounded authority
  constraints, and corrective records satisfy every equality; and after every
  canonical member's detailed CLI
  support has complete comparison source-occurrence and support-candidate
  accounting across declaration, exact `__main__.py`/parser/`main()` reachability,
  operation/request validation, successful transaction path, detailed command
  semantics, and applicable caller authority. In a mixed claim, preserve every
  authorized support and non-operation command exactly; add missing runtime
  members and remove only exact unsupported-operation extras. Include every
  applicable transition only after all comparison-authority and target
  occurrences are independently inventoried, authority and target admitted/
  completed equalities pass, every authority coalescence has a complete semantic-
  equivalence witness including exact conditions, effects, owner, `sole_writer`,
  and readback fields, and every target assertion has a claimed-field canonical-
  transition witness.
  An absent target field remains unasserted and need not be added merely to
  restate authority-owned detail.
- Narrow the generic wording or explicitly delegate exact membership and
  detailed transition semantics to the applicable declaration, executable,
  detailed-command, and caller authorities. Narrowing completeness must not
  reclassify or delete valid support commands and must not use support content to
  hide a runtime omission.

The action must preserve runtime behavior, the single writer, closed request
validation, caller eligibility, and lifecycle partitioning. It must not change
`RUNTIME_OPERATIONS`, add an alternate writer, weaken request closure, infer
membership from prose majority, invent runtime behavior, or repair a claim from
unresolved applicability, completeness/domain classification, target-
presentation or command accounting, token interpretation, authority source/
capability/corrective accounting, comparison-authority occurrence, purported but
uninterpretable target assertion, transition equivalence, or source/adapter
evidence on the affected axis. It must not turn an unasserted target field into a
contradiction, remove an authorized support command as an extra, broadly rewrite
command syntax, or seed target filtering from canonical operation names. It also
must not advertise an importable helper by
borrowing `main()`'s lock/recovery context, treat an override or alternate
namespace as globally serialized, or treat `expected_manifest` projection
validation or either direct-import mode as live readback. Supported-operation
inclusion means functional detailed CLI reachability only; the action may not add
or imply global serialization, namespace safety, helper authority, availability,
latency, throughput, bounded-wait, bounded-lock-hold, scale, state-size, or
mature-state-cost assurances.

For every non-clean gap, `suggested_action` follows each independent
`failure_obligations` record above. It preserves the advisory disposition and
recommended owner, ordered next actions, original parser/adapter error when
applicable, and proposed terminal condition for every occurrence without
claiming authorization or closure. At `WRITE`, target-document, caller, runtime,
namespace, lock, writer/readback, rollback, recovery, cleanup, corrective,
detailed-command, mapper, validator, adapter, and runner labels are routing
recommendations only. Source-versus-adapter attribution stays
`unresolved-source-or-adapter-attribution` at the adapter/runner boundary; no
source-owner repair or terminal source invalidity is suggested. None of these
non-clean states permits repair from a comparison it blocks, enforced retry/
reconciliation, or fresh-result closure based on assumptions. An independent
adjacent obligation does not prohibit a separately established narrow generic-
claim repair; the finding reports both actions independently and expressly says
that the documentation repair does not close or validate the adjacent runtime
obligation.

## Consumers and supported-surface boundary

Current consumers are ACR-403 reviewers, future ACR-398 reviewers after the
qualified handoff, and maintainers or agents reviewing complete-looking generic
tool and lifecycle claims through separate exact-target comparisons. The
supported runtime-operation surface for this eval is the detailed human CLI
entered through `tools/wu-session-migration/__main__.py`, `_parser()`, and top-
level `main()` with its exact selected state-root, lock-inode, journal namespace,
recovery, closed operation/request,
transaction-completion, detailed-command, applicable caller, and exclusive CLI
live-readback antecedents. `supported` means only functional reachability under
those named CLI antecedents; global serialization, alternate-namespace safety,
helper authority, availability, latency, throughput, wait/lock bounds, scale,
state-size, and mature-state cost are outside this eval's documentation repair.
Direct standalone WUs using
planning root `P` and feature direct/refactoring routes using `F/routes` are
request-topology cohorts behind that surface, not alternate invocation modes.
Importable helpers and direct readback calls remain outside the generic CLI
support and live-acceptance comparison even when a caller is named. Every mode
is still derived from the independently closed source/capability domain and
losslessly inventoried. An override, alternate namespace, unbound mode,
purported direct-live authority, or rollback/recovery/cleanup/corrective path
becomes a complete independent adjacent obligation unless it directly supplies a
compared field. No effecting mode can be clean-excluded, and every corrective
occurrence retains caller, authorization/lock, namespace/alias, attempt/journal,
phase disposition, target/effect, and completion evidence. This specification
does not repair or disable the adjacent environment override, authorize a direct-
live integration, or authorize a recovery or corrective action.

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
absence. Its source inspection admits the canonical repository/path/anchor
fields, unique target occurrence, source span, and claim content as one
structured `target_claim_identity`; binds declaration and exact detailed CLI
entrypoint/invocation-mode support to the same identity; derives
`applicable_canonical_operations` from caller/lifecycle/cohort authority; builds
the complete catalog-bearing source span and lossless target-presentation
candidate inventory before command recognition; preserves every complete raw
command, exact suffix, operation-token child, command disposition, and raw/
interpreted operation exactly; resolves orthogonal completeness and command-
domain classification; independently admits the fixed authority source blobs and
partition spans, proves complete raw source coverage, and inventories every raw
candidate, accepted capability, readback/direct-caller mode, environment or
other namespace selector, lock path, writer/readback path, executable transition,
detailed-command occurrence, owning-caller transition authority, rollback,
recovery, cleanup, and corrective occurrence before semantic occurrence or
candidate construction; builds every corrective-capability record; losslessly
inventories every target transition occurrence and structured assertion with
explicit claimed-field presence; and checks scope/applicability resolution, all
target and authority equalities, bounded authority-constraint comparisons,
support comparisons, injective transition identity with exact authority-side
conditions, effects, owner, `sole_writer`, and readback fields, authority
equivalence witnesses, claimed-field target assertion-to-canonical witnesses,
CLI-exclusive live readback, independent adjacent obligation preservation, and
per-obligation advisory routing.
Step 6c must reject a missing TI entry; any noncanonical, aliased, repeated, or
multiply resolving target selector; any missing transition-authority partition;
any ambiguous completeness, command domain, membership applicability, target
presentation candidate, command disposition, token interpretation, target
transition purported field, or exact authority writer field; any missing source-
domain blob or partition span, uncovered source text, unsupported/dynamic source
shape, clean exclusion of an accepted effecting capability, or missing/duplicate
raw-candidate, capability, source-occurrence, corrective-record, command, target,
or authority disposition; any incomplete authority-constraint, support,
authority transition, or target claimed-field transition comparison; any missing
authority or target equivalence witness; any rule that defaults an absent target
field or calls it a contradiction; any rule that gives a direct import live-
acceptance authority; any rule that treats a support command as a runtime extra
or lets it hide a runtime
omission; any rule that lets an independent alternate-namespace/helper/
corrective obligation erase documentation drift; any authoritative source/
adapter attribution at `WRITE`; or any mapping whose proposal source, eval path,
eval identity, or required evidence does not match this specification and the
approved proposal. The presence of a completely accounted adjacent runtime
obligation is not itself a specification rejection when it is separately
preserved with narrow claim-repair semantics and prevents bare `None`.

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
  per-exact-claim non-fire, degraded, repeated-cause per-obligation,
  evidence/identity/selector/completeness/command-domain/membership-applicability/
  target-presentation/command-disposition/token/authority-source-domain/source-
  coverage/raw-candidate/capability/authority-constraint/namespace/lock/
  occurrence/corrective-record/target-assertion/claimed-field/equivalence/
  comparison/scope gap, combined drift-plus-adjacent-obligation, source-or-
  adapter attribution, and lifecycle-prohibited fixtures. It must independently
  bind the accepted source blobs and
  partition spans, prove lossless raw source coverage, and inventory every raw
  candidate, accepted capability, entrypoint, invocation mode, environment or
  other namespace selector, lock path, readback mode/direct or null caller,
  writer/readback, rollback, recovery, cleanup, corrective, executable
  transition, detailed-command, and caller-partition occurrence before semantic
  occurrence or candidate construction. It must preserve every raw command,
  suffix, operation-token child, command disposition, and raw/interpreted
  operation; exercise the exact shorthand plus wrong-option, malformed operand,
  extra operand, unsupported-operation, support-command, and non-runtime inverse
  cases; derive orthogonal completeness/domain classifications and scoped
  applicable operation sets; prove all source, presentation, command, authority,
  corrective, support-candidate, authority-transition, and target-assertion
  equalities; retain every canonical transition field while comparing only
  target-claimed fields; validate exact `sole_writer` in authority equivalence;
  enforce top-level CLI exclusivity for live acceptance; preserve independent
  adjacent obligations without making them documentation-drift vetoes; and
  select a structured `source_validity_authority_record` before assigning source
  versus adapter blame. It must also select and bind acting authority,
  authorization evidence, attempt identity, parent-obligation lineage, and
  durable closure evidence before enforcing any retry, repair, reconciliation,
  termination, or lifecycle action; then resolve evidence, validate reports,
  observe advisory executions, review false positives/evidence drift, and name
  downstream wiring.
- `ENFORCE` additionally requires trusted findings, a named caller and
  hookpoint, severity policy, repair routing, fail-closed evidence behavior, and
  durable enforcement-readiness evidence.
- `MAINTAIN` tracks authority syntax, semantic claim anchors, evidence adapters,
  accepted authority source registry and partition spans, canonical target-
  selector uniqueness, target-presentation grammar and source coverage, exact
  shorthand and token grammar, completeness/domain classification, command
  dispositions, membership-applicability authority, namespace/lock/alias
  evidence, raw-candidate/capability/source-occurrence/authority-constraint/
  corrective-record and authority-transition candidate coverage, target-
  transition claimed-field
  assertion coverage, exact authority writer/condition/effect/owner/readback
  semantics, authority and target equivalence witnesses, CLI-exclusive live
  readback, finding comparability, classifier false positives, source-validity/
  adapter attribution, obligation lineage and closure, downstream currentness,
  and lifecycle regression when reliability no longer supports enforcement.

Global serialization, namespace safety, helper authority, availability, latency,
throughput, bounded wait or lock hold, scale, state-size, and mature-state cost
remain outside this eval's `support_state` and repair semantics. Measuring or
governing those dimensions requires separately authorized later lifecycle work;
their absence does not get silently converted into support evidence, a veto of
completed documentation drift, or generic claim repair here.

No eval detector language, parser library, fixture serialization, eval-runner
mode, report path, eval CLI, CI, scheduler, cron, scan cadence, hookpoint, or
enforcing caller is selected here. Rollback of state introduced by the exact
repository delta is deletion or reversion of this one Markdown specification;
that delta introduces no runtime, schema, data, session/index, or deployment
state. Repository rollback cannot reverse an external action. Direct-route
compliance, attestation, and any external or protected-state reconciliation are
Work Manager responsibilities outside this eval contract. This eval neither
requires route process-audit or remote-state proof nor claims that repository
evidence establishes external non-action.

## Merge-qualified ACR-398 handoff

Only after ACR-403 is verified merged may ACR-398 cite the merged specification
as inherited Step 6b structural-verification intent. ACR-398 retains its exact
two-file repair scope, `tools/README.md` and
`conventions/wu-session-lifecycle.md`, and retains direct point-in-time
authority-versus-final-claim and final-diff inspection. That inspection must use
one canonical repository identity, admit each exact target through the canonical
path/anchor and unique occurrence/content binding, treat selector,
completeness/domain classification, membership-applicability, target-
presentation/command accounting, token, declaration/detailed-CLI support,
authority source-domain/blob/span/coverage/raw-candidate/capability/occurrence
accounting, bounded authority-constraint comparisons, corrective-capability
records, target-transition claimed-field assertion inventory, exact authority
conditions, effects, owner, `sole_writer`, and readback fields, equivalence-
witness, and comparison-equality conflicts as non-
clean; derive the applicable canonical operation subset for each target;
preserve support commands while comparing runtime members in mixed claims;
independently inventory every named support, transition-authority, target-
presentation, target-transition, rollback, recovery, cleanup, and corrective
occurrence before recognition or candidates; and compare every admitted
applicable authority candidate against only the fields each target assertion
actually claims. Unasserted target fields are not defaults or contradictions;
purported but uninterpretable fields remain blocking. Independent namespace,
helper, direct-readback, rollback, recovery, cleanup, corrective-capability, and
global-serialization obligations remain visible beside an established
documentation result and do not erase it or permit bare `None`. ACR-398 owns any
target selection across its exact two-file scope; this eval supplies no claim-
discovery completeness and no repository aggregate. Functional CLI support in
the handoff carries no global-serialization, namespace-safety, helper-authority,
availability, or bounded-cost claim. The merged `WRITE` specification supplies
intent, not a detector result.

The handoff does not copy this eval into ACR-398's diff, execute it, establish a
clean result for any unselected claim or the repository, replace ACR-398's
direct inspection, change runtime membership or sequencing, or advance this
eval beyond `WRITE`. ACR-398 remains the owner of the generic claim repair and
its separately verified per-target outcome. Its mixed-claim repair must retain
authorized support commands, add missing runtime members or remove exact
unsupported-operation extras only when comparison completes, and never broaden
the bounded shorthand into generic rewriting.

## Anti-scope

This `WRITE` artifact does not define or authorize detector code, Python or Rust
implementation, fixtures, tests, pytest imports or assertions, a one-off
verifier, a resolver, a parser, a source/capability discovery adapter, an eval-
runner adapter, CLI/CI/scheduler/cron wiring, broad command rewriting, runtime
writer changes, serialization or namespace changes, helper adapters, direct-live
readback integration, rollback/recovery/cleanup/corrective execution or authority,
global-locking work, protected-state mechanisms or writes, ACR-398 edits, ticket
actions, estimate mutation, direct-route compliance attestation, external non-
action proof, or external reconciliation. Its deterministic source/target
grammars, closed-domain rules, and schemas are specification obligations, not
runnable parsers, fixtures, adapters, discovery mechanisms, or selected detector
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
- `workflows/index.json`
- `agents/wu-session-resumer.md`
- `contracts/operators/wu-session-resumer.yaml`
- `~/projects/ai/planning/acr-403-operation-catalog-eval/proposals/acr-403-ACR-403.md`
- `~/projects/ai/planning/acr-403-operation-catalog-eval/contracts/acr-403-wu-session-runtime-operation-catalog-drift.md`
