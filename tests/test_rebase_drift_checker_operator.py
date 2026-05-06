"""Structural tests for the NES-167 rebase-drift-checker operator."""

import re
from pathlib import Path


OPERATOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "agents"
    / "rebase-drift-checker.md"
)

REQUIRED_FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_H2_HEADINGS = (
    "Role",
    "Use When",
    "Do Not Use When",
    "Required Inputs",
    "Optional Context",
    "Procedure",
    "Output Contract",
    "Stop Conditions",
    "Anti-Scope",
)


def _operator_text():
    assert OPERATOR_PATH.exists(), "missing agents/rebase-drift-checker.md"
    return OPERATOR_PATH.read_text(encoding="utf-8")


def _frontmatter_and_body(text):
    assert text.startswith("---\n"), "operator file must start with YAML frontmatter"
    closing = text.find("\n---\n", len("---\n"))
    assert closing != -1, "operator file must close YAML frontmatter before body"
    frontmatter = text[len("---\n") : closing]
    body = text[closing + len("\n---\n") :]
    assert body.strip(), "operator body must follow YAML frontmatter"
    return frontmatter, body


def _parse_frontmatter(text):
    frontmatter_text, _body = _frontmatter_and_body(text)
    frontmatter = {}
    for line in frontmatter_text.splitlines():
        if not line.strip():
            continue
        assert not line.startswith((" ", "\t")), (
            f"frontmatter key must be top-level: {line}"
        )
        key, separator, value = line.partition(":")
        assert separator, f"invalid frontmatter line: {line}"
        frontmatter[key.strip()] = value.strip()
    return frontmatter


def _section_after_h2(text, heading):
    pattern = rf"(?m)^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text)
    assert match, f"missing section heading: ## {heading}"

    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    if next_h1_or_h2:
        return following[: next_h1_or_h2.start()]
    return following


def test_frontmatter_present_and_correct():
    frontmatter = _parse_frontmatter(_operator_text())

    assert set(frontmatter) == REQUIRED_FRONTMATTER_KEYS, (
        f"frontmatter keys must be exactly {sorted(REQUIRED_FRONTMATTER_KEYS)}"
    )
    assert frontmatter["description"], "description frontmatter must be non-empty"
    assert frontmatter["model"] == "gpt-high", (
        "model frontmatter must be the literal gpt-high"
    )
    assert frontmatter["output_format"] == "''", (
        "output_format frontmatter must be the literal empty string marker: ''"
    )


def test_required_sections_present():
    text = _operator_text()
    _frontmatter, body = _frontmatter_and_body(text)
    h1s = re.findall(r"(?m)^#\s+(.+?)\s*$", body)
    h2s = re.findall(r"(?m)^##\s+(.+?)\s*$", body)

    assert h1s, "operator body must contain an H1"
    assert h1s[0] == "Rebase Drift Checker Operator", (
        "first H1 must be # Rebase Drift Checker Operator"
    )
    assert tuple(h2s) == REQUIRED_H2_HEADINGS, (
        f"H2 headings must be exactly, in order: {REQUIRED_H2_HEADINGS}"
    )


def test_required_input_names():
    required_inputs = _section_after_h2(_operator_text(), "Required Inputs")

    for input_name in (
        "merged_base_diff_path",
        "problem_map_path",
        "report_path",
    ):
        assert input_name in required_inputs, (
            f"Required Inputs section must name {input_name}"
        )


def test_output_vocabulary():
    text = _operator_text()
    _frontmatter, body = _frontmatter_and_body(text)

    for token in (
        "drift detected",
        "no drift",
        "rebase-drift:",
        "report=",
        "BLOCKED:",
    ):
        assert token in body, f"operator body must include output token {token}"
    assert "NEEDS_INPUT" in body, (
        "operator body must include NEEDS_INPUT or NEEDS_INPUT:"
    )

    output_contract = _section_after_h2(body, "Output Contract")
    assert "rebase-drift: drift detected; report=" in output_contract, (
        "Output Contract must document the drift-detected verdict line"
    )
    assert "rebase-drift: no drift; report=" in output_contract, (
        "Output Contract must document the no-drift verdict line"
    )


def test_overlap_standard_and_anti_scope():
    _frontmatter, body = _frontmatter_and_body(_operator_text())
    lower_body = body.lower()

    for term_group in (
        ("rename", "relocated"),
        ("helper", "helpers"),
        ("test", "tests"),
        ("doc", "docs", "comment", "comments"),
        ("contract", "contracts"),
    ):
        assert any(term in lower_body for term in term_group), (
            f"operator body must mention one overlap term from {term_group}"
        )

    anti_scope = _section_after_h2(body, "Anti-Scope")
    lower_anti_scope = anti_scope.lower()
    assert "orchestrator" in lower_anti_scope, (
        "Anti-Scope must exclude orchestrator dispatch wiring"
    )
    assert (
        "verified-rebase" in lower_anti_scope
        or "verified rebase" in lower_anti_scope
    ), "Anti-Scope must exclude verified-rebase mechanics"
    assert "conflict" in lower_anti_scope, (
        "Anti-Scope must exclude conflict resolution"
    )
    assert "push" in lower_anti_scope and "rollback" in lower_anti_scope, (
        "Anti-Scope must exclude push/rollback decisions"
    )
    assert "coverage" in lower_anti_scope, (
        "Anti-Scope must exclude coverage judgments"
    )
    assert "test" in lower_anti_scope and "rerun" in lower_anti_scope, (
        "Anti-Scope must exclude full test reruns"
    )
    assert "phase 6" in lower_anti_scope, (
        "Anti-Scope must exclude Phase 6 contract verification"
    )


def test_blocked_triggers_are_enumerated():
    _frontmatter, body = _frontmatter_and_body(_operator_text())
    stop_conditions = _section_after_h2(body, "Stop Conditions")
    procedure = _section_after_h2(body, "Procedure")
    combined = f"{procedure}\n{stop_conditions}"
    lower_combined = combined.lower()
    lower_body = body.lower()

    assert (
        "missing problem_map_path" in lower_combined
        or "missing problem map" in lower_combined
    ), "Stop Conditions or Procedure must enumerate missing problem_map_path"
    assert (
        "missing touched-surface enumeration" in lower_combined
        or "no touched-surface enumeration" in lower_combined
        or "problem map without touched" in lower_combined
    ), "Stop Conditions or Procedure must enumerate missing touched surfaces"
    assert "unreadable" in lower_combined and "diff" in lower_combined, (
        "Stop Conditions or Procedure must enumerate unreadable diff"
    )
    assert "malformed" in lower_combined and "diff" in lower_combined, (
        "Stop Conditions or Procedure must enumerate malformed diff"
    )
    assert "unwritable" in lower_combined and "report" in lower_combined, (
        "Stop Conditions or Procedure must enumerate unwritable report path"
    )
    assert "empty" in lower_body or "no-change" in lower_body, (
        "operator must distinguish a valid empty/no-change diff as no drift"
    )
    assert any(token in lower_body for token in ("unreadable", "malformed", "truncated")), (
        "operator must distinguish invalid diff evidence as BLOCKED"
    )


def test_procedure_reads_and_cross_references_both_inputs():
    procedure = _section_after_h2(_operator_text(), "Procedure")
    lower_procedure = procedure.lower()

    assert (
        "problem_map_path" in lower_procedure
        or "problem map" in lower_procedure
    ), "Procedure must read or reference problem_map_path"
    assert (
        "merged_base_diff_path" in lower_procedure
        or "merged-base diff" in lower_procedure
    ), "Procedure must read or reference merged_base_diff_path"
    assert any(
        token in lower_procedure
        for token in ("cross-reference", "cross reference", "intersect", "overlap")
    ), "Procedure must cross-reference/intersect/overlap both evidence sources"
