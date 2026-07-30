"""Tests for CodeRabbit review verdict extraction."""

from __future__ import annotations

import pathlib
import sys

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import coderabbit_review_driver as driver  # noqa: E402


BOT_LOGIN = "coderabbitai[bot]"


def _review(
    review_id: int,
    state: str,
    submitted_at: str,
    login: str = BOT_LOGIN,
    commit_id: str = "head-sha",
) -> dict:
    return {
        "id": review_id,
        "state": state,
        "submitted_at": submitted_at,
        "commit_id": commit_id,
        "user": {"login": login},
    }


def _summary(
    comment_id: int, body: str, updated_at: str, login: str = BOT_LOGIN
) -> dict:
    return {
        "id": comment_id,
        "body": body,
        "created_at": updated_at,
        "updated_at": updated_at,
        "user": {"login": login},
    }


def _ack_body(action_marker: str, review_marker: str) -> str:
    return f"<summary>{action_marker}</summary>\n\n{review_marker}\n"


def test_current_incremental_completion_acknowledgement_reports_observed_marker(
    monkeypatch,
) -> None:
    body = _ack_body("Action performed", "Review finished.")
    repo = driver.Repo(owner="nestharus", name="agent-core")
    monkeypatch.setattr(driver, "repo_label_enabled", lambda *args: (True, {}))
    monkeypatch.setattr(driver, "gh_json", lambda *args: {"id": 100})
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(
        driver,
        "gh_paginated_array",
        lambda *args: [{"id": 101, "body": body, "user": {"login": BOT_LOGIN}}],
    )
    monkeypatch.setattr(driver, "save_bot_login", lambda *args: None)

    evidence = driver.trigger_review(repo, 192, "incremental", driver.DEFAULT_LABEL)

    assert evidence["ack_marker"] == "Review finished."
    assert evidence["ack_body"] == body


def test_current_full_completion_acknowledgement_is_supported() -> None:
    body = _ack_body("Action performed", "Full review finished.")

    assert driver.trigger_ack_marker(body, "full") == "Full review finished."


def test_legacy_triggered_acknowledgement_is_supported() -> None:
    body = _ack_body("Actions performed", "Review triggered.")

    assert driver.trigger_ack_marker(body, "incremental") == "Review triggered."


def test_incremental_mode_rejects_full_review_acknowledgement() -> None:
    body = _ack_body("Action performed", "Full review finished.")

    assert driver.trigger_ack_marker(body, "incremental") is None


def test_unrelated_bot_text_is_not_an_acknowledgement() -> None:
    body = "Review finished. Here are unrelated release notes."

    assert driver.trigger_ack_marker(body, "incremental") is None


def test_approved_review_is_terminal_even_when_later_commented_review_exists() -> None:
    signal = driver.coderabbit_decision_signal(
        [
            _review(1, "CHANGES_REQUESTED", "2026-05-21T09:38:26Z"),
            _review(2, "COMMENTED", "2026-05-21T09:51:38Z"),
            _review(3, "APPROVED", "2026-05-21T09:51:46Z"),
            _review(4, "COMMENTED", "2026-05-21T09:51:48Z"),
        ],
        [],
        BOT_LOGIN,
    )

    assert signal["decision"] == "APPROVED"
    assert signal["source"] == "github_review"
    assert signal["review_id"] == 3
    assert driver.review_decision_outcome(signal["decision"]) == "approved"


def test_changes_requested_review_is_terminal_even_when_later_commented_review_exists() -> (
    None
):
    signal = driver.coderabbit_decision_signal(
        [
            _review(1, "APPROVED", "2026-05-21T09:38:26Z"),
            _review(2, "CHANGES_REQUESTED", "2026-05-21T09:51:46Z"),
            _review(3, "COMMENTED", "2026-05-21T09:51:48Z"),
        ],
        [],
        BOT_LOGIN,
    )

    assert signal["decision"] == "CHANGES_REQUESTED"
    assert signal["source"] == "github_review"
    assert signal["review_id"] == 2
    assert driver.review_decision_outcome(signal["decision"]) == "changes_requested"


def test_changes_requested_without_actionable_comments_escalates_instead_of_polling() -> (
    None
):
    assert driver.changes_requested_without_actionable_comments(
        "CHANGES_REQUESTED", "changes_requested", []
    )
    assert not driver.changes_requested_without_actionable_comments(
        "NONE", "pending", []
    )
    assert not driver.changes_requested_without_actionable_comments(
        "CHANGES_REQUESTED", "changes_requested", [{"comment_id": 1}]
    )


def test_review_loop_does_not_redispatch_handled_comment_ids() -> None:
    comment = {
        "comment_id": 42,
        "kind": "in-diff",
        "resolved": False,
    }
    poll_result = {
        "new_comments": [],
        "actionable_comments": [comment],
    }

    assert driver.select_actionable_comments(poll_result) == [comment]
    assert driver.select_actionable_comments(poll_result, {42}) == []


def test_previous_head_approval_is_not_terminal_for_current_head() -> None:
    signal = driver.coderabbit_decision_signal(
        [_review(3, "APPROVED", "2026-05-21T09:51:46Z", commit_id="previous-sha")],
        [],
        BOT_LOGIN,
    )

    assert (
        driver.current_head_decision_outcome(
            signal,
            "current-sha",
            driver.parse_time("2026-05-21T09:50:00Z"),
        )
        is None
    )


def test_current_head_approval_is_terminal() -> None:
    signal = driver.coderabbit_decision_signal(
        [_review(3, "APPROVED", "2026-05-21T09:51:46Z", commit_id="current-sha")],
        [],
        BOT_LOGIN,
    )

    assert (
        driver.current_head_decision_outcome(
            signal,
            "current-sha",
            driver.parse_time("2026-05-21T09:50:00Z"),
        )
        == "approved"
    )


def test_summary_decision_must_follow_current_head_commit() -> None:
    body = (
        driver.SUMMARY_COMMENT_MARKER
        + "\nNo actionable comments were generated in the recent review.\n"
    )
    head_committed_at = driver.parse_time("2026-05-21T09:50:00Z")

    old_signal = driver.coderabbit_decision_signal(
        [], [_summary(10, body, "2026-05-21T09:49:59Z")], BOT_LOGIN
    )
    current_signal = driver.coderabbit_decision_signal(
        [], [_summary(11, body, "2026-05-21T09:50:01Z")], BOT_LOGIN
    )
    edited_old_summary = _summary(12, body, "2026-05-21T09:49:59Z")
    edited_old_summary["updated_at"] = "2026-05-21T09:50:02Z"
    edited_old_signal = driver.coderabbit_decision_signal(
        [], [edited_old_summary], BOT_LOGIN
    )

    assert (
        driver.current_head_decision_outcome(
            old_signal, "current-sha", head_committed_at
        )
        is None
    )
    assert (
        driver.current_head_decision_outcome(
            current_signal, "current-sha", head_committed_at
        )
        == "approved"
    )
    assert (
        driver.current_head_decision_outcome(
            edited_old_signal, "current-sha", head_committed_at
        )
        is None
    )


def test_summary_comment_approved_marker_is_terminal_fallback() -> None:
    body = (
        driver.SUMMARY_COMMENT_MARKER
        + "\nNo actionable comments were generated in the recent review.\n"
    )
    signal = driver.coderabbit_decision_signal(
        [
            _review(1, "CHANGES_REQUESTED", "2026-05-21T09:38:26Z"),
            _review(2, "COMMENTED", "2026-05-21T09:51:48Z"),
        ],
        [_summary(10, body, "2026-05-21T09:51:50Z")],
        BOT_LOGIN,
    )

    assert signal["decision"] == "APPROVED"
    assert signal["source"] == "summary_comment"
    assert signal["comment_id"] == 10
    assert driver.review_decision_outcome(signal["decision"]) == "approved"


def test_review_comment_uses_owning_review_commit_for_head_scope() -> None:
    repo = driver.Repo(owner="nestharus", name="agent-core")
    records = driver.collect_comment_records(
        repo,
        198,
        [
            _review(
                7,
                "CHANGES_REQUESTED",
                "2026-05-21T09:51:00Z",
                commit_id="previous-sha",
            )
        ],
        [
            {
                "id": 42,
                "pull_request_review_id": 7,
                "body": "old finding",
                "commit_id": "current-sha",
                "position": 1,
                "user": {"login": BOT_LOGIN},
            }
        ],
        [],
        {},
        BOT_LOGIN,
    )

    assert records[0]["metadata"]["commit_id"] == "current-sha"
    assert records[0]["metadata"]["review_commit_id"] == "previous-sha"
    assert not driver.comment_matches_review_head(records[0]["metadata"], "current-sha")
    assert driver.comment_matches_review_head(records[0]["metadata"], None)


def test_current_head_evidence_is_filtered_before_terminal_signal_selection() -> None:
    summary_body = (
        driver.SUMMARY_COMMENT_MARKER
        + "\nNo actionable comments were generated in the recent review.\n"
    )
    reviews, comments = driver.current_head_review_evidence(
        [
            _review(1, "APPROVED", "2026-05-21T09:51:00Z"),
            _review(
                2,
                "CHANGES_REQUESTED",
                "2026-05-21T09:53:00Z",
                commit_id="previous-sha",
            ),
        ],
        [
            _summary(10, summary_body, "2026-05-21T09:49:00Z"),
        ],
        "head-sha",
        driver.parse_time("2026-05-21T09:50:00Z"),
    )

    signal = driver.coderabbit_decision_signal(reviews, comments, BOT_LOGIN)

    assert signal["decision"] == "APPROVED"
    assert signal["review_id"] == 1
    assert comments == []


def test_old_summary_edit_does_not_become_current_head_evidence() -> None:
    summary_body = driver.SUMMARY_COMMENT_MARKER + "\nActionable comments posted: 1\n"
    summary = _summary(10, summary_body, "2026-05-21T09:49:00Z")
    summary["updated_at"] = "2026-05-21T09:51:00Z"

    _, comments = driver.current_head_review_evidence(
        [],
        [summary],
        "head-sha",
        driver.parse_time("2026-05-21T09:50:00Z"),
    )

    assert comments == []


def test_initial_trigger_auto_skips_when_terminal_review_exists(monkeypatch) -> None:
    repo = driver.Repo(owner="nestharus", name="agent-runner")

    def fake_gh_paginated_array(endpoint: str) -> list[dict]:
        if endpoint.endswith("/reviews"):
            return [_review(3, "APPROVED", "2026-05-21T09:51:46Z")]
        if endpoint.endswith("/issues/130/comments"):
            return []
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    monkeypatch.setattr(driver, "gh_paginated_array", fake_gh_paginated_array)
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)

    decision = driver.initial_trigger_decision(
        repo,
        130,
        "incremental",
        "auto",
        "head-sha",
        driver.parse_time("2026-05-21T09:50:00Z"),
    )

    assert decision["trigger"] is False
    assert decision["outcome"] == "approved"
    assert decision["review_decision"] == "APPROVED"


def test_initial_trigger_auto_does_not_skip_previous_head_approval(monkeypatch) -> None:
    repo = driver.Repo(owner="nestharus", name="agent-runner")

    def fake_gh_paginated_array(endpoint: str) -> list[dict]:
        if endpoint.endswith("/reviews"):
            return [
                _review(
                    3,
                    "APPROVED",
                    "2026-05-21T09:51:46Z",
                    commit_id="previous-sha",
                )
            ]
        if endpoint.endswith("/issues/130/comments"):
            return []
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    monkeypatch.setattr(driver, "gh_paginated_array", fake_gh_paginated_array)
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)

    decision = driver.initial_trigger_decision(
        repo,
        130,
        "incremental",
        "auto",
        "current-sha",
        driver.parse_time("2026-05-21T09:50:00Z"),
    )

    assert decision["trigger"] is True
    assert (
        decision["reason"] == "initial-trigger-policy:auto:no-pending-trigger-detected"
    )


def test_initial_trigger_selects_current_head_terminal_review_before_newer_stale_review(
    monkeypatch,
) -> None:
    repo = driver.Repo(owner="nestharus", name="agent-runner")

    def fake_gh_paginated_array(endpoint: str) -> list[dict]:
        if endpoint.endswith("/reviews"):
            return [
                _review(3, "APPROVED", "2026-05-21T09:51:46Z"),
                _review(
                    4,
                    "CHANGES_REQUESTED",
                    "2026-05-21T09:52:46Z",
                    commit_id="previous-sha",
                ),
            ]
        if endpoint.endswith("/issues/130/comments"):
            return []
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    monkeypatch.setattr(driver, "gh_paginated_array", fake_gh_paginated_array)
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)

    decision = driver.initial_trigger_decision(
        repo,
        130,
        "incremental",
        "auto",
        "head-sha",
        driver.parse_time("2026-05-21T09:50:00Z"),
    )

    assert decision["trigger"] is False
    assert decision["outcome"] == "approved"
    assert decision["review_decision"] == "APPROVED"


def test_initial_trigger_ignores_newer_stale_review_when_ack_is_pending(
    monkeypatch,
) -> None:
    repo = driver.Repo(owner="nestharus", name="agent-runner")
    ack = _summary(
        10,
        _ack_body("Action performed", "Review finished."),
        "2026-05-21T09:51:00Z",
    )

    def fake_gh_paginated_array(endpoint: str) -> list[dict]:
        if endpoint.endswith("/reviews"):
            return [
                _review(
                    3,
                    "COMMENTED",
                    "2026-05-21T09:52:00Z",
                    commit_id="previous-sha",
                )
            ]
        if endpoint.endswith("/issues/130/comments"):
            return [ack]
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    monkeypatch.setattr(driver, "gh_paginated_array", fake_gh_paginated_array)
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)

    decision = driver.initial_trigger_decision(
        repo,
        130,
        "incremental",
        "auto",
        "head-sha",
        driver.parse_time("2026-05-21T09:50:00Z"),
    )

    assert decision["trigger"] is False
    assert (
        decision["reason"]
        == "initial-trigger-policy:auto:pending-ack-newer-than-latest-review"
    )
    assert decision["latest_review_at"] is None


def test_loop_cadence_ignores_standalone_poll_timestamp(monkeypatch, tmp_path) -> None:
    repo = driver.Repo(owner="nestharus", name="agent-runner")
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(
        repo,
        130,
        {
            "last_polled_at": driver.utc_now(),
            "seen_comment_hashes": {},
            "comment_status": {},
        },
    )

    cadence = driver.wait_for_loop_poll_cadence(repo, 130, 300)

    assert cadence["waited_seconds"] == 0
    assert cadence["last_poll_at"] is None


def test_dispatch_comment_agent_backfills_missing_fix_commit_sha(
    monkeypatch, tmp_path
) -> None:
    iteration_dir = tmp_path / "iteration"
    template_path = tmp_path / "fix-prompt.md"
    template_path.write_text("Fix comment $comment_id", encoding="utf-8")
    raw_outcome = {
        "comment_id": 123,
        "outcome": "fixed",
        "commit_sha": None,
        "reply_body_file": None,
        "rationale": "Applied the focused fix.",
        "files_touched": ["tools/example.py"],
        "review_provided_value": True,
    }
    monkeypatch.setattr(
        driver.subprocess,
        "run",
        lambda *args, **kwargs: driver.subprocess.CompletedProcess(
            args=[], returncode=0, stdout=driver.json.dumps(raw_outcome)
        ),
    )
    monkeypatch.setattr(driver, "git_dirty_paths", lambda *args: [])
    heads = iter(["head-before", "agent-commit-sha"])
    monkeypatch.setattr(driver, "git_head", lambda *args: next(heads))

    outcome = driver.dispatch_comment_agent(
        comment={"comment_id": 123, "file_path": "/tmp/comment.md"},
        repo=driver.Repo(owner="nestharus", name="agent-core"),
        pr_num=198,
        pr_branch="fix/review",
        worktree_path=tmp_path,
        iteration_dir=iteration_dir,
        template_path=template_path,
        fixer_agent=None,
        fixer_model="gpt-high",
    )

    outcome_path = iteration_dir / "agent-123.prompt.outcome.json"
    persisted = driver.json.loads(outcome_path.read_text(encoding="utf-8"))
    assert outcome["commit_sha"] == "agent-commit-sha"
    assert persisted["commit_sha"] == "agent-commit-sha"


def test_dispatch_comment_agent_rejects_fix_without_new_commit(
    monkeypatch, tmp_path
) -> None:
    iteration_dir = tmp_path / "iteration"
    template_path = tmp_path / "fix-prompt.md"
    template_path.write_text("Fix comment $comment_id", encoding="utf-8")
    raw_outcome = {
        "comment_id": 123,
        "outcome": "fixed",
        "commit_sha": None,
        "reply_body_file": None,
        "rationale": "Applied the focused fix.",
        "files_touched": ["tools/example.py"],
        "review_provided_value": True,
    }
    monkeypatch.setattr(
        driver.subprocess,
        "run",
        lambda *args, **kwargs: driver.subprocess.CompletedProcess(
            args=[], returncode=0, stdout=driver.json.dumps(raw_outcome)
        ),
    )
    monkeypatch.setattr(driver, "git_dirty_paths", lambda *args: [])
    monkeypatch.setattr(driver, "git_head", lambda *args: "unchanged-head")

    with pytest.raises(driver.DriverError, match="produced no commit"):
        driver.dispatch_comment_agent(
            comment={"comment_id": 123, "file_path": "/tmp/comment.md"},
            repo=driver.Repo(owner="nestharus", name="agent-core"),
            pr_num=198,
            pr_branch="fix/review",
            worktree_path=tmp_path,
            iteration_dir=iteration_dir,
            template_path=template_path,
            fixer_agent=None,
            fixer_model="gpt-high",
        )


def test_validated_pr_head_identity_accepts_pushed_head(monkeypatch, tmp_path) -> None:
    metadata = {"headRefName": "fix/review", "headRefOid": "new-sha"}
    monkeypatch.setattr(
        driver,
        "git_output",
        lambda *args: "2026-07-30T10:10:56-07:00",
    )

    branch, head_oid, committed_at = driver.validated_pr_head_identity(
        metadata,
        driver.Repo(owner="nestharus", name="agent-core"),
        198,
        tmp_path,
        expected_branch="fix/review",
        expected_oid="new-sha",
    )

    assert branch == "fix/review"
    assert head_oid == "new-sha"
    assert committed_at == driver.parse_time("2026-07-30T10:10:56-07:00")


def test_validated_pr_head_identity_caps_future_commit_time(
    monkeypatch, tmp_path
) -> None:
    metadata = {"headRefName": "fix/review", "headRefOid": "new-sha"}
    observed_at = driver.parse_time("2026-07-30T18:00:00Z")
    monkeypatch.setattr(driver, "utc_now_dt", lambda: observed_at)
    monkeypatch.setattr(
        driver,
        "git_output",
        lambda *args: "2026-07-31T18:00:00Z",
    )

    _, _, evidence_cutoff = driver.validated_pr_head_identity(
        metadata,
        driver.Repo(owner="nestharus", name="agent-core"),
        198,
        tmp_path,
        expected_branch="fix/review",
        expected_oid="new-sha",
    )

    assert evidence_cutoff == observed_at


def test_validated_pr_head_identity_rejects_stale_provider_head(
    monkeypatch, tmp_path
) -> None:
    metadata = {"headRefName": "fix/review", "headRefOid": "old-sha"}

    with pytest.raises(driver.DriverError, match="did not match pushed commit"):
        driver.validated_pr_head_identity(
            metadata,
            driver.Repo(owner="nestharus", name="agent-core"),
            198,
            tmp_path,
            expected_branch="fix/review",
            expected_oid="new-sha",
        )


def test_poll_revalidation_rejects_external_head_change(monkeypatch, tmp_path) -> None:
    repo = driver.Repo(owner="nestharus", name="agent-core")
    monkeypatch.setattr(
        driver,
        "pr_metadata",
        lambda *args: {
            "headRefName": "fix/review",
            "headRefOid": "external-sha",
        },
    )
    monkeypatch.setattr(driver, "git_head", lambda *args: "local-sha")
    monkeypatch.setattr(driver, "remote_branch_oid", lambda *args: "local-sha")

    with pytest.raises(driver.DriverError, match="did not match pushed commit"):
        driver.revalidate_current_pr_head(
            repo,
            198,
            tmp_path,
            "fix/review",
        )


def test_poll_aborts_when_external_head_changes_during_poll(
    monkeypatch, tmp_path
) -> None:
    repo = driver.Repo(owner="nestharus", name="agent-core")
    metadata = iter(
        [
            {"headRefName": "fix/review", "headRefOid": "local-sha"},
            {"headRefName": "fix/review", "headRefOid": "external-sha"},
        ]
    )
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: next(metadata))
    monkeypatch.setattr(driver, "git_head", lambda *args: "local-sha")
    monkeypatch.setattr(driver, "remote_branch_oid", lambda *args: "local-sha")
    monkeypatch.setattr(
        driver,
        "git_output",
        lambda *args: "2026-07-30T10:10:56-07:00",
    )
    monkeypatch.setattr(driver, "poll", lambda *args: {"outcome": "approved"})

    with pytest.raises(driver.DriverError, match="did not match pushed commit"):
        driver.poll_current_pr_head(
            repo,
            198,
            tmp_path,
            "fix/review",
        )


def test_wait_for_provider_pr_head_allows_metadata_propagation(
    monkeypatch, tmp_path
) -> None:
    repo = driver.Repo(owner="nestharus", name="agent-core")
    metadata = iter(
        [
            {"headRefName": "fix/review", "headRefOid": "old-sha"},
            {"headRefName": "fix/review", "headRefOid": "new-sha"},
        ]
    )
    sleeps = []
    monkeypatch.setattr(driver, "remote_branch_oid", lambda *args: "new-sha")
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: next(metadata))
    monkeypatch.setattr(
        driver,
        "git_output",
        lambda *args: "2026-07-30T10:10:56-07:00",
    )
    monkeypatch.setattr(driver.time, "sleep", sleeps.append)

    head_oid, _ = driver.wait_for_provider_pr_head(
        repo,
        198,
        tmp_path,
        "fix/review",
        "new-sha",
    )

    assert head_oid == "new-sha"
    assert sleeps == [driver.DEFAULT_POLL_INTERVAL_SECONDS]


def test_wait_for_provider_pr_head_rejects_remote_branch_change(
    monkeypatch, tmp_path
) -> None:
    repo = driver.Repo(owner="nestharus", name="agent-core")
    monkeypatch.setattr(driver, "remote_branch_oid", lambda *args: "external-sha")

    with pytest.raises(driver.DriverError, match="remote PR branch changed after push"):
        driver.wait_for_provider_pr_head(
            repo,
            198,
            tmp_path,
            "fix/review",
            "new-sha",
        )
