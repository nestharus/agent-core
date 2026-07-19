# Pattern: Global Constraints

A **global constraints** section is a short numbered list of
non-negotiables at the project level. Other workflows and decisions bend
around them. They exist when the project has rules that would otherwise
be misread as mere preferences.

## When to include one

- The project has cross-cutting constraints that affect every workflow:
  hosting choice, target scale, data-shape invariants, audience type, or
  regulatory limits.
- A new contributor or agent would otherwise have to infer those rules
  from scattered mentions.

If the project has no such constraints, do not add the section. An
empty list is worse than no list.

## Placement

- Put it near the bottom of `AGENTS.md`.
- Title it `## Global Constraints`.
- Keep it short enough that each item reads as load-bearing.

## Shape

A short numbered list. Each entry should contain:

- **Rule** — one sentence stating the constraint.
- **Justification** — at most one short clause when the reason is not
  obvious.

Example (infrastructure / scale / stack):

````md
## Global Constraints

1. All work in worktrees; `main` checkout stays clean.
2. All PRs open in draft mode; promotion to ready-for-review is a human decision.
3. Hosting: Railway + Supabase. No AWS, no GCP. (Chose for solo-operator ops budget.)
4. Target scale: 10 users MVP. Do not over-engineer for 10k. (Premature scale adds review cost without value at this stage.)
5. No required env vars the user has to set; all config is derived or defaulted.
````

Example (domain-first framing):

````md
## Global Constraints

1. Motion is data. Every frame is evidence of the artifact's intended behavior.
2. No super-agents. (See `~/ai/models/roles.md`.)
3. No compatibility shims. (See `~/ai/conventions/no-backwards-compatibility.md`.)
4. Per-medium additive risk. Each medium adds its own risk class; do not treat them uniformly.
5. Reduced-motion rule applies to any output that could trigger vestibular or photosensitivity issues.
````

## Rules

- Each constraint is a one-line rule plus at most one short clause of
  justification.
- Keep the list project-specific. Do not copy another project's entries
  wholesale.
- Treat the section as stable. If it changes every PR, those items are
  preferences, not global constraints.
- Keep the list short; more than 6-8 entries usually means some are not
  truly load-bearing.

## What belongs here

- Rules that override local convenience.
- Constraints that multiple workflows must respect.
- Domain framing that changes how downstream decisions are made.

## Anti-patterns

- Aspirational goals dressed up as constraints.
- Implementation details that belong in a convention doc.
- Long justifications that should be their own section.
- Boilerplate lists copied across unrelated projects.

## Exemplars

- `/home/nes/work/AGENTS.md` — infrastructure + scale + stack
  constraints.
- `/home/nes/projects/videos/AGENTS.md` — domain-first constraints
  (`Motion is data`) that drive downstream decisions.

The project file owns the real list. This pattern doc only explains when
the section is worth adding and what shape it should take.
