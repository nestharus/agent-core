---
id: verification-plan-reviewer
slug: verification-plan-reviewer
lifecycle: WRITE
lifecycle_state: WRITE
operator_under_test: agents/verification-plan-reviewer.md
created: 2026-08-08
risk_class: HIGH
scope: Verification-plan assessment for proposals and RCA fix decisions
behavior_class: Behavior-claim to executable-experiment fit
severity_when_fires: HIGH
evidence_source_kinds:
  - proposal
  - rca-fix-decision
  - verification-plan
  - behavior-claim
  - experiment-command-or-action
  - expected-observation
suggested_action_class: revise-verification-plan-or-narrow-behavior-claim
supersedes: []
---

# Verification Plan Reviewer Eval

## Purpose

This WRITE-state specification defines the behavior contract for
`agents/verification-plan-reviewer.md`. It is acceptance intent, not executable
evidence, and must never be cited as proof that a scenario passed.

The reviewer assesses whether a Phase 3 proposal or RCA fix decision contains a
direct executable plan. It does not run the experiment, produce an observed
result, or establish the behavior claim.

## Finding Contract

Every future finding retains the eval convention fields `eval_id`, `severity`,
`evidence_paths`, `summary`, `suggested_action`, and `confidence`, plus:

- `finding_ids`: `VPR-<NNN>` report-local IDs
- `behavior_claim`
- `verification_plan_excerpt`
- `experiment_command_or_action`
- `expected_observation`
- `claim_experiment_fit`
- `proxy_class`
- `evidence_refs`
- `expected_terminal_verdict`

## Required Trace Fields

- `mode`
- `proposal_path`
- `report_path`
- `worktree_path`
- `contract_path` for Phase 6 per-component review

Missing required inputs produce `BLOCKED:<reason>`.

## Scenarios

### VPR-001: missing verification plan

```text
mode: phase-3-proposal
proposal:
  # Runtime dependency fix
  The worker image will include the native dependency at startup.
  ## Verification
  Run the existing tests.
```

Expected verdict: `HIGH`. A behavior claim requires `## Verification plan`.

### VPR-002: missing behavior claim

```text
## Verification plan
**Experiment command or action**: Build and run the worker image.
**Expected observation**: The production entrypoint starts successfully.
**Claim-experiment fit**: The command executes the shipped image.
```

Expected verdict: `HIGH`.

### VPR-003: missing executable experiment

```text
## Verification plan
**Behavior claim**: The API container accepts production-path login requests.
**Expected observation**: The request returns the documented success response.
**Claim-experiment fit**: Runtime execution is needed for this claim.
```

Expected verdict: `HIGH`.

### VPR-004: missing expected observation

```text
## Verification plan
**Behavior claim**: The migration applies to the production schema.
**Experiment command or action**: Run the migration against a production-shaped clone.
**Claim-experiment fit**: The clone exercises the target schema shape.
```

Expected verdict: `HIGH`.

### VPR-005: missing claim-experiment fit

```text
## Verification plan
**Behavior claim**: The migration applies to the production schema.
**Experiment command or action**: Run the migration against a production-shaped clone.
**Expected observation**: The command exits zero and the expected schema diff is present.
```

Expected verdict: `HIGH`.

### VPR-006: proxy substituted for runtime claim

```text
## Verification plan
**Behavior claim**: The container imports module X during startup.
**Experiment command or action**: Import module X in the host test environment.
**Expected observation**: The host import exits zero.
**Claim-experiment fit**: Tests pass, so the container is fixed.
```

Expected verdict: `HIGH`. The host import is a proxy for container startup.

### VPR-007: honestly scoped proxy

```text
## Verification plan
**Behavior claim**: The test harness reports missing optional services as skipped.
**Experiment command or action**: Execute the harness's missing-service case.
**Expected observation**: The runner records one skip with the documented reason.
**Claim-experiment fit**: The claim is only about test-harness behavior.
```

Expected verdict: `LOW`.

### VPR-008: direct build and runtime experiment

```text
## Verification plan
**Behavior claim**: The built updater starts and imports cryptography before update.
**Experiment command or action**: Build the image and run its production entrypoint.
**Expected observation**: Build and run exit zero and the runtime log records import and update success.
**Claim-experiment fit**: The command executes the exact built artifact and entrypoint named by the claim.
```

Expected verdict: `LOW`.

### VPR-009: self-certification is not execution

```text
## Verification plan
**Behavior claim**: The deployed runner no longer crashes.
**Experiment command or action**: Accept this plan after model review.
**Expected observation**: The reviewer returns LOW.
**Claim-experiment fit**: The implementation is straightforward.
```

Expected verdict: `HIGH`.

### VPR-010: direct deterministic inspection

```text
## Verification plan
**Behavior claim**: The generated index exactly projects current workflow frontmatter.
**Experiment command or action**: Run the canonical workflow-index check against the named revision.
**Expected observation**: The command exits zero with no stale or parser error.
**Claim-experiment fit**: The deterministic checker compares the exact source and projection named by the claim.
```

Expected verdict: `LOW` at deterministic repository scope, not runtime scope.

### VPR-011: direct recorded application interaction

```text
## Verification plan
**Behavior claim**: A user with the named role can complete checkout in stage.
**Experiment command or action**: Perform the named checkout use case in stage and retain the report and screenshots.
**Expected observation**: The order confirmation appears and the report records the expected and actual result.
**Claim-experiment fit**: The action exercises the claimed role, environment, and use case directly.
```

Expected verdict: `LOW`.

## Non-Fire Cases

- Tests directly exercising a claim scoped to test or library behavior.
- Deterministic inspection claims limited to the inspected repository fact.
- Mixed plans that scope proxy evidence narrowly and separately execute the
  runtime or application experiment required for a broader claim.
- `LOW` wording that says only the plan is suitable to execute.

## Fire Cases

- Any model verdict, prose, bundle path, or WRITE eval is represented as the
  observed result of an experiment.
- A pending or fail-expected production test is represented as passing.
- A broad runtime or application claim relies only on a proxy.
- The plan lacks a command or action, expected observation, or target scope.

## Lifecycle Notes

Lifecycle is `WRITE`. No runnable detector, fixture execution, CLI integration,
or enforcement transition is supplied by this file.
