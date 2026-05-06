from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import timezone
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_DIR = REPO_ROOT / "tools" / "pr-batch-poller"
# The tool directory contains a hyphen, so add it directly for module import.
sys.path.insert(0, str(TOOL_DIR))

import pr_batch_poller
from pr_batch_poller import (
    DEFAULT_CHUNK_SIZE,
    SCHEMA_VERSION,
    build_graphql_request,
    dedupe_prs,
    filter_rows_since,
    make_error_row,
    make_success_row,
    map_graphql_response,
    parse_pr_token,
    parse_prs_arg,
    parse_prs_file,
    parse_since,
    plan_chunks,
    render_json,
    render_jsonl,
    render_table,
)


TEST_FILE = Path(__file__)
README_PATH = TOOL_DIR / "README.md"
CATALOG_PATH = REPO_ROOT / "tools" / "README.md"
ENTRYPOINT_PATH = TOOL_DIR / "__main__.py"

ERR_REPO_NOT_FOUND = "repo_not_found_or_forbidden"
ERR_PR_NOT_FOUND = "pr_not_found_or_forbidden"
ERR_GRAPHQL_PARTIAL = "graphql_partial_error"
ERR_COMMENT_WINDOW = "comment_window_exceeded"
ERROR_CODES = {
    "repo": ERR_REPO_NOT_FOUND,
    "pr": ERR_PR_NOT_FOUND,
    "partial": ERR_GRAPHQL_PARTIAL,
    "window": ERR_COMMENT_WINDOW,
}

STATUS_KEYS = {
    "pr_url",
    "state",
    "merged",
    "merged_at",
    "merge_sha",
    "head_sha",
    "head_ref_name",
    "base_ref_name",
    "base_ref_oid",
    "updated_at",
    "last_event_at",
    "last_comment_at",
    "new_comments_since",
}
IDENTITY_KEYS = {"schema_version", "row_type", "pr", "owner", "repo", "number"}
REQUIRED_ROW_KEYS = IDENTITY_KEYS | STATUS_KEYS | {"error"}


def _pr(token: str):
    return parse_pr_token(token)


def _canon(prs):
    return [pr.canonical for pr in prs]


def _comments(*updated_at: str, has_next_page: bool = False):
    return {
        "nodes": [{"updatedAt": value} for value in updated_at],
        "pageInfo": {"hasNextPage": has_next_page},
    }


def _pr_node(
    number: int = 1,
    *,
    updated_at: str = "2026-05-06T12:00:00Z",
    comments: dict | None = None,
):
    return {
        "number": number,
        "url": f"https://github.com/acme/widget/pull/{number}",
        "state": "MERGED",
        "merged": True,
        "mergedAt": "2026-05-06T12:30:00Z",
        "mergeCommit": {"oid": f"merge-{number}"},
        "headRefName": f"feature-{number}",
        "headRefOid": f"head-{number}",
        "baseRefName": "main",
        "baseRefOid": f"base-{number}",
        "updatedAt": updated_at,
        "comments": comments if comments is not None else _comments(),
    }


def _response_for_request(request, *, nodes_by_pr: dict[str, dict] | None = None):
    data: dict[str, dict] = {}
    nodes_by_pr = nodes_by_pr or {}
    for repo_alias, pr_alias in request.alias_map:
        pr = request.alias_map[(repo_alias, pr_alias)]
        repo_data = data.setdefault(repo_alias, {})
        repo_data[pr_alias] = nodes_by_pr.get(pr.canonical, _pr_node(pr.number))
    return {"data": data}


def _response_with_repo_null(request, repo_alias: str):
    response = _response_for_request(request)
    response["data"][repo_alias] = None
    return response


def _capture_main(argv, monkeypatch, fake_run_gh_graphql):
    monkeypatch.setattr("pr_batch_poller.run_gh_graphql", fake_run_gh_graphql)
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = pr_batch_poller.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _assert_success_schema(row):
    assert set(row) == REQUIRED_ROW_KEYS
    assert row["schema_version"] == SCHEMA_VERSION
    assert row["row_type"] == "pr_status"
    assert row["error"] is None


def _assert_error_schema(row, code: str):
    assert set(row) == REQUIRED_ROW_KEYS
    assert row["schema_version"] == SCHEMA_VERSION
    assert row["row_type"] == "error"
    assert row["error"]["code"] == code
    assert row["error"]["message"]


def _row_fixture(**overrides):
    row = {
        "schema_version": SCHEMA_VERSION,
        "row_type": "pr_status",
        "pr": "acme/widget#1",
        "owner": "acme",
        "repo": "widget",
        "number": 1,
        "pr_url": "https://github.com/acme/widget/pull/1",
        "state": "OPEN",
        "merged": False,
        "merged_at": None,
        "merge_sha": None,
        "head_sha": "head-1",
        "head_ref_name": "feature-1",
        "base_ref_name": "main",
        "base_ref_oid": "base-1",
        "updated_at": "2026-05-06T12:00:00Z",
        "last_event_at": "2026-05-06T12:00:00Z",
        "last_comment_at": None,
        "new_comments_since": None,
        "error": None,
    }
    row.update(overrides)
    return row


def test_t1_prs_arg_accepts_comma_tokens_and_trims_whitespace():
    """Risk: parser ambiguity; level: unit; source: T1/A7."""
    parsed = parse_prs_arg(" acme/widget#1, Octo/repo.name#2 ")

    assert _canon(parsed) == ["acme/widget#1", "Octo/repo.name#2"]


def test_t1_prs_arg_rejects_empty_comma_token_with_cli_error(monkeypatch):
    """Risk: parser ambiguity; level: unit; source: T1/A7."""
    code, stdout, stderr = _capture_main(
        ["--prs", "acme/widget#1,,acme/widget#2"],
        monkeypatch,
        lambda query: pytest.fail("run_gh_graphql must not be called for invalid input"),
    )

    assert code == 2
    assert stdout == ""
    assert stderr.startswith("pr-batch-poller:")


def test_t2_prs_file_ignores_blank_lines(tmp_path):
    """Risk: file input contract drift; level: unit; source: T2/A7."""
    prs_file = tmp_path / "prs.txt"
    prs_file.write_text("\nacme/widget#1\n   \nacme/widget#2\n", encoding="utf-8")

    assert _canon(parse_prs_file(prs_file)) == ["acme/widget#1", "acme/widget#2"]


def test_t2_prs_file_has_no_comment_syntax(tmp_path):
    """Risk: file input contract drift; level: unit; source: T2/A7."""
    prs_file = tmp_path / "prs.txt"
    prs_file.write_text("acme/widget#1\n# acme/widget#2\n", encoding="utf-8")

    with pytest.raises(Exception):
        parse_prs_file(prs_file)


def test_t2_prs_and_prs_file_are_mutually_exclusive(tmp_path, monkeypatch):
    """Risk: file input contract drift; level: unit; source: T2/A7."""
    prs_file = tmp_path / "prs.txt"
    prs_file.write_text("acme/widget#1\n", encoding="utf-8")

    code, stdout, stderr = _capture_main(
        ["--prs", "acme/widget#1", "--prs-file", str(prs_file)],
        monkeypatch,
        lambda query: pytest.fail("run_gh_graphql must not be called for invalid input"),
    )

    assert code == 2
    assert stdout == ""
    assert stderr.startswith("pr-batch-poller:")


@pytest.mark.parametrize(
    ("token", "owner", "repo", "number", "canonical"),
    [
        ("acme/widget#1", "acme", "widget", 1, "acme/widget#1"),
        ("Octo/repo.name_2#12", "Octo", "repo.name_2", 12, "Octo/repo.name_2#12"),
        ("a/r-1#9", "a", "r-1", 9, "a/r-1#9"),
    ],
    ids=["simple", "multi-digit", "short-owner"],
)
def test_t3_pr_token_accepts_approved_grammar(token, owner, repo, number, canonical):
    """Risk: PR grammar ambiguity; level: unit; source: T3/A8."""
    parsed = parse_pr_token(token)

    assert (parsed.owner, parsed.repo, parsed.number, parsed.canonical) == (
        owner,
        repo,
        number,
        canonical,
    )


@pytest.mark.parametrize(
    "token",
    [
        "acme-widget#1",
        "acme/widget1",
        "acme/widget#0",
        "acme/widget#-1",
        "acme/widget#abc",
        "/widget#1",
        "acme/#1",
        "-acme/widget#1",
        "acme/widget#0012",
    ],
    ids=[
        "missing-slash",
        "missing-hash",
        "zero",
        "negative",
        "non-integer",
        "empty-owner",
        "empty-repo",
        "owner-leading-hyphen",
        "leading-zero-number",
    ],
)
def test_t3_pr_token_rejects_invalid_grammar(token):
    """Risk: PR grammar ambiguity; level: unit; source: T3/A8.

    Per contract §PR identifier grammar, the regex is `[1-9][0-9]*` (no
    leading zeros). Leading-zero forms are rejected at the input boundary
    rather than silently normalized.
    """
    with pytest.raises(Exception):
        parse_pr_token(token)


def test_t4_dedupe_preserves_first_seen_order_after_canonicalization():
    """Risk: duplicate handling; level: unit; source: T4/A7."""
    prs = [
        _pr("acme/widget#1"),
        _pr("beta/api#2"),
        _pr("acme/widget#1"),
        _pr("acme/widget#3"),
        _pr("beta/api#2"),
    ]

    assert _canon(dedupe_prs(prs)) == ["acme/widget#1", "beta/api#2", "acme/widget#3"]


@pytest.mark.parametrize(
    "value",
    [
        "2026-05-06T12:00:00Z",
        "2026-05-06T05:00:00-07:00",
    ],
    ids=["zulu", "offset"],
)
def test_t5_since_accepts_offset_aware_timestamps(value):
    """Risk: timestamp correctness; level: unit; source: T5/A6."""
    parsed = parse_since(value)

    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.astimezone(timezone.utc).isoformat() == "2026-05-06T12:00:00+00:00"


@pytest.mark.parametrize("value", ["2026-05-06T12:00:00", "not-a-date"], ids=["naive", "unparseable"])
def test_t5_since_rejects_naive_and_unparseable_values(value, monkeypatch):
    """Risk: timestamp correctness; level: unit; source: T5/A6."""
    code, stdout, stderr = _capture_main(
        ["--prs", "acme/widget#1", "--since", value],
        monkeypatch,
        lambda query: pytest.fail("run_gh_graphql must not be called for invalid input"),
    )

    assert code == 2
    assert stdout == ""
    assert stderr.startswith("pr-batch-poller:")


def test_t6_graphql_alias_map_round_trips_response_identities():
    """Risk: query/response alias mismatch; level: unit; source: T6/A1."""
    request = build_graphql_request(plan_chunks([_pr("acme/widget#1"), _pr("beta/api#2")])[0])

    assert len(request.alias_map) == 2
    assert {pr.canonical for pr in request.alias_map.values()} == {"acme/widget#1", "beta/api#2"}
    rows = map_graphql_response(request, _response_for_request(request), since=None)

    assert [row["pr"] for row in rows] == ["acme/widget#1", "beta/api#2"]
    assert [(row["owner"], row["repo"], row["number"]) for row in rows] == [
        ("acme", "widget", 1),
        ("beta", "api", 2),
    ]


def test_t6_graphql_request_includes_every_contracted_field():
    """Risk: query/response alias mismatch — exact field set; level: unit; source: T6/A1.

    The contract §GraphQL field set names exactly the fields each PR alias
    MUST request. This test asserts they all appear in the generated query
    text so a future edit cannot silently drop one (which would either
    null-out a downstream row field or cause `comment_window_exceeded`
    semantics to misfire).
    """
    request = build_graphql_request(plan_chunks([_pr("acme/widget#1")])[0])

    assert "repository(" in request.query
    assert "pullRequest(" in request.query
    for field in (
        "number",
        "url",
        "state",
        "merged",
        "mergedAt",
        "mergeCommit",
        "oid",
        "headRefName",
        "headRefOid",
        "baseRefName",
        "baseRefOid",
        "updatedAt",
        "comments(",
        "first: 100",
        "UPDATED_AT",
        "DESC",
        "hasNextPage",
    ):
        assert field in request.query, f"contracted GraphQL field/clause missing: {field!r}"


def test_t7_chunking_uses_default_size_fifty_and_splits_fifty_one():
    """Risk: batch cost regression; level: unit; source: T7/A2."""
    fifty = [_pr(f"acme/widget#{number}") for number in range(1, DEFAULT_CHUNK_SIZE + 1)]
    fifty_one = fifty + [_pr(f"acme/widget#{DEFAULT_CHUNK_SIZE + 1}")]

    assert len(plan_chunks(fifty)) == 1
    chunks = plan_chunks(fifty_one)
    alias_counts = [len(build_graphql_request(chunk).alias_map) for chunk in chunks]

    assert DEFAULT_CHUNK_SIZE == 50
    assert len(chunks) == 2
    assert alias_counts == [50, 1]


def test_t7_chunking_allows_multiple_repositories_in_one_chunk():
    """Risk: batch cost regression; level: unit; source: T7/A2."""
    chunk = plan_chunks([_pr("acme/widget#1"), _pr("beta/api#2"), _pr("acme/widget#3")])[0]
    request = build_graphql_request(chunk)

    assert {pr.canonical for pr in request.alias_map.values()} == {
        "acme/widget#1",
        "beta/api#2",
        "acme/widget#3",
    }
    assert {pr.repo for pr in request.alias_map.values()} == {"widget", "api"}


def test_t8_repo_null_emits_error_for_every_pr_in_that_repo():
    """Risk: repository null handling; level: unit; source: T8/A1."""
    request = build_graphql_request(plan_chunks([_pr("acme/widget#1"), _pr("acme/widget#2")])[0])
    repo_alias = next(iter(request.alias_map))[0]

    rows = map_graphql_response(request, _response_with_repo_null(request, repo_alias), since=None)

    assert [row["pr"] for row in rows] == ["acme/widget#1", "acme/widget#2"]
    assert all(row["error"]["code"] == ERROR_CODES["repo"] for row in rows)
    for row in rows:
        _assert_error_schema(row, ERROR_CODES["repo"])


def test_t9_pr_null_emits_error_without_failing_sibling_pr():
    """Risk: PR null handling; level: unit; source: T9/A1."""
    request = build_graphql_request(plan_chunks([_pr("acme/widget#1"), _pr("acme/widget#2")])[0])
    response = _response_for_request(request)
    first_repo_alias, first_pr_alias = next(iter(request.alias_map))
    response["data"][first_repo_alias][first_pr_alias] = None

    rows = map_graphql_response(request, response, since=None)

    assert rows[0]["pr"] == "acme/widget#1"
    _assert_error_schema(rows[0], ERROR_CODES["pr"])
    assert rows[1]["pr"] == "acme/widget#2"
    _assert_success_schema(rows[1])


def test_t10_mapped_graphql_error_becomes_partial_error_row():
    """Risk: partial GraphQL error handling; level: unit; source: T10/A1."""
    request = build_graphql_request(plan_chunks([_pr("acme/widget#1"), _pr("acme/widget#2")])[0])
    repo_alias, pr_alias = next(iter(request.alias_map))
    response = _response_for_request(request)
    response["errors"] = [{"message": "field unavailable", "path": [repo_alias, pr_alias]}]

    rows = map_graphql_response(request, response, since=None)

    assert rows[0]["pr"] == "acme/widget#1"
    _assert_error_schema(rows[0], ERROR_CODES["partial"])
    _assert_success_schema(rows[1])


def test_t10_unmapped_graphql_error_is_fatal_cli_exit(monkeypatch):
    """Risk: partial GraphQL error handling; level: unit; source: T10/A1."""
    code, stdout, stderr = _capture_main(
        ["--prs", "acme/widget#1"],
        monkeypatch,
        lambda query: {"data": {}, "errors": [{"message": "rate limited", "path": ["viewer"]}]},
    )

    assert code == 1
    assert stdout == ""
    assert stderr.startswith("pr-batch-poller:")


def test_t11_comment_window_exceeded_when_count_is_untrustworthy():
    """Risk: comment count trust; level: unit; source: T11/A11."""
    since = parse_since("2026-05-06T12:00:00Z")
    request = build_graphql_request(plan_chunks([_pr("acme/widget#1")])[0])
    node = _pr_node(
        1,
        comments=_comments(
            *(["2026-05-06T12:01:00Z"] * 100),
            has_next_page=True,
        ),
    )

    rows = map_graphql_response(request, _response_for_request(request, nodes_by_pr={"acme/widget#1": node}), since)

    assert len(rows) == 1
    _assert_error_schema(rows[0], ERROR_CODES["window"])
    assert rows[0]["new_comments_since"] is None


def test_t12_since_filter_suppresses_only_unchanged_success_rows():
    """Risk: since filtering false negatives; level: unit; source: T12/A6."""
    since = parse_since("2026-05-06T12:00:00Z")
    unchanged = _row_fixture(pr="acme/widget#1", number=1, last_event_at="2026-05-06T12:00:00Z")
    changed = _row_fixture(pr="acme/widget#2", number=2, last_event_at="2026-05-06T12:00:01Z")
    error = make_error_row(_pr("acme/widget#3"), ERROR_CODES["pr"], "missing")

    rows = filter_rows_since([unchanged, changed, error], since)

    assert [row["pr"] for row in rows] == ["acme/widget#2", "acme/widget#3"]


def test_t13_comment_counts_and_latest_comment_with_since():
    """Risk: comment count semantics; level: unit; source: T13/A5/A11."""
    since = parse_since("2026-05-06T12:00:00Z")
    node = _pr_node(
        1,
        comments=_comments(
            "2026-05-06T12:03:00Z",
            "2026-05-06T12:00:00Z",
            "2026-05-06T11:59:00Z",
            "2026-05-06T12:01:00Z",
        ),
    )

    row = make_success_row(_pr("acme/widget#1"), node, since)

    _assert_success_schema(row)
    assert row["last_comment_at"] == "2026-05-06T12:03:00Z"
    assert row["new_comments_since"] == 2


def test_t13_comment_count_is_null_when_since_is_omitted():
    """Risk: comment count semantics; level: unit; source: T13/A5/A11."""
    node = _pr_node(1, comments=_comments("2026-05-06T12:03:00Z"))

    row = make_success_row(_pr("acme/widget#1"), node, since=None)

    _assert_success_schema(row)
    assert row["last_comment_at"] == "2026-05-06T12:03:00Z"
    assert row["new_comments_since"] is None


def test_t14_jsonl_renderer_outputs_one_object_per_line_with_trailing_newline():
    """Risk: renderer contract drift; level: unit; source: T14/A9."""
    rows = [_row_fixture(number=1), _row_fixture(pr="acme/widget#2", number=2)]

    rendered = render_jsonl(rows)

    assert rendered.endswith("\n")
    parsed = [json.loads(line) for line in rendered.splitlines()]
    assert parsed == rows


def test_t14_json_renderer_outputs_array_of_same_objects():
    """Risk: renderer contract drift; level: unit; source: T14/A9."""
    rows = [_row_fixture(number=1), _row_fixture(pr="acme/widget#2", number=2)]

    assert json.loads(render_json(rows)) == rows


def test_t14_table_renderer_is_human_only_smoke():
    """Risk: renderer contract drift; level: unit; source: T14/A9."""
    table = render_table([_row_fixture(pr="acme/widget#1", state="MERGED")])

    assert "acme/widget#1" in table
    assert "MERGED" in table or "pr_status" in table


def test_t15_fatal_cli_errors_use_exit_2_stderr_and_no_stdout(monkeypatch):
    """Risk: fatal CLI behavior; level: unit; source: T15/A10."""
    code, stdout, stderr = _capture_main(
        ["--format", "xml", "--prs", "acme/widget#1"],
        monkeypatch,
        lambda query: pytest.fail("run_gh_graphql must not be called for invalid input"),
    )

    assert code == 2
    assert stdout == ""
    assert stderr.startswith("pr-batch-poller:")


@pytest.mark.parametrize(
    ("label", "message"),
    [
        ("missing-gh", "gh executable not found"),
        ("nonzero-gh", "gh api graphql exited non-zero"),
        ("malformed-json", "gh api graphql returned malformed JSON"),
    ],
    ids=["missing-gh", "nonzero-gh", "malformed-json"],
)
def test_t16_adapter_fatal_runtime_failures_exit_1_without_rows(label, message, monkeypatch):
    """Risk: runtime fatal behavior; level: unit; source: T16/A3/A10."""

    def fake_run_gh_graphql(query):
        raise RuntimeError(message)

    code, stdout, stderr = _capture_main(["--prs", "acme/widget#1"], monkeypatch, fake_run_gh_graphql)

    assert label
    assert code == 1
    assert stdout == ""
    assert stderr.startswith("pr-batch-poller:")


def test_t16_adapter_times_out_hung_gh_graphql_process(monkeypatch):
    """Risk: runtime fatal behavior; level: unit; source: T16/A3/A10."""

    def fake_run(args, **kwargs):
        assert kwargs["timeout"] == pr_batch_poller.GH_GRAPHQL_TIMEOUT_SECONDS
        raise pr_batch_poller.subprocess.TimeoutExpired(args, kwargs["timeout"])

    monkeypatch.setattr("pr_batch_poller.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="gh api graphql timed out"):
        pr_batch_poller.run_gh_graphql("query { viewer { login } }")


def test_t17_schema_version_is_stamped_on_success_and_error_rows():
    """Risk: schema version omission; level: unit; source: T17/A2."""
    success = make_success_row(_pr("acme/widget#1"), _pr_node(1), since=None)
    error = make_error_row(_pr("acme/widget#2"), ERROR_CODES["partial"], "partial")

    assert SCHEMA_VERSION == 1
    assert success["schema_version"] == SCHEMA_VERSION
    assert error["schema_version"] == SCHEMA_VERSION


def test_t18_success_and_error_rows_have_all_required_nullable_keys():
    """Risk: nullable-rule drift; level: unit; source: T18/A10."""
    success = make_success_row(_pr("acme/widget#1"), _pr_node(1), since=None)
    error = make_error_row(_pr("acme/widget#2"), ERROR_CODES["repo"], "repo missing")

    _assert_success_schema(success)
    _assert_error_schema(error, ERROR_CODES["repo"])
    for key in STATUS_KEYS:
        assert key in success
        assert key in error


def test_t19_main_entrypoint_is_thin_delegation_only():
    """Risk: entrypoint leakage; level: unit/static; source: T19/A8."""
    text = ENTRYPOINT_PATH.read_text(encoding="utf-8")

    assert "from pr_batch_poller import main" in text
    assert "SystemExit(main())" in text
    for forbidden in [
        "SCHEMA_VERSION =",
        ERROR_CODES["repo"],
        "argparse",
        "pullRequest",
        "render_json",
        "comments(first:",
    ]:
        assert forbidden not in text


def test_t20_readme_documents_implemented_contract_without_skeleton_markers():
    """Risk: README skeleton/TODO brittleness; level: unit/static; source: T20/A2-A11."""
    text = README_PATH.read_text(encoding="utf-8")
    lower = text.lower()

    for required in [
        "implemented",
        "one concern",
        "--prs",
        "--prs-file",
        "--since",
        "offset-aware",
        "jsonl",
        "json",
        "table",
        "schema version",
        "success row",
        "error row",
        "chunk",
        "50",
        "resumer",
        "exit",
        "anti-scope",
        "used by",
        "scheduler",
        "wu-session-resumer",
    ]:
        assert required in lower
    for code in ERROR_CODES.values():
        assert code in text
    for forbidden in [
        "Status: skeleton",
        "TODO",
        "Implement.",
        "transport choice",
        "stable JSONL schema",
        "error semantics",
        "--since filtering",
        "we'll figure out",
    ]:
        assert forbidden not in text


def test_t21_catalog_marks_poller_implemented_and_preserves_composition_wording():
    """Risk: catalog stale status; level: unit/static smoke; source: T21/A4."""
    text = CATALOG_PATH.read_text(encoding="utf-8")
    line = next(line for line in text.splitlines() if "pr-batch-poller/" in line)

    assert "implemented" in line.lower()
    assert "skeleton only" not in line.lower()
    for term in ["scheduler", "pr-batch-poller", "wu-session-resumer"]:
        assert term in text


def test_t22_test_file_centralizes_schema_fixture_and_error_code_assertions():
    """Risk: test change-path entropy; level: unit/static smoke; source: T22/A10."""
    text = TEST_FILE.read_text(encoding="utf-8")

    assert "REQUIRED_ROW_KEYS =" in text
    assert "STATUS_KEYS =" in text
    assert "ERROR_CODES =" in text
    assert "def _pr_node(" in text
    assert "def _assert_success_schema(" in text
    assert "def _assert_error_schema(" in text
    for code in ERROR_CODES.values():
        assert code in text
    assert text.count("def test_t") >= 22
