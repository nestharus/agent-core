#!/usr/bin/env python3
"""Standalone tests for the ACR-187 structural verifier."""

from __future__ import annotations

import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path
from typing import Callable


sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify  # noqa: E402


ANCHOR_NAMES = [
    "audience_rule_what_this_means",
    "audience_rule_first_content_section",
    "audience_rule_one_to_three_sentences",
    "audience_rule_plain_language",
    "audience_rule_forbidden_content",
    "audience_rule_routine_refactor",
    "body_structure_first_section",
    "body_structure_technical_sections_follow",
    "body_structure_stacking_after",
    "worked_example_present",
    "worked_example_starts_with_chosen_heading",
    "worked_example_no_internal_jargon",
    "procedure_compose_first",
    "procedure_self_audit_first_heading",
    "procedure_self_audit_length",
    "procedure_self_audit_forbidden_content",
    "procedure_self_audit_routine_refactor",
]


TESTS: list[Callable[[], None]] = []


def test(func: Callable[[], None]) -> Callable[[], None]:
    """orchestration"""

    TESTS.append(func)
    return func


def _baseline_operator() -> str:
    """accessor"""

    return """---
description: 'Write a PR title and body for a draft pull request'
model: claude-opus
---

# PR Writer

## Required Audience Rules -- ABSOLUTE

These are not preferences; violations will be rejected.

### What this means

Every PR body must start with `## What this means` as the first content section.
Write 1-3 sentences in plain language for a non-technical reviewer with zero technical context.
This section must not include code references, code paths, agent names, phase numbers, planning phases, auditor verdicts, gate language, scratch or planning paths, or internal jargon.
For routine refactor work, use plain framing such as routine refactor or no user-visible change rather than inventing product value.

### No internal jargon

Do not leak project-only terms into reviewer-facing prose.

## Recommended Body Structure

Most PRs read well with this skeleton:

```markdown
## What this means

(1-3 sentences in plain language.)

## What's broken

(Observable failure or gap.)

## What this PR does

(Behavior changes by audience and impact.)

## Verification

(Commands and observations.)
```

Stack PRs add `## Stacking` only after `## What this means`, so the plain-terms section remains first.

### Worked example

```markdown
## What this means

This PR makes generated pull request descriptions easier for reviewers to understand before they reach technical details.
It keeps the opening short and focused on the product outcome.

## What this PR does

- Adds a required opening section to the production PR body guidance.

## Verification

- Ran the structural verifier.
```

## Procedure

5. Compose the title and body following the rules above. Compose the `## What this means` section before all technical content, including stack, verification, out-of-scope, and footer content.
6. Self-audit before writing the output:
   - Body: the first Markdown heading, first content section, and first H2 must be `## What this means`.
   - Body: the `## What this means` section must be 1-3 sentences.
   - Body: the `## What this means` section must contain no code references, code paths, agent names, phase numbers, planning phases, auditor verdicts, gate language, internal jargon, scratch paths, or planning paths.
   - Body: for a routine refactor, use routine refactor or no user-visible change framing instead of inventing product value.
"""


MUTATIONS = {
    "audience_rule_what_this_means": {
        "old": "Every PR body must start with `## What this means` as the first content section.",
        "new": "Every PR body must start with a brief reviewer-facing opener.",
    },
    "audience_rule_first_content_section": {
        "old": "as the first content section.",
        "new": "near the beginning.",
    },
    "audience_rule_one_to_three_sentences": {
        "old": "Write 1-3 sentences in plain language",
        "new": "Write a short paragraph in plain language",
    },
    "audience_rule_plain_language": {
        "old": "plain language for a non-technical reviewer with zero technical context",
        "new": "review-oriented language",
    },
    "audience_rule_forbidden_content": {
        "old": "code references, code paths, agent names, phase numbers, planning phases, auditor verdicts",
        "new": "irrelevant implementation details",
    },
    "audience_rule_routine_refactor": {
        "old": "routine refactor or no user-visible change rather than inventing product value",
        "new": "maintenance context rather than inventing product value",
    },
    "body_structure_first_section": {
        "old": "```markdown\n## What this means\n\n(1-3 sentences in plain language.)",
        "new": "```markdown\n## What's broken\n\n(Observable failure or gap.)",
    },
    "body_structure_technical_sections_follow": {
        "old": "## What's broken\n\n(Observable failure or gap.)\n\n## What this PR does\n\n(Behavior changes by audience and impact.)",
        "new": "### Background\n\n(Reviewer context.)\n\n### Changes\n\n(Behavior changes by audience and impact.)",
    },
    "body_structure_stacking_after": {
        "old": "Stack PRs add `## Stacking` only after `## What this means`, so the plain-terms section remains first.",
        "new": "Stack PRs add `## Stacking` near the top.",
    },
    "worked_example_present": {
        "old": """### Worked example

```markdown
## What this means

This PR makes generated pull request descriptions easier for reviewers to understand before they reach technical details.
It keeps the opening short and focused on the product outcome.

## What this PR does

- Adds a required opening section to the production PR body guidance.

## Verification

- Ran the structural verifier.
```
""",
        "new": "",
    },
    "worked_example_starts_with_chosen_heading": {
        "old": "### Worked example\n\n```markdown\n## What this means",
        "new": "### Worked example\n\n```markdown\n## Summary",
    },
    "worked_example_no_internal_jargon": {
        "old": "It keeps the opening short and focused on the product outcome.",
        "new": "It keeps the opening short and focused on the product outcome while avoiding planning/notes leakage.",
    },
    "worked_example_no_internal_jargon_historical_pr_reference": {
        "old": "It keeps the opening short and focused on the product outcome.",
        "new": "It keeps the opening short and focused on the product outcome introduced after #123.",
    },
    "procedure_compose_first": {
        "old": "Compose the `## What this means` section before all technical content, including stack, verification, out-of-scope, and footer content.",
        "new": "Compose the body using whichever sections apply.",
    },
    "procedure_self_audit_first_heading": {
        "old": "the first Markdown heading, first content section, and first H2 must be `## What this means`.",
        "new": "the opening section must be clear.",
    },
    "procedure_self_audit_length": {
        "old": "the `## What this means` section must be 1-3 sentences.",
        "new": "the `## What this means` section must be concise.",
    },
    "procedure_self_audit_forbidden_content": {
        "old": "code references, code paths, agent names, phase numbers, planning phases, auditor verdicts, gate language, internal jargon, scratch paths, or planning paths",
        "new": "irrelevant internal details",
    },
    "procedure_self_audit_routine_refactor": {
        "old": "for a routine refactor, use routine refactor or no user-visible change framing instead of inventing product value.",
        "new": "for a routine refactor, describe the work honestly.",
    },
}


def _mutated_operator(anchor_name: str) -> str:
    """orchestration"""

    spec = MUTATIONS[anchor_name]
    operator_text = _baseline_operator()
    _require_substring(
        operator_text,
        spec["old"],
        f"mutation target not found: {spec['old']!r}",
    )
    return _replace_first_occurrence(operator_text, spec["old"], spec["new"])


def _str_contains(text: str, old: str) -> bool:
    """predicate"""

    return old in text


def _require_substring(text: str, old: str, context: str) -> None:
    """validator"""

    if not _str_contains(text, old):
        raise AssertionError(context)


def _replace_first_occurrence(text: str, old: str, new: str) -> str:
    """mapper"""

    return text.replace(old, new, 1)


def _check_function(anchor_name: str) -> Callable[[str], None]:
    """accessor"""

    return getattr(verify, f"check_{anchor_name}")


def _assert_check_passes(anchor_name: str, operator_text: str) -> None:
    """validator"""

    try:
        _check_function(anchor_name)(operator_text)
    except verify.CheckFailed as exc:
        raise AssertionError(f"{anchor_name} should pass: {exc}") from exc


def _assert_check_fails(anchor_name: str, operator_text: str) -> None:
    """validator"""

    try:
        _check_function(anchor_name)(operator_text)
    except verify.CheckFailed:
        return
    raise AssertionError(f"{anchor_name} should fail")


def _exit_code_from_system_exit(exc: SystemExit) -> int:
    """mapper"""

    if exc.code is None:
        return 0
    if isinstance(exc.code, int):
        return exc.code
    return 1


def _run_main_with_operator(operator_text: str) -> tuple[int, str]:
    """orchestration"""

    with tempfile.TemporaryDirectory() as temp_dir:
        operator_path = Path(temp_dir) / "pr-writer.md"
        operator_path.write_text(operator_text, encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                result = verify.main(["--operator-path", str(operator_path)])
                code = int(result)
            except SystemExit as exc:
                code = _exit_code_from_system_exit(exc)
            except verify.CheckFailed:
                code = 1
        return code, output.getvalue()


def _assert_fail_line(stdout: str, anchor_name: str) -> None:
    """validator"""

    pattern = rf"^FAIL {re.escape(anchor_name)}: .+$"
    if re.search(pattern, stdout, flags=re.MULTILINE) is None:
        raise AssertionError(f"missing well-formed fail line for {anchor_name}:\n{stdout}")


def _assert_positive_and_negative(anchor_name: str) -> None:
    """validator"""

    _assert_check_passes(anchor_name, _baseline_operator())
    _assert_check_fails(anchor_name, _mutated_operator(anchor_name))


@test
def test_audience_rule_what_this_means_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("audience_rule_what_this_means")


@test
def test_audience_rule_first_content_section_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("audience_rule_first_content_section")


@test
def test_audience_rule_one_to_three_sentences_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("audience_rule_one_to_three_sentences")


@test
def test_audience_rule_plain_language_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("audience_rule_plain_language")


@test
def test_audience_rule_forbidden_content_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("audience_rule_forbidden_content")


@test
def test_audience_rule_routine_refactor_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("audience_rule_routine_refactor")


@test
def test_body_structure_first_section_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("body_structure_first_section")


@test
def test_body_structure_technical_sections_follow_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("body_structure_technical_sections_follow")


@test
def test_body_structure_stacking_after_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("body_structure_stacking_after")


@test
def test_worked_example_present_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("worked_example_present")


@test
def test_worked_example_starts_with_chosen_heading_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("worked_example_starts_with_chosen_heading")


@test
def test_worked_example_no_internal_jargon_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("worked_example_no_internal_jargon")


@test
def test_worked_example_no_internal_jargon_historical_pr_reference_negative() -> None:
    """validator"""

    _assert_check_fails(
        "worked_example_no_internal_jargon",
        _mutated_operator("worked_example_no_internal_jargon_historical_pr_reference"),
    )


@test
def test_procedure_compose_first_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("procedure_compose_first")


@test
def test_procedure_self_audit_first_heading_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("procedure_self_audit_first_heading")


@test
def test_procedure_self_audit_length_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("procedure_self_audit_length")


@test
def test_procedure_self_audit_forbidden_content_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("procedure_self_audit_forbidden_content")


@test
def test_procedure_self_audit_routine_refactor_positive_and_negative() -> None:
    """validator"""

    _assert_positive_and_negative("procedure_self_audit_routine_refactor")


@test
def test_main_exits_zero_for_synthetic_operator() -> None:
    """validator"""

    code, stdout = _run_main_with_operator(_baseline_operator())
    if code != 0:
        raise AssertionError(f"expected exit 0, got {code}:\n{stdout}")
    for anchor_name in ANCHOR_NAMES:
        if f"PASS {anchor_name}" not in stdout:
            raise AssertionError(f"missing PASS line for {anchor_name}:\n{stdout}")
    if "FAIL " in stdout:
        raise AssertionError(f"unexpected FAIL line:\n{stdout}")


@test
def test_main_exits_one_for_missing_anchor() -> None:
    """validator"""

    anchor_name = "audience_rule_what_this_means"
    code, stdout = _run_main_with_operator(_mutated_operator(anchor_name))
    if code != 1:
        raise AssertionError(f"expected exit 1, got {code}:\n{stdout}")
    _assert_fail_line(stdout, anchor_name)


@test
def test_fail_lines_are_well_formed_for_each_anchor() -> None:
    """validator"""

    for anchor_name in ANCHOR_NAMES:
        code, stdout = _run_main_with_operator(_mutated_operator(anchor_name))
        if code != 1:
            raise AssertionError(f"{anchor_name}: expected exit 1, got {code}:\n{stdout}")
        _assert_fail_line(stdout, anchor_name)


def _run_registered_tests(
    tests: list[Callable[[], None]],
) -> list[tuple[str, bool, str]]:
    """orchestration"""

    results: list[tuple[str, bool, str]] = []
    for func in tests:
        try:
            func()
        except Exception as exc:  # noqa: BLE001
            results.append((func.__name__, False, str(exc)))
        else:
            results.append((func.__name__, True, ""))
    return results


def _format_test_status_line(name: str, ok: bool, msg: str) -> str:
    """formatter"""

    if ok:
        return f"PASS {name}"
    return f"FAIL {name}: {msg}"


def main() -> int:
    """orchestration"""

    results = _run_registered_tests(TESTS)
    for name, ok, msg in results:
        print(_format_test_status_line(name, ok, msg))
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
