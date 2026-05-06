# Code Quality Convention

This convention defines code-shape rules for generated and reviewed code across the `~/ai/` ecosystem.

## Purpose

This is the canonical, language-neutral code-shape rule list for generated and reviewed code; downstream auditors enforce these rules in their own passes, and this convention does not itself run checks.

## Scope

These rules apply uniformly across Rust, TypeScript, Python, and any other project language. They apply to both human-authored and agent-authored code. They are review rules for ordinary PR review and for specialized auditor passes that inspect function shape, responsibility boundaries, duplicate handling, and cross-system coupling.

The convention is intentionally language-neutral. A project may have local style rules for naming, formatting, framework boundaries, or idioms, but those local rules do not replace the code-shape requirements here.

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

## Numerical thresholds

These are starting calibration points for downstream auditors A4 / A5 / A6 (NES-140 / NES-141 / NES-148). Those auditors may refine measurement details, but they should treat these thresholds as the initial shared baseline.

| Metric | LOW | MEDIUM | HIGH |
|---|---|---|---|
| `Nesting depth` | 0-1 | n/a | >= 2 |
| `Function categories per function` | 1 | n/a | >= 2 |
| `Cohesion by classifications touched` | 1 classification | n/a | >= 2 classifications |
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

- `~/ai/agents/function-classification-auditor.md` - A5 / NES-141 enforcement surface for the `Function categories per function` threshold and `multi-classifier function` findings; this is a forward pointer only and does not change this convention's categories, rule, failure modes, thresholds, or policy-only status.
- `~/ai/conventions/risk-profile.md` § Scoring axes - duplicate-system count, change-path entropy, and risk scoring mechanics.
- `~/ai/workflows/implementation-pipeline.md` § Step 2.5.4 and § Phase 3 - duplicate-systems inventory plus cascade/consolidate/accept handling.
- `~/ai/conventions/agent-questions-and-session-graph.md` § Pull-vs-Push Policy - terminology disambiguation only.
