# Prototype ACR-254 Clarify Risk Profile

Prototype stable state scored: `prototype-acr-254-clarify-p2-stable` / `c7a2d7a0d887d8b6a203ae3b2a6bf10953fe5a43`.

This profile scores the surfaces actually touched by the prototype branch, not the broader anticipated ACR-254 implementation surface. Scoring follows `~/ai/conventions/risk-profile.md`: score each touched surface on coverage gap, behavioral ambiguity, blast radius, language fragmentation, duplicate-system count, brittleness markers, change-path entropy, and lifecycle visibility; any HIGH axis yields a HIGH surface verdict, and three or more MEDIUM axes also yield HIGH.

## Touched-Surface Enumeration

Command:

```bash
git -C /home/nes/ai/worktrees/prototype-acr-254-clarify diff master..HEAD --name-only
```

Excluded from scoring: `dossier/evidence/*`. Those files are prototype evidence artifacts, not shipping deliverable surfaces.

Scored surfaces:

```text
agents/coverage-auditor.md
agents/implementation-pipeline-orchestrator.md
agents/push-pull-auditor.md
agents/rca-orchestrator.md
agents/test-audit-gate.md
conventions/code-quality.md
conventions/evidence-class.md
conventions/risk-profile.md
evals/validation-surface-integrity/eval.md
workflows/implementation-pipeline.md
workflows/pr-review.md
workflows/rca.md
```

## Evidence Index

- `R1`: Risk rubric and verdict rule: `/home/nes/ai/conventions/risk-profile.md:19-28`, `/home/nes/ai/conventions/risk-profile.md:34-38`.
- `Q1`: Prototype question and acceptable answer shapes: `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/answer.md:5-17`.
- `Q2`: Updater-hotfix grounding incident and exit condition: `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/answer.md:42-56`.
- `A1`: Extend-existing architecture requires active implementation, PR-review, test-audit, coverage, push-pull, and RCA consumers: `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vA-extend-existing/architecture.md:5-15`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vA-extend-existing/architecture.md:19-66`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vA-extend-existing/architecture.md:68-98`.
- `A2`: Extend-existing self-assessment: existing gates help but do not bind without active consumption and RCA mirror rules: `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vA-extend-existing/self-assessment.md:7-24`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vA-extend-existing/self-assessment.md:28-46`.
- `B1`: New-auditor vector shows validation meaning is a coherent concern but needs evidence-class state: `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vB-new-auditor/architecture.md:5-10`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vB-new-auditor/architecture.md:27-43`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vB-new-auditor/architecture.md:82-120`.
- `B2`: New-auditor self-assessment: separate concern, but the binding constraint is first-class evidence-class state: `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vB-new-auditor/self-assessment.md:5-13`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vB-new-auditor/self-assessment.md:27-38`.
- `C1`: Evidence-class architecture: durable ledger, four-class taxonomy, authors/readers, and demonstration edits: `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vC-evidence-class/architecture.md:5-11`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vC-evidence-class/architecture.md:21-30`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vC-evidence-class/architecture.md:32-63`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vC-evidence-class/architecture.md:65-98`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vC-evidence-class/architecture.md:147-162`.
- `C2`: Evidence-class self-assessment: state alone is passive; active gates must consume it; known limits remain: `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vC-evidence-class/self-assessment.md:5-14`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vC-evidence-class/self-assessment.md:18-27`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/vC-evidence-class/self-assessment.md:41-54`.
- `P1`: P1 challenge notes record PR-review/test-audit drift, weak RCA mirror, passive evidence-class state, and the new-auditor/evidence-class dependency: `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/challenges.md:9-39`.
- `P2`: Stabilizer found consistent references, canonical field names, WRITE eval-spec output, and only unrelated workflow-index debt: `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/p2-stabilize-output.md:5-20`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/p2-stabilize-output.md:22-28`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/p2-stabilize-output.md:45-56`, `/home/nes/ai/planning/prototype-acr-254-clarify/dossier/evidence/p2-stabilize-output.md:63-73`.
- `O1`: Original ACR-254 risk profile is the starting point but wider than this prototype; it scored 24 of 29 anticipated surfaces HIGH and named duplicate/lifecycle/coverage drivers: `/home/nes/ai/planning/acr-254-validation-integrity/risk/acr-254-risk-profile.md:40-70`, `/home/nes/ai/planning/acr-254-validation-integrity/risk/acr-254-risk-profile.md:106-117`, `/home/nes/ai/planning/acr-254-validation-integrity/risk/acr-254-risk-profile.md:118-133`.

## Per-Surface Scores

Legend: `Cvg` coverage gap, `Amb` behavioral ambiguity, `Blast` blast radius, `Lang` language fragmentation, `Dup` duplicate-system count, `Brit` brittleness markers, `Ent` change-path entropy, `Life` lifecycle visibility.

| Surface | Cvg | Amb | Blast | Lang | Dup | Brit | Ent | Life | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| `agents/coverage-auditor.md` | HIGH | MEDIUM | HIGH | LOW | HIGH | LOW | HIGH | MEDIUM | HIGH |
| `agents/implementation-pipeline-orchestrator.md` | HIGH | HIGH | HIGH | MEDIUM | HIGH | LOW | HIGH | HIGH | HIGH |
| `agents/push-pull-auditor.md` | HIGH | MEDIUM | HIGH | LOW | MEDIUM | LOW | MEDIUM | MEDIUM | HIGH |
| `agents/rca-orchestrator.md` | HIGH | HIGH | HIGH | MEDIUM | HIGH | LOW | HIGH | HIGH | HIGH |
| `agents/test-audit-gate.md` | HIGH | MEDIUM | HIGH | MEDIUM | HIGH | LOW | HIGH | MEDIUM | HIGH |
| `conventions/code-quality.md` | HIGH | MEDIUM | HIGH | LOW | MEDIUM | LOW | MEDIUM | MEDIUM | HIGH |
| `conventions/evidence-class.md` | HIGH | HIGH | HIGH | LOW | LOW | LOW | HIGH | HIGH | HIGH |
| `conventions/risk-profile.md` | HIGH | MEDIUM | HIGH | LOW | LOW | LOW | MEDIUM | MEDIUM | HIGH |
| `evals/validation-surface-integrity/eval.md` | MEDIUM | MEDIUM | MEDIUM | MEDIUM | MEDIUM | LOW | MEDIUM | MEDIUM | HIGH |
| `workflows/implementation-pipeline.md` | HIGH | HIGH | HIGH | MEDIUM | HIGH | LOW | HIGH | HIGH | HIGH |
| `workflows/pr-review.md` | HIGH | MEDIUM | HIGH | MEDIUM | HIGH | LOW | HIGH | MEDIUM | HIGH |
| `workflows/rca.md` | HIGH | HIGH | HIGH | MEDIUM | HIGH | LOW | HIGH | HIGH | HIGH |

### `agents/coverage-auditor.md` - HIGH

Coverage gap is HIGH because the changed operator behavior is prompt/procedure text with no runnable behavior test; the stabilizer confirms the only emitted proof artifact is the WRITE-state eval spec, not a detector or test runner (`P2`). Behavioral ambiguity is MEDIUM because the new language clearly classifies validation weakening as `HARMFUL`, but deciding whether a test/report supplies `runtime-path` versus `validation-proxy` evidence remains dependent on external evidence-class context (`agents/coverage-auditor.md:31-44`, `agents/coverage-auditor.md:72-74`, `agents/coverage-auditor.md:173-174`). Blast radius is HIGH because this shared auditor feeds `test-audit-gate.md` and can turn changed tests into `FAIL`; duplicate-system count and entropy are HIGH because the same logical rule is also present in PR review, test-audit, RCA, and implementation-pipeline surfaces (`A1`, `A2`, `P1`). Language fragmentation is LOW because the surface itself stays Markdown prompt text. Brittleness markers are LOW; no TODO/FIXME/HACK-style marker was introduced on the changed lines. Lifecycle visibility is MEDIUM: inputs and verdict role are named, but downstream consumers and runtime evidence sources come from other workflow artifacts.

### `agents/implementation-pipeline-orchestrator.md` - HIGH

Coverage gap, behavioral ambiguity, blast radius, change-path entropy, and lifecycle visibility are HIGH. This operator now actively carries `${planning_dir}/evidence-class.md` from Phase 2.5 into Phase 3, Phase 4, Phase 6, and Phase 8, composes proposer/gate prompts with validation-surface integrity rules, blocks Step 6c on evidence-class mismatch, and dispatches Phase 8 test-audit with actual-diff evidence (`agents/implementation-pipeline-orchestrator.md:180-180`, `agents/implementation-pipeline-orchestrator.md:273-278`, `agents/implementation-pipeline-orchestrator.md:298-298`, `agents/implementation-pipeline-orchestrator.md:357-369`, `agents/implementation-pipeline-orchestrator.md:380-381`, `agents/implementation-pipeline-orchestrator.md:520-520`). The behavior is not backed by runnable tests, and it is central workflow control, so blast radius is HIGH. Language fragmentation is MEDIUM because Markdown orchestration composes shell/CLI child dispatch and durable file artifacts. Duplicate-system count and entropy are HIGH because the same validation-integrity relation must stay aligned across workflow prose, orchestrator prompt composition, PR-review, test-audit, RCA, and evidence-class convention (`A1`, `C1`, `P1`, `O1`). Brittleness markers are LOW for the changed rule text.

### `agents/push-pull-auditor.md` - HIGH

Coverage gap is HIGH because the new validation-surface pull-site procedure has no behavior test. Behavioral ambiguity is MEDIUM: the prototype deliberately keeps evidence-class as context and preserves A1 scoring, but deciding whether a validation source is a supported runtime artifact or test-owned substitute requires artifact-specific judgment (`agents/push-pull-auditor.md:46-59`, `agents/push-pull-auditor.md:83-109`). Blast radius is HIGH because this shared code-quality auditor can emit blocking `uncontrolled-source coupler` findings for proof paths, though it is not the primary validation-integrity gate (`conventions/code-quality.md:123-133`, `A1`). Language fragmentation is LOW for the Markdown surface. Duplicate-system count and change-path entropy are MEDIUM because push-pull is adjacent rather than the authoritative detector, but it must still stay consistent with code-quality, evidence-class, test-audit, and PR-review wording (`C1`, `P1`). Lifecycle visibility is MEDIUM: input/output shape is clear, but its use as a supporting gate depends on caller-provided evidence-class and diff context.

### `agents/rca-orchestrator.md` - HIGH

Coverage gap, behavioral ambiguity, blast radius, duplicate-system count, change-path entropy, and lifecycle visibility are HIGH. The operator now maintains an RCA evidence-class ledger, requires Phase 1 reproduction and Phase 2 root cause to preserve runtime/proxy distinctions, rejects validation-only runtime fixes at Phase 3, records supplied evidence class at apply, and blocks green verification when validation changed without independent `runtime-path` proof (`agents/rca-orchestrator.md:13-13`, `agents/rca-orchestrator.md:44-49`, `agents/rca-orchestrator.md:54-54`). This is a caller-facing RCA contract for incidents and failing tests, with no runnable test for the new loop semantics. Language fragmentation is MEDIUM because Markdown operator instructions drive CLI child invocations and planning artifacts. The RCA mirror was explicitly identified as the weak point in P1 notes and vector A (`P1`, `A1`, `A2`), and it must stay aligned with `workflows/rca.md` plus implementation-pipeline/PR-review validation rules, producing HIGH entropy and lifecycle risk. Brittleness markers are LOW.

### `agents/test-audit-gate.md` - HIGH

Coverage gap is HIGH because the changed lightweight gate semantics have no runnable gate test. Behavioral ambiguity is MEDIUM: the prompt now defines blocking evidence-class mismatch and validation-surface weakening patterns, but the gate still synthesizes three sub-audits from external diff, spec, coverage, report, and ledger inputs (`agents/test-audit-gate.md:30-45`, `agents/test-audit-gate.md:65-70`, `agents/test-audit-gate.md:171-196`, `agents/test-audit-gate.md:270-276`). Blast radius is HIGH because this gate can block implementation and PR-review paths. Language fragmentation is MEDIUM because Markdown prompt composition consumes CLI inputs, CI artifacts, and durable ledgers. Duplicate-system count and change-path entropy are HIGH because the same anti-weakening and runtime-path proof rule must remain coherent with PR-review, coverage-auditor, implementation-pipeline, RCA, and evidence-class (`A1`, `P1`, `C1`). Lifecycle visibility is MEDIUM because the three sub-audit flow is named, but complete proof depends on external artifacts and consumers. Brittleness markers are LOW.

### `conventions/code-quality.md` - HIGH

Coverage gap is HIGH because the convention changed shared A1 interpretation with no runnable guard. Behavioral ambiguity is MEDIUM: the new text usefully limits validation-surface integrity to the adjacent case where proof pulls runtime truth from a test-owned substitute, but deciding whether a substitute is a valid common interface is evidence-sensitive (`conventions/code-quality.md:123-133`). Blast radius is HIGH because code-quality conventions are shared auditor inputs and shape downstream blocking findings. Language fragmentation is LOW for the edited convention text. Duplicate-system count and change-path entropy are MEDIUM because code-quality is explicitly not the primary detector, yet it must stay aligned with `push-pull-auditor.md` and the evidence-class reader rule (`A1`, `C1`). Lifecycle visibility is MEDIUM because the decoupling direction is named, but the convention does not itself define end-to-end runtime proof lifecycle. Brittleness markers are LOW.

### `conventions/evidence-class.md` - HIGH

Coverage gap, behavioral ambiguity, blast radius, change-path entropy, and lifecycle visibility are HIGH. This is a brand-new convention defining durable ledger paths, schema fields, minimum evidence classes, authorship, reader behavior, and composition rules (`conventions/evidence-class.md:1-27`, `conventions/evidence-class.md:29-58`, `conventions/evidence-class.md:60-83`, `conventions/evidence-class.md:85-99`). The architecture evidence says evidence-class state is necessary but passive without readers (`C1`, `C2`), and P2 only verified internal consistency, not runtime enforcement (`P2`). Blast radius is HIGH because the convention is a shared contract consumed by implementation-pipeline, PR-review, test-audit, coverage-auditor, push-pull, and RCA. Duplicate-system count is LOW because this is the canonical state surface rather than a parallel implementation. Language fragmentation is LOW for the convention itself, though downstream consumers cross file/artifact boundaries. Brittleness markers are LOW.

### `conventions/risk-profile.md` - HIGH

Coverage gap is HIGH because the convention change has no behavior test. Behavioral ambiguity is MEDIUM because it introduces a new distinction between risk scoring and evidence-class ledgers; the distinction is clear in text, but future risk profiles must decide when evidence-class uncertainty raises coverage, ambiguity, or lifecycle risk (`conventions/risk-profile.md:1-11`). Blast radius is HIGH because the risk-profile convention controls Phase 2.5/P3 risk scoring and downstream mode selection (`R1`). Language fragmentation is LOW. Duplicate-system count is LOW because the text explicitly avoids replacing evidence-class. Change-path entropy and lifecycle visibility are MEDIUM because this convention must stay coherent with evidence-class and prototype P3 scoring, but it is not itself a gate implementation (`C1`, `C2`). Brittleness markers are LOW.

### `evals/validation-surface-integrity/eval.md` - HIGH

This surface is scored as a WRITE-lifecycle behavior contract, not as a shipping detector. Coverage gap is MEDIUM rather than HIGH because the file is itself the prototype's intended proof artifact for structural-verification work, but it explicitly has no runnable detector, trace adapters, fixtures, rollout state, or enforcement wiring yet (`evals/validation-surface-integrity/eval.md:1-28`, `P2`). Behavioral ambiguity, blast radius, language fragmentation, duplicate-system count, change-path entropy, and lifecycle visibility are MEDIUM: the spec names unwanted behavior, non-fire cases, required trace fields, severity guidance, suggested actions, and updater-hotfix examples, but actual detection and enforcement remain downstream work (`evals/validation-surface-integrity/eval.md:38-73`, `evals/validation-surface-integrity/eval.md:128-144`, `evals/validation-surface-integrity/eval.md:148-159`, `evals/validation-surface-integrity/eval.md:177-248`). Three or more MEDIUM axes produce a HIGH verdict under `R1`; the HIGH verdict is about contract hardening risk, not an already-shipping detector failure. Brittleness markers are LOW.

### `workflows/implementation-pipeline.md` - HIGH

Coverage gap, behavioral ambiguity, blast radius, duplicate-system count, change-path entropy, and lifecycle visibility are HIGH. The workflow now requires Phase 3 validation-surface integrity content, Phase 4 non-LOW risk for proxy-only runtime claims, Phase 6 evidence-class preservation/output-index mapping/alignment before Step 6c, a Step 6c prohibition on validation-only green, and Phase 8 actual-diff test-audit enforcement (`workflows/implementation-pipeline.md:313-327`, `workflows/implementation-pipeline.md:352-358`, `workflows/implementation-pipeline.md:401-404`, `workflows/implementation-pipeline.md:420-443`, `workflows/implementation-pipeline.md:453-460`, `workflows/implementation-pipeline.md:462-486`, `workflows/implementation-pipeline.md:513-518`). This is the central implementation workflow contract; no runnable behavior tests cover the new rules. Language fragmentation is MEDIUM because Markdown workflow text controls shell/CLI dispatches and planning/evidence artifacts. Entropy is HIGH because the same semantic relation must propagate through proposer, critics, Step 6b/6c, PR-review, and evidence-class state (`A1`, `C1`, `O1`). Brittleness markers are LOW for this prototype edit.

### `workflows/pr-review.md` - HIGH

Coverage gap is HIGH because the changed PR-review test-audit rules have no runnable PR-review detector. Behavioral ambiguity is MEDIUM: the rules are concrete about evidence-class reading, runtime-path proof, and validation weakening, but reviewers still need to map actual diff/report evidence to prior validation meaning (`workflows/pr-review.md:143-156`, `workflows/pr-review.md:196-203`). Blast radius is HIGH because PR-review is the late actual-diff gate before draft PR. Language fragmentation is MEDIUM because the Markdown workflow consumes PR diffs, report bundles, Phase 6 artifacts, and evidence-class ledgers. Duplicate-system count and entropy are HIGH because PR-review overlaps with `test-audit-gate.md`, coverage-auditor quality classification, implementation Phase 8 routing, and RCA mirror rules (`A1`, `P1`, `O1`). Lifecycle visibility is MEDIUM because PR-review's local lifecycle is clear, but the origin of each required artifact spans earlier phases. Brittleness markers are LOW.

### `workflows/rca.md` - HIGH

Coverage gap, behavioral ambiguity, blast radius, duplicate-system count, change-path entropy, and lifecycle visibility are HIGH. The workflow now adds `${planning_dir}/rca/<failure-id>-evidence-class.md`, requires runtime/proxy classification at reproduction, preserves evidence class at root cause, rejects validation-only runtime fixes, records supplied evidence at apply, and blocks Verify-Or-Return on evidence-class mismatch (`workflows/rca.md:89-112`, `workflows/rca.md:123-129`, `workflows/rca.md:135-151`, `workflows/rca.md:163-175`). This is the caller-facing RCA lifecycle and mirrors `agents/rca-orchestrator.md`, so duplicate-system count and entropy are HIGH. Language fragmentation is MEDIUM because the Markdown workflow controls CLI child dispatches and planning artifacts. The RCA surface was explicitly identified as the weak mirror that allowed green verification to be over-trusted (`P1`, `A2`). Brittleness markers are LOW.

## Rollup Summary

Count by verdict:

| Verdict | Count |
|---|---:|
| HIGH | 12 |
| MEDIUM | 0 |
| LOW | 0 |

HIGH surfaces:

- `agents/coverage-auditor.md`
- `agents/implementation-pipeline-orchestrator.md`
- `agents/push-pull-auditor.md`
- `agents/rca-orchestrator.md`
- `agents/test-audit-gate.md`
- `conventions/code-quality.md`
- `conventions/evidence-class.md`
- `conventions/risk-profile.md`
- `evals/validation-surface-integrity/eval.md`
- `workflows/implementation-pipeline.md`
- `workflows/pr-review.md`
- `workflows/rca.md`

The rollup remains HIGH even though the prototype touched fewer surfaces than the original ACR-254 profile. The original WU profile scored a much wider anticipated surface set, with 24 of 29 surfaces HIGH (`O1`). This prototype narrowed the deliverable set, but every actual surface is still shared workflow/operator/convention/eval infrastructure with no runnable behavior coverage and non-local consumers.

## Architecture-Driven Vs Compositional HIGH Risk

Architecture-driven HIGH surfaces are high because of the shape of the new architecture itself. `conventions/evidence-class.md` is brand new durable state: it defines a ledger, schema, taxonomy, author phases, reader phases, and fail-closed rule, but it has no independent caller rollout or runnable enforcement in this prototype. `evals/validation-surface-integrity/eval.md` is intentionally WRITE lifecycle: it is a behavior contract and worked example, not a deployed detector. `conventions/risk-profile.md` is also architecture-adjacent because it adds the risk/evidence-class boundary that future risk authors must preserve.

Compositional HIGH surfaces are high because the prototype spreads one validation-surface integrity relation across existing consumers that downstream implementation work must actually consume. `workflows/implementation-pipeline.md`, `agents/implementation-pipeline-orchestrator.md`, `workflows/pr-review.md`, `agents/test-audit-gate.md`, `agents/coverage-auditor.md`, `workflows/rca.md`, and `agents/rca-orchestrator.md` all gained versions of the same rule: a green validation signal is not runtime proof when the validation surface was weakened and the supplied evidence class does not satisfy the required runtime class. `conventions/code-quality.md` and `agents/push-pull-auditor.md` are supporting compositional surfaces: they frame test-owned runtime truth as an uncontrolled-source shape where appropriate, without becoming the primary validation-integrity detector.

This artifact intentionally does not propose implementation tickets. It names the actual risk in the touched surfaces so P3.3 can decide follow-up work separately.
