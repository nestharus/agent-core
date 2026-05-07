# Model Roles

Central rule for which model to reach for.
Workflow docs in `~/ai/workflows/` reference this file.
Do not restate the matrix there.

## The mental model

> GPT proposes "these are what solve these problems."
>
> Opus states "do they now? I'll be the judge of that."

- **GPT** (`gpt-high`): proposer, builder, auditor. Works with facts, checklists, and presence checks.
- **Opus** (`claude-opus`): judge. Assesses whether a proposed solution serves its stated purpose, whether the direction is right, whether claims match reality.
- **Opus never synthesizes.**
- Synthesis is construction, not judgement.

## Matrix

| Model | Role | Use for |
|---|---|---|
| `gpt-high` | **Default.** Proposer/builder/auditor. | RCA, research, synthesis, proposals, hookpoint analysis, implementation, test writing, audit risk, coverage analysis, behavior investigation, CodeRabbit fixes, commit hygiene, test-audit gate, ticket generation. Use it for anything that gathers evidence, enumerates cases, builds artifacts, or checks presence against a checklist. |
| `gpt-xhigh` | Reserve for **very large** problems only. Not the default coordinator. | Multi-file proposals spanning subsystems; research that needs deep reasoning across many sources before delegation; rare strategic synthesis where reasoning depth, not judgement, is the bottleneck. |
| `claude-opus` | Judge. Intent / alignment / purpose-fit only. | Scope risk, shortcut risk, alignment gates, multi-concern PR review, justification PR review, adversarial writing reviews, and "does this still serve the stated purpose?" checks. |
| `claude-sonnet` | Light checks, summaries, fast passes. | Quick sanity checks, diff summaries, formatting work. |

## Phase-by-phase assignment (implementation pipeline)

This table is the authoritative source for pipeline phase ownership.
`~/ai/workflows/implementation-pipeline.md` cites this section.

| Phase | Model | Why |
|---|---|---|
| RCA (bug fix) | `gpt-high` | Evidence gathering |
| Problem research | `gpt-high` | Facts, citations |
| Synthesis (integrate findings) | `gpt-high` | Construction, not judgement |
| Proposal | `gpt-high` | Propose |
| Audit risk | `gpt-high` | Presence/checklist: validations, tests, migrations, contracts |
| Scope risk | `claude-opus` | Intent: does this stay within the stated scope? |
| Shortcut risk | `claude-opus` | Intent: do the shortcuts compromise the underlying purpose? |
| Hookpoint research | `gpt-high` | Analysis |
| Implementation | `gpt-high` | Build |
| Test writing (separate agent) | `gpt-high` | Enumerate cases from contract |
| CodeRabbit loop | tool | Automated |
| Test-audit gate | `gpt-high` | Checklist against stated acceptance criteria |
| Commit-hygiene check | `gpt-high` | Checklist against small-testable-commit rules |
| Multi-concern PR review | `claude-opus` | Intent: does this PR belong together? |
| Justification PR review | `claude-opus` | Intent: does every change justify its presence? |
| Alignment gate (skill/ai-workflow) | `claude-opus` | Direction check: is this going the right way? |

## Coordinator / researcher split for large tasks

Use a split when the task needs both broad reasoning and detailed research.

- **Coordinator**: `gpt-high` by default.
- **Coordinator**: `gpt-xhigh` only when the problem is very large.
- **Researcher**: `gpt-high`.

Coordinator responsibilities:

- Identify the questions that need answers.
- Write research prompts.
- Launch researchers.
- Synthesize researcher findings into the deliverable.

Researcher responsibilities:

- Receive a focused question.
- Investigate.
- Return findings.

Rules:

- The coordinator does **not** do deep research itself.
- The coordinator delegates research.
- The coordinator **does** synthesize.
- Synthesis stays with the coordinator because synthesis is construction.
- Do not promote synthesis to `claude-opus`.
- Do not treat `gpt-xhigh` as the default coordinator.

A single agent that tries to do both deep research and synthesis across parallel findings produces shallow work.
Split the roles.

## When Opus is NOT the right choice

Reach for Opus when the question is:

- Does this serve its stated purpose?
- Is this aligned with the intended direction?
- Do these changes belong together?
- Do the claimed justifications actually hold?

Do **not** reach for Opus when the question is:

- Is the evidence present?
- Does this match a checklist?
- Build an artifact from these inputs.
- Integrate findings into a deliverable.
- Summarize this quickly.

Model routing for those cases:

- Evidence / checklist / presence checks: `gpt-high`
- Construction / integration / synthesis: `gpt-high`
- Quick summaries / fast passes: `claude-sonnet`

Using Opus for construction wastes reasoning budget and confuses judge-work with builder-work.

## Invocation

All models are invoked through the `agents` CLI.
Workflow wrapper: `~/ai/workflows/agents-cli.md`
Full CLI reference: `/home/nes/projects/agent-runner/README.md`
