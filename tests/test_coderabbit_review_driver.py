"""Tests for CodeRabbit review verdict extraction."""

from __future__ import annotations

import pathlib
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import coderabbit_review_driver as driver  # noqa: E402


BOT_LOGIN = "coderabbitai[bot]"


def _review(review_id: int, state: str, submitted_at: str, login: str = BOT_LOGIN) -> dict:
    return {
        "id": review_id,
        "state": state,
        "submitted_at": submitted_at,
        "user": {"login": login},
    }


def _summary(comment_id: int, body: str, updated_at: str, login: str = BOT_LOGIN) -> dict:
    return {
        "id": comment_id,
        "body": body,
        "created_at": updated_at,
        "updated_at": updated_at,
        "user": {"login": login},
    }


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


def test_changes_requested_review_is_terminal_even_when_later_commented_review_exists() -> None:
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

    decision = driver.initial_trigger_decision(repo, 130, "incremental", "auto")

    assert decision["trigger"] is False
    assert decision["outcome"] == "approved"
    assert decision["review_decision"] == "APPROVED"


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
