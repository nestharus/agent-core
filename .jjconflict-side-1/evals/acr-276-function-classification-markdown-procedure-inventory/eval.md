---
id: acr-276-function-classification-markdown-procedure-inventory
eval_id: acr-276-function-classification-markdown-procedure-inventory
lifecycle: WRITE
lifecycle_state: WRITE
operator_under_test: agents/function-classification-auditor.md
owner_wu: ACR-276
risk_class: HIGH
behavior_class: Structural verification of function-classification-auditor inventory boundary
severity_when_fires: HIGH
evidence_source_kinds:
  - synthetic-fixture-inline
  - representative-ai-workflows-agents-conventions-quotation-inline
suggested_action_class: revise-function-classification-auditor-inventory-boundary
---

# ACR-276 Function Classification Markdown Procedure Inventory Eval

## Declared roles

`validator`

This file-local declaration follows `~/ai/conventions/code-quality.md` `## Declared roles`: this eval spec validates the `function-classification-auditor` inventory boundary by protecting A1 strictness for real executable functions while rejecting false `multi-classifier function` findings on non-runnable `~/ai` Markdown procedure prose.

## Lifecycle state

WRITE

This is an eval-spec authoring artifact only. It defines the behavior contract for a future detector or review pass; it does not provide runnable detector code, fixtures, CI wiring, pytest tests, or verifier scripts.

## Identity

- `eval_id`: `acr-276-function-classification-markdown-procedure-inventory`
- `owner_wu`: `ACR-276`
- `operator_under_test`: `function-classification-auditor`
- `artifact`: `evals/acr-276-function-classification-markdown-procedure-inventory/eval.md`
- `behavior_class`: structural verification of function-classification-auditor inventory boundary
- `severity_when_fires`: `HIGH`

## Behavior contract

The `function-classification-auditor` must build its A5 inventory from actual executable function-like symbols with inspectable bodies. Real source-code functions, methods, closures, lambdas, shell function definitions, or equivalent language-level symbols remain eligible for A1 scoring. Markdown headings, workflow phases, operator procedure sections, convention narrative sections, shell snippets, and YAML carriers in `~/ai/{workflows,agents,conventions}/*.md` are not A5 function inventory items merely because their prose describes validation, parsing, mapping, formatting, routing, or sequencing work.

This eval finding should fire when either side of that boundary regresses:

- A real source-code function with two or more A1 categories is downgraded because of the markdown-procedure carve-out.
- A non-runnable `~/ai` Markdown procedure heading or prose section is admitted as a function/symbol row and receives a `multi-classifier function` finding.

## Evidence source kinds

Evidence for this WRITE-state spec is inline and representative:

- synthetic source-code fixture bodies for real executable functions;
- representative `~/ai/workflows/*.md`, `~/ai/agents/*.md`, and `~/ai/conventions/*.md` Markdown procedure quotations expressed in this spec body.

No runnable detector is part of this WU.

## Finding contract

Every future finding produced from this eval must preserve the minimum fields from `~/ai/conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Recommended ACR-276 extensions:

- `scenario_id`
- `operator_under_test`
- `observed_auditor_verdict`
- `expected_auditor_verdict`
- `fixture_kind`
- `inventory_boundary_failure`
- `affected_report_section`

Severity guidance:

- `HIGH` when the observed auditor verdict weakens A1 for a real multi-class source-code function or emits a `multi-classifier function` finding for ordinary `~/ai` Markdown procedure prose.
- `MEDIUM` when the observed report is ambiguous enough to allow either regression but does not clearly emit the forbidden verdict.
- `LOW` only for evidence drift or incomplete trace fields in a future runnable detector.

## Scenarios

### S-001: real multi-classifier source function stays HIGH

Operator under test: `function-classification-auditor`.

Fixture description: A real Python function body parses external input, validates it, maps it into a domain object, and formats an error/response inline:

```python
import json


def import_user(raw_event: str) -> dict:
    try:
        payload = json.loads(raw_event)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"invalid json: {exc.msg}"}

    email = str(payload.get("email", "")).strip()
    if "@" not in email:
        return {"ok": False, "error": f"invalid email: {email}"}

    user = {
        "email": email.lower(),
        "display_name": str(payload.get("name", "")).strip() or "unknown",
        "source": "import",
    }
    return {"ok": True, "user": user, "message": f"created user {user['email']}"}
```

Expected auditor verdict: `HIGH` `multi-classifier function` with two or more A1 categories. The expected category evidence includes parsing `raw_event`, validating email shape, mapping payload fields into the `user` domain object, and formatting returned error/response strings inline.

Protected behavior: the markdown-procedure carve-out does not weaken scoring for real source-code functions.

### S-002: workflow `### N. Preflight` step is not a function

Operator under test: `function-classification-auditor`.

Fixture description: A representative `~/ai/workflows/*.md` numbered procedure step whose prose says validate inputs, map paths into bundle names, format status output, and sequence child work:

```markdown
### 1. Preflight

Validate that `repo_root`, `worktree_path`, and `scratch_dir` are readable.
Map each provided path into the bundle name used for the run report.
Format a short status line for the caller before sequencing child work.
Route blocked or missing inputs to the caller instead of continuing.
```

Expected auditor verdict: NO `multi-classifier function` finding for the `### 1. Preflight` heading or section.

Protected behavior: workflow procedure steps can describe multiple responsibilities without being inventoried as executable functions.

### S-003: operator `## Procedure: Verified Rebase` section is not a function

Operator under test: `function-classification-auditor`.

Fixture description: A representative `~/ai/agents/*.md` `## Procedure:` section whose prose validates preconditions, maps command outputs, formats artifacts, and sequences commands:

```markdown
## Procedure: Verified Rebase

Validate that the working tree has no unrelated dirty files before starting.
Run the rebase command, map command output into a conflict summary, and
format the conflict artifact for review. Sequence resolution, verification,
and handback commands according to the caller's requested branch.
```

Expected auditor verdict: NO `multi-classifier function` finding for the `## Procedure: Verified Rebase` heading or section.

Protected behavior: operator procedure sections remain prompt workflow structure, not source-code symbols.

### S-004: convention narrative procedure prose is not a function

Operator under test: `function-classification-auditor`.

Fixture description: A representative `~/ai/conventions/*.md` narrative section explaining a procedure in prose, mentioning validate, map, format, parse, and route steps without declaring an executable function body:

```markdown
## Procedure Notes

The caller validates the artifact list before routing it to the selected
operator. The operator may parse existing reports, map findings into a
summary table, and format a concise handoff note. These steps describe the
workflow contract; they do not declare a function, method, closure, lambda,
shell function, or other executable symbol body.
```

Expected auditor verdict: NO `multi-classifier function` finding for the narrative section.

Protected behavior: convention prose can define process semantics without entering A5 per-function scoring.

## Anti-scope

This WU must not produce or require any of the following:

- `tests/test_*.py`
- pytest imports, pytest fixtures, or pytest-shaped assertion code
- `tools/<wu>-verify/*.py`
- `evals/acr-276-function-classification-markdown-procedure-inventory/eval.py`
- `evals/acr-276-function-classification-markdown-procedure-inventory/eval.rs`
- `evals/acr-276-function-classification-markdown-procedure-inventory/fixtures/`
- runnable detectors, parser code, adapters, CI wiring, cron jobs, or ticket-backend automation

## Suggested action

Revise `agents/function-classification-auditor.md` so its inventory procedure admits only actual executable function-like symbols with inspectable bodies while preserving the existing A1 category vocabulary, threshold row, and `multi-classifier function` failure mode for real source-code functions.

Excluded Markdown procedure headings or sections must not appear as rows in `Functions In Touched Files` or `Multi-Classifier Findings`. They may appear only in residual ambiguity or stop-condition notes when needed to explain inventory exclusion or a genuine unresolved boundary ambiguity.

## Lifecycle notes

ACR-276 owns only this WRITE-state eval spec for Step 6b. Step 6c owns the auditor markdown refinement and must satisfy these scenarios without modifying this eval spec or adding runnable eval/test infrastructure.

## Cross-references

- Contract: `/home/nes/ai/planning/acr-276-fc-auditor-markdown-procedure/contracts/acr-276-fca-markdown-procedure-inventory.md`
- Proposal: `/home/nes/ai/planning/acr-276-fc-auditor-markdown-procedure/proposals/acr-276-ACR-276.md`
- Hookpoint research: `/home/nes/ai/planning/acr-276-fc-auditor-markdown-procedure/research/acr-276-hookpoints.md`
- Eval convention: `/home/nes/ai/conventions/evals.md`
- Routing precedent: `/home/nes/ai/evals/route-ai-structural-guards-to-eval-specs/eval.md`
- A1 scope precedent: `/home/nes/ai/evals/auditor-whole-file-scope/eval.md`
