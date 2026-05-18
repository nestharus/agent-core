# Evidence Class

Evidence class is the durable state that says what kind of proof a workflow has for a surface, and what kind of proof the surface requires. It exists to prevent a green validation proxy from being mistaken for runtime behavior.

This convention is intentionally small. It does not prescribe a full ontology of evidence. It defines only the minimum distinction needed for validation-surface integrity: a runtime claim cannot be cleared by evidence that only exercised a test harness, mock, fixture, schema relaxation, or other validation proxy.

## Vocabulary

- `surface_id`: stable identifier for the behavior, artifact, dependency, command, job, endpoint, or workflow claim being validated.
- `claim`: the behavior or property being asserted for that surface.
- `required_evidence_class`: the minimum class of evidence needed before a gate may clear the claim.
- `supplied_evidence_class`: the strongest class of evidence currently supplied for that claim.
- `validation_surface_ref`: the test, eval, fixture, mock, harness, CI job, reproduction command, report, or runtime command that produced the evidence.
- `runtime_surface_ref`: the actual runtime path or artifact the claim is about when the claim is runtime-scoped.

## Minimum Classes

These classes are derived from the ACR-254 updater-hotfix failure shape, not from a general taxonomy:

| Class | Meaning | Can satisfy |
|---|---|---|
| `runtime-path` | Evidence from the actual runtime artifact, deployed/packaged artifact, container, production-path command, field log, durable runtime state, or equivalent supported customer path. | Runtime claims and weaker claims when the validation preserves the same observable. |
| `validation-proxy` | Evidence from tests, evals, CI jobs, mocks, fixtures, harnesses, generated baselines, local simulations, or reproduction tests that stand in for the runtime path. | Test/proxy claims only, unless a separate entry justifies why the proxy is equivalent to the runtime path. |
| `static-or-documentary` | Evidence from code reading, specs, diffs, dependency files, plans, or documentation without executing the relevant path. | Static/documentary claims only. |
| `unknown` | The workflow does not yet know what class it has. | Nothing; readers fail closed. |

No class is permanently stronger in the abstract. Strength is claim-relative. For ACR-254, the load-bearing rule is narrow: `validation-proxy`, `static-or-documentary`, and `unknown` do not satisfy a `runtime-path` required class for a runtime-scoped claim.

## Entry Schema

Durable evidence-class ledgers are Markdown files with a table or YAML blocks. The canonical implementation-pipeline ledger path is:

```text
${planning_dir}/evidence-class.md
```

The canonical RCA ledger path is:

```text
${planning_dir}/rca/<failure-id>-evidence-class.md
```

Each entry must carry these fields:

```yaml
surface_id: <stable id>
claim: <runtime/test/static claim>
required_evidence_class: <runtime-path | validation-proxy | static-or-documentary | unknown>
supplied_evidence_class: <runtime-path | validation-proxy | static-or-documentary | unknown>
validation_surface_ref: <path, command, report, log, or none>
runtime_surface_ref: <path, artifact, command, deployed path, or none>
producer_phase: <phase/operator that wrote or last updated this entry>
consumer_phases: [<phase/gate names expected to read it>]
status: <required | satisfied | mismatched | residual>
justification: <why this required/supplied pairing is valid>
```

`status: residual` is allowed only when the owning workflow already has a residual-risk mechanism and the residual does not collapse the approved net-value case. A runtime-scoped claim with `required_evidence_class: runtime-path` and no `runtime-path` supplied evidence is normally `mismatched`, not residual.

## Authorship

Implementation pipeline:

- Phase 2.5 authors initial entries when the lifecycle, entrypoint, coverage, or risk-profile research identifies a runtime-scoped surface, changed validation surface, or unsupported evidence boundary.
- Phase 3 updates entries in the proposal by naming the proposed proof per surface, including required and supplied evidence classes in the test-intent track.
- Phase 6b/6c update supplied evidence when tests, eval specs, runtime commands, reports, or residual entries are produced.
- Phase 8 does not author the required class for a claim; it reads the ledger and may update only the observed supplied evidence from the actual diff and report bundle.

RCA:

- Phase 1 or the failing-test trigger records the evidence class of the original signal.
- Phase 2 records which evidence class supports the root-cause claim.
- Phase 3 records the required evidence class for fix verification.
- Phase 5 records the supplied evidence class from local verification notes and changed paths.
- Phase 6 reads the ledger before accepting a green rerun as verified.

## Reader Rule

Any gate or auditor that consumes evidence-class state compares required and supplied class per `surface_id`.

- If `required_evidence_class: runtime-path` and supplied evidence is only `validation-proxy`, `static-or-documentary`, or `unknown`, the gate returns a blocking mismatch.
- If the validation surface changed in the same WU, PR, or RCA cycle, green output from that surface remains `validation-proxy` until an independent entry supplies `runtime-path` evidence or the workflow records a justified proxy-equivalence entry.
- If `required_evidence_class` is `unknown`, the reader fails closed with `NEEDS_INPUT` only when the class is a genuine human-owned evidence/trade-off question; otherwise it returns a blocking artifact-quality failure.

## Composition

Evidence class composes with existing state rather than replacing it:

- `risk-profile.md` decides rigor and mode. It may cite evidence-class uncertainty as coverage, behavioral ambiguity, or lifecycle-visibility evidence, but it is not the evidence-class ledger.
- `risk/NN-test-residuals.md` records bounded unverified test risks. It does not turn a runtime-path mismatch into a harmless residual when that mismatch collapses supported-surface value.
- `test-audit-gate.md` and `workflows/pr-review.md` consume evidence-class ledgers to decide whether test evidence proves the claim it is being used to prove.
- `push-pull-auditor.md` may cite evidence-class entries as context for runtime truth boundaries, but evidence-class is not a push-vs-pull coupling score.
- `process-tree-auditor.md` proves that the producing and consuming phases ran and that artifacts are current; it does not decide whether supplied evidence satisfies required evidence class.

## Anti-Scope

- This convention does not define a new auditor count, auditor name, workflow gate, eval runner, or machine enforcement layer.
- This convention does not require a universal evidence taxonomy beyond the four minimum classes above.
- This convention does not replace test firstness, supported-surface verification, code-quality gates, risk-profile scoring, or process-tree audit.
