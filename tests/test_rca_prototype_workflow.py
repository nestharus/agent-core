"""Structural tests for ACR-144 prototype RCA workflow surfaces.

Contract:
/home/nes/projects/ai/planning/acr-144-rca-prototype-workflow/contracts/acr-144-rca-prototype.md

T24 is intentionally not represented as a test: README discoverability is out
of scope for ACR-144 per proposal D8.
"""

import json
import re
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_MD = REPO_ROOT / "workflows" / "rca-prototype.md"
OPERATOR_MD = REPO_ROOT / "agents" / "prototype-rca-orchestrator.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
INDEX_JSON = REPO_ROOT / "workflows" / "index.json"
MODELS_ROLES_MD = REPO_ROOT / "models" / "roles.md"

DISPATCH_CONTRACT_KEYS = {
    "orchestrator",
    "inputs",
    "expectations",
    "outputs",
    "non_goals",
}
REQUIRED_WORKFLOW_H2 = {
    "## Purpose",
    "## Use When",
    "## Do Not Use When",
    "## Required Inputs",
    "## Output Paths",
    "## Phase Map",
    "## Phase 1 - Root Cause",
    "## Phase 2 - Fix And Targeted Re-Run",
    "## Loop Semantics",
    "## Handback Contract",
    "## Stop Conditions",
    "## Anti-Scope",
    "## Cross-References",
}
REQUIRED_OPERATOR_H2 = {
    "## Role",
    "## Use When",
    "## Do Not Use When",
    "## Required Inputs",
    "## Procedure",
    "## Output Contract",
    "## NEEDS_INPUT Handling",
    "## Stop Conditions",
    "## Anti-Scope",
}
OPERATOR_FRONTMATTER_KEYS = {"description", "model", "output_format"}
TRIGGER_ENVELOPE_TOKENS = (
    "trigger_type",
    "trigger_evidence_path",
    "trigger_command",
    "failure_id",
    "repo_root",
    "worktree_path",
    "planning_dir",
    "scratch_dir",
    "hard_cap",
    "handback_callback",
    "qa_use_case_id",
    "test",
    "qa",
)
HANDback_TOKENS = (
    "outcome",
    "failure_id",
    "iterations",
    "fix_artifact_path",
    "evidence_paths",
    "fixed",
    "cap-hit",
    "blocked",
    "needs-input",
)
AGENTS_ROUTING_INPUTS = (
    "failure_id",
    "trigger_type",
    "trigger_evidence_path",
    "repo_root",
    "worktree_path",
    "planning_dir",
    "scratch_dir",
    "handback_callback",
    "trigger_command",
    "qa_use_case_id",
    "hard_cap",
)
ANTI_SCOPE_PATHS = (
    r"(?:~/ai|/home/nes/ai)/workflows/rca\.md",
    r"(?:~/ai|/home/nes/ai)/agents/behavior-investigator\.md",
    r"(?:~/ai|/home/nes/ai)/agents/incident-investigator\.md",
)
ANTI_FRAMING_ALLOWED_SECTIONS = {
    "Anti-Scope",
    "Cross-References",
    "Stop Conditions",
}
ANTI_FRAMING_PHRASES = (
    "machine enforcement",
    "machine-enforcement",
    "tracked in a separate ticket",
)
RUNTIME_CEREMONY_TOKENS = (
    "coderabbit",
    "risk gate",
    "risk-gate",
    "process-tree audit",
    "process tree audit",
    "process-tree-audit",
    "code review",
)
NEGATION_TERMS = (
    "not",
    "no",
    "without",
    "out of scope",
    "do not",
    "does not",
    "must not",
    "never",
    "excluded",
    "anti-scope",
)


def _read_required_file(path, item_id):
    assert path.is_file(), f"{item_id}: required file is missing: {path}"
    text = path.read_text(encoding="utf-8")
    assert text.strip(), f"{item_id}: required file must be non-empty: {path}"
    return text


def _frontmatter_and_body(text, item_id):
    assert text.startswith("---\n") or text.startswith("---\r\n"), (
        f"{item_id}: Markdown file must start with YAML frontmatter"
    )
    lines = text.splitlines()
    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    assert closing_index is not None, f"{item_id}: YAML frontmatter must close with ---"
    raw_yaml = "\n".join(lines[1:closing_index])
    parsed = yaml.safe_load(raw_yaml)
    assert isinstance(parsed, dict), f"{item_id}: frontmatter must parse as a mapping"
    return parsed, "\n".join(lines[closing_index + 1 :])


def _h1_headings(body):
    return re.findall(r"(?m)^# .+$", body)


def _h2_headings(body):
    return re.findall(r"(?m)^## .+$", body)


def _section_after_h2(text, heading, item_id):
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    assert match, f"{item_id}: missing section heading {heading}"
    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    return following[: next_h1_or_h2.start()] if next_h1_or_h2 else following


def _section_any_h2(text, headings, item_id):
    for heading in headings:
        match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", text)
        if match:
            following = text[match.end() :]
            next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
            return following[: next_h1_or_h2.start()] if next_h1_or_h2 else following
    expected = ", ".join(f"## {heading}" for heading in headings)
    pytest.fail(f"{item_id}: missing one of section headings: {expected}")


def _h2_sections(text):
    matches = list(re.finditer(r"(?m)^##\s+(?P<title>.+?)\s*$", text))
    sections = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group("title")] = text[match.end() : end]
    return sections


def _contains_regex(text, pattern, message):
    assert re.search(pattern, text, re.IGNORECASE | re.DOTALL), message


def _contains_tokens(text, tokens, item_id):
    missing = [token for token in tokens if token not in text]
    assert missing == [], f"{item_id}: missing required tokens: {missing}"


def _routing_row(text, name, item_id):
    match = re.search(rf"(?ms)^- `{re.escape(name)}` - .*?(?=^- `|\Z)", text)
    assert match, f"{item_id}: AGENTS.md missing routing row for {name}"
    return match.group(0)


def _workflow_text(item_id):
    return _read_required_file(WORKFLOW_MD, item_id)


def _workflow_body(item_id):
    _frontmatter, body = _frontmatter_and_body(_workflow_text(item_id), item_id)
    return body


def _operator_text(item_id):
    return _read_required_file(OPERATOR_MD, item_id)


def test_workflow_file_exists_t1():
    assert WORKFLOW_MD.is_file(), f"T1: workflow file must exist at {WORKFLOW_MD}"
    assert WORKFLOW_MD.stat().st_size > 0, "T1: workflow file must be non-empty"


def test_workflow_frontmatter_valid_t2():
    frontmatter, _body = _frontmatter_and_body(_workflow_text("T2"), "T2")
    workflow = frontmatter.get("workflow")
    contract = frontmatter.get("workflow_dispatch_contract")

    assert isinstance(workflow, dict), "T2: workflow frontmatter must be a mapping"
    assert workflow.get("id") == "rca-prototype", (
        "T2: workflow.id must equal rca-prototype"
    )
    assert workflow.get("id") == WORKFLOW_MD.stem, (
        "T2: workflow.id must equal the workflow filename stem"
    )
    assert isinstance(contract, dict), (
        "T2: workflow_dispatch_contract must be a mapping"
    )
    assert set(contract) == DISPATCH_CONTRACT_KEYS, (
        "T2: workflow_dispatch_contract keys must be exactly "
        f"{sorted(DISPATCH_CONTRACT_KEYS)}"
    )
    assert contract.get("orchestrator") == "prototype-rca-orchestrator", (
        "T2: workflow_dispatch_contract.orchestrator must target "
        "prototype-rca-orchestrator"
    )
    for key in ("inputs", "expectations", "outputs", "non_goals"):
        value = contract.get(key)
        assert isinstance(value, list) and value, (
            f"T2: workflow_dispatch_contract.{key} must be a non-empty list"
        )
        assert all(isinstance(item, str) and item.strip() for item in value), (
            f"T2: workflow_dispatch_contract.{key} must contain non-empty strings"
        )
    assert "workflow_aliases" not in frontmatter, (
        "T2: workflow_aliases must be absent"
    )


def test_workflow_h1_h2_shape_t3():
    body = _workflow_body("T3")
    assert _h1_headings(body)[:1] == ["# RCA Prototype Workflow"], (
        "T3: workflow H1 must be exactly '# RCA Prototype Workflow'"
    )
    headings = set(_h2_headings(body))
    assert REQUIRED_WORKFLOW_H2.issubset(headings), (
        "T3: workflow H2 headings must include the required RCA prototype subset; "
        f"missing {sorted(REQUIRED_WORKFLOW_H2 - headings)}"
    )


def test_workflow_names_two_trigger_types_t4():
    text = _workflow_text("T4")
    _contains_tokens(text, ("trigger_type", "test", "qa"), "T4")
    _contains_regex(
        text,
        r"failing[- ]behavior[- ]test|failed[- ]behavior[- ]test|behavior test",
        "T4: workflow must name the failing behavior test trigger",
    )
    _contains_regex(
        text,
        r"qa.{0,80}(observation|screenshot)|(observation|screenshot).{0,80}qa",
        "T4: workflow must name the QA observation/screenshot trigger",
    )


def test_workflow_coarse_signal_is_reproduction_t5():
    text = _workflow_text("T5")
    _contains_regex(
        text,
        (
            r"(failing (?:behavior )?test|qa observation|observation/screenshot|"
            r"screenshot).{0,160}\bis the reproduction\b|"
            r"\bis the reproduction\b.{0,160}(failing (?:behavior )?test|"
            r"qa observation|observation/screenshot|screenshot)"
        ),
        "T5: workflow must state the failing test or QA observation/screenshot "
        "is the reproduction",
    )
    _contains_regex(
        text,
        (
            r"(individualized|individual).{0,80}reproduction[- ]test.{0,80}"
            r"(out of scope|not|do not|must not)|"
            r"reproduction[- ]test creation.{0,80}(out of scope|not|do not|must not)"
        ),
        "T5: workflow must state individualized reproduction-test creation is out of scope",
    )


def test_workflow_light_vs_full_boundary_t6():
    text = _workflow_text("T6")
    _contains_regex(
        text,
        r"(?:~/ai|/home/nes/ai)/workflows/rca\.md",
        "T6: workflow must reference the full RCA workflow path",
    )
    _contains_regex(
        text,
        r"\b(full|production)\b.{0,60}\brca\b|\brca\b.{0,60}\b(full|production)\b",
        "T6: workflow must call rca.md the full or production RCA",
    )
    _contains_regex(
        text,
        r"(does not|must not|not)\s+replace|replace\s+it",
        "T6: workflow must state the light workflow does not replace full RCA",
    )


def test_workflow_phase_1_root_cause_contract_t7():
    phase = _section_after_h2(_workflow_body("T7"), "## Phase 1 - Root Cause", "T7")
    _contains_regex(
        phase,
        r"(?:~/ai|/home/nes/ai)/agents/behavior-investigator\.md|behavior-investigator",
        "T7: Phase 1 must reference behavior-investigator",
    )
    _contains_tokens(
        phase,
        ("root cause", "failure surface", "evidence trail", "${planning_dir}/rca/<failure-id>.md"),
        "T7",
    )
    assert "propose a fix" not in phase.casefold(), (
        "T7: Phase 1 must not include the forbidden fix-proposal phrase"
    )


def test_workflow_phase_2_fix_contract_t8():
    phase = _section_after_h2(
        _workflow_body("T8"),
        "## Phase 2 - Fix And Targeted Re-Run",
        "T8",
    )
    _contains_regex(
        phase,
        r"inline.{0,80}gpt-high.{0,80}fix|gpt-high.{0,80}fix dispatch|fix agent",
        "T8: Phase 2 must name an inline gpt-high fix dispatch or fix agent",
    )
    _contains_regex(
        phase,
        r"read.{0,80}(rca artifact|rca report|root-cause artifact)",
        "T8: Phase 2 must state that the fix dispatch reads the RCA artifact",
    )
    _contains_regex(
        phase,
        r"(apply|applying|applies).{0,80}(code changes|changes).{0,80}\$\{worktree_path\}",
        "T8: Phase 2 must apply code changes in ${worktree_path}",
    )
    assert "${planning_dir}/rca/<failure-id>-fixed.md" in phase, (
        "T8: Phase 2 must name the fixed artifact path"
    )
    _contains_regex(
        phase,
        r"only.{0,80}targeted.{0,40}pass|targeted.{0,40}pass.{0,80}only",
        "T8: fixed artifact must be written only on targeted pass",
    )


def test_workflow_targeted_rerun_only_t9():
    text = _workflow_text("T9")
    _contains_regex(
        text,
        r"test trigger.{0,120}(re-runs|reruns|runs).{0,40}only.{0,80}"
        r"(trigger_command|pytest <node-id>)",
        "T9: test trigger must re-run only trigger_command or pytest <node-id>",
    )
    _contains_regex(
        text,
        r"qa trigger.{0,120}(re-walks|rewalks|walks).{0,60}only.{0,80}"
        r"(one|single).{0,40}use case",
        "T9: QA trigger must re-walk only one use case",
    )
    _contains_regex(
        text,
        r"full regression.{0,120}(upstream caller|caller|upstream).{0,80}"
        r"(responsibility|owns|owned)",
        "T9: full regression must remain the upstream caller responsibility",
    )


def test_workflow_loop_cap_and_termination_t10():
    text = _workflow_text("T10")
    _contains_regex(
        text,
        r"default.{0,40}hard_cap\s*=?\s*5|hard_cap\s*[:=]\s*5|hard cap.{0,40}5",
        "T10: workflow must set default hard_cap to 5",
    )
    assert "${planning_dir}/rca/<failure-id>-iter<N>.md" in text, (
        "T10: workflow must name per-iteration RCA artifacts"
    )
    for state in ("fixed", "cap-hit", "blocked", "needs-input"):
        assert state in text.casefold(), f"T10: workflow must name stop state {state}"


def test_handback_return_shape_t11():
    combined = ""
    if WORKFLOW_MD.exists():
        combined += WORKFLOW_MD.read_text(encoding="utf-8")
    if OPERATOR_MD.exists():
        combined += "\n" + OPERATOR_MD.read_text(encoding="utf-8")
    _contains_tokens(combined.casefold(), HANDback_TOKENS, "T11")


def test_operator_file_exists_t12():
    assert OPERATOR_MD.is_file(), f"T12: operator file must exist at {OPERATOR_MD}"
    assert OPERATOR_MD.stat().st_size > 0, "T12: operator file must be non-empty"


def test_operator_frontmatter_contract_t13():
    frontmatter, _body = _frontmatter_and_body(_operator_text("T13"), "T13")
    assert set(frontmatter) == OPERATOR_FRONTMATTER_KEYS, (
        "T13: operator frontmatter keys must be exactly "
        f"{sorted(OPERATOR_FRONTMATTER_KEYS)}"
    )
    assert frontmatter["description"], "T13: operator description must be non-empty"
    assert frontmatter["model"] == "claude-opus", (
        "T13: operator model must be claude-opus"
    )
    assert frontmatter["output_format"] == "", (
        "T13: operator output_format must be the empty string"
    )
    roles = _read_required_file(MODELS_ROLES_MD, "T13")
    assert re.search(r"(?m)(^|[^A-Za-z0-9_-])claude-opus([^A-Za-z0-9_-]|$)", roles), (
        "T13: claude-opus must resolve in models/roles.md"
    )


def test_operator_body_sections_t14():
    _frontmatter, body = _frontmatter_and_body(_operator_text("T14"), "T14")
    assert _h1_headings(body)[:1] == ["# Prototype RCA Orchestrator"], (
        "T14: operator H1 must be '# Prototype RCA Orchestrator'"
    )
    headings = set(_h2_headings(body))
    assert REQUIRED_OPERATOR_H2.issubset(headings), (
        "T14: operator H2 headings must include the required RCA prototype subset; "
        f"missing {sorted(REQUIRED_OPERATOR_H2 - headings)}"
    )


def test_operator_trigger_normalization_t15():
    _frontmatter, body = _frontmatter_and_body(_operator_text("T15"), "T15")
    inputs_and_procedure = (
        _section_after_h2(body, "## Required Inputs", "T15")
        + "\n"
        + _section_after_h2(body, "## Procedure", "T15")
    )
    _contains_tokens(inputs_and_procedure, TRIGGER_ENVELOPE_TOKENS, "T15")


def test_operator_phase_1_procedure_t16():
    _frontmatter, body = _frontmatter_and_body(_operator_text("T16"), "T16")
    procedure = _section_after_h2(body, "## Procedure", "T16")
    _contains_tokens(
        procedure,
        (
            "behavior-investigator",
            "target",
            "repo_root",
            "planning_root",
            "context",
            "${planning_dir}/rca/<failure-id>-iter<N>.md",
        ),
        "T16",
    )
    _contains_regex(
        procedure,
        r"on[- ]disk|verify.{0,80}(exists|path|artifact)|exists.{0,80}on disk",
        "T16: Phase 1 procedure must verify the RCA artifact on disk",
    )


def test_operator_phase_2_procedure_t17():
    _frontmatter, body = _frontmatter_and_body(_operator_text("T17"), "T17")
    procedure = _section_after_h2(body, "## Procedure", "T17")
    _contains_regex(
        procedure,
        r"inline.{0,80}gpt-high.{0,80}fix|gpt-high.{0,80}fix dispatch|fix agent",
        "T17: Phase 2 procedure must name the inline gpt-high fix dispatch",
    )
    assert "${scratch_dir}/prompts/" in procedure, (
        "T17: Phase 2 procedure must name the fix prompt path under ${scratch_dir}/prompts/"
    )
    _contains_regex(
        procedure,
        r"narrow fix|narrowest.{0,60}fix|avoid.{0,40}broad refactor|no broad refactor",
        "T17: Phase 2 procedure must require narrow-fix or anti-broad-refactor language",
    )
    _contains_regex(
        procedure,
        r"targeted.{0,60}test command|trigger_command|qa.{0,40}handback|hand back.{0,80}qa",
        "T17: Phase 2 procedure must name targeted test command or QA handback",
    )
    assert "${planning_dir}/rca/<failure-id>-fixed.md" in procedure, (
        "T17: Phase 2 procedure must name the fixed artifact path"
    )


def test_operator_loop_control_t18():
    _frontmatter, body = _frontmatter_and_body(_operator_text("T18"), "T18")
    loop_text = (
        _section_after_h2(body, "## Procedure", "T18")
        + "\n"
        + _section_after_h2(body, "## Stop Conditions", "T18")
    )
    _contains_regex(
        loop_text,
        r"default.{0,40}hard_cap\s*=?\s*5|hard_cap\s*[:=]\s*5|hard cap.{0,40}5",
        "T18: operator must name default hard_cap=5",
    )
    _contains_regex(
        loop_text,
        r"iteration.{0,60}(increment|increase|advance|next)",
        "T18: operator must name iteration increment behavior",
    )
    _contains_regex(
        loop_text,
        r"(pass|success|fixed).{0,80}(stop|terminate|return)",
        "T18: operator must state pass/success terminates the loop",
    )
    _contains_regex(
        loop_text,
        r"(still[- ]failing|still failing|targeted failure|continues to fail).{0,120}"
        r"Phase 1|Phase 1.{0,120}(still[- ]failing|continues to fail)",
        "T18: operator must state still-failing triggers loop to Phase 1",
    )
    _contains_regex(
        loop_text,
        r"cap-hit.{0,120}(human review|NEEDS_INPUT)|human review.{0,120}cap-hit",
        "T18: cap-hit must emit human review or NEEDS_INPUT",
    )
    assert "BLOCKED" in loop_text, "T18: operator must name BLOCKED stop state"
    assert "NEEDS_INPUT" in loop_text, (
        "T18: operator must name NEEDS_INPUT stop state"
    )


def test_agents_md_routing_row_t19():
    row = _routing_row(
        _read_required_file(AGENTS_MD, "T19"),
        "prototype-rca-orchestrator",
        "T19",
    )
    assert re.search(
        r"File:\s+\[~/ai/agents/prototype-rca-orchestrator\.md\]"
        r"\(agents/prototype-rca-orchestrator\.md\)",
        row,
    ), "T19: AGENTS routing row must have the expected File: target under agents/"
    for input_name in AGENTS_ROUTING_INPUTS:
        assert re.search(rf"`{re.escape(input_name)}\??`", row), (
            f"T19: AGENTS routing row must name input {input_name}"
        )
    assert re.search(r"Model:\s*`claude-opus`", row), (
        "T19: AGENTS routing row must declare Model: `claude-opus`"
    )


def test_agents_md_topology_link_t20():
    agents_text = _read_required_file(AGENTS_MD, "T20")
    topology = _section_after_h2(agents_text, "## Workflow Topologies", "T20")
    assert re.search(r"\]\(workflows/rca-prototype\.md\)", topology), (
        "T20: AGENTS Workflow Topologies must link to workflows/rca-prototype.md"
    )


def test_workflow_index_entry_t21():
    index = json.loads(_read_required_file(INDEX_JSON, "T21"))
    workflows = index.get("workflows")
    assert isinstance(workflows, dict), "T21: workflow index must contain workflows mapping"
    entry = workflows.get("rca-prototype")
    assert isinstance(entry, dict), "T21: workflow index must contain rca-prototype entry"
    assert entry.get("path") == "workflows/rca-prototype.md", (
        "T21: rca-prototype index entry path must be workflows/rca-prototype.md"
    )
    entry_id = entry.get("id", entry.get("workflow", {}).get("id"))
    assert entry_id == "rca-prototype", (
        "T21: rca-prototype index entry id must be rca-prototype"
    )


def test_anti_framing_absence_t22():
    documents = {
        "workflow": _workflow_body("T22"),
        "operator": _frontmatter_and_body(_operator_text("T22"), "T22")[1],
    }
    for label, text in documents.items():
        for title, section in _h2_sections(text).items():
            if title in ANTI_FRAMING_ALLOWED_SECTIONS:
                continue
            lower = section.casefold()
            for phrase in ANTI_FRAMING_PHRASES:
                assert phrase not in lower, (
                    f"T22: {label} section ## {title} must not use forbidden "
                    f"anti-framing phrase {phrase!r} outside allowed boundary sections"
                )
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", section):
                sentence_lower = sentence.casefold()
                if not sentence_lower.strip():
                    continue
                for token in RUNTIME_CEREMONY_TOKENS:
                    if token not in sentence_lower:
                        continue
                    assert any(term in sentence_lower for term in NEGATION_TERMS), (
                        f"T22: {label} section ## {title} appears to instruct runtime "
                        f"{token!r} work instead of forbidding it: {sentence.strip()}"
                    )
                if re.search(
                    r"(create|write|add|author).{0,80}"
                    r"(individualized|individual).{0,80}reproduction[- ]test",
                    sentence_lower,
                ):
                    assert any(term in sentence_lower for term in NEGATION_TERMS), (
                        f"T22: {label} section ## {title} appears to instruct "
                        "individualized reproduction-test creation"
                    )


def test_read_only_adjacent_surfaces_t23():
    anti_scope = _section_after_h2(_workflow_body("T23"), "## Anti-Scope", "T23")
    for pattern in ANTI_SCOPE_PATHS:
        _contains_regex(
            anti_scope,
            pattern,
            f"T23: Anti-Scope must name adjacent read-only surface matching {pattern}",
        )
    _contains_regex(
        anti_scope,
        r"not (modified|redefined|edited)|do not (modify|redefine|edit)|must not "
        r"(modify|redefine|edit)|remain(?:s)? (read-only|unchanged|unmodified)",
        "T23: Anti-Scope must state adjacent surfaces are not modified or redefined",
    )
