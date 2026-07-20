"""Tests for CodeRabbit review verdict extraction."""

from __future__ import annotations

import json
import pathlib
import sys
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace

import pytest


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


def _comment(comment_id: int) -> dict:
    return {
        "comment_id": comment_id,
        "kind": "in-diff",
        "resolved": False,
        "file_path": f"/fake/comment-{comment_id}.md",
        "code_path": "src/example.py",
        "code_line": comment_id,
        "review_id": 20,
        "thread_parent": None,
    }


def _poll_result(
    decision: str,
    actionable_comments: list[dict] | None = None,
    *,
    new_comments: list[dict] | None = None,
) -> dict:
    actionable_comments = actionable_comments or []
    outcome = driver.review_decision_outcome(decision)
    return {
        "review_decision": decision,
        "terminal": outcome is not None,
        "outcome": outcome,
        "review_decision_source": "github_review",
        "new_comments": actionable_comments if new_comments is None else new_comments,
        "actionable_comments": actionable_comments,
        "resolved_since_last_poll": [],
        "bot_login": BOT_LOGIN,
    }


def _fixer_outcome(comment_id: int, outcome: str, provided_value: bool) -> dict:
    return {
        "comment_id": comment_id,
        "outcome": outcome,
        "commit_sha": "abc123" if outcome in driver.FIX_OUTCOMES else None,
        "reply_body_file": f"/fake/reply-{comment_id}.md" if outcome in driver.REPLY_OUTCOMES else None,
        "rationale": f"fixture outcome for {comment_id}",
        "files_touched": ["src/example.py"] if outcome in driver.FIX_OUTCOMES else [],
        "review_provided_value": provided_value,
    }


class ReviewLoopHarness:
    def __init__(self, monkeypatch, tmp_path: pathlib.Path) -> None:
        self.events: list[str] = []
        self.poll_results: list[dict] = []
        self.fixer_outcomes: list[dict] = []
        self.dirty_paths: list[str] = []
        self.dispatch_error: driver.DriverError | None = None
        self.stdout = StringIO()
        self.worktree_path = tmp_path / "worktree"
        self.worktree_path.mkdir()
        self.args = SimpleNamespace(
            repo="example/repo",
            pr_num=7,
            label=driver.DEFAULT_LABEL,
            worktree_path=str(self.worktree_path),
            fixer_agent="fake-fixer",
            fixer_model=None,
            template=str(tmp_path / "template.md"),
            poll_interval_seconds=driver.DEFAULT_REVIEW_LOOP_POLL_INTERVAL_SECONDS,
            mode="incremental",
            initial_trigger="skip",
        )

        monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path / "cache")
        monkeypatch.setattr(driver, "repo_label_enabled", lambda *args: (True, {"enabled": True}))
        monkeypatch.setattr(
            driver,
            "pr_metadata",
            lambda *args: {"headRefName": "feature", "headRefOid": "abc123"},
        )
        monkeypatch.setattr(driver, "ensure_worktree_branch", lambda *args: None)
        monkeypatch.setattr(
            driver,
            "initial_trigger_decision",
            lambda *args: {"trigger": False, "reason": "fixture-skip"},
        )
        monkeypatch.setattr(
            driver,
            "wait_for_loop_poll_cadence",
            lambda *args: {"waited_seconds": 0, "last_poll_at": None},
        )
        monkeypatch.setattr(driver, "mark_loop_poll", lambda *args: None)
        monkeypatch.setattr(driver, "git_dirty_paths", self._dirty_paths)
        monkeypatch.setattr(driver, "poll", self._poll)
        monkeypatch.setattr(driver, "dispatch_comment_agent", self._dispatch)
        monkeypatch.setattr(driver, "push_branch", self._push)
        monkeypatch.setattr(driver, "post_reply", self._reply)
        monkeypatch.setattr(driver, "trigger_review", self._trigger)

    def _poll(self, *args) -> dict:
        self.events.append("poll")
        return self.poll_results.pop(0)

    def _dispatch(self, **kwargs) -> dict:
        self.events.append(f"dispatch:{kwargs['comment']['comment_id']}")
        if self.dispatch_error is not None:
            raise self.dispatch_error
        return self.fixer_outcomes.pop(0)

    def _dirty_paths(self, *args) -> list[str]:
        self.events.append("dirty-check")
        return self.dirty_paths

    def _push(self, *args) -> dict:
        self.events.append("push")
        return {"pushed": True, "branch": "feature", "head_sha": "abc123"}

    def _reply(self, *args) -> dict:
        self.events.append(f"reply:{args[2]}")
        return {"posted": True, "comment_id": args[2]}

    def _trigger(self, *args) -> dict:
        self.events.append("trigger")
        return {"mode": "incremental", "triggered": True}

    def run(self, poll_results: list[dict], fixer_outcomes: list[dict] | None = None) -> tuple[int, dict]:
        self.poll_results = list(poll_results)
        self.fixer_outcomes = list(fixer_outcomes or [])
        self.stdout = StringIO()
        with redirect_stdout(self.stdout):
            exit_code = driver.command_review_loop(self.args)
        self.events.append("result")
        return exit_code, json.loads(self.stdout.getvalue())


@pytest.fixture
def review_loop_harness(monkeypatch, tmp_path) -> ReviewLoopHarness:
    return ReviewLoopHarness(monkeypatch, tmp_path)


def _run_all_no_value_scenario(harness: ReviewLoopHarness) -> tuple[int, dict]:
    comments = [_comment(101), _comment(102), _comment(103)]
    outcomes = [_fixer_outcome(comment["comment_id"], "rejected", False) for comment in comments]
    return harness.run(
        [_poll_result("CHANGES_REQUESTED", comments, new_comments=[])],
        outcomes,
    )


def _run_valuable_then_approved_scenario(harness: ReviewLoopHarness) -> tuple[int, dict, dict]:
    comment = _comment(201)
    outcome = _fixer_outcome(201, "fixed_and_replied", True)
    exit_code, result = harness.run(
        [_poll_result("CHANGES_REQUESTED", [comment]), _poll_result("APPROVED")],
        [outcome],
    )
    return exit_code, result, outcome


def _run_caller_decision_scenario(harness: ReviewLoopHarness) -> tuple[int, dict, list[dict]]:
    comments = [_comment(301), _comment(302)]
    outcomes = [
        _fixer_outcome(301, "rejected", True),
        _fixer_outcome(302, "deferred", True),
    ]
    exit_code, result = harness.run([_poll_result("CHANGES_REQUESTED", comments)], outcomes)
    return exit_code, result, outcomes


def _run_approval_scenario(harness: ReviewLoopHarness) -> tuple[int, dict]:
    return harness.run([_poll_result("APPROVED")])


def _run_dirty_worktree_scenario(harness: ReviewLoopHarness) -> tuple[int, dict]:
    harness.dirty_paths = ["src/dirty.py"]
    return harness.run([_poll_result("CHANGES_REQUESTED", [_comment(401)], new_comments=[])])


def _run_fixer_failure_scenario(harness: ReviewLoopHarness) -> tuple[int, dict]:
    harness.dispatch_error = driver.DriverError("fixture fixer failed")
    return harness.run([_poll_result("CHANGES_REQUESTED", [_comment(402)], new_comments=[])])


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


def test_review_loop_dispatches_changes_requested_actionable_comments_before_convergence(
    review_loop_harness,
) -> None:
    exit_code, result = _run_all_no_value_scenario(review_loop_harness)

    assert review_loop_harness.events == [
        "poll",
        "dirty-check",
        "dispatch:101",
        "dispatch:102",
        "dispatch:103",
        "result",
    ]
    assert result["iterations"][0]["new_comments"] == []
    assert [comment["comment_id"] for comment in result["iterations"][0]["actionable_comments"]] == [
        101,
        102,
        103,
    ]
    assert [outcome["comment_id"] for outcome in result["iterations"][0]["outcomes"]] == [101, 102, 103]
    assert exit_code == 0
    assert result["terminal"] is True
    assert result["terminal_reason"] == "no_value_provided"
    assert result["terminal_reason"] != "changes_requested"


def test_review_loop_retriggers_after_valuable_fixer_outcomes_then_converges_on_approval(
    review_loop_harness,
) -> None:
    exit_code, result, outcome = _run_valuable_then_approved_scenario(review_loop_harness)

    assert review_loop_harness.events == [
        "poll",
        "dirty-check",
        "dispatch:201",
        "push",
        "reply:201",
        "trigger",
        "poll",
        "result",
    ]
    assert result["iterations"][0]["outcomes"] == [outcome]
    assert result["iterations"][0]["push_result"]["pushed"] is True
    assert result["iterations"][0]["reply_results"] == [{"posted": True, "comment_id": 201}]
    assert result["iterations"][0]["trigger_result"]["mode"] == "incremental"
    assert exit_code == 0
    assert result["terminal_reason"] == "approved"
    assert result["review_decision"] == "APPROVED"


def test_review_loop_returns_caller_decision_for_valuable_rejected_and_deferred_outcomes(
    review_loop_harness,
) -> None:
    exit_code, result, outcomes = _run_caller_decision_scenario(review_loop_harness)

    assert review_loop_harness.events == [
        "poll",
        "dirty-check",
        "dispatch:301",
        "dispatch:302",
        "result",
    ]
    assert exit_code == 3
    assert result["terminal"] is False
    assert result["terminal_reason"] is None
    assert result["needs_caller_decision"] is True
    assert result["iterations"][0]["outcomes"] == outcomes
    assert result["iterations"][0]["caller_decision_outcomes"] == outcomes


def test_review_loop_approved_decision_converges_without_dispatch(review_loop_harness) -> None:
    exit_code, result = _run_approval_scenario(review_loop_harness)

    assert review_loop_harness.events == ["poll", "result"]
    assert exit_code == 0
    assert result["terminal"] is True
    assert result["terminal_reason"] == "approved"
    assert result["iterations"][0]["outcomes"] == []


def test_review_loop_refuses_dirty_worktree_before_changes_requested_dispatch(
    review_loop_harness,
) -> None:
    with pytest.raises(driver.DriverError, match="worktree is dirty before comment dispatch") as error:
        _run_dirty_worktree_scenario(review_loop_harness)

    assert error.value.exit_code == 2
    assert review_loop_harness.events == ["poll", "dirty-check"]
    assert review_loop_harness.stdout.getvalue() == ""


def test_review_loop_propagates_changes_requested_fixer_failure(review_loop_harness) -> None:
    with pytest.raises(driver.DriverError, match="fixture fixer failed") as error:
        _run_fixer_failure_scenario(review_loop_harness)

    assert error.value.exit_code == 2
    assert review_loop_harness.events == ["poll", "dirty-check", "dispatch:402"]
    assert review_loop_harness.stdout.getvalue() == ""
