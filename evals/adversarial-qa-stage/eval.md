---
eval_id: adversarial-qa-stage
behavior_class: ACR-149 adversarial QA stage structural drift
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - markdown-document
  - markdown-frontmatter
  - markdown-section-header
  - command-transcript
  - workflow-index-report
suggested_action_class: revise-adversarial-qa-stage-docs
---

# Adversarial QA Stage

## Eval identity

This is a markdown behavior specification for `adversarial-qa-stage`, not runnable eval code. It translates the structural intent currently encoded in `tests/test_adversarial_qa_stage.py`.

The target behavior surfaces are `workflows/adversarial-qa-stage.md`, `agents/adversarial-qa-driver.md`, and `workflows/eval-runtime.md`. The legacy pytest file's self-declared A1 role marker is captured as a legacy-source compatibility check, not as a durable requirement to keep pytest in the replacement path.

The eval is in `WRITE` lifecycle state: the spec is reviewable and binding as a behavior contract, but no runnable detector is required in this work unit.

## Unwanted behavior

The unwanted behavior is drift in the stage-only adversarial QA workflow or driver that weakens its stage/prototype/production boundary, evidence-backed bug-report contract, ticket-backend abstraction, readiness contract, eval-runtime indexability, or A1 role declaration discipline.

Drift is present when any translated check below fails against the normalized evidence bundle.

## Positive evidence

### AQS-01 workflow file and dispatch metadata

`workflows/adversarial-qa-stage.md` exists, is non-empty, starts with YAML frontmatter, has a closing frontmatter delimiter, and contains all of:

- `workflow:`
- `id: adversarial-qa-stage`
- `workflow_dispatch_contract:`
- `orchestrator:`
- `inputs:`
- `expectations:`
- `outputs:`
- `non_goals:`
- `agents/adversarial-qa-driver`

### AQS-02 workflow section and phase map

The workflow contains exact H2 headings for `Purpose`, `Workflow Dispatch Surface`, `Required Inputs`, `Output Paths`, `Phase Map`, `Stop Conditions`, `Anti-Scope`, `Handoff Boundary`, and `Cross-References`.

The workflow also contains exact H2 headings for the five runtime phases: `setup`, `normal-usage regression sweep`, `adversarial probing`, `bug report filing`, and `summary report`.

### AQS-03 workflow stage scope and split

The workflow text contains all of `stage-only`, `production`, `prototype`, `normal-usage regression sweep`, and `adversarial probing`.

The `normal-usage regression sweep` and `adversarial probing` strings must occur at distinct positions, and the workflow must explicitly exclude both production and prototype scopes using wording equivalent to "exclude/not/outside production" and "exclude/not/outside prototype".

### AQS-04 workflow bug-report contents

The workflow text contains all of `expected behavior`, `actual behavior`, `deterministic steps to reproduce`, `UTC timestamp`, `local logs when available`, `environment`, `labels`, `severity/priority`, and `RCA handoff`.

It contains at least one of `screenshot` or `video`, and contains cross-references to `~/ai/conventions/test-reports.md` and `~/ai/conventions/risk-profile.md`.

### AQS-05 workflow forbidden framing absent

The workflow text does not contain `machine enforcement` or `tracked in a separate ticket`.

### AQS-06 operator file, frontmatter, and headings

`agents/adversarial-qa-driver.md` exists, is non-empty, starts with YAML frontmatter, has a closing frontmatter delimiter, and its frontmatter keys are exactly `description`, `model`, and `output_format` in that order.

The frontmatter contains `description:`, `model: gpt-high`, and `output_format: ''`.

The operator contains exact H2 headings for `Role`, `Use When`, `Do Not Use When`, `Inputs`, `Procedure`, `Evidence And Bug Report Contract`, `Stop Conditions`, `Escalation`, and `Outputs`.

### AQS-07 operator input contract

The operator text contains all of `stage_url`, `health_check_url`, `use_case_dossier_path`, `run_id`, `ticket_system`, `${ticket_operator}`, and `feature_flags`.

It also names at least one planning/evidence root (`planning_dir` or `evidence_dir_root`), at least one ticket-backend routing input (`linear_team_key`, `linear_project_id`, or a `jira_` input), a browser identity token (`browser` or `browser_identity`), at least one credentials/roles token in the `Inputs` section (`credentials_path`, `credentials`, `role`, `roles`, or `role_bindings`), and a local log input (`local_log_paths` or `log_capture_path`).

### AQS-08 operator core subprocedures and ticket abstraction

The operator text contains all of:

- `evidence-capture sub-procedure`
- `bug filing sub-procedure`
- `summary-write sub-procedure`
- `ticket_system`
- `${ticket_operator}`
- `create`
- `comment-write`
- `linear-operator.md task=create`
- `linear-operator.md task=upsert-comment`
- `jira-operator.md task=create`
- `jira-operator.md task=comment`

The operator states that it invokes exactly two abstract ticket tasks. The external ticket-operator surface, parsed from `## Ticket Operator Surface` or equivalent external-surface section, exposes exactly `create` and `comment-write`, and does not introduce standalone `comment` or `apply-labels` as abstract tasks.

### AQS-09 operator evidence policy

The operator text contains all of:

- `~/ai/conventions/test-reports.md`
- `per-finding PDF`
- `raw screenshots`
- `videos`
- `logs`
- `run bundle`
- `UTC timestamp`
- `stage environment`
- `browser/agent identity`
- `feature flags`
- `deterministic repro steps`
- `component labels`
- `severity/priority`
- `local logs when available`
- `run-bundle links`
- `~/ai/conventions/risk-profile.md`
- `insufficient for stage QA`

### AQS-10 operator readiness contract

The operator text contains all of `health_check_url`, `HTTP`, `status`, `2xx`, `4xx`, `5xx`, `no body parsing`, `connection-refused`, and `timeout`.

It must also contain both `body` and `parsing`, preserving the rejection of private response-body coupling.

### AQS-11 eval-runtime frontmatter and workflow index health

`workflows/eval-runtime.md` exists, starts with YAML frontmatter, has a closing delimiter within the first 60 lines, and that frontmatter contains a `workflow:` mapping and nested `id: <non-empty>` entry.

The normalized trace bundle contains a successful workflow-index check equivalent to:

```text
python3 -m tools.workflow_index check --repo-root <repo-root> --workflows-dir workflows
```

The command must exit 0. Stdout and stderr must be preserved when it fails.

### AQS-12 A1 role declarations

The workflow declares exactly the A1 roles `orchestration`, `validator`, and `formatter`.

The operator declares exactly the A1 roles `orchestration`, `validator`, `accessor`, and `formatter`.

The legacy structural pytest source, when present as an evaluated legacy source, declares exactly the A1 roles `orchestration`, `filter`, `validator`, `predicate`, `mapper`, `accessor`, and `parser`.

Declared role tokens must be drawn only from the A1 vocabulary: `orchestration`, `filter`, `validator`, `predicate`, `mapper`, `accessor`, `formatter`, and `parser`.

## Non-fire cases

The eval returns no finding when:

- the workflow and operator files exist, are readable, non-empty, and have valid delimiter-bounded frontmatter;
- the workflow frontmatter and dispatch contract expose the required adversarial-QA stage identity and driver reference;
- all required workflow headings and the five phase headings are present;
- the workflow explicitly keeps production and prototype out of scope and treats normal regression and adversarial probing as distinct phases;
- the workflow bug-report contents and cross-references match AQS-04;
- forbidden workflow framing from AQS-05 is absent;
- operator frontmatter keys and required headings match AQS-06;
- operator inputs include the required URL, dossier, run, planning/evidence, ticket, browser, credential/role, feature flag, and log surfaces;
- the operator exposes exactly the `create` and `comment-write` abstract ticket tasks and maps them to Linear and JIRA bindings as specified;
- the operator preserves evidence policy and readiness contract text;
- eval-runtime frontmatter is parseable and workflow-index check evidence exits 0;
- A1 role declarations match the exact sets in AQS-12.

The eval must not fire on backend-specific task names such as `linear-operator.md task=upsert-comment` or `jira-operator.md task=comment` when they are correctly mapped behind the abstract `comment-write` task. It must not treat generic words such as `ticket`, `task`, `backend`, `labels`, `linear-operator`, or `jira-operator` as abstract ticket tasks.

## Required trace fields

The preferred evidence boundary is saved `agents trace --json` plus companion artifacts. A future runner must normalize these semantic fields before executing the detector:

- `eval_id`
- `root_invocation_uuid` or `session_id`
- `repo_root`
- `target_documents`, including path, existence, byte size, text or content digest, and excerpt resolver for each target surface
- `frontmatter_spans` for workflow, operator, and eval-runtime documents
- `markdown_headings` for workflow and operator documents
- `section_spans`, especially `Inputs`, `Ticket Operator Surface`, external-surface fallback, `Procedure`, and `Declared roles`
- `abstract_ticket_tasks`
- `workflow_index_check`, including argv, cwd, exit code, stdout, and stderr
- `declared_role_tokens` by source surface
- `failed_check_id`
- `evidence_excerpt`

Missing document evidence or missing workflow-index command evidence is not silently treated as no finding. It is a runner evidence error, maintenance-drift result, or `NEEDS_INPUT` equivalent unless the caller intentionally selected a mode that excludes AQS-11.

## Finding shape

Findings preserve the minimum schema fields from `conventions/evals.md`: `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`.

Allowed extensions include `root_invocation_uuid`, `session_id`, `repo_root`, `failed_check_id`, `target_document_path`, `section_header`, `section_span`, `missing_tokens`, `forbidden_tokens`, `observed_frontmatter_keys`, `observed_abstract_tasks`, `expected_abstract_tasks`, `observed_roles`, `expected_roles`, `workflow_index_exit_code`, `stdout`, `stderr`, and `evidence_excerpt`.

`severity` is `HIGH` for any failure that weakens stage-only scope, bug-report completeness, ticket-task abstraction, readiness behavior, or eval-runtime indexability. It may be `MEDIUM` for isolated A1 role-declaration drift when the workflow behavior contract remains intact.

## Suggested action

Return `revise-adversarial-qa-stage-docs`. The fix target is the failing source surface named in the finding: `workflows/adversarial-qa-stage.md`, `agents/adversarial-qa-driver.md`, `workflows/eval-runtime.md`, or the workflow-index metadata consumed by `tools.workflow_index`.

Do not restore `tests/test_adversarial_qa_stage.py` as the durable guard. If AQS-12's legacy pytest self-role assertion is considered still valuable after pytest removal, move that role-declaration expectation to the eval spec or detector implementation artifact instead.

## Lifecycle notes

This eval ships in `WRITE` state. It intentionally replaces the pytest-on-Markdown scraper with a reviewable behavior spec. Runnable code, fixtures, CLI integration, trace adapters, and enforcement wiring are deferred to a future eval-runtime implementation ticket.

The workflow-index assertion requires command-transcript evidence or an equivalent workflow-index report in the normalized trace bundle. The eval-spec format can name that requirement, but it does not itself run the command.

## References

- `tests/test_adversarial_qa_stage.py`
- `workflows/adversarial-qa-stage.md`
- `agents/adversarial-qa-driver.md`
- `workflows/eval-runtime.md`
- `tools.workflow_index`
- `conventions/evals.md`
