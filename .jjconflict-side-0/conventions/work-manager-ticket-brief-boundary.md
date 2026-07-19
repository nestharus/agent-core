# Work Manager Ticket Brief Boundary

## Declared roles

`validator`, `predicate`, `mapper`, `formatter`, `parser`

This convention validates Work Manager ticket brief shape, predicates allowed and forbidden content by brief kind, maps draft evidence into the pre-posting audit handoff, formats the canonical evidence bundle, and parses that bundle for producer, critic, workflow, and eval consumers. Role tokens come from `/home/nes/ai/conventions/code-quality.md`.

## Purpose

This is the canonical contract for Work Manager-created direct ticket drafts before backend posting. It distinguishes problem-shaped intake from approved implementation briefs, owns the `work-manager-ticket-draft-evidence` schema, and defines the handoff between `/home/nes/ai/agents/work-manager-ticket-filing-operator.md`, `/home/nes/ai/agents/work-manager-ticket-brief-auditor.md`, `/home/nes/ai/workflows/work-manager-ticket-draft-audit.md`, and `/home/nes/ai/worktrees/acr-256-work-manager-over-prescription/evals/acr-256-work-manager-ticket-brief-boundary/eval.md`.

Source contract: `/home/nes/ai/planning/acr-256-work-manager-over-prescription/contracts/acr-256-work-manager-ticket-design.md`.

Related evidence and constraints:

- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/proposals/acr-256-ACR-256.md`
- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-problem-map.md`
- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/research/acr-256-hookpoints.md`
- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/.scratch/phase6/step6b-output-index.md`
- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/.scratch/phase6/step6c-consumed-evidence.txt`
- `/home/nes/ai/planning/acr-256-work-manager-over-prescription/.scratch/phase6/step6c-side-channel-manifest.md`
- `/home/nes/ai/conventions/code-quality.md`
- `/home/nes/ai/conventions/agent-questions-and-session-graph.md`
- `/home/nes/ai/conventions/evals.md`
- `/home/nes/ai/agents/work-manager-operator.md`
- `/home/nes/ai/agents/linear-operator.md`
- `/home/nes/ai/agents/jira-operator.md`
- `/home/nes/ai/agents/ticket-generation-agent.md`
- `/home/nes/ai/agents/workflow-process-auditor.md`
- `/home/nes/ai/agents/agent-design-auditor.md`
- `/home/nes/ai/agents/workflow-design-auditor.md`

## Brief-kind contract

`problem-statement` is used when Work Manager has evidence of a problem, risk, friction, or desired outcome but does not have an approved design source that already owns implementation detail.

Required sections:

- `## Problem statement`
- `## Evidence`
- `## Risk`
- `## Routing`

Optional sections:

- `## Design inputs from root`
- `## Design inputs from work-manager`

Allowed content:

- observed symptoms, evidence paths, ticket or incident references, user-stated constraints, operational risk, unknowns, routing recommendation, and design-input facets framed as questions or constraints;
- concrete artifacts as evidence when they are not presented as selected implementation work.

Forbidden content:

- prescribed solution architecture;
- schema field lists;
- touched-file enumeration;
- sub-WU phase shapes;
- named auditor counts;
- detailed acceptance criteria;
- ticket-template field prescriptions.

`implementation-brief` is used only when technical detail already comes from an approved design, discovery, roadmap, prototype dossier, feature/refactoring plan, proposal, or explicit root design artifact.

Required sections:

- `## Problem`
- `## Approved design source`
- `## Implementation detail`
- `## Out of scope`
- `## Routing`

Required citation:

- every technical detail in `## Implementation detail` traces to `## Approved design source`;
- the approved source must appear in `source_evidence_paths` in the evidence bundle;
- copied detail must preserve the source's constraints and must not add new unapproved architecture, schema, touched-file, phase, auditor, or acceptance-detail prescriptions.

## Evidence bundle schema

`work-manager-ticket-draft-evidence` is the canonical schema consumed by `/home/nes/ai/agents/work-manager-ticket-filing-operator.md`, `/home/nes/ai/agents/work-manager-ticket-brief-auditor.md`, `/home/nes/ai/workflows/work-manager-ticket-draft-audit.md`, and `/home/nes/ai/worktrees/acr-256-work-manager-over-prescription/evals/acr-256-work-manager-ticket-brief-boundary/eval.md`.

```yaml
work_manager_ticket_draft_evidence:
  draft_brief_path: <abs path to the draft brief markdown>
  route_decision_path: <abs path to a markdown artifact recording the routing decision>
  source_evidence_paths: [<list of abs paths to approved-source evidence>]
  active_manager_flavor: <max | pragmatic | hackerman | base>
  backend_target: <linear | jira>
  ticket_kind: <problem-statement | implementation-brief>
  currentness:
    captured_at: <ISO-8601 timestamp>
    captured_against_commit_sha: <sha>
  producer_invocation:
    invocation_uuid: <uuid>
    prompt_path: <abs path>
    log_path: <abs path>
  audit_report_path: <abs path to N3 audit report, written by N4>
  posting_decision: <posted | blocked | revised | routed-to-discovery>
```

The field names above are stable. Consumers must not infer a private schema from draft headings, filenames, backend issue fields, or model-authored status text.

## Pre-posting audit handoff paths

The caller supplies `scratch_dir` and `planning_dir`. The filing operator may choose a run slug, but it must keep these artifact roles explicit:

- draft brief: `${scratch_dir}/work-manager-ticket-draft/<run_slug>/draft-brief.md`
- route decision: `${scratch_dir}/work-manager-ticket-draft/<run_slug>/route-decision.md`
- evidence bundle: `${scratch_dir}/work-manager-ticket-draft/<run_slug>/work-manager-ticket-draft-evidence.yaml`
- N4 prompt: `${scratch_dir}/work-manager-ticket-draft/<run_slug>/work-manager-ticket-draft-audit-prompt.md`
- N4 log: `${scratch_dir}/work-manager-ticket-draft/<run_slug>/work-manager-ticket-draft-audit.log`
- N3 audit report: `${planning_dir}/work-manager-ticket-draft-audits/<run_slug>/brief-audit.md`

Load-bearing proof that these paths existed, were current, and were consumed must come from orchestrator, runner, or helper-authored artifacts under `/home/nes/ai/conventions/agent-questions-and-session-graph.md`, not from the audited model's own read confirmation or self-attestation.

## S5 non-equivalence

`/home/nes/ai/agents/ticket-generation-agent.md` is not precedent for ad hoc Work Manager solution prescription.

S5-generated tickets are roadmap materialization artifacts: they preserve named contracts, schemas, acceptance criteria, dependencies, and estimates from approved upstream roadmap or proposal inputs. Work Manager-created direct filing is different. It may carry technical detail only under the `implementation-brief` contract and only when the approved source chain is recorded in `source_evidence_paths`.

An auditor must not strip or block legitimate S5 technical detail merely because it is technical. The audit question is whether the technical detail is copied from an approved upstream source chain, not whether technical detail exists.

## Backend boundary

`/home/nes/ai/agents/linear-operator.md` and `/home/nes/ai/agents/jira-operator.md` remain mechanical backend posting surfaces. Semantic brief validation belongs to this convention, `/home/nes/ai/agents/work-manager-ticket-filing-operator.md`, `/home/nes/ai/agents/work-manager-ticket-brief-auditor.md`, and `/home/nes/ai/workflows/work-manager-ticket-draft-audit.md` before backend create.

## Eval relationship

Structural verification for this markdown/operator/workflow surface follows `/home/nes/ai/conventions/evals.md`. The WRITE-state eval spec is `/home/nes/ai/worktrees/acr-256-work-manager-over-prescription/evals/acr-256-work-manager-ticket-brief-boundary/eval.md`; this convention does not redeclare the eval lifecycle or finding schema.

## Intrinsic-surface declarations

```yaml
intrinsic_surface_declarations:
  - component: /home/nes/ai/conventions/work-manager-ticket-brief-boundary.md
    role: intrinsic-surface
    Domain: work-manager-ticket-brief-boundary
    Owns:
      - ticket_kind
      - problem-statement content boundary
      - implementation-brief approved-source boundary
      - work-manager-ticket-draft-evidence schema
      - pre-posting audit handoff output paths
      - roadmap-generated ticket non-equivalence
```
