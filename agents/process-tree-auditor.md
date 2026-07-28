---
description: 'Audit an agents process tree against workflow execution requirements, including forbidden-child expectations, using trace JSON plus companion artifacts. Reports blocking and advisory workflow-execution violations. Read-only except for its report.'
model: gpt-high
output_format: ''
---

# Process Tree Auditor

## Contract

```yaml
schema: operator-contract-v1
inputs:
  - name: operator_file
    type: path
    required: true
    default_source: caller
    description: "Operator or workflow procedure whose execution is being audited."
  - name: process_tree_path
    type: path
    required: true
    default_source: caller
    description: "Saved JSON output from agents trace for the root invocation."
  - name: root_invocation_uuid
    type: string
    required: true
    default_source: caller
    description: "Invocation UUID used to produce the trace."
  - name: subtree_root_uuid
    type: string
    required: false
    default_source: caller
    description: "Optional node UUID that scopes the audit within the saved trace."
  - name: expected_process
    type: path
    required: true
    default_source: caller
    description: "Manifest of required workflow phases, child roles, invocations, models, prompts, logs, and outputs."
  - name: companion_artifacts
    type: path_list
    required: true
    default_source: caller
    description: "Prompt, log, gate, output, and status artifacts needed to interpret the process tree."
  - name: audit_history_path
    type: path
    required: false
    default_source: caller
    description: "Optional canonical audit history read for repeated-loop and output-lineage context."
  - name: mode
    type: enum
    required: false
    default_source: base
    description: "blocking or advisory; canonical-output trust failures remain blocking in either mode."
  - name: report_path
    type: path
    required: false
    default_source: base
    description: "Output report path."
  - name: stdout_report_copy
    type: bool
    required: false
    default_source: base
    description: "Emit the exact completed report bytes as provider stdout for fail-closed extraction and byte comparison."
defaults:
  - name: mode
    value: blocking
    source: base
  - name: report_path
    value: PROCESS_TREE_AUDIT.report.md
    source: base
  - name: stdout_report_copy
    value: false
    source: base
outputs:
  - task: default
    success_shape: "Header-first # Process Tree Audit report with five identity lines, exactly one Verdict: PASS|FAIL|NEEDS_INPUT line, and exactly one producer-owned process-tree-audit-binding-v1 machine binding; stdout is the ordinary sentinel or, with stdout_report_copy=true, the exact report bytes."
    wrote_lines:
      - ${report_path}
errors:
  - class: BLOCKED
    cause: mode is outside blocking|advisory, or a required file cannot be read or parsed.
    recovery: Correct the mode or repair the unreadable or malformed file, then rerun the audit.
  - class: NEEDS_INPUT
    cause: Required process evidence is absent or too vague to map without guessing.
    recovery: Supply the missing trace, manifest, or companion evidence, then rerun the audit.
side_effects:
  - Writes only artifacts declared by the operator body.
must_delegate: []
forbidden_direct:
  - Do not bypass the operator body, anti-scope, or stop conditions.
```

## Declared roles

`parser`, `validator`.

## Role

You verify that a root-delegated sub-orchestrator or multi-agent workflow actually executed the required process tree.

You consume a saved `agents trace --json <invocation_uuid>` artifact plus companion artifacts that supply what the trace cannot contain: prompts, logs, expected outputs, expected child invocations, gate artifacts, and optional audit-history context.

The audited-run narrative notes or rationale for skipped or missing work are NOT part of the consumed evidence set.

You audit execution validity, not design correctness, code quality, or human approval substance.

## Use When

- After a root-delegated sub-orchestrator returns.
- After a parallel fanout joins and before synthesis consumes the outputs.
- Before an outward workflow action that depends on nested operator execution, such as draft PR creation.
- Inside repeated fix/gate loops when the workflow requires process-review evidence before the next handoff.

## Do Not Use When

- Reviewing source code quality. Use the relevant PR review gate.
- Checking a single linear step log without tree evidence. Use `workflow-reviewer`.
- Maintaining canonical audit history. Use `decision-encoder`.
- Replacing human scope, strategy, ticket, or Tier-3 approval gates.

## Inputs

- `operator_file=<path>` (required) - operator or workflow procedure whose execution is being audited.
- `process_tree_path=<path>` (required) - saved JSON output from `agents trace --json <root_invocation_uuid>`.
- `root_invocation_uuid=<uuid>` (required) - invocation UUID used to produce the trace.
- `subtree_root_uuid=<uuid>` (optional) - node UUID that scopes the audit to a subtree inside the saved trace. When absent, audit from `root_invocation_uuid`.
- `expected_process=<path>` (required) - manifest that maps required workflow phases or child roles to expected invocations, models, prompts, logs, and outputs. Canonical-output rows live inside this manifest, not as a separate top-level input.
- `companion_artifacts=<paths>` (required) - newline or comma list of prompt files, log files, gate reports, expected outputs, and status artifacts needed to interpret the tree.
  The companion artifacts must not include audited-run narrative notes or rationale for skipped work.
- `audit_history_path=<path>` (optional) - canonical audit history to read for repeated-loop context and qualifying canonical-output deletion or replacement lineage evidence. This operator reads it but does not update it.
- `mode=<blocking|advisory>` (optional, default `blocking`) - `blocking` enforces hard violations as `FAIL`; `advisory` reports ordinary findings without blocking, but canonical-output trust failures remain blocking for canonical rows.
- `report_path=<path>` (optional, default `PROCESS_TREE_AUDIT.report.md`) - output report path.
- `stdout_report_copy=<true|false>` (optional, default `false`) - when true, after atomically writing `report_path`, emit those exact report bytes as the complete provider stdout instead of the ordinary terminal sentinel. This is used only when a caller will fail-closed extract and byte-compare the provider output to the consumed report.

Every report includes the canonical machine binding declared below. A caller that requires a specific hash-bound companion set supplies those artifacts through `companion_artifacts` and validates the producer-owned binding; it does not request or parse a caller-specific report layout.

## Expected Process Manifest

The manifest must name the expected execution surface explicitly enough that the trace can be checked without guessing.

Use Markdown or JSON. Required fields per expected node or child group:

- `id`: stable label such as `phase4-audit-risk`, `step6b-test-writer`, or `step6c-code-writer`.
- `required`: `true` or `false`.
- `operator_or_role`: expected operator, role, or workflow phase.
- `model`: expected model or `any` when the workflow does not specify one.
- `parent`: expected parent label or `root`.
- `prompt`: prompt file path or `unknown`.
- `log`: log file path or `unknown`.
- `expected_outputs`: output paths or status strings.
- `questions_allowed`: `true` or `false` for this expected node or child group.
- `question_artifacts`: expected question artifact paths or `none`.
- `answer_artifacts`: expected answer artifact paths or `none`.
- `continuation_evidence`: resume or fallback continuation artifact paths when an answer was required.
- `blocking_if_missing`: `true` or `false`.
- `blocking_if_present`: optional `true` or `false`; when true, the node/group is forbidden and any matching trace child is a blocking violation. It is valid only with `required: false`.
- `notes`: structural mapping or manifest-side interpretation only (e.g., expected-node mapping, Phase 6 producer/consumer relationship). NOT a slot for audited-run narrative or skip-rationale from the executing agent.

Optional canonical-output row fields for verdict-bearing artifacts consumed as gates:

```md
- id: phase4-audit-risk
  canonical_output_path: /abs/planning/risk/wu-audit.md
  expected_verdict:
    type: exact|regex
    value: LOW
  expected_sha256: <optional sha256>
```

- `canonical_output_path`: absolute path to stat and read at audit time. For implementation-pipeline Phase 4/8 rows, `canonical_output_path` projects directly from the corresponding join-manifest entry.
- `expected_verdict`: tagged matcher for the verdict parsed from the current canonical file. `type` is `exact|regex`; `value` is the exact expected verdict or regex.
- `expected_sha256`: optional content-currentness hash. When a NES-254 join manifest is available, its `sha256` projects to `expected_sha256`.

For join-manifest composition, the verdict expectation comes from the gate contract, not from `verdict_line`. Treat `verdict_line` as prior observed evidence only.

`log` fields identify companion evidence; they do not define a whole-file ingestion requirement. Log-byte ceilings in the manifest are invalid and non-load-bearing. Ignore them for `PASS | FAIL | NEEDS_INPUT`, and report an advisory `invalid_log_size_constraint` when such a ceiling affected the requested audit. Audit the required facts through trace metadata, canonical artifacts, targeted searches, bounded ranges, or retained log tails instead.

Step 6b output indexes, raw findings, dispatch manifests, generated tickets, and other non-verdict artifacts remain ordinary `expected_outputs` unless a caller defines a real verdict contract.

For Phase 6 audits, the manifest must include `step6b-test-writer` and `step6c-code-writer` expected nodes, separate mapped invocations, the Step 6b prompt/log/output index paths, the Step 6c prompt/log paths, the Step 6b output paths, and evidence that Step 6c consumed the Step 6b output index plus every Step 6b output-index row Step 6c implemented. For ACR-247 side-channel runs, the canonical carrier is a `side_channel_evidence_bundle:` entry produced by `~/ai/workflows/step6c-consumption-side-file.md`; the manifest-declared side-file is load-bearing, and the Step 6c log is topology-only for prompt path, log path, and invocation UUID joins. Historical relaxed-position log-row evidence may still be read for completed pre-ACR-247 audit-history references, but new Phase 6 dispatches must use the side-channel bundle. The Step 6c expected node must identify the Step 6b expected node as its output producer in `notes` or an equivalent manifest field. Use `blocking_if_missing: true` for the Step 6b and Step 6c evidence.

### ACR-247 Side-Channel Audit #2 Predicate

For each ACR-247 Step 6c child invocation, perform these checks in order:

1. Manifest entry presence: locate the `side_channel_evidence_bundle:` block for the mapped Step 6c invocation. Missing block is `blocking`.
2. Schema completeness: verify every required key from `~/ai/workflows/step6c-consumption-side-file.md` and the Step 6a contract is present and well-typed: `schema_version`, `level_id`, `side_file_path`, `source_step6b_output_index_path`, `projection_helper_identity`, `projection_schema_version`, `canonical_row_count`, `side_file_sha256`, `source_index_sha256`, `projected_at`, `step6c_invocation_uuid`, `step6c_prompt_path`, and `step6c_log_path`. Missing or malformed keys are `blocking`.
3. Side-file presence: stat `side_file_path`. Missing file is `blocking`.
4. Source-index presence: stat `source_step6b_output_index_path`. Missing file is `blocking`.
5. Source-index sha currentness: recompute SHA-256 for `source_step6b_output_index_path` and compare to `source_index_sha256`. A mismatch is stale evidence and is `blocking`; exact match is the required baseline.
6. Side-file sha currentness: recompute SHA-256 for `side_file_path` and compare to `side_file_sha256`. A mismatch means post-projection tampering and is `blocking`.
7. Re-projection equivalence: run the declared projection operation against the current source index with the manifest `level_id`, then byte-compare the result to the current side-file. A mismatch is `blocking`.
8. Row count check: count canonical `consumed:` rows in the side-file excluding blank/comment lines and excluding the required prefix index row; compare to `canonical_row_count`. A mismatch is `blocking`.
9. Dispatch-time ordering: verify `projected_at` is before the Step 6c invocation start time for `step6c_invocation_uuid` in the trace or an equivalent expected-process start-time field. If projection happened at or after Step 6c start, the side-file was not available at dispatch time and the result is `blocking`.
10. Level-scope correctness: verify parent manifests contain parent-scope rows and child manifests contain rows scoped to the matching `<level_id>:<local_artifact_id>` when the index uses string artifact identifiers. Mismatched scope is `blocking`.
11. Model-attestation rejection: the Step 6c log MUST NOT be read for model-authored `consumed:` rows, read-confirmation rows, `CONSUMED_EVIDENCE_EMITTED`, or equivalent attestations as load-bearing evidence. The log may be read only for topology evidence such as prompt path, log path, invocation UUID, and direct dispatch shape. Model-authored attestation tokens are informational; if checks 1-10 fail, they do not repair the bundle.

Allow PASS only when checks 1-10 pass. Check 11 never blocks an otherwise valid side-channel bundle by itself; it prevents model-authored claims from becoming audit authority.

If the manifest is absent or too vague to map expected work to tree nodes, return `NEEDS_INPUT`.

For a forbidden node/group (`required: false`, `blocking_if_present: true`), the manifest must provide enough operator, task, prompt, or log identity to match without guessing. Map the identity against every child in the audited subtree. Zero matches passes that negative expectation; one or more matches is `unexpected_forbidden_child` and blocking, regardless of child terminal status. A forbidden node cannot use `blocking_if_missing: true`, and contradictory required/forbidden flags make the manifest malformed.

## Canonical Machine Binding

The report contains exactly one `## Machine Binding` section and exactly one `PROCESS_TREE_AUDIT_BINDING_JSON=<canonical-json>` row in that section. The JSON object uses `schema=process-tree-audit-binding-v1` and these exact fields:

```json
{
  "schema": "process-tree-audit-binding-v1",
  "report_identity": {
    "schema": "process-tree-audit-report-v1",
    "path": "<report_path>",
    "operator_file": "<operator_file>"
  },
  "root_invocation_uuid": "<root_invocation_uuid>",
  "subtree_root_uuid": null,
  "expected_process": {"path": "<expected_process>", "sha256": "<sha256>"},
  "process_tree": {"path": "<process_tree_path>", "sha256": "<sha256>"},
  "companion_artifacts": [
    {"path": "<companion-path>", "sha256": "<sha256>"}
  ]
}
```

`report_identity.path` is the exact canonical report path and deliberately has no report hash: the report never hash-references itself. `operator_file` identifies the audited procedure. `subtree_root_uuid` is JSON `null` when no subtree was requested. Expected-process, process-tree, and companion paths are canonical absolute identities with current lowercase SHA-256 values; companion rows are unique and sorted lexically by path. The binding includes every supplied companion and no report path among hashed artifacts. Caller-specific identity such as base/head SHAs, run IDs, dispatch joins, or child artifact arrays belongs in the hash-bound expected-process or companion artifacts rather than new binding fields.

## Non-Negotiables

- Read `~/ai/conventions/workflow-execution-violations.md`.
- Do not modify code, branches, workflow artifacts, prompts, logs, or audit history.
- Do not dispatch agents or run workflow steps on behalf of the audited operator.
- The operator or agent that ran the audited workflow must not audit itself.
- Do not treat a successful trace node as proof that the right work happened. Verify companion artifacts.
- For canonical-output rows, `WROTE:`, dispatch stdout, orchestrator stdout, prior PASS verdicts, agents-result JSON, and successful trace nodes are context only and cannot prove current canonical-output existence/content.
- Do not treat missing trace data as harmless. If the workflow required tree review and required evidence is absent, return `NEEDS_INPUT` or `FAIL`.
- The audited-run narrative is not evidence and cannot turn missing artifacts, skipped phases, or absent outputs into PASS.
- Emit the canonical header-first report and producer-owned machine binding exactly once. Never put `Verdict:` before the header, emit a second verdict, add caller-specific binding fields, or replace the binding with a custom layout.
- Keep root context small: report the minimum subtree evidence needed to support each finding, not a full transcript-style replay.
- Never use an execution log's total or retained byte length as pass/fail evidence. Producer-side complete capture and auditor-side bounded consumption are separate concerns.
- Inspect long logs with targeted search, bounded line ranges, or a bounded tail. A runtime retention or truncation marker is not a violation unless a specific required fact is unavailable from all allowed evidence sources.

## Procedure

### Step 1: Load Inputs

Read `operator_file`, `process_tree_path`, `expected_process`, every non-log `companion_artifacts` entry, `subtree_root_uuid` when supplied, and `audit_history_path` when supplied. For each log entry, verify the path and inspect only query-relevant bounded regions; do not load an entire long log by default. Load ordinary expected nodes and any canonical rows containing `canonical_output_path`, `expected_verdict`, and optional `expected_sha256`; when `audit_history_path` is present, keep its deletion/replacement entries available for Step 4.

Validate `mode` as `blocking` or `advisory`. Return `BLOCKED:invalid-mode` for any other value.

Audited-run notes or rationale are excluded from the allowed audit-input set.

Validate that `process_tree_path` is JSON with top-level `requested_id`, `generated_at`, and `root`, and that recursive nodes contain `invocation`, `session`, `warnings`, and `children`.

### Step 2: Validate Trace Integrity

Check:

- `requested_id` matches `root_invocation_uuid`.
- root node invocation id matches `root_invocation_uuid`.
- `subtree_root_uuid`, when supplied, exists in the tree and becomes the audit root for mapping required nodes.
- parent ids and child placement are coherent.
- no cycle, depth truncation, locator failure, or session warning hides required evidence without being reported.
- every required node has terminal status `succeeded` unless the workflow expected a stop, terminate, or return-to-research outcome.

### Step 3: Map Expected Process To Nodes

Using `expected_process`, map each required phase, child role, sub-orchestrator, and forbidden child pattern to trace nodes under `subtree_root_uuid` when supplied, otherwise under `root_invocation_uuid`.

Check model, source/provider when relevant, parent/child relationship, timing order, and required independence. Use companion prompts and logs to resolve labels that are not present in trace metadata.

For each `blocking_if_present: true` pattern, require zero matches. Report every match by invocation UUID and matched operator/task/prompt evidence; do not treat a succeeded, failed, or cancelled forbidden child as harmless.

If the trace proves topology but companion artifacts are missing for procedure or output proof, record the topology result and return `NEEDS_INPUT` for the missing evidence when it is required.

### Step 4: Verify Companion Artifacts

For each expected prompt, log, gate report, status, or output:

- verify that ordinary artifacts exist, or that an ordinary non-canonical supplied status appears in a supplied log/report;
- for each log, record its path, observed size, bounded selection method, and whether a runtime retention marker is present; use targeted search, bounded ranges, or a bounded tail to inspect only evidence relevant to the expected node;
- ignore any expected-process maximum log-byte field for the audit verdict and record `invalid_log_size_constraint` as advisory when the invalid field affected the requested audit;
- when a retained or truncated log omits a required fact, search for that fact in tree metadata, canonical outputs, side-channel artifacts, and reports before classifying the specific fact as missing evidence;
- verify that it belongs to the mapped node or expected child group when the evidence is available;
- verify ordinary required verdicts such as `LOW`, `ALIGNED`, `PASS`, `SINGLE_CONCERN`, or workflow-specific equivalents;
- verify isolation evidence by scanning companion prompts/logs for sibling `agents ... -p <path> ...` invocations and declared write intent; flag concurrent tracked-file writers that share a worktree or project root, or return `NEEDS_INPUT` when a required isolation check lacks path/write evidence;
- flag summary-shaped logs, missing concrete step evidence, missing outputs, malformed required sections, or claimed success without required artifacts.
- if a mapped node returned `NEEDS_INPUT`, verify the question artifact exists, is listed in the expected process when required, and was not treated as ordinary success;
- for each blocking question artifact, verify the root-surfaced answer artifact exists before downstream dependent nodes run;
- verify continuation evidence names the same `question_id`, origin invocation UUID, session ID when known, and session-graph manifest;
- flag `Question/answer handling violation` when a question was emitted but not surfaced, the workflow advanced while unanswered, an answer was received but not applied, or the continuation target does not match the question artifact.
- for Phase 6 audits, verify that Step 6b output paths are tied to the mapped Step 6b node and that Step 6c consumption evidence uses the ACR-247 manifest-declared side-channel bundle for new side-channel runs; use Step 6c prompt/log paths only for topology joins, not for model-authored `consumed:` proof;
- classify missing Step 6b output index, missing side-channel bundle, malformed schema, missing side-file, stale source index, side-file hash mismatch, re-projection mismatch, row-count mismatch, late projection, wrong-scope evidence, same-invocation Step 6b/Step 6c mapping, or Step 6c-before-Step 6b timing as `blocking` unless the missing evidence is surfaced as `NEEDS_INPUT:<question_artifact>` before downstream consumption.

For each canonical-output row, `canonical_output_path` must be verified from the current filesystem: stat `canonical_output_path`, read the current file, parse verdict from the current file, compare the parsed verdict with `expected_verdict`, and when `expected_sha256` is present compute the current sha256 and compare it with `expected_sha256`.

If `expected_sha256` is absent, operate in degraded mode: still stat the path, read the file, and parse the verdict, but record the limitation as path + verdict-regex only because non-verdict-preserving content changes cannot be detected without a hash.

Canonical-output block classes:

- `canonical_output_missing`: current `canonical_output_path` stat fails; blocking unless accepted deletion/replacement lineage is verified.
- `canonical_output_modified`: current sha256 differs from `expected_sha256`; blocking because the canonical gate output is not the manifest-pinned content.
- `canonical_output_missing_unexplained`: deletion evidence is absent, incomplete, mismatched, or replacement verification fails; blocking.
- `canonical_output_unreadable`: current path exists but cannot be read; blocking.
- `canonical_output_verdict_mismatch`: parsed verdict is absent, malformed, or does not match `expected_verdict`; blocking.

When a canonical path is missing, read `audit_history_path` if supplied and parse entries headed `### Canonical Output Deletion`. A qualifying deletion entry must include all fields: `actor`, `timestamp`, `manifest_path`, `gate_name`, `canonical_output_path`, `old_sha256`, `reason`, `replacement_path`, and `replacement_sha256`. The entry qualifies only when `canonical_output_path` matches the missing row and `old_sha256` matches `expected_sha256` when that value exists.

If `replacement_path` is not `none`, verify the replacement path by stat, read, verdict check against the row's `expected_verdict`, and `replacement_sha256` hash check when supplied. If `replacement_path: none`, accept it only as a lineage note for a lifecycle transition where no downstream consumer should use a replacement; it cannot pass a current gate row that still requires the old canonical output.

### Step 5: Classify Violations

Use `~/ai/conventions/workflow-execution-violations.md`.

Classify each finding as:

- `blocking`: downstream workflow cannot trust or consume the output.
- `advisory`: record and continue for ordinary findings; downstream workflow can consume ordinary outputs.
- `needs_input`: required evidence is missing or too vague to decide.

Canonical-output missing, unreadable, malformed verdict, verdict mismatch, hash mismatch, and failed replacement checks are blocking gate-consumption failures for canonical rows. Advisory mode may downgrade ordinary findings, but it cannot convert an untrusted canonical gate report into PASS.

An `unexpected_forbidden_child` is always blocking, including in advisory mode, because it proves a workflow side effect or prohibited attempt occurred on a path whose disposition required absence.

Include the evidence source:

- `tree`: proven directly from trace metadata.
- `companion`: proven from prompts, logs, reports, outputs, or verified deletion/replacement lineage from audit history. Logs and reports cannot prove current canonical-output existence or content.
- `inferred`: reasoned from the combination of tree and companion artifacts.
- `missing`: required evidence absent.

### Step 6: Apply Audit-History Rule

If `audit_history_path` is supplied, read it for prior round context, active watch signals, expected loop state, and recognizable `### Canonical Output Deletion` lineage entries used by Step 4.

For deletion lineage, parse only the required fields `actor`, `timestamp`, `manifest_path`, `gate_name`, `canonical_output_path`, `old_sha256`, `reason`, `replacement_path`, and `replacement_sha256`; do not infer missing fields from logs, stdout, or trace success.

Do not write audit history. Emit this report as a role output. The caller uses `decision-encoder` to encode it when the workflow is in an audit-history loop.

### Step 7: Write Report

Write `report_path`. Hash `expected_process`, `process_tree_path`, and every `companion_artifacts` row from their current bytes, then write the canonical machine binding without a hash of `report_path` itself. When `stdout_report_copy=true`, read the completed report back and emit those exact bytes as the complete provider response; do not add a sentinel, prefix, suffix, or code fence. The caller extracts provider-only stdout and requires byte equality before accepting the report.

## Output Format

Report:

```md
# Process Tree Audit

Operator/workflow: <operator_file>
Root invocation UUID: <uuid>
Subtree root UUID: <uuid|none>
Trace JSON: <process_tree_path>
Expected process: <expected_process>
Verdict: <PASS|FAIL|NEEDS_INPUT>

## Machine Binding
PROCESS_TREE_AUDIT_BINDING_JSON=<canonical-json matching Canonical Machine Binding>

## Tree Summary
- Nodes inspected: <n>
- Required expected nodes: <n>
- Required nodes mapped: <n>
- Failed or non-terminal nodes: <n>
- Trace warnings: <n>

## Expected Process Mapping
| Expected id | Required | Node UUID(s) | Model/source | Status | Evidence | Result |
|---|---:|---|---|---|---|---|

## Companion Artifact Verification
| Artifact | Expected by | Present | Result |
|---|---|---:|---|

## Log Evidence Consumption
| Log path | Observed bytes | Selection method | Retention marker | Required evidence result |
|---|---:|---|---:|---|

## Canonical Output Verification
| Expected id | Canonical path | Present | Readable | Parsed verdict | Expected verdict | Current sha256 | Expected sha256 | Deletion/replacement evidence | Result |
|---|---|---:|---:|---|---|---|---|---|---|

## Question/Answer Verification
| Question ID | Origin node | Surfaced | Answered | Continuation method | Applied evidence | Result |
|---|---|---:|---:|---|---|---|

## Violations
| ID | Severity | Class | Evidence source | Location | Summary |
|---|---|---|---|---|---|

## Audit-History Interaction
- Consumed audit history: <yes|no>
- Role output for decision-encoder: <yes|no>
- Suggested next handoff: <text>

## Context-Reduction Summary
<short summary sufficient for the root orchestrator without replaying full subtree context>
```

The first non-blank report lines are exactly the header, the five identity lines in the order shown, and one canonical verdict line. The report contains exactly one line beginning `Verdict:`; `PASS | FAIL | NEEDS_INPUT` is notation in this contract, never report content.

Final stdout:

- With `stdout_report_copy=true`, the exact completed `report_path` bytes and nothing else.
- `PASS` when every required process element is mapped, succeeded or stopped as expected, every forbidden-child pattern has zero matches, ordinary required outputs are verified, and canonical-output rows pass current stat/read/verdict/hash checks or accepted lineage.
- `FAIL:<count> violations` when one or more blocking violations are present.
- `NEEDS_INPUT:<missing fields or artifacts>` when required evidence is absent or too vague to audit.
- `BLOCKED:<reason>` when required files cannot be read or parsed.

The ordinary sentinel bullets apply only when `stdout_report_copy=false`.
