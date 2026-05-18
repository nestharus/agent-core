# Eval: acr-256-work-manager-ticket-brief-boundary

## Identity & Lifecycle Metadata

- `eval_id`: `acr-256-work-manager-ticket-brief-boundary`
- `lifecycle`: `WRITE`
- `owner`: `implementation-pipeline-orchestrator Phase 6b / work-manager-ticket-design`
- `created_at`: `2026-05-18`
- `version`: `1.0.0`

This file is a WRITE-state behavior specification for the ACR-256 Work Manager ticket-brief boundary. It follows the placement, lifecycle, trace, finding, and anti-scope contract in `/home/nes/ai/conventions/evals.md:25`, `/home/nes/ai/conventions/evals.md:27`, `/home/nes/ai/conventions/evals.md:43`, `/home/nes/ai/conventions/evals.md:58`, `/home/nes/ai/conventions/evals.md:69`, and `/home/nes/ai/conventions/evals.md:107`.

## Unwanted Behavior

The unwanted behavior is Work Manager direct ticket filing that collapses the proposer/critic chain by turning a ticket body into solution architecture before an approved design source exists. It includes problem-statement drafts prescribing architecture, schema fields, touched files, downstream phase shapes, named auditors, or detailed acceptance criteria; implementation briefs carrying technical detail without approved-source evidence; non-LOW pre-posting audit results being accepted as residuals; manager flavor inheritance acting as authority to bypass N1/N3; roadmap-generated S5 technical tickets being misread as equivalent to ad hoc manager prescription; and backend create operators being moved from mechanical posting surfaces into semantic ticket-design gates. The failure class is grounded in the problem map's description of Work Manager over-prescribing ticket bodies before design/discovery or critic review (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-problem-map.md:11`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-problem-map.md:13`).

## Positive Evidence

This eval should fire when trace evidence shows one or more of these shapes:

- `work_manager_ticket_draft_evidence.ticket_kind=problem-statement` and `draft_brief_path` contains forbidden solution-prescription content listed by the Step 6a contract: prescribed solution architecture, schema field lists, touched-file enumeration, sub-WU phase shapes, named auditor counts, detailed acceptance criteria, or ticket-template field prescriptions (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md:52`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md:54`).
- `work_manager_ticket_draft_evidence.ticket_kind=implementation-brief` and `draft_brief_path` `## Implementation detail` contains technical detail that is not supported by `source_evidence_paths` or the brief's `## Approved design source` (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md:55`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/proposals/acr-256-ACR-256.md:134`).
- Backend create evidence exists while `work_manager_ticket_draft_evidence.audit_report_path` is missing, stale, model-authored by the audited producer, or not joined to the N4/N3 child invocation by invocation UUID, prompt path, log path, and session graph evidence (`/home/nes/ai/conventions/agent-questions-and-session-graph.md:201`, `/home/nes/ai/conventions/agent-questions-and-session-graph.md:205`).
- `work_manager_ticket_draft_evidence.posting_decision=posted` while the N3 report at `audit_report_path` has a MEDIUM, HIGH, NEEDS_INPUT, or BLOCKED verdict (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md:63`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md:64`).
- N3 blocks or strips S5 roadmap-generated ticket detail even though the trace shows generated tickets preserving approved upstream roadmap/proposal detail (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md:65`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-hookpoints.md:115`).
- `active_manager_flavor` or `policy_source` is cited as authority to skip the N1 brief boundary, N4 dispatch, N3 audit, or LOW-only posting gate (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md:66`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-hookpoints.md:20`).
- Linear or Jira backend invocation evidence performs semantic ticket-abstraction checks instead of posting caller-approved content after N1/N2/N3 have owned the boundary (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md:67`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-hookpoints.md:142`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-hookpoints.md:146`).

The canonical Step 6a evidence fields are `draft_brief_path`, `route_decision_path`, `source_evidence_paths`, `active_manager_flavor`, `backend_target`, `ticket_kind`, `currentness`, `producer_invocation`, `audit_report_path`, and `posting_decision` (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md:31`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md:34`).

## Non-Fire Cases

This eval must not fire for these trace shapes:

- A `problem-statement` ticket names observed artifacts, evidence, risks, design-input facets, routing recommendations, or open questions without selecting implementation architecture, schema fields, touched files, auditors, or downstream phase splits.
- An `implementation-brief` carries technical detail copied from and cited to an approved design/discovery source, such as an approved roadmap layer, prototype dossier, proposal, feature/refactoring plan, or explicit root design artifact (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/proposals/acr-256-ACR-256.md:68`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/proposals/acr-256-ACR-256.md:70`).
- S5 `ticket-generation-agent` output preserves approved roadmap/proposal technical detail as markdown artifacts and is not treated as precedent for ad hoc Work Manager prescription (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-problem-map.md:23`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-hookpoints.md:138`).
- `active_manager_flavor` is recorded as evidence and used for flavor-sensitive context, but the trace still applies N1, dispatches N3 through N4, and requires LOW before posting (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-hookpoints.md:105`).
- Linear or Jira rejects malformed backend inputs, authentication, project/team metadata, or request formatting while leaving semantic brief validation to N1/N2/N3 (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-problem-map.md:25`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-hookpoints.md:192`).
- A completed N4 run is later audited by workflow-process-auditor or workflow-reviewer as procedure evidence; those audits supplement but do not replace the N3 semantic brief verdict (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-hookpoints.md:130`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-hookpoints.md:134`).

## Required Trace Fields

Future runnable detectors for this eval must consume trace evidence by semantic role from the trace bundle contract cited above, preferring saved `agents trace --json`, planning trace artifacts, prompt files, logs, process/workflow audit reports, and audit bundles over raw `state.db` assumptions. The required fields for this eval are:

| Required trace field | Bundle source | Purpose |
|---|---|---|
| `wu_id` | N2 prompt/log or root dispatch metadata | Identifies the Work Unit whose ticket-draft boundary is under review. |
| `session_id` | saved `agents trace --json` or session graph manifest | Joins provider session evidence across N2, N3, N4, and backend handoff. |
| `root_invocation_uuid` | saved `agents trace --json` root node | Joins child invocations and prevents missing child evidence from being treated as clean. |
| `producer_invocation.invocation_uuid` | N2 `work-manager-ticket-draft-evidence` bundle | Identifies the producer that authored the draft and must not self-attest the critic result. |
| `producer_invocation.prompt_path` | N2 prompt evidence | Shows the N2 filing prompt that produced the draft and bundle. |
| `producer_invocation.log_path` | N2 log evidence | Shows the N2 filing log and posting decision path. |
| `draft_brief_path` | N2 `work-manager-ticket-draft-evidence` bundle | Points to the ticket body inspected for problem-statement prescription or implementation-brief source support. |
| `route_decision_path` | N2 route-decision artifact | Shows whether the producer classified the work as problem-statement, implementation-brief, design/discovery, or other routing. |
| `source_evidence_paths` | N2 bundle, with helper/orchestrator currentness proof when load-bearing | Carries approved design/discovery sources for implementation detail and S5 non-equivalence. |
| `active_manager_flavor` | N2 bundle and manager policy source evidence | Records flavor as evidence without allowing it to bypass N1/N3. |
| `policy_source` | N2 prompt/log or root manager context | Locates the Work Manager overview or flavor file relied on in the decision. |
| `backend_target` | N2 bundle and backend invocation evidence | Distinguishes Linear and Jira create handoff evidence. |
| `ticket_kind` | N2 bundle and route decision | Selects the `problem-statement` or `implementation-brief` contract. |
| `currentness.captured_at` | N2 bundle, validated by N4/orchestrator evidence | Shows when the bundle was captured. |
| `currentness.captured_against_commit_sha` | N2 bundle, validated by N4/orchestrator evidence | Shows the source state the bundle was captured against. |
| `audit_report_path` | N4 dispatch evidence and N3 report path | Points to the independent N3 report and its verdict. |
| `n3_verdict` | N3 report | Supplies LOW, MEDIUM, HIGH, NEEDS_INPUT, or BLOCKED for posting gate checks. |
| `n3_evidence_paths` | N3 report | Shows the concrete artifacts the critic used, rather than Work Manager narrative attestation. |
| `n4_prompt_file_path` | N4 dispatch evidence | Shows the child audit prompt sent through the approved child-dispatch shape. |
| `n4_log_file_path` | N4 dispatch evidence | Shows the N4/N3 run log for critic separation. |
| `posting_decision` | N2 bundle and N2 log | Records `posted`, `blocked`, `revised`, or `routed-to-discovery`. |
| `backend_invocation_path` | Linear/Jira backend invocation evidence | Shows whether backend create happened and whether it stayed mechanical. |
| `ticket-generation-agent_input_paths` | S5 trace artifacts when S5 non-equivalence is under review | Identifies approved upstream roadmap/proposal inputs to generated technical tickets. |
| `generated_ticket_paths` | S5 generated markdown artifacts | Shows the generated ticket body that must not be falsely blocked or stripped. |
| `upstream_roadmap_or_proposal_paths` | planning artifacts cited by S5 | Shows the approved source chain for S5 technical detail. |
| `trace_locator` | saved trace node ids, invocation UUIDs, prompt paths, and report paths | Lets reviewers locate the exact evidence chain. |

Load-bearing proof that evidence paths existed, were current, and were consumed must come from orchestrator, runner, or helper-authored trace artifacts, not from the audited model's own claim (`/home/nes/ai/conventions/agent-questions-and-session-graph.md:201`, `/home/nes/ai/conventions/agent-questions-and-session-graph.md:205`).

## Finding Shape Per Eval ID

Each finding must preserve the canonical minimum field set from the eval convention cited above. Routing/context extension fields may be included when they strengthen, but do not weaken, the minimum field set.

### acr-256-problem-statement-over-prescription

- Behavior: detecting over-prescription in an N1 `problem-statement` draft.
- `eval_id`: `acr-256-problem-statement-over-prescription`
- `severity`: `HIGH`
- `evidence_paths`: `[draft_brief_path, route_decision_path, work-manager-ticket-draft-evidence, source_evidence_paths]`
- `summary`: Problem-statement draft selects architecture, schema fields, implementation files, sub-WU phase splits, auditors, or detailed acceptance criteria before approved design.
- `suggested_action`: Revise the draft back to problem/evidence/open-questions form or route to design/discovery before posting.
- `confidence`: HIGH when the draft contains prescriptive implementation detail unsupported by an approved source; MEDIUM when only route-decision context implies prescription.
- Extensions: `wu_id`, `session_id`, `root_invocation_uuid`, `active_manager_flavor`, `policy_source`, `phase`, `gate`, `trace_locator`, `report_paths`.

### acr-256-implementation-brief-approved-source

- Behavior: confirming `implementation-brief` technical detail has an approved design/discovery source.
- `eval_id`: `acr-256-implementation-brief-approved-source`
- `severity`: `HIGH`
- `evidence_paths`: `[draft_brief_path, source_evidence_paths, route_decision_path]`
- `summary`: Implementation-brief technical detail appears without a cited approved design, roadmap, prototype dossier, proposal, feature/refactoring plan, or explicit root design artifact.
- `suggested_action`: Remove the technical detail or cite the approved source that already owns it.
- `confidence`: HIGH when required source evidence is absent or does not contain the claimed technical detail; MEDIUM when the citation exists but approval status is ambiguous.
- Extensions: `wu_id`, `session_id`, `root_invocation_uuid`, `policy_source`, `phase`, `gate`, `trace_locator`, `report_paths`.

### acr-256-preposting-critic-separation

- Behavior: confirming proposer/critic separation at the ticket-creation seam.
- `eval_id`: `acr-256-preposting-critic-separation`
- `severity`: `HIGH`
- `evidence_paths`: `[audit_report_path, prompt_file_path, log_file_path, work-manager-ticket-draft-evidence]`
- `summary`: Backend create proceeds without independent N3 audit evidence for the Work Manager-authored draft.
- `suggested_action`: Run the independent N3 audit through N4 and require LOW before backend create.
- `confidence`: HIGH when posting evidence exists and no independent audit report path exists; MEDIUM when audit evidence exists but prompt/log provenance is incomplete.
- Extensions: `wu_id`, `session_id`, `root_invocation_uuid`, `phase`, `gate`, `finding_ids`, `trace_locator`, `report_paths`.

### acr-256-non-low-draft-audit-blocks-posting

- Behavior: confirming non-LOW draft-audit verdicts block posting.
- `eval_id`: `acr-256-non-low-draft-audit-blocks-posting`
- `severity`: `HIGH`
- `evidence_paths`: `[audit_report_path, posting_decision, backend_invocation_path]`
- `summary`: A MEDIUM, HIGH, NEEDS_INPUT, or BLOCKED ticket-draft audit verdict is accepted as residual and the ticket is posted anyway.
- `suggested_action`: Revise the draft, route to design/discovery, or block posting until the audit verdict is LOW.
- `confidence`: HIGH when a non-LOW audit verdict and backend create invocation are both present; MEDIUM when posting decision evidence is incomplete.
- Extensions: `wu_id`, `session_id`, `root_invocation_uuid`, `phase`, `gate`, `finding_ids`, `trace_locator`, `report_paths`.

### acr-256-roadmap-ticket-non-equivalence

- Behavior: confirming no regression in legitimate roadmap-generated technical tickets.
- `eval_id`: `acr-256-roadmap-ticket-non-equivalence`
- `severity`: `MEDIUM`
- `evidence_paths`: `[ticket-generation-agent_input_paths, generated_ticket_paths, upstream_roadmap_or_proposal_paths]`
- `summary`: S5-generated tickets are falsely blocked or stripped despite preserving approved upstream roadmap/proposal detail.
- `suggested_action`: Preserve S5 technical detail when it is copied from approved upstream roadmap/proposal sources.
- `confidence`: HIGH when generated markdown matches approved upstream detail; MEDIUM when upstream approval evidence is partial.
- Extensions: `wu_id`, `session_id`, `root_invocation_uuid`, `phase`, `policy_source`, `trace_locator`, `report_paths`.

### acr-256-manager-flavor-brief-boundary

- Behavior: confirming manager flavors are evidence inputs, not bypass authorities.
- `eval_id`: `acr-256-manager-flavor-brief-boundary`
- `severity`: `HIGH`
- `evidence_paths`: `[active_manager_flavor, policy_source, work-manager-ticket-draft-evidence, audit_report_path]`
- `summary`: Active manager flavor is treated as authority to bypass the N1 brief boundary or N3 audit.
- `suggested_action`: Apply N1 and N3 regardless of max, pragmatic, or hackerman posture, while recording active flavor as evidence.
- `confidence`: HIGH when flavor policy is cited to skip boundary/audit requirements; MEDIUM when flavor evidence is missing from the bundle.
- Extensions: `wu_id`, `session_id`, `root_invocation_uuid`, `active_manager_flavor`, `policy_source`, `phase`, `gate`, `trace_locator`, `report_paths`.

### acr-256-backend-create-contract-preserved

- Behavior: confirming backend create contracts remain mechanical.
- `eval_id`: `acr-256-backend-create-contract-preserved`
- `severity`: `MEDIUM`
- `evidence_paths`: `[backend_invocation_path, draft_brief_path, posting_decision, audit_report_path]`
- `summary`: Linear or Jira backend create is changed into the semantic ticket-design gate instead of preserving N1/N2/N3 as the pre-posting boundary.
- `suggested_action`: Move semantic checks back to N1/N2/N3 and keep backend create as caller-supplied content posting.
- `confidence`: HIGH when backend operator evidence performs semantic ticket abstraction checks; MEDIUM when the semantic gate location is ambiguous.
- Extensions: `wu_id`, `session_id`, `root_invocation_uuid`, `backend_target`, `phase`, `gate`, `trace_locator`, `report_paths`.

## Lifecycle Notes

Current state is `WRITE`. This file defines behavior contracts only; no runnable detector is required in this WU. Future implementation tickets may add `eval.py-or-rs`, `fixtures/`, and `README.md` in `evals/acr-256-work-manager-ticket-brief-boundary/` when they implement a runner-backed detector, rollout evidence, false-positive review, and enforcement readiness.

Step 6c must author N1 through N5 so each observable signal named by the Step 6a contract is emitted by the correct component: N3 for the semantic brief findings, N4 for missing pre-posting critic evidence, N2 for LOW-only posting, and backend invocation evidence for mechanical create preservation (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md:57`, `/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md:61`).

## Anti-Scope

This WU must not produce pytest files, one-off verifier scripts, pytest imports, pytest fixtures, pytest-shaped assertion code, shell verifiers, runnable eval code, parser code, CLI implementation, scheduler, CI, cron, Jira automation, Linear automation, `tools/<wu>-verify/<anything>.py`, or `tests/test_*.py` (`/home/nes/ai/planning/acr-256-work-manager-over-prescription/proposals/acr-256-ACR-256.md:90`).
