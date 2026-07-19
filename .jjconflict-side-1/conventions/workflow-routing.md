# Workflow Routing

A project's `AGENTS.md` maps user cues to workflows.

This doc defines the routing rules for that table.

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
