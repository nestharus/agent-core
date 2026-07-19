---
workflow:
  id: work-manager-ticket-draft-audit
workflow_dispatch_contract:
  orchestrator: "work-manager-ticket-filing-operator or root orchestrator before backend ticket create"
  inputs:
    - "N1-shaped work-manager-ticket-draft-evidence bundle path"
    - "worktree path, model, prompt path, log path, audit report path, scratch dir, planning dir"
    - "runner/orchestrator currentness and session graph evidence when load-bearing"
  expectations:
    - "verifies bundle currentness before dispatching the independent pre-posting critic"
    - "dispatches work-manager-ticket-brief-auditor through the approved non-interactive agents CLI shape"
    - "writes a pre-posting audit report path before any backend create handoff"
  outputs:
    - "N3 prompt path, log path, and report path"
    - "LOW/MEDIUM/HIGH/NEEDS_INPUT/BLOCKED audit result consumed by the filing operator"
  non_goals:
    - "does not post tickets, mutate backend state, or replace Linear/Jira create contracts"
    - "does not replace workflow-process-auditor for completed-run procedure review"
---

# Work Manager Ticket Draft Audit

## Declared roles

`orchestration`, `validator`, `mapper`, `formatter`, `parser`

This workflow orchestrates the pre-posting critic pass, validates bundle currentness, maps N1 bundle paths into an N3 prompt, formats prompt/log/report paths, and parses the audit result for the filing operator. Role tokens come from `/home/nes/ai/conventions/code-quality.md`.

## Purpose

Run the independent ticket-brief critic between Work Manager draft production and backend ticket creation. `/home/nes/ai/agents/work-manager-ticket-filing-operator.md` owns drafting and backend handoff; this workflow owns the audit procedure and evidence path discipline; `/home/nes/ai/agents/work-manager-ticket-brief-auditor.md` owns the semantic verdict.

Canonical contract and context:

- `/home/nes/ai/conventions/work-manager-ticket-brief-boundary.md`
- `/home/nes/ai/agents/work-manager-ticket-filing-operator.md`
- `/home/nes/ai/agents/work-manager-ticket-brief-auditor.md`
- `/home/nes/ai/workflows/agents-cli.md`
- `/home/nes/ai/conventions/agent-questions-and-session-graph.md`
- `/home/nes/ai/conventions/evals.md`
- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md`
- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/proposals/acr-256-ACR-256.md`
- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-problem-map.md`
- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-hookpoints.md`
- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/.scratch/phase6/step6b-output-index.md`
- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/.scratch/phase6/step6c-consumed-evidence.txt`
- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/.scratch/phase6/step6c-side-channel-manifest.md`
- `/home/nes/ai/worktrees/acr-256-work-manager-over-prescription/evals/acr-256-work-manager-ticket-brief-boundary/eval.md`
- `/home/nes/ai/agents/operator-file-format.md`
- `/home/nes/ai/agents/workflow-process-auditor.md`
- `/home/nes/ai/agents/agent-design-auditor.md`
- `/home/nes/ai/agents/workflow-design-auditor.md`
- `/home/nes/ai/agents/linear-operator.md`
- `/home/nes/ai/agents/jira-operator.md`
- `/home/nes/ai/conventions/code-quality.md`

## Workflow Dispatch Surface

### Orchestrator

`/home/nes/ai/agents/work-manager-ticket-filing-operator.md` or a root orchestrator acting before backend ticket create.

### Inputs

- `evidence_bundle_path=<absolute path>` using the schema owned by `/home/nes/ai/conventions/work-manager-ticket-brief-boundary.md`.
- `worktree_path=<absolute path>`.
- `scratch_dir=<absolute path>`.
- `planning_dir=<absolute path>`.
- `model=<model>` for `/home/nes/ai/agents/work-manager-ticket-brief-auditor.md`.
- `prompt_file_path=<absolute path>`.
- `log_file_path=<absolute path>`.
- `audit_report_path=<absolute path>`.
- Currentness evidence from the runner/orchestrator: capture timestamp, commit SHA, invocation UUIDs, and session graph or trace locator when available.

### Expectations

- Validate that the bundle is current for the draft, route-decision artifact, source evidence paths, producer prompt, producer log, active flavor, backend target, and commit SHA.
- Write an N3 prompt that names `/home/nes/ai/agents/work-manager-ticket-brief-auditor.md`, `/home/nes/ai/conventions/work-manager-ticket-brief-boundary.md`, the evidence bundle path, and the report path.
- Dispatch the child in non-interactive form. The approved minimum shape is:

```bash
agents -m <model> -f <prompt-file> 2>&1 | tee <log>
```

When a workflow caller needs explicit worktree isolation, use the `/home/nes/ai/workflows/agents-cli.md` compatible extension with `-p <worktree-path>` while preserving `agents -m <model> -f <prompt-file>` as the child invocation core and preserving full `2>&1 | tee <log>` capture.

### Outputs

- N3 prompt file at `prompt_file_path`.
- N3 log file at `log_file_path`.
- N3 report at `audit_report_path`.
- Updated or companion evidence showing the bundle's `audit_report_path` points to the N3 report.
- A workflow result of `LOW`, `MEDIUM`, `HIGH`, `NEEDS_INPUT`, or `BLOCKED`.

### Non-goals

- No backend ticket creation.
- No semantic ticket repair by this workflow.
- No replacement for `/home/nes/ai/agents/workflow-process-auditor.md`; a completed N4 run may later be audited there as runtime procedure evidence.
- No runnable eval, pytest, shell verifier, or CI implementation. `/home/nes/ai/conventions/evals.md` owns structural eval routing.

## Procedure

1. Read `/home/nes/ai/conventions/work-manager-ticket-brief-boundary.md` and the N1-shaped evidence bundle.
2. Check bundle currentness before dispatch:
   - all path fields are absolute;
   - draft brief, route decision, source evidence paths, producer prompt, and producer log exist;
   - `currentness.captured_against_commit_sha` matches the caller's currentness evidence or is explicitly marked stale;
   - `producer_invocation.invocation_uuid`, `producer_invocation.prompt_path`, and `producer_invocation.log_path` are present;
   - `audit_report_path` is a writable absolute path under the caller-supplied planning or scratch root.
3. If currentness is missing, stale, or self-attested only by the audited model, stop with `BLOCKED` or `NEEDS_INPUT`; do not dispatch N3 as if evidence were clean.
4. Write the N3 prompt file. The prompt must instruct N3 to read `/home/nes/ai/conventions/work-manager-ticket-brief-boundary.md`, the evidence bundle, and concrete paths named by the bundle; it must instruct N3 to write the report at `audit_report_path`.
5. Dispatch N3 through the approved child invocation shape:

```bash
agents -m <model> -f <prompt-file> 2>&1 | tee <log>
```

Do not call bare `agents`. Do not launch an interactive UI. Do not replace this with the host CLI built-in sub-agent or Task tool.

6. Parse the N3 report. The report must include `Verdict: <LOW|MEDIUM|HIGH|NEEDS_INPUT|BLOCKED>` and the final stdout line shape documented by `/home/nes/ai/agents/work-manager-ticket-brief-auditor.md`.
7. Enforce pre-posting critic separation. Emit `HIGH` for `acr-256-preposting-critic-separation` when backend-create time arrives and no independent N3 `audit_report_path` exists in the bundle, when the report is stale for the bundle, or when report provenance cannot be joined to the prompt/log path.
8. Return the N3 verdict to `/home/nes/ai/agents/work-manager-ticket-filing-operator.md`. Only `LOW` permits posting. `MEDIUM`, `HIGH`, `NEEDS_INPUT`, and `BLOCKED` route to revision, design/discovery, question handling, or evidence repair without backend create.

## Stop Conditions

- `LOW`: N3 report exists at `audit_report_path`, is current for the bundle, and returns `LOW`.
- `MEDIUM`: N3 returns `MEDIUM`; the filing operator must revise, preserve legitimate S5 detail, or inspect backend-boundary ambiguity before re-audit.
- `HIGH`: N3 returns `HIGH`, or this workflow detects missing independent critic evidence at backend-create time.
- `NEEDS_INPUT:<question_artifact_path>`: source approval, currentness, route decision, or backend target needs root/user decision under `/home/nes/ai/conventions/agent-questions-and-session-graph.md`.
- `BLOCKED:<reason>`: bundle, prompt, log, report path, or currentness evidence is absent, unreadable, stale, malformed, or self-attested only by the audited model.

## Audit Contract

This workflow is the pre-posting audit procedure. Its process evidence is:

- the N1-shaped bundle path and content;
- N3 prompt file path;
- N3 log file path;
- N3 report path;
- runner/orchestrator currentness evidence;
- invocation UUIDs or trace/session graph locators that join producer, workflow, critic, and backend handoff evidence.

`/home/nes/ai/agents/workflow-process-auditor.md` may later audit a completed run of this workflow using the artifacts above, but that post-run procedure audit does not replace the N3 semantic verdict and does not permit backend create on a non-LOW N3 result.

## Intrinsic-surface declarations

```yaml
intrinsic_surface_declarations:
  - component: /home/nes/ai/workflows/work-manager-ticket-draft-audit.md
    role: intrinsic-surface
    Domain: work-manager-ticket-draft-audit-procedure
    Owns:
      - draft-to-audit phase order
      - prompt/log/report output paths
      - LOW-only posting gate
      - non-LOW revise-or-route disposition
      - backend-create handoff boundary
```
