# Model Roles

Central rule for which model to reach for.
Workflow docs in `~/ai/workflows/` reference this file.
Do not restate the matrix there.

## The mental model

> GPT proposes "these are what solve these problems."
>
> Opus states "do they now? I'll be the judge of that."

- **GPT** (`gpt-high`): Default proposer, builder, researcher, implementer, and checklist auditor. Use it for evidence gathering, case enumeration, implementation, tests, and most artifact construction.
- **Opus** (`claude-opus`): Judgement, alignment, purpose-fit review, high-stakes external prose, and judge/router orchestration. Use it when the task depends on intent judgement, review quality, ticket-system prose, PR prose, or routing/gate arbitration.
- **Opus is not the default synthesizer**, but shipped exceptions exist where writing quality or judgement-heavy routing is the point.
- Synthesis is usually construction; route it to `gpt-high` unless a workflow/operator explicitly owns a narrower Opus exception.

## Matrix

| Model | Role | Use for |
|---|---|---|
| `gpt-high` | **Default.** Proposer/builder/auditor. | RCA, research, most synthesis, proposals, hookpoint analysis, implementation, test writing, implementation-pipeline audit risk, coverage analysis, behavior investigation, CodeRabbit fixes, commit hygiene, test-audit gate, and roadmap ticket-file generation. Use it for work that gathers evidence, enumerates cases, builds internal artifacts, or checks presence against a checklist unless a workflow/operator names a narrower exception. |
| `gpt-xhigh` | Reserve for **very large** problems only. Not the default coordinator. | Multi-file proposals spanning subsystems; research that needs deep reasoning across many sources before delegation; rare strategic synthesis where reasoning depth, not judgement, is the bottleneck. |
| `claude-opus` | Judge / reviewer / external-prose specialist / judge-router. | Use for scope risk, shortcut risk, supported-surface risk, alignment gates, multi-concern PR review, justification PR review, adversarial writing reviews, PR title/body writing, ticket-system read/comment/create/search/transition operators, and orchestrators whose prompt limits them to routing, gate evaluation, or arbitration rather than product implementation. |
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
| Supported-surface risk | `claude-opus` | Intent: does this still serve the supported surface? |
| Hookpoint research | `gpt-high` | Analysis |
| Implementation | `gpt-high` | Build |
| Test writing (separate agent) | `gpt-high` | Enumerate cases from contract |
| CodeRabbit loop | tool | Automated |
| Test-audit gate | `gpt-high` | Checklist against stated acceptance criteria |
| Commit-hygiene check | `gpt-high` | Checklist against small-testable-commit rules |
| Multi-concern PR review | `claude-opus` | Intent: does this PR belong together? |
| Justification PR review | `claude-opus` | Intent: does every change justify its presence? |
| PR writing | `claude-opus` | External-reader writing quality. |
| Alignment gate (skill/ai-workflow) | `claude-opus` | Direction check: is this going the right way? |

## Coordinator / researcher split for large tasks

Use a split when the task needs both broad reasoning and detailed research.

- For research fanout, **coordinator** is `gpt-high` by default.
- For research fanout, **coordinator** is `gpt-xhigh` only when the research synthesis problem is very large.
- For research fanout, **researcher** is `gpt-high`.

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
- For research fanout, the coordinator **does** synthesize.
- For research fanout, synthesis stays with the coordinator because synthesis is construction.
- This does not override workflow/operator-specific Opus assignments for judge/router orchestration, ticket-system prose, or PR prose.
- Do not treat `gpt-xhigh` as the default coordinator.

A single agent that tries to do both deep research and synthesis across parallel findings produces shallow work.
Split the roles.

## When Opus is NOT the right choice

Reach for Opus when the question is:

- Does this serve its stated purpose?
- Is this aligned with the intended direction?
- Do these changes belong together?
- Do the claimed justifications actually hold?
- Does this PR/ticket prose need external-reader quality?
- Is this an orchestrator/gate arbitration role whose prompt forbids implementation?

Do **not** reach for Opus when the question is:

- Is the evidence present?
- Does this match a checklist?
- Build an internal artifact from these inputs.
- Integrate internal findings into a deliverable.
- Summarize this quickly.

Scoped routing summary:

- Evidence / checklist / presence checks: `gpt-high`
- Internal construction / integration / synthesis: `gpt-high`
- PR prose and ticket-system prose: `claude-opus`
- Quick summaries / fast passes: `claude-sonnet`
- Opus construction is exceptional and must be named by frontmatter or workflow dispatch.

## Invocation

All models are invoked through the `agents` CLI.
Workflow wrapper: `~/ai/workflows/agents-cli.md`
Full CLI reference: `/home/nes/projects/agent-runner/README.md`
