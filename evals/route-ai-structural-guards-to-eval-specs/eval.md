# Eval: route-ai-structural-guards-to-eval-specs

## Lifecycle state

WRITE

No runnable detector is required for ACR-209. Detector implementation and runtime fixture wiring are owned by ACR-212.

## Identity

- `eval_id`: `route-ai-structural-guards-to-eval-specs`
- `owner_wu`: `ACR-209`
- `scope`: clean newly-composed `~/ai` markdown/operator/workflow/convention/routing/anchor structural-verification dispatches
- `artifact`: `evals/route-ai-structural-guards-to-eval-specs/eval.md`

## Unwanted behavior

A clean newly-composed structural-verification dispatch for `~/ai` markdown, operator, workflow, convention, routing, or anchor guard work produces pytest-shaped or verifier-script output instead of a WRITE-state eval spec.

This eval should fire when the trace shows any of these outputs for the structural route:

- `tests/test_*.py` files.
- Pytest imports, fixtures, or assertion-shaped code, even outside `tests/test_*.py`.
- One-off verifier scripts under `tools/<wu>-verify/<anything>.py`.
- Step 6b output-index rows that map the structural test intent to pytest/verifier artifacts rather than an eval spec.

The route applies to phrases such as "structural test", "structural verification", "markdown anchor check", "workflow/operator shape guard", and "convention-routing guard" when the target is a `~/ai` markdown/operator/workflow/convention/routing/anchor surface.

## Positive evidence

Positive evidence is the before-after flip captured in `/home/nes/projects/ai/planning/prototype-acr-199-clarify/dossier/evidence/p1-vector-b-before-after-hand-trace.md`.

Before-state discriminator:

- Fixture WU asks for a structural test verifying the `agents/pr-writer.md` `Plain-terms` section keeps a `Story Point Estimate:` line.
- The surface is `~/ai` operator markdown / anchor structure.
- Phase 2.5, Phase 3, and Phase 6b routing compose a test-writer prompt and Step 6b checks for test files.
- Likely output class is pytest/verifier-shaped test artifact, not eval spec.

After-state discriminator:

- The same fixture routes through eval-spec intent in Phase 2.5 and Phase 3.
- Phase 6b composes an eval-spec authoring pass instead of a test-writer prompt.
- Step 6b verifies `evals/<slug>/eval.md` plus `${scratch_dir}/phase6/step6b-output-index.md`.
- Fallback test-writer dispatch refuses with `BLOCKED:route-to-eval-spec-authoring`.
- The accepted output class is WRITE-state eval-spec output plus output-index mapping, not pytest/verifier output.

For ACR-209, the concrete positive output is:

- `evals/route-ai-structural-guards-to-eval-specs/eval.md` with lifecycle `WRITE`.
- `/home/nes/ai/planning/acr-209-route-structural-guards-to-eval-specs/.scratch/phase6/step6b-output-index.md` mapping that eval spec to the proposal `## Test-intent track` and the inherited predecessor proof.

## Non-fire cases

This eval must not fire for legitimate behavior-test work outside the structural `~/ai` route, including:

- Non-structural product-code tests that exercise runtime behavior with inputs and expected outputs.
- Characterization tests for existing product behavior before an implementation change.
- Workflow or configuration behavior tests where the test exercises an actual runtime path rather than checking markdown, operator, convention, routing, or anchor structure.
- Runnable detector implementation or runtime fixture wiring performed by ACR-212 or later eval-runtime work, as long as it implements this eval contract rather than replacing it with pytest/verifier structural output.

## Required trace fields

A detector for this eval needs enough trace evidence to identify:

- The approved proposal `## Test-intent track` for the WU.
- Step 6b output-index rows, including emitted artifact paths and lifecycle state.
- The Step 6b prompt composition, including whether it asks for eval-spec authoring or test-writer/pytest/verifier output.
- The actual Step 6b dispatch target, including accidental `test-writer` dispatches.
- Any fallback test-writer result, including `BLOCKED:route-to-eval-spec-authoring` refusal when applicable.
- The structural-route match evidence: target surface class, structural phrase, and WU id.
- The emitted artifact paths for `evals/<slug>/eval.md`, `tests/test_*.py`, and `tools/<wu>-verify/<anything>.py` when present.

## Finding shape

Findings must preserve the minimum fields from `conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Recommended ACR-209 extensions:

- `wu_id`
- `phase`
- `gate`
- `proposal_path`
- `contract_path`
- `output_index_path`
- `step6b_prompt_path`
- `dispatch_target`
- `emitted_artifact_paths`
- `trace_locator`

Severity guidance:

- `HIGH` when a clean newly-composed structural route emits pytest/verifier artifacts or Step 6b accepts them.
- `MEDIUM` when prompt composition is ambiguous enough to allow pytest/verifier artifacts, but no forbidden artifact is emitted in the observed trace.
- `LOW` when trace fields are incomplete and the detector can only report evidence drift or missing instrumentation.

## Suggested action

Route the WU through WRITE-state eval-spec authoring under `conventions/evals.md`. The accepted Step 6b output for this structural route is `evals/<slug>/eval.md` plus `${scratch_dir}/phase6/step6b-output-index.md`.

Refuse or revise any Step 6b prompt, fallback test-writer dispatch, output-index row, or emitted artifact that produces `tests/test_*.py`, pytest imports/fixtures/assertion-shaped code, or `tools/<wu>-verify/<anything>.py` for this structural route.

## Lifecycle notes

prototype-pending: detector implementation + runtime fixture wiring deferred to ACR-212; remove `prototype-pending:` marker and make this eval runnable in ACR-212 spawned work

ACR-209 owns only this WRITE-state eval spec and the routing-text work that makes clean newly-composed dispatches choose it. ACR-212 owns detector implementation, runtime fixtures, and lifecycle advancement beyond `WRITE`.

## Cross-references

- Predecessor hand-trace: `/home/nes/projects/ai/planning/prototype-acr-199-clarify/dossier/evidence/p1-vector-b-before-after-hand-trace.md`
- Proposal: `/home/nes/ai/planning/acr-209-route-structural-guards-to-eval-specs/proposals/acr-209-ACR-209.md`
- Contract: `/home/nes/ai/planning/acr-209-route-structural-guards-to-eval-specs/contracts/acr-209-route-structural-guards-to-eval-specs.md`
- Predecessor carry-forward evidence: `/home/nes/ai/planning/acr-209-route-structural-guards-to-eval-specs/.scratch/predecessor-prototype-evidence.md`
- Eval convention: `/home/nes/ai/conventions/evals.md`
- Prototype pending convention: `/home/nes/ai/conventions/prototype-pending-tests.md`
- Successor detector/runtime owner: ACR-212
