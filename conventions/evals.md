# Evals

## Purpose

Evals are the behavior-detection replacement path for brittle structural markdown tests removed under ACR-174. They give `~/ai` a shared way to name unwanted workflow or agent behavior, consume agent-runner trace evidence, and produce reviewable findings without asserting that a markdown file has a particular shape.

The canonical route for `~/ai` markdown/operator/workflow/convention/routing/anchor structural-verification work is WRITE-state eval-spec authoring at `evals/<slug>/eval.md`, not pytest files, pytest-shaped assertions, or one-off verifier scripts. This route covers phrases such as "structural test", "structural verification", "markdown anchor check", "workflow/operator shape guard", and "convention-routing guard" when the target is a `~/ai` structural surface. The predecessor prototype evidence at `/home/nes/projects/ai/planning/prototype-acr-199-clarify/dossier/evidence/p1-vector-b-routing-sufficiency.md` and `/home/nes/projects/ai/planning/prototype-acr-199-clarify/dossier/evidence/p1-vector-b-before-after-hand-trace.md` records the routing flip from pytest/verifier-shaped output to eval-spec output.

This convention defines the stable contract for eval specifications, future runnable eval implementations, findings, lifecycle state, repository placement, and evidence-source boundaries. `eval.md` files are reviewable behavior specifications. They are not executable assertions and do not enforce behavior by themselves.

## Declared roles

`validator`, `mapper`

This file-local declaration follows `~/ai/conventions/code-quality.md` `## Declared roles`: this convention validates eval-spec, finding, lifecycle, placement, and evidence-source contracts while mapping trace evidence into the future `trace -> finding | None` eval contract.

## Eval definition

An eval is future Python or Rust code shaped as:

`trace -> finding | None`

The trace input is a normalized evidence bundle for one session, WU, PR, or selected invocation subtree. The returned finding is a structured report when the named unwanted behavior is present. `None` means the eval did not find that behavior in the provided evidence.

The markdown file at `evals/<eval-id>/eval.md` defines the behavior contract: identity, unwanted behavior, positive evidence, non-fire cases, required trace fields, finding shape, suggested action, and lifecycle notes. Runnable code, fixtures, adapters, and CLI integration belong to downstream implementation tickets.

## Trace bundle contract

Trace evidence is named by role, not by raw storage schema. A future eval runner may consume:

- saved `agents trace --json` output;
- planning-directory trace artifacts;
- agent run logs and prompt files;
- process-tree-auditor reports and expected-process manifests;
- workflow-process-auditor reports;
- audit bundles such as `findings.json`, `findings.md`, aggregate reports, and companion artifacts;
- state DB evidence where available and resolved by the runner.

The preferred machine boundary is saved `agents trace --json`, because it exposes invocation UUIDs, parent/child edges, transcripts, and session graph data without binding evals to one raw SQLite path or table layout. Raw `state.db` evidence is a best-effort source behind the resolver. Its current path or schema must be verified by the runner before use.

Evidence across child invocations is joined by invocation UUID, parent invocation ID, root invocation UUID, prompt file path, and session graph semantics from `conventions/agent-questions-and-session-graph.md`. Missing child evidence is not silently treated as no behavior unless the eval specification explicitly permits that fallback.

## Finding schema

Every eval finding must preserve these minimum fields exactly:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

`severity` describes the eval finding, not the upstream risk-profile or code-quality verdict. It may use `LOW`, `MEDIUM`, and `HIGH`, but the meaning must be tied to the eval's behavior impact.

Routing and context extension fields are allowed when they do not weaken the minimum schema. Common extensions include `wu_id`, `session_id`, `root_invocation_uuid`, `active_manager_flavor`, `policy_source`, `phase`, `gate`, `finding_ids`, `trace_locator`, and `report_paths`.

## Lifecycle states

Eval lifecycle state is one of:

- `WRITE`: the behavior specification exists, but no runnable detector is required to exist.
- `ROLL_OUT`: runnable detector exists and reports advisory findings while false positives and evidence drift are observed.
- `ENFORCE`: the detector is trusted enough for a caller to halt, revise, decompose, or block according to the owning workflow.
- `MAINTAIN`: the detector is established and must be kept current as trace surfaces, manager flavors, or workflow gates change.

Transitions require a durable note in the owning eval spec or companion decision record that names evidence, false-positive review, downstream wiring, and enforcement readiness.

## Repository placement

Eval assets use this repository layout:

`evals/<eval-id>/{eval.md, eval.py-or-rs, fixtures/, README.md}`

For `~/ai` structural-verification routes, this layout is the canonical target: Step 6b may author only `evals/<eval-id>/eval.md` while the lifecycle is `WRITE`, and future detector work may add `eval.py-or-rs`, fixtures, and README files in a later ticket.

ACR-175 creates only `eval.md` seed specifications. Future implementation tickets may add `eval.py-or-rs`, fixtures, and README files when they ship runnable detectors.

## Evidence source stability

Stable contracts:

- eval identity and lifecycle metadata in `eval.md`;
- minimum finding schema fields;
- semantic evidence roles named in each eval spec;
- saved `agents trace --json` as the preferred trace boundary;
- invocation UUID and session graph vocabulary from `conventions/agent-questions-and-session-graph.md`;
- report bundle expectations from `workflows/eval-runtime.md` and `agents/eval-runner.md`.

Best-effort evidence surfaces:

- raw `state.db` schema and path;
- transient logs not saved into planning artifacts;
- reviewer comments, CodeRabbit outputs, and ticket backend data unless copied into the trace bundle or report bundle;
- inferred workflow state without a corresponding artifact.

`agents/process-tree-auditor.md` remains the topology authority. Evals may consume process-tree reports as evidence, but they do not replace expected-process manifests or emit `PASS | FAIL` topology verdicts. `workflows/audit.md` and workflow-process audit artifacts are companion evidence, not duplicate eval runtime systems.

## Maintenance & drift obligations

When trace surfaces evolve, maintainers must update affected eval specs and runnable adapters before relying on old evidence semantics. The update should name the changed trace source, the affected eval IDs, whether findings remain comparable across old and new traces, and whether lifecycle state must move backward from `ENFORCE` to `ROLL_OUT` or `WRITE`.

Flavor-sensitive evals must record the declared active manager flavor, policy-source file, actual trace decision, and mismatch. They must not flatten `manager-max`, `manager-pragmatic`, and `manager-hackerman` into one generic policy table.

Audit-history integration is caller-owned. Eval reports can be cited in audit-history `report_artifacts` or `role_outputs`, but eval-runner does not become the canonical audit-history writer.

## Anti-scope

- No eval Python code, Rust code, parser code, fixtures, CLI implementation, scheduler, CI, cron, Jira, or Linear routing is defined here.
- No pytest revival and no structural markdown tests. For `~/ai` markdown/operator/workflow/convention/routing/anchor structural-verification routes, forbidden outputs include `tools/<wu>-verify/<anything>.py`, `tests/test_*.py`, pytest imports or fixtures, and pytest-shaped assertion code in any file.
- No required edits to `workflows/index.json`, `AGENTS.md`, agent-runner README, implementation-pipeline hooks, or backend ticket automation.
- No raw SQLite schema or single state DB path is the sole stable contract.
- No redefinition of process-tree, workflow-process, code-quality, coupling, cohesion, or push-pull auditor verdict systems.

## Cross-references

- `workflows/eval-runtime.md`
- `agents/eval-runner.md`
- `conventions/agent-questions-and-session-graph.md`
- `conventions/audit-history.md`
- `conventions/risk-profile.md`
- `agents/process-tree-auditor.md`
- `workflows/audit.md`
- `agents/workflow-process-auditor.md`
- `conventions/code-quality.md`
- ACR-174 pytest removal / deletion contract
