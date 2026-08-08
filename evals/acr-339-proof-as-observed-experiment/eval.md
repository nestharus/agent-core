---
id: acr-339-proof-as-observed-experiment
slug: acr-339-proof-as-observed-experiment
eval_id: acr-339-proof-as-observed-experiment
lifecycle: WRITE
lifecycle_state: WRITE
created: 2026-08-08
risk_class: HIGH
scope: Repository-wide behavioral-proof authority, evidence-role separation, and synchronized public terminology
behavior_class: Expected-versus-observed experiment evidence and review-boundary integrity
severity_when_fires: HIGH
evidence_source_kinds:
  - convention
  - operator
  - workflow
  - optimized-contract
  - generated-index
  - executed-experiment-record
  - eval-specification
suggested_action_class: restore-experiment-evidence-authority-and-synchronized-contracts
supersedes: []
---

# ACR-339 Proof as Observed Experiment Eval

## Purpose

This WRITE-state specification defines acceptance intent for the repository's
behavioral-proof vocabulary and evidence-role boundaries. It is not executable
and is not evidence that any scenario ran or passed.

The canonical rule comes from `conventions/behavioral-proof.md`: behavioral
proof is the recorded comparison between the expected result of a named
experiment and the observed result produced when that experiment is executed
against the named target. Model reading, favorable review, validation,
packaging, and PR prose may assess or present evidence but do not produce the
experiment's observed result.

## Trace Roles

- `experiment_producer`: runner, deterministic inspection, build/runtime
  invocation, or recorded application interaction that produces an observation.
- `plan_reviewer`: `verification-plan-reviewer`, which judges pre-execution
  completeness, executability, directness, expected observation, and proxy risk.
- `integrity_reviewer`: `validation-integrity-auditor`, which judges whether an
  actual diff or supplied evidence weakens or substitutes a validation surface.
- `evidence_consumer`: validator, packager, adapter, writer, model reviewer, or
  human reviewer that reads, transports, or presents an existing record.
- `projection_producer`: workflow-index generator that deterministically
  projects authoritative workflow frontmatter.
- `process_validator`: topology/currentness/hash validator whose result concerns
  process integrity rather than application behavior.

## Finding Contract

Every future finding preserves:

- `eval_id`
- `scenario_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`
- `claim`
- `expected_observation`
- `observed_result_ref`
- `evidence_role`
- `active_identity`
- `blocks_pipeline`

## Canonical Term Model

| Term | Required meaning |
|---|---|
| Experiment | Executed command or action against a named target. |
| Expected result | Observation declared before the experiment executes. |
| Observed result | Actual status, output, artifact difference, runtime response, or application observation produced by execution. |
| Behavioral proof | Record comparing expected and observed results at a stated target and scope. |
| Review | Assessment of a plan, source, diff, log, artifact, or evidence record. |
| Verification-plan assessment | Pre-execution review; favorable assessment authorizes execution only. |
| Pending production behavior test | Fail-expected implementation contract, not passing production evidence. |
| Process proof | Invocation topology, currentness, and artifact-integrity evidence, not behavioral evidence. |

## Scenarios

| Scenario | Required behavior | Fire condition | Non-fire case |
|---|---|---|---|
| `B01` | One canonical definition owns behavioral proof. | An active source defines a competing authority or omits the canonical citation where it makes a behavioral-proof claim. | `conventions/behavioral-proof.md` is authoritative and active callers cite it. |
| `B02` | Tests, deterministic inspections, build/execution, and recorded application use are recognized experiment classes. | An active policy excludes one class or treats an unexecuted artifact as that class. | Every class retains command/action, target, expected, observed, and status/provenance. |
| `B03` | Semantic analysis is review, critique, hypothesis, or plan assessment. | Model reading or a favorable verdict claims that behavior occurred. | Review is explicitly bounded to assessment. |
| `B04` | The semantic reviewer uses verification-plan identity. | An active route, source, sidecar, gate, report, finding, or eval selects the retired semantic identity. | All active projections select `verification-plan-reviewer` and `verification-plan-review`. |
| `B05` | Verification plans use four exact fields. | `Behavior claim`, `Experiment command or action`, `Expected observation`, or `Claim-experiment fit` is absent, duplicated, or renamed. | One exact `## Verification plan` contains all four fields. |
| `B06` | Plan review rejects proxy substitution while allowing honestly narrowed scope. | A broad runtime/application claim is accepted from a proxy-only experiment. | The claim is narrowed to the proxy fact or a direct experiment is required. |
| `B07` | Post-change passing claims cite execution and observed results. | Proposal text, model judgment, file presence, or a favorable review substitutes for a run record. | Exact action, target, expected, observed, output, and status are retained. |
| `B08` | Implementation Phase 3/4/6/8 keeps plan review separate from run evidence. | A plan-review row is used as post-change execution evidence or claim roles are collapsed. | Plan, behavior claim, runtime claim, and executed evidence retain distinct fields and rows. |
| `B09` | RCA reviews before application and reruns the original signal after application. | Either the fix-decision review or the exact original-signal rerun is absent or substituted by the other. | Both current artifacts exist and block independently. |
| `B10` | Code-quality separates plan review from validation-integrity review. | One row aliases the other, uses the wrong model/inputs, or claims to execute behavior. | Each reviewer receives its own context and reports only its stated assessment. |
| `B11` | Prototype discovery separates observed prototype results, pending production contracts, and model review. | Pending tests are called passing evidence or model review is called the prototype experiment. | State-specific terminology and no-silent-drop carry-forward remain explicit. |
| `B12` | Shippable-prototype evidence remains run-backed. | Behavior-test, QA expected/observed, screenshot, or deep-rebuild evidence is omitted or replaced by bundle/prose acceptance. | All four evidence families remain explicit in the experiment-evidence bundle. |
| `B13` | Validators, packagers, adapters, writers, and reviewers are consumers/formatters. | A consumer claims its own acceptance or output produced the observed behavior. | The consumer names the record it read and the artifact it wrote without claiming execution. |
| `B14` | Operators, contracts, routing, roles, reports, manifests, evals, and generated metadata use one terminology. | Source, sidecar, caller, or generated projection disagrees on an active identity or field. | The active graph is synchronized from authoritative sources. |
| `B15` | Workflow index is deterministically generated and current. | The canonical read-only check is nonzero or prose/model comparison substitutes for it. | Generation completes and the final canonical check exits zero. |
| `B16` | Model reading cannot claim behavior was demonstrated. | Reading source, plans, logs, diffs, screenshots, or evidence records is described as the experiment. | The model reports only review conclusions and cites the independent producer. |
| `B17` | No ambiguous compatibility alias exists without a concrete reader. | A retired operator, gate, report, field, or route remains selectable without persisted-schema and reproduced-reader evidence. | Historical records retain bytes but active dispatch has no old-name alias. |
| `B18` | Generic process validation keeps its distinct authority. | Process-tree, currentness, or hash PASS is represented as application behavior, or is weakened during the semantic migration. | Existing process-proof contracts remain unchanged and topology-only. |

## Positive Evidence

A future detector fires when active source or runtime evidence satisfies any
scenario's fire condition. The finding must cite the exact active producer and
consumer paths, not only a repository-wide search summary.

## Non-Fire Rules

- Historical `DECISIONS.md`, persisted reports, and deprecated frozen-snapshot
  consumers may retain old bytes when active dispatch does not select them.
- A negative fixture may quote retired or misleading wording when the fixture
  clearly identifies it as the behavior under detection.
- `runtime_claim` remains valid for post-change validation-integrity context; it
  is not an alias for pre-execution `behavior_claim`.
- Process-proof terminology remains valid for topology, currentness, and hash
  integrity.
- A WRITE eval file may define acceptance intent but never counts as a passing
  execution result.

## Required Cross-Surface Evidence

- `conventions/behavioral-proof.md`
- verification-plan reviewer source, sidecar, eval, routing, and model role
- implementation, code-quality, apply-gate-set, RCA, and PR-review contracts
- prototype discovery, pending-test, validation, packaging, adapter, and writer contracts
- generated `workflows/index.json` plus canonical freshness command result
- applicable existing deterministic verifier and regression outputs

## Lifecycle Notes

Lifecycle is `WRITE`. Runnable detector code, fixtures, CLI integration,
scheduler/CI wiring, and enforcement transitions are downstream work. A future
transition must retain separately captured experiment output and may not infer a
pass from this specification's existence.
