# Eval Runtime

## Purpose

Eval runtime is the future workflow for executing trace-consuming behavior detectors defined by `conventions/evals.md`. It describes invocation modes, evidence normalization, result validation, report storage, routing semantics, and failure handling without wiring any runtime hook in ACR-175.

ACR-175 ships this design contract only. It does not add workflow dispatch metadata, regenerate `workflows/index.json`, implement `agents eval-run`, add CI, or schedule post-merge scans.

## Invocation modes

Eval runtime has exactly three invocation modes:

- `on-trace`: future pipeline integration that runs selected evals against a WU/session trace at a named hookpoint. ACR-175 describes this mode but wires no implementation-pipeline hook.
- `post-merge`: future scheduled scan over recent merged-PR traces, used to detect regressions that were not blocking during the original WU.
- `on-demand`: future spot check invoked with `agents eval-run <eval-id> --trace <session-id>`.

All three modes use the same eval identity, trace normalization, finding-schema validation, and report bundle rules. They differ only in who initiates the run and how findings are routed.

## Eval selection

The active manager flavor and owning workflow select which evals are active. Flavor-sensitive evals compare trace behavior against the declared policy source for that session, such as `agents/work-manager-operator.md` plus `agents/work-manager-operator-max.md`, `agents/work-manager-operator-pragmatic.md`, or `agents/work-manager-operator-hackerman.md`.

Eval selection must record the source of the selection: manager flavor, workflow hookpoint, on-demand user request, or post-merge scan policy. Missing selection evidence is a runner failure or `NEEDS_INPUT` condition, not an implicit no-finding.

## Trace resolution

The runner resolves a trace locator into a trace bundle. Accepted locator forms include a session ID, root invocation UUID, saved `agents trace --json` path, or planning artifact that points to those values.

Resolution gathers companion planning artifacts when present: prompts, run logs, process-tree reports, workflow-process reports, audit bundles, gate reports, question and answer artifacts, branch diff paths, and report sinks. The resolver prefers saved `agents trace --json` boundaries and uses raw state DB evidence only through a verified adapter.

## Normalize evidence

Before eval execution, the runtime normalizes evidence into semantic fields. Normalization joins child invocations by UUID and parent relationships, attaches prompt and report paths, maps phase/gate names to the owning workflow vocabulary, and records missing or degraded sources explicitly.

Normalization does not infer compliance. If evidence is absent, stale, or ambiguous, the normalized bundle must carry that state so the eval can return a finding, no finding, validation error, or `NEEDS_INPUT` according to its spec.

## Run eval

The future runner loads the target `eval.md` specification and runnable eval code when it exists. The executor passes the normalized trace bundle to the eval implementation and receives either a finding object or `None`.

This workflow specifies the loader and executor protocol only. ACR-175 does not write runtime code, eval code, fixture code, trace parser code, or a CLI command.

## Validate result

Every non-null result is validated against the minimum finding schema from `conventions/evals.md`: `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`.

Validation also checks that `eval_id` matches the loaded eval, evidence paths exist or are explicitly marked unavailable, severity is valid for the eval, and any extension fields are JSON-serializable routing/context fields. Invalid finding shape is a runner validation error, not a behavior finding.

## Store report

Reports are written under the caller-declared planning sink, defaulting to:

`planning_dir/<wu>/evals/findings.md`

The same bundle includes a machine-readable JSON report. The JSON report preserves eval identity, mode, trace locator, normalized evidence summary, terminal status, findings, validation errors, and degraded evidence notes.

Markdown reports are reviewer-facing summaries. JSON reports are the durable machine boundary for downstream audit-history, PR review, or future enforcement.

## Route action

Routing is design-only in ACR-175. A future caller may treat a finding as:

- advisory log: record the report and continue;
- blocking halt: stop a workflow phase until revise/decompose/human disposition happens;
- follow-up ticket: create a backlog item through the owning ticket backend.

The eval report must distinguish the suggested action from the side effect. Eval runtime may suggest `halt-pipeline`, `decompose`, `revise-proposal`, `file-followup-ticket`, or `advisory-log`, but backend writes and pipeline mutations belong to future caller-owned integration.

## Failure handling

Runtime distinguishes:

- `NO_FINDING`: eval ran and returned no behavior finding.
- Behavior finding: eval returned a valid finding.
- Runner error: trace cannot be resolved, runnable code is unavailable when execution was requested, or declared sinks cannot be written.
- Validation error: eval returned a result that does not satisfy the finding schema.
- Maintenance drift: evidence source changed enough that the eval spec or adapter must be updated before the result is trusted.

Runner errors and validation errors are not silently downgraded to `NO_FINDING`.

## Downstream integration notes

Future on-trace integration may use hookpoints from `agents/implementation-pipeline-orchestrator.md` and phase vocabulary from `workflows/implementation-pipeline.md`, especially Phase 4 risk/audit gates, Phase 6 alignment and implementation separation, Phase 7 CodeRabbit review, and Phase 8 process-tree/diff review gates.

Those hookpoints are references only in ACR-175. This WU does not edit the implementation pipeline, create a dispatch row, regenerate workflow indexes, or activate eval runtime in any live gate.

## Anti-scope

- No pipeline phase, CI job, cron job, CLI command, scheduler, or backend ticket writer is wired here.
- No workflow dispatch metadata and no required `workflows/index.json` edit.
- No eval implementation code, Python/Rust snippets, pytest, or executable file-shape assertions.
- No redefinition of manager flavor policy, audit workflows, process-tree topology review, or code-quality scoring.

## Cross-references

- `conventions/evals.md`
- `agents/eval-runner.md`
- `agents/implementation-pipeline-orchestrator.md`
- `workflows/implementation-pipeline.md`
- `conventions/agent-questions-and-session-graph.md`
- `agents/work-manager-operator.md`
- `agents/work-manager-operator-max.md`
- `agents/work-manager-operator-pragmatic.md`
- `agents/work-manager-operator-hackerman.md`
- ACR-174 pytest removal / deletion contract
