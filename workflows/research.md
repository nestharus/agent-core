# Research Workflow

For open-ended investigation: option analysis, external-source review,
feasibility assessment, comparable-product study. Also used as Phase 1 of the
implementation pipeline when the problem is not pre-scoped.

Model assignments follow `~/ai/models/roles.md`.
This doc cites phase-level choices but does not restate the matrix.

Agent invocation: `~/ai/workflows/agents-cli.md`
Parallel-agent isolation: `~/ai/conventions/worktree-isolation.md`

## When to use

- The question cannot be answered from the current codebase alone.
- An external source is required to form a view.
- The problem is not scoped tightly enough to write a proposal yet.
- You need to compare approaches, products, or technologies before deciding.

## Shape

Choose based on how the question decomposes.

### Single-agent (default for small questions)

- **Who**: one `gpt-high` researcher.
- **When**: one focused question, with reasonable expectation that one agent can
  answer it without drowning.
- **Artifact**: `planning/research/NN-<topic>.md` or the project-specific
  equivalent.

### Parallel-fanout (default for broad questions)

- **Who**: one coordinator plus `gpt-high` researchers in parallel.
- **Coordinator**: `gpt-high` by default; `gpt-xhigh` only when the problem is
  very large.
- **Coordinator role**: identify the sub-questions, write focused prompts,
  launch the researchers, then synthesize the findings into one deliverable.
- **Researchers**: each receives one focused sub-question and returns
  evidence-backed findings with citations.
- **Artifacts**:
  `planning/research/NN-<topic>.md` for the synthesized report.
  `planning/research/NN-<topic>-<subtopic>.md` for each raw finding set.

### Deep-reasoning escalation

- **Who**: one `gpt-xhigh` researcher.
- **When**: the question needs layered reasoning across many sources and cannot
  be cleanly split into independent sub-questions.
- **Rule**: rare. If the question can be split, split it and use
  parallel-fanout.

## Phases

### Phase 1 - Scope

Human writes or confirms the question.
Scope it tightly. "Which caching library should we use?" beats
"How should caching work?".

### Phase 2 - Research

Dispatch according to the chosen shape.
Each researcher:

- Receives one focused question.
- Investigates with primary sources: documentation, source code, release notes,
  standards, issue trackers, and real-world reports when they are the original
  record.
- Returns findings with citations.
- Sources every non-obvious claim.
- Does not design solutions.

Research produces evidence, not proposals.

### Phase 3 - Synthesis

The coordinator, or the single researcher in single-agent mode, integrates the
findings into one deliverable.

- Synthesis is `gpt-high`. Not `claude-opus`. See `~/ai/models/roles.md`.
- Synthesis is construction, not judgement.
- Output structure: question -> evidence -> options with tradeoffs ->
  recommendation.
- If the evidence is inconclusive, say so.

Do not invent a recommendation from thin data.

### Phase 4 - Decision

Human reads the synthesized report and decides next steps.

- Accept the recommendation and move to proposal.
- Reject and reframe the question.
- Commission follow-up research.

## Rules

- **Primary sources only.** Do not cite derivative summaries when the original
  source exists.
- **Evidence before opinion.** Claims that affect the recommendation must trace
  to cited findings.
- **No solution design in research.** Research produces facts. Proposal designs
  solutions.
- **Parallel researchers work in isolation.** If they write tracked files, use
  separate worktrees per `~/ai/conventions/worktree-isolation.md`. If they only
  write to `.tmp/` or `.build/`, shared project root is acceptable.
- **Synthesis happens once.** Do not synthesize the synthesis. If the result is
  wrong, fix the bad research output and re-synthesize from source findings.

## Design Research Specialization

When the question is specifically about UI, UX, or visual patterns:

- Ask for concrete patterns, not abstract principles.
- Reference comparable products by name.
- Request implementation approaches, wiring details, failure modes, and
  tradeoffs.
- Keep synthesis on `gpt-high`.
- Use `claude-opus` only for adversarial review of the synthesized design, not
  for synthesis.

## Output Location

Default location: `planning/research/NN-<topic>.md`, where `NN` is zero-padded
order within the project.

Projects with different conventions, such as `research/NN-<topic>.md`, follow
their own convention. `~/ai/` does not override project-local paths.

## References

- Canonical phase structure: `/home/nes/projects/videos/AGENTS.md`
- Minimal single-agent form: `/home/nes/projects/server-manager/AGENTS.md`
- Design research specialization:
  `/home/nes/projects/visual-code-editor/AGENTS.md`
- Model-role authority: `~/ai/models/roles.md`
