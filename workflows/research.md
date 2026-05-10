---
workflow:
  id: research
workflow_dispatch_contract:
  orchestrator: "research coordinator or implementation-pipeline Phase 1"
  inputs:
    - "focused research question, scope constraints, output location, and source requirements"
    - "optional decomposition into single-agent, parallel-fanout, or deep-reasoning shape"
  expectations:
    - "collects primary-source evidence before forming options or recommendations"
    - "keeps research factual and separate from solution proposal design"
    - "synthesizes findings once into a traceable report with assumptions and tradeoffs"
  outputs:
    - "planning research report with question, evidence, options, recommendation, and open risks"
    - "raw finding artifacts for parallel-fanout sub-questions when used"
    - "optional draft problem map and assumption register for downstream proposal work"
  non_goals:
    - "does not design or implement the solution"
    - "does not cite derivative summaries when primary sources are available"
    - "does not advance past inconclusive evidence that needs user-owned reframing"
---
# Research Workflow

For open-ended investigation: option analysis, external-source review,
feasibility assessment, comparable-product study. Also used as Phase 1 of the
implementation pipeline when the problem is not pre-scoped.

Model assignments follow `~/ai/models/roles.md`.
This doc cites phase-level choices but does not restate the matrix.

Agent invocation: `~/ai/workflows/agents-cli.md`
Agent Q&A and session graph convention: `~/ai/conventions/agent-questions-and-session-graph.md`
Worktree isolation and central-checkout read-state rule: `~/ai/conventions/worktree-isolation.md`
Process-tree review operator: `~/ai/agents/process-tree-auditor.md`
Workflow-execution violation taxonomy: `~/ai/conventions/workflow-execution-violations.md`

## Workflow Dispatch Surface

### Orchestrator

research coordinator or implementation-pipeline Phase 1

### Inputs

- focused research question, scope constraints, output location, and source requirements
- optional decomposition into single-agent, parallel-fanout, or deep-reasoning shape

### Expectations

- collects primary-source evidence before forming options or recommendations
- keeps research factual and separate from solution proposal design
- synthesizes findings once into a traceable report with assumptions and tradeoffs

### Outputs

- planning research report with question, evidence, options, recommendation, and open risks
- raw finding artifacts for parallel-fanout sub-questions when used
- optional draft problem map and assumption register for downstream proposal work

### Non-goals

- does not design or implement the solution
- does not cite derivative summaries when primary sources are available
- does not advance past inconclusive evidence that needs user-owned reframing

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

Delegated agents may return `NEEDS_INPUT:<question_artifact>` only for scope clarification or reframing questions that block research. The root handles those questions through `~/ai/conventions/agent-questions-and-session-graph.md` before Phase 2 starts.

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

In parallel fanout, delegated researchers may ask only for scope corrections that change their assigned sub-question. The root must answer and record continuation evidence before Phase 3 consumes the affected finding.

For parallel-fanout research, after Phase 2 returns and before Phase 3 synthesis, run `process-tree-auditor` on the fanout subtree. The expected process lists each researcher question, prompt, log, and raw finding artifact. A blocking process violation prevents synthesis from consuming incomplete fanout.

### Phase 3 - Synthesis

The coordinator, or the single researcher in single-agent mode, integrates the
findings into one deliverable.

- Synthesis is `gpt-high`. Not `claude-opus`. See `~/ai/models/roles.md`.
- Synthesis is construction, not judgement.
- Output structure: question -> evidence -> options with tradeoffs ->
  recommendation.
- When the deliverable feeds proposal work on an existing system, append a
  draft current `problem map` plus a short draft assumption register for the
  touched surface. Phase 2.5 validates and narrows the map into
  `research/NN-problem-map.md`; Phase 3 validates and narrows the register
  into the approved assumption register in `proposals/NN-*.md`. Do not keep
  competing second artifacts.
- If the evidence is inconclusive, say so.

Do not invent a recommendation from thin data.

If inconclusive evidence leaves a human-owned reframe or follow-up decision unresolved, the coordinator may return `NEEDS_INPUT:<question_artifact>`. Do not synthesize a recommendation or advance to Phase 4 until the answer is applied.

### Phase 4 - Decision

Human reads the synthesized report and decides next steps.

- Accept the recommendation and move to proposal only when the current
  `problem map` is explicit enough to constrain proposal work.
- Reject and reframe the question.
- Commission follow-up research.
- If later evidence invalidates a recorded assumption, re-enter research and
  resume at Phase 2.5 rather than patching the proposal around it.

Any delegated question at this phase must be limited to accept, reframe, or follow-up decisions owned by the user. The root surfaces it and blocks downstream proposal work until continuation evidence exists.

## Rules

- **Primary sources only.** Do not cite derivative summaries when the original
  source exists.
- **Evidence before opinion.** Claims that affect the recommendation must trace
  to cited findings.
- **No solution design in research.** Research produces facts. Proposal designs
  solutions.
- **Parallel researchers work in isolation.** Parallel researchers each work in their own worktree per `~/ai/conventions/worktree-isolation.md`; tracked-file writes and branch work always run from a worktree, regardless of concurrency. Read-state inspection of the central checkout (no tracked-file edits) is acceptable. Outside-repo scratch (e.g. `/tmp/$(uuidgen)`) for non-tracked artifacts remains a recognized carve-out for read-only investigations.
- **Synthesis happens once.** Do not synthesize the synthesis. If the result is
  wrong, fix the bad research output and re-synthesize from source findings.
- **Use audit history for repeated review loops.** When research synthesis is revised and re-reviewed across rounds, follow `~/ai/conventions/audit-history.md` so prior findings, watch signals, and determinations remain visible.
- **Question handling.** Use `~/ai/conventions/agent-questions-and-session-graph.md` for delegated scope, reframe, inconclusive-synthesis, and follow-up questions. Sub-agents must not ask the user to replace required research or model-owned synthesis.

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
