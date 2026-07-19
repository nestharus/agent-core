# AGENTS.md Inventory — 2026-04-22

## Summary
- Files analyzed: 7
- Total sections identified: 199 headings (Markdown headings outside fenced code blocks)
- SHARED_EXACT: 6 section instances in 3 families
- SHARED_WITH_DRIFT: 72 section instances in 20 families
- PROJECT_SPECIFIC: 118 section instances
- CONTRADICTION: 3 primary section instances; 3 cross-source conflicts recorded

## SHARED_EXACT
### CLI Syntax
Canonical phrasing (from `agent-implementation-skill`, L33-50):
```text
agents [OPTIONS] [AGENT] [PROMPT...]
| Option | Description |
|--------|-------------|
| `-m, --model <MODEL>` | Execute a model directly (no agent file) |
| `-a, --agent-file <AGENT_FILE>` | Path to an agent `.md` file (any location) |
| `-f, --file <FILE>` | Read prompt from file |
| `-p, --project <PROJECT>` | Working directory for the subprocess |
| `-i, --input <KEY=VALUE>` | Pass model inputs as key=value (repeatable) |
```
Sources: `work` L292-309; `agent-implementation-skill` L33-50

### Multimodal Models
Canonical phrasing (from `work`, L365-386):
```text
Image/video generation models use wrapper scripts as their `command`. The scripts handle HTTP APIs, polling, downloading — the runner just validates inputs and passes flags through.
# Generate an image (raw bytes on stdout, pipe to file)
agents -m seedream-t2i "A sunset over mountains" > sunset.jpeg
# Generate a video
agents -m seedance-t2v-low -i duration=5 -i resolution=480p "A whale swimming" > whale.mp4
# Image-to-video with source image
agents -m seedance-i2v-fast -i image=./photo.jpg "Slow camera orbit" > orbit.mp4
# Image editing with reference images
```
Sources: `work` L365-386; `agent-implementation-skill` L139-160

### Available Models
Canonical phrasing (from `work`, L407-410):
```text
See `~/.config/oulipoly-agent-runner/models/` for the full list. Model selection guidance is in `src/models.md`.
```
Sources: `work` L407-410; `agent-implementation-skill` L161-166

## SHARED_WITH_DRIFT
### Agents CLI Entry Points / Sub-Agent Execution
- work — Running External Models + Running Sub-Agents — `/home/nes/work/AGENTS.md` (L156-179, L288-291)
```text
The `agents` CLI (`~/.local/bin/agents`) runs external models and agents.
# Run a model directly (no agent file needed):
agents -m gpt-high -p /home/nes/work/rfqautomation-linux "your prompt here"
agents -m claude-opus -p /home/nes/work/rfqautomation-linux "your prompt here"
# Run from a prompt file:
agents -m gpt-high -p /home/nes/work/rfqautomation-linux -f prompt.md
# Run a named agent (from agents/ directory):
```
Distinct: Combines direct model execution, named-agent execution, config-path notes, and an explicit instruction to use the external `agents` binary rather than the built-in agent tool.
- agent-implementation-skill — Running Sub-Agents — `/home/nes/projects/agent-implementation-skill/AGENTS.md` (L29-32)
```text
Sub-agents are invoked via the `agents` binary (`~/.local/bin/agents`), not through Claude Code's built-in Agent tool. The binary is the CLI mode of [Oulipoly Agent Runner](https://github.com/nestharus/agent-runner).
```
Distinct: Near-copy of the work repo wording, but scoped to this skill repository and followed immediately by runner-specific CLI docs.
- server-manager — Running Sub-Agents — `/home/nes/projects/server-manager/AGENTS.md` (L417-451)
```text
The `agents` CLI (`~/.local/bin/agents`) runs external models.
# Run a model with a prompt:
agents -m gpt-high -p <worktree-path> "your prompt"
# Run from a prompt file:
agents -m gpt-high -p <worktree-path> -f prompt.md
# Available models: gpt-high, gpt-medium, gpt-low, gpt-xhigh,
#   claude-opus, claude-sonnet, claude-haiku,
```
Distinct: Same external CLI family, but shortened and paired with a strong worktree-isolation rule for parallel writers.
Semantic difference summary: Substantive drift. All three use the same `agents` CLI, but the work repo is the fullest runner reference, while `server-manager` adds mandatory per-agent worktree isolation. Also cross-cited in CONTRADICTION C1 because `ai-workflow` prescribes a different delegation mechanism.

### Common Invocation Patterns
- work — Common Patterns — `/home/nes/work/AGENTS.md` (L310-325)
```text
# Model + prompt file (pipeline standard)
agents --model gpt-high --file prompt.md
# Agent file + model override
agents --agent-file ~/work/agents/e2e-operator.md --model claude-opus --file prompt.md
# Pipe prompt from stdin
cat spec.md | agents --model glm
# Set working directory
```
Distinct: Uses work-specific examples, including an operator file under `~/work/agents/`.
- agent-implementation-skill — Common Invocation Patterns — `/home/nes/projects/agent-implementation-skill/AGENTS.md` (L51-69)
```text
# Model + prompt file (pipeline standard)
agents --model gpt-high --file prompt.md
# Agent file + model override
agents --agent-file src/staleness/agents/alignment-judge.md --model claude-opus --file prompt.md
# Named agent (resolved from agents directory)
agents code-reviewer "Review this function"
# Pipe prompt from stdin
```
Distinct: Adds a named-agent example and slightly more explicit wording around subprocess working directories.
Semantic difference summary: Mostly cosmetic drift. The examples differ, but the invocation shapes are the same.

### Agent File Format / Agent Skeleton
- work — Agent File Format — `/home/nes/work/AGENTS.md` (L326-337)
```text
---
description: 'One-line description'
model: claude-opus
output_format: ''
---
System prompt / instructions here.
```
Distinct: Minimal frontmatter template for operator files.
- agent-implementation-skill — Agent File Format — `/home/nes/projects/agent-implementation-skill/AGENTS.md` (L70-85)
```text
Agent definitions live in `src/<system>/agents/*.md`. Each is a markdown file with YAML frontmatter:
---
description: 'One-line description of what this agent does'
model: claude-opus
output_format: ''
---
System prompt / reasoning method goes here.
```
Distinct: Adds path expectations (`src/<system>/agents/*.md`) and explains that `model` is only a default override.
- videos — Adding an agent file — `/home/nes/projects/videos/AGENTS.md` (L418-441)
```text
New agents go in `agents/*.md` following the `~/work/agents/*.md` format:
---
description: 'One-line description'
model: <default-model>
output_format: ''
---
# Agent name
```
Distinct: Builds on the same frontmatter but adds a full document skeleton (`Use When`, `Procedure`, `Stop Conditions`, etc.).
Semantic difference summary: Substantive drift. The frontmatter core is shared, but `videos` imposes a richer operator-document contract and `agent-implementation-skill` adds repository placement/override rules.

### Input Schema / Runner Input Semantics
- work — Input Schema — `/home/nes/work/AGENTS.md` (L338-364)
```text
Models can declare typed input parameters via `[[inputs]]` in their TOML configs. The runner validates user-supplied `-i key=value` flags against the schema and maps them to CLI flags on the wrapped command.
| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Input identifier |
| `type` | yes | `string`, `integer`, `number`, `boolean`, `enum`, `array` |
| `flag` | no | CLI flag to pass to the command (e.g. `"--size"`) |
| `required` | no | Fail if not provided and no default |
```
Distinct: Canonical runner-facing field table and flow description.
- agent-implementation-skill — Input Schema — `/home/nes/projects/agent-implementation-skill/AGENTS.md` (L112-138)
```text
Models can declare typed input parameters via `[[inputs]]` in their TOML configs. The runner validates user-supplied `-i key=value` flags against the schema and maps them to CLI flags on the wrapped command.
| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Input identifier |
| `type` | yes | `string`, `integer`, `number`, `boolean`, `enum`, `array` |
| `flag` | no | CLI flag to pass to the command (e.g. `"--size"`) |
| `required` | no | Fail if not provided and no default |
```
Distinct: Verbatim copy of the same runner-facing contract.
- agent-runner — Input Schema System — `/home/nes/projects/agent-runner/AGENTS.md` (L95-117)
```text
Models can declare typed input parameters via `[[inputs]]` in their TOML
configs. The runner validates user-supplied `-i key=value` flags against
the schema and maps them to CLI flags on the wrapped command.
**How inputs flow:**
1. The `default_input = true` input receives the positional prompt (args, `--file`, or stdin)
2. Named inputs (`-i key=value`) are validated against the schema
3. Each input's `flag` field determines the CLI flag passed to the command (e.g., `flag = "--size"`)
```
Distinct: Explains the same concept from the app product angle, including UI grouping implications and raw binary/stdout handling in Rust.
Semantic difference summary: Mostly cosmetic-to-moderate drift. The mechanism is the same; `agent-runner` reframes it for the control-plane product rather than the external caller.

### Model / Command Configuration Semantics
- agent-implementation-skill — Model Configuration — `/home/nes/projects/agent-implementation-skill/AGENTS.md` (L86-111)
```text
Model configs are TOML files in `~/.config/oulipoly-agent-runner/models/` (one per model). The filename minus `.toml` is the model name used with `--model`.
Single provider:
command = "claude"
args = ["-p", "--model", "haiku"]
prompt_mode = "stdin"
Multiple providers (load balanced):
prompt_mode = "arg"
```
Distinct: Documents TOML model configs, multi-provider load balancing, and the SQLite state file used by the runner.
- agent-runner — Model Command Syntax — `/home/nes/projects/agent-runner/AGENTS.md` (L118-151)
```text
The `command` field in model TOML configs supports multi-token strings.
The **last token** is extracted as the provider name for pool grouping
and display. Earlier tokens are treated as a command prefix (e.g., for
setting or unsetting environment variables).
**Simple command** — provider is the command itself:
command = "claude"
# Provider name: "claude"
```
Distinct: Documents how multi-token command strings are parsed so the UI can derive a provider name for grouping/display.
Semantic difference summary: Substantive drift. Both sections explain runner configuration, but one is backend/provider orchestration and the other is UI/provider-name parsing.

### Repository Structure Maps
- work — Folder Structure — `/home/nes/work/AGENTS.md` (L101-126)
```text
~/work/
  rfqautomation-linux/          # App repo — on main (never commit here directly)
  rfqinstallation-linux/        # Installation/setup repo
  agents/                       # Specialist agent files
  worktrees/                    # Git worktrees — one per active task
  planning/
    e2e/                        # E2E testing project
```
Distinct: Filesystem layout for the coordinating `~/work/` repo, including planning, worktrees, and external task folders.
- agent-implementation-skill — Project Structure — `/home/nes/projects/agent-implementation-skill/AGENTS.md` (L3-28)
```text
├── governance/              # Project governance layer
│   ├── problems/index.md    # Why this code exists (PRB-XXXX)
│   ├── patterns/index.md    # How we solve recurring problems (PAT-XXXX)
│   ├── audit/prompt.md      # Audit process for external models
│   ├── audit/history.md     # Cumulative audit log (105 rounds)
│   ├── design/              # Design rationale documents
│   └── risk-register.md     # Landed-code risks and debt
```
Distinct: Repo tree centered on governance docs, philosophy, runtime skill code, evals, and tests.
- agent-runner — Current UI Architecture + Tauri Backend Structure — `/home/nes/projects/agent-runner/AGENTS.md` (L65-88, L269-287)
```text
App.tsx
├── SetupView (first-run wizard)
│   └── SetupSession (streaming event handler)
│       ├── StatusBar (with InlineSpinner)
│       ├── ProgressBar (Ark UI Progress)
│       ├── FormRenderer (dynamic forms)
│       ├── WizardStepper (Ark UI Steps)
```
Distinct: Splits structure into frontend component hierarchy and backend Rust module layout.
- server-manager — Architecture (Three Services) — `/home/nes/projects/server-manager/AGENTS.md` (L452-482)
```text
services/
  api/          # FastAPI — the mutation gateway. Both UI and Discord daemon call it.
    api/        # endpoints (versioned: v1/)
    contracts/  # Pydantic schemas / DTOs
    core/       # factory, settings, dependencies, middleware
    services/   # business logic
    repositories/  # database access
```
Distinct: High-level service architecture (API, Discord daemon, web app, shared types, migrations) rather than a simple repo tree.
- visual-code-editor — Directory Structure — `/home/nes/projects/visual-code-editor/AGENTS.md` (L51-61)
```text
app/assets/
  cards/           — SVG card frames per node type
  icons/           — type-specific icons (cluster, system, file, agent, store, etc.)
  panels/          — panel header/section decorations
  animations/      — SVG animation definitions (SMIL or CSS-driven)
  shared/          — reusable SVG fragments (gradients, filters, patterns)
```
Distinct: Narrow asset-pipeline tree focused on SVG storage and reuse.
Semantic difference summary: Substantive drift. Many repos include structure maps, but the scope ranges from local folder trees to runtime architecture and asset layout.

### Implementation & Bug-Fix Workflow
- work — Implementation & Bug-Fix Workflow — `/home/nes/work/AGENTS.md` (L180-212)
```text
All code changes follow the same pipeline. Bugs start with RCA; features skip it.
| Step | Model | Role |
|------|-------|------|
| 1. RCA (bugs only) | `gpt-high` | Investigate root cause. Read code, trace failure, produce report. Do NOT propose fixes. |
| 2. Proposal | `gpt-high` | Propose a fix/feature based on findings. Write a design proposal. Do NOT implement. |
| 3. Risk assessment | 3x `claude-opus` | Three sub-agents **in parallel**: audit risk + scope risk + shortcut risk. All must return **LOW**. If MEDIUM/HIGH, revise proposal and re-run. |
| 4. Research | `gpt-high` | **Only after all three risks are LOW.** Research hookpoints in the codebase. Understand what exists. Avoid building parallel systems. |
```
Distinct: Most elaborate pipeline: RCA/proposal/risk/research plus test discovery, red/green gates, CodeRabbit, test-audit, split review, commit hygiene, and draft PR opening.
- agent-implementation-skill — Implementation & Bug-Fix Workflow + Bug Fixes + Features / Refactors — `/home/nes/projects/agent-implementation-skill/AGENTS.md` (L389-393, L394-405, L406-409)
```text
All code changes — bug fixes, features, refactors — follow the same pipeline.
The only difference between a bug fix and a feature is that bugs start with RCA.
| Step | Model | Role |
|------|-------|------|
| 1. RCA | `gpt-high` | Investigate root cause. Read code, trace failure, produce report. Do NOT propose fixes. |
| 2. Proposal | `gpt-high` | Propose a fix based on RCA findings. Write a design proposal. Do NOT implement. |
| 3. Alignment | `claude-opus` | Check proposal against governance (patterns, philosophy, problems). Directional coherence, not coverage. Identify contradictions and gaps. Returns ALIGNED, MISALIGNED, or NEEDS_REVISION. |
```
Distinct: Adds an explicit governance-alignment loop before risk assessment and distinguishes bug-fix RCA from feature/refactor entry.
- server-manager — Implementation & Bug-Fix Workflow — `/home/nes/projects/server-manager/AGENTS.md` (L51-67)
```text
The 5-phase pipeline. Features skip RCA; bugs start with it. Nothing
is skipped except by explicit decision recorded in `DECISIONS.md`.
| Phase | Model | Artifact | Role |
|-------|-------|----------|------|
| 0. RCA (bugs only) | `gpt-high` | `research/NN-rca.md` | Investigate root cause. Read code, trace failure, produce report. **Do NOT propose fixes.** |
| 1. Problem research | `gpt-high` | `research/NN-*.md` | Document problem space with evidence. **Do NOT design solutions.** |
| 2. Synthesize user needs | `claude-opus` (this session, orchestrator) | `research/NN-*-needs.md` | Map research to Humility's specific context. Flag gaps. |
```
Distinct: Adds problem-space research and human synthesis/user-needs mapping before proposal, then feeds implementation into test/code separation.
- visual-code-editor — Implementation & Bug-Fix Workflow — `/home/nes/projects/visual-code-editor/AGENTS.md` (L255-268)
```text
All code changes follow the pipeline from `~/work/AGENTS.md`:
| Step | Model | Role |
|------|-------|------|
| 1. RCA (bugs only) | `gpt-high` | Investigate root cause. Do NOT propose fixes. |
| 2. Proposal | `gpt-high` | Propose a fix/feature. Do NOT implement. |
| 3. Risk assessment | 3x `claude-opus` | Audit risk + scope risk + shortcut risk in parallel. All must be LOW. |
| 4. Research | `gpt-high` | Research hookpoints in the codebase. |
```
Distinct: Explicitly says it inherits the work-repo pipeline, but only restates the high-level five-step version locally.
Semantic difference summary: Substantive drift. All four share RCA → proposal → risk/research → implement, but the intermediate gates, number of risk checks, and PR-prep steps differ materially.

### Implementation Principles
- agent-implementation-skill — Principles — `/home/nes/projects/agent-implementation-skill/AGENTS.md` (L410-425)
```text
- **Separate agents for separate concerns** — RCA agents don't propose. Proposal
  agents don't implement. Alignment agents don't fix. Each agent has one job.
- **Risk drives decomposition** — Don't decompose because "it's complex." Decompose
  because audit risk or alignment risk exceeds what one agent can handle reliably.
- **Alignment is directional** — "Is this going the right way?" not "Did we cover
  everything?" Alignment is sparse, checking concerns where there's risk of mismatch.
- **Research before implementation** — Every piece gets codebase research to find
```
Distinct: Frames alignment as directional and says decomposition should be driven by audit/alignment risk rather than complexity alone.
- server-manager — Principles — `/home/nes/projects/server-manager/AGENTS.md` (L68-81)
```text
- **Separate agents for separate concerns.** RCA agents don't propose;
  proposal agents don't implement. This is how you avoid the
  solution-fixation trap.
- **Zero-risk gate.** All three risk assessments must return LOW before
  implementation starts. Shortcut risk flags proposals that introduce
  their own shortcuts.
- **No compatibility shims** anywhere in the pipeline.
```
Distinct: Centers zero-risk gating, no compatibility shims, and role separation to avoid solution fixation.
Semantic difference summary: Substantive drift. Both promote separation of concerns and research-first implementation, but `agent-implementation-skill` is governance/alignment-heavy while `server-manager` is risk-gate-heavy.

### PR Review / Post-CodeRabbit Gates
- work — Post-CodeRabbit Review Gates + PR Review Workflow — `/home/nes/work/AGENTS.md` (L219-252, L253-281)
```text
Once CodeRabbit converges, run three gates **in parallel** on the actual
diff before opening any PRs:
The **test-audit gate** runs `agents/test-audit-gate.md` on the actual diff
and synthesizes spec-alignment, test-quality, and coverage-delta audits.
Both `FAIL` and `PARTIAL` from the test-audit gate block PR opening, except
the implementation-mode coverage-delta `PARTIAL` which is acknowledged.
1. **Multi-concern review.** Can this PR be split into smaller PRs, one per
```
Distinct: Turns PR review into a full post-CodeRabbit gate: test-audit, research verification, multi-concern, justification, commit hygiene, synthesis/posting, and optional proposal/domain loops.
- server-manager — PR Review Workflow — `/home/nes/projects/server-manager/AGENTS.md` (L176-196)
```text
After implementation and CodeRabbit, before merging, all PRs go through
decomposition review.
| Step | Model | Role |
|------|-------|------|
| 1. Multi-concern check | `claude-opus` | Can this PR be decomposed into smaller PRs with single concerns? Identify each concern, the lines/functions involved, and dependency order. |
| 2. Justification check | `claude-opus` | What deserves to be in this PR? What does not? Anything separable goes to its own PR. |
**Rules:**
```
Distinct: Keeps PR review narrow: multi-concern decomposition plus justification, both on the actual diff.
Semantic difference summary: Substantive drift. `server-manager` preserves the structural-review idea, but `work` expands it into a much heavier review orchestration stack.

### Research Workflow
- server-manager — Research Workflow — `/home/nes/projects/server-manager/AGENTS.md` (L245-256)
```text
For open-ended investigation:
1. **Scope** — define what question needs answering
2. **Research agent** (`gpt-high` or `gpt-xhigh` for deep research) —
   investigate, produce a report
3. **Synthesis** (this session) — integrate findings into project context
4. **Decision** — user decides next steps based on findings
---
```
Distinct: Single-agent or deep-research pass, then local synthesis and user decision.
- videos — Research workflow — `/home/nes/projects/videos/AGENTS.md` (L207-241)
```text
For open questions the project doesn't already have answers to.
Based on the `~/projects/server-manager/AGENTS.md` pattern:
| Phase | Agent | Role |
|---|---|---|
| 1. Scope | Orchestrator | Split the question into focused sub-questions |
| 2. Research (parallel) | `gpt-high` × N researchers | Web search, cite primary sources, write to `planning/research/NN-topic.md` |
| 3. Synthesis | Orchestrator | Integrate findings into project context |
```
Distinct: Explicitly parallelizes focused researchers, requires primary-source citation, and records outputs under `planning/research/NN-topic.md`.
- visual-code-editor — Research Workflow — `/home/nes/projects/visual-code-editor/AGENTS.md` (L160-170)
```text
Use `gpt-high` for design research. Research prompts should:
- Reference specific comparable products/sites
- Ask for concrete patterns, not abstract principles
- Request implementation approaches, not just ideas
agents --model gpt-high --file /tmp/research-prompt.md --project ~/projects/visual-code-editor
```
Distinct: Narrows the pattern to design/comparable-product research prompts aimed at concrete implementation patterns.
Semantic difference summary: Substantive drift. The shared backbone is scope → research → synthesis → decision, but concurrency, citation expectations, and domain focus vary materially.

### Model Roles / No-Super-Agent Boundary
- server-manager — Model Roles + No Super Agents — `/home/nes/projects/server-manager/AGENTS.md` (L379-387, L388-416)
```text
| Model | Use for |
|-------|---------|
| `gpt-high` | RCA, proposals, research, hookpoint analysis, implementation |
| `gpt-xhigh` | Coordination and deep reasoning (see below) |
| `claude-opus` | Risk assessments, PR reviews, alignment reviews, synthesis |
| `claude-sonnet` | Quick checks, summaries |
**CRITICAL**: No single agent should both research AND synthesize for
```
Distinct: Defines the canonical coordinator/researcher split (`gpt-xhigh` vs `gpt-high`) and bans single-agent deep-research/synthesis combos.
- videos — Model roles — `/home/nes/projects/videos/AGENTS.md` (L277-294)
```text
Mirrors `~/work/AGENTS.md` and `~/projects/server-manager/AGENTS.md`:
| Model | Role |
|---|---|
| `gpt-high` | RCA, proposals, research, hookpoint analysis, implementation |
| `gpt-xhigh` | Coordinator for large tasks |
| `claude-opus` | Risk assessments, reviews, alignment, synthesis |
| `claude-sonnet` | Quick checks, summaries |
```
Distinct: Reuses the same GPT/Claude split, then adds multimodal analysis (`gemini-video-*`) and generation (`seedream-*`, `seedance-*`).
- visual-code-editor — Model Roles + Model Boundary: Gemini vs GPT — `/home/nes/projects/visual-code-editor/AGENTS.md` (L73-86, L87-96)
```text
| Task | Model | Why |
|------|-------|-----|
| Research (best practices, patterns, prior art) | `gpt-high` | Best at systematic analysis and synthesis |
| SVG generation + art direction | `gemini-high` | Best SVG output, visual reasoning, self-correcting loops |
| SVG iteration / quick fixes | `gemini-low` | Speed over polish for tweaks |
| Visual design RCA (shadows, colors, borders, card styling) | `gemini-high` | Visual interpretation — reads screenshots, determines shades/colors, proposes CSS values |
| Animation design + parameterization | `gemini-high` | Visual reasoning for motion design |
```
Distinct: Makes the boundary visual: Gemini owns screenshot-based visual judgment and SVG/art direction; GPT owns code/algorithms; GLM is used for quick verification.
Semantic difference summary: Substantive drift. All three divide models by role, but the actual model roster and the role boundary are highly domain-specific.

### Gate Ownership / When To Ask The User
- server-manager — Gate ownership per phase + When to Ask the User — `/home/nes/projects/server-manager/AGENTS.md` (L82-110, L530-563)
```text
Different phases have different gates. Some are model-gated, some are
human-gated. Getting this wrong burns cycles and erodes trust.
| Phase | Gate owner | What the gate does |
|---|---|---|
| 0. RCA (bugs) | **Human** | User decides if the bug is worth fixing at all |
| 1. Problem research | **Human** | User confirms scope framing — did the research find the right problems? |
| 2. Synthesis | **Human** | User confirms the mapping to their actual needs and answers any open questions |
```
Distinct: Detailed human-vs-model gate table plus explicit “ask / do not ask” rules to avoid overchecking.
- videos — Gate ownership — `/home/nes/projects/videos/AGENTS.md` (L260-276)
```text
| Phase | Gate owner | Why |
|---|---|---|
| Problem space | Human | Scope / framing |
| Research | Human after each researcher report | Confirm findings are relevant |
| Synthesis | Human | Needs mapping |
| Proposal (pipeline design) | 3× `claude-opus` parallel risk | Risk IS the review |
| Hookpoint (what code/tools to reuse) | Human | Confirm pre-existing survives |
```
Distinct: Same scope-vs-validation split, but adapted to pipeline design, per-artifact review, and final motion deliverables.
Semantic difference summary: Mostly cosmetic with extra detail. Both use the same governing principle: users own scope framing, models own validation gates.

### Workflow Routing Tables
- server-manager — Workflows — `/home/nes/projects/server-manager/AGENTS.md` (L35-50)
```text
Pick the workflow that matches the situation. If unclear, ask the user.
| Cue | Workflow |
|-----|----------|
| "What does the server look like?" / audit / inspect | Server Inspection |
| New feature, enhancement, refactor | Implementation & Bug-Fix |
| Something is broken, errors in logs | Bug Investigation (RCA-first) |
| External service is down / bot not responding | Integration Triage |
```
Distinct: Maps operational Discord/server-management cues to implementation, inspection, mutation, research, and deployment workflows.
- videos — Workflows (cue → workflow) — `/home/nes/projects/videos/AGENTS.md` (L67-84)
```text
| Cue | Workflow |
|---|---|
| "Analyse this reference video" / "What happens at t=X?" | Motion Analysis |
| "Critique this motion" / "Is this choreography good?" | Critique |
| "Are my critique's numbers actually right?" | Review Audit (inside Critique) |
| "Plan a new scene" / "Storyboard X" | Planning |
| "Make this look like that" / "Generate X in style Y" | Generation |
```
Distinct: Maps motion-design/user-critique prompts to analysis, critique, planning, generation, HCI review, research, and roadmap work, with a fixed ordering rule when cues overlap.
Semantic difference summary: Mostly cosmetic drift. The structure is the same, but the workflow catalog is domain-specific and `videos` adds precedence ordering.

### Roadmap / Strategy Layers
- server-manager — Product Strategy Workflow — `/home/nes/projects/server-manager/AGENTS.md` (L330-378)
```text
For strategic product decisions, use the alignment loop in
`product-strategy/`. See `product-strategy/orchestrator.md` for the
full process.
**CRITICAL**: Each stage is a SEPARATE sub-agent invocation. Claude Code
acts as the orchestrator, NOT a single mega-agent. Do not collapse the
multi-stage workflow into a single agent.
Pipeline after alignment converges — see
```
Distinct: Full strategic pipeline: market research, executive roadmap, engineering roadmap, AI roadmap, ticket generation, each with risk gates and human checkpoints.
- videos — Roadmap workflow — `/home/nes/projects/videos/AGENTS.md` (L242-259)
```text
Layered, matching `~/projects/server-manager/AGENTS.md` roadmap loop:
| Layer | Output | Risk types |
|---|---|---|
| 0. Market research | target-audience & competitor visual standards | market misread, dependency, completeness |
| 1. Executive roadmap | strategic ordering of mediums / content / UI types | market misread, dependency, completeness |
| 2. Engineering roadmap | pipeline + tooling ordering | feasibility, integration, drift |
| 3. AI roadmap | which agents are worth building, in what order | decomposition, coverage, dependency |
```
Distinct: Condensed adaptation of the same layered roadmap loop for expanding the motion pipeline by medium/content/UI type.
Semantic difference summary: Mostly compression/adaptation. `videos` explicitly inherits the layered idea from `server-manager`, but strips most orchestration detail.

### No Backwards Compatibility
- ai-workflow — No Backwards Compatibility + Forbidden Patterns + When Updating Code — `/home/nes/projects/ai-workflow/AGENTS.md` (L147-151, L152-167, L168-182)
```text
**CRITICAL**: This project has a strict NO BACKWARDS COMPATIBILITY policy.
Always prioritize optimal implementations over legacy support.
Do NOT use any of these backwards-compatibility patterns:
* **Backwards-compatibility shims**: Adapter layers, deprecated aliases, or
  compatibility wrappers
* **Deprecated aliases**: `old_name = new_name  # For backwards compatibility`
* **Version checks**: `if version < 2: use_old_method() else: use_new_method()`
```
Distinct: Turns the policy into a blacklist of forbidden compatibility techniques plus mandatory migration steps.
- server-manager — No Backwards Compatibility — `/home/nes/projects/server-manager/AGENTS.md` (L564-578)
```text
**CRITICAL**: Never introduce backward-compatibility shims, feature
flags for old behavior, transitional code paths, deprecated aliases,
re-exports, or dual support. Ship changes cleanly.
When updating code:
1. Find all usages
2. Update all call sites
3. Delete old code
```
Distinct: Shorter statement of the same principle, with a compact five-step cleanup rule.
Semantic difference summary: Mostly cosmetic-to-moderate drift. The rule is the same; `ai-workflow` just expands it into explicit anti-patterns.

### No Deferred Stubs
- ai-workflow — No Deferred Stubs Without Plan Authorization + Reporting Incomplete Implementation — `/home/nes/projects/ai-workflow/AGENTS.md` (L75-107, L134-146)
```text
**CRITICAL**: Do NOT create placeholder stubs, TODO comments, or deferred
implementations unless the plan explicitly indicates the item is planned
for a later task.
* **Before creating a stub**: Check if the functionality is specified in
  the current task
* **If specified in current task**: Implement it fully, even if it
  requires more effort
```
Distinct: Adds authorized-deferral examples, task-reference requirements, and mandatory incomplete-work reporting.
- server-manager — No Deferred Stubs — `/home/nes/projects/server-manager/AGENTS.md` (L579-586)
```text
Do not create placeholder stubs or TODO comments unless the
implementation plan explicitly indicates the item is planned for a
later task. Implement fully or document what's blocking.
---
```
Distinct: Compact one-paragraph form of the same rule.
Semantic difference summary: Mostly cosmetic-to-moderate drift. Same underlying rule; `ai-workflow` documents the exception and the reporting format in more detail.

### Git / Branch Conventions
- work — Branch Flow + Project branch documentation — `/home/nes/work/AGENTS.md` (L127-138, L139-155)
```text
feat/<name> (worktree) → draft PR → review → main
- **`main`** — protected. All work merges here via reviewed PRs.
- **`feat/<name>`** — feature branches created from `main` in worktrees.
- **`basis/<name>`** — multi-parent basis branches (managed by jj-operator).
- **`integration/<name>`** — temporary integration branches for cross-PR testing.
- **All PRs opened in draft mode.**
When a project spans multiple PRs with dependencies, maintain a tracking
```
Distinct: Focuses on worktree branch topology, basis/integration branches, draft PR flow, and a tracking-table format for multi-PR initiatives.
- ai-workflow — Git Commit Signing + Git Commit Authorship + Git Branch Naming for Linear Integration — `/home/nes/projects/ai-workflow/AGENTS.md` (L208-231, L232-244, L245-260)
```text
All commits are automatically GPG-signed using the configured signing key.
This is required by the repository's branch protection rules.
**Current configuration** (already set globally):
git config --global user.signingkey 2AAAEEBD97F32BFE
git config --global commit.gpgsign true
**Key location**: `~/.gnupg/` (RSA 4096-bit, no passphrase)
**GitHub verification**: The public key must be added to GitHub at
```
Distinct: Focuses on signed commits, no agent attribution, and exact-casing branch names for Linear ticket auto-linking.
- server-manager — Git Conventions — `/home/nes/projects/server-manager/AGENTS.md` (L587-593)
```text
- All work in worktrees — main checkout stays clean
- All PRs opened in draft mode
- GPG-signed commits (key `2AAAEEBD97F32BFE`)
- No Co-Authored-By lines — agents do not add themselves as authors
- Branch naming: `feat/<description>` or `<TICKET-ID>-<description>`
```
Distinct: Compresses worktree, draft PR, signing, authorship, and branch naming into one terse bullet list.
Semantic difference summary: Substantive drift. All are git hygiene sections, but they emphasize different layers: branch topology vs commit identity vs compressed repo-local policy. Also cross-cited in CONTRADICTION C3 because `videos` treats PR pushes as approval-gated Tier 3 actions.

### Infrastructure References
- work — Infrastructure Reference + JIRA / Railway API / AWS Access / Tailscale Network & Self-Hosted Runners — `/home/nes/work/AGENTS.md` (L422-423, L424-495, L496-515, L516-530, L531-545)
```text
Two project boards, each team-managed (next-gen):
| Project | Key | Board | Scope | Issue types (board-visible) |
|---------|-----|-------|-------|-----------------------------|
| Infrastructure | `INFA` | [INFA board (#34)](https://lamaai.atlassian.net/jira/software/projects/INFA/boards/34) | CI/build, deployment, distribution, updater, release pipeline, infra tooling | `Task` (Epics are timeline/backlog only) |
| QA Testing | `KAN` | [KAN board (#1)](https://lamaai.atlassian.net/jira/software/projects/KAN/boards/1) | Frontend UX bugs, product bugs surfaced by QA or E2E, test-side fixes/harmonization, cross-scenario baseline drift | `Bug`, `Feature` |
**Routing rule of thumb:** if a ticket is about how the app *behaves from the user's perspective* or about E2E/QA tests themselves, file in `KAN`. If it is about how the app gets *built, shipped, or kept running* (CI, artifacts, updater, releases, deployment), file in `INFA`. When in doubt, file in the board the person reviewing it lives on.
**Auth:** Basic auth — `$AZURE_EMAIL:$JIRA_API_KEY`
```
Distinct: Large operational appendix with live boards, API endpoints, auth expectations, cloud accounts, runner hosts, and shell snippets.
- server-manager — Infrastructure Reference + Discord / Hosting — `/home/nes/projects/server-manager/AGENTS.md` (L515-516, L517-523, L524-529)
```text
| Item | Value |
|------|-------|
| Guild ID | `960634531159896064` |
| Guild name | Humility |
Platform decisions will be recorded in `DECISIONS.md` as they are made.
---
```
Distinct: Much smaller appendix: guild identity plus a placeholder hosting decision note.
Semantic difference summary: Substantive drift. The shared pattern is an ops/reference appendix, but the content is almost entirely project-specific.

### Global Constraints
- work — Global Constraints — `/home/nes/work/AGENTS.md` (L546-552)
```text
- **`rfqautomation-linux/` stays on `main`** — all work in worktrees
- **All PRs opened in draft mode**
- **Cloud stack is Railway (compute) + Supabase (database)** — separate services, not AWS
- **MVP targets 10 users** — defer anything not needed at that scale
- **Never introduce required env vars for on-prem** — customers auto-update and don't modify `.env`. Hardcode defaults; env vars override, not define.
```
Distinct: Top-level non-negotiables about worktrees, draft PRs, cloud stack, MVP scale, and on-prem env-var policy.
- videos — Global constraints — `/home/nes/projects/videos/AGENTS.md` (L352-372)
```text
- **Motion is data.** Numeric signals are authoritative; still frames
  are supporting evidence only.
- **No super-agents.** Coordinator / researcher split when a question
  spans multiple topics.
- **No compatibility shims.** Pipelines ship clean.
- **Per-medium risk is additive.** UI work = base three risks + UI
  motion risk. Sprite work = base three + sprite risk. Etc.
```
Distinct: Top-level non-negotiables about motion-as-data, no super-agents, additive per-medium risk, reduced motion, and temple-brawl regression checks.
Semantic difference summary: Substantive drift. Both are non-negotiable bullet lists, but the actual constraints live at completely different layers.

### Tiered Approval Safety
- server-manager — The Live Server Principle + Mutation Safety Workflow — `/home/nes/projects/server-manager/AGENTS.md` (L18-34, L232-244)
```text
This project operates on a live Discord server with real users.
Every action falls into one of three tiers:
| Tier | Examples | Authorization |
|------|----------|---------------|
| 1 — Read | List channels, read messages, fetch member list, inspect roles | Always allowed |
| 2 — Confined write | Create/edit files locally, commit to git, run tests | Always allowed |
| 3 — Visible write | Send messages, create channels, modify roles, kick/ban, change permissions | **Requires explicit per-action user approval** unless a runbook has been pre-authorized in `DECISIONS.md` |
```
Distinct: Defines the three-tier safety model for a live Discord guild, then gives the step-by-step reversal/approval/verify cycle for user-visible actions.
- videos — Tier safety — `/home/nes/projects/videos/AGENTS.md` (L51-66)
```text
Motion work is authored locally, so most actions are Tier 2 (confined
write). A small number are Tier 3:
| Tier | Examples | Authorization |
|---|---|---|
| 1 — Read | Read video, read pose.npz, read project files | Always |
| 2 — Confined write | Generate SVGs, render videos, write review docs | Always |
| 3 — Visible write | Publish to a landing page, deploy to a web app, email-ready HTML, push a PR | Explicit per-action approval |
```
Distinct: Reuses the same three-tier shape for motion-pipeline publishing, deployment, and PR pushes.
Semantic difference summary: Substantive drift. Same approval model, but `server-manager` adds a full mutation workflow and `videos` broadens Tier 3 to cover PR pushes/publishing. Also cross-cited in CONTRADICTION C3.

## PROJECT_SPECIFIC
### /home/nes/work/AGENTS.md
- L1-7 "Work Folder — Agent Instructions" — Defines the coordinating role of the `~/work/` repo: planning, task packaging, worktree management, and project state tracking rather than direct code implementation. Generalizable? N — project identity and repo-local operating role.
- L8-15 "Cross-session work log — READ FIRST" — ~/work/rfqautomationlinux/WORKLOG.md (gitignored) holds crosssession context that used to live in the disabled memory tool: user feedback to apply going forward, decisions on open questions, pointers to active Generalizable? Y — reusable cross-session context-log pattern.
- L16-22 "Specialist Agents" — Procedural knowledge lives in ~/work/agents/.md. Read the agent file and pass its content as the prompt when spawning a subagent via the Claude Code Agent tool. The subagent gets full procedure incontext Generalizable? Y — reusable operator-library/index pattern.
- L23-50 "Routing Table" — Cue-to-operator dispatch table for the `~/work/agents/*.md` library, including E2E, QA, worktree, JIRA, PR review, release, and coverage roles. Generalizable? Y — reusable routing-table pattern for specialist agents.
- L51-57 "How to Invoke" — 1. Read the agent file: Read ~/work/agents/<agent.md 2. Construct a prompt combining the agent file content + dynamic context (branch names, paths, specific task) 3. Spawn via Agent tool with the combined prompt Generalizable? Y — reusable operator invocation pattern.
- L58-63 "When NOT to Delegate" — Quick singlecommand operations (e.g., git worktree list) — just run them directly Reading/inspecting files — use Read/Grep directly Ambiguous requests — clarify with the user first, then delegate Generalizable? Y — reusable delegation-boundary rule.
- L64-90 "Active Projects" — Live initiative matrix with JIRA tickets, status, locations, and dependencies across the RFQ platform portfolio. Generalizable? N — live portfolio snapshot tied to one project set. STALE? live initiative statuses, PR numbers, and dependency notes will drift quickly.
- L91-100 "uv/pip packaging migration" — Current planning snapshot for the uv/pip packaging migration, including blocked design questions and a high-risk assessment. Generalizable? N — initiative-specific planning status. STALE? risk/status snapshot for one migration initiative.
- L282-287 "Workflow Step Reporting & Review" — Multistep workflows must state each concrete action as it is performed (not summaries), and a separate reviewer agent verifies compliance against the operator's procedure after the workflow finishes. → see agents/workflo Generalizable? Y — reusable workflow-audit/reporting convention.
- L387-400 "Running in Background" — Use the Claude Code Agent tool with runinbackground: true. Do NOT use while pgrep loops — you will be notified when the agent completes. For file output from background bash commands, write the wrapper inside the worktre Generalizable? Y — reusable background-run convention.
- L401-406 "File naming for prompts, responses, and wrappers" — Pipeline scratch (prompts, responses, wrapper scripts, perphase outputs) lives inside the worktree — never bare in /tmp/ — to prevent crosssession filename collisions that have previously shipped bad work to background a Generalizable? Y — reusable scratch-file naming convention.
- L411-421 "Adding Tasks" — Naming/location rules for adding new planning tasks under the `planning/` tree. Generalizable? Y — reusable task-indexing convention.

### /home/nes/projects/agent-implementation-skill/AGENTS.md
- L1-2 "Agent-Implementation-Skill" — Repository identity header for the agent-implementation-skill codebase. Generalizable? N — repo identity header.
- L167-172 "Cleanup Backlog" — Backlog pointer for structural cleanup work discovered during the repo reorganization. Generalizable? Y — reusable cleanup-backlog pattern for large refactors.
- L173-184 "Governance Documents" — Governance-document inventory covering problems, patterns, risk register, philosophy, and system synthesis. Generalizable? Y — reusable governance-artifact pattern.
- L185-193 "Working with Governance Docs" — Before proposing code changes: Check governance/patterns/index.md for applicable patterns Before creating new artifacts: Check governance/problems/index.md for the problem being solved Pattern violations: Must propose a  Generalizable? Y — reusable governance-usage convention.
- L194-197 "Audit Cycle: Handling New Responses" — Entrypoint for the “New response up” audit round that fans into the seven concrete maintenance steps below. Generalizable? Y — reusable audit-round entrypoint.
- L198-204 "Step 1: Read Inputs" — Read in parallel: ~/work/tmp/executionphilosophy/response.md — the new audit response governance/audit/history.md — full cycle history for cycle detection Generalizable? Y — reusable audit-step pattern.
- L205-214 "Step 2: Assess Violations" — For each violation in the response, check audit history: Cycle — the exact fix was already tried in a prior round and reverted or dismissed. Do NOT reimplement. Note the round numbers. False positive — the "violation" de Generalizable? Y — reusable audit-step pattern.
- L215-226 "Step 3: Implement" — For each nondismissed violation, make the minimal code change that resolves it. Consult governance/patterns/index.md for applicable patterns. Key patterns: PAT0001 (Corruption Preservation): malformed JSON → renamemalfor Generalizable? Y — reusable audit-step pattern.
- L227-235 "Step 4: Run Tests" — cd /home/nes/projects/agentimplementationskill uv run python m pytest x q Fix any failures before proceeding. Generalizable? Y — reusable audit-step pattern.
- L236-246 "Step 5: Commit and Push" — cd /home/nes/projects/agentimplementationskill git add A git commit m "feat(audit): Round N — <summary" Generalizable? Y — reusable audit-step pattern.
- L247-259 "Step 6: Update Audit History" — Edit governance/audit/history.md: 1. Perround index table — add row: | N | <sha7 | <test count | <violation count | <summary | 2. Active Concern Threads — update threads this round progressed Generalizable? Y — reusable audit-step pattern.
- L260-267 "Step 7: Update Governance Artifacts" — If the round's changes affect governance: New patterns discovered → update governance/patterns/index.md Problems resolved or evolved → update governance/problems/index.md Generalizable? Y — reusable audit-step pattern.
- L268-279 "Step 8: Rezip Codebase" — Delete the old zip and recreate: cd /home/nes/projects/agentimplementationskill rm f ~/work/tmp/executionphilosophy/codebase.zip Generalizable? Y — reusable packaging/hand-off pattern.
- L280-285 "Agentic Eval QA Process" — Endtoend behavioral testing of the multiagent workflow system. Evals preseed realistic workspace state, trigger real workflows with QA interception, and validate outcomes with structural checks + an LLM judge. Generalizable? Y — reusable agentic-eval workflow.
- L286-306 "Running Evals" — cd /home/nes/projects/agentimplementationskill List all scenarios uv run agenticevals list Generalizable? Y — reusable eval-run command pattern.
- L307-317 "Eval Flow" — 1. Seed — isolated temp planspace/codespace from fixture files, parameters.json with qamode: true autoinjected 2. Trigger — run real workflow entry points (readiness gate, dispatcher, scan, Generalizable? Y — reusable eval lifecycle pattern.
- L318-332 "Investigating Failures" — When evals expose behavioral gaps: 1. Observe and report — document the exact failure from the eval report 2. Dispatch investigation agents — use agents model gpthigh file <prompt.md Generalizable? Y — reusable failure-investigation workflow.
- L333-343 "Important Rules" — QA mode is mandatory — all eval runs use qamode: true so dispatched agents are intercepted, not live Observe, report, stop — when monitoring an eval: do NOT manually write artifacts Generalizable? Y — reusable eval-guardrail rules.
- L344-355 "Current Wave 1 Results (7 scenarios)" — Current Wave 1 Results (7 scenarios) Generalizable? N — time-sensitive results snapshot. STALE? eval results snapshot (“Current Wave 1 Results”) is inherently time-sensitive.
- L356-367 "Files" — Artifact/path index for the agentic eval harness, judge agent, temp investigation folder, and current design prompt. Generalizable? Y — reusable artifact-index pattern.
- L368-375 "Cycle Detection Reference" — Common dismissal patterns from history: Tests / pyproject.toml absent from zip — tests/ included in bundle as of R118. pyproject.toml ships under src/. Model names in models.md — gpt5.4high and gpt5.4xhigh are current na Generalizable? Y — reusable cycle-detection reference pattern.
- L376-388 "Files" — Artifact/path index for the audit-response bundle, zip file, audit prompt, history, and governance catalogs. Generalizable? Y — reusable artifact-index pattern.
- L426-433 "Open Design: Blocker Resolution Phase" — ~/work/tmp/executionphilosophy/blockerresolutiondesign.md — Design document for the blocker resolution phase and postimplementation verification/testing system. QA runs 89 revealed that sections blocked at the readiness  Generalizable? Y — general blocker-resolution design pattern.
- L434-437 "System Visualization" — We are currently building visual representations of the system so a human can review what was built and validate that the right thing exists. Two locations are involved: Generalizable? Y — reusable system-visualization pattern.
- L438-453 "Diagrams" — executionphilosophy/diagrams/ — Mermaid/diagram source files representing the system. Contains generate.py for rendering, .map files (codemap, lifemap), agent definitions, tools, and a site/ output directory. These diagr Generalizable? Y — reusable diagram-generation/serve pattern.
- L454-459 "Visual Code Editor" — ~/projects/visualcodeeditor — A separate project used to render and interact with the system diagrams. Currently under active development (bug fixing and feature work) to support the visualization effort. The editor is t Generalizable? N — project-local dependency pointer.
- L460-464 "Bug Triage: Where to Fix" — Diagram content issues (wrong labels, missing nodes, incorrect connections, data representing agentimplementationskill) → fix in executionphilosophy/diagrams/ (this repo) Visualization bugs (edge rendering, card highligh Generalizable? Y — reusable cross-repo bug-triage rule.

### /home/nes/projects/agent-runner/AGENTS.md
- L1-2 "Oulipoly Plane — Agent Entry Point" — Repository identity header for Oulipoly Plane. Generalizable? N — repo identity header.
- L3-13 "What This Is" — Oulipoly Plane is a desktop control plane for AI coding agent CLIs (Claude, Codex, Gemini, OpenCode). It handles discovery, configuration, load balancing, and monitoring. Built with Tauri v2 (Rust backend) + Generalizable? N — product identity/mission statement.
- L14-25 "Tech Stack" — Product-local tech-stack table covering Rust/Tauri, SolidJS, Ark UI, Tailwind, FontAwesome, Vitest, Playwright, and Bun. Generalizable? N — stack snapshot tied to this product.
- L26-31 "Design System: Ollie" — Brand-system section for the Ollie mascot, its aesthetic, and associated UI language. Generalizable? N — brand-specific design system.
- L32-40 "Brand Colors (from Ollie's body)" — Exact brand color tokens derived from the Ollie mascot artwork. Generalizable? N — brand-specific color tokens.
- L41-47 "Integrated Components" — Inventory of shipped mascot/spinner components tied to the Oulipoly brand. Generalizable? N — brand-specific component inventory.
- L48-57 "CSS Animations (in `src/app.css`)" — Specific CSS keyframes used by the app’s mascot/spinner presentation layer. Generalizable? N — brand-specific animation inventory.
- L58-64 "Color Token Migration: COMPLETE" — Completion note for the color-token migration from hardcoded hex values to theme tokens. Generalizable? N — status note for one migration.
- L89-94 "Model Naming Convention" — Models use group~facet format (e.g., claude~high, codex~low). The ~ separator triggers grouping in the UI via src/lib/grouping.ts. Standalone models without ~ render as single entries. Generalizable? Y — reusable model-naming convention.
- L152-153 "Design Workflow" — Marker section introducing the external design-package workflow used outside the repo. Generalizable? Y — reusable design-workflow pattern.
- L154-188 "External Design Directory" — Location: ~/work/tmp/oulipolye2e/ This directory contains all design work, organized as packages for an external design model (LLM that generates SVGs, animations, CSS). It is Generalizable? Y — reusable external-design workspace pattern.
- L189-200 "How Design Packages Work" — Each package is a focused ask for the design model (a separate LLM). A package contains: brief.md — what's needed, constraints, references Generalizable? Y — reusable design-package packaging rule.
- L201-207 "Designer Tendencies to Steer Away From" — 1. Chatlog/conversational UI — app is NOT a chat interface 2. Sidebar navigation — app does too few things for persistent nav 3. Fullpage redesigns — designer drops detail at page scale Generalizable? Y — reusable negative-prompt/design-anti-pattern checklist.
- L208-219 "Design Deliverables Already Received" — Status inventory of design HTML mockups already delivered by the external design model. Generalizable? N — delivered-assets inventory.
- L220-234 "Remaining TODO(design) Comments" — Per-file list of remaining UI areas that still need dedicated design work. Generalizable? N — current backlog snapshot.
- L235-248 "UX Direction: Task-Centric Home Screen" — Proposed product-direction change from a configuration-first landing view to a task-centric home screen. Generalizable? N — product-direction decision specific to this app.
- L249-268 "Commands" — Development bun run dev Start Vite dev server (frontend only) cargo tauri dev Start full Tauri app (frontend + backend) Generalizable? Y — reusable repo command appendix.
- L288-295 "E2E Test Infrastructure" — Tests use a Tauri mock builder that injects fake window.TAURIINTERNALS via page.addInitScript(). See e2e/fixtures/taurimock.ts for the mock builder and e2e/fixtures/scenarios.ts for prebuilt mock configurations. Generalizable? Y — reusable Tauri/Playwright E2E mock pattern.

### /home/nes/projects/ai-workflow/AGENTS.md
- L1-16 "AI Agent Entry Point" — Repository-wide entrypoint that forbids searching for other AGENTS files and pushes agents toward linked documentation modules. Generalizable? N — repo identity + local file-discovery rule.
- L17-31 "Documentation Modules" — Index of documentation modules (`usage`, `development`, `testing`, `architecture`, `processes`) used as the primary guidance surface. Generalizable? Y — reusable documentation-module/index pattern.
- L32-35 "How To Run And Understand Python Tests Correctly" — [docs/testing/pythontests.md](docs/testing/pythontests.md) Generalizable? Y — reusable link-out to test execution docs.
- L36-39 "How To Generate OpenAPI Schema (app/)" — [docs/development/generateopenapi.md](docs/development/generateopenapi.md) Generalizable? Y — reusable link-out to OpenAPI generation docs.
- L40-47 "How To Execute Python Tools Correctly" — Do not invoke python or python3 directly outside uv run. Always use uv run <entrypoint for modules that have entry points defined in pyproject.toml (e.g., uv run agents, uv run spec, uv run lint). Generalizable? Y — reusable Python-tool execution convention.
- L48-52 "How To Write Documentation Correctly" — When documenting Python commands in markdown files, toml files, or README files, always use the uv run <entrypoint pattern for project modules. Generalizable? Y — reusable documentation-command convention.
- L53-56 "How To Add Python Dependencies Correctly" — [docs/development/addingdependencies.md](docs/development/addingdependencies.md) Generalizable? Y — reusable link-out to dependency-addition docs.
- L57-60 "How To Add Models Correctly" — [docs/development/addingmodels.md](docs/development/addingmodels.md) Generalizable? Y — reusable link-out to model-addition docs.
- L61-64 "How To Write Agents Correctly" — [docs/development/writingagents.md](docs/development/writingagents.md) Generalizable? Y — reusable link-out to agent-authoring docs.
- L65-68 "How To Execute Agents Correctly" — [docs/development/executingagents.md](docs/development/executingagents.md) Generalizable? Y — reusable link-out to agent-execution docs.
- L69-74 "Plan Execution Guidelines" — High-level rule that planned implementation work must be executed completely and consistently against `docs/plans/`. Generalizable? Y — reusable plan-execution meta-rule.
- L183-188 "External Repositories" — Explains the `.repositories/` cache of cloned external repos used by root tooling. Generalizable? N — repo-local filesystem convention.
- L189-207 "External Resources" — When stuck on implementation details, library usage, or unfamiliar patterns, use the Firecrawl MCP tools to search the web for documentation and examples: Generalizable? Y — reusable external-research/tooling convention.

### /home/nes/projects/server-manager/AGENTS.md
- L1-8 "AGENTS.md — Humility Discord Server Project" — Repository identity header for the Humility Discord server-management project. Generalizable? N — repo identity header.
- L9-17 "Project" — Project overview with the Humility guild ID and long-term daemon/orchestrator goal. Generalizable? N — project-specific guild identity and mission.
- L111-118 "Implementation Workflow — Test/Code Agent Separation" — Explicit rule that test writing and code writing must happen in separate agent invocations. Generalizable? Y — reusable contract-test/code-writer separation pattern.
- L119-143 "Per-feature PR workflow" — Step-by-step contract → tests → code → verify → review flow for feature PRs. Generalizable? Y — reusable per-feature PR implementation sequence.
- L144-154 "Optimistic locking in tests" — Contract-level optimistic-locking expectations that tests must encode for versioned entities. Generalizable? Y — reusable optimistic-locking test rule.
- L197-205 "Bug Investigation Workflow (RCA-First)" — RCA-first bug triage entrypoint that feeds investigation output back into the implementation pipeline. Generalizable? Y — reusable RCA-entry workflow.
- L206-215 "Server Inspection Workflow" — Read-only inspection workflow for Discord server state and expected-vs-actual comparisons. Generalizable? N — Discord-specific inspection workflow.
- L216-231 "Integration Triage Workflow" — Outage triage flow for unresponsive bots or external services, from status check through post-mortem. Generalizable? Y — reusable external-service triage pattern.
- L257-269 "Deployment Workflow" — Infra-change workflow covering proposal, risk, dry run, execution, verification, and documentation. Generalizable? Y — reusable deployment-change workflow.
- L270-293 "Prototyping Workflow" — Discovery-first prototyping pipeline for high-uncertainty slices; prototype code is disposable and never shipped. Generalizable? Y — reusable prototyping workflow.
- L294-329 "Writing Pipeline" — Public-document writing quality system with content revision, rubric passes, quality gate, and PDF render. Generalizable? Y — reusable multi-agent writing-quality workflow.
- L483-489 "API-First Design Rule" — Architecture rule stating that both human UI and agent API are first-class clients of the same structured API surface. Generalizable? Y — reusable API-first architecture rule.
- L490-514 "Key Patterns from References" — Imported patterns from `ai-workflow`, `java-interview-setup`, and `ui-designer` that shape this repo’s service architecture and tooling choices. Generalizable? Y — reusable borrowed-pattern/reference section.

### /home/nes/projects/videos/AGENTS.md
- L1-33 "AGENTS.md — visual motion pipeline" — Repository identity/status header for the visual-motion pipeline, including research status and two first-class rules. Generalizable? N — repo identity/status snapshot.
- L34-50 "What this pipeline is NOT" — Anti-scope list defining what the motion pipeline is explicitly not meant to do. Generalizable? Y — reusable anti-scope template.
- L85-103 "Motion Analysis workflow" — Numeric-signal workflow for deriving motion timelines and event artifacts from a reference or draft. Generalizable? Y — reusable motion-analysis workflow.
- L104-120 "Critique workflow" — Review workflow that splits choreography/composition/HCI critique from review-audit validation. Generalizable? Y — reusable critique-and-audit workflow.
- L121-141 "Planning workflow" — Phase-by-phase planning workflow from brief to final deliverable, with repeated risk gates. Generalizable? Y — reusable staged planning workflow.
- L142-169 "3× risk gate (applies at every gate in phases 3–8)" — Definition of the core 3× risk gate plus medium-specific add-on risk classes for motion work. Generalizable? Y — reusable multi-axis risk-gate pattern.
- L170-186 "Generation workflow" — Generation workflow for new raster/video/SVG outputs, including self-review and bounded regeneration. Generalizable? Y — reusable generation/self-review loop.
- L187-206 "HCI Review workflow (UI work only)" — HCI review rubric for UI motion, with WCAG/platform/performance source expectations. Generalizable? Y — reusable HCI-review rubric pattern.
- L295-351 "Artifact naming" — Per-project folder/schema for policies, references, plans, reviews, keyframes, composites, finals, and risk artifacts. Generalizable? Y — reusable artifact-layout pattern.
- L373-417 "Sub-AGENTS.md documents `[PLANNED]`" — Planned decomposition of the motion rules into medium-, content-, and UI-subtype sub-AGENTS documents. Generalizable? Y — reusable sub-document decomposition pattern. STALE? marked `[PLANNED]`, but `Open items` later says 17 sub-AGENTS craft-rule docs already exist.
- L442-488 "Open items" — Project status section listing what has landed and what still remains to run or wire up. Generalizable? N — status/backlog snapshot. STALE? explicit done/to-do snapshot.

### /home/nes/projects/visual-code-editor/AGENTS.md
- L1-2 "Visual Code Editor — Agent Workflows" — Repository identity header for the visual code editor. Generalizable? N — repo identity header.
- L3-11 "Project Context" — Project overview describing the editor as an interactive system-visualization and drill-down/detail-panel UI. Generalizable? N — product-specific project overview.
- L12-19 "Technology Stack" — SolidJS + TanStack Solid Router — reactive UI framework ELK.js — graph layout engine (layered algorithm with orthogonal edge routing) Custom SVG/HTML rendering — nodes as HTML cards, edges as SVG paths in layered composi Generalizable? N — stack snapshot tied to this app.
- L20-32 "Current Visual State (as of 2026-04-15)" — Point-in-time summary of animation/UI fixes already landed as of 2026-04-15. Generalizable? N — dated status snapshot.
- L33-36 "Known remaining items" — Short list of remaining known issues after the recent animation QA pass. Generalizable? N — dated/local backlog note.
- L37-46 "Dual-View Problem" — Specific UX problem statement about cards that need both drill-down and detail-panel affordances. Generalizable? Y — general UI/interaction-design problem pattern.
- L47-50 "Visual Asset Pipeline" — Top-level rule that all visual assets are version-controlled SVGs under `app/assets/`. Generalizable? Y — reusable visual-asset pipeline rule.
- L62-72 "SVG Requirements" — All SVGs must: Use currentColor for text/icon fills (inherits from CSS) Use CSS custom properties (var(border), var(accent), etc.) where possible Generalizable? Y — reusable SVG authoring requirements.
- L97-118 "SVG Self-Correcting Loop" — Gemini-specific visual review loop for SVG generation using SVG→PNG conversion and iterative inspection. Generalizable? Y — reusable SVG self-correction loop.
- L119-122 "Animation Pipeline" — Animation-system heading introducing parameterization, interpolation, and selection work. Generalizable? Y — reusable animation-system design pattern.
- L123-130 "Animation Types" — 1. Card hover — lift, float, settle (currently CSS transitions + JS spring physics) 2. Diagram transitions — crossfade between diagrams when navigating 3. Edge flow — animated dashes showing data/control flow direction Generalizable? Y — reusable animation taxonomy.
- L131-159 "Animation Design Process" — 1. Design (geminihigh): Describe the interaction context. Gemini proposes animation parameters: Easing curves (cubicbezier values) Duration and delay Generalizable? Y — reusable animation design workflow.
- L171-198 "Research Areas" — 1. Interactive graph visualization UX — How do tools like Figma, Miro, Lucidchart, GitHub dependency graphs handle: Node type differentiation (visual, not just color) Drilldown vs detail split (cards that are both contai Generalizable? Y — reusable research-prompt checklist.
- L199-202 "Animation QA Workflow" — Semantic animation QA workflow built from Playwright video capture plus Gemini video review. Generalizable? Y — reusable semantic animation-QA workflow.
- L203-208 "How It Works" — 1. Capture: Playwright records short video clips of specific animations/interactions 2. Judge: agents model geminivideohigh analyzes the video against expected behavior described in the prompt 3. Human review: Human read Generalizable? Y — reusable capture→judge→human-review loop.
- L209-222 "Running Captures" — Build and serve first cd ~/projects/visualcodeeditor npm run build && npm run serve & Generalizable? Y — reusable Playwright capture command pattern.
- L223-237 "Sending to Gemini for QA" — Reference the video file in the prompt — geminivideohigh can read video files agents model geminivideohigh p ~/projects/visualcodeeditor \ "Review the animation video at .tmp/animationqa/captures/<dir/<file.webm Generalizable? Y — reusable multimodal-review dispatch pattern.
- L238-244 "Capture Specs" — Capture Specs Generalizable? Y — reusable capture inventory pattern.
- L245-254 "When to Run" — Before/after animation or interaction changes When investigating visual bugs For prereview QA on motionheavy PRs Generalizable? Y — reusable QA-trigger checklist.
- L269-292 "Build & Verify" — Local build/regenerate/preview/Playwright verification checklist for visual changes. Generalizable? Y — reusable build/verify checklist for visual changes. STALE? says “Then send captures to gemini-high for analysis,” but the earlier Animation QA section says only `gemini-video-high` can process video files.
- L293-301 "Cross-Project References" — Local path pointers into the diagram source repo, SVG conversion script, and parent AGENTS files. Generalizable? N — repo-local path/reference appendix.
- L302-319 "Visual Regression" — Pixel-baseline workflow for visual regression testing, including local harness use and snapshot update guidance. Generalizable? Y — reusable visual-regression workflow.
- L320-331 "CI (GitHub Actions)" — GitHub Actions recipe for the visual-regression workflow and the CI-based rebaseline path. Generalizable? Y — reusable CI rebaseline pattern.
- L332-335 "Known limits" — Known limitations of the visual-regression harness and icon/font stability strategy. Generalizable? N — tooling-specific known-limit notes.

## CONTRADICTION ⚠️
### C1. Delegation Mechanism: Built-In Task Tool vs `agents` CLI
- ai-workflow — `/home/nes/projects/ai-workflow/AGENTS.md` (L108-133)
```text
For plans with many requirements, the primary agent should:
1. **Save the plan to `.tmp/`**: Split the plan into numbered task files
2. **Delegate to sub-agents**: Use the `Task` tool with
   `subagent_type="general-purpose"` to delegate individual tasks
3. **Review each completion**: After each sub-agent returns, verify the task
   was fully implemented before proceeding to the next task
```
- work — `/home/nes/work/AGENTS.md` (L288-291)
```text
Sub-agents are invoked via the `agents` binary (`~/.local/bin/agents`), not through Claude Code's built-in Agent tool. The binary is the CLI mode of Oulipoly Agent Runner.
```
- agent-implementation-skill — `/home/nes/projects/agent-implementation-skill/AGENTS.md` (L29-32)
```text
Sub-agents are invoked via the `agents` binary (`~/.local/bin/agents`), not through Claude Code's built-in Agent tool. The binary is the CLI mode of Oulipoly Agent Runner.
```
Question for user: Should `~/ai/` standardize on the external `agents` CLI, on built-in task/subagent tooling, or document project-level rules for when each is allowed?

### C2. CodeRabbit Loop: Push Policy and Stop Condition
- work — `/home/nes/work/AGENTS.md` (L213-218)
```text
CodeRabbit CLI is step 9 of the implementation pipeline. It iterates until per-pass value drops to zero (typically 3–6 passes), amending a single commit so each pass reviews a clean diff against `main`. The branch is never pushed during the loop.
```
- server-manager — `/home/nes/projects/server-manager/AGENTS.md` (L155-175)
```text
CodeRabbit CLI is a formal stage in the per-feature PR workflow.
One pass is NOT enough — keep rerunning until the review is clean.

`git commit --amend --no-edit`
`git push --force-with-lease`
`coderabbit review --plain --base main --cwd <project-dir>`
```
Question for user: During the CodeRabbit loop, should agents keep the branch local until convergence, or force-push amended commits between passes? And is the stop rule “no more valuable findings” or “report is clean”?

### C3. PR Opening: Routine Automation vs Explicit Approval
- work — `/home/nes/work/AGENTS.md` (L180-212)
```text
| 14. Draft PR(s) | `gh` CLI | **After steps 10, 11, 12, and 13 agree.** Open one or more **draft** PRs against `main`. One PR per concern the reviewers isolated; dependency order. A single-concern change is one PR. |

- Draft-only — all PRs opened by this pipeline are drafts; promotion to "ready for review" is a human decision
```
- server-manager — `/home/nes/projects/server-manager/AGENTS.md` (L587-593)
```text
- All work in worktrees — main checkout stays clean
- All PRs opened in draft mode
- GPG-signed commits (key `2AAAEEBD97F32BFE`)
```
- videos — `/home/nes/projects/videos/AGENTS.md` (L51-66)
```text
| 3 — Visible write | Publish to a landing page, deploy to a web app, email-ready HTML, push a PR | Explicit per-action approval |

Tier-3 rule mirrors `~/projects/server-manager/AGENTS.md` — describe exactly what will happen, wait for explicit yes, no batching.
```
Question for user: Should opening/pushing PRs be treated as a routine autonomous git step, or as a user-visible action that always needs explicit per-action approval?

## Per-source section maps
### /home/nes/work/AGENTS.md
- L1-7 "Work Folder — Agent Instructions" → PROJECT_SPECIFIC (Defines the coordinating role of the `~/work/` repo: planning, task packaging, worktree management, and projec; Generalizable? N)
- L8-15 "Cross-session work log — READ FIRST" → PROJECT_SPECIFIC (~/work/rfqautomationlinux/WORKLOG.md (gitignored) holds crosssession context that used to live in the disabled; Generalizable? Y)
- L16-22 "Specialist Agents" → PROJECT_SPECIFIC (Procedural knowledge lives in ~/work/agents/.md. Read the agent file and pass its content as the prompt when s; Generalizable? Y)
- L23-50 "Routing Table" → PROJECT_SPECIFIC (Cue-to-operator dispatch table for the `~/work/agents/*.md` library, including E2E, QA, worktree, JIRA, PR rev; Generalizable? Y)
- L51-57 "How to Invoke" → PROJECT_SPECIFIC (1. Read the agent file: Read ~/work/agents/<agent.md 2. Construct a prompt combining the agent file content + ; Generalizable? Y)
- L58-63 "When NOT to Delegate" → PROJECT_SPECIFIC (Quick singlecommand operations (e.g., git worktree list) — just run them directly Reading/inspecting files — u; Generalizable? Y)
- L64-90 "Active Projects" → PROJECT_SPECIFIC (Live initiative matrix with JIRA tickets, status, locations, and dependencies across the RFQ platform portfoli; Generalizable? N)
- L91-100 "uv/pip packaging migration" → PROJECT_SPECIFIC (Current planning snapshot for the uv/pip packaging migration, including blocked design questions and a high-ri; Generalizable? N)
- L101-126 "Folder Structure" → SHARED_WITH_DRIFT (Repository Structure Maps)
- L127-138 "Branch Flow" → SHARED_WITH_DRIFT (Git / Branch Conventions)
- L139-155 "Project branch documentation" → SHARED_WITH_DRIFT (Git / Branch Conventions)
- L156-179 "Running External Models" → SHARED_WITH_DRIFT (Agents CLI Entry Points / Sub-Agent Execution)
- L180-212 "Implementation & Bug-Fix Workflow" → SHARED_WITH_DRIFT (Implementation & Bug-Fix Workflow; also cited in C3 (draft PR opening as routine pipeline step))
- L213-218 "CodeRabbit Review Loop" → CONTRADICTION (CodeRabbit loop policy)
- L219-252 "Post-CodeRabbit Review Gates (steps 10 + 11 + 12)" → SHARED_WITH_DRIFT (PR Review / Post-CodeRabbit Gates)
- L253-281 "PR Review Workflow" → SHARED_WITH_DRIFT (PR Review / Post-CodeRabbit Gates)
- L282-287 "Workflow Step Reporting & Review" → PROJECT_SPECIFIC (Multistep workflows must state each concrete action as it is performed (not summaries), and a separate reviewe; Generalizable? Y)
- L288-291 "Running Sub-Agents" → SHARED_WITH_DRIFT (Agents CLI Entry Points / Sub-Agent Execution; also cited in C1 (delegation mechanism))
- L292-309 "CLI Syntax" → SHARED_EXACT (CLI Syntax)
- L310-325 "Common Patterns" → SHARED_WITH_DRIFT (Common Invocation Patterns)
- L326-337 "Agent File Format" → SHARED_WITH_DRIFT (Agent File Format / Agent Skeleton)
- L338-364 "Input Schema" → SHARED_WITH_DRIFT (Input Schema / Runner Input Semantics)
- L365-386 "Multimodal Models" → SHARED_EXACT (Multimodal Models)
- L387-400 "Running in Background" → PROJECT_SPECIFIC (Use the Claude Code Agent tool with runinbackground: true. Do NOT use while pgrep loops — you will be notified; Generalizable? Y)
- L401-406 "File naming for prompts, responses, and wrappers" → PROJECT_SPECIFIC (Pipeline scratch (prompts, responses, wrapper scripts, perphase outputs) lives inside the worktree — never bar; Generalizable? Y)
- L407-410 "Available Models" → SHARED_EXACT (Available Models)
- L411-421 "Adding Tasks" → PROJECT_SPECIFIC (Naming/location rules for adding new planning tasks under the `planning/` tree; Generalizable? Y)
- L422-423 "Infrastructure Reference" → SHARED_WITH_DRIFT (Infrastructure References)
- L424-495 "JIRA" → SHARED_WITH_DRIFT (Infrastructure References)
- L496-515 "Railway API" → SHARED_WITH_DRIFT (Infrastructure References)
- L516-530 "AWS Access" → SHARED_WITH_DRIFT (Infrastructure References)
- L531-545 "Tailscale Network & Self-Hosted Runners" → SHARED_WITH_DRIFT (Infrastructure References)
- L546-552 "Global Constraints" → SHARED_WITH_DRIFT (Global Constraints)

### /home/nes/projects/agent-implementation-skill/AGENTS.md
- L1-2 "Agent-Implementation-Skill" → PROJECT_SPECIFIC (Repository identity header for the agent-implementation-skill codebase; Generalizable? N)
- L3-28 "Project Structure" → SHARED_WITH_DRIFT (Repository Structure Maps)
- L29-32 "Running Sub-Agents" → SHARED_WITH_DRIFT (Agents CLI Entry Points / Sub-Agent Execution; also cited in C1 (delegation mechanism))
- L33-50 "CLI Syntax" → SHARED_EXACT (CLI Syntax)
- L51-69 "Common Invocation Patterns" → SHARED_WITH_DRIFT (Common Invocation Patterns)
- L70-85 "Agent File Format" → SHARED_WITH_DRIFT (Agent File Format / Agent Skeleton)
- L86-111 "Model Configuration" → SHARED_WITH_DRIFT (Model / Command Configuration Semantics)
- L112-138 "Input Schema" → SHARED_WITH_DRIFT (Input Schema / Runner Input Semantics)
- L139-160 "Multimodal Models" → SHARED_EXACT (Multimodal Models)
- L161-166 "Available Models" → SHARED_EXACT (Available Models)
- L167-172 "Cleanup Backlog" → PROJECT_SPECIFIC (Backlog pointer for structural cleanup work discovered during the repo reorganization; Generalizable? Y)
- L173-184 "Governance Documents" → PROJECT_SPECIFIC (Governance-document inventory covering problems, patterns, risk register, philosophy, and system synthesis; Generalizable? Y)
- L185-193 "Working with Governance Docs" → PROJECT_SPECIFIC (Before proposing code changes: Check governance/patterns/index.md for applicable patterns Before creating new ; Generalizable? Y)
- L194-197 "Audit Cycle: Handling New Responses" → PROJECT_SPECIFIC (Entrypoint for the “New response up” audit round that fans into the seven concrete maintenance steps below; Generalizable? Y)
- L198-204 "Step 1: Read Inputs" → PROJECT_SPECIFIC (Read in parallel: ~/work/tmp/executionphilosophy/response.md — the new audit response governance/audit/history; Generalizable? Y)
- L205-214 "Step 2: Assess Violations" → PROJECT_SPECIFIC (For each violation in the response, check audit history: Cycle — the exact fix was already tried in a prior ro; Generalizable? Y)
- L215-226 "Step 3: Implement" → PROJECT_SPECIFIC (For each nondismissed violation, make the minimal code change that resolves it. Consult governance/patterns/in; Generalizable? Y)
- L227-235 "Step 4: Run Tests" → PROJECT_SPECIFIC (cd /home/nes/projects/agentimplementationskill uv run python m pytest x q Fix any failures before proceeding; Generalizable? Y)
- L236-246 "Step 5: Commit and Push" → PROJECT_SPECIFIC (cd /home/nes/projects/agentimplementationskill git add A git commit m "feat(audit): Round N — <summary"; Generalizable? Y)
- L247-259 "Step 6: Update Audit History" → PROJECT_SPECIFIC (Edit governance/audit/history.md: 1. Perround index table — add row: | N | <sha7 | <test count | <violation co; Generalizable? Y)
- L260-267 "Step 7: Update Governance Artifacts" → PROJECT_SPECIFIC (If the round's changes affect governance: New patterns discovered → update governance/patterns/index.md Proble; Generalizable? Y)
- L268-279 "Step 8: Rezip Codebase" → PROJECT_SPECIFIC (Delete the old zip and recreate: cd /home/nes/projects/agentimplementationskill rm f ~/work/tmp/executionphilo; Generalizable? Y)
- L280-285 "Agentic Eval QA Process" → PROJECT_SPECIFIC (Endtoend behavioral testing of the multiagent workflow system. Evals preseed realistic workspace state, trigge; Generalizable? Y)
- L286-306 "Running Evals" → PROJECT_SPECIFIC (cd /home/nes/projects/agentimplementationskill List all scenarios uv run agenticevals list; Generalizable? Y)
- L307-317 "Eval Flow" → PROJECT_SPECIFIC (1. Seed — isolated temp planspace/codespace from fixture files, parameters.json with qamode: true autoinjected; Generalizable? Y)
- L318-332 "Investigating Failures" → PROJECT_SPECIFIC (When evals expose behavioral gaps: 1. Observe and report — document the exact failure from the eval report 2. ; Generalizable? Y)
- L333-343 "Important Rules" → PROJECT_SPECIFIC (QA mode is mandatory — all eval runs use qamode: true so dispatched agents are intercepted, not live Observe, ; Generalizable? Y)
- L344-355 "Current Wave 1 Results (7 scenarios)" → PROJECT_SPECIFIC (Current Wave 1 Results (7 scenarios); Generalizable? N)
- L356-367 "Files" → PROJECT_SPECIFIC (Artifact/path index for the agentic eval harness, judge agent, temp investigation folder, and current design p; Generalizable? Y)
- L368-375 "Cycle Detection Reference" → PROJECT_SPECIFIC (Common dismissal patterns from history: Tests / pyproject.toml absent from zip — tests/ included in bundle as ; Generalizable? Y)
- L376-388 "Files" → PROJECT_SPECIFIC (Artifact/path index for the audit-response bundle, zip file, audit prompt, history, and governance catalogs; Generalizable? Y)
- L389-393 "Implementation & Bug-Fix Workflow" → SHARED_WITH_DRIFT (Implementation & Bug-Fix Workflow)
- L394-405 "Bug Fixes" → SHARED_WITH_DRIFT (Implementation & Bug-Fix Workflow)
- L406-409 "Features / Refactors" → SHARED_WITH_DRIFT (Implementation & Bug-Fix Workflow)
- L410-425 "Principles" → SHARED_WITH_DRIFT (Implementation Principles)
- L426-433 "Open Design: Blocker Resolution Phase" → PROJECT_SPECIFIC (~/work/tmp/executionphilosophy/blockerresolutiondesign.md — Design document for the blocker resolution phase a; Generalizable? Y)
- L434-437 "System Visualization" → PROJECT_SPECIFIC (We are currently building visual representations of the system so a human can review what was built and valida; Generalizable? Y)
- L438-453 "Diagrams" → PROJECT_SPECIFIC (executionphilosophy/diagrams/ — Mermaid/diagram source files representing the system. Contains generate.py for; Generalizable? Y)
- L454-459 "Visual Code Editor" → PROJECT_SPECIFIC (~/projects/visualcodeeditor — A separate project used to render and interact with the system diagrams. Current; Generalizable? N)
- L460-464 "Bug Triage: Where to Fix" → PROJECT_SPECIFIC (Diagram content issues (wrong labels, missing nodes, incorrect connections, data representing agentimplementat; Generalizable? Y)

### /home/nes/projects/agent-runner/AGENTS.md
- L1-2 "Oulipoly Plane — Agent Entry Point" → PROJECT_SPECIFIC (Repository identity header for Oulipoly Plane; Generalizable? N)
- L3-13 "What This Is" → PROJECT_SPECIFIC (Oulipoly Plane is a desktop control plane for AI coding agent CLIs (Claude, Codex, Gemini, OpenCode). It handl; Generalizable? N)
- L14-25 "Tech Stack" → PROJECT_SPECIFIC (Product-local tech-stack table covering Rust/Tauri, SolidJS, Ark UI, Tailwind, FontAwesome, Vitest, Playwright; Generalizable? N)
- L26-31 "Design System: Ollie" → PROJECT_SPECIFIC (Brand-system section for the Ollie mascot, its aesthetic, and associated UI language; Generalizable? N)
- L32-40 "Brand Colors (from Ollie's body)" → PROJECT_SPECIFIC (Exact brand color tokens derived from the Ollie mascot artwork; Generalizable? N)
- L41-47 "Integrated Components" → PROJECT_SPECIFIC (Inventory of shipped mascot/spinner components tied to the Oulipoly brand; Generalizable? N)
- L48-57 "CSS Animations (in `src/app.css`)" → PROJECT_SPECIFIC (Specific CSS keyframes used by the app’s mascot/spinner presentation layer; Generalizable? N)
- L58-64 "Color Token Migration: COMPLETE" → PROJECT_SPECIFIC (Completion note for the color-token migration from hardcoded hex values to theme tokens; Generalizable? N)
- L65-88 "Current UI Architecture" → SHARED_WITH_DRIFT (Repository Structure Maps)
- L89-94 "Model Naming Convention" → PROJECT_SPECIFIC (Models use group~facet format (e.g., claude~high, codex~low). The ~ separator triggers grouping in the UI via ; Generalizable? Y)
- L95-117 "Input Schema System" → SHARED_WITH_DRIFT (Input Schema / Runner Input Semantics)
- L118-151 "Model Command Syntax" → SHARED_WITH_DRIFT (Model / Command Configuration Semantics)
- L152-153 "Design Workflow" → PROJECT_SPECIFIC (Marker section introducing the external design-package workflow used outside the repo; Generalizable? Y)
- L154-188 "External Design Directory" → PROJECT_SPECIFIC (Location: ~/work/tmp/oulipolye2e/ This directory contains all design work, organized as packages for an extern; Generalizable? Y)
- L189-200 "How Design Packages Work" → PROJECT_SPECIFIC (Each package is a focused ask for the design model (a separate LLM). A package contains: brief.md — what's nee; Generalizable? Y)
- L201-207 "Designer Tendencies to Steer Away From" → PROJECT_SPECIFIC (1. Chatlog/conversational UI — app is NOT a chat interface 2. Sidebar navigation — app does too few things for; Generalizable? Y)
- L208-219 "Design Deliverables Already Received" → PROJECT_SPECIFIC (Status inventory of design HTML mockups already delivered by the external design model; Generalizable? N)
- L220-234 "Remaining TODO(design) Comments" → PROJECT_SPECIFIC (Per-file list of remaining UI areas that still need dedicated design work; Generalizable? N)
- L235-248 "UX Direction: Task-Centric Home Screen" → PROJECT_SPECIFIC (Proposed product-direction change from a configuration-first landing view to a task-centric home screen; Generalizable? N)
- L249-268 "Commands" → PROJECT_SPECIFIC (Development bun run dev Start Vite dev server (frontend only) cargo tauri dev Start full Tauri app (frontend +; Generalizable? Y)
- L269-287 "Tauri Backend Structure" → SHARED_WITH_DRIFT (Repository Structure Maps)
- L288-295 "E2E Test Infrastructure" → PROJECT_SPECIFIC (Tests use a Tauri mock builder that injects fake window.TAURIINTERNALS via page.addInitScript(). See e2e/fixtu; Generalizable? Y)

### /home/nes/projects/ai-workflow/AGENTS.md
- L1-16 "AI Agent Entry Point" → PROJECT_SPECIFIC (Repository-wide entrypoint that forbids searching for other AGENTS files and pushes agents toward linked docum; Generalizable? N)
- L17-31 "Documentation Modules" → PROJECT_SPECIFIC (Index of documentation modules (`usage`, `development`, `testing`, `architecture`, `processes`) used as the pr; Generalizable? Y)
- L32-35 "How To Run And Understand Python Tests Correctly" → PROJECT_SPECIFIC ([docs/testing/pythontests.md](docs/testing/pythontests.md); Generalizable? Y)
- L36-39 "How To Generate OpenAPI Schema (app/)" → PROJECT_SPECIFIC ([docs/development/generateopenapi.md](docs/development/generateopenapi.md); Generalizable? Y)
- L40-47 "How To Execute Python Tools Correctly" → PROJECT_SPECIFIC (Do not invoke python or python3 directly outside uv run. Always use uv run <entrypoint for modules that have e; Generalizable? Y)
- L48-52 "How To Write Documentation Correctly" → PROJECT_SPECIFIC (When documenting Python commands in markdown files, toml files, or README files, always use the uv run <entryp; Generalizable? Y)
- L53-56 "How To Add Python Dependencies Correctly" → PROJECT_SPECIFIC ([docs/development/addingdependencies.md](docs/development/addingdependencies.md); Generalizable? Y)
- L57-60 "How To Add Models Correctly" → PROJECT_SPECIFIC ([docs/development/addingmodels.md](docs/development/addingmodels.md); Generalizable? Y)
- L61-64 "How To Write Agents Correctly" → PROJECT_SPECIFIC ([docs/development/writingagents.md](docs/development/writingagents.md); Generalizable? Y)
- L65-68 "How To Execute Agents Correctly" → PROJECT_SPECIFIC ([docs/development/executingagents.md](docs/development/executingagents.md); Generalizable? Y)
- L69-74 "Plan Execution Guidelines" → PROJECT_SPECIFIC (High-level rule that planned implementation work must be executed completely and consistently against `docs/pl; Generalizable? Y)
- L75-107 "No Deferred Stubs Without Plan Authorization" → SHARED_WITH_DRIFT (No Deferred Stubs)
- L108-133 "Task Decomposition for Complex Plans" → CONTRADICTION (Delegation tool choice)
- L134-146 "Reporting Incomplete Implementation" → SHARED_WITH_DRIFT (No Deferred Stubs)
- L147-151 "No Backwards Compatibility" → SHARED_WITH_DRIFT (No Backwards Compatibility)
- L152-167 "Forbidden Patterns" → SHARED_WITH_DRIFT (No Backwards Compatibility)
- L168-182 "When Updating Code" → SHARED_WITH_DRIFT (No Backwards Compatibility)
- L183-188 "External Repositories" → PROJECT_SPECIFIC (Explains the `.repositories/` cache of cloned external repos used by root tooling; Generalizable? N)
- L189-207 "External Resources" → PROJECT_SPECIFIC (When stuck on implementation details, library usage, or unfamiliar patterns, use the Firecrawl MCP tools to se; Generalizable? Y)
- L208-231 "Git Commit Signing" → SHARED_WITH_DRIFT (Git / Branch Conventions)
- L232-244 "Git Commit Authorship" → SHARED_WITH_DRIFT (Git / Branch Conventions)
- L245-260 "Git Branch Naming for Linear Integration" → SHARED_WITH_DRIFT (Git / Branch Conventions)

### /home/nes/projects/server-manager/AGENTS.md
- L1-8 "AGENTS.md — Humility Discord Server Project" → PROJECT_SPECIFIC (Repository identity header for the Humility Discord server-management project; Generalizable? N)
- L9-17 "Project" → PROJECT_SPECIFIC (Project overview with the Humility guild ID and long-term daemon/orchestrator goal; Generalizable? N)
- L18-34 "The Live Server Principle" → SHARED_WITH_DRIFT (Tiered Approval Safety)
- L35-50 "Workflows" → SHARED_WITH_DRIFT (Workflow Routing Tables)
- L51-67 "Implementation & Bug-Fix Workflow" → SHARED_WITH_DRIFT (Implementation & Bug-Fix Workflow)
- L68-81 "Principles" → SHARED_WITH_DRIFT (Implementation Principles)
- L82-110 "Gate ownership per phase" → SHARED_WITH_DRIFT (Gate Ownership / When To Ask The User)
- L111-118 "Implementation Workflow — Test/Code Agent Separation" → PROJECT_SPECIFIC (Explicit rule that test writing and code writing must happen in separate agent invocations; Generalizable? Y)
- L119-143 "Per-feature PR workflow" → PROJECT_SPECIFIC (Step-by-step contract → tests → code → verify → review flow for feature PRs; Generalizable? Y)
- L144-154 "Optimistic locking in tests" → PROJECT_SPECIFIC (Contract-level optimistic-locking expectations that tests must encode for versioned entities; Generalizable? Y)
- L155-175 "CodeRabbit Review Loop" → CONTRADICTION (CodeRabbit loop policy)
- L176-196 "PR Review Workflow" → SHARED_WITH_DRIFT (PR Review / Post-CodeRabbit Gates)
- L197-205 "Bug Investigation Workflow (RCA-First)" → PROJECT_SPECIFIC (RCA-first bug triage entrypoint that feeds investigation output back into the implementation pipeline; Generalizable? Y)
- L206-215 "Server Inspection Workflow" → PROJECT_SPECIFIC (Read-only inspection workflow for Discord server state and expected-vs-actual comparisons; Generalizable? N)
- L216-231 "Integration Triage Workflow" → PROJECT_SPECIFIC (Outage triage flow for unresponsive bots or external services, from status check through post-mortem; Generalizable? Y)
- L232-244 "Mutation Safety Workflow" → SHARED_WITH_DRIFT (Tiered Approval Safety)
- L245-256 "Research Workflow" → SHARED_WITH_DRIFT (Research Workflow)
- L257-269 "Deployment Workflow" → PROJECT_SPECIFIC (Infra-change workflow covering proposal, risk, dry run, execution, verification, and documentation; Generalizable? Y)
- L270-293 "Prototyping Workflow" → PROJECT_SPECIFIC (Discovery-first prototyping pipeline for high-uncertainty slices; prototype code is disposable and never shipp; Generalizable? Y)
- L294-329 "Writing Pipeline" → PROJECT_SPECIFIC (Public-document writing quality system with content revision, rubric passes, quality gate, and PDF render; Generalizable? Y)
- L330-378 "Product Strategy Workflow" → SHARED_WITH_DRIFT (Roadmap / Strategy Layers)
- L379-387 "Model Roles" → SHARED_WITH_DRIFT (Model Roles / No-Super-Agent Boundary)
- L388-416 "No Super Agents" → SHARED_WITH_DRIFT (Model Roles / No-Super-Agent Boundary)
- L417-451 "Running Sub-Agents" → SHARED_WITH_DRIFT (Agents CLI Entry Points / Sub-Agent Execution)
- L452-482 "Architecture (Three Services)" → SHARED_WITH_DRIFT (Repository Structure Maps)
- L483-489 "API-First Design Rule" → PROJECT_SPECIFIC (Architecture rule stating that both human UI and agent API are first-class clients of the same structured API ; Generalizable? Y)
- L490-514 "Key Patterns from References" → PROJECT_SPECIFIC (Imported patterns from `ai-workflow`, `java-interview-setup`, and `ui-designer` that shape this repo’s service; Generalizable? Y)
- L515-516 "Infrastructure Reference" → SHARED_WITH_DRIFT (Infrastructure References)
- L517-523 "Discord" → SHARED_WITH_DRIFT (Infrastructure References)
- L524-529 "Hosting" → SHARED_WITH_DRIFT (Infrastructure References)
- L530-563 "When to Ask the User" → SHARED_WITH_DRIFT (Gate Ownership / When To Ask The User)
- L564-578 "No Backwards Compatibility" → SHARED_WITH_DRIFT (No Backwards Compatibility)
- L579-586 "No Deferred Stubs" → SHARED_WITH_DRIFT (No Deferred Stubs)
- L587-593 "Git Conventions" → SHARED_WITH_DRIFT (Git / Branch Conventions; also cited in C3 (draft PRs as default convention))

### /home/nes/projects/videos/AGENTS.md
- L1-33 "AGENTS.md — visual motion pipeline" → PROJECT_SPECIFIC (Repository identity/status header for the visual-motion pipeline, including research status and two first-clas; Generalizable? N)
- L34-50 "What this pipeline is NOT" → PROJECT_SPECIFIC (Anti-scope list defining what the motion pipeline is explicitly not meant to do; Generalizable? Y)
- L51-66 "Tier safety" → SHARED_WITH_DRIFT (Tiered Approval Safety; also cited in C3 (PR push requires explicit approval))
- L67-84 "Workflows (cue → workflow)" → SHARED_WITH_DRIFT (Workflow Routing Tables)
- L85-103 "Motion Analysis workflow" → PROJECT_SPECIFIC (Numeric-signal workflow for deriving motion timelines and event artifacts from a reference or draft; Generalizable? Y)
- L104-120 "Critique workflow" → PROJECT_SPECIFIC (Review workflow that splits choreography/composition/HCI critique from review-audit validation; Generalizable? Y)
- L121-141 "Planning workflow" → PROJECT_SPECIFIC (Phase-by-phase planning workflow from brief to final deliverable, with repeated risk gates; Generalizable? Y)
- L142-169 "3× risk gate (applies at every gate in phases 3–8)" → PROJECT_SPECIFIC (Definition of the core 3× risk gate plus medium-specific add-on risk classes for motion work; Generalizable? Y)
- L170-186 "Generation workflow" → PROJECT_SPECIFIC (Generation workflow for new raster/video/SVG outputs, including self-review and bounded regeneration; Generalizable? Y)
- L187-206 "HCI Review workflow (UI work only)" → PROJECT_SPECIFIC (HCI review rubric for UI motion, with WCAG/platform/performance source expectations; Generalizable? Y)
- L207-241 "Research workflow" → SHARED_WITH_DRIFT (Research Workflow)
- L242-259 "Roadmap workflow" → SHARED_WITH_DRIFT (Roadmap / Strategy Layers)
- L260-276 "Gate ownership" → SHARED_WITH_DRIFT (Gate Ownership / When To Ask The User)
- L277-294 "Model roles" → SHARED_WITH_DRIFT (Model Roles / No-Super-Agent Boundary)
- L295-351 "Artifact naming" → PROJECT_SPECIFIC (Per-project folder/schema for policies, references, plans, reviews, keyframes, composites, finals, and risk ar; Generalizable? Y)
- L352-372 "Global constraints" → SHARED_WITH_DRIFT (Global Constraints)
- L373-417 "Sub-AGENTS.md documents `[PLANNED]`" → PROJECT_SPECIFIC (Planned decomposition of the motion rules into medium-, content-, and UI-subtype sub-AGENTS documents; Generalizable? Y)
- L418-441 "Adding an agent file" → SHARED_WITH_DRIFT (Agent File Format / Agent Skeleton)
- L442-488 "Open items" → PROJECT_SPECIFIC (Project status section listing what has landed and what still remains to run or wire up; Generalizable? N)

### /home/nes/projects/visual-code-editor/AGENTS.md
- L1-2 "Visual Code Editor — Agent Workflows" → PROJECT_SPECIFIC (Repository identity header for the visual code editor; Generalizable? N)
- L3-11 "Project Context" → PROJECT_SPECIFIC (Project overview describing the editor as an interactive system-visualization and drill-down/detail-panel UI; Generalizable? N)
- L12-19 "Technology Stack" → PROJECT_SPECIFIC (SolidJS + TanStack Solid Router — reactive UI framework ELK.js — graph layout engine (layered algorithm with o; Generalizable? N)
- L20-32 "Current Visual State (as of 2026-04-15)" → PROJECT_SPECIFIC (Point-in-time summary of animation/UI fixes already landed as of 2026-04-15; Generalizable? N)
- L33-36 "Known remaining items" → PROJECT_SPECIFIC (Short list of remaining known issues after the recent animation QA pass; Generalizable? N)
- L37-46 "Dual-View Problem" → PROJECT_SPECIFIC (Specific UX problem statement about cards that need both drill-down and detail-panel affordances; Generalizable? Y)
- L47-50 "Visual Asset Pipeline" → PROJECT_SPECIFIC (Top-level rule that all visual assets are version-controlled SVGs under `app/assets/`; Generalizable? Y)
- L51-61 "Directory Structure" → SHARED_WITH_DRIFT (Repository Structure Maps)
- L62-72 "SVG Requirements" → PROJECT_SPECIFIC (All SVGs must: Use currentColor for text/icon fills (inherits from CSS) Use CSS custom properties (var(border); Generalizable? Y)
- L73-86 "Model Roles" → SHARED_WITH_DRIFT (Model Roles / No-Super-Agent Boundary)
- L87-96 "Model Boundary: Gemini vs GPT" → SHARED_WITH_DRIFT (Model Roles / No-Super-Agent Boundary)
- L97-118 "SVG Self-Correcting Loop" → PROJECT_SPECIFIC (Gemini-specific visual review loop for SVG generation using SVG→PNG conversion and iterative inspection; Generalizable? Y)
- L119-122 "Animation Pipeline" → PROJECT_SPECIFIC (Animation-system heading introducing parameterization, interpolation, and selection work; Generalizable? Y)
- L123-130 "Animation Types" → PROJECT_SPECIFIC (1. Card hover — lift, float, settle (currently CSS transitions + JS spring physics) 2. Diagram transitions — c; Generalizable? Y)
- L131-159 "Animation Design Process" → PROJECT_SPECIFIC (1. Design (geminihigh): Describe the interaction context. Gemini proposes animation parameters: Easing curves ; Generalizable? Y)
- L160-170 "Research Workflow" → SHARED_WITH_DRIFT (Research Workflow)
- L171-198 "Research Areas" → PROJECT_SPECIFIC (1. Interactive graph visualization UX — How do tools like Figma, Miro, Lucidchart, GitHub dependency graphs ha; Generalizable? Y)
- L199-202 "Animation QA Workflow" → PROJECT_SPECIFIC (Semantic animation QA workflow built from Playwright video capture plus Gemini video review; Generalizable? Y)
- L203-208 "How It Works" → PROJECT_SPECIFIC (1. Capture: Playwright records short video clips of specific animations/interactions 2. Judge: agents model ge; Generalizable? Y)
- L209-222 "Running Captures" → PROJECT_SPECIFIC (Build and serve first cd ~/projects/visualcodeeditor npm run build && npm run serve &; Generalizable? Y)
- L223-237 "Sending to Gemini for QA" → PROJECT_SPECIFIC (Reference the video file in the prompt — geminivideohigh can read video files agents model geminivideohigh p ~; Generalizable? Y)
- L238-244 "Capture Specs" → PROJECT_SPECIFIC (Capture Specs; Generalizable? Y)
- L245-254 "When to Run" → PROJECT_SPECIFIC (Before/after animation or interaction changes When investigating visual bugs For prereview QA on motionheavy P; Generalizable? Y)
- L255-268 "Implementation & Bug-Fix Workflow" → SHARED_WITH_DRIFT (Implementation & Bug-Fix Workflow)
- L269-292 "Build & Verify" → PROJECT_SPECIFIC (Local build/regenerate/preview/Playwright verification checklist for visual changes; Generalizable? Y)
- L293-301 "Cross-Project References" → PROJECT_SPECIFIC (Local path pointers into the diagram source repo, SVG conversion script, and parent AGENTS files; Generalizable? N)
- L302-319 "Visual Regression" → PROJECT_SPECIFIC (Pixel-baseline workflow for visual regression testing, including local harness use and snapshot update guidanc; Generalizable? Y)
- L320-331 "CI (GitHub Actions)" → PROJECT_SPECIFIC (GitHub Actions recipe for the visual-regression workflow and the CI-based rebaseline path; Generalizable? Y)
- L332-335 "Known limits" → PROJECT_SPECIFIC (Known limitations of the visual-regression harness and icon/font stability strategy; Generalizable? N)

## Suggested ~/ai/ file list

### `~/ai/workflows/*.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/workflows/pr-review.md`
- `~/ai/workflows/research.md`
- `~/ai/workflows/roadmap.md`
- `~/ai/workflows/tiered-approval.md`
- `~/ai/workflows/agents-cli.md`
- `~/ai/workflows/governance-audit-cycle.md`
- `~/ai/workflows/agentic-evals.md`
- `~/ai/workflows/visual-asset-pipeline.md`
- `~/ai/workflows/animation-qa.md`
- `~/ai/workflows/writing-quality.md`

### `~/ai/agents/*.md`
- `~/ai/agents/README.md`
- `~/ai/agents/routing-index.md`
- `~/ai/agents/operator-file-format.md`
- `~/ai/agents/subagent-boundaries.md`
- Reference only in Phase 1a; actual prompt bodies belong to Phase 1b.

### `~/ai/models/*.md`
- `~/ai/models/roles.md`
- `~/ai/models/runner-config.md`
- `~/ai/models/input-schema.md`
- `~/ai/models/multimodal-models.md`

### `~/ai/conventions/*.md`
- `~/ai/conventions/no-backwards-compatibility.md`
- `~/ai/conventions/no-deferred-stubs.md`
- `~/ai/conventions/git.md`
- `~/ai/conventions/session-log.md`
- `~/ai/conventions/scratch-file-naming.md`
- `~/ai/conventions/worktree-isolation.md`
- `~/ai/conventions/workflow-step-reporting.md`

### `~/ai/patterns/*.md`
- `~/ai/patterns/repo-structure-map.md`
- `~/ai/patterns/api-first-service-layout.md`
- `~/ai/patterns/test-code-agent-separation.md`
- `~/ai/patterns/governance-documents.md`
- `~/ai/patterns/design-package-workflow.md`
- `~/ai/patterns/system-visualization.md`
- `~/ai/patterns/visual-regression.md`

