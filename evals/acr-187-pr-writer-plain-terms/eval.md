---
eval_id: acr-187-pr-writer-plain-terms
behavior_class: ACR-187 PR-writer plain-terms structural drift
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - markdown-document
  - markdown-section-header
  - fenced-markdown-block
  - verifier-output
suggested_action_class: revise-pr-writer-guidance
---

# ACR-187 PR Writer Plain Terms

## Eval identity

This is a markdown behavior specification for `acr-187-pr-writer-plain-terms`, not runnable eval code. It translates the structural intent currently encoded in `tools/acr-187-verify/verify.py`, `tools/acr-187-verify/anchors.json`, and `tools/acr-187-verify/test_verify.py`.

The target behavior surface is `agents/pr-writer.md`. The eval is in `WRITE` lifecycle state: the spec is reviewable and binding as a behavior contract, but no runnable detector is required in this work unit.

## Unwanted behavior

The unwanted behavior is drift in the PR writer prompt that allows generated PR descriptions to start with technical, internal, or workflow-centered content instead of a short plain-language `## What this means` section for an external reviewer.

The drift classes are:

- the required audience rule no longer states that `## What this means` is the first content section;
- the audience rule no longer requires 1-3 sentences in plain language for a non-technical reviewer with zero technical context;
- the audience rule no longer lists the forbidden internal content categories;
- the routine-refactor guidance no longer prevents invented product value;
- the recommended body skeleton no longer starts its first fenced Markdown block with `## What this means`;
- technical sections no longer follow that opening section;
- stacking guidance no longer places `## Stacking` after `## What this means`;
- the worked example is missing, starts with the wrong heading, or contains internal jargon or historical PR-number references;
- the procedure no longer requires composing and self-auditing the `## What this means` section before technical content.

## Positive evidence

The future detector consumes the resolved `agents/pr-writer.md` text or a trace-attached snapshot of that text. Region boundaries are inherited from the legacy verifier:

- `audience_rules`: from `## Required Audience Rules -- ABSOLUTE` through, but not including, `## Recommended Body Structure`.
- `audience_what_this_means_subsection`: from `### What this means` through, but not including, `### No internal jargon`, inside `audience_rules`.
- `recommended_body_structure`: from `## Recommended Body Structure` through, but not including, `### Linear close-keyword footer`.
- `procedure`: from `## Procedure` through, but not including, `### Existing-PR title/body edit`.
- `worked_example`: from `### Worked example` through, but not including, `### Linear close-keyword footer` or `## Procedure`, inside `recommended_body_structure`.

The detector fires when any of the following named anchor checks fails. Substring checks are case-insensitive unless a future runnable detector records a stricter decision in its implementation notes.

- `audience_rule_what_this_means`: `audience_what_this_means_subsection` contains `` `## What this means` ``.
- `audience_rule_first_content_section`: `audience_what_this_means_subsection` contains `first content section`.
- `audience_rule_one_to_three_sentences`: `audience_what_this_means_subsection` contains `1-3 sentences`.
- `audience_rule_plain_language`: `audience_what_this_means_subsection` contains at least one of `plain language`, `non-technical reviewer`, or `zero technical context`.
- `audience_rule_forbidden_content`: `audience_what_this_means_subsection` contains all of `code references`, `code paths`, `agent names`, `phase numbers`, `planning phases`, `auditor verdicts`, `gate language`, `scratch or planning paths`, and `internal jargon`.
- `audience_rule_routine_refactor`: `audience_what_this_means_subsection` contains all of `routine refactor`, `no user-visible change`, and `inventing product value`.
- `body_structure_first_section`: the first fenced Markdown block in `recommended_body_structure` has first H2 exactly `## What this means`.
- `body_structure_technical_sections_follow`: `recommended_body_structure` matches a section-order pattern equivalent to: first fenced block contains `## What this means`, later `## What's broken`, and later `## What this PR does`.
- `body_structure_stacking_after`: `recommended_body_structure` states that `` `## Stacking` `` occurs after `` `## What this means` `` within a short local window.
- `worked_example_present`: `worked_example` contains `### Worked example` and a fenced Markdown block.
- `worked_example_starts_with_chosen_heading`: the first fenced Markdown block in `worked_example` has first H2 exactly `## What this means`.
- `worked_example_no_internal_jargon`: `worked_example` does not contain any of `planning/`, `~/projects/`, `${scratch_dir}`, `phase`, `audit`, `gate`, `DECISIONS`, `WU-`, or `wave`, and does not match `#[0-9]{3,}`.
- `procedure_compose_first`: `procedure` contains all of ``Compose the `## What this means` section before all technical content``, `stack`, `verification`, `out-of-scope`, and `footer`.
- `procedure_self_audit_first_heading`: `procedure` contains all of `first Markdown heading`, `first content section`, `first H2`, and `` `## What this means` ``.
- `procedure_self_audit_length`: `procedure` contains ``the `## What this means` section must be 1-3 sentences``.
- `procedure_self_audit_forbidden_content`: `procedure` contains all of `code references`, `code paths`, `agent names`, `phase numbers`, `planning phases`, `auditor verdicts`, `gate language`, `internal jargon`, `scratch paths`, and `planning paths`.
- `procedure_self_audit_routine_refactor`: `procedure` contains all of `routine refactor`, `no user-visible change`, and `inventing product value`.

Verifier-behavior evidence from `test_verify.py` is preserved as detector-output intent rather than as pytest shape: a clean target returns no finding, a target with one missing anchor returns a finding that names the failed anchor, and a target with multiple missing anchors may return one finding per anchor or one aggregate finding with `failed_anchors`.

## Non-fire cases

The eval returns no finding when:

- `agents/pr-writer.md` exists, is readable, and every named region above is found.
- The audience rule subsection includes the required `## What this means`, first-content-section, 1-3 sentence, plain-language, forbidden-content, and routine-refactor guidance.
- The recommended body structure's first fenced Markdown block starts with `## What this means`, and the skeleton orders the technical sections after it.
- Stacking guidance places the stacking section after the plain-language opener.
- The worked example exists, starts with `## What this means`, and avoids the listed internal jargon tokens and historical PR-number pattern.
- The procedure instructs the operator to compose and self-audit the `## What this means` section first, including length, forbidden-content, and routine-refactor checks.
- Mentions of forbidden tokens outside `worked_example` do not satisfy `worked_example_no_internal_jargon`.

## Required trace fields

The preferred evidence boundary is saved `agents trace --json` plus companion artifacts. A future runner must normalize these semantic fields before executing the detector:

- `eval_id`
- `root_invocation_uuid` or `session_id`
- `target_document_path`
- `target_document_text` or a stable content digest plus evidence excerpt resolver
- `target_document_revision` when available
- `region_spans` keyed by the five region names above
- `failed_anchor` or `failed_anchors`
- `missing_tokens`, `forbidden_tokens`, or `missing_pattern`
- `evidence_excerpt`
- `legacy_verifier_source_paths` when the finding is produced from verifier-output evidence instead of direct Markdown evidence

Missing target-document evidence is not a no-finding result. It is a runner evidence error or `NEEDS_INPUT` equivalent, because this eval cannot decide without the PR-writer prompt text.

## Finding shape

Findings preserve the minimum schema fields from `conventions/evals.md`: `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`.

Allowed extensions include `root_invocation_uuid`, `session_id`, `target_document_path`, `target_document_revision`, `failed_anchor`, `failed_anchors`, `region_name`, `region_span`, `missing_tokens`, `forbidden_tokens`, `missing_pattern`, `observed_heading`, and `evidence_excerpt`.

`severity` is `HIGH` when the failed anchor can allow reviewer-facing PR prose to begin with internal technical content or omit the plain-language opening contract. It may be `MEDIUM` for isolated worked-example wording drift when the normative audience and procedure rules remain intact.

## Suggested action

Return `revise-pr-writer-guidance`. The fix target is `agents/pr-writer.md`; restore the failed anchor in the named region without reintroducing pytest-on-Markdown tests or `tools/<wu>-verify/` verifier code.

## Lifecycle notes

This eval ships in `WRITE` state. It intentionally replaces the legacy verifier and pytest-scraper shape with a reviewable behavior spec. Runnable code, fixtures, CLI integration, trace adapters, and enforcement wiring are deferred to a future eval-runtime implementation ticket.

The spec preserves exact region carving and token/pattern intent from `tools/acr-187-verify/anchors.json`. The only translation change is that verifier CLI exit lines (`PASS <anchor>` / `FAIL <anchor>: ...`) become eval finding fields instead of a pytest-observed stdout contract.

## References

- `tools/acr-187-verify/verify.py`
- `tools/acr-187-verify/anchors.json`
- `tools/acr-187-verify/test_verify.py`
- `agents/pr-writer.md`
- `conventions/evals.md`
