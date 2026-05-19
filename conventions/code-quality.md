# Code Quality Convention

This convention defines code-shape rules for generated and reviewed code across the `~/ai/` ecosystem.

## Purpose

This is the canonical, language-neutral code-shape rule list for generated and reviewed code; downstream auditors enforce these rules in their own passes, and this convention does not itself run checks.

## Scope

These rules apply uniformly across Rust, TypeScript, Python, and any other project language. They apply to both human-authored and agent-authored code. They are review rules for ordinary PR review and for specialized auditor passes that inspect function shape, responsibility boundaries, duplicate handling, and cross-system coupling.

`~/ai` markdown/operator/workflow/convention/routing/anchor structural guard requests are not code-quality checker authoring and are not pytest work. Structural-verification requests for those surfaces route to WRITE eval-spec authoring under `~/ai/conventions/evals.md`, with no narrower prohibition than that convention's binding enumeration: no `tools/<wu>-verify/<anything>.py`, no `tests/test_*.py`, no pytest imports or fixtures, and no pytest-shaped assertion code.

The convention is intentionally language-neutral. A project may have local style rules for naming, formatting, framework boundaries, or idioms, but those local rules do not replace the code-shape requirements here.

## Declared roles

`validator`, `mapper`

## Auditor Scope Boundary

For every A1 auditor, the WU's diff identifies the touched files or touched components that are in scope. Within those touched files/components, the auditor evaluates the whole file/component, not only hunk lines, changed functions, changed symbols, changed fields, changed Markdown blocks, or WU-authored declarations. Pre-existing findings inside touched files/components are current-WU findings and block the gate under the usual metric thresholds. Findings in untouched files/components remain out of scope except as context, residual evidence, or decomposition evidence.

Diffs, changed-function inventories, traces, proposals, risks, callers, callees, broader files, and adjacent declarations are boundary-resolution aids for determining the touched set and understanding evidence; they do not narrow the blocking target below the whole touched file/component. Residual rows are valid only for genuinely context-only evidence outside touched ownership, and use the existing residual schema (`id`, `severity`, `surface`, `anchor`, `evidence`, and `blocking-or-residual`) without raising the current gate severity.

ACR-249 changes judgment scope only. The existing A1 categories, numerical thresholds, LOW-only disposition policy, bootstrap exception, and ACR-156 oscillation handling remain authoritative in their existing sections.

## Auditor Set

The canonical A1 auditor inventory for composite fanout routing is:

This section is an inventory catalog of the four A1 auditor modules that make up the composite fanout set; the bullets below declare catalog membership for routing and do not make this convention a coupling target with four module dependencies.

- `agents/cohesion-auditor.md` - A6 cohesion.
- `agents/coupling-auditor.md` - A6 coupling.
- `agents/function-classification-auditor.md` - A5.
- `agents/push-pull-auditor.md` - A4.
- `agents/validation-integrity-auditor.md` - ACR-254 validation-integrity critic for applicable PR diff and RCA dossier contexts.
- `agents/proof-risk-auditor.md` - ACR-254 proof-risk critic for applicable proposal and RCA fix-decision contexts.

Workflows dispatch by reference to this list rather than by maintaining a separate canonical auditor inventory.

### Active validation-integrity / proof-risk layer

ACR-254 is enforced by active operator dispatch, not by declarative convention text. The enforcement operators are `agents/validation-integrity-auditor.md` and `agents/proof-risk-auditor.md`; workflow callers select them through `workflows/code-quality.md`, `workflows/implementation-pipeline.md`, and RCA critic wiring when their evidence contexts apply.

The acceptance criteria for these operators are the WRITE eval specs at `evals/validation-integrity-auditor/eval.md`, `evals/proof-risk-auditor/eval.md`, and the workflow-wiring coverage in `evals/acr-254-workflow-wiring/eval.md`. This convention names the active layer and its composition with the auditor set; the operators define how findings are detected, ratified, and reported.

The LOW-only disposition policy, touched-file ownership, and bootstrap exception below still govern pipeline-callable aggregate results. A non-LOW active-layer child verdict is preserved by aggregation and is not converted into passive advice by this convention.

## Function classification

### Single-classification rule

A function must classify cleanly as exactly one of the categories below. If it cannot, it is messy and must be split until each resulting function has one primary classification. The failure mode is a **multi-classifier function**.

Max function categories per function = 1.

### Categories

- `orchestration`: Does it sequence other already-named operations while keeping its own business logic thin?
- `filter`: Does it select, exclude, or partition existing items without changing their shape?
- `validator`: Does it accept input and either return the accepted input, return a transformed-valid version of it, or raise/report validation failure?
- `predicate`: Does it answer a boolean question about a value without returning the value itself or a transformed valid value?
- `mapper`: Does it transform one structured representation into another structured representation for internal use?
- `accessor`: Does it retrieve or expose data without changing its meaning?
- `formatter`: Does it transform a value into display, log, message, wire, or other presentation text/shape?
- `parser`: Does it turn unstructured or externally encoded input into structured data?

A useful split is usually visible when a proposed function title needs "and", when a body first validates and then formats, or when a helper both fetches data and decides what should happen next. The caller may orchestrate several classified functions, but each callee must still have one classification.

## Nesting depth

One level of nesting is opened by any control-flow construct: `if`, `loop`, `try`, `with`, `match`/`switch`, or the nearest equivalent in the project language. The body of that construct is one level deep. `match`/`switch` case arms count as the body of one level, not as additional levels per arm.

Max nesting depth = 1. A function with `if` plus `loop`, `if` plus `if`, `loop` plus `if`, or any other control-flow construct nested inside another construct violates this convention. The failure mode is a **deep-nest violator**.

Prefer early returns, guard clauses, and helper extraction when a second level would appear. The goal is not shorter code at any cost; the goal is a function whose control flow can be reviewed in one pass without holding multiple branch contexts at once.

```text
if not ready: return
process_ready_case()
```

## Inline functions

An inline function is a code block that exists only as a one-off mini-function inside another function. Common examples are a multi-line block under a comment header, a local closure that is immediately invoked, or an IIFE used to hide several steps inside an expression.

The rule is: extract the mini-function to a named function. Extraction forces the code through the single-classification rule and keeps the caller's nesting at 1. If the extracted function cannot be named with one classification, split it again.

The failure mode is an **inline-function carrier**. A comment header such as "validate request", "build output", or "parse options" is usually evidence that the block already wants to become a named function.

## Duplicate handling

The plain-language rule is: do not duplicate handling of the same responsibility across files, languages, targets, generated artifacts, or hand-written adapters. When the same responsibility appears in more than one place, consolidate it or push-pull-decouple the systems so the responsibility has one agreed owner and one agreed interface.

This convention cites the existing duplicate-system mechanics instead of redefining them:

- `~/ai/conventions/risk-profile.md` § Scoring axes owns `Duplicate-system count`, `Change-path entropy`, and risk scoring mechanics.
- `~/ai/workflows/implementation-pipeline.md` § Step 2.5.4 owns the duplicate-systems inventory artifact.
- `~/ai/workflows/implementation-pipeline.md` § Phase 3 owns the cascade-vs-consolidate-vs-accept-divergence decision.

The failure mode is a **duplicate-responsibility carrier**. The reviewer should name the duplicated responsibility in plain language, then route scoring and disposition through the existing risk-profile and implementation-pipeline references above.

## Push-vs-pull system coupling

This system-coupling rule is distinct from `~/ai/conventions/agent-questions-and-session-graph.md` § Pull-vs-Push Policy, which is about session-graph context transfer.

Pulling from a source you do not control is high-coupling. Either control the source, or push into a common interface that both sides agree on, then pull from that common interface.

The failure mode is an **uncontrolled-source coupler**. The important question is ownership: if a consumer must know another system's private storage shape, private file layout, unstable generated output, or incidental naming convention, the consumer is coupled to a source it does not control. A common interface can be a contract, schema, API boundary, generated artifact with a declared owner, or another explicit agreement that both sides treat as stable.

A canonical `~/ai` workflow, convention, or orchestrator Markdown file is
recognized as the **declared schema owner** for a generated artifact when a
dedicated `## Schema`, `## Format`, `## Output Paths`, or phase-specific
schema-declaration section in that file declares the parsed artifact shape
inline (field lists, required keys, parse semantics, terminal-state
vocabulary, or required-token sets). Push-pull's "separate schema-owner"
requirement is satisfied by the inline declaration; the pull site does
not score HIGH for parsing that artifact's declared shape. This narrows
"generated artifact with a declared owner" above; it does not weaken any
HIGH recipe below.

HIGH still fires for pulls of private file layouts no canonical doc
declares, pulls of incidental naming conventions or undeclared parsing
tokens, pulls of generated artifacts where no canonical `~/ai` doc owns
the schema, pulls of private endpoints or private storage shape, and the
undeclared portion of mixed pull sites that combine a declared
canonical-doc schema with adjacent undeclared layout (the auditor must
split such findings).

## Declared roles

Declared role set tokens must come from the A1 category vocabulary: `orchestration`, `filter`, `validator`, `predicate`, `mapper`, `accessor`, `formatter`, `parser`.

For cohesion scoring, compare the actual classification set to the declared role set before applying count-only fallback.

The default declared role set for `agents/*-orchestrator.md` is `orchestration`, `parser`.

A documented path default supplies declared roles only when the file has no `## Declared roles` section. File-local `## Declared roles` content overrides the documented path default for that file.

## Touched-file ownership

When a WU's diff touches a file, the WU owns that file's whole-file LOW verdict on all code-quality gates selected for that WU. Pre-existing findings on touched files are this WU's work, not separate tech-debt tickets and not residual rows. The same rule applies to touched components when a workflow invokes a component-level audit: the whole touched component is audit-owned.

If whole-file or whole-component cleanup is too large for one WU, the orchestrator decomposes the work before advance. Decomposition produces multiple smaller WUs, each responsible for fewer touched files/components; it does not predeclare a narrower finding set inside a file that the current WU has already touched.

When that whole-file/component cleanup is too large, `~/ai/conventions/decomposition-strategies.md` selects the remediation or decomposition shape. The selector operates after this ownership rule fires and does not predeclare a narrower in-file finding set.

## Continuous refactor

Each touch forces cleanup of the touched file's pre-existing code-quality defects. Technical debt gets paid down as features and fixes ship, not only through separate cleanup tickets. The codebase should compound toward `LOW` as ordinary WUs pass through the pipeline.

## Anti-scope discipline

Behavior-forbidding anti-scope is retained. Prompts and proposals may still forbid residual acceptance on non-LOW gates, precedent-citation as a residual basis, idle timeouts, sentinel-file polling, wall-clock kill heuristics, watcher shortcuts, test smuggling, unauthorized git mutations, and other unsafe execution behaviors.

Work-narrowing anti-scope is forbidden. Clauses such as "do not touch file X", "no scope expansion to concern Y", "only update the changed function", or "leave adjacent cleanup out of scope" cannot exclude required A1 cleanup inside touched files/components. If the required cleanup is too large, decompose the WU; do not pre-declare narrowness by anti-scope.

### Component declared roles (multi-file WU components)

When the cohesion auditor scores a multi-file WU component as a single component, per `~/ai/workflows/implementation-pipeline.md` Phase 6 per-component code-quality fanout, the component itself may have a declared role set living in the Phase 6a contract under a `## Component declared roles` heading. The cohesion auditor MUST read this section before falling back to per-file declared roles, path defaults, or count-only scoring when the touched component is the target of a component-level invocation.

When a component declared role set is present, the same subset-check semantic applies at the component level: LOW when the actual classifications in the touched component are a subset of the component declared role set; HIGH when the actual classifications exceed the component declared role set or include classifications outside it. The count-only fallback (LOW = exactly 1 classification; HIGH = 2 or more) applies only when no file-local, path-default, or component declared roles cover the touched classifications.

A component declared role set is the union of per-file roles the component legitimately covers as part of one coordinated change; it does not extend the A1 vocabulary, alter LOW/MEDIUM/HIGH semantics, or replace per-file declared roles where those exist for the files in the component.

## Declared-role examples

- LOW: `agents/implementation-pipeline-orchestrator.md` may touch `orchestration` and `parser` work because `agents/*-orchestrator.md` defaults to declared roles `orchestration`, `parser`.
- HIGH: an orchestrator surface with actual classifications outside the declared role set fails the declared-role-match metric.

## Adapter declarations

Adapter declarations are the explicit carrier for coupling-aware translation components. They do not extend the declared-role vocabulary above; `adapter` is a coupling role, not a function-classification token.

Carrier shape:

```yaml
adapter_declarations:
  - component: path/or/component-name
    role: adapter
    Translates:
      - stable-external-contract-surface
```

Each `adapter_declarations:` entry names `component`, requires `role: adapter`, and lists `Translates:` as stable external contract surfaces. `Translates:` must contain at least one contract surface; an empty list is malformed. A valid declaration may live inside a `## Adapter declarations` section of a `proposal_path` or `contract_path` artifact.

For declared adapter components, A1 coupling counts distinct external CONTRACTS in `Translates:`, not field references within those contracts. A component declared as translating two stable contracts bridges 2 contracts even if each contract has many fields.

The default adapter threshold is `N = 5` distinct contracts: LOW when the adapter bridges `<= N` named contracts and all external references are subordinate to the declared `Translates:` surfaces; HIGH when it bridges `> N` contracts or when the component reaches undeclared external contracts not subordinate to `Translates:`.

Malformed adapter declarations emit `BLOCKED:malformed-adapter-declaration:<component>:<reason>`. Valid-but-over-threshold adapters remain HIGH, and valid declarations with non-subordinate references remain HIGH. The same malformed-declaration disposition policy applies to intrinsic-surface declarations in the section below.

A reference is subordinate to a declared `Translates:` contract when it is a field, method, type, symbol, section, or documented operation directly defined by that contract surface. References to contracts not listed in `Translates:` are not subordinate.

Non-adapter coupling keeps the existing raw threshold: LOW `0-2`, MEDIUM `3-5`, HIGH `>= 6` distinct external symbols/modules. The adapter rule is an opt-in branch for explicitly declared adapter components only; it does not weaken the non-adapter coupling row in `## Numerical thresholds`.

Use adapter declarations for explicit translation components, such as an operator bridging stable contracts. Do not use them for components reaching many unrelated external surfaces dressed up as "adapter"; that is sprawl masquerading as adapter and remains HIGH.

Adapter status MUST be explicit. The component must be named under an `adapter_declarations:` carrier with `role: adapter`; auto-declared or inferred adapters are HIGH.

This convention is canonical for adapter declarations. `~/ai/agents/coupling-auditor.md` mirrors and applies this rule, and edits to the convention and auditor rule must land in lockstep.

## Intrinsic-surface declarations

Intrinsic-surface declarations are a sister mechanism to adapter declarations, distinct from adapter translation work. They are for components whose purpose is a predicate, filter, or selector over a coherent named data domain.

```yaml
intrinsic_surface_declarations:
  - component: conventions/code-quality.md
    role: intrinsic-surface
    Domain: code_quality_policy
    Owns:
      - touched_file_ownership_rule
      - low_only_disposition_rule
      - oscillation_decompose_rule
      - bootstrap_exception_rule
      - numerical_thresholds
```

Carrier shape:

```text
intrinsic_surface_declarations:
  - component: <path-or-component-name>
    role: intrinsic-surface
    Domain: <stable-domain-name>
    Owns:
      - <domain-owned-symbol-or-operation>
      - ...
```

Each `intrinsic_surface_declarations:` entry requires `component`, `role: intrinsic-surface`, exactly one `Domain:`, and a non-empty `Owns:` list. The carrier may live in `## Intrinsic-surface declarations` of `contract_path` when present, which is preferred, or in `## Intrinsic-surface declarations` of `proposal_path` when no contract carrier is supplied. Section names are exact; aliases do not apply.

For declared intrinsic-surface components, A1 coupling counts named `Domain:` entries, not raw field references within those domains. The default intrinsic-surface threshold is `N = 5` named domains: LOW when the declared component covers `<= N` named `Domain:` entries and all external references are subordinate to the declared `Owns:` set; HIGH when it covers `> N` domains or when external references reach symbols, operations, contracts, or modules outside the declared `Owns:` set.

Malformed intrinsic-surface declarations emit `BLOCKED:malformed-intrinsic-surface-declaration:<component>:<reason>`.

A reference is subordinate to a declared `Owns:` set when it is a field, method, type, symbol, section, or documented operation directly named by, or directly belonging to, that domain-owned symbol or operation set. References outside `Owns:` are not subordinate.

Non-declared coupling keeps the existing raw threshold: LOW `0-2`, MEDIUM `3-5`, HIGH `>= 6` distinct external symbols/modules. The intrinsic-surface rule is an opt-in branch for explicitly declared intrinsic-surface components only; it does not weaken the non-declared coupling row in `## Numerical thresholds`.

Intrinsic-surface status MUST be explicit in the resolved carrier. The component must be named under an `intrinsic_surface_declarations:` carrier with `role: intrinsic-surface`; auto-declaration or inference from names, paths, domain vocabulary, or raw-reference counts is forbidden.

This convention is canonical for intrinsic-surface declarations. `~/ai/agents/coupling-auditor.md` MUST match this section on carrier shape, role name, required fields, `N = 5` threshold, subordinate-reference rule, malformed disposition, and preserved raw thresholds. Edits to the convention and auditor rule must land in lockstep.

## Adapter-declaration examples

- LOW: `agents/prototype-validation-proof-bundle-adapter.md` is declared with `role: adapter` and `Translates:` containing `prototype-validation-proof-bundle` and `agents/prototype-pr-writer.md`. The component bridges 2 stable contracts, and all external references are subordinate to those surfaces.
- HIGH: `agents/release-and-ticket-sync.md` declares `role: adapter` but lists 6 unrelated contracts in `Translates:`, or reaches Slack, Jira, CI, release manifests, code-quality reports, and workflow internals without declaring those surfaces. The adapter declaration does not apply as LOW because the declaration exceeds `N = 5` or because undeclared external contracts are reached.

## Intrinsic-surface examples

- LOW: `agents/provider-quota-filter.md` is declared with `role: intrinsic-surface`, `Domain: quota_state`, and `Owns:` containing `provider_quotas`, `provider_quota_windows`, `exhausted_at`, `resets_at`, `filtered_indices`, and `clear_exhausted`. The component covers 1 domain and all external references are subordinate to the declared quota-state symbols and operations.
- HIGH: `agents/provider-quota-filter.md` declares `role: intrinsic-surface` for `Domain: quota_state` but also reads routing-log internals or writes billing records outside `Owns:`. The intrinsic-surface declaration does not apply as LOW because non-subordinate references are reached.


## Disposition policy

Only LOW passes pipeline-callable code-quality gates. `MEDIUM` and `HIGH` block advance, trigger remediation/revise, and require a rerun from current evidence. Neither severity is ever a residual, a `NEEDS_INPUT` user choice, or a "stable" allow-advance state for code-quality / risk-gate / prototype-risk verdicts.

For current, well-formed semantic `MEDIUM` or `HIGH` findings, `~/ai/conventions/decomposition-strategies.md` selects remediation, MOVE, split, or decomposition handling. Neither severity becomes a residual or user-disposition state through that selector.

This rule is the ACR-156 parent regression disposition and is enforced across all four canonical surfaces: `~/ai/agents/implementation-pipeline-orchestrator.md`, `~/ai/workflows/implementation-pipeline.md`, this convention, and `~/ai/workflows/code-quality.md`.

### Bootstrap exception

A Work Unit whose primary deliverable is itself a change to the code-quality metric, convention, verifier, or auditor surface may, narrowly, advance past a pipeline-callable code-quality gate that scores `MEDIUM` or `HIGH` on the intrinsic lockstep elements that the WU's own change is rewriting. The exception applies only when ALL of the following conditions are met:

1. The WU's primary deliverable fixes or extends the code-quality metric or rule currently scoring the WU non-LOW.
2. The non-LOW finding is on intrinsic lockstep elements required by the metric / convention / verifier / auditor change itself, not on collateral product code.
3. The post-merge codebase satisfies the new rule under the new metric — i.e. once the WU lands, the same audit on the new tree returns LOW.
4. The exception is declared in Phase 3 of `~/ai/workflows/implementation-pipeline.md` and ratified in the Phase 4 join manifest as a `bootstrap-exception` row marked `RATIFIED`, with a corresponding `### <ticket-id> — Bootstrap exception ratification` entry in `${worktree_path}/DECISIONS.md` citing this subsection.

This is the ONLY local carve-out from the LOW-only rule above. Ordinary residual acceptance, `NEEDS_INPUT` user choice, stable-allow-advance, or any manager-flavor / root / DECISIONS-only acceptance of a non-LOW pipeline-callable code-quality verdict remains forbidden under `~/ai/conventions/workflow-execution-violations.md` § `Named anti-pattern: Non-LOW gate residual acceptance`. Missing the Phase 3 declaration, missing the DECISIONS ratification entry, missing the citation to this subsection, or missing the Phase 4 join-manifest `bootstrap-exception` row marked `RATIFIED` falls through to the LOW-only blocking rule above.

### Oscillation signals WU-too-large

After two consecutive rounds that do not converge to `LOW`, the Work Unit is too large for the current grain and must decompose instead of attempting a third remediation pass. Decompose is autonomous, not `NEEDS_INPUT`-mediated; the caller records the oscillation evidence and opens the smaller WU path required by the owning workflow.

After this two-round non-convergence trigger fires, `~/ai/conventions/decomposition-strategies.md` names the smaller-WU shape and any follow-up-ticket handoff evidence. It does not make decompose `NEEDS_INPUT`-mediated.

## Numerical thresholds

These are starting calibration points for downstream auditors A4 / A5 / A6 (NES-140 / NES-141 / NES-148). Those auditors may refine measurement details, but they should treat these thresholds as the initial shared baseline.

| Metric | LOW | MEDIUM | HIGH |
|---|---|---|---|
| `Nesting depth` | 0-1 | n/a | >= 2 |
| `Function categories per function` | 1 | n/a | >= 2 |
| `Cohesion by classifications touched` | actual classifications are a subset of the declared role set (file-local, path default, or component-level declared roles in a Phase 6a contract); for components and files without any declared roles, exactly 1 classification | n/a | actual classifications exceed the declared role set or include classifications outside the declared role set; for components and files without any declared roles, 2 or more classifications |
| `Coupling by distinct external symbols/modules referenced` | 0-2 | 3-5 | >= 6 |

The first two rows are hard code-shape thresholds in this convention. The cohesion and coupling rows are review calibration: they identify where a function is likely doing too many kinds of work or depending on too many external surfaces.

## Failure modes

- `multi-classifier function`
- `deep-nest violator`
- `inline-function carrier`
- `duplicate-responsibility carrier`
- `uncontrolled-source coupler`

## What this convention does not enforce

This convention is policy, not enforcement. Auditors and future WUs enforce it. No linter, CI gate, pre-commit hook, workflow gate, language-specific style configuration, or runtime checker is established by this file.

It also does not replace project-local architecture rules. A project may have stricter framework, package, API, or naming rules; those rules layer on top of this convention when they do not conflict with it.

## Cross-references

- `~/ai/conventions/decomposition-strategies.md` - selector for remediation, MOVE, split, or decomposition after existing ownership, LOW-only, bootstrap, and oscillation signals fire.
- `~/ai/workflows/code-quality.md` - composite dispatch workflow for existing A1 auditors; this is an operational pointer only and does not change this convention's rule text, failure modes, numerical thresholds, or policy-only status.
- `~/ai/workflows/code-quality.md` § `Stop Conditions And Escalation` - separates standalone advisory use from pipeline-callable blocking use; pipeline-callable blocking enforces this disposition policy, including LOW-only passage and autonomous decomposition after oscillation.
- `~/ai/agents/function-classification-auditor.md` - A5 / NES-141 enforcement surface for the `Function categories per function` threshold and `multi-classifier function` findings; this is a forward pointer only and does not change this convention's categories, rule, failure modes, thresholds, or policy-only status.
- `~/ai/conventions/risk-profile.md` § Scoring axes - duplicate-system count, change-path entropy, and risk scoring mechanics.
- `~/ai/workflows/implementation-pipeline.md` § Step 2.5.4 and § Phase 3 - duplicate-systems inventory plus cascade/consolidate/accept handling.
- `~/ai/conventions/agent-questions-and-session-graph.md` § Pull-vs-Push Policy - terminology disambiguation only.
- `~/ai/agents/push-pull-auditor.md` - A4 / NES-140 enforcement surface for the `Push-vs-pull system coupling` rule and `uncontrolled-source coupler` findings; this is a forward pointer only and does not change this convention's rule text, failure modes, numerical thresholds, or policy-only status.
- `~/ai/conventions/workflow-execution-violations.md` § `Named anti-pattern: Non-LOW gate residual acceptance` - the forbidden baseline this convention's `### Bootstrap exception` is narrowly carved from; manager / root / DECISIONS-only acceptance of a non-LOW pipeline-callable code-quality verdict remains a blocking gate/termination violation outside the four-condition path declared and ratified per § `Bootstrap exception`.
