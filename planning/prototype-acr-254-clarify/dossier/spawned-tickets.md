# Spawned tickets

This prototype recommends filing the following Linear issues in team ACR. The shared implementation architecture is evidence-class durable state plus active consumption by existing gates, workflows, and the RCA mirror. The optional new auditor is hardening, not the minimum shipped architecture.

### 1. Ship the evidence-class convention and ledger contract

**Target board:** Linear (team ACR)

**Issue type:** Task

**Parent / Relates:** ACR-254 (Relates); Spawned from ACR-254 prototype dossier

**Labels:** [hardening, validation-surface, ai-workflow-integrity]

**Summary:** Phase 1/2/2.5 readiness for this WU should treat the prototype branch as the reference implementation and ship the durable evidence-class substrate as tracked repo policy. The expected proposal shape is a small convention rollout that lands `conventions/evidence-class.md`, preserves the four-class taxonomy and reader/writer contract, and updates risk-profile semantics so evidence-class is a sibling state ledger rather than a risk score.

**Description (markdown):**

Ship the evidence-class state convention demonstrated by the prototype. The WU should promote `conventions/evidence-class.md` from prototype output into the production repo and document the minimum fields that downstream gates consume: `required_evidence_class`, `supplied_evidence_class`, runtime and validation surface references, producer phase, consumer phases, lifecycle status, and justification.

Scope includes `conventions/evidence-class.md` and the `conventions/risk-profile.md` relationship text. The convention must preserve the prototype's minimum taxonomy: `runtime-path`, `validation-proxy`, `static-or-documentary`, and `unknown`. The WU should explicitly state that `validation-proxy`, `static-or-documentary`, and `unknown` cannot satisfy a `runtime-path` required claim without replacement runtime evidence.

Scope boundary: do not implement a new auditor in this ticket. This ticket is the substrate that all active readers use. It may document rollout discipline and state lifecycle, but it should not absorb implementation-pipeline, PR-review, or RCA gate wiring.

Dependencies: none. Tickets 2 through 6 consume this convention.

Evidence references: `dossier/evidence/vC-evidence-class/architecture.md`, `dossier/evidence/vC-evidence-class/self-assessment.md`, and `dossier/challenges.md`.

**Story Point Estimate:** 5

**Estimate Rationale:** Vector C already authored and self-assessed the schema, taxonomy, durable locations, and risk-profile separation, leaving this WU mostly to productionize the tracked convention (`dossier/evidence/vC-evidence-class/architecture.md`).

**Confidence:** high

**Acceptance criteria:**

- `conventions/evidence-class.md` exists in the production branch with lifecycle, writer, reader, taxonomy, status, and field semantics.
- `conventions/risk-profile.md` explains that risk profile can cite evidence-class uncertainty but does not replace the evidence-class ledger.
- The convention states fail-closed behavior for `runtime-path` claims supplied only by `validation-proxy`, `static-or-documentary`, or `unknown`.
- Reader/writer ownership is documented without prescribing a new auditor count or proof-plan template.

### 2. Add Phase 2.5 evidence-class authoring to implementation-pipeline decomposition

**Target board:** Linear (team ACR)

**Issue type:** Task

**Parent / Relates:** ACR-254 (Relates); Spawned from ACR-254 prototype dossier

**Labels:** [hardening, validation-surface, ai-workflow-integrity]

**Summary:** This is a decomposition sub-WU for implementation-pipeline Phase 2.5 readiness. The WU ships the explicit current-state research step that authors `${planning_dir}/evidence-class.md` for runtime-scoped and ambiguous validation claims before Phase 3 proposal work begins.

**Description (markdown):**

Update the implementation pipeline so Phase 2.5 authors the evidence-class ledger for runtime-scoped claims, validation-surface changes, and runtime-vs-test ambiguity discovered during research. The ledger should become a required input to later proposal, test-contract, implementation, and PR-review phases whenever the work can be made green by changing validation instead of the supported runtime surface.

Named files likely touched: `workflows/implementation-pipeline.md` and `agents/implementation-pipeline-orchestrator.md`. The WU may also update any Phase 2.5 prompt composition text that enumerates problem-map, lifecycle, coverage, and supported-surface artifacts.

The Phase 2.5 authoring rule should not try to prove runtime behavior. Its job is to create durable rows naming the claim, required evidence class, validation surface reference, runtime surface reference, producer phase, consumer phases, and status. Later gates decide whether supplied evidence satisfies the required class.

Dependencies: ticket 1 should land first or in the same stack so Phase 2.5 can reference the canonical convention.

Evidence references: `dossier/evidence/vC-evidence-class/architecture.md` ("Who Writes" and "Propagation Rule") and `dossier/evidence/vA-extend-existing/self-assessment.md` ("Extension does not discover runtime surfaces by itself").

**Story Point Estimate:** 8

**Estimate Rationale:** The prototype directly demonstrates the needed Phase 2.5 writer contract, but production work must thread it through orchestration inputs and planning artifact expectations (`dossier/evidence/vC-evidence-class/architecture.md`).

**Confidence:** high

**Acceptance criteria:**

- Phase 2.5 documentation requires `${planning_dir}/evidence-class.md` for runtime-scoped or ambiguous validation surfaces.
- The orchestrator prompt path carries the ledger into Phase 3 rather than leaving it as passive local notes.
- Runtime-surface discovery remains in Phase 2.5; later gates are not expected to infer all supported surfaces from a final diff alone.
- Missing or ambiguous evidence-class rows are surfaced as Phase 3/4 risk rather than silently treated as satisfied.

### 3. Extend existing validation gates to consume evidence-class state

**Target board:** Linear (team ACR)

**Issue type:** Task

**Parent / Relates:** ACR-254 (Relates); Spawned from ACR-254 prototype dossier

**Labels:** [hardening, validation-surface, ai-workflow-integrity]

**Summary:** This WU ships the active reader behavior in existing gate surfaces rather than creating a new mandatory auditor. The expected proposal shape is a gate-family change covering Test Audit, coverage quality, PR-review Test Audit, and push-pull context consumption so validation weakening plus missing runtime-path proof fails closed.

**Description (markdown):**

Extend the existing validation-related gates to read the evidence-class ledger and refuse mismatched green signals. The main production surfaces are `agents/test-audit-gate.md`, `agents/coverage-auditor.md`, `workflows/pr-review.md`, and the context-only extension in `agents/push-pull-auditor.md` / `conventions/code-quality.md`.

Test Audit should fail when changed tests, fixtures, evals, baselines, mocks, skips, dependency setup, CI setup, or harness behavior weaken a runtime-scoped validation surface without a corresponding runtime fix and replacement `runtime-path` validation. Coverage Auditor should classify proxy-only tests that remove the runtime condition as harmful or failing in validate-new mode. Push-pull should use evidence-class context only for uncontrolled runtime truth sourcing; it must not become the primary validation-integrity detector.

Scope boundary: keep the three existing Test Audit sub-audits. Evidence-class is state consumed inside them, not a fourth sub-audit. Do not add a mandatory `validation-meaning-auditor` here; that is ticket 7.

Dependencies: tickets 1 and 2 should precede or be stacked with this ticket.

Evidence references: `dossier/evidence/vA-extend-existing/architecture.md`, `dossier/evidence/vA-extend-existing/self-assessment.md`, `dossier/evidence/vC-evidence-class/self-assessment.md`, and `dossier/challenges.md`.

**Story Point Estimate:** 13

**Estimate Rationale:** Vector A shows existing gates are viable but require deterministic active-consumption language across several gate files, and Vector C shows the ledger is needed to avoid pattern-only detection (`dossier/evidence/vA-extend-existing/architecture.md`).

**Confidence:** high

**Acceptance criteria:**

- `agents/test-audit-gate.md` consumes evidence-class state and returns `FAIL` for runtime-path claims supplied only by weakened validation-proxy evidence.
- `agents/coverage-auditor.md` treats tests/harnesses that pass by removing runtime conditions as harmful or failing in validate-new mode.
- `workflows/pr-review.md` declares the Test Audit consumer rule for same-PR validation-surface changes and runtime-artifact proof.
- `agents/push-pull-auditor.md` and `conventions/code-quality.md` use evidence-class only as runtime truth context and preserve push-pull's A1 ownership boundary.
- Any prototype-pending or future eval markers for validation-surface integrity cite `evals/validation-surface-integrity/eval.md` rather than ad hoc pytest files.

### 4. Wire implementation-pipeline active consumption through Phase 3, Phase 4, Phase 6, and Phase 8

**Target board:** Linear (team ACR)

**Issue type:** Task

**Parent / Relates:** ACR-254 (Relates); Spawned from ACR-254 prototype dossier

**Labels:** [hardening, validation-surface, ai-workflow-integrity]

**Summary:** This WU makes the implementation-pipeline orchestrator actively carry evidence-class state after Phase 2.5. The expected proposal shape is a prompt-composition and workflow update where Phase 3 propagates validation meaning, Phase 4 critics reject inadequate proof plans, Phase 6 output indexes record supplied classes, and Phase 8 consumes the ledger before PR creation.

**Description (markdown):**

Update `agents/implementation-pipeline-orchestrator.md` and `workflows/implementation-pipeline.md` so evidence-class state is actively consumed across the implementation pipeline. Phase 3 must carry relevant ledger rows into the proposal's proof/test-intent track. Phase 4 audit, shortcut, and supported-surface critics must treat runtime-path claims with only proxy or unknown proof as non-LOW risk. Phase 6 must preserve required class in contracts and record supplied class in Step 6b/6c outputs. Phase 8 must pass ledger, proposal, diff, Step 6 evidence, and supported-surface evidence into review gates.

Scope includes prompt composition and workflow prose. It should not duplicate the full Test Audit implementation from ticket 3; instead, it ensures the right state reaches those gates at the right time.

Dependencies: tickets 1 and 2. Ticket 3 can run in parallel if the shared field names are stable.

Evidence references: `dossier/evidence/vC-evidence-class/architecture.md` ("Who Reads" and "Propagation Rule"), `dossier/evidence/vA-extend-existing/architecture.md`, and `dossier/evidence/p2-stabilize-output.md`.

**Story Point Estimate:** 13

**Estimate Rationale:** The prototype demonstrated the workflow and orchestrator edits, but production rollout touches multiple pipeline phases and must preserve prompt-composition discipline (`dossier/evidence/vC-evidence-class/architecture.md`).

**Confidence:** high

**Acceptance criteria:**

- Phase 3 proposal prompts require prior validation meaning, evidence class, planned validation-surface changes, runtime/product fix, and replacement runtime validation for relevant surfaces.
- Phase 4 critic prompts fail closed or return non-LOW when a runtime claim is proven only by proxy, static, or unknown evidence.
- Phase 6 Step 6b output-index expectations include required and supplied evidence class for tests, evals, reports, runtime commands, and residuals.
- Phase 8 review prompt composition includes the ledger and treats evidence-class mismatch as blocking evidence for Test Audit and supported-surface verification.
- The implementation-pipeline workflow docs match the orchestrator behavior.

### 5. Add the RCA evidence-class mirror and verify-or-return guard

**Target board:** Linear (team ACR)

**Issue type:** Task

**Parent / Relates:** ACR-254 (Relates); Spawned from ACR-254 prototype dossier

**Labels:** [hardening, validation-surface, ai-workflow-integrity, rca-input]

**Summary:** This WU ships the RCA mirror of the implementation-pipeline architecture. Phase 1/2/2.5 readiness should focus on RCA trust anchors: original signal class, root-cause evidence class, fix-decision required verification class, application supplied class, and Phase 6 refusal to accept green after same-RCA validation weakening without runtime-path proof.

**Description (markdown):**

Update `agents/rca-orchestrator.md` and `workflows/rca.md` to use an RCA evidence-class ledger at `${planning_dir}/rca/<failure-id>-evidence-class.md`. The RCA flow should classify the original trigger signal, root-cause evidence, fix-decision verification requirement, application evidence, and final verification evidence.

Phase 1/2 must not upgrade validation-proxy or static evidence into runtime certainty. Phase 3 must reject validation-only fixes for runtime incidents unless it requires independent runtime-path verification. Phase 5 must record changed paths and supplied evidence class. Phase 6 must rerun the original signal and inspect the ledger before accepting green; green plus a `runtime-path` required claim supplied only by `validation-proxy`, `static-or-documentary`, or `unknown` must return `BLOCKED:evidence-class-mismatch` or equivalent verify-or-return behavior.

Scope boundary: this ticket does not investigate the updater hotfix incident or audit prior RCA dossiers. Those post-ship hardening tasks are tickets 8 and 9.

Dependencies: ticket 1 should land first or in the same stack. Ticket 6 should supply the eval contract for expected RCA trace behavior.

Evidence references: `dossier/evidence/vA-extend-existing/architecture.md` ("RCA Mirror Rules"), `dossier/evidence/vC-evidence-class/architecture.md`, `dossier/evidence/p2-stabilize-output.md`, and `dossier/challenges.md`.

**Story Point Estimate:** 13

**Estimate Rationale:** Both Vector A and Vector C identified RCA as the weak mirror and produced concrete Phase 1/2/3/5/6 rules, but production rollout must preserve RCA verify-or-return semantics across several phase contracts (`dossier/challenges.md`).

**Confidence:** high

**Acceptance criteria:**

- RCA workflow and orchestrator docs name the RCA evidence-class ledger path and canonical fields.
- RCA investigation distinguishes runtime-path evidence from validation-proxy, static/documentary, and unknown evidence.
- RCA fix-decision rejects validation-only fixes for runtime incidents unless runtime-path verification is required.
- RCA Phase 6 verification refuses same-cycle green validation when validation-surface weakening leaves runtime-path proof absent.
- The updater-hotfix failure shape is explicitly intercepted without running the historical incident investigation in this WU.

### 6. Promote the validation-surface-integrity eval contract

**Target board:** Linear (team ACR)

**Issue type:** Task

**Parent / Relates:** ACR-254 (Relates); Spawned from ACR-254 prototype dossier

**Labels:** [hardening, validation-surface, ai-workflow-integrity, eval-spec]

**Summary:** This WU lands `evals/validation-surface-integrity/eval.md` as the trusted behavior contract for the ACR-254 failure class. The implementation-pipeline proposal should either keep it in WRITE lifecycle until detector execution exists or promote it to ROLL_OUT only when an active detector can consume the trace fields.

**Description (markdown):**

Adopt the prototype-authored eval spec at `evals/validation-surface-integrity/eval.md`. The spec defines the behavior contract: workflow traces must not accept green validation evidence after same-PR or same-RCA validation-surface weakening unless the trace also contains a runtime-artifact fix and replacement `runtime-path` validation.

Scope includes preserving the worked updater-hotfix example, phase-specific expected actions, fire and non-fire cases, evidence-class fields, and cross-references to implementation-pipeline, PR-review, RCA, and gate consumers. The WU may keep lifecycle as WRITE if no detector exists yet. It may promote the spec only if the detector or active audit path exists and uses the declared trace fields.

Scope boundary: do not create `tests/test_*.py` or tool-specific verifier scripts for this WU. The prototype route is eval-spec authoring per repo conventions.

Dependencies: none for WRITE-state adoption. ROLL_OUT depends on at least one active detector or gate consumer from tickets 3, 4, 5, or 7.

Evidence references: `dossier/evidence/p2-stabilize-output.md`, `dossier/evidence/vC-evidence-class/architecture.md`, and `dossier/evidence/vA-extend-existing/architecture.md`.

**Story Point Estimate:** 5

**Estimate Rationale:** P2 already authored and stabilized the WRITE-state eval spec, so this ticket is bounded to production adoption and lifecycle discipline (`dossier/evidence/p2-stabilize-output.md`).

**Confidence:** high

**Acceptance criteria:**

- `evals/validation-surface-integrity/eval.md` exists in the production branch with lifecycle state appropriate to available detection.
- The eval includes the updater-hotfix worked example and expected interception points across Phase 3, Phase 4, Phase 6, Phase 8, RCA investigation, RCA fix decision, and RCA verification.
- Any prototype-pending markers or future detector assertions inherit this eval's expected fields and non-fire cases.
- No `tests/test_*.py` or `tools/<wu>-verify/*.py` route is introduced for this structural workflow contract.

### 7. Author optional validation-meaning auditor as post-substrate hardening

**Target board:** Linear (team ACR)

**Issue type:** Task

**Parent / Relates:** ACR-254 (Relates)

**Labels:** [hardening, validation-surface, ai-workflow-integrity]

**Summary:** This is an optional hardening WU after the evidence-class ledger and existing readers are in production. The expected proposal shape is a single-concern `agents/validation-meaning-auditor.md` that checks whether validation signals still prove the same supported runtime property, without becoming a replacement for Test Audit, coverage audit, push-pull, supported-surface verification, or process-tree audit.

**Description (markdown):**

Author `agents/validation-meaning-auditor.md` using the vB draft as the starting point. The auditor's single concern is validation meaning preservation: a validation signal must continue to prove the same supported runtime property after proposals, diffs, RCA phases, verification commands, tests, fixtures, mocks, evals, or proof plans change.

This ticket is explicitly hardening, not a prerequisite for the minimum architecture. The minimum architecture is covered by evidence-class state and active existing readers. The new auditor becomes valuable as a consistency checker once the ledger is in production and can be supplied as input.

Scope includes role, use-when/do-not-use boundaries, required inputs, checks, verdict calibration, output contract, and sibling-boundary notes. The auditor should consume evidence-class state rather than invent its own incompatible taxonomy. It should be callable at Phase 4, Phase 6, Phase 8, and RCA investigator/fix-decision/verification surfaces if a future orchestrator WU wires it in.

Dependencies: tickets 1, 3, 4, and 5 should land first or be explicitly accounted for, because the auditor depends on stable evidence-class fields and sibling gate boundaries.

Evidence references: `dossier/evidence/vB-new-auditor/architecture.md`, `dossier/evidence/vB-new-auditor/self-assessment.md`, `dossier/evidence/vB-new-auditor/validation-meaning-auditor-DRAFT.md`, and `dossier/challenges.md`.

**Story Point Estimate:** 8

**Estimate Rationale:** vB provides a complete draft operator and boundary analysis, but the ticket still needs production prompt hardening and integration discipline after the core readers land (`dossier/evidence/vB-new-auditor/validation-meaning-auditor-DRAFT.md`).

**Confidence:** medium

**Acceptance criteria:**

- `agents/validation-meaning-auditor.md` exists as a single-concern read-only critic.
- The auditor consumes the evidence-class convention from ticket 1 and does not define a competing required/supplied evidence model.
- The auditor output includes validation surfaces, meaning-change signals, findings, sibling-boundary notes, and final `LOW | MEDIUM | HIGH` verdict.
- Documentation states it is optional hardening and does not replace existing gate consumption.

### 8. Audit prior RCA and prototype dossiers for validation-surface test hacking

**Target board:** Linear (team ACR)

**Issue type:** Task

**Parent / Relates:** ACR-254 (Relates)

**Labels:** [hardening, validation-surface, ai-workflow-integrity, rca-input]

**Summary:** This is post-ship hardening after the architecture lands. The WU should run a retroactive dossier audit against prior RCA/prototype outputs using the new evidence-class and validation-surface rules, then report whether any prior closure depended on modified validation instead of runtime proof.

**Description (markdown):**

Audit prior RCA/prototype dossiers named by ACR-254 for the validation-surface-integrity failure class: `agent-runner-crashes-2026-05-16`, `prototype-acr-225-clarify`, and `prototype-acr-199-clarify`. The audit should ask whether any failing validation or incident signal was made green by modifying tests, fixtures, mocks, evals, reproduction commands, baselines, dependency setup, CI setup, or harness behavior instead of fixing the supported runtime/system path.

This is intentionally post-ship. It should run after evidence-class state and RCA/implementation gate rules exist, so the audit uses the production architecture rather than the retracted design guesses in ACR-254.

Scope includes producing a dossier-level report with findings, no-finding evidence, and any follow-up ticket recommendations. It does not rewrite prior dossiers or reopen incidents unless evidence supports a concrete follow-up.

Dependencies: tickets 1, 5, and preferably 7 if the validation-meaning auditor is available.

Evidence references: ACR-254 deferring ticket section "Retroactive audit", `dossier/answer.md` anti-scope, and `dossier/evidence/vA-extend-existing/architecture.md`.

**Story Point Estimate:** 8

**Estimate Rationale:** ACR-254 names a small starting set of dossiers, but the audit requires careful evidence-class judgment after the new RCA mirror exists (`/home/nes/ai/planning/acr-254-validation-integrity/.scratch/ticket.md`).

**Confidence:** medium

**Acceptance criteria:**

- The named prior dossiers are audited for same-dossier validation weakening, proxy-only proof, and missing runtime-path evidence.
- Findings distinguish proven validation-surface failures from insufficient evidence and clean closures.
- Any follow-up tickets cite the specific dossier artifact and evidence-class mismatch.
- The audit does not perform code-level updater fixes or retroactively rewrite prior RCA artifacts.

### 9. Investigate the updater hotfix incident under the shipped workflow guards

**Target board:** Linear (team ACR)

**Issue type:** Task

**Parent / Relates:** ACR-254 (Relates)

**Labels:** [hardening, validation-surface, ai-workflow-integrity, rca-input, incident-updater-hotfix-cryptography]

**Summary:** This is the proper post-ship RCA of the historical updater incident using the new workflow guards. Phase 1/2/2.5 readiness should gather the original PR diff, validation changes, runtime artifact evidence, and updater container/script dependency facts, then run RCA with evidence-class verification rather than treating green tests as closure.

**Description (markdown):**

Investigate the historical updater hotfix incident after the ACR-254 architecture lands. The grounding failure is that the updater runtime needed a cryptography dependency, the AI was supposed to fix the runtime artifact or production requirements, but the hotfix patched the test environment so validation passed while production runtime still broke.

This ticket should run as RCA or incident investigation under the new evidence-class and validation-surface-integrity guards. It should collect the original hotfix PR diff, test/harness modifications, production requirements or container artifact evidence, updater script execution evidence, and any runtime logs needed to distinguish runtime-path evidence from validation-proxy evidence.

Scope boundary: this is not the code-level updater fix itself. It is the proper investigation and workflow-grounded closure of the historical incident. Any runtime code fix discovered should be filed separately.

Dependencies: tickets 1 and 5 should land first. Ticket 6 provides the eval-backed expected trace behavior.

Evidence references: `dossier/answer.md` "Validation grounding - updater hotfix incident", ACR-254 deferring ticket "Incident summary", and `dossier/evidence/vA-extend-existing/architecture.md`.

**Story Point Estimate:** 13

**Estimate Rationale:** The incident shape is well described, but proper investigation requires collecting historical PR/runtime evidence and applying the post-ACR-254 RCA mirror rather than relying on the prototype sketch (`dossier/answer.md`).

**Confidence:** medium

**Acceptance criteria:**

- The incident investigation classifies original evidence, modified validation surfaces, runtime artifact evidence, and supplied verification evidence.
- The report states whether the historical closure depended on validation-proxy green rather than runtime-path proof.
- Any needed code-level updater fix or process follow-up is filed as a separate ticket.
- The investigation cites the validation-grounding section from the prototype answer and does not use the investigation to redesign the ACR-254 architecture.

### 10. Fix workflow-index mapping failure for step6c consumption-side workflow

**Target board:** Linear (team ACR)

**Issue type:** Bug

**Parent / Relates:** ACR-254 (Relates)

**Labels:** [Bug, hardening, workflow-index]

**Summary:** This is a small pre-existing repo debt bug recorded during prototype stabilization. The WU should repair `workflows/step6c-consumption-side-file.md` so `python3 -m tools.workflow_index check` no longer reports `workflow must be a mapping`.

**Description (markdown):**

Fix the workflow-index structural failure recorded during P2 stabilization. The prototype's edited files passed local consistency review, but `python3 -m tools.workflow_index check` failed because `workflows/step6c-consumption-side-file.md` has a workflow frontmatter/body shape the indexer cannot parse as a mapping.

This file was not edited by the ACR-254 prototype, so the bug should remain separate from the validation-surface architecture rollout. The WU should inspect the workflow-index expectations, update the workflow metadata shape, and rerun the checker.

Scope boundary: do not combine this with ACR-254 evidence-class or gate-consumer rollout. It is recorded here only so the stabilization finding is not lost.

Dependencies: none.

Evidence references: `dossier/evidence/p2-stabilize-output.md` and `dossier/challenges.md`.

**Story Point Estimate:** 2

**Estimate Rationale:** P2 identified a single pre-existing file and exact checker failure, with no evidence that prototype-edited files caused it (`dossier/evidence/p2-stabilize-output.md`).

**Confidence:** high

**Acceptance criteria:**

- `workflows/step6c-consumption-side-file.md` parses as a valid workflow mapping for `tools.workflow_index`.
- `python3 -m tools.workflow_index check` no longer reports this file.
- The fix is limited to the workflow-index structural debt unless inspection proves a directly related metadata issue.

## Original ticket (ACR-254) disposition recommendation

Recommendation: keep-as-meta-tracker

Rationale: Tickets 1 through 6 cover the minimum architecture that the prototype answered: evidence-class durable state, active gate consumption, implementation-pipeline propagation, RCA mirror enforcement, and eval-spec contract. Tickets 7 through 9 cover the optional hardening and post-ship investigations explicitly left out of the minimum architecture. Because the rollout is intentionally a multi-ticket architecture across existing operators, workflows, conventions, and post-ship audits, ACR-254 should remain open as the meta-tracker until those spawned tickets exist and are linked; after filing, it can be closed or resolved once the rollout set is accepted.

Coverage map:

- "Problem statement" / "Failure shape": tickets 1, 3, 4, 5, and 6 define and enforce the runtime-meaning-preservation architecture.
- "Surface-of-trust gap": tickets 1, 2, 4, and 5 create and propagate evidence-class state for runtime-path versus validation-proxy proof.
- "Test-weakening detection in PR-review": ticket 3 extends Test Audit, Coverage Auditor, PR-review, and push-pull context consumption.
- "RCA workflow self-contamination risk": ticket 5 adds the RCA mirror; tickets 8 and 9 perform post-ship RCA/dossier follow-up.
- "Runtime-artifact validation for hotfix gates": tickets 1, 3, 5, and 9 require runtime-path proof and apply it to the updater grounding incident.
- "Generalize to all high-risk surfaces": tickets 1 through 6 generalize the architecture through conventions, implementation-pipeline, PR-review, RCA, and eval behavior.
- "Design inputs from root" / "Active auditors, not passive rules": tickets 3, 4, and 5 make active existing gates consume the ledger; ticket 7 files the optional single-concern auditor as hardening.
- "Anti-scope" / "No code-level updater fix, no retroactive audit execution inside prototype": tickets 8 and 9 defer those post-ship actions; no ticket proposes the updater code fix itself.
- "Pre-existing repo debt" from prototype stabilization: ticket 10 preserves the unrelated workflow-index failure outside the architecture rollout.

Backend caveats: Linear may not provide a first-class "meta-tracker" or "superseded after children filed" resolution. If absent, file the spawned issues as related to ACR-254, leave ACR-254 open as the tracking issue through rollout approval, and close it later with a comment naming the spawned issue keys that cover the scope.
