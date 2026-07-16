# Model Roles

Central rule for which model to reach for.
Workflow docs in `~/ai/workflows/` reference this file.
Do not restate the matrix there.

## The mental model

- **`gpt-high`** is the standard reasoning route for workers and coordinators: proposal, research, implementation, orchestration, alignment, risk assessment, review gates, and external-facing prose.
- **`gpt-medium`** is the fast automation route for bounded, structured operator loops.
- Legacy provider-specific model ids are deprecated for shared routing. Do not add new provider-specific assignments to operational docs; update the operator frontmatter and this matrix instead.

## Matrix

| Model | Role | Use for |
|---|---|---|
| `gpt-high` | **Default.** Worker, coordinator, auditor, and writer. | RCA, research, synthesis, proposals, implementation, testing, orchestration, alignment, risk assessment, review gates, behavior investigation, commit hygiene, ticket prose, PR prose, and roadmap generation. Keep separate concerns in separate invocations even when they use the same model. |
| `gpt-medium` | Fast, structured per-comment automation. | CodeRabbit operator + per-comment fixer driving the PR-mode review loop. |

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
| Scope risk | `gpt-high` | Intent + estimate-delta reasoning: does this stay within the stated scope, including the >2x inherited estimate-delta signal? |
| Shortcut risk | `gpt-high` | Intent: do the shortcuts compromise the underlying purpose? |
| Supported-surface risk | `gpt-high` | Intent: does this still serve the supported surface? |
| Proof risk | `gpt-high` | Runtime-claim to proof-method evidence-class match. |
| Hookpoint research | `gpt-high` | Analysis |
| Implementation | `gpt-high` | Build |
| Test writing (separate agent) | `gpt-high` | Enumerate cases from contract |
| CodeRabbit loop (operator + per-comment fixer) | `gpt-medium` | Structured per-comment automation against the PR-mode driver. |
| Test-audit gate | `gpt-high` | Checklist against stated acceptance criteria |
| Commit-hygiene check | `gpt-high` | Checklist against small-testable-commit rules |
| Multi-concern PR review | `gpt-high` | Decide whether the PR should be split. |
| Justification PR review | `gpt-high` | Decide whether every change justifies its presence. |
| PR writing | `gpt-high` | External-reader writing quality. |
| Alignment gate (skill/ai-workflow) | `gpt-high` | Direction check: is this going the right way? |
| Orchestrator (any `*-orchestrator`) | `gpt-high` | Routes a workflow end-to-end; depth-of-reasoning is the bottleneck. |

## Coordinator / researcher split for large tasks

Use a split when the task needs both broad reasoning and detailed research.

- For research fanout, **coordinator** is `gpt-high`.
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
- Coordinator and researcher remain separate invocations even though both use `gpt-high`.

A single agent that tries to do both deep research and synthesis across parallel findings produces shallow work.
Split the roles.

## When to use `gpt-medium`

Use `gpt-high` for substantive reasoning, including:

- Does this route the whole workflow correctly?
- Do the shortcuts compromise the underlying purpose?
- Does this still serve the supported surface?
- Does this require deep alignment or risk reasoning across many inputs?

Use `gpt-medium` only for bounded, structured automation where speed matters more than reasoning depth, such as:

- Applying one already-decided transformation repeatedly.
- Driving a deterministic per-comment loop.
- Producing a quick summary that does not make a gate decision.

Scoped routing summary:

- Evidence, judgement, construction, integration, synthesis, and prose: `gpt-high`
- Bounded structured automation and non-decisional fast passes: `gpt-medium`

## Invocation

All models are invoked through the `agents` CLI.
Workflow wrapper: `~/ai/workflows/agents-cli.md`
Full CLI reference: `/home/nes/projects/agent-runner/README.md`
