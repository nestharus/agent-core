---
id: acr-280-decomposition-strategy-selection
slug: acr-280-decomposition-strategy-selection
lifecycle: WRITE
lifecycle_state: WRITE
class: structural-verification
behavior_class: markdown-operator-workflow-convention-structural-verification
created: 2026-05-18
contract: /home/nes/ai/planning/acr-280-decomposition-strategies/contracts/acr-280-decomposition-strategies.md
proposal: /home/nes/ai/planning/acr-280-decomposition-strategies/proposals/acr-280-ACR-280.md
coverage_inventory: /home/nes/ai/planning/acr-280-decomposition-strategies/research/acr-280-coverage-inventory.md
hookpoints: /home/nes/ai/planning/acr-280-decomposition-strategies/research/acr-280-hookpoints.md
severity_when_fires: HIGH
evidence_source_kinds:
  - convention-markdown
  - operator-markdown
  - workflow-markdown
  - structural-anchor
suggested_action_class: revise-acr-280-product-markdown-before-step6c-acceptance
---

# ACR-280 Decomposition Strategy Selection Eval

## Purpose

This WRITE-state eval specification defines structural verification for ACR-280 decomposition-strategy selection. It tells Step 6c and any future detector what markdown/operator/convention anchors must exist after the product edits land.

The eval is not runnable code. It authorizes no verifier script, no test file, and no executable assertion implementation. Future runnable detector work, if any, must be handled by a later ticket under `~/ai/conventions/evals.md`.

## Scope

The structural surfaces under verification are:

- `/home/nes/ai/worktrees/acr-280-decomposition-strategies/conventions/decomposition-strategies.md`
- `/home/nes/ai/worktrees/acr-280-decomposition-strategies/conventions/code-quality.md`
- `/home/nes/ai/worktrees/acr-280-decomposition-strategies/conventions/design-patterns.md`
- `/home/nes/ai/worktrees/acr-280-decomposition-strategies/agents/implementation-pipeline-orchestrator.md`

The scenarios cover ACR-280 behaviors B1-B9 from `/home/nes/ai/planning/acr-280-decomposition-strategies/research/acr-280-coverage-inventory.md`.

## Evidence Rules

Evidence is the resolved markdown text of the exact file paths named in each scenario. A future detector may use repository-relative paths after resolving the worktree root, but findings must report the absolute evidence paths above.

Structural verification means heading presence, fenced YAML block presence, named token presence, and forbidden promotion text absence. The detector must distinguish anti-scope statements that forbid a behavior from text that promotes the forbidden behavior.

## Finding Contract

Every future finding produced from this spec must preserve the eval convention minimum fields:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

ACR-280 findings also carry:

- `scenario_id`: one of `ACR280-DSS-001` through `ACR280-DSS-009`.
- `intended_observation`: the required structural behavior that was missing or contradicted.
- `evidence_shape`: the exact path and structural assertion that failed.
- `accept_criteria`: the acceptance condition that was not met.
- `fail_criteria`: the failure condition that fired.
- `residual_handling`: whether any uncovered residual exists; for ACR-280 scenarios this is expected to be `none`.

## Scenarios

### ACR280-DSS-001: Strategy convention exists with required sections and strategy vocabulary

Scenario id: `ACR280-DSS-001`

Intended observation: `conventions/decomposition-strategies.md` exists and defines the canonical decomposition strategy selector without redefining ownership, disposition, or gate verdict systems.

Evidence shape: `/home/nes/ai/worktrees/acr-280-decomposition-strategies/conventions/decomposition-strategies.md` must contain these structural assertions:

- Heading existence, in order: `# Decomposition Strategies`, `## Purpose`, `## Scope`, `## Declared roles`, `## Intrinsic-surface declarations`, `## Strategy definitions`, `## Signal-to-strategy table`, `## Preserved anti-scope`, `## Phase 4 application`, `## Phase 8 application`, `## Audit-history label registry`, `## Cross-references`.
- YAML fenced-block presence containing `intrinsic_surface_declarations:`, `component: conventions/decomposition-strategies.md`, `role: intrinsic-surface`, `Domain: decomposition_strategy_selection`, and owned tokens `move_and_import_strategy`, `in_place_file_decomposition_strategy`, `in_place_helper_extraction_strategy`, `in_wu_head_on_remediation_strategy`, `follow_up_ticket_strategy`.
- Named strategy tokens present: `MOVE-and-import`, `In-place file-decomposition`, `In-place helper extraction`, `In-WU head-on remediation`, `Follow-up ticket`.
- Each strategy entry names the fixed fields `Signal`, `Cost`, `Risk`, and `Exclusions`.
- The signal-to-strategy table names the Phase 4 supported-surface, Phase 4 code-quality, single-function multi-classifier, wrong/overloaded file, Phase 8 god-file, one bolted-on domain, multi-unrelated-domain debt, WU-authored test debt, and genuine value/scope question rows.

Accept criteria: All required headings, YAML declaration tokens, five strategy names, four strategy fields, and table signal rows are present in the new convention file.

Fail criteria: The file is missing; any required heading is missing or materially reordered; the intrinsic-surface YAML block is absent or names the wrong component/domain; any of the five strategy names or fixed fields is absent; or the signal-to-strategy table omits a required signal row.

Residual handling: none. This scenario covers B1 directly.

### ACR280-DSS-002: Anti-scope is preserved across strategy, code-quality, and orchestrator text

Scenario id: `ACR280-DSS-002`

Intended observation: The strategy convention, code-quality pointers, and orchestrator text preserve the ACR-280 safety boundaries: no god-file ownership carve-out, no named-deferred residual promotion, whole-file/component ownership remains, LOW-only disposition remains, follow-up tickets are decomposition artifacts rather than pass states, and the ACR-280 additions do not introduce dispatch-output truncation, idle-timeout polling heuristics, retired Phase 7/CodeRabbit dispatch, or new orchestrator-owned ticket-status transitions.

Evidence shape: The following file paths must satisfy the structural assertions:

- `/home/nes/ai/worktrees/acr-280-decomposition-strategies/conventions/decomposition-strategies.md` contains a `## Preserved anti-scope` heading and the present anti-scope strings `NO god-file ownership carve-out`, `NO new "named-deferred residual" verdict category` or equivalent `no named-deferred residual`, `Whole-file/component ownership stays` or equivalent `Whole-file ownership stays`, `LOW-only disposition stays`, and `Follow-up tickets are decomposition artifacts`.
- `/home/nes/ai/worktrees/acr-280-decomposition-strategies/conventions/code-quality.md` contains pointer text near `## Touched-file ownership`, `## Disposition policy`, and `### Oscillation signals WU-too-large` that cites `~/ai/conventions/decomposition-strategies.md` while preserving whole-file/component ownership, LOW-only disposition, and autonomous decompose semantics.
- `/home/nes/ai/worktrees/acr-280-decomposition-strategies/agents/implementation-pipeline-orchestrator.md` contains Phase 4 and Phase 8 strategy-selector text that treats follow-up tickets as decomposition artifacts and requires rerun, narrowing, or `DECOMPOSED` handoff before advance.
- Across those files, forbidden promotion text is absent: no text introduces a god-file ownership carve-out, no text promotes `named-deferred residual` into a verdict class or allow-advance state, and no text promotes follow-up tickets to a pass state.
- In the ACR-280 new convention text and planned orchestrator additions, dispatch stdout truncation text is absent: no literal `| tail -N`, `| tail -n`, `| tail -1`, or equivalent `tail` pipeline appears in any orchestrator-dispatch line or convention guidance for ACR-280 dispatch handling.
- In the ACR-280 planned orchestrator dispatch additions, idle-timeout polling text is absent: no phrase `idle timeout`, `idle-timeout`, `idle timer`, `wall-clock kill`, `wall clock kill`, or equivalent polling-based wall-clock kill heuristic is introduced.
- In the ACR-280 planned orchestrator additions, retired Phase 7 dispatch text is absent: no new `Phase 7` dispatch line, no `CodeRabbit` dispatch language, and no `coderabbit-operator` reference is introduced.
- In the ACR-280 planned orchestrator additions, ticket-status transition text is absent: no new orchestrator-owned Linear or ticket status transition language such as `move ticket`, `transition ticket`, `set status`, `mark as In Progress`, `mark as Done`, or equivalent status-change instruction is introduced. The existing Phase 2.5 defer-marker exception remains unchanged and is not treated as a failure by this assertion.

Accept criteria: Required anti-scope strings are present where the contract requires them, no product text converts the forbidden concepts into an allowed verdict, residual, scope carve-out, or pass state, and grep-shaped absent-string checks over the touched files' Step 6c output find no ACR-280-introduced dispatch truncation, idle-timeout polling heuristic, retired Phase 7/CodeRabbit dispatch, or new orchestrator-owned ticket-status transition text.

Fail criteria: Any required anti-scope string is missing from the strategy convention; code-quality pointer text weakens ownership or LOW-only disposition; orchestrator text allows current-WU advance merely because a follow-up ticket exists; any inspected file promotes a god-file carve-out, named-deferred residual verdict class, or follow-up-ticket pass state; or the ACR-280 convention/orchestrator additions contain `| tail -N`, a `| tail -n`/`| tail -1` variant, idle-timeout polling language, new Phase 7 or CodeRabbit dispatch text, a `coderabbit-operator` reference, or new ticket-status transition language outside the unchanged Phase 2.5 defer-marker exception.

Residual handling: none. This scenario covers B2 directly.

### ACR280-DSS-003: Code-quality pointer additions and intrinsic-surface declaration exist without semantic rewrite

Scenario id: `ACR280-DSS-003`

Intended observation: `conventions/code-quality.md` adds only the ACR-280 pointer text and `code_quality_policy` intrinsic-surface declaration, while preserving existing severity, ownership, disposition, oscillation, and bootstrap-exception semantics.

Evidence shape: `/home/nes/ai/worktrees/acr-280-decomposition-strategies/conventions/code-quality.md` must contain these structural assertions:

- YAML fenced-block presence containing `intrinsic_surface_declarations:`, `component: conventions/code-quality.md`, `role: intrinsic-surface`, `Domain: code_quality_policy`, and owned tokens `touched_file_ownership_rule`, `low_only_disposition_rule`, `oscillation_decompose_rule`, `bootstrap_exception_rule`, `numerical_thresholds`.
- Pointer text after or inside `## Touched-file ownership` naming `~/ai/conventions/decomposition-strategies.md`, whole-file/component cleanup, remediation/decomposition shape, and no predeclared narrower in-file finding set.
- Pointer text in `## Disposition policy` naming semantic `MEDIUM`/`HIGH`, remediation, `MOVE`, split or decomposition, and neither severity becoming residual or user-disposition.
- Pointer text in `### Oscillation signals WU-too-large` naming two-round non-convergence, smaller-WU or follow-up-ticket handoff evidence, and decomposition not becoming `NEEDS_INPUT`-mediated.
- A `## Cross-references` bullet to `~/ai/conventions/decomposition-strategies.md`.

Accept criteria: All declaration and pointer tokens are present, and the surrounding text continues to describe LOW-only disposition, whole touched-file/component ownership, and the existing bootstrap-exception sub-rule as preserved authority.

Fail criteria: The intrinsic-surface declaration is absent or malformed; any required pointer region is absent; pointer text narrows ownership to hunks or changed functions; pointer text makes `MEDIUM` or `HIGH` a residual/user-disposition state; oscillation text makes autonomous decomposition user-mediated; or bootstrap exception text is rewritten into a second non-LOW allow-advance path.

Residual handling: none. This scenario covers B3 directly.

### ACR280-DSS-004: DP-013 citation entry and design-pattern intrinsic surface exist

Scenario id: `ACR280-DSS-004`

Intended observation: `conventions/design-patterns.md` declares itself as a citation index and adds DP-013 after DP-012 as a citation-shaped entry, not as an embedded procedure.

Evidence shape: `/home/nes/ai/worktrees/acr-280-decomposition-strategies/conventions/design-patterns.md` must contain these structural assertions:

- A `## Intrinsic-surface declarations` heading before `## Pattern Index`.
- YAML fenced-block presence containing `intrinsic_surface_declarations:`, `component: conventions/design-patterns.md`, `role: intrinsic-surface`, `Domain: design_pattern_citations`, and `dp_xxx_index_entries`.
- A heading `### DP-013 - Strategy selection before NEEDS_INPUT` after the DP-012 entry.
- DP-013 contains field-shaped text for short statement, canonical authority, exemplars, and auditor use.
- DP-013 canonical authority cites `~/ai/conventions/decomposition-strategies.md`; if `~/ai/conventions/no-operator-behavior-override-in-dispatch.md` exists in the product tree, DP-013 also cites it as dispatcher read-protocol authority.
- DP-013 exemplars name `~/ai/agents/implementation-pipeline-orchestrator.md` Phase 4 supported-surface, Phase 4 code-quality, and Phase 8 code-quality.
- DP-013 does not include the signal-to-strategy table or the five strategy definitions.

Accept criteria: The intrinsic-surface declaration exists before the pattern index; DP-013 exists after DP-012; DP-013 has citation-index fields and required citations/exemplars; and the entry remains citation-shaped.

Fail criteria: The declaration is absent or malformed; DP-013 is missing, not placed after DP-012, or lacks canonical authority/exemplar/auditor-use fields; DP-013 embeds the signal-to-strategy table or operational procedure; or the required optional dispatcher citation is omitted when its authority file exists.

Residual handling: none. This scenario covers B4 directly.

### ACR280-DSS-005: Phase 4 supported-surface non-LOW strategy branch exists before generic revise

Scenario id: `ACR280-DSS-005`

Intended observation: `agents/implementation-pipeline-orchestrator.md` classifies current, well-formed semantic Phase 4 supported-surface non-LOW findings before generic revise or user escalation.

Evidence shape: `/home/nes/ai/worktrees/acr-280-decomposition-strategies/agents/implementation-pipeline-orchestrator.md` must contain these structural assertions in the Phase 4 supported-surface/proposal-risk region:

- Token presence for `supported-surface`, `current`, `well-formed`, `semantic`, `MEDIUM`, and `HIGH`.
- Exact classification tokens `in_domain_current_wu`, `unrelated_caller_domain`, and `needs_value_input`.
- The `in_domain_current_wu` branch names in-WU head-on remediation, rerun of all current proposal-risk gates from clean state, and audit-history label `STRATEGY_PHASE4_SUPPORTED_SURFACE_INWU`.
- The `unrelated_caller_domain` branch names follow-up ticket decomposition, `${ticket_operator}` or ticket-operator routing, current-WU narrowing and rerun or explicit `DECOMPOSED`, and audit-history label `STRATEGY_PHASE4_SUPPORTED_SURFACE_FOLLOWUP`.
- The `needs_value_input` branch names `${scratch_dir}/questions/q-<uuidv4>.question.json` and `NEEDS_INPUT:<absolute_question_artifact_path>`.
- Invalidated-assumption and non-positive-value supported-surface termination remain orthogonal to strategy selection.

Accept criteria: The supported-surface branch exists before generic revise/evidence-repair handling and includes all three classifications, branch outcomes, rerun/decompose requirements, question artifact handling, and audit-history labels.

Fail criteria: Supported-surface `MEDIUM`/`HIGH` goes directly to generic revise or `NEEDS_INPUT`; any classification token is absent; unrelated caller-domain findings advance only because a ticket exists; the question artifact path is absent for genuine value questions; or the branch fails to record the canonical Phase 4 supported-surface labels.

Residual handling: none. This scenario covers B5 directly.

### ACR280-DSS-006: Phase 4 code-quality semantic non-LOW strategy branch preserves evidence repair and bootstrap exception

Scenario id: `ACR280-DSS-006`

Intended observation: `agents/implementation-pipeline-orchestrator.md` routes current, well-formed semantic Phase 4 code-quality `MEDIUM`/`HIGH` through the strategy table before generic evidence-repair `NEEDS_INPUT`, while missing/malformed evidence, stop states, and the bootstrap-exception sub-gate keep their existing roles.

Evidence shape: `/home/nes/ai/worktrees/acr-280-decomposition-strategies/agents/implementation-pipeline-orchestrator.md` must contain these structural assertions in the Phase 4 code-quality region:

- Token presence for `code-quality`, `aggregate`, `current`, `well-formed`, `semantic`, `MEDIUM`, `HIGH`, `LOW`, `NEEDS_INPUT`, and `BLOCKED`.
- Evidence-repair stop-state text names missing manifest, missing report or aggregate, unreadable, blank, malformed, stale, `NEEDS_INPUT`, and `BLOCKED` as non-strategy stop paths.
- Bootstrap-exception sub-gate text remains present, local to Phase 4, and not a second non-LOW allow-advance path.
- Strategy-selection options present: in-WU head-on remediation with label `STRATEGY_PHASE4_CODE_QUALITY_INWU`, in-place helper extraction with label `STRATEGY_PHASE4_CODE_QUALITY_HELPER_EXTRACTION`, `MOVE-and-import` with label `STRATEGY_PHASE4_CODE_QUALITY_MOVE_AND_IMPORT`, in-place file-decomposition, and follow-up-ticket decomposition.
- Rerun/currentness text requires rerun of the Phase 4 code-quality gate before Phase 4 join-manifest publication after any in-WU, helper, MOVE, or file-decomposition action.

Accept criteria: Semantic non-LOW code-quality findings are separated from evidence repair, bootstrap exception remains preserved, all strategy options and labels are present, and rerun/currentness is required before join-manifest publication.

Fail criteria: Current semantic `MEDIUM`/`HIGH` falls into generic evidence-repair `NEEDS_INPUT` without strategy selection; malformed/stale/stop-state evidence is treated as strategy-selectable semantic debt; bootstrap exception is altered or broadened; a required strategy option or label is absent; or rerun/currentness before the Phase 4 join manifest is missing.

Residual handling: none. This scenario covers B6 directly.

### ACR280-DSS-007: Phase 8 code-quality dispatch, aggregate, fifth manifest row, and selector exist

Scenario id: `ACR280-DSS-007`

Intended observation: `agents/implementation-pipeline-orchestrator.md` dispatches Phase 8 code-quality against the actual PR diff, parses the aggregate, writes a fifth `code-quality` join-manifest row, and applies the ACR-280 strategy selector before Process-tree audit #3 and PR creation.

Evidence shape: `/home/nes/ai/worktrees/acr-280-decomposition-strategies/agents/implementation-pipeline-orchestrator.md` must contain these structural assertions in the Phase 8 PR-review gate region:

- Dispatch text after the four PR-review gates and before `phase-8-join-manifest.json` names `${scratch_dir}/prompts/${wu_lower}-phase-8-code-quality.md`, `agents -m gpt-high -p ${worktree_path} -f ${prompt} 2>&1 | tee ${log}`, and actual PR diff code-quality review.
- Required canonical output tokens under `${planning_dir}/code-quality/${wu_lower}-phase-8/`: `dispatch-manifest.md`, `findings.json`, `findings.md`, child reports, and `aggregate-code-quality.md`.
- Aggregate parse tokens: `LOW`, `MEDIUM`, `HIGH`, `NEEDS_INPUT:<absolute_artifact_path>`, and `BLOCKED:<reason>`.
- Fifth join-manifest row text names `gate_name=code-quality`, `${planning_dir}/risk/phase-8-join-manifest.json`, identity/integrity fields matching PR-review rows, and `canonical_output_path=${planning_dir}/code-quality/${wu_lower}-phase-8/aggregate-code-quality.md`.
- Selector text maps Phase 8 semantic `MEDIUM`/`HIGH` to `MOVE-and-import` by default when WU code lifts cleanly from a touched god-file with label `STRATEGY_PHASE8_CODE_QUALITY_MOVE_AND_IMPORT`, in-place file-decomposition only for one bolted-on domain with label `STRATEGY_PHASE8_CODE_QUALITY_FILE_DECOMPOSITION`, in-WU remediation/helper extraction for WU-authored code/test findings with label `STRATEGY_PHASE8_CODE_QUALITY_INWU`, and follow-up-ticket decomposition for unrelated multi-domain touched-file debt with label `STRATEGY_PHASE8_CODE_QUALITY_FOLLOWUP`.
- Currentness text requires rerun after MOVE, file split, helper extraction, or in-WU remediation before Process-tree audit #3 and PR creation.
- Process-tree audit #3 expected-process composition consumes all five Phase 8 manifest rows including `code-quality`.

Accept criteria: Phase 8 includes the code-quality dispatch, canonical outputs, aggregate parse, fifth join-manifest row, four selector outcomes with labels, rerun/currentness, and Process-tree audit #3 five-row requirement.

Fail criteria: Phase 8 omits code-quality dispatch or runs it outside the required order; aggregate parse omits non-LOW or stop states; the fifth join row is missing or lacks the canonical output path; any Phase 8 strategy outcome or label is missing; rerun/currentness is absent; or Process-tree audit #3 still consumes only four rows.

Residual handling: none. This scenario covers B7 directly.

### ACR280-DSS-008: Declared roles, adapter declaration, audit-history labels, and finding-ID preservation exist

Scenario id: `ACR280-DSS-008`

Intended observation: `agents/implementation-pipeline-orchestrator.md` declares the mapper role and adapter contracts, and the strategy-label registry is present without replacing audit-history schema or canonical finding IDs.

Evidence shape: The following file paths must satisfy the structural assertions:

- `/home/nes/ai/worktrees/acr-280-decomposition-strategies/agents/implementation-pipeline-orchestrator.md` contains `## Declared roles` near the top with exactly `orchestration, parser, validator, mapper, formatter`, and the explanatory paragraph justifies `orchestration` for phase sequencing, `parser` for gate artifact or aggregate parsing, `validator` for evidence and disposition checks, `mapper` for supported-surface classification and signal-to-strategy selection, and `formatter` for audit-history record, join-manifest output, prompt, ticket, or PR body composition.
- `/home/nes/ai/worktrees/acr-280-decomposition-strategies/agents/implementation-pipeline-orchestrator.md` contains `## Adapter declarations` with a YAML fenced block containing `adapter_declarations:`, `component: agents/implementation-pipeline-orchestrator.md`, `role: adapter`, and `Translates:` entries `ticket-system-backend-surface`, `phase-gate-and-join-manifest-surface`, `agents-trace-output-schema`, `audit-history-and-decisions-surface`, and `process-tree-auditor-surface`.
- `/home/nes/ai/worktrees/acr-280-decomposition-strategies/conventions/decomposition-strategies.md` contains all nine canonical labels: `STRATEGY_PHASE4_SUPPORTED_SURFACE_INWU`, `STRATEGY_PHASE4_SUPPORTED_SURFACE_FOLLOWUP`, `STRATEGY_PHASE4_CODE_QUALITY_INWU`, `STRATEGY_PHASE4_CODE_QUALITY_HELPER_EXTRACTION`, `STRATEGY_PHASE4_CODE_QUALITY_MOVE_AND_IMPORT`, `STRATEGY_PHASE8_CODE_QUALITY_MOVE_AND_IMPORT`, `STRATEGY_PHASE8_CODE_QUALITY_FILE_DECOMPOSITION`, `STRATEGY_PHASE8_CODE_QUALITY_INWU`, and `STRATEGY_PHASE8_CODE_QUALITY_FOLLOWUP`.
- `/home/nes/ai/worktrees/acr-280-decomposition-strategies/agents/implementation-pipeline-orchestrator.md` references the relevant labels at the Phase 4 supported-surface, Phase 4 code-quality, and Phase 8 code-quality insertion points.
- `/home/nes/ai/worktrees/acr-280-decomposition-strategies/conventions/decomposition-strategies.md` states that labels live inside existing audit-history fields such as `role_outputs`, `new_findings`, `decompose_trigger`, `verdict_or_determination`, and decision-register entries; do not replace canonical `R<N>-F<NN>` finding IDs; and do not add a new audit-history schema.

Accept criteria: The declared-role set is exact, adapter declaration contains all five translated contracts, all nine labels appear in the label registry, orchestrator insertion points use the relevant labels, and schema/finding-ID preservation is explicit.

Fail criteria: `mapper` is missing or extra roles appear in the declared-role set; adapter declarations are absent or missing a translated contract; any canonical label is missing from the registry; orchestrator strategy branches do not use the labels; or product text introduces new required audit-history schema fields or replaces `R<N>-F<NN>` finding IDs with strategy labels.

Residual handling: none. This scenario covers B8 directly.

### ACR280-DSS-009: CLOUD-249 replay shapes route to strategies without non-value user escalation

Scenario id: `ACR280-DSS-009`

Intended observation: The orchestrator text recognizes the CLOUD-249 three-case replay sequence and maps each structural halt shape to an autonomous strategy, surfacing `NEEDS_INPUT` only for genuine `needs_value_input` cases.

Evidence shape: `/home/nes/ai/worktrees/acr-280-decomposition-strategies/agents/implementation-pipeline-orchestrator.md` must contain these structural assertions:

- Phase 4 supported-surface mixed-domain replay tokens: `supported-surface`, `MEDIUM`, `mixed-domain` or equivalent text that splits in-domain and unrelated-domain findings, `in_domain_current_wu`, `unrelated_caller_domain`, in-WU remediation, follow-up ticket decomposition, rerun or `DECOMPOSED`, and `needs_value_input` as the only user-question classification.
- Phase 8 code-quality first replay tokens: `code-quality`, `HIGH`, `god-file`, `WU code lifts cleanly`, `MOVE-and-import`, and `STRATEGY_PHASE8_CODE_QUALITY_MOVE_AND_IMPORT`.
- Phase 8 code-quality after-MOVE replay tokens: `after MOVE` or currentness-after-MOVE phrasing, unrelated multi-domain touched-file debt, follow-up tickets, `STRATEGY_PHASE8_CODE_QUALITY_FOLLOWUP`, WU-authored test debt, in-WU remediation, and `STRATEGY_PHASE8_CODE_QUALITY_INWU`.
- Anti-escalation text: no user escalation merely because an auditor cannot validate a mixed surface; `NEEDS_INPUT` is reserved for genuine `needs_value_input` or value/scope judgment.

Accept criteria: The Phase 4 mixed-domain shape, Phase 8 god-file MOVE shape, and Phase 8 after-MOVE follow-up plus WU-authored remediation shape are structurally present and route without user escalation except genuine value input.

Fail criteria: The orchestrator text lacks one of the three replay shapes; a replay shape routes directly to generic user escalation; `NEEDS_INPUT` is allowed for auditor uncertainty or residual approval; or follow-up tickets are treated as a pass state instead of decomposition artifacts requiring rerun, narrowing, or `DECOMPOSED`.

Residual handling: none. This scenario covers B9 directly.

## Residuals

No structural coverage residual is expected for ACR-280. Scenarios `ACR280-DSS-001` through `ACR280-DSS-009` cover behaviors B1-B9 directly. Runnable detector implementation, fixtures, CLI integration, CI wiring, and ticket-backend automation are outside WRITE-state eval-spec authoring and are not test residuals for this WU.

## Forbidden Outputs

This WRITE-state structural-verification route must not author `tools/<wu>-verify/<anything>.py`, `tests/test_*.py`, pytest imports, pytest fixtures, or pytest-shaped assertion code.
