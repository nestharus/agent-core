# Workflow Routing

A project's `AGENTS.md` maps user cues to workflows.

This doc defines the routing rules for that table.

## Shared delivery precedence

[`~/ai/AGENTS.md`](../AGENTS.md#mandatory-general-landable-change-lifecycle) owns the shared landable-change lifecycle: observe → interpret against purpose/environment → decide across choices → correction/solution search → observe consequences. This overrides conflicting default pipeline routes in manager/flavor operators, their sidecars and older feature/refactoring conventions. Those legacy delivery orchestrators require explicit selection; their gates never substitute for consumer-owned decisions, verification or external authority. Specialized operational triggers below still apply, but resulting protected changes return to the shared lifecycle.

Review observations are evidence, not recommendations or automatic fix mandates. The consumer considers all decisions and their interactions, accepted/no-action observations and unresolved consequential user questions. Only the latter prevent affected completion merely by remaining unresolved; preserve evidence and uncertainty in either case. Do not turn decision-making into specification generation. Initial observation of a protected change defaults to a CRW coverage episode under AGENTS.md step 1, with all nine CRW-defined families; use the CRW-owned episode interface, not a local family definition or scheduling protocol. Focused observations, explicit single-family assignments and reviewer children do not independently select full episodes. Missing required observation remains explicit, not silently waived or replaced by inline work. Consequence-driven observation remains consumer-owned, without automatic full-family scheduling after each correction or mandatory unchanged sweeps.

Process-only Markdown edits do not automatically select semantic product review or empirical evals; this does not exempt protected instruction/process changes from the initial coverage default. Changes to agent matching/recognition warrant agent-design review, including mixed edits. Follow the transition boundary in AGENTS.md: a proposed rule cannot waive the currently governing acceptance process for itself.

## Shape

Project `AGENTS.md` includes a cue-to-workflow routing table near
the top of its Workflows section.

Example:

```md
| Cue | Workflow |
|---|---|
| "Something is broken, errors in logs" | Bug Investigation (RCA-first) |
| "Research X" / "What are the options for Y" | Research |
| "New feature" / "enhancement" / "refactor" | Implementation & Bug-Fix |
| "Deploy..." / "update infra..." | Deployment |
```

The table matches common user requests to the workflow that handles
them.

Not every project needs every workflow.

## Precedence when cues overlap

If a user request matches multiple cues, pick the most specific
workflow.

Apply these precedence rules:

1. **Tier-3 cues first.**
   If the request would cause a user-visible change such as
   publishing, permission changes, or outbound messaging, route to
   the workflow that handles Tier-3 before any implementation
   routing.

2. **Bug cues before feature cues.**
   "Something is broken and we should add X" routes to Bug
   Investigation.
   Fix the break first.
   Run the feature as a separate pipeline afterward.

3. **Research before proposal.**
   "Should we use X, and can you build it" routes to Research, not
   Implementation.
   Evidence first.
   Then run a scoped implementation workflow if needed.

4. **Deployment before implementation.**
   "Let's refactor and deploy" routes to Deployment, not
   Implementation.
   Deployment carries its own pre-flight and risk gates.

## Fallback: ask the user

If the cue is still ambiguous after applying precedence, ask the
user which workflow they want.

One question is cheaper than running the wrong workflow.

Example:

"You said 'investigate and fix the logging regression' - I can run
Bug Investigation (RCA first, then a scoped fix) or Implementation
starting from a problem-framing phase. Which should I run?"

## Project-specific cues

The routing table in each project's `AGENTS.md` reflects that
project's domain.

Do not try to centralize every possible cue in `~/ai/`.

The table is project-specific by design.

What `~/ai/` centralizes:

- The precedence rule above.

- The fallback rule: ask the user if still ambiguous.

- The requirement that project `AGENTS.md` includes a routing table.

Everything else is per-project.
