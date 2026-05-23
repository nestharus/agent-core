# Model Roles

Central rule for which model to reach for.
Workflow docs in `~/ai/workflows/` reference this file.
Do not restate the matrix there.

## The mental model

> GPT proposes "these are what solve these problems."
>
> Opus states "do they now? I'll be the judge of that."

- **GPT** (`gpt-high`): Default proposer, builder, researcher, implementer, and checklist auditor. Use it for evidence gathering, case enumeration, implementation, tests, and most artifact construction.
- **Opus** (`claude-opus`): Judgement, purpose-fit review, and high-stakes external prose. Use it when the task depends on intent judgement on narrow gates (shortcut risk, supported-surface risk), adversarial writing review, ticket-system prose, or PR prose.
- **gpt-xhigh**: Orchestration, alignment, deep-reasoning audits, and risk-assessment work where reasoning depth across many inputs is the bottleneck.
- **Opus is not the default synthesizer**, but shipped exceptions exist where writing quality or judgement-heavy routing is the point.
- Synthesis is usually construction; route it to `gpt-high` unless a workflow/operator explicitly owns a narrower Opus exception.

## Matrix

| Model | Role | Use for |
|---|---|---|
| `gpt-high` | **Default.** Proposer/builder/auditor. | RCA, research, most synthesis, proposals, hookpoint analysis, implementation, test writing, implementation-pipeline audit risk, behavior investigation, CodeRabbit comment fixing when not delegated to gpt-medium, commit hygiene, test-audit gate, multi-concern PR review, justification PR review, and roadmap ticket-file generation. Use it for work that gathers evidence, enumerates cases, builds internal artifacts, or checks presence against a checklist unless a workflow/operator names a narrower exception. |
| `gpt-xhigh` | Orchestrators, deep-reasoning auditors, alignment, and risk-assessment work. | All `*-orchestrator` operators that route a workflow end-to-end; proof-risk, scope-risk, coverage, risk-assessor, philosophy-alignment, workflow-reviewer, agent-design / workflow-design / workflow-process auditors, work-manager ticket-brief auditor, rebase-drift-checker; multi-file proposals spanning subsystems; research that needs deep reasoning across many sources before delegation; strategic synthesis where reasoning depth is the bottleneck. |
| `claude-opus` | Judge / reviewer / external-prose specialist. | Use for shortcut risk, supported-surface risk, adversarial writing reviews, PR title/body writing, ticket-system read/comment/create/search/transition operators, and other intent-judgement or external-prose tasks. Orchestrators no longer default to Opus; see `gpt-xhigh`. |
| `gpt-medium` | Fast, structured per-comment automation. | CodeRabbit operator + per-comment fixer driving the PR-mode review loop. |
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
| Scope risk | `gpt-xhigh` | Intent + estimate-delta reasoning: does this stay within the stated scope, including the >2x inherited estimate-delta signal? |
| Shortcut risk | `claude-opus` | Intent: do the shortcuts compromise the underlying purpose? |
| Supported-surface risk | `claude-opus` | Intent: does this still serve the supported surface? |
| Proof risk | `gpt-xhigh` | Runtime-claim to proof-method evidence-class match. |
| Hookpoint research | `gpt-high` | Analysis |
| Implementation | `gpt-high` | Build |
| Test writing (separate agent) | `gpt-high` | Enumerate cases from contract |
| CodeRabbit loop (operator + per-comment fixer) | `gpt-medium` | Structured per-comment automation against the PR-mode driver. |
| Test-audit gate | `gpt-high` | Checklist against stated acceptance criteria |
| Commit-hygiene check | `gpt-high` | Checklist against small-testable-commit rules |
| Multi-concern PR review | `gpt-high` | Decide whether the PR should be split. |
| Justification PR review | `gpt-high` | Decide whether every change justifies its presence. |
| PR writing | `claude-opus` | External-reader writing quality. |
| Alignment gate (skill/ai-workflow) | `gpt-xhigh` | Direction check: is this going the right way? |
| Orchestrator (any `*-orchestrator`) | `gpt-xhigh` | Routes a workflow end-to-end; depth-of-reasoning is the bottleneck. |

## Coordinator / researcher split for large tasks

Use a split when the task needs both broad reasoning and detailed research.

- For research fanout, **coordinator** is `gpt-xhigh` by default (orchestrator-class work).
- For research fanout, **coordinator** may drop to `gpt-high` for narrow fanouts whose synthesis is mechanical aggregation rather than reasoning depth.
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
- This does not override workflow/operator-specific Opus assignments for ticket-system prose or PR prose.

A single agent that tries to do both deep research and synthesis across parallel findings produces shallow work.
Split the roles.

## When Opus is NOT the right choice

Reach for Opus when the question is:

- Do the shortcuts compromise the underlying purpose?
- Does this still serve the supported surface?
- Does this PR/ticket prose need external-reader quality?

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
