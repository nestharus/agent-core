# Initiative 02 — Tests encode intent, driven by risk

**Status:** queued
**Depends on:** Initiative 01 (risk and value axes) reaching Phase 4 user acceptance
**Blocks:** —

## Problem (user framing, verbatim)

> We have some test workflows. We need to modify our implementation workflows to encode behavior through tests first to clarify and codify intent. We do not write tests after we write code. We encode our behavior into our tests so that it is clear and evident. We do not edit fixtures into our tests. Any fixtures must be externally applied to the test. The tests are the ground truth and cannot be modified. They are the expected behavior.
>
> We can test units, components, particular integrations, and end to end.
>
> Per the test workflows, tests have value and are driven by risk. Tests fit in nicely with the risk assessment work we expanded across. Yes, we have risks that something could go wrong. How do we verify? How do we discover? How do we further reduce those risks? We also need to recognize that if there is just way too much chaos it may be impossible for us to actually verify. There could be an edge case or some other system somewhere that we just aren't noticing. There are algorithms to attempt to improve discovery. We can use seed files to search through. So we can iteratively select seeds and search from them to discover the graph from various sources. That's very expensive, very slow, and still may not work.
>
> We codify tests and test necessity is driven by risk/value. It is a natural extension to the current phase you are working on and brings our test workflow methodologies into our implementation workflows and our PR review workflow.

## Firm constraints (treat as ground rules for any proposal)

1. **Tests first.** Behavior is encoded into tests before the code that satisfies them. No post-hoc test authoring.
2. **Tests are ground truth.** Once written, tests are not modified to match implementation.
3. **Fixtures are external.** Fixtures are applied to tests from outside; they are never edited into the test body.
4. **Test levels are explicit.** unit / component / particular-integration / end-to-end — each is a distinct level with its own role.
5. **Risk drives necessity.** A test exists because a risk exists. Tests without a risk behind them have no justification.
6. **Value comes from risk reduction.** A test's value is the fraction of the risk it verifiably reduces — ties directly to Initiative 01's value computation.
7. **Discovery is bounded.** Some risks cannot be verified: hidden systems, unknown edges, combinatorial chaos. The workflow must name this limit rather than pretend to cover it. Seed-driven graph search is acknowledged as expensive/slow/incomplete.

## Scope

**In scope:**
- `~/ai/workflows/implementation-pipeline.md` — integrate test-first encoding as an explicit phase (likely before implementation), with risk-driven scope selection.
- `~/ai/workflows/pr-review.md` — review gate must confirm: behavior was encoded as tests first, fixtures are external, test level matches the risk being reduced.
- Test-related operators (`test-writer`, `test-discovery`, `test-audit-gate`, `coverage-analyzer`, `coverage-auditor`, `red-phase-gate`, `green-phase-gate`) — audit their current role and update to enforce the firm constraints above.
- Possibly a new operator or convention for **fixture externalization** if no existing operator owns that rule.
- A discovery-limits convention — how to name the residual risk the workflow cannot verify, so it doesn't get silently treated as covered.

**Out of scope:**
- Any new test framework. Work with what the downstream projects already use.
- Rewriting existing tests in existing projects.

## Depends on (why blocked)

The value of a given test depends on the risk it reduces and the existing-state risk profile of the surface it covers — both vocabulary produced by Initiative 01. Starting this before 01's axes are accepted risks re-work. Wait for Initiative 01's Phase 4 acceptance.

## Expected research tracks (sketch — will be re-scoped when unblocked)

- **Test-workflow audit.** Map every current test operator against the 7 firm constraints. Identify violations and silent gaps.
- **Integration points.** Where in the implementation-pipeline and pr-review does the test-first phase insert; what does it consume from the risk-axes work; what does it hand off.
- **Discovery-limits study.** Minimal treatment of seed-driven graph discovery — what signal marks a risk as "unverifiable by finite test effort" so the workflow can name that residual honestly.

## Artifacts (empty until unblocked)

- `.build/A<NN>-tests-intent-*-prompt.md`
- `.build/A<NN>-tests-intent-*-findings.md`
- Proposal target: edits to the two workflow files, possibly new convention in `~/ai/conventions/`.

## Log

- **2026-04-23** — Initiative queued. Captured firm constraints from user. Blocked on Initiative 01.
