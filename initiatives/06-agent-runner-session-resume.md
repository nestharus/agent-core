# Initiative 06 — Agent-runner session-id resumption

**Status:** queued
**Depends on:** 04 (for the `~/ai` question envelope, session-graph convention, and feature-detection contract)
**Blocks:** Ideal Init 04 resume-by-session-id path; provider-cache-preserving continuation for answered sub-agent questions

## Problem

Init 04 defines how `~/ai` sub-agents emit questions through files, how the root orchestrator surfaces those questions, and how answered work continues. The preferred continuation is to resume the actual underlying provider session by session ID with a non-interactive answer payload. The current observed runner surface is not enough: `agents repl <model> --resume <session-id>` exists, but it is interactive and does not provide a clean root-orchestrator path for `resume this session with this answer file`.

This initiative owns the agent-runner work only. It must not rewrite the `~/ai` conventions except to document the implemented command shape that satisfies Init 04 feature detection.

## Firm constraints

1. Preserve the root-orchestrator boundary from Init 04: sub-agents do not talk to the user directly.
2. Provide a non-interactive resume-with-answer path. Interactive REPL resume is not sufficient.
3. Resume by actual provider session ID when the provider and local store support it.
4. Keep lookup explicit: distinguish runner invocation UUID, provider session ID, and session turns.
5. Confirm acceptance: traces or command output must show whether the resumed child actually attached to the intended session.
6. Feature-detectable: `~/ai` must be able to detect support without relying on source inspection.
7. Provider-aware: unsupported providers must fail clearly and let `~/ai` use the session-files fallback.
8. No broad CLI rewrite beyond the minimum resume and structured handoff surface.

## Scope

In scope:

- `/home/nes/projects/agent-runner/README.md`
- `/home/nes/projects/agent-runner/AGENTS.md`
- agent-runner CLI command or flag for non-interactive session resume
- provider resume configuration and validation
- session lookup through `session_turns` and invocation/session metadata
- trace evidence that records resume attempt, target session ID, provider, and acceptance status
- structured answer/session-graph payload support sufficient for Init 04
- tests or fixture-level verification for supported provider adapters

Out of scope:

- Changing `~/ai` workflow semantics beyond documenting the satisfied command shape.
- Implementing provider-local store migration across machines.
- Guaranteeing prompt caching for providers that do not expose it.
- Replacing the Init 04 session-files fallback.
- Adding live stdin question loops for sub-agents.

## Required capability

The runner must expose one feature-detectable non-interactive shape. Preferred:

```bash
agents resume -m <model> -p <worktree-path> --session-id <session_id> -f <answer-payload.md>
```

Acceptable equivalent:

```bash
agents -m <model> -p <worktree-path> --resume <session_id> -f <answer-payload.md>
```

The help text must make this discoverable through `agents resume --help` or `agents --help`.

The command must:

- validate the session ID against runner-known session metadata where possible;
- identify the provider and resume mechanism;
- pass the answer payload into the resumed provider session non-interactively;
- record whether provider resume was accepted, rejected, unsupported, or unconfirmed;
- emit a stable failure code/message when the `~/ai` fallback should be used.

## Acceptance criteria

- `~/ai` feature detection can distinguish supported non-interactive resume from current `agents repl --resume`.
- A root orchestrator can provide an answer payload file and receive a normal captured log through `tee`.
- The runner preserves invocation UUID versus provider session ID semantics in logs and traces.
- Resume lookup does not depend solely on raw provider transcript files when `session_turns` has the needed mapping.
- Trace output includes enough evidence for `process-tree-auditor` to classify resume acceptance or unconfirmed acceptance.
- Unsupported provider/config cases fail closed with a message that tells the root to use session-files fallback.
- README documents the command, feature detection, provider requirements, and known cross-machine/local-store limits.

## Artifacts

- `.build/A22-runner-resume-*-prompt.md`
- `.build/A22-runner-resume-*-findings.md`
- `.build/A22-runner-resume-proposal.md`
- agent-runner branch/PR artifacts under `/home/nes/projects/agent-runner`

## Log

- **2026-04-24** — Spawned from Init 04 proposal synthesis. Scope split keeps `~/ai` convention work separate from runner implementation.
