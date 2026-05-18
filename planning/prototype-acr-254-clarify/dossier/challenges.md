# Challenges

P1 hack agents appended running notes here as they encountered friction, surprise, blockers, and false starts. P3.2 deduplicates those notes, groups them by theme, and preserves the useful "headline then paragraph" shape for downstream readers.

This file records what was hard, surprising, or blocking while the prototype explored three vectors: vA extending existing gates, vB adding a validation-meaning auditor, and vC adding durable evidence-class state.

## What surprised the vectors

### PR-review already had the strongest anti-weakening language

Vector A and Vector B both found that `workflows/pr-review.md` was not the weak point for ordinary PR-time test weakening. Its Test Audit already blocks assertion relaxation, baseline regeneration, deleted coverage, narrowed input space, and red-to-green without a product-code fix. The surprise was not that a new concern was absent everywhere; it was that the strongest existing language lived in PR-review while lighter standalone gates and RCA did not carry the same deterministic pattern.

### The minimum evidence taxonomy stayed smaller than expected

Vector C expected pressure toward a richer ontology, but the updater failure only needed a small binding distinction: `runtime-path` versus `validation-proxy`, with `static-or-documentary` and `unknown` to avoid accidental upgrades from docs, diffs, or unclassified evidence. Finer classes such as production logs, CI build artifacts, mocks, and inference may matter later, but they were not required to explain or stop this prototype's failure class.

### A new auditor is coherent, but not self-sufficient

Vector B confirmed that validation meaning preservation is a real single concern: whether a green signal still proves the same supported runtime property after tests, fixtures, mocks, evals, proof plans, or verification commands change. The surprise was that a standalone auditor cannot bind well without durable evidence-class state. Without that state, the auditor catches visible weakening late and infers too much at proposal and RCA time.

### Evidence-class state is necessary, but immediately passive without readers

Vector C found that `required_evidence_class` and `supplied_evidence_class` make the updater failure explicit and portable, but a ledger alone does not refuse a false green. The state only binds when Phase 4, Phase 6 alignment, Phase 8 Test Audit, and RCA verify-or-return consume it and fail closed on mismatches.

## Where the architecture fails to reach

### Extension does not discover runtime surfaces by itself

Vector A's extension path depends on Phase 2.5 identifying the supported runtime surface: updater container, production requirements, updater scripts, and runtime import path. If the problem map omits that surface, later gates may not know what evidence to require, even if the anti-weakening rules are well written.

### Extension does not create runtime evidence

Existing-gate extensions can reject weak proof, but they cannot manufacture runtime access. If the workflow cannot build or run the container, inspect the production artifact, or execute the runtime updater path, it must block or downgrade confidence. A green proxy signal cannot be converted into runtime proof by convention text.

### Evidence-class does not validate the command itself

Vector C's ledger can say a claim requires `runtime-path` and a supplied signal claims to be `runtime-path`, but readers still have to judge whether the command actually targets the supported artifact. A row can be mislabeled, too shallow, or aimed at the wrong artifact. Supported-surface review, command provenance, and test/report inspection remain necessary.

### Evidence-class does not detect fabrication or firstness failures

Durable state does not prove that evidence was actually produced, that a command output is authentic, or that a runtime-path command was written before implementation rather than backfilled after the fact. Process-tree evidence, report discipline, firstness checks, and test-intent review still carry those parts of the workflow.

### The auditor cannot prove runtime behavior by itself

Vector B's auditor reads artifacts; it does not build containers, run services, fetch production logs, execute updater scripts, or decide ambiguous product truth. If intended behavior is unclear, the right result is `NEEDS_INPUT` or a non-low risk verdict, not an auditor-authored product decision.

### Push-pull is adjacent, not universal

Vector A and Vector B both rejected overloading `push-pull-auditor.md`. Push-pull catches proof paths that pull runtime truth from private test-owned sources or uncontrolled couplers. It does not naturally catch assertion deletion, skip broadening, narrowed input matrices, baseline relaxation, or a controlled harness that no longer proves the runtime artifact.

## Compositional friction

### vA needed vC's state to make existing gates precise

Extending existing gates works best when the gates can compare a runtime claim against explicit `required_evidence_class` and `supplied_evidence_class` fields. Without vC's ledger, vA's extension becomes a list of weakening patterns and can miss proxy substitution that does not match a named pattern.

### vC needed vA's readers to stop passive documentation drift

Evidence-class state makes the mismatch durable, but it is inert unless existing readers consume it. The binding closure comes from Phase 4 proposal critique, Phase 6 output-index alignment, Phase 8 Test Audit, coverage/test quality review, and RCA verify-or-return refusing mismatched or unknown proof.

### vB needed vC's state to avoid late-only diff inference

The validation-meaning auditor owns a real concern, but without evidence-class state it has to infer required proof class from prose, diffs, and incomplete artifacts. With the ledger, it can ask a sharper question earlier: does the supplied proof class still support the runtime property this work claims to preserve or fix?

### The triangle is stronger than any single vector

The minimum architecture is not "extend gates only," "state only," or "new auditor only." Existing gates already own many decisions, evidence-class state prevents guesswork, and a validation-meaning auditor can provide a single-concern consistency check where lifecycle-wide semantics need attention. Each vector covers the others' blind spot.

## Workflow / RCA gaps surfaced

### RCA was the weakest mirror

Vector A found that RCA verify-or-return treated "original signal now green" as too self-authenticating. That is necessary evidence, but not sufficient when the RCA cycle itself can change tests, fixtures, commands, or harness setup. RCA needs same-dossier validation-change checks and evidence-class comparison before accepting green verification.

### Implementation Phase 8 was not the primary weak point

The prototype did not find Phase 8 PR-review empty. The weaker implementation surfaces were earlier and lighter: Phase 3 needed to emit runtime property, validation signal, evidence class, and planned validation-surface changes; Phase 4 needed to critique those fields; Phase 6 needed to keep Step 6b/6c output indexes aligned with the proof class.

### Phase 3 is a source surface, not an audit surface

Vector B clarified a boundary: Phase 3 cannot independently audit proof semantics because the proposal artifact is what creates the evidence. The practical hook is to make Phase 3 emit the fields needed for later critique, then let Phase 4 run the active validation-meaning check.

### Standalone test-audit and coverage-auditor lagged PR-review

Vector A found drift between PR-review's strong anti-weakening language and `agents/test-audit-gate.md` / `coverage-auditor.md`. Those lighter gates need the same deterministic diff-pattern and evidence-class consumption behavior so prototype safety does not depend on reaching the heavier PR-review surface.

## Pre-existing repo debt encountered

### Workflow-index failed on unrelated frontmatter debt

Both vA notes and P2 stabilization recorded `python3 -m tools.workflow_index check` failing on `workflows/step6c-consumption-side-file.md` with `workflow must be a mapping`. The prototype branch did not edit that file, and the stabilizer confirmed no prototype-edited `agents/`, `workflows/`, `conventions/`, or `evals/` file was named by the checker. This is pre-existing repository verification debt, not evidence that the prototype output is structurally unstable.

### RCA stabilization needed a final consistency pass

P2 found that RCA prose was semantically aligned but less explicit than the RCA operator and implementation-pipeline surfaces. Stabilization tightened `workflows/rca.md` to name `${planning_dir}/rca/<failure-id>-evidence-class.md`, reference `~/ai/conventions/evidence-class.md`, use canonical field names, and add `BLOCKED:evidence-class-mismatch` for runtime claims supplied only by proxy, static, or unknown evidence.

## False starts / abandoned hypotheses

### Embedding evidence-class in `risk-profile.md` was rejected

Vector C initially considered `risk-profile.md` because it was the closest existing precedent for durable workflow state. That blurred two questions: risk profile decides how much rigor a surface needs, while evidence-class decides whether the supplied proof class matches the claim. The cleaner shape is a small `${planning_dir}/evidence-class.md` ledger, with RCA using `${planning_dir}/rca/<failure-id>-evidence-class.md`.

### Making push-pull the universal detector was rejected

The updater failure is adjacent to A1 push-vs-pull concerns, but not identical. A proof path can be controlled and still fail to prove the runtime artifact. Overloading push-pull with validation semantics would blur its ownership of uncontrolled-source coupling and decoupling direction.

### Treating a new auditor as the whole answer was rejected

Vector B's auditor is useful, but it cannot run runtime systems, invent missing evidence, or reliably infer evidence class from sparse artifacts. The prototype abandoned "auditor only" as a complete answer and kept it as a possible active gate or consistency checker that consumes first-class state.

### Treating evidence-class as the whole answer was rejected

Vector C's ledger clarifies the proof mismatch but does not enforce it. The prototype abandoned "state only" because passive convention text can be ignored unless proposal critique, output-index alignment, Test Audit, coverage/test quality review, and RCA verification fail closed.

## Implications for downstream tickets

### Evidence-class adoption rollout

The adoption work should focus on durable fields plus active readers, not on taxonomy expansion. The important downstream frame is to introduce `required_evidence_class` and `supplied_evidence_class` where proposal, implementation, PR-review, test audit, coverage audit, and RCA artifacts already make go/no-go decisions, then require those readers to fail closed on runtime claims supplied by proxy, static, or unknown evidence.

### RCA mirror hardening

RCA work should treat "green rerun" as insufficient when the same RCA cycle touched validation surfaces. The downstream frame is to harden investigation, fix-decision, and verify-or-return around same-dossier validation changes, runtime-artifact fixes, replacement `runtime-path` validation, and explicit `BLOCKED:evidence-class-mismatch` outcomes.

### Validation-meaning auditor or consistency gate

If a new auditor ticket is spawned, it should be scoped as validation meaning preservation across lifecycle artifacts, not general test quality, coverage, push-pull coupling, or runtime execution. Its inputs should include the evidence-class ledger so it can check semantic preservation early instead of becoming a late PR-diff-only critic.

### Existing gate alignment

Gate-alignment work should cascade PR-review's stronger anti-weakening rules into `test-audit-gate`, `coverage-auditor`, Phase 4 critique, and Phase 6 output-index alignment. The downstream frame is consistency: the same validation-surface weakening should not pass merely because it appears in a lightweight gate, an RCA loop, or a pre-PR phase.

### Dossier audit and eval proof

Dossier audit work should verify that the final answer is not claiming any single vector as sufficient. The proof target is the composition: small evidence taxonomy, explicit runtime-surface discovery, active gate readers, RCA mirror hardening, and the WRITE-state validation-surface-integrity eval that traces the updater-hotfix failure across proposal, implementation, PR review, and RCA.
