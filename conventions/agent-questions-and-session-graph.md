# Agent Questions And Session Graph

Use this convention when a delegated sub-agent needs user input and must route the question through the root orchestrator.

This convention also defines the file-based session graph used to continue answered work when non-interactive provider session resume is unavailable or when the resumed agent needs to pull exact prior context.

## Vocabulary

- `root orchestrator`: the workflow actor that talks to the user.
- `sub-agent`: an operator or delegated agent invoked by the root.
- `question artifact`: machine-readable JSON emitted by a sub-agent that needs user input.
- `answer artifact`: machine-readable JSON written by the root after the user answers.
- `invocation UUID`: agent-runner process identity, used by `agents trace`.
- `session ID`: wrapped provider conversation identity, used for provider resume when available.
- `session graph`: file-based graph of invocations, sessions, turns, artifacts, questions, answers, and continuation attempts.
- `pull access`: the continued agent reads exact graph files by stable ID.
- `push access`: the root renders prior state into the prompt or provider-resumed context.

## Question Emission Rule

Sub-agents do not talk to the user directly.

When a sub-agent needs user input, it writes:

```text
<scratch_dir>/questions/<question_id>.question.json
```

`scratch_dir` is the directory declared in the sub-agent's invocation prompt. The question artifact's `state_refs.session_graph_manifest` is the authoritative absolute graph path. The root reads the declared `scratch_dir` and manifest path, not its own local default.

and returns:

```text
NEEDS_INPUT:<question_artifact_path>
```

The sub-agent must stop before taking any action that depends on the answer. It must not report ordinary success for unanswered blocking work.

`question_id` must use `q-<uuidv4>`. Do not use counters, phase labels, filenames, or other locally scoped IDs.

When `origin.invocation_uuid` or `origin.session_id` is unknown at emission time, `origin.prompt_path` and `origin.log_path` are mandatory. The root must correlate those paths to SQLite state through `agents trace --json` and `session_turns` before attempting session-id resume.

## AskUserQuestion Permission-Denial

Direct `AskUserQuestion` permission-denial on a human-owned new-value, scope, or trade-off question is a question-emission trigger alongside the sub-agent emission rule, and it uses the existing question-artifact envelope rather than an inline answer.

For that denied human-owned question, write `${scratch_dir}/questions/q-<uuidv4>.question.json` as JSON per the Question Artifact Schema, return `NEEDS_INPUT:<absolute_artifact_path>`, and halt before any dependent action.

Procedural permission-denial or procedural `NEEDS_INPUT` that the orchestrator can resolve from supplied inputs stays inline and does not bother the root.

Forbidden language: permission denial is not a user decline and does not authorize defaults or self-applied answers. self-applying defaults on a new-value, scope, or trade-off question after `AskUserQuestion` is denied is a contract violation.

## Question Artifact Schema

The artifact is JSON. Required fields:

```json
{
  "schema_version": 1,
  "kind": "agent_question",
  "question_id": "q-<uuidv4>",
  "created_at": "<ISO-8601 timestamp>",
  "status": "needs_input",
  "origin": {
    "operator": "<operator-or-workflow-name>",
    "role": "<role-or-phase>",
    "invocation_uuid": "<uuid-or-unknown>",
    "parent_invocation_uuid": "<uuid-or-unknown>",
    "session_id": "<provider-session-id-or-unknown>",
    "model": "<model>",
    "worktree_path": "<path>",
    "prompt_path": "<path-or-unknown>",
    "log_path": "<path-or-unknown>"
  },
  "workflow": {
    "name": "<workflow-name>",
    "phase": "<phase-or-step>",
    "blocking": true,
    "blocked_outputs": ["<artifact-or-action>"]
  },
  "question": {
    "title": "<short human-facing title>",
    "body": "<question text>",
    "type": "single_choice",
    "required": true,
    "options": [
      {
        "id": "A",
        "label": "<short label>",
        "description": "<what choosing this means>",
        "default": false
      }
    ],
    "allow_free_text": false
  },
  "state_refs": {
    "session_graph_manifest": "<path-or-unknown>",
    "relevant_invocation_ids": [],
    "relevant_session_ids": [],
    "relevant_turn_ids": [],
    "artifact_paths": [],
    "state_capsule": "<brief current-state summary>"
  },
  "answer_contract": {
    "answer_schema": "single_option_id",
    "apply_to": "<phase/gate/artifact/finding-chain>",
    "resume_instruction": "<what the continued agent must do with the answer>"
  },
  "continuation": {
    "preferred": "resume-by-session-id",
    "fallback": "session-files-to-new-agent",
    "target_model": "<model>",
    "requires_same_session": false
  }
}
```

Allowed `question.type` values:

- `single_choice`
- `multi_choice`
- `free_text`
- `confirm`

Every option needs a stable `id`, short `label`, and operational `description`. Use option IDs in answer artifacts and continuation prompts.

## Answer Artifact Schema

The root writes:

```text
<scratch_dir>/questions/<question_id>.answer.json
```

Required fields:

```json
{
  "schema_version": 1,
  "kind": "agent_answer",
  "question_id": "<question_id>",
  "answered_at": "<ISO-8601 timestamp>",
  "answered_by": "user-via-root-orchestrator",
  "answer": {
    "selected_option_ids": ["A"],
    "free_text": "",
    "confirmed": null
  },
  "root_decision": {
    "presented_options": true,
    "decision_summary": "<short summary>",
    "blocks_released": ["<artifact-or-action>"]
  },
  "continuation_plan": {
    "method": "resume-by-session-id",
    "feature_detection": "<supported|unsupported|unknown>",
    "session_graph_manifest": "<path>",
    "next_prompt_path": "<path>"
  }
}
```

## Root Surfacing Rule

The root orchestrator reads the question artifact, presents the question and options to the user, writes the answer artifact, and continues the blocked work. It must not advance dependent workflow steps until continuation evidence exists.

If the question is malformed, missing required fields, or does not identify the blocked output, the root records `BLOCKED:<reason>` and asks for clarification only when the workflow cannot otherwise fail closed.

Legacy `NEEDS_INPUT:<reason>` returns, where the tail does not resolve to a readable question artifact path, are treated as free-text reasons, surfaced directly to the user, and do not trigger resume/fallback. Operators migrate to the envelope case by case; no bulk migration is required by this initiative.

## Session Graph Layout

Use one graph root per root invocation or workflow run:

```text
<scratch_dir>/session-graph/<root_invocation_uuid>/
  manifest.json
  invocations/<invocation_uuid>.json
  sessions/<session_id_safe>.json
  turns/<session_id_safe>.jsonl
  artifacts/index.json
  questions/<question_id>.question.json
  answers/<question_id>.answer.json
  continuations/<question_id>.<resume|fallback>.json
  summaries/<summary_id>.md
```

`manifest.json` records:

- graph ID and root invocation UUID;
- creation and update timestamps;
- known invocations, sessions, and artifacts;
- question IDs and answer IDs;
- edges between nodes;
- local path policy and redaction notes.

The root orchestrator, or a designated helper operator acting for the root, populates `invocations/`, `sessions/`, and `turns/` from `agents trace --json` and `session_turns` before answer-writing. Sub-agents write only the `questions/` artifacts they emit and `artifacts/index.json` fragments for artifacts they authored.

Turn-content provenance uses references instead of copied transcript bodies. `turns/<session_id_safe>.jsonl` records turn IDs, role/timestamp metadata when available, and `source_file` pointers to provider raw logs with offsets or line metadata when available. Continuations pull exact turn content from those referenced source files when needed and record both graph files and source files read.

Edges use these names:

- `parent_invocation`
- `uses_session`
- `produced_turn`
- `references_artifact`
- `emitted_question`
- `answered_by`
- `resumed_by`
- `fallback_continued_by`

## Pull-vs-Push Policy

Default to pull access. Pass only the answer artifact, a short state capsule, graph manifest path, and relevant node IDs in the continuation prompt.

The continued agent reads exact graph files as needed. It records the graph files it read in the continuation artifact.

Push prior context only when:

- the provider resume path requires it;
- local file access is unavailable;
- graph pull is too slow or too large for the task.

Summaries are allowed only as derived aids. They must cite source graph node IDs and must not replace available graph files as source of truth.

## Resume-by-Session-ID Path

Before using session resume, feature-detect a non-interactive answer-payload path:

```bash
agents resume --help
agents --help
```

The installed runner qualifies only when it supports a session ID plus a prompt or answer file in a non-interactive command.

Preferred shape:

```bash
agents resume -m <model> -p <worktree-path> --session-id <session_id> -f <answer-payload.md>
```

Accepted equivalent:

```bash
agents -m <model> -p <worktree-path> --resume <session_id> -f <answer-payload.md>
```

Do not treat `agents repl <model> --resume <session-id>` as sufficient for root workflow automation.

## Session-Files Fallback

When feature detection fails, dispatch a fresh agent:

```bash
agents -m <model> -p <worktree-path> -f <fallback-prompt.md>
```

The fallback prompt must include:

- question artifact path;
- answer artifact path;
- session-graph manifest path;
- relevant graph node IDs;
- instruction to pull needed context from graph files;
- instruction to continue the blocked task rather than restart;
- required continuation artifact path.

## Continuation Evidence

Every continuation writes:

```text
<scratch_dir>/session-graph/<root_invocation_uuid>/continuations/<question_id>.<resume|fallback>.json
```

Required fields:

- `question_id`
- `answer_artifact`
- `method`
- `origin_invocation_uuid`
- `origin_session_id`
- `new_invocation_uuid`
- `new_session_id`
- `session_graph_manifest`
- `graph_files_read`
- `source_files_read`
- `accepted_resume`: `true`, `false`, or `unconfirmed`
- `result`: `continued`, `blocked`, or `failed`
- `output_artifacts`

## Audit And Process Review

Question and answer artifacts are companion artifacts for `process-tree-auditor` when a workflow step could emit questions.

A Q&A turn enters audit history only when it affects a revise/review loop, gate, verdict, or `continue` / `apply` / `decompose` decision.
