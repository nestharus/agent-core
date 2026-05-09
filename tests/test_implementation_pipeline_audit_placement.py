import re
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = repo_root / "workflows" / "implementation-pipeline.md"
ORCHESTRATOR_PATH = repo_root / "agents" / "implementation-pipeline-orchestrator.md"

PHASE_4_HEADING = "## Phase 4 - Risk Gates (required; parallel)"
PHASE_4_5_HEADING = "## Phase 4.5 - Alignment (optional; governance layer only)"
PHASE_6_HEADING = "## Phase 6 - Implementation (required; test/code separation)"
PHASE_7_HEADING = "## Phase 7 - CodeRabbit Loop"
PHASE_8_HEADING = "## Phase 8 - Post-CodeRabbit Review Gates"
PHASE_8_5_HEADING = "## Phase 8.5 - Human Local Review Gate (tickets-first variant only)"
STEP_6B_HEADING = "### Step 6b - Encode tests first"
STEP_6C_HEADING = "### Step 6c - Write code"

ORCH_PHASE_6_HEADING = (
    "### Phase 6 — Implementation (test/code separation) + Process-tree Audit #2"
)
ORCH_STEP_6B_HEADING = "#### Step 6b — Encode tests first"
ORCH_STEP_6C_HEADING = "#### Step 6c — Write code"
ORCH_PROCESS_TREE_AUDIT_2_HEADING = "#### Process-tree audit #2"

SURFACE_1_HEADING = "#### Phase 6 prototype risk review"
SURFACE_2_HEADING = "#### Phase 6 tests/contracts alignment review"
SURFACE_3_HEADING = "#### Per-component code-quality auditor fanout"

SURFACE_1_TOKENS = (
    "Phase 6 prototype risk review",
    "risk-assessor",
    "${planning_dir}/risk/${wu_lower}-prototype-risk.md",
    "LOW",
    "MEDIUM",
    "HIGH",
    "agents -m gpt-high -p ${worktree_path} -f ${prompt}",
    "passing level prototype",
    "actor=implementation-pipeline-orchestrator",
    "prototype_risk_review_missing_or_blocking",
    "${scratch_dir}/questions/q-<uuidv4>.question.json",
    "NEEDS_INPUT:<absolute_question_artifact_path>",
    "must not synthesize or repair the prototype-risk artifact inline",
    "downstream derivation trigger / PrototypeSwapRecord production or consumption / Phase 7 advance",
)

SURFACE_2_TOKENS = (
    "Phase 6 tests/contracts alignment review",
    "${planning_dir}/alignment/${wu_lower}-tests-contracts.md",
    "ALIGNED",
    "MISALIGNED",
    "NEEDS_REVISION",
    "${scratch_dir}/phase6/step6b-output-index.md",
    "mkdir -p ${planning_dir}/alignment",
    "before composing or dispatching Step 6c",
    "agents -m gpt-high -p ${worktree_path} -f ${prompt}",
    "actor=implementation-pipeline-orchestrator",
    "tests_contracts_alignment_missing_or_blocking",
    "${scratch_dir}/questions/q-<uuidv4>.question.json",
    "NEEDS_INPUT:<absolute_question_artifact_path>",
    "must not synthesize or repair the alignment artifact inline",
    "Step 6c prompt composition / Step 6c dispatch",
)

SURFACE_3_TOKENS = (
    "Per-component code-quality auditor fanout",
    "~/ai/workflows/code-quality.md",
    "cohesion-auditor",
    "function-classification-auditor",
    "push-pull-auditor",
    "mkdir -p ${planning_dir}/code-quality/${wu_lower}-${component_slug}/reports",
    "${planning_dir}/code-quality/${wu_lower}-${component_slug}/dispatch-manifest.md",
    "${planning_dir}/code-quality/${wu_lower}-${component_slug}/reports/cohesion-auditor.md",
    "${planning_dir}/code-quality/${wu_lower}-${component_slug}/reports/function-classification-auditor.md",
    "${planning_dir}/code-quality/${wu_lower}-${component_slug}/reports/push-pull-auditor.md",
    "${planning_dir}/code-quality/${wu_lower}-${component_slug}/aggregate-code-quality.md",
    "LOW",
    "MEDIUM",
    "HIGH",
    "NEEDS_INPUT",
    "BLOCKED",
    "agents -m gpt-high -p ${worktree_path} -f ${prompt}",
    "actor=implementation-pipeline-orchestrator",
    "per_component_code_quality_missing_or_blocking",
    "${scratch_dir}/questions/q-<uuidv4>.question.json",
    "NEEDS_INPUT:<absolute_question_artifact_path>",
    "does not replace Phase 7 CodeRabbit or Phase 8 PR-review aggregate gates",
    "must not synthesize missing child reports or aggregate findings inline",
    "component closure into aggregate diff consumed by Phase 7 CodeRabbit",
)

_WORKFLOW_TEXT = None
_ORCHESTRATOR_TEXT = None


def _load_workflow_text():
    global _WORKFLOW_TEXT
    if _WORKFLOW_TEXT is None:
        assert WORKFLOW_PATH.exists(), f"workflow file not found: {WORKFLOW_PATH}"
        _WORKFLOW_TEXT = WORKFLOW_PATH.read_text(encoding="utf-8")
    return _WORKFLOW_TEXT


def _load_orchestrator_text():
    global _ORCHESTRATOR_TEXT
    if _ORCHESTRATOR_TEXT is None:
        assert ORCHESTRATOR_PATH.exists(), (
            f"orchestrator file not found: {ORCHESTRATOR_PATH}"
        )
        _ORCHESTRATOR_TEXT = ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    return _ORCHESTRATOR_TEXT


def _section(text, start_heading, end_heading=None):
    assert start_heading in text, f"heading not found: {start_heading!r}"
    start = text.index(start_heading)
    if end_heading is None:
        end = len(text)
    else:
        text_after_start = text[start + len(start_heading) :]
        assert end_heading in text_after_start, (
            f"end heading not found after start: {end_heading!r}"
        )
        end = text.index(end_heading, start + len(start_heading))
    return text[start:end]


def _section_text(md: str, heading: str) -> str:
    if heading.startswith("#"):
        pattern = rf"^{re.escape(heading)}\s*$"
        level = len(heading) - len(heading.lstrip("#"))
    else:
        pattern = rf"^(?P<hashes>#+)\s+{re.escape(heading)}\s*$"
        level = None

    match = re.search(pattern, md, flags=re.MULTILINE)
    assert match is not None, f"heading not found: {heading!r}"
    if level is None:
        level = len(match.group("hashes"))

    next_heading = re.search(
        rf"^#{{1,{level}}}\s+",
        md[match.end() :],
        flags=re.MULTILINE,
    )
    if next_heading is None:
        return md[match.start() :]
    return md[match.start() : match.end() + next_heading.start()]


def _phase_6_section(text):
    return _section(text, PHASE_6_HEADING, PHASE_7_HEADING)


def _orchestrator_phase_6_section(text):
    return _section_text(text, ORCH_PHASE_6_HEADING)


def _step_6b_to_6c_boundary(text):
    return _section(_phase_6_section(text), STEP_6B_HEADING, STEP_6C_HEADING)


def _step_6c_section(text):
    return _section(_phase_6_section(text), STEP_6C_HEADING)


def _phase_4_section(text):
    return _section(text, PHASE_4_HEADING, PHASE_4_5_HEADING)


def _phase_7_section(text):
    return _section(text, PHASE_7_HEADING, PHASE_8_HEADING)


def _phase_8_section(text):
    return _section(text, PHASE_8_HEADING, PHASE_8_5_HEADING)


def _line_window_after_token(text, token, *, lines_after, lines_before=0):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if token in line:
            start = max(0, index - lines_before)
            end = min(len(lines), index + lines_after + 1)
            return "\n".join(lines[start:end])
    raise AssertionError(f"missing anchor token: {token!r}")


def _between(text, start_token, end_token):
    assert start_token in text, f"missing start token: {start_token!r}"
    start = text.index(start_token)
    assert end_token in text[start:], f"missing end token after start: {end_token!r}"
    end = text.index(end_token, start + len(start_token))
    return text[start:end]


def _assert_contains_all(text, tokens, *, where):
    missing = [token for token in tokens if token not in text]
    assert missing == [], f"{where} missing required tokens: {missing}"


def _assert_regex(text, pattern, *, where):
    assert re.search(pattern, text), f"{where} missing pattern: {pattern}"


def _assert_not_regex(text, pattern, *, where):
    assert not re.search(pattern, text), f"{where} matched forbidden pattern: {pattern}"


def _assert_order(text, ordered_tokens, *, where):
    cursor = -1
    for token in ordered_tokens:
        index = text.find(token, cursor + 1)
        assert index != -1, f"{where} missing ordered token after {cursor}: {token!r}"
        cursor = index


def _operator_block(heading):
    return _section_text(_load_orchestrator_text(), heading)


def _workflow_audit_rule_window(lead_phrase):
    return _line_window_after_token(
        _phase_6_section(_load_workflow_text()),
        lead_phrase,
        lines_after=4,
    )


def test_phase6_declares_prototype_risk_review_with_risk_assessor():
    # Risk: workflow declares only proposal-time risk and misses prototype-risk audit. Level: unit / structural. Source: proposal T1, contract T1.
    boundary = _step_6b_to_6c_boundary(_load_workflow_text())
    review_rule = _line_window_after_token(
        boundary,
        "Phase 6 prototype risk review",
        lines_after=25,
    )

    _assert_contains_all(
        review_rule,
        (
            "Phase 6 prototype risk review",
            "risk-assessor",
            "passing level prototype",
            "level behavior tests",
            "${planning_dir}/risk/${wu_lower}-prototype-risk.md",
            "LOW",
            "MEDIUM",
            "HIGH",
            "before Phase 7",
            "PrototypeSwapRecord",
        ),
        where="Phase 6 prototype risk review rule",
    )
    _assert_regex(
        review_rule,
        r"(?is)does\s+NOT\s+redefine|does\s+not\s+redefine",
        where="risk-assessor output-contract non-redesign clause",
    )
    _assert_contains_all(
        review_rule,
        ("~/ai/workflows/build-prototype.md", "dossier/risk-profile.md"),
        where="exploratory prototype dossier differentiation",
    )
    assert STEP_6C_HEADING not in boundary

    block = _operator_block(SURFACE_1_HEADING)
    phase_6 = _orchestrator_phase_6_section(_load_orchestrator_text())
    _assert_contains_all(block, SURFACE_1_TOKENS, where="operator Surface 1 block")
    _assert_order(
        phase_6,
        (
            ORCH_STEP_6C_HEADING,
            SURFACE_1_HEADING,
            "Detect the post-prototype internal contract derivation trigger",
            ORCH_PROCESS_TREE_AUDIT_2_HEADING,
        ),
        where="operator Surface 1 placement",
    )


def test_phase6_declares_tests_contracts_alignment_before_step6c():
    # Risk: tests and contracts can guide implementation without a right-problem alignment check. Level: unit / structural. Source: proposal T2, contract T2.
    boundary = _step_6b_to_6c_boundary(_load_workflow_text())
    review_rule = _line_window_after_token(
        boundary,
        "Phase 6 tests/contracts alignment review",
        lines_after=25,
    )

    _assert_contains_all(
        review_rule,
        (
            "Phase 6 tests/contracts alignment review",
            "Step 6a contract",
            "Step 6b tests",
            "${scratch_dir}/phase6/step6b-output-index.md",
            "${planning_dir}/alignment/${wu_lower}-tests-contracts.md",
            "ALIGNED",
            "MISALIGNED",
            "NEEDS_REVISION",
            "before Step 6c",
            "approved proposal test-intent track",
        ),
        where="Phase 6 tests/contracts alignment review rule",
    )
    assert STEP_6C_HEADING not in boundary

    block = _operator_block(SURFACE_2_HEADING)
    phase_6 = _orchestrator_phase_6_section(_load_orchestrator_text())
    _assert_contains_all(block, SURFACE_2_TOKENS, where="operator Surface 2 block")
    _assert_order(
        phase_6,
        (ORCH_STEP_6B_HEADING, SURFACE_2_HEADING, ORCH_STEP_6C_HEADING),
        where="operator Surface 2 placement",
    )


def test_step6c_declares_per_component_code_quality_fanout_before_derivation():
    # Risk: code-quality remains aggregate-only through Phase 7 and misses local component closure. Level: unit / structural. Source: proposal T3, contract T3.
    step_6c = _step_6c_section(_load_workflow_text())
    placement_region = _between(
        step_6c,
        "Step 6c log output must echo",
        "Post-prototype internal contract derivation",
    )
    fanout_rule = _line_window_after_token(
        placement_region,
        "per-component code-quality auditor fanout",
        lines_after=30,
    )

    _assert_contains_all(
        fanout_rule,
        (
            "per-component code-quality auditor fanout",
            "individual component",
            "component_slug",
            "cohesion-auditor",
            "function-classification-auditor",
            "push-pull-auditor",
            "${planning_dir}/code-quality/${wu_lower}-${component_slug}/dispatch-manifest.md",
            "${planning_dir}/code-quality/${wu_lower}-${component_slug}/reports/cohesion-auditor.md",
            "${planning_dir}/code-quality/${wu_lower}-${component_slug}/reports/function-classification-auditor.md",
            "${planning_dir}/code-quality/${wu_lower}-${component_slug}/reports/push-pull-auditor.md",
            "${planning_dir}/code-quality/${wu_lower}-${component_slug}/aggregate-code-quality.md",
            "LOW",
            "MEDIUM",
            "HIGH",
            "NEEDS_INPUT",
            "BLOCKED",
            "Phase 7 CodeRabbit",
            "~/ai/workflows/code-quality.md",
            "Phase 8 PR-review",
        ),
        where="per-component code-quality auditor fanout rule",
    )
    _assert_regex(
        fanout_rule,
        r"(?is)before.{0,160}Phase 7 CodeRabbit",
        where="per-component fanout before aggregate CodeRabbit gate",
    )
    _assert_regex(
        fanout_rule,
        r"(?is)(NOT|not).{0,160}replac",
        where="per-component fanout does not replace aggregate gates",
    )

    block = _operator_block(SURFACE_3_HEADING)
    phase_6 = _orchestrator_phase_6_section(_load_orchestrator_text())
    _assert_contains_all(block, SURFACE_3_TOKENS, where="operator Surface 3 block")
    _assert_order(
        phase_6,
        (ORCH_STEP_6C_HEADING, SURFACE_3_HEADING, ORCH_PROCESS_TREE_AUDIT_2_HEADING),
        where="operator Surface 3 placement",
    )


def test_phase4_risk_gate_invocation_is_preserved():
    # Risk: adding prototype risk accidentally weakens proposal-time risk review. Level: unit / structural. Source: proposal T4, contract T4.
    phase_4 = _phase_4_section(_load_workflow_text())
    workflow = _load_workflow_text()

    _assert_contains_all(
        phase_4,
        (
            "Risk Gates (required; parallel)",
            "risk/NN-audit.md",
            "risk/NN-scope.md",
            "risk/NN-shortcut.md",
            "risk/NN-supported-surface.md",
            "`audit risk`",
            "`scope risk`",
            "`shortcut risk`",
            "`supported-surface risk`",
            "all four reports must return `LOW`",
        ),
        where="Phase 4 four risk gates",
    )
    _assert_contains_all(
        workflow,
        ("audit", "scope", "shortcut", "supported-surface"),
        where="Phase 4 / Phase 8 gate names",
    )


def test_phase7_coderabbit_and_phase8_review_gates_are_preserved():
    # Risk: per-component audit is mistaken as a replacement for aggregate review. Level: unit / structural. Source: proposal T5, contract T5.
    phase_7 = _phase_7_section(_load_workflow_text())
    phase_8 = _phase_8_section(_load_workflow_text())

    _assert_contains_all(
        phase_7,
        ("coderabbit-loop.md", "actual diff"),
        where="Phase 7 CodeRabbit aggregate review",
    )
    _assert_contains_all(
        phase_8,
        ("test-audit", "multi-concern", "justification"),
        where="Phase 8 PR-review gates",
    )
    _assert_regex(
        phase_8,
        r"commit[- ]hygiene",
        where="Phase 8 commit-hygiene gate",
    )


def test_audit_placement_scope_remains_structural_only():
    # Risk: test imports runtime orchestrator modules or creates deferred runtime behavior in this WU. Level: unit / structural. Source: proposal T7, contract T6.
    source = Path(__file__).read_text(encoding="utf-8")
    workflow = _load_workflow_text()
    phase_6 = _phase_6_section(workflow)
    import_lines = [
        line
        for line in source.splitlines()
        if re.match(r"^\s*(?:import|from)\s+", line)
    ]
    allowed_imports = {"import re", "from pathlib import Path"}

    assert set(import_lines) <= allowed_imports
    for line in import_lines:
        _assert_not_regex(
            line,
            r"\b(?:agents\.|clients\.|runtime|orchestrator)\b",
            where="runtime/orchestrator import guard",
        )

    assert "### Step 6d" not in phase_6
    assert ORCHESTRATOR_PATH.name == "implementation-pipeline-orchestrator.md"
    test_phase4_risk_gate_invocation_is_preserved()
    test_phase7_coderabbit_and_phase8_review_gates_are_preserved()
    _assert_not_regex(
        workflow,
        r"~/ai/(?:agents|workflows)/[^`\s)]*NES-281[^`\s)]*",
        where="NES-281-specific new operator or workflow path",
    )


def test_workflow_audit_position_rules_reference_operator_substeps_without_deferral():
    # Risk: workflow text preserves the round-1 follow-up-ticket fiction instead of pointing to the operator-file sub-steps. Level: unit / structural. Source: proposal T7.
    for lead_phrase in (
        "Phase 6 prototype risk review",
        "Phase 6 tests/contracts alignment review",
        "per-component code-quality auditor fanout",
    ):
        nearby = _workflow_audit_rule_window(lead_phrase)
        _assert_contains_all(
            nearby,
            (lead_phrase, "agents/implementation-pipeline-orchestrator.md"),
            where=f"{lead_phrase} operator-file reference",
        )
        _assert_not_regex(
            nearby,
            r"(?is)tracked in a separate ticket|Orchestrator-runtime enforcement|structural pytest plus operator review only",
            where=f"{lead_phrase} no deferral language",
        )


def test_operator_phase6_prototype_risk_review_dispatches_and_blocks_on_missing_or_high():
    block = _operator_block(SURFACE_1_HEADING)

    _assert_contains_all(block, SURFACE_1_TOKENS, where="operator Surface 1 block")
    _assert_regex(
        block,
        r"(?is)1\..{0,800}2\..{0,800}3\..{0,800}4\..{0,800}5\..{0,1200}6\.",
        where="operator Surface 1 numbered gate shape",
    )
    _assert_regex(
        block,
        r"(?is)HIGH.{0,500}(blocking|refus)",
        where="operator Surface 1 high-risk block",
    )


def test_operator_phase6_tests_contracts_alignment_runs_before_step6c():
    block = _operator_block(SURFACE_2_HEADING)
    phase_6 = _orchestrator_phase_6_section(_load_orchestrator_text())

    _assert_contains_all(block, SURFACE_2_TOKENS, where="operator Surface 2 block")
    _assert_order(
        phase_6,
        (ORCH_STEP_6B_HEADING, SURFACE_2_HEADING, ORCH_STEP_6C_HEADING),
        where="operator Surface 2 before Step 6c",
    )
    _assert_regex(
        block,
        r"(?is)(MISALIGNED|NEEDS_REVISION).{0,700}(refuse|blocking|halt)",
        where="operator Surface 2 blocking alignment verdicts",
    )


def test_operator_phase6_per_component_code_quality_fanout_blocks_component_closure():
    block = _operator_block(SURFACE_3_HEADING)
    phase_6 = _orchestrator_phase_6_section(_load_orchestrator_text())

    _assert_contains_all(block, SURFACE_3_TOKENS, where="operator Surface 3 block")
    _assert_order(
        phase_6,
        (SURFACE_1_HEADING, SURFACE_3_HEADING, ORCH_PROCESS_TREE_AUDIT_2_HEADING),
        where="operator Surface 3 after Surface 1 before process-tree audit",
    )
    _assert_regex(
        block,
        r"(?is)(HIGH|NEEDS_INPUT|BLOCKED).{0,700}(refuse|blocking|halt)",
        where="operator Surface 3 blocking code-quality verdicts",
    )


def test_operator_process_tree_audit_2_includes_acr6_gate_evidence():
    # Risk: the new Phase 6 audit-position gates can run procedurally but escape the Phase 6 process-tree review. Level: unit / structural. Source: CodeRabbit R2-F01.
    block = _operator_block(ORCH_PROCESS_TREE_AUDIT_2_HEADING)

    _assert_contains_all(
        block,
        (
            "Phase 6 tests/contracts alignment review",
            "${planning_dir}/alignment/${wu_lower}-tests-contracts.md",
            "ALIGNED",
            "Phase 6 prototype risk review",
            "${planning_dir}/risk/${wu_lower}-prototype-risk.md",
            "PrototypeSwapRecord",
            "per-component code-quality auditor fanout",
            "${planning_dir}/code-quality/${wu_lower}-${component_slug}/...",
            "Phase 7 CodeRabbit",
            "${scratch_dir}/phase6/step6c-multi-layer-derivation-check.md",
            "${scratch_dir}/phase6/post-prototype-derivation-status.md",
        ),
        where="operator Process-tree audit #2 ACR-6 gate evidence",
    )


def test_operator_audit_position_substeps_preserve_phase7_and_phase8_aggregate_gates():
    orchestrator = _load_orchestrator_text()

    _assert_regex(
        orchestrator,
        r"(?is)Phase 7.{0,5000}CodeRabbit",
        where="operator Phase 7 CodeRabbit gate",
    )
    _assert_regex(
        orchestrator,
        r"(?is)Phase 8.{0,8000}(test-audit|test audit).{0,8000}(multi-concern|multi concern).{0,8000}justification",
        where="operator Phase 8 aggregate review gates",
    )
    _assert_regex(
        orchestrator,
        r"(?is)Phase 8.{0,8000}commit[- ]hygiene",
        where="operator Phase 8 commit-hygiene gate",
    )
