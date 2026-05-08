import re
from pathlib import Path

from tools.workflow_index.generator import DISPATCH_CONTRACT_KEYS, parse_frontmatter


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / "workflows"


def _workflow_docs():
    return sorted(WORKFLOWS_DIR.glob("*.md"))


def _extract_body_section(text: str, h2: str) -> list[str]:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                lines = lines[index + 1 :]
                break
    heading = f"## {h2}"
    starts = [
        index for index, line in enumerate(lines) if line.strip() == heading
    ]
    assert len(starts) == 1, (
        f"expected exactly one {heading!r} section, found {len(starts)}"
    )
    start = starts[0] + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return lines[start:end]


def _parse_body_dispatch_surface(text: str) -> dict[str, str | list[str]]:
    lines = _extract_body_section(text, "Workflow Dispatch Surface")
    expected_labels = [
        ("### Orchestrator", "orchestrator"),
        ("### Inputs", "inputs"),
        ("### Expectations", "expectations"),
        ("### Outputs", "outputs"),
        ("### Non-goals", "non_goals"),
    ]
    headings = [
        (index, line.strip())
        for index, line in enumerate(lines)
        if line.strip().startswith("### ")
    ]
    actual_labels = [label for _, label in headings]
    expected_label_names = [label for label, _ in expected_labels]
    assert actual_labels == expected_label_names, (
        "Workflow Dispatch Surface labels must be exactly "
        f"{expected_label_names}, got {actual_labels}"
    )

    result: dict[str, str | list[str]] = {}
    for position, ((start, _), (_, key)) in enumerate(zip(headings, expected_labels)):
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        content = lines[start + 1 : end]
        values = [line.strip() for line in content if line.strip()]
        if key == "orchestrator":
            result[key] = "\n".join(values).strip()
            continue
        if values == ["- (none)"]:
            result[key] = []
            continue
        unexpected = [line for line in values if not line.startswith("- ")]
        assert unexpected == [], (
            f"Workflow Dispatch Surface {key} has non-bullet lines: {unexpected}"
        )
        result[key] = [line[2:].strip() for line in values]
    return result


def _extract_body_excluding_dispatch_surface(text: str) -> list[str]:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                lines = lines[index + 1 :]
                break
    body_lines = []
    in_fence = False
    in_dispatch_surface = False
    for line in lines:
        if in_dispatch_surface and line.startswith("## "):
            in_dispatch_surface = False
        if not in_dispatch_surface and line.strip() == "## Workflow Dispatch Surface":
            in_dispatch_surface = True
            continue
        if in_dispatch_surface:
            continue
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        body_lines.append(line)
    return body_lines


# future legitimate rewrites of contract-body prose must update this baseline at the same time
_T4_BASELINE: dict[str, list[str]] = {
    "audit.md": [
        "It does not duplicate the child auditor procedures. It preserves each source operator's contract and verdict vocabulary, then writes a durable audit bundle for a standalone caller or a future pipeline caller.",
        "Non-`LOW` aggregate or drift signal seeds proposer/revision work or blocks continuation according to the caller's mode. NES-223 documents this callable contract only; implementation-pipeline wiring is deferred to NES-224.",
    ],
    "build-prototype.md": [
        "Discipline applies here, retroactively. P3 is the prototype's analog of `~/ai/workflows/pr-review.md`: it makes the work consumable for downstream readers. The two workflows share `commit-hygiene-operator` but are otherwise distinct — PR-review's gates presuppose a proposal contract; P3's analog gates presuppose an answer.",
        "PR-review's justification verifies every change in the diff traces to ticket / proposal / contract / hookpoints. The prototype analog verifies every piece of code on the prototype branch traces to the answer.",
        "- A Layer 3 ai-roadmap decomposes a phase into Work Units. If a WU's contract / parallelizability / schema cannot be named without trying it, a prototype clarifies it. The dossier then drives the WU's eventual ticket and the WU's contract.",
    ],
    "coderabbit-loop.md": [
        "- **Run tests as needed, not as a loop ritual.** Validate when a finding changes behavior, contracts, or risk. The loop contract itself is amend-and-rerun, not \"new commit plus full push cycle.\"",
    ],
    "implementation-pipeline.md": [
        "Every Work Unit is an issue on the project's configured ticket system — currently either **JIRA** (Atlassian) or **Linear**, selected per project. The orchestrator dispatches the matching ticket operator at Phase 0 bootstrap (`~/ai/agents/jira-operator.md` for JIRA, `~/ai/agents/linear-operator.md` for Linear) to read (or first-draft) the ticket and renders the description into the per-WU `${scratch_dir}/ticket.md`. The ticket only needs a non-empty description; scope, code and test boundaries, acceptance criteria, and anti-scope are **derived** during Phase 2.5 (problem map), Phase 3 (proposal), and Step 6a (contract) — not pre-declared on the ticket. Pre-declared boundaries are brittle: real surface and scope are discovered during research, and forcing them upfront either creates inaccurate inputs the pipeline then trusts or blocks tickets that could otherwise proceed. There is **no** `plans/tickets/<phase>/<wu_id>.md` file in git for this pipeline. The orchestrator does not read from such a path. If a project's `AGENTS.md` still references the old git-resident ticket convention, treat the orchestrator's input contract (`~/ai/agents/implementation-pipeline-orchestrator.md`) as authoritative and update the project doc.",
        "**Ticket-system selection** is per-project: each project's `AGENTS.md` declares either `ticket_system: jira` (with `jira_url`, `jira_project`, `jira_account_email`) or `ticket_system: linear` (with `linear_team_key` and optional `linear_project_id`). The orchestrator's pluggability table (in `~/ai/agents/implementation-pipeline-orchestrator.md` § Ticket System Pluggability) is the authoritative input contract. JIRA descriptions and comments use ADF; Linear uses Markdown natively. The orchestrator routes operator dispatches accordingly, so phase procedures below speak generically about \"the ticket\" rather than calling out one system unless the difference matters.",
        "- Recursion edge: completed parent `Phase 6` component work may open a child recursion level that enters `level-open` and reuses the same Phase 6 contract/test/code path; the parent reaches `child-levels-open` only after candidate children have been considered for framing.",
        "A substantive revision is any change to audited target paths or target-manifest items; commit/head/ref, PR base/head/file list, runtime invocation UUID, runtime artifact bundle, or non-git content hash; proposal closure strategy; workflow/operator/runtime behavior contract; or corpus/reference path used to justify closure. Formatting-only or typo-only edits outside audited sections may be recorded as non-substantive with a reason. Uncertainty is substantive.",
        "Phase artifacts (`research/NN-*`, `proposals/NN-*`, `risk/NN-*`, contracts, audit history, scratch logs) are **planning** content. They live under the project's **planning directory**, not inside the working repository or its worktrees.",
        "- Rule: when deterministic reproduction is not feasible (for example, races that need real infrastructure), produce a contract-level test that asserts the invariant the fix must establish (call ordering, post-condition check, blocking guard, etc.), and reproduce behaviorally on the appropriate runner when one is available. Document any unreproduced hypothesis as `Hypothesis (unreproduced)` with the specific evidence that would confirm or refute it; downstream phases must not assume an unreproduced hypothesis as cause.",
        "- Rule: for each uncovered behavior on the touched surface, the orchestrator dispatches a `gpt-high` test-writer (via the test-coverage workflow) to produce **characterization tests** that capture the current behavior **before** Phase 3 designs any change. Characterization tests land on the WU branch (or a precursor branch). The behavior they capture becomes the contract Phase 3 works against.",
        "- Rule: every entrypoint has a contract — name the contract (parameters, expected output, side effects). Missing contracts are MEDIUM on `behavioral-ambiguity`.",
        "- Rule: dispatch the `code-tracer` operator (`~/ai/agents/code-tracer.md`) when the surface crosses any language boundary. The operator produces a graph of readers/callers/contracts.",
        "- Rule: implicit contracts across language boundaries are HIGH on `language-fragmentation`. Make them explicit, or score them HIGH and let Phase 3 narrow them.",
        "- The cross-language trace (sub-step 2.5.5) reveals the surface crosses boundaries with implicit contracts in so many places that the change-path entropy alone scores HIGH.",
        "- `audit risk`: presence, contracts, migrations, test-intent track, fixture source, residual-risk artifact, and other checklist obligations",
        "- Rule: in **exhaustive mode** for any surface scored HIGH on language-fragmentation or change-path-entropy, dispatch the `code-tracer` operator (`~/ai/agents/code-tracer.md`) to produce the cross-language readers/callers/contracts graph for that surface. Hookpoints derived from a single-language grep are insufficient when the surface crosses boundaries.",
        "That rule is load-bearing: if the same agent writes both, the tests mirror the implementation instead of validating the contract.",
        "Step 6a defines the level outer contract; during Step 6c, once passing evidence exists, post-prototype internal component contract derivation may be triggered.",
        "After Step 6c has passing level evidence, the derivation trigger logic decides whether the level derives accepted internal component contracts, records an evidence-bearing halt/no-split when a trigger fires but no split earns granularity, or proceeds to Phase 7 unchanged when neither trigger arm fires.",
        "- Rule: Recursive Phase 6 reuse. Once a child recursion level enters `level-open`, the same Step 6a contract, Step 6b test-first, Step 6c implementation, procedural-test, swap, and audit semantics apply at that child's `level_id` where those semantics exist, with continuous-overlay review evidence carried through `audit_overlay_refs` for the audited framing record.",
        "### Step 6a - Define contract",
        "- Produces: the level outer contract: schemas, signatures, commands, interface boundaries, explicit behavioral assumptions, fixture application points, and test-intent handoff",
        "- Rule: the contract must be clear enough that another agent can write tests from it without seeing implementation code.",
        "- Rule: the contract must preserve every change risk or verification risk, selected test level, fixture source, assumption-register link, and expected observable signal from the approved proposal test-intent track.",
        "- Rule: Step 6a does not author internal component contracts; those can only be derived from later prototype evidence when the Post-prototype internal contract derivation rule in Step 6c is triggered.",
        "- Rule: `ChildLevelFramingRecord` is Step 6a contract text for recursive child entry, not a standalone schema file or operator output. Required fields, in order:",
        "- Inputs: level outer contract, approved proposal test-intent track, approved `problem map`, **approved `risk/NN-risk-profile.md`**, characterization tests already produced in Phase 2.5 step 2.5.1 for any uncovered behaviors on the touched surface, `risk/NN-supported-surface.md`, and hookpoint research.",
        "- Rule: tests encode intended behavior from the contract and proposal test-intent track before Step 6c writes product code.",
        "- Output-index fields: approved proposal path, contract path, approved `problem map` path, `risk/NN-supported-surface.md` path, hookpoint research path, Step 6b prompt path, Step 6b log path, `level_id` when recursive Phase 6 work emits level-scoped artifacts, each test-intent item, named risk, selected level, proposal or assumption-register source, emitted test file path and test or test-group identifier, residual entry path when the item maps to `risk/NN-test-residuals.md`, documented non-applicability reason when no test is emitted, declared fixture source or fixture application point, procedural obligation, Step 6c evidence that discovered the obligation, emitted procedural test file path and test or test-group identifier when a procedural test was authored, or procedural residual entry path when no procedural test is emitted; residual class when no procedural test is emitted. The path `${scratch_dir}/phase6/step6b-output-index.md` remains the Step 6b output index path; recursive rows and artifact identifiers carry `level_id` and use `<level_id>:<local_artifact_id>` when a string identifier is needed.",
        "- Rule: Phase 6 prototype risk review runs `risk-assessor` after Step 6c produces a passing level prototype and level behavior tests pass, and writes `${planning_dir}/risk/${wu_lower}-prototype-risk.md` with verdict vocabulary `LOW`, `MEDIUM`, and `HIGH` before downstream derivation, `PrototypeSwapRecord`, or before Phase 7 consumes the prototype. Orchestrator-runtime enforcement and runtime refusal at the Phase 6 prototype risk review gate are tracked in a separate ticket and land after this WU; until that ticket lands, this workflow prohibition is enforced by structural pytest plus operator review only. This rule reuses the existing `risk-assessor` operator and does NOT redefine its output contract, and it is distinct from `~/ai/workflows/build-prototype.md` exploratory prototype `dossier/risk-profile.md` lifecycle.",
        "- Rule: Phase 6 tests/contracts alignment review consumes the Step 6a contract, Step 6b tests, and `${scratch_dir}/phase6/step6b-output-index.md`; checks them against the approved proposal test-intent track before Step 6c; and writes `${planning_dir}/alignment/${wu_lower}-tests-contracts.md` with verdict vocabulary `ALIGNED`, `MISALIGNED`, and `NEEDS_REVISION`. Orchestrator-runtime enforcement and owner assignment for this alignment review are tracked in a separate ticket and land after this WU; until that ticket lands, this workflow prohibition is enforced by structural pytest plus operator review only.",
        "- Inputs: contracts, `${scratch_dir}/phase6/step6b-output-index.md`, and the tests from Step 6b.",
        "- Rule: if a test is wrong, that is the contract's fault, not the test's.",
        "- Rule: if contract intent truly changed, revise the contract explicitly and regenerate the affected tests from that revised contract.",
        "- Rule: Post-prototype internal contract derivation: after Step 6c produces a passing level prototype that passes level behavior tests, derive internal component contracts only when Phase 3 opened recursive or component-decomposition scope, or when candidate internal components emerge from the passing prototype.",
        "- Rule: Post-prototype internal contract derivation is precisely one layer deep at the current recursion level. The derivation output may name only the immediate internal components needed to satisfy what the passing prototype found at that level; it must not include nested sub-components, grandchild components, or any multi-layer component hierarchy in the same derivation pass. Deeper decomposition happens only through recursive child entry and recursive Phase 6 reuse after an accepted immediate component opens a child level with its own `level_id`.",
        "- Rule: derived internal contracts are recorded as named post-prototype subsections in the existing `${planning_dir}/contracts/${wu_lower}-${slug}.md` contract artifact, not in a new file.",
        "- Rule: Evidence-bearing halt rule: a level halts only when candidate splits earn granularity under none of the `halt_basis` options: `clarify contracts`, `reduce accidental coupling`, `expose a design challenge`, `improve evidence`, `lower meaningful risk`. The `halt_basis` field records option-level evidence showing why each listed option was unsatisfied.",
        "- Rule: **the title and body MUST be authored by `~/ai/agents/pr-writer.md`** — never hand-written by the orchestrator and never inlined into the `gh pr create` invocation. The writer enforces audience-and-content rules (no internal jargon, no commit-history sections, no closed-PR or local-planning-artifact references) that hand-written or templated bodies routinely violate. Pass the relevant phase artifacts (`problem-map.md`, `proposal.md`, `contract.md`, RCA evidence) as `context_files` so the writer has intent grounding without citing them in the body. For stacked PRs, supply `stack_parent_pr=<num>`; for any reference to merged work, supply `merged_refs=<list>`; when the selected ticket backend is Linear and the Linear key is known, supply `linear_issue_keys=<KEY>` so `pr-writer` emits the close-keyword footer itself.",
    ],
    "pr-review.md": [
        "This phase is decomposition review plus supported-surface verification, test-coverage, and commit-organization checks. Each gate presupposes a **proposal** as the contract being enforced — the gates are not directly applicable to work without a proposal (e.g. prototypes).",
        "For prototype presentation — work that arrived at an answer without a proposal — see `~/ai/workflows/build-prototype.md` § Phase P3, which runs the **functional analogs** of these gates (proof-test audit, one-question check, answer-trace, commit-hygiene) without requiring a proposal contract. The two workflows share `commit-hygiene-operator` but are otherwise distinct: PR-review presents *implementation*, P3 presents *prototypes*.",
        "- Read the contract next: schemas, endpoint signatures, CLI definitions, public interfaces, explicit acceptance criteria, fixture application points, and test-intent handoff.",
        "| Valid test correction/invalidation | `return to research` when framing or assumptions changed; otherwise `ordinary fix-pass findings` after the contract and affected tests are corrected. |",
        "| Contract revised because implementation failed | `blocking`; if the failure exposes invalidated framing, `return to research`. |",
        "- Flag over-assertion, weak tests, and same-agent authorship: tests must validate the contract, fail when implementation is wrong, and be written by a separate test writer from the implementation writer.",
        "Reference `~/ai/conventions/git.md` for the commit contract.",
    ],
    "project-bootstrap.md": [
        "- The task asks to migrate existing project-local wrappers across projects; this workflow only defines the bootstrap procedure and emission contract.",
        "### Closed Path Dispatch Contract",
    ],
    "release-management.md": [
        "- A future release orchestrator needs one workflow contract for cutting `release/*`, handling `hotfix/*` cherry-picks, promoting to `main`, creating the release `tag`, and closing reconcile obligations.",
    ],
    "risk-reduction.md": [
        "This workflow is **not** part of the implementation pipeline. It produces its own small ticket per item. Items are typically smaller than implementation WUs because the change is focused: write tests for one uncovered surface, consolidate two duplicate scripts, document one undocumented contract, etc.",
        "| **Contract documentation** | `behavioral-ambiguity`, `language-fragmentation` (when contracts cross languages) | small | a markdown contract doc next to the surface; ambiguities resolved by writing them down |",
        "- **Contract documentation**: dispatch a `gpt-high` researcher with the surface and a request for a contract doc (parameters, expected output, side effects, error modes). The doc lives next to the code or in `planning/contracts/<surface>.md` per project convention.",
    ],
    "roadmap.md": [
        "- **Prototype escape hatch**: when feasibility risk cannot be assessed from research alone (the proposed substrate's behavior under load, the third-party integration's actual contract, etc.), dispatch `~/ai/agents/prototype-orchestrator.md` per `~/ai/workflows/build-prototype.md` with `roadmap_layer=engineering-roadmap` and the unanswered feasibility question. The prototype's dossier supplies the evidence the feasibility risk gate is waiting on. Roadmap revision incorporates the dossier's findings before the layer's gates re-run.",
        "- **Prototype escape hatch**: when a slice's contract / parallelizability / schema cannot be named without trying it, dispatch `~/ai/agents/prototype-orchestrator.md` with `roadmap_layer=ai-roadmap-phase-N` and the slice's unknowns as the prototype's question. The dossier's spawned-tickets.md becomes the slice's eventual implementation tickets at Layer 4; the dossier's risk-profile becomes the slice's pre-Phase-2.5 baseline.",
    ],
    "verified-rebase.md": [
        "Workflow files aren't unit-testable. The contract is:",
    ],
}


# Proposal test-intent item 6 risk: tracked workflow docs skip required
# metadata or use incompatible contract shape; selected level: component
# shape-guard.
def test_all_workflow_docs_have_valid_dispatch_contract():
    from tools.workflow_index.generator import (
        parse_frontmatter,
        validate_dispatch_contract,
    )

    workflow_docs = _workflow_docs()
    assert workflow_docs, f"no workflow docs found under {WORKFLOWS_DIR}"

    for path in workflow_docs:
        parsed = parse_frontmatter(path.read_text(encoding="utf-8"), str(path))

        assert parsed.get("workflow", {}).get("id") == path.stem, (
            f"{path}: workflow.id must match filename stem"
        )
        assert "workflow_dispatch_contract" in parsed, (
            f"{path}: missing workflow_dispatch_contract"
        )
        contract = parsed["workflow_dispatch_contract"]
        assert set(contract) == DISPATCH_CONTRACT_KEYS, (
            f"{path}: workflow_dispatch_contract must have exactly "
            f"{sorted(DISPATCH_CONTRACT_KEYS)}"
        )
        assert isinstance(contract["orchestrator"], str), (
            f"{path}: orchestrator must be a string"
        )
        assert contract["orchestrator"].strip(), (
            f"{path}: orchestrator must be non-empty"
        )
        for key in ("inputs", "expectations", "outputs", "non_goals"):
            assert isinstance(contract[key], list), f"{path}: {key} must be a list"
            assert contract[key], f"{path}: {key} must be non-empty"
            assert all(isinstance(item, str) and item for item in contract[key]), (
                f"{path}: {key} must contain only non-empty strings"
            )
        validate_dispatch_contract(contract, str(path))


# Proposal test-intent item 6 and assumption-register entry 2 risk:
# unevidenced aliases or empty alias blocks get shipped; selected level:
# component shape-guard.
def test_workflow_docs_omit_aliases_until_evidenced():
    from tools.workflow_index.generator import parse_frontmatter

    for path in _workflow_docs():
        parsed = parse_frontmatter(path.read_text(encoding="utf-8"), str(path))

        assert "workflow_aliases" not in parsed, (
            f"{path}: omit workflow_aliases until there is concrete alias evidence"
        )


# Proposal test-intent item 5 risk: checked-in generated index is stale;
# selected level: component shape-guard.
def test_workflow_index_is_current():
    from tools.workflow_index.generator import check_index

    matches, diff_text = check_index(WORKFLOWS_DIR, WORKFLOWS_DIR / "index.json")

    assert matches is True, (
        "workflow index is stale; run "
        "`python3 -m tools.workflow_index generate`.\n"
        f"{diff_text}"
    )


def test_all_workflow_docs_have_normalized_body_dispatch_surface():
    workflow_docs = _workflow_docs()
    assert workflow_docs, f"no workflow docs found under {WORKFLOWS_DIR}"

    for path in workflow_docs:
        text = path.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text, str(path))
        contract = frontmatter["workflow_dispatch_contract"]
        try:
            body = _parse_body_dispatch_surface(text)
        except AssertionError as error:
            assert False, f"{path}: {error}"

        assert body["orchestrator"] == contract["orchestrator"], (
            f"{path}: body dispatch surface orchestrator must mirror frontmatter"
        )
        for key in ("inputs", "expectations", "outputs", "non_goals"):
            assert body[key] == contract[key], (
                f"{path}: body dispatch surface {key} must mirror frontmatter"
            )


def test_workflow_doc_body_contract_lines_preserved():
    word = re.compile(r"\bcontracts?\b", re.IGNORECASE)
    for doc_name, baseline_lines in _T4_BASELINE.items():
        path = WORKFLOWS_DIR / doc_name
        assert path.exists(), f"missing workflow doc from T4 baseline: {path}"
        post_edit_lines = _extract_body_excluding_dispatch_surface(
            path.read_text(encoding="utf-8")
        )

        for baseline_line in baseline_lines:
            assert any(baseline_line in post_line for post_line in post_edit_lines), (
                f"{path}: missing frozen contract-body baseline line: "
                f"{baseline_line!r}"
            )
        count = sum(1 for line in post_edit_lines if word.search(line))
        assert count >= len(baseline_lines), (
            f"{path}: contract/contracts body-line count fell from "
            f"{len(baseline_lines)} to {count}"
        )


# Proposal test-intent item 7 risk: the generator lands but is not
# discoverable from the tool catalog; selected level: unit.
def test_workflow_index_tool_is_discoverable():
    underscore_readme = REPO_ROOT / "tools" / "workflow_index" / "README.md"
    hyphen_readme = REPO_ROOT / "tools" / "workflow-index" / "README.md"
    tools_readme = REPO_ROOT / "tools" / "README.md"

    assert underscore_readme.exists() or hyphen_readme.exists(), (
        "missing workflow-index tool README"
    )
    assert tools_readme.exists(), f"missing tools catalog: {tools_readme}"

    catalog_text = tools_readme.read_text(encoding="utf-8")
    assert "workflow_index" in catalog_text or "workflow-index" in catalog_text
