---
eval_id: acr-279-lint-promotion-regression
behavior_class: Regression evidence for blocking high-risk missing-contract lint
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - audit-bundle
  - process-tree-audit
  - workflow-report
  - markdown-file
suggested_action_class: add-curated-missing-contract-regression-evidence
---

# ACR-279 Lint Promotion Regression

## Eval identity

This WRITE-state eval spec defines the future structural-verification and regression-evidence contract for ACR-279 lint-promotion regression coverage. Source authority is `/home/nes/ai/planning/acr-279-operator-contract-rollout/contracts/acr-279-operator-contract-rollout.md` sections 4, 5, 6, and 8, Phase 4 audit-risk finding `ACR279-AUDIT-001`, the proposal, the hookpoint research, `/home/nes/ai/conventions/evals.md`, and `/home/nes/ai/agents/operator-file-format.md`.

Structural-verification claim: the promoted lint rules block on a high-risk operator missing `## Contract`.

Regression-evidence claim: a curated `agentsmd-curator` audit against the fixture high-risk operator without a `## Contract` block emits the expected missing-contract blocking finding and a non-zero or otherwise blocking run signal.

## Lifecycle state

WRITE.

This spec declares the regression evidence record only. It does not provide runnable detector code, pytest tests, verifier scripts, or CI wiring.

## Declared roles

`validator`, `mapper`

## Inputs the auditor reads

The future auditor reads:

| Evidence role | Path or invocation |
|---|---|
| Fixture high-risk operator without contract | `/home/nes/ai/worktrees/acr-279-operator-contract-rollout/evals/acr-279-lint-promotion-regression/fixtures/high-risk-operator-missing-contract.md` |
| Fixture AGENTS routing file | `/home/nes/ai/worktrees/acr-279-operator-contract-rollout/evals/acr-279-lint-promotion-regression/fixtures/AGENTS.md` |
| Curated prompt file | `/home/nes/ai/worktrees/acr-279-operator-contract-rollout/evals/acr-279-lint-promotion-regression/fixtures/agentsmd-curator-missing-contract-regression.prompt.md` |
| Curator lint surface | `/home/nes/ai/agents/agentsmd-curator.md` |
| Schema/carve-out reference | `/home/nes/ai/agents/operator-file-format.md` |
| Regression invocation | `agents -m gpt-high -f /home/nes/ai/worktrees/acr-279-operator-contract-rollout/evals/acr-279-lint-promotion-regression/fixtures/agentsmd-curator-missing-contract-regression.prompt.md` |
| Expected failing finding identifier | `ACR279-CURATOR-MISSING-CONTRACT-BLOCKING` |
| Expected blocking signal | Non-zero exit code, or if the runner does not use exit codes for curator findings, an aggregate `Status: BLOCKING` with the expected finding identifier in stdout or the saved audit report. |

The auditor confirms all fixture files exist before running the invocation. The high-risk operator fixture path above remains the stable regression input.

## Unwanted behavior

The unwanted behavior is regression drift where the lint rules appear structurally promoted in prose but a curated audit of a high-risk missing-contract operator does not fail with a blocking signal and the expected finding identifier.

## Positive evidence

Positive evidence may include:

- The fixture file is absent.
- The fixture AGENTS routing file is absent or does not route to the high-risk operator fixture.
- The curated prompt file is absent or does not specify `mode=audit`, the fixture AGENTS path, and the fixture agents directory.
- The fixture contains a valid `## Contract` block, making it no longer a missing-contract regression input.
- The curated invocation exits zero and produces no blocking aggregate signal.
- The output lacks `ACR279-CURATOR-MISSING-CONTRACT-BLOCKING`.
- The output reports only `advisory`, `MINOR`, `MAJOR`, or equivalent non-blocking severity for the high-risk missing-contract fixture.
- The curator treats the fixture as trivial/minimum-body despite credentials, ticket, branch-topology, or external-service language in the file.

## Non-fire cases

The eval must not fire on:

- A non-zero exit code with the expected finding identifier.
- A zero process exit when the `agents` runner conventionally reports gate failures through `Status: BLOCKING`, provided the expected identifier is present and the caller treats it as blocking.
- Additional advisory findings about missing recommended body sections.
- Additional routing prose in the fixture AGENTS file, provided it still routes to the high-risk missing-contract operator fixture.

## Pass/fail criteria

Pass: the fixture operator, fixture AGENTS routing file, and curated prompt file exist; the operator lacks a `## Contract` block; the operator looks high-risk under the lint classifier; and the exact curated invocation produces `ACR279-CURATOR-MISSING-CONTRACT-BLOCKING` plus a non-zero exit code or an equivalent `Status: BLOCKING` signal.

Fail: the fixture is missing or no longer missing a contract; the invocation cannot run for reasons unrelated to the expected blocking finding; the finding identifier is absent; or the output is advisory/non-blocking. The finding is `blocking` for acceptance. The `advisory` trivial/minimum-body carve-out is expected not to apply because the fixture intentionally looks high-risk.

## Required trace fields

| Field | Description |
|---|---|
| `fixture_path` | Stable fixture path under this eval directory. |
| `fixture_agents_md` | Stable AGENTS routing fixture path. |
| `fixture_prompt_file` | Stable curated prompt file path used by `agents -m gpt-high -f`. |
| `fixture_contract_status` | Whether the fixture contains `## Contract`. |
| `fixture_high_risk_signals` | Credentials, branch topology, tickets, worktrees, external service, or release signals found in the fixture. |
| `curator_invocation` | Exact `agents -m gpt-high -f ...` command. |
| `exit_code` | Process exit code when available. |
| `blocking_signal` | `Status: BLOCKING` or equivalent gate signal when exit code is not non-zero. |
| `expected_finding_id` | `ACR279-CURATOR-MISSING-CONTRACT-BLOCKING`. |
| `observed_finding_ids` | Finding identifiers emitted by the curator. |
| `severity_observed` | Observed severity for the missing-contract finding. |

## Finding schema

Findings preserve the minimum fields from `conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

The finding schema also includes `fixture_path`, `fixture_agents_md`, `fixture_prompt_file`, `fixture_contract_status`, `fixture_high_risk_signals`, `curator_invocation`, `exit_code`, `blocking_signal`, `expected_finding_id`, `observed_finding_ids`, and `severity_observed`.

`severity` is `HIGH` when the regression fixture does not produce the expected blocking signal; `MEDIUM` is for invocation-environment ambiguity with the expected finding present; `LOW` is for future trace-adapter uncertainty.

## Suggested action

Return `add-curated-missing-contract-regression-evidence`. The caller should repair the lint-promotion rule or regression fixture so the curated audit blocks with `ACR279-CURATOR-MISSING-CONTRACT-BLOCKING`.

## Coverage

| Scenario ID | Scenario |
|---|---|
| ACR279-LR-001 | Verify fixture exists and has no `## Contract` block. |
| ACR279-LR-002 | Verify fixture AGENTS routing file points to the high-risk missing-contract operator. |
| ACR279-LR-003 | Verify fixture contains high-risk classifier signals. |
| ACR279-LR-004 | Verify curated prompt file specifies the fixture AGENTS and agents directory. |
| ACR279-LR-005 | Run exact curated `agentsmd-curator` invocation. |
| ACR279-LR-006 | Verify expected failing finding identifier. |
| ACR279-LR-007 | Verify non-zero exit code or equivalent blocking signal. |
