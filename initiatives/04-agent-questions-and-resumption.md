# Initiative 04 — Agent question-back + session resumption

**Status:** landed (~/ai-side convention + workflow edits applied; agent-runner work spawned as Init 06)
**Depends on:** 03 (landed)
**Blocks:** —
**Spawned:** Initiative 06 (agent-runner session-id resumption)

## Problem (user framing, verbatim)

> Sometimes orchestrators and agents will ask for answers to questions that they may have. They may provide options. agents operator gives us ways to resume prior sessions, though it is a bit hacky right now. We can pass in the session and have the underlying agent pull the session information out with the agents binary (just the part that it represents) to ingest the turns. We could alternatively summarize the session information to what is useful with another agent from the agents binary and pass that off to reduce context. So we can potentially package up sessions into file-based graphs that we can use to resume agents. Agents can then withdraw details as they need them if they need them rather than trying to rely on a summary.
>
> This initiative is about allowing agents to ask questions back to the user and then resuming them. The orchestrator can receive the question because the agent it executed finishes and it sent a response back as part of the output file or whatever. The root orchestrator can then present those questions to the user to be answered. Once answered the root orchestrator can then resume the underlying agent with the answers.
>
> What would likely be more ideal would be to resume the specific actual session id. I don't think agents provides a way to do that right now, but that could actually be another task to provide a method to do that. ... Being able to resume sessions would allow us to make use of caching. If that is too complex we still have a workaround by just sending the session files to a new agent.

## Firm constraints

1. **Only the root orchestrator talks to the user.** Sub-agents that need answers write their questions to their output file; the root surfaces them.
2. **Questions can include options.** The schema must support structured choice, not just free text.
3. **Two resumption paths are acceptable, ranked:**
   1. **Resume by actual session id** (ideal). Requires agent-runner change. Unlocks provider-level prompt caching.
   2. **Pass session files to a new agent** (fallback). Works today but misses caching and may drift on summarization.
4. **Session-file packaging is a file-based graph.** Agents can *withdraw* details as needed from the graph — summarization is only a last resort because a summary can hide what the agent actually needs.

## Scope

**In scope:**
- `~/ai/workflows/*` — patterns for how a sub-agent signals "I have a question" in its output file, and how the root handles it.
- Output-file schema convention (new file under `~/ai/conventions/`?) — questions, options, current working state reference, required session-graph pointer.
- A session-graph convention — on-disk layout that lets a resumed agent withdraw exactly the turns or artifacts it needs.
- **Sub-track: agent-runner feature work** at `/home/nes/projects/agent-runner`:
  - Docs: `~/projects/agent-runner/README.md`
  - Project AGENTS: `~/projects/agent-runner/AGENTS.md`
  - Goal: support `agents <something> --resume <session-id>` (or equivalent) so a new invocation continues in the same session context and benefits from provider caching.
- Possibly new operator: `question-bridge` (or extend an existing orchestrator operator) to package user answers into a resume payload.

**Out of scope:**
- Rewriting the agent-runner CLI surface beyond what session resumption requires.
- Adding an interactive TTY loop inside a sub-agent — questions go through the file-based output handoff, not live stdin.

## Open questions (to resolve during scoping, not now)

- Does the ideal design make session-graph access *pull* (the resumed agent queries the graph) or *push* (the graph is rendered into the new prompt)? Pull preserves context budget; push is simpler.
- When does summarization become acceptable? Probably only when the session is larger than the resumed agent's context budget and the pull path cannot prune fast enough.
- How does the root orchestrator know *which* agent to resume when multiple sub-agents have questions?

## Expected sub-initiative: agent-runner session-id resumption

If the agent-runner README shows no clean way to resume a session:

1. Study `/home/nes/projects/agent-runner/` for how session state is persisted today (the `agents trace` subcommand hints at UUID-keyed trees).
2. Design a minimal resume flag and persistence contract.
3. Land it in agent-runner first, then consume in `~/ai/` workflows.

This sub-initiative may spawn its own initiative file (`05-agent-runner-session-resume.md`) if it grows beyond a small change.

## Artifacts (empty until unblocked)

- `.build/A<NN>-agent-qa-resume-*-prompt.md`
- `.build/A<NN>-agent-qa-resume-*-findings.md`
- Proposal targets: workflow pattern docs, new convention(s), agent-runner change.

## Log

- **2026-04-23** — Initiative queued. Captured framing, firm constraints, and the agent-runner sub-track.
- **2026-04-24** — Research fan-out: R1 runner capability (real `agents` help output), R2 question-back patterns, R3 workflow integration (confirmed Init-02b does NOT block Init 04), R4 session-graph survey (LangGraph / MCP / Claude Code / Temporal / OpenAI Assistants). Synthesis: 17 QG-gaps, 8 options (A-H). All A-H move to proposal; agent-runner work (D runner track) spawns Init 06.
- **2026-04-24** — Proposal cycle: v0 (11 non-blocking R-findings including R-B backward-compat) → v2 (1 S-finding, internal §2/§8.2 scope inconsistency on decision-encoder). S1 resolved at apply by keeping decision-encoder in Init 04 scope (closes QG15 fully). Convergence in one revision round. 0 blocking, 0 oscillation.
- **2026-04-24** — Applied: new `~/ai/conventions/agent-questions-and-session-graph.md`, updates to `audit-history.md` (new `User Q&A Inputs` section + skeleton line), `workflow-execution-violations.md` (new question/answer handling violation class), `decision-encoder.md` (Q&A role_outputs), `process-tree-auditor.md` (Q&A verification step), 7 workflow files, AGENTS.md routing. Spawned Init 06 (agent-runner session-id resumption).
