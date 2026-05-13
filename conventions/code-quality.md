# Code Quality Convention

This convention defines code-shape rules for generated and reviewed code across the `~/ai/` ecosystem.

## Purpose

This is the canonical, language-neutral code-shape rule list for generated and reviewed code; downstream auditors enforce these rules in their own passes, and this convention does not itself run checks.

## Scope

These rules apply uniformly across Rust, TypeScript, Python, and any other project language. They apply to both human-authored and agent-authored code. They are review rules for ordinary PR review and for specialized auditor passes that inspect function shape, responsibility boundaries, duplicate handling, and cross-system coupling.

The convention is intentionally language-neutral. A project may have local style rules for naming, formatting, framework boundaries, or idioms, but those local rules do not replace the code-shape requirements here.

## Declared roles

`validator`, `mapper`

## Auditor Scope Boundary

For every A1 auditor, the diff, or an equivalent WU-owned corpus when a literal diff is unavailable, is the judgment target; auditors may inspect other evidence only to decide whether a finding is owned by the current Work Unit.

The context set includes broader files, traces, proposals, risks, callers, and callees; these are context evidence that may inform the judgment but are not the target.

Residual records use this schema: `id`, `severity`, `surface`, `anchor`, `evidence`, and `blocking-or-residual`. A finding is blocking when it is introduced, worsened, or made gate-relevant by the current diff or WU-owned corpus; otherwise it is recorded as residual through the `blocking-or-residual` field and preserved without raising the current gate severity.

ACR-180 changes judgment scope only. The existing A1 categories, numerical thresholds, LOW-only disposition policy, and ACR-156 oscillation handling remain authoritative in their existing sections.

## Auditor Set

The canonical A1 auditor inventory for composite fanout routing is:

This section is an inventory catalog of the four A1 auditor modules that make up the composite fanout set; the bullets below declare catalog membership for routing and do not make this convention a coupling target with four module dependencies.

- `agents/cohesion-auditor.md` - A6 cohesion.
- `agents/coupling-auditor.md` - A6 coupling.
- `agents/function-classification-auditor.md` - A5.
- `agents/push-pull-auditor.md` - A4.

Workflows dispatch by reference to this list rather than by maintaining a separate canonical auditor inventory.

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

## Declared roles

Declared role set tokens must come from the A1 category vocabulary: `orchestration`, `filter`, `validator`, `predicate`, `mapper`, `accessor`, `formatter`, `parser`.

For cohesion scoring, compare the actual classification set to the declared role set before applying count-only fallback.

The default declared role set for `agents/*-orchestrator.md` is `orchestration`, `parser`.

A documented path default supplies declared roles only when the file has no `## Declared roles` section. File-local `## Declared roles` content overrides the documented path default for that file.

### Component declared roles (multi-file WU components)

When the cohesion auditor scores a multi-file WU component as a single component, per `~/ai/workflows/implementation-pipeline.md` Phase 6 per-component code-quality fanout, the component itself may have a declared role set living in the Phase 6a contract under a `## Component declared roles` heading. The cohesion auditor MUST read this section before falling back to per-file declared roles, path defaults, or count-only scoring when the diff or WU-owned corpus is the target of a component-level invocation.

When a component declared role set is present, the same subset-check semantic applies at the component level: LOW when the diff-owned classifications touched by the component are a subset of the component declared role set; HIGH when the diff-owned classifications exceed the component declared role set or include classifications outside it. The count-only fallback (LOW = exactly 1 classification; HIGH = 2 or more) applies only when no file-local, path-default, or component declared roles cover the touched classifications.

A component declared role set is the union of per-file roles the component legitimately covers as part of one coordinated change; it does not extend the A1 vocabulary, alter LOW/MEDIUM/HIGH semantics, or replace per-file declared roles where those exist for the files in the component.

## Declared-role examples

- LOW: `agents/implementation-pipeline-orchestrator.md` may touch `orchestration` and `parser` work because `agents/*-orchestrator.md` defaults to declared roles `orchestration`, `parser`.
- HIGH: an orchestrator surface with actual classifications outside the declared role set fails the declared-role-match metric.

## Disposition policy

Only LOW passes pipeline-callable code-quality gates. `MEDIUM` and `HIGH` block advance, trigger remediation/revise, and require a rerun from current evidence. Neither severity is ever a residual, a `NEEDS_INPUT` user choice, or a "stable" allow-advance state for code-quality / risk-gate / prototype-risk verdicts.

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

## Numerical thresholds

These are starting calibration points for downstream auditors A4 / A5 / A6 (NES-140 / NES-141 / NES-148). Those auditors may refine measurement details, but they should treat these thresholds as the initial shared baseline.

| Metric | LOW | MEDIUM | HIGH |
|---|---|---|---|
| `Nesting depth` | 0-1 | n/a | >= 2 |
| `Function categories per function` | 1 | n/a | >= 2 |
| `Cohesion by classifications touched` | actual classifications are a subset of the declared role set (file-local, path default, or component-level declared roles in a Phase 6a contract); for components and files without any declared roles, exactly 1 classification | n/a | actual classifications exceed the declared role set or include classifications outside the declared role set; for components and files without any declared roles, 2 or more classifications |
| `Coupling by distinct external symbols/modules referenced` | 0-2 | >= 3 | >= 6 |

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

- `~/ai/workflows/code-quality.md` - composite dispatch workflow for existing A1 auditors; this is an operational pointer only and does not change this convention's rule text, failure modes, numerical thresholds, or policy-only status.
- `~/ai/workflows/code-quality.md` § `Stop Conditions And Escalation` - separates standalone advisory use from pipeline-callable blocking use; pipeline-callable blocking enforces this disposition policy, including LOW-only passage and autonomous decomposition after oscillation.
- `~/ai/agents/function-classification-auditor.md` - A5 / NES-141 enforcement surface for the `Function categories per function` threshold and `multi-classifier function` findings; this is a forward pointer only and does not change this convention's categories, rule, failure modes, thresholds, or policy-only status.
- `~/ai/conventions/risk-profile.md` § Scoring axes - duplicate-system count, change-path entropy, and risk scoring mechanics.
- `~/ai/workflows/implementation-pipeline.md` § Step 2.5.4 and § Phase 3 - duplicate-systems inventory plus cascade/consolidate/accept handling.
- `~/ai/conventions/agent-questions-and-session-graph.md` § Pull-vs-Push Policy - terminology disambiguation only.
- `~/ai/agents/push-pull-auditor.md` - A4 / NES-140 enforcement surface for the `Push-vs-pull system coupling` rule and `uncontrolled-source coupler` findings; this is a forward pointer only and does not change this convention's rule text, failure modes, numerical thresholds, or policy-only status.
- `~/ai/conventions/workflow-execution-violations.md` § `Named anti-pattern: Non-LOW gate residual acceptance` - the forbidden baseline this convention's `### Bootstrap exception` is narrowly carved from; manager / root / DECISIONS-only acceptance of a non-LOW pipeline-callable code-quality verdict remains a blocking gate/termination violation outside the four-condition path declared and ratified per § `Bootstrap exception`.
