---
workflow:
  id: prototype-validation-shipping
workflow_dispatch_contract:
  orchestrator: prototype-validation-orchestrator
  inputs:
    - truth branch and truth worktree path
    - eval branch and eval worktree path
    - planning path and scratch path
    - proposal or dossier reference
    - behavior-test manifest
    - base branch
    - registry target
    - prototype slug
    - package output paths
  expectations:
    - keeps product code and behavior tests on the truth branch and eval scaffolding on the eval branch
    - gates each phase advance on contract-validator acceptance, recorded behavior-test results, QA walkthrough experiment evidence, and deep rebuild verification
    - routes failing behavior tests through the light prototype RCA workflow and applies only RCA-supplied fixes
  outputs:
    - eval branch with compose, Dockerfile, README, and eval helper scripts
    - experiment-evidence bundle covering behavior tests, QA walkthrough, deep rebuild, and package material
    - one evidence-focused draft PR shipping the stabilized prototype
  non_goals:
    - does not discover or stabilize a prototype answer (see workflows/build-prototype.md)
    - does not ship production implementation work (see workflows/implementation-pipeline.md)
    - does not run adversarial QA or production-pipeline gates against the eval surface
declared_roles:
  - orchestration
  - validator
---
# Prototype Validation Shipping Workflow

This workflow ships a stabilized prototype as the deliverable. It turns a truth branch plus proposal or dossier evidence into one evidence-focused draft PR after behavior tests, recorded QA experiment evidence, deep rebuild verification, package material, and cleanup contracts are satisfied.

It is distinct from `~/ai/workflows/build-prototype.md`, which discovers and stabilizes an answer, and from `~/ai/workflows/implementation-pipeline.md`, which ships production implementation work.

## Declared roles

- `orchestration`: sequence phases, dispatch child operators, route RCA handbacks, and preserve the truth/eval branch boundary.
- `validator`: verify root inputs, branch separation, phase outputs, RCA envelopes, experiment-evidence bundles, stop states, and cleanup scope before the orchestrator advances. Validation consumes records and does not reproduce their experiments.

## Lifecycle Procedure

1. `Phase 0` - Branch and worktree setup. Record the truth branch, truth worktree, eval branch, eval worktree, planning path, scratch path, proposal or dossier reference, behavior-test manifest, base branch, registry target, prototype slug, and package output paths. Dispatch the contract validator for root input and branch topology acceptance before writing eval scaffolding.
2. `Phase 1` - Compose authoring on the eval branch. Keep product code and behavior tests on truth. Keep compose, Dockerfile, README, and eval helper scripts on eval. Rebase eval on truth before any runnable experiment, and validate branch separation after authoring.
3. `Phase 2` - Behavior tests gate. Run the initial behavior-test suite from the truth branch. For every failing behavior test, dispatch the light prototype RCA workflow with the failing command or node ID as the reproduction signal, consume `rca_handback_path`, apply only fixed handbacks, rebase eval on truth, and rerun the targeted signal before continuing.
4. `Phase 2b` - Behavior tests final regression gate. Re-run the complete behavior-test suite after all targeted fixes. Continue only when the validator accepts passing behavior evidence and no unresolved RCA handback remains.
5. `Phase 3` - Recorded QA experiment walkthrough. Run each approved QA action against the eval environment and record use-case/environment identity, expected observation, actual observation, status, report, and screenshots. Capture `qa_walkthrough_report_path`, `screenshot_dir`, and `metadata_manifest`, then dispatch `prototype-validation-screenshot-uploader.md`. The uploader returns `screenshot_url_manifest_path`; upload and validation consume the recorded evidence and are not additional experiments.
6. `Phase 4` - QA bug-fix gate. For each failed walkthrough observation, call `~/ai/workflows/rca-prototype.md` with `trigger_type: qa`, consume `rca_handback_path`, apply fixed handbacks to truth only, rebase eval on truth, and rerun only the affected QA use case until the stop condition is fixed, blocked, or needs-input.
7. `Phase 4b` - QA final regression walkthrough and deep-rebuild verification. Rebuild from a clean eval environment, rerun the full QA walkthrough set, capture refreshed `qa_walkthrough_report_path`, `screenshot_dir`, and `metadata_manifest`, then dispatch `prototype-validation-screenshot-uploader.md` again. The uploader writes the final `screenshot_url_manifest_path`; the validator accepts deep-rebuild evidence and final screenshot URLs before package assembly.
8. `Phase 5` - Image publish and zip packaging. Dispatch `prototype-validation-packager.md` to build or publish the prototype image tag, write the thin compose/README deliverables, create the zip path, write `package_manifest_path`, and assemble `experiment_evidence_bundle_path` from validator-approved test, QA, screenshot URL, deep-rebuild, deliverable, and PR-context evidence.
9. `Phase 6` - Open the truth branch's single PR. Dispatch `prototype-validation-evidence-bundle-adapter.md` with `experiment_evidence_bundle_path` and `pr_writer_input_bundle_path`; the adapter maps the evidence bundle to the seven `prototype-pr-writer.md` required inputs and dispatches the writer. Open or refresh one draft PR from the truth branch only.
10. `Phase 7` - Iteration cycle after PR open. For reviewer-requested prototype changes, land product/test changes on truth, update eval only for deliverable scaffolding, rerun the relevant behavior and QA gates, refresh uploads and package material when visible behavior changes, and refresh the evidence-focused PR body through the adapter.
11. `Phase 8` - Post-merge cleanup. After the prototype PR merges or the caller accepts terminal delivery, dispatch the packager for validator-approved cleanup of the eval branch, exact image tag, exact zip path, and package outputs, then validate `cleanup_report_path`.
12. `Phase 8b` - Cleanup when validation is incomplete or abandoned. When validation stops without a shipped PR, use the same validator-approved cleanup path for the eval branch and package artifacts, preserve evidence and stop-state records, and do not delete truth branch evidence unless the caller explicitly owns that action.

Ordering anchor: the screenshot-uploader runs AFTER the Phase 3 / Phase 4b QA walkthrough and BEFORE the packager's experiment-evidence-bundle assembly.

## Contracts

### `branch_topology_contract`

- Truth branch owns product code, behavior tests, and the single draft PR.
- Eval branch owns compose, Dockerfile, README, eval scripts, image build context, and package staging.
- Eval branch rebases on truth before behavior experiments, QA experiments, packaging, or rerun verification.
- Eval branch is never opened as its own PR and never carries product-code changes.

### `validation_gate_contract`

- Initial behavior-test execution runs before recorded QA experiments.
- Targeted behavior reruns use the failing command, node ID, or existing red-phase signal.
- QA walkthrough evidence records expected versus observed notes, screenshot metadata, use-case IDs, environment, action, and status.
- Deep rebuild verification happens before package assembly and PR writing.
- Final regression includes behavior tests plus the full QA walkthrough set after all targeted fixes.

### `rca_handback_contract`

- Test and QA failures route to `~/ai/workflows/rca-prototype.md`.
- The caller consumes one `rca_handback_path`.
- The handback envelope fields remain `outcome`, `failure_id`, `iterations`, optional `fix_artifact_path`, `evidence_paths`, and nested `handback_callback` with `workflow_id`, `phase_to_resume`, and `parent_run_id`.
- Fixed RCA handbacks apply code changes to truth; eval is updated only by rebasing on truth before rerun.

### `screenshot_url_manifest_contract`

The screenshot upload handoff starts from local `screenshot_dir` plus `metadata_manifest` and ends at `screenshot_url_manifest_path`.

```yaml
- use_case_id: <stable id>
  caption: <text>
  screenshot_url: <https://github.com/user-attachments/assets/...>
  ordering: <int>
```

### `experiment_evidence_bundle_contract`

The experiment-evidence bundle is written at `experiment_evidence_bundle_path` after behavior-test results, QA expected-versus-observed records, uploaded screenshot URLs, deep-rebuild results, package material, and PR context exist. The packager transports existing records; packaging is not another behavior experiment.

```yaml
proposal_ref: <path or durable reference>
behavior_evidence: <path>
qa_evidence: <path>
deliverable_manifest: <path>
pr_context: <base + truth branch refs, optional existing PR URL>
```

The bundle carries enough evidence for `prototype-validation-evidence-bundle-adapter.md` to produce `truth_branch_ref`, `proposal_path`, `behavior_tests_paths`, `test_results`, `qa_walkthrough_report_path`, `qa_screenshots_dir`, and `deliverable_paths` for `prototype-pr-writer.md`.

### `artifact_cleanup_contract`

- Cleanup is scoped to one prototype slug and terminal event.
- Cleanup candidates are exact eval branch ref, exact registry image tag, exact zip path, package manifest, and related package staging paths.
- `prototype-validation-contract-validator.md` approves cleanup scope before `prototype-validation-packager.md` deletes anything.
- The packager writes `cleanup_report_path` with attempted actions, completed actions, skipped actions, evidence, and residuals.

## Structural Verification Anchors

| Anchor | Purpose |
|---|---|
| `branch_topology_contract` | Truth/eval ownership and PR boundary |
| `validation_gate_contract` | Behavior, QA, targeted rerun, and deep rebuild gates |
| `rca_handback_contract` | Stable RCA handback envelope consumption |
| `screenshot_url_manifest_contract` | Uploaded screenshot URL manifest shape |
| `experiment_evidence_bundle_contract` | Stable experiment-evidence bundle shape and adapter handoff |
| `artifact_cleanup_contract` | Validator-approved package and eval cleanup scope |
