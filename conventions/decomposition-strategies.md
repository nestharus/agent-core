# Decomposition Strategies

## Purpose

This convention selects a remediation or decomposition strategy after an existing supported-surface, code-quality, review, or oscillation signal has already fired. It does not create new gate verdicts, relax LOW-only policy, narrow touched-file or touched-component ownership, or convert semantic blockers into user-approved residuals.

## Scope

This selector applies to implementation-pipeline Phase 4 supported-surface semantic non-LOW findings, Phase 4 code-quality semantic non-LOW findings, Phase 8 code-quality semantic non-LOW findings, and related split or decompose signals produced by existing review and code-quality authorities.

This selector excludes missing, malformed, unreadable, blank, stale, `NEEDS_INPUT:<absolute_artifact_path>`, and `BLOCKED:<reason>` evidence. Those are evidence repair or stop states owned by the calling workflow, not strategy-selection inputs.

## Declared roles

`validator`, `mapper`, `orchestration`, `formatter`

`validator` enforces anti-scope and separates semantic blockers from evidence-repair stop states. `mapper` owns the signal-to-strategy table and the mapping from current findings to supported strategies. `orchestration` sequences Phase 4 and Phase 8 application, rerun, narrowing, and `DECOMPOSED` handoff. `formatter` defines audit-history labels and cross-reference shape without adding a new audit-history schema.

## Intrinsic-surface declarations

```yaml
intrinsic_surface_declarations:
  - component: conventions/decomposition-strategies.md
    role: intrinsic-surface
    Domain: decomposition_strategy_selection
    Owns:
      - move_and_import_strategy
      - in_place_file_decomposition_strategy
      - in_place_helper_extraction_strategy
      - in_wu_head_on_remediation_strategy
      - follow_up_ticket_strategy
```

## Strategy definitions

### MOVE-and-import

- Signal: Coherent WU-authored or WU-modified logic sits in a wrong or overloaded file and can lift cleanly into a clean new file or module.
- Cost: Low to medium; create the new file or module, update imports and call sites, and delete the old location when no public compatibility contract requires it.
- Risk: Low when the moved logic has a clear boundary and rerun evidence can prove currentness; higher if call sites or public import contracts are ambiguous.
- Exclusions: Do not use when the logic does not lift cleanly, when the finding spans multiple unrelated domains, or when the move would create a compatibility shim forbidden by `~/ai/conventions/no-backwards-compatibility.md`.

### In-place file-decomposition

- Signal: A touched god-file or overloaded file has exactly one clear bolted-on domain that can be separated while preserving the current WU's behavior.
- Cost: High; split the file, update imports and call sites, and rerun the owning gates against the new surface.
- Risk: Medium to high because the change resembles behavior-preserving refactoring and can expose hidden coupling.
- Exclusions: Do not use when debt spans multiple unrelated domains, when no stable boundary exists, or when the required decomposition exceeds the current WU and should return `DECOMPOSED`.

### In-place helper extraction

- Signal: A touched function or inline mini-function carries multiple classifications but can be split into named helpers inside the same file.
- Cost: Low to medium; extract helpers, preserve call flow, and rerun the function-classification or code-quality gate.
- Risk: Low when each helper has one primary classification and no behavior changes are introduced.
- Exclusions: Do not use to redefine function-classification mechanics, to hide unrelated file-level debt, or to avoid whole-file/component ownership.

### In-WU head-on remediation

- Signal: The finding is WU-authored, WU-modified, or same-domain current-WU debt that belongs in the current WU rather than in a separate decomposition unit.
- Cost: Variable; revise the proposal, tests, code, or documentation directly and rerun the owning gate from current evidence.
- Risk: Low to medium when the remediation stays inside the WU's value surface; higher when it begins to pull unrelated domains into the current change.
- Exclusions: Do not use as a residual acceptance path, user-disposition path, or replacement for `DECOMPOSED` when the WU is too large.

### Follow-up ticket

- Signal: Mechanical caller or import touches expose unrelated-domain whole-file/component debt after the current WU has narrowed as far as it safely can.
- Cost: Low for the current WU and deferred to a separately scoped WU for the unrelated debt.
- Risk: Medium if the current WU advances without narrowing or rerun evidence; low only when the follow-up is paired with current-WU narrowing, rerun to LOW, or explicit `DECOMPOSED` handoff.
- Exclusions: Follow-up tickets are decomposition artifacts, not a pass-state. Do not use them for WU-authored debt, same-domain debt, residual approval, or artifact repair.

## Signal-to-strategy table

| Signal | Strategy | Required handling |
|---|---|---|
| Phase 4 supported-surface mixed-domain findings | In-WU head-on remediation for `in_domain_current_wu`; Follow-up ticket for `unrelated_caller_domain`; user question only for `needs_value_input` | Classify each current, well-formed semantic finding before generic revise; rerun all current proposal-risk gates after remediation or narrowing. |
| Phase 4 code-quality same-domain findings | In-WU head-on remediation | Revise the current WU and rerun the Phase 4 code-quality gate before join-manifest publication. |
| Single-function multi-classifier findings | In-place helper extraction | Split the function or inline mini-function into named helpers and rerun the relevant code-quality aggregate. |
| Coherent WU logic in a wrong/overloaded file | MOVE-and-import | Move the coherent logic to a clean location, update imports/call sites, delete the old location when allowed, and rerun. |
| Phase 8 code-quality god-file findings where WU code lifts cleanly | MOVE-and-import | Default Phase 8 strategy when the current diff can be lifted out of the touched god-file. |
| Phase 8 code-quality god-file findings with one bolted-on domain | In-place file-decomposition | Use only when exactly one separable domain is bolted on and the split is bounded. |
| Phase 8 code-quality multi-unrelated-domain debt | Follow-up ticket plus narrowing or `DECOMPOSED` | File decomposition work for unrelated domains and either narrow/rerun the current WU or return explicit `DECOMPOSED`. |
| Phase 8 FC HIGH in WU-authored test files | In-WU head-on remediation or In-place helper extraction | Fix WU-authored test debt directly and rerun Phase 8 code-quality before PR creation. |
| Genuine value/scope questions | `NEEDS_INPUT` via the caller's question artifact protocol | Use only when the blocker requires a user-owned value or scope judgment. |

## Preserved anti-scope

- NO god-file ownership carve-out
- NO new "named-deferred residual" verdict category
- Whole-file/component ownership stays
- LOW-only disposition stays
- Follow-up tickets are decomposition artifacts, not a pass-state
- `NEEDS_INPUT` is not used for artifact repair or residual approval under this selector

## Phase 4 application

Phase 4 strategy selection starts only after the caller has verified that the relevant supported-surface or code-quality artifact is present, readable, non-blank, current, well-formed, and semantic. Missing, malformed, unreadable, blank, stale, `NEEDS_INPUT`, and `BLOCKED` evidence stays on the existing evidence-repair or stop-state path.

For Phase 4 supported-surface semantic non-LOW findings, classify each finding as exactly one of `in_domain_current_wu`, `unrelated_caller_domain`, or `needs_value_input`. `in_domain_current_wu` selects In-WU head-on remediation, records `STRATEGY_PHASE4_SUPPORTED_SURFACE_INWU`, and requires a clean rerun of all current proposal-risk gates. `unrelated_caller_domain` selects Follow-up ticket, records `STRATEGY_PHASE4_SUPPORTED_SURFACE_FOLLOWUP`, and requires either current-WU narrowing plus rerun or an explicit `DECOMPOSED` handoff. `needs_value_input` writes the caller's question artifact and halts with `NEEDS_INPUT` because the decision is genuinely user-owned.

For Phase 4 code-quality semantic `MEDIUM` or `HIGH`, run any local bootstrap-exception sub-gate required by the caller before generic evidence repair. If the bootstrap exception does not ratify the non-LOW aggregate, select from In-WU head-on remediation, In-place helper extraction, MOVE-and-import, In-place file-decomposition, or Follow-up ticket according to the signal table. Record the selected label in audit history, apply the strategy, and rerun the Phase 4 code-quality gate before Phase 4 join-manifest publication. If narrowing cannot produce a current smaller WU surface, return `DECOMPOSED`.

## Phase 8 application

Phase 8 code-quality runs against the actual PR diff after the PR-review gates and before PR creation. The caller parses the aggregate for `LOW`, `MEDIUM`, `HIGH`, `NEEDS_INPUT:<absolute_artifact_path>`, or `BLOCKED:<reason>`, adds the required `code-quality` row to the Phase 8 join manifest, and applies this selector only to current, well-formed semantic `MEDIUM` or `HIGH`.

Default to MOVE-and-import when WU code lifts cleanly from a touched god-file and record `STRATEGY_PHASE8_CODE_QUALITY_MOVE_AND_IMPORT`. Select In-place file-decomposition only for one bolted-on domain and record `STRATEGY_PHASE8_CODE_QUALITY_FILE_DECOMPOSITION`. Select In-WU head-on remediation or In-place helper extraction for WU-authored code or test findings and record `STRATEGY_PHASE8_CODE_QUALITY_INWU`. Select Follow-up ticket for unrelated multi-domain touched-file debt and record `STRATEGY_PHASE8_CODE_QUALITY_FOLLOWUP`; the current WU must still narrow and rerun or return `DECOMPOSED`.

After any MOVE, file split, helper extraction, in-WU remediation, or follow-up-ticket narrowing decision, rerun Phase 8 code-quality so the join manifest and Process-tree audit #3 consume current evidence. Split, rerun, and currentness ordering must complete before PR creation.

## Audit-history label registry

Canonical strategy labels:

- `STRATEGY_PHASE4_SUPPORTED_SURFACE_INWU`
- `STRATEGY_PHASE4_SUPPORTED_SURFACE_FOLLOWUP`
- `STRATEGY_PHASE4_CODE_QUALITY_INWU`
- `STRATEGY_PHASE4_CODE_QUALITY_HELPER_EXTRACTION`
- `STRATEGY_PHASE4_CODE_QUALITY_MOVE_AND_IMPORT`
- `STRATEGY_PHASE8_CODE_QUALITY_MOVE_AND_IMPORT`
- `STRATEGY_PHASE8_CODE_QUALITY_FILE_DECOMPOSITION`
- `STRATEGY_PHASE8_CODE_QUALITY_INWU`
- `STRATEGY_PHASE8_CODE_QUALITY_FOLLOWUP`

These labels live inside existing audit-history fields such as `role_outputs`, `new_findings`, `decompose_trigger`, `verdict_or_determination`, and decision-register entries per `~/ai/conventions/audit-history.md`. They do NOT replace canonical `R<N>-F<NN>` finding IDs and do NOT add a new audit-history schema.

## Cross-references

- `~/ai/conventions/code-quality.md`
- `~/ai/workflows/code-quality.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/conventions/audit-history.md`
- `~/ai/conventions/risk-profile.md`
- `~/ai/conventions/evals.md`
- `~/ai/conventions/no-backwards-compatibility.md`
- `~/ai/conventions/refactoring-workflow.md`
