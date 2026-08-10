"""Tests for generation-aware CodeRabbit PR review handling."""

from __future__ import annotations

import pathlib
import sys

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import coderabbit_review_driver as driver  # noqa: E402


BOT_LOGIN = "coderabbitai[bot]"
REPO = driver.Repo(owner="nestharus", name="agent-core")


@pytest.fixture(autouse=True)
def authenticated_actor(monkeypatch) -> None:
    monkeypatch.setattr(driver, "authenticated_actor_login", lambda: "nestharus")


def _review(
    review_id: int,
    state: str,
    submitted_at: str = "2026-08-07T10:01:00Z",
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


def _issue_comment(
    comment_id: int,
    body: str,
    observed_at: str = "2026-08-07T10:01:00Z",
    login: str = BOT_LOGIN,
) -> dict:
    return {
        "id": comment_id,
        "body": body,
        "created_at": observed_at,
        "updated_at": observed_at,
        "html_url": f"https://github.test/comments/{comment_id}",
        "user": {"login": login},
    }


def _generation(
    *,
    head_oid: str = "head-sha",
    baseline_review_ids: list[int] | None = None,
    baseline_issue_comment_ids: list[int] | None = None,
) -> dict:
    return {
        "schema": driver.GENERATION_SCHEMA,
        "generation_id": 100,
        "result": "WAITING_FOR_REVIEW",
        "repo": REPO.slug,
        "pr_num": 198,
        "mode": "incremental",
        "baseline_review_ids": baseline_review_ids or [1],
        "baseline_issue_comment_ids": baseline_issue_comment_ids or [90, 100],
        "trigger_comment_id": 100,
        "triggered_at": "2026-08-07T10:00:00Z",
        "expected_head_oid": head_oid,
        "current_head_oid": head_oid,
        "accepted_review_id": None,
        "accepted_review_state": None,
        "accepted_review_commit_id": None,
        "rate_limit": None,
        "capacity_query": None,
        "next_permitted_action": "poll",
        "blocked_reason": None,
    }


def _review_loop_args(tmp_path: pathlib.Path) -> driver.argparse.Namespace:
    return driver.argparse.Namespace(
        repo=REPO.slug,
        pr_num=198,
        label=driver.DEFAULT_LABEL,
        worktree_path=str(tmp_path),
        fixer_agent=None,
        fixer_model="gpt-high",
        template=str(driver.DEFAULT_FIX_BRIEF_TEMPLATE),
        poll_interval_seconds=driver.DEFAULT_REVIEW_LOOP_POLL_INTERVAL_SECONDS,
        initial_trigger="auto",
        mode="incremental",
    )


@pytest.mark.parametrize("first_head", ["old-head", "head-sha"])
def test_new_changes_requested_review_completes_changed_and_unchanged_head_generations(
    first_head: str,
) -> None:
    result = driver.classify_review_generation(
        _generation(),
        "head-sha",
        [
            _review(1, "CHANGES_REQUESTED", commit_id=first_head),
            _review(2, "CHANGES_REQUESTED", commit_id="head-sha"),
        ],
        [],
        BOT_LOGIN,
    )

    assert result["result"] == "REVIEW_COMPLETED"
    assert result["accepted_review_id"] == 2
    assert result["accepted_review_state"] == "CHANGES_REQUESTED"
    assert result["accepted_review_commit_id"] == "head-sha"


def test_stale_same_head_review_in_trigger_baseline_does_not_complete() -> None:
    result = driver.classify_review_generation(
        _generation(),
        "head-sha",
        [_review(1, "APPROVED")],
        [],
        BOT_LOGIN,
    )

    assert result["result"] == "WAITING_FOR_REVIEW"
    assert result["accepted_review_id"] is None


def test_out_of_baseline_review_submitted_before_trigger_does_not_complete() -> None:
    result = driver.classify_review_generation(
        _generation(),
        "head-sha",
        [
            _review(1, "CHANGES_REQUESTED"),
            _review(
                2,
                "CHANGES_REQUESTED",
                submitted_at="2026-08-07T09:59:59Z",
            ),
        ],
        [],
        BOT_LOGIN,
    )

    assert result["result"] == "WAITING_FOR_REVIEW"
    assert result["accepted_review_id"] is None


def test_new_wrong_head_review_does_not_complete() -> None:
    result = driver.classify_review_generation(
        _generation(),
        "head-sha",
        [
            _review(1, "CHANGES_REQUESTED"),
            _review(2, "APPROVED", commit_id="wrong"),
        ],
        [],
        BOT_LOGIN,
    )

    assert result["result"] == "WAITING_FOR_REVIEW"


def test_acknowledgements_and_summary_comments_do_not_complete() -> None:
    comments = [
        _issue_comment(101, "<summary>Action performed</summary>\nReview triggered."),
        _issue_comment(102, "<summary>Action performed</summary>\nReview finished."),
        _issue_comment(
            103,
            driver.SUMMARY_COMMENT_MARKER
            + "\nNo actionable comments were generated in the recent review.",
        ),
    ]

    result = driver.classify_review_generation(
        _generation(),
        "head-sha",
        [_review(1, "CHANGES_REQUESTED")],
        comments,
        BOT_LOGIN,
    )

    assert result["result"] == "WAITING_FOR_REVIEW"


def test_aggregate_approval_without_active_generation_is_informational(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        driver,
        "gh_paginated_array",
        lambda endpoint: (
            [_review(7, "APPROVED")] if endpoint.endswith("/reviews") else []
        ),
    )
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(driver, "graphql_review_threads", lambda *args: {})
    monkeypatch.setattr(driver, "load_state", lambda *args: {})
    monkeypatch.setattr(driver, "save_state", lambda *args: None)
    monkeypatch.setattr(driver, "save_bot_login", lambda *args: None)
    monkeypatch.setattr(driver, "write_comment_file", lambda *args: None)

    result = driver.poll(REPO, 198)

    assert result["aggregate_review_decision"] == "APPROVED"
    assert result["review_decision"] == "NONE"
    assert result["review_completed"] is False
    assert result["generation"]["result"] == "BLOCKED"


def test_poll_projects_generation_and_findings_from_one_provider_snapshot(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": _generation()})
    review_calls = 0

    def fake_paginated(endpoint: str) -> list[dict]:
        nonlocal review_calls
        if endpoint.endswith("/reviews"):
            review_calls += 1
            if review_calls == 1:
                return [_review(1, "CHANGES_REQUESTED")]
            return [
                _review(1, "CHANGES_REQUESTED"),
                _review(2, "CHANGES_REQUESTED"),
            ]
        return []

    monkeypatch.setattr(driver, "gh_paginated_array", fake_paginated)
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(driver, "graphql_review_threads", lambda *args: {})
    monkeypatch.setattr(driver, "save_bot_login", lambda *args: None)
    monkeypatch.setattr(driver, "write_comment_file", lambda *args: None)
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: {"headRefOid": "head-sha"})

    result = driver.poll(REPO, 198, head_oid="head-sha")

    assert review_calls == 1
    assert result["generation"]["result"] == "WAITING_FOR_REVIEW"


def test_poll_classifies_generation_against_provider_head_not_finding_scope(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": _generation(head_oid="head-a")})
    monkeypatch.setattr(
        driver,
        "gh_paginated_array",
        lambda endpoint: (
            [_review(2, "APPROVED", commit_id="head-a")]
            if endpoint.endswith("/reviews")
            else []
        ),
    )
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(driver, "graphql_review_threads", lambda *args: {})
    monkeypatch.setattr(driver, "save_bot_login", lambda *args: None)
    monkeypatch.setattr(driver, "write_comment_file", lambda *args: None)
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: {"headRefOid": "head-b"})

    result = driver.poll(REPO, 198, head_oid="head-a")

    assert result["generation"]["result"] == "BLOCKED"
    assert result["generation"]["current_head_oid"] == "head-b"
    assert result["generation"]["blocked_reason"] == (
        "PR head changed during review generation"
    )


def test_post_trigger_rate_limit_comment_is_generation_terminal() -> None:
    result = driver.classify_review_generation(
        _generation(),
        "head-sha",
        [_review(1, "APPROVED", commit_id="old-head")],
        [_issue_comment(101, "Review rate limited: couldn't start this review.")],
        BOT_LOGIN,
    )

    assert result["result"] == "RATE_LIMITED_NO_REVIEW"
    assert result["accepted_review_id"] is None
    assert result["rate_limit"] == {
        "comment_id": 101,
        "comment_url": "https://github.test/comments/101",
        "observed_at": "2026-08-07T10:01:00Z",
        "trigger_comment_id": 100,
        "expected_head_oid": "head-sha",
        "check_evidence": [],
    }


def test_ambiguous_rate_limit_comments_block_the_generation() -> None:
    result = driver.classify_review_generation(
        _generation(),
        "head-sha",
        [],
        [
            _issue_comment(101, "Review rate limited: couldn't start this review."),
            _issue_comment(102, "Review rate limited: review limit reached."),
        ],
        BOT_LOGIN,
    )

    assert result["result"] == "BLOCKED"
    assert result["blocked_reason"] == (
        "ambiguous rate-limit evidence for trigger generation"
    )
    assert result["next_permitted_action"] == "inspect_rate_limit_comments"


def test_stale_rate_limit_comment_cannot_classify_later_generation() -> None:
    result = driver.classify_review_generation(
        _generation(baseline_issue_comment_ids=[90, 99, 100]),
        "head-sha",
        [],
        [_issue_comment(99, "Review rate limited: review limit reached.")],
        BOT_LOGIN,
    )

    assert result["result"] == "WAITING_FOR_REVIEW"


def test_passing_rate_limited_check_alone_is_not_review_evidence(
    monkeypatch, tmp_path
) -> None:
    passing_check = [
        {
            "kind": "check_run",
            "id": 500,
            "name": "Review rate limited",
            "status": "completed",
            "conclusion": "success",
        }
    ]
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": _generation()})
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: {"headRefOid": "head-sha"})
    monkeypatch.setattr(
        driver,
        "gh_paginated_array",
        lambda endpoint: (
            [_review(1, "APPROVED")] if endpoint.endswith("/reviews") else []
        ),
    )
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(
        driver,
        "rate_limit_check_evidence",
        lambda *args: passing_check,
    )

    result = driver.poll_review_generation(REPO, 198)

    assert result["result"] == "WAITING_FOR_REVIEW"
    assert result.get("rate_limit") is None


def test_bound_rate_limit_comment_persists_matching_check_identity(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": _generation()})
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: {"headRefOid": "head-sha"})

    def fake_paginated(endpoint: str) -> list[dict]:
        if endpoint.endswith("/reviews"):
            return [_review(1, "APPROVED", commit_id="old-head")]
        return [_issue_comment(101, "Review rate limited: couldn't start this review.")]

    monkeypatch.setattr(driver, "gh_paginated_array", fake_paginated)
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(
        driver,
        "gh_json",
        lambda args: (
            {
                "check_runs": [
                    {
                        "id": 500,
                        "name": "Review rate limited",
                        "status": "completed",
                        "conclusion": "success",
                        "html_url": "https://github.test/checks/500",
                    }
                ]
            }
            if args[-1].endswith("/check-runs")
            else {"statuses": []}
        ),
    )

    result = driver.poll_review_generation(REPO, 198)

    assert result["result"] == "RATE_LIMITED_NO_REVIEW"
    assert result["rate_limit"]["comment_id"] == 101
    assert result["rate_limit"]["check_evidence"][0]["id"] == 500
    assert result["rate_limit"]["check_evidence"][0]["conclusion"] == "success"


def test_capacity_query_binds_exact_new_response_and_exposes_provider_guidance(
    monkeypatch, tmp_path
) -> None:
    generation = _generation()
    generation["result"] = "RATE_LIMITED_NO_REVIEW"
    generation["capacity_query"] = {
        "generation_id": 200,
        "query_comment_id": 200,
        "query_comment_url": "https://github.test/comments/200",
        "queried_at": "2026-08-07T10:02:00Z",
        "baseline_issue_comment_ids": [150, 200],
        "response": None,
    }
    stale = _issue_comment(
        150,
        "Review rate limit: 0 reviews remaining. Next review available in: **old**",
        "2026-08-07T09:00:00Z",
    )
    response = _issue_comment(
        201,
        "<summary>Action performed</summary>\nReview rate limit: 2 reviews remaining. "
        "Next review available in: **15 minutes**",
        "2026-08-07T10:03:00Z",
    )
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": generation})
    monkeypatch.setenv("CODERABBIT_CAPACITY_QUERY_ATTEMPTS", "1")
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(driver, "gh_paginated_array", lambda *args: [stale, response])

    result = driver.capacity_query(REPO, 198)
    projection = result["capacity_query"]["response"]

    assert result["result"] == "RATE_LIMITED_NO_REVIEW"
    assert result["next_permitted_action"] == "trigger"
    assert projection["capacity_query_id"] == 200
    assert projection["comment_id"] == 201
    assert projection["remaining_reviews"] == 2
    assert projection["retry_guidance"] == "15 minutes"
    assert projection["capacity_available"] is True
    assert pathlib.Path(projection["response_body_path"]).is_file()


def test_capacity_query_rejects_stale_response(monkeypatch, tmp_path) -> None:
    generation = _generation()
    generation["result"] = "RATE_LIMITED_NO_REVIEW"
    generation["capacity_query"] = {
        "generation_id": 200,
        "query_comment_id": 200,
        "queried_at": "2026-08-07T10:02:00Z",
        "baseline_issue_comment_ids": [200],
        "response": None,
    }
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    monkeypatch.setattr(driver, "authenticated_actor_login", lambda: "nestharus")
    driver.save_state(REPO, 198, {"active_generation": generation})
    monkeypatch.setenv("CODERABBIT_CAPACITY_QUERY_ATTEMPTS", "1")
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(
        driver,
        "gh_paginated_array",
        lambda *args: [
            _issue_comment(
                150,
                "Review rate limit: 3 reviews remaining.",
                "2026-08-07T09:00:00Z",
            )
        ],
    )

    result = driver.capacity_query(REPO, 198)

    assert result["result"] == "BLOCKED"
    assert result["capacity_query"]["response"] is None


def test_capacity_query_rejects_ambiguous_responses(monkeypatch, tmp_path) -> None:
    generation = _generation()
    generation["result"] = "RATE_LIMITED_NO_REVIEW"
    generation["capacity_query"] = {
        "generation_id": 200,
        "query_comment_id": 200,
        "queried_at": "2026-08-07T10:02:00Z",
        "baseline_issue_comment_ids": [200],
        "response": None,
    }
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": generation})
    monkeypatch.setenv("CODERABBIT_CAPACITY_QUERY_ATTEMPTS", "1")
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(
        driver,
        "gh_paginated_array",
        lambda *args: [
            _issue_comment(
                201,
                "Review rate limit: 1 review remaining.",
                "2026-08-07T10:03:00Z",
            ),
            _issue_comment(
                202,
                "Review rate limit: 2 reviews remaining.",
                "2026-08-07T10:03:01Z",
            ),
        ],
    )

    result = driver.capacity_query(REPO, 198)

    assert result["result"] == "BLOCKED"
    assert result["blocked_reason"] == "ambiguous capacity-query response"


def test_capacity_query_posts_at_most_once_per_query_generation(
    monkeypatch, tmp_path
) -> None:
    generation = _generation()
    generation["result"] = "RATE_LIMITED_NO_REVIEW"
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": generation})
    monkeypatch.setenv("CODERABBIT_CAPACITY_QUERY_ATTEMPTS", "1")
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    posts: list[list[str]] = []
    response = _issue_comment(201, "Review rate limit: 0 reviews remaining.")
    calls = iter([[], [response]])
    monkeypatch.setattr(driver, "gh_paginated_array", lambda *args: next(calls))

    def fake_gh_json(args: list[str]) -> dict:
        persisted = driver.active_review_generation(REPO, 198)
        assert persisted["capacity_query"]["status"] == "posting"
        assert persisted["capacity_query"]["query_comment_id"] is None
        posts.append(args)
        return _issue_comment(200, driver.CAPACITY_QUERY_BODY, login="nestharus")

    monkeypatch.setattr(driver, "gh_json", fake_gh_json)

    first = driver.capacity_query(REPO, 198)
    second = driver.capacity_query(REPO, 198)

    assert len(posts) == 1
    assert first["capacity_query"]["generation_id"] == 200
    assert second["capacity_query"]["generation_id"] == 200


def test_capacity_query_reconciles_inflight_command_before_polling(
    monkeypatch, tmp_path
) -> None:
    generation = _generation()
    generation["result"] = "RATE_LIMITED_NO_REVIEW"
    generation["capacity_query"] = {
        "status": "posting",
        "generation_id": None,
        "query_comment_id": None,
        "query_comment_url": None,
        "body": driver.CAPACITY_QUERY_BODY,
        "actor_login": "nestharus",
        "started_at": "2026-08-07T10:02:00Z",
        "queried_at": None,
        "baseline_issue_comment_ids": [100],
        "response": None,
    }
    command = _issue_comment(
        200,
        driver.CAPACITY_QUERY_BODY,
        "2026-08-07T10:02:01Z",
        login="nestharus",
    )
    response = _issue_comment(
        201,
        "Review rate limit: 1 review remaining.",
        "2026-08-07T10:03:00Z",
    )
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": generation})
    monkeypatch.setenv("CODERABBIT_CAPACITY_QUERY_ATTEMPTS", "1")
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    calls = iter([[command], [response]])
    monkeypatch.setattr(driver, "gh_paginated_array", lambda *args: next(calls))
    monkeypatch.setattr(
        driver,
        "gh_json",
        lambda *args: pytest.fail("reconciled capacity query must not post again"),
    )

    result = driver.capacity_query(REPO, 198)

    assert result["capacity_query"]["status"] == "posted"
    assert result["capacity_query"]["query_comment_id"] == 200
    assert result["capacity_query"]["response"]["comment_id"] == 201


def test_ambiguous_inflight_capacity_query_blocks(monkeypatch, tmp_path) -> None:
    generation = _generation()
    generation["result"] = "RATE_LIMITED_NO_REVIEW"
    generation["capacity_query"] = {
        "status": "posting",
        "body": driver.CAPACITY_QUERY_BODY,
        "actor_login": "nestharus",
        "started_at": "2026-08-07T10:02:00Z",
        "baseline_issue_comment_ids": [100],
        "response": None,
    }
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": generation})
    monkeypatch.setattr(
        driver,
        "gh_paginated_array",
        lambda *args: [
            _issue_comment(
                200,
                driver.CAPACITY_QUERY_BODY,
                "2026-08-07T10:02:01Z",
                login="nestharus",
            ),
            _issue_comment(
                201,
                driver.CAPACITY_QUERY_BODY,
                "2026-08-07T10:02:02Z",
                login="nestharus",
            ),
        ],
    )

    result = driver.capacity_query(REPO, 198)

    assert result["result"] == "BLOCKED"
    assert result["blocked_reason"] == "ambiguous in-flight capacity-query identity"
    assert result["next_permitted_action"] == "inspect_capacity_query_comments"


def test_unobserved_inflight_capacity_query_requires_explicit_refresh(
    monkeypatch, tmp_path
) -> None:
    generation = _generation()
    generation["result"] = "RATE_LIMITED_NO_REVIEW"
    generation["capacity_query"] = {
        "status": "posting",
        "body": driver.CAPACITY_QUERY_BODY,
        "actor_login": "nestharus",
        "started_at": "2026-08-07T10:02:00Z",
        "baseline_issue_comment_ids": [100],
        "response": None,
    }
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": generation})
    monkeypatch.setattr(driver, "gh_paginated_array", lambda *args: [])
    monkeypatch.setattr(driver, "authenticated_actor_login", lambda: "nestharus")

    with pytest.raises(driver.DriverError, match="no provider identity yet"):
        driver.capacity_query(REPO, 198)

    monkeypatch.setattr(
        driver,
        "gh_json",
        lambda *args: _issue_comment(
            200, driver.CAPACITY_QUERY_BODY, login="nestharus"
        ),
    )
    monkeypatch.setenv("CODERABBIT_CAPACITY_QUERY_ATTEMPTS", "1")
    refreshed = driver.capacity_query(REPO, 198, refresh=True)

    assert refreshed["capacity_query_history"][0]["abandon_reason"] == (
        "explicit-refresh-with-no-provider-identity"
    )


def test_capacity_projection_does_not_capture_number_from_later_line() -> None:
    projection = driver.capacity_response_projection(
        _issue_comment(201, "Remaining reviews:\nUnrelated issue 99")
    )

    assert projection["remaining_reviews"] is None
    assert projection["capacity_available"] is None


def test_capacity_projection_accepts_live_next_review_wording() -> None:
    comment = _issue_comment(
        201,
        "You're currently rate limited. Your next review will be available in 29 minutes.",
    )

    assert driver.is_capacity_response_body(comment["body"]) is True
    projection = driver.capacity_response_projection(comment)
    assert projection["retry_guidance"] == "29 minutes."
    assert projection["capacity_available"] is False


def test_capacity_projection_accepts_live_available_now_wording() -> None:
    comment = _issue_comment(201, "Reviews are available now.")

    assert driver.is_capacity_response_body(comment["body"]) is True
    projection = driver.capacity_response_projection(comment)
    assert projection["capacity_available"] is True


def test_available_now_does_not_override_active_review_constraint() -> None:
    projection = driver.capacity_response_projection(
        _issue_comment(
            201,
            "Reviews are available now, but only one review at a time and a review is in progress.",
        )
    )

    assert projection["one_review_at_a_time"] is True
    assert projection["active_review"] is True
    assert projection["capacity_available"] is False


@pytest.mark.parametrize(
    ("generation", "reason"),
    [
        (_generation(), "review request is already outstanding"),
        (
            {
                **_generation(),
                "result": "RATE_LIMITED_NO_REVIEW",
                "capacity_query": {
                    "response": {
                        "capacity_available": False,
                        "remaining_reviews": 0,
                    }
                },
            },
            "CodeRabbit has not reported restored review capacity",
        ),
        (
            {
                **_generation(),
                "result": "RATE_LIMITED_NO_REVIEW",
                "capacity_query": {
                    "response": {
                        "capacity_available": False,
                        "one_review_at_a_time": True,
                        "active_review": True,
                    }
                },
            },
            "CodeRabbit has not reported restored review capacity",
        ),
        (
            {**_generation(), "result": "BLOCKED"},
            "the active review generation is blocked",
        ),
    ],
)
def test_review_trigger_is_suppressed_for_outstanding_or_unavailable_generations(
    generation: dict, reason: str
) -> None:
    assert driver.generation_suppresses_trigger(generation) == (True, reason)


def test_one_at_a_time_active_capacity_response_disallows_trigger() -> None:
    projection = driver.capacity_response_projection(
        _issue_comment(
            201,
            "Review rate limit: 1 review remaining; one review at a time; review in progress.",
        )
    )

    assert projection["one_review_at_a_time"] is True
    assert projection["active_review"] is True
    assert projection["capacity_available"] is False


@pytest.mark.parametrize(
    "generation",
    [
        _generation(),
        _generation(head_oid="old-head"),
        {
            **_generation(),
            "result": "RATE_LIMITED_NO_REVIEW",
            "capacity_query": {
                "response": {"capacity_available": False, "remaining_reviews": 0}
            },
        },
        {
            **_generation(),
            "result": "RATE_LIMITED_NO_REVIEW",
            "capacity_query": {
                "response": {
                    "capacity_available": False,
                    "remaining_reviews": 1,
                    "one_review_at_a_time": True,
                    "active_review": True,
                }
            },
        },
    ],
)
def test_suppressed_generation_never_posts_second_review_trigger(
    generation: dict, monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": generation})
    monkeypatch.setattr(driver, "repo_label_enabled", lambda *args: (True, {}))
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: {"headRefOid": "head-sha"})
    monkeypatch.setattr(
        driver,
        "gh_json",
        lambda *args: pytest.fail("suppressed trigger must not post"),
    )
    monkeypatch.setattr(
        driver,
        "gh_paginated_array",
        lambda *args: pytest.fail("suppressed trigger must not collect a new baseline"),
    )

    result = driver.trigger_review(REPO, 198, "incremental", driver.DEFAULT_LABEL)

    assert result["posted"] is False
    assert result["suppressed"] is True


def test_forced_trigger_persists_marker_and_archives_active_generation(
    monkeypatch, tmp_path
) -> None:
    prior = _generation()
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": prior})
    monkeypatch.setattr(driver, "repo_label_enabled", lambda *args: (True, {}))
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: {"headRefOid": "head-sha"})
    monkeypatch.setattr(driver, "gh_paginated_array", lambda *args: [])
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)

    def fake_post(args: list[str]) -> dict:
        state = driver.load_state(REPO, 198)
        assert state["inflight_trigger"]["expected_head_oid"] == "head-sha"
        assert state["inflight_trigger"]["body"] == driver.TRIGGER_BODIES["incremental"]
        return _issue_comment(
            200,
            driver.TRIGGER_BODIES["incremental"],
            login="nestharus",
        )

    monkeypatch.setattr(driver, "gh_json", fake_post)
    monkeypatch.setattr(
        driver,
        "poll_review_generation",
        lambda repo, pr_num, generation: {
            **generation,
            "result": "REVIEW_COMPLETED",
        },
    )

    result = driver.trigger_review(
        REPO, 198, "incremental", driver.DEFAULT_LABEL, force=True
    )
    state = driver.load_state(REPO, 198)

    assert result["generation_id"] == 200
    assert state["review_generation_history"][0]["generation_id"] == 100
    assert "inflight_trigger" not in state


def test_trigger_returns_waiting_without_polling_provider(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    monkeypatch.setattr(driver, "repo_label_enabled", lambda *args: (True, {}))
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: {"headRefOid": "head-sha"})
    monkeypatch.setattr(driver, "gh_paginated_array", lambda *args: [])
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(
        driver,
        "gh_json",
        lambda *args: _issue_comment(
            200,
            driver.TRIGGER_BODIES["incremental"],
            login="nestharus",
        ),
    )
    monkeypatch.setattr(
        driver,
        "poll_review_generation",
        lambda *args: pytest.fail("trigger must not poll provider review state"),
    )

    result = driver.trigger_review(REPO, 198, "incremental", driver.DEFAULT_LABEL)

    assert result["result"] == "WAITING_FOR_REVIEW"
    assert result["next_permitted_action"] == "poll"


def test_provider_command_lock_rejects_concurrent_holder(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)

    with driver.provider_command_lock(REPO, 198):
        with pytest.raises(driver.DriverError, match="already in progress"):
            with driver.provider_command_lock(REPO, 198):
                pytest.fail("nested provider command lock must not be acquired")


def test_trigger_reconciles_inflight_command_without_duplicate_post(
    monkeypatch, tmp_path
) -> None:
    inflight = {
        "schema": "coderabbit-inflight-trigger-v1",
        "repo": REPO.slug,
        "pr_num": 198,
        "mode": "incremental",
        "body": driver.TRIGGER_BODIES["incremental"],
        "actor_login": "nestharus",
        "expected_head_oid": "head-sha",
        "started_at": "2026-08-07T10:00:00Z",
        "baseline_review_ids": [1],
        "baseline_issue_comment_ids": [90],
    }
    command = _issue_comment(
        200,
        driver.TRIGGER_BODIES["incremental"],
        "2026-08-07T10:00:01Z",
        login="nestharus",
    )
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(
        REPO,
        198,
        {"active_generation": _generation(), "inflight_trigger": inflight},
    )
    assert driver.initial_trigger_decision(REPO, 198, "auto", "head-sha") == {
        "trigger": True,
        "reason": "initial-trigger-policy:reconcile-inflight-trigger",
    }
    monkeypatch.setattr(driver, "repo_label_enabled", lambda *args: (True, {}))
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: {"headRefOid": "head-sha"})

    def fake_paginated(endpoint: str) -> list[dict]:
        return (
            [_review(1, "CHANGES_REQUESTED")]
            if endpoint.endswith("/reviews")
            else [command]
        )

    monkeypatch.setattr(driver, "gh_paginated_array", fake_paginated)
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(
        driver,
        "gh_json",
        lambda *args: pytest.fail("reconciled trigger must not post again"),
    )
    monkeypatch.setattr(
        driver,
        "poll_review_generation",
        lambda repo, pr_num, generation: {
            **generation,
            "result": "REVIEW_COMPLETED",
        },
    )

    result = driver.trigger_review(REPO, 198, "full", driver.DEFAULT_LABEL, force=True)

    assert result["generation_id"] == 200
    assert result["mode"] == "incremental"
    assert result["supersession_deferred_reason"] == "reconciled-inflight-trigger"
    assert driver.active_review_generation(REPO, 198)["generation_id"] == 200
    assert "inflight_trigger" not in driver.load_state(REPO, 198)


def test_inflight_command_candidates_require_authenticated_actor() -> None:
    marker = {
        "body": driver.TRIGGER_BODIES["incremental"],
        "actor_login": "nestharus",
        "started_at": "2026-08-07T10:00:00Z",
        "baseline_issue_comment_ids": [10],
    }
    comments = [
        _issue_comment(
            11,
            driver.TRIGGER_BODIES["incremental"],
            "2026-08-07T10:00:01Z",
            login="foreign-reviewer",
        ),
        _issue_comment(
            12,
            driver.TRIGGER_BODIES["incremental"],
            "2026-08-07T10:00:02Z",
            login="nestharus",
        ),
    ]

    assert [
        comment["id"]
        for comment in driver.inflight_command_candidates(marker, comments)
    ] == [12]
    marker.pop("actor_login")
    assert driver.inflight_command_candidates(marker, comments) == []


def test_prior_approval_is_archived_but_cannot_approve_rate_limited_new_head(
    monkeypatch, tmp_path
) -> None:
    prior = _generation(head_oid="old-head")
    prior.update(
        {
            "result": "REVIEW_COMPLETED",
            "accepted_review_id": 1,
            "accepted_review_state": "APPROVED",
            "accepted_review_commit_id": "old-head",
        }
    )
    current = _generation(head_oid="new-head")
    current["generation_id"] = 200
    result = driver.classify_review_generation(
        current,
        "new-head",
        [_review(1, "APPROVED", commit_id="old-head")],
        [_issue_comment(201, "Review rate limited: review limit reached.")],
        BOT_LOGIN,
    )
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, {"active_generation": prior})
    driver.activate_review_generation(REPO, 198, result)
    state = driver.load_state(REPO, 198)

    assert result["result"] == "RATE_LIMITED_NO_REVIEW"
    assert result["accepted_review_id"] is None
    assert state["review_generation_history"][0]["accepted_review_state"] == "APPROVED"
    assert state["active_generation"]["expected_head_oid"] == "new-head"


def test_open_findings_include_exact_in_diff_and_outside_diff_identities(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    reviews = [_review(7, "CHANGES_REQUESTED")]
    review_comments = [
        {
            "id": 42,
            "pull_request_review_id": 7,
            "body": "unresolved in-diff finding",
            "position": 1,
            "path": "tools/example.py",
            "line": 9,
            "created_at": "2026-08-07T10:02:00Z",
            "html_url": "https://github.test/review/42",
            "user": {"login": BOT_LOGIN},
        },
        {
            "id": 43,
            "pull_request_review_id": 7,
            "body": "resolved finding",
            "position": 1,
            "path": "tools/example.py",
            "line": 10,
            "created_at": "2026-08-07T10:02:00Z",
            "html_url": "https://github.test/review/43",
            "user": {"login": BOT_LOGIN},
        },
    ]
    issue_comments = [
        _issue_comment(50, "Outside diff finding that still requires action.")
    ]
    records = driver.collect_comment_records(
        REPO,
        198,
        reviews,
        review_comments,
        issue_comments,
        {
            42: {"thread_id": "PRRT_thread", "is_resolved": False},
            43: {"thread_id": "PRRT_resolved", "is_resolved": True},
        },
        BOT_LOGIN,
    )
    findings = []
    for record in records:
        driver.write_comment_file(record["path"], record["metadata"], record["body"])
        if driver.is_open_finding_record(record, "head-sha"):
            findings.append(driver.output_metadata(record, "head-sha"))

    assert [finding["comment_id"] for finding in findings] == [42, 50]
    assert findings[0]["review_id"] == 7
    assert findings[0]["thread_id"] == "PRRT_thread"
    assert findings[0]["url"] == "https://github.test/review/42"
    assert findings[0]["head_oid"] == "head-sha"
    assert findings[0]["resolution_state"] == "unresolved"
    assert findings[1]["kind"] == "out-of-diff"
    assert findings[1]["thread_id"] is None
    assert findings[1]["head_oid"] is None
    assert findings[1]["review_id"] == 0
    assert all(pathlib.Path(item["body_path"]).is_file() for item in findings)

    unbound_record = driver.collect_comment_records(
        REPO,
        198,
        [],
        [],
        issue_comments,
        {},
        BOT_LOGIN,
    )[0]
    assert driver.output_metadata(unbound_record, "head-sha")["head_oid"] is None


def test_review_thread_resolution_is_authoritative_over_outdated_diff(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    comment = {
        "id": 42,
        "pull_request_review_id": 7,
        "body": "finding",
        "position": None,
        "path": "tools/example.py",
        "created_at": "2026-08-07T10:02:00Z",
        "user": {"login": BOT_LOGIN},
    }
    record = driver.collect_comment_records(
        REPO,
        198,
        [_review(7, "CHANGES_REQUESTED")],
        [comment],
        [],
        {
            42: {
                "thread_id": "thread-42",
                "root_comment_id": 42,
                "comment_ids": [42],
                "is_resolved": False,
                "is_outdated": True,
            }
        },
        BOT_LOGIN,
    )[0]

    assert record["metadata"]["outdated"] is True
    assert driver.is_open_finding_record(record, "head-sha") is True

    record["metadata"]["resolved"] = True
    assert driver.is_open_finding_record(record, "head-sha") is False


def test_conversation_history_and_pushback_advance_independently(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    comments = [
        {
            "id": 42,
            "pull_request_review_id": 7,
            "body": "Initial finding",
            "position": 1,
            "path": "tools/example.py",
            "created_at": "2026-08-07T10:02:00Z",
            "user": {"login": BOT_LOGIN},
        },
        {
            "id": 43,
            "pull_request_review_id": 8,
            "in_reply_to_id": 42,
            "body": "Our first reply",
            "position": 1,
            "path": "tools/example.py",
            "created_at": "2026-08-07T10:03:00Z",
            "user": {"login": "nestharus"},
        },
        {
            "id": 44,
            "pull_request_review_id": 9,
            "in_reply_to_id": 42,
            "body": "CodeRabbit pushback",
            "position": 1,
            "path": "tools/example.py",
            "created_at": "2026-08-07T10:04:00Z",
            "user": {"login": BOT_LOGIN},
        },
        {
            "id": 52,
            "pull_request_review_id": 7,
            "body": "Independent finding",
            "position": 1,
            "path": "tools/other.py",
            "created_at": "2026-08-07T10:02:00Z",
            "user": {"login": BOT_LOGIN},
        },
    ]
    thread_status = {
        comment_id: {
            "thread_id": "thread-42",
            "root_comment_id": 42,
            "comment_ids": [42, 43, 44],
            "is_resolved": False,
            "is_outdated": False,
        }
        for comment_id in (42, 43, 44)
    }
    thread_status[52] = {
        "thread_id": "thread-52",
        "root_comment_id": 52,
        "comment_ids": [52],
        "is_resolved": False,
        "is_outdated": False,
    }
    records = driver.collect_comment_records(
        REPO,
        198,
        [_review(7, "CHANGES_REQUESTED")],
        comments,
        [],
        thread_status,
        BOT_LOGIN,
    )
    roots = {
        record["metadata"]["comment_id"]: record
        for record in records
        if record["metadata"].get("thread_parent") is None
    }
    records_by_id = {record["metadata"]["comment_id"]: record for record in records}
    assert (
        records_by_id[42]["metadata"]["conversation_path"]
        == records_by_id[44]["metadata"]["conversation_path"]
    )
    assert not (tmp_path / "nestharus" / "agent-core" / "pr-198" / "review-9").exists()
    assert len(list(tmp_path.rglob("conversation-*.md"))) == 2
    history = pathlib.Path(roots[42]["metadata"]["conversation_path"]).read_text()
    assert history.index("Initial finding") < history.index("Our first reply")
    assert history.index("Our first reply") < history.index("CodeRabbit pushback")

    actions = {
        "42": {"latest_bot_comment_id": 42},
        "52": {"latest_bot_comment_id": 52},
    }
    generation = {
        **_generation(),
        "result": "REVIEW_COMPLETED",
        "accepted_review_id": 7,
    }
    assert driver.conversation_resolution_state(roots[42], actions) == "pushback"
    assert driver.is_actionable_finding_record(
        roots[42], "new-head", {}, generation, actions
    )

    assert (
        driver.conversation_resolution_state(roots[52], actions)
        == "awaiting_coderabbit"
    )
    assert not driver.is_actionable_finding_record(
        roots[52], "new-head", {}, generation, actions
    )

    actions["52"]["status"] = "resolved"
    assert driver.conversation_resolution_state(roots[52], actions) == "pushback"
    assert driver.is_actionable_finding_record(
        roots[52], "new-head", {}, generation, actions
    )

    actions["42"]["latest_bot_comment_id"] = 44
    assert (
        driver.conversation_resolution_state(roots[42], actions)
        == "awaiting_coderabbit"
    )
    assert not driver.is_actionable_finding_record(
        roots[42], "new-head", {}, generation, actions
    )

    roots[42]["metadata"]["latest_bot_comment_id"] = 46
    assert driver.conversation_resolution_state(roots[42], actions) == "pushback"
    assert driver.is_actionable_finding_record(
        roots[42], "new-head", {}, generation, actions
    )


def test_completed_generation_survives_fix_push_and_suppresses_second_trigger() -> None:
    generation = {
        **_generation(head_oid="reviewed-head"),
        "result": "REVIEW_COMPLETED",
        "accepted_review_id": 7,
        "accepted_review_state": "CHANGES_REQUESTED",
        "accepted_review_commit_id": "reviewed-head",
    }

    classified = driver.classify_review_generation(
        generation, "fixed-head", [], [], BOT_LOGIN
    )

    assert classified == generation
    assert driver.generation_suppresses_trigger(classified) == (
        True,
        "the single review generation is already complete",
    )


def test_completed_generation_suppresses_forced_trigger_before_final_approval(
    monkeypatch, tmp_path
) -> None:
    generation = {
        **_generation(head_oid="reviewed-head"),
        "result": "REVIEW_COMPLETED",
        "accepted_review_id": 7,
        "accepted_review_state": "CHANGES_REQUESTED",
        "accepted_review_commit_id": "reviewed-head",
    }
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_review_generation(REPO, 198, generation)
    monkeypatch.setattr(driver, "repo_label_enabled", lambda *args: (True, {}))
    monkeypatch.setattr(
        driver,
        "pr_metadata",
        lambda *args: {"headRefOid": "fixed-head"},
    )
    monkeypatch.setattr(
        driver,
        "gh_json",
        lambda *args: pytest.fail("completed generation must not post another review"),
    )

    result = driver.trigger_review(
        REPO, 198, "incremental", driver.DEFAULT_LABEL, force=True
    )

    assert result["posted"] is False
    assert result["suppression_reason"] == (
        "single-review-policy:generation-already-completed"
    )


def test_completion_requires_resolved_threads_and_exact_current_head_approval(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    generation = {
        **_generation(head_oid="reviewed-head"),
        "result": "REVIEW_COMPLETED",
        "accepted_review_id": 7,
        "accepted_review_state": "CHANGES_REQUESTED",
        "accepted_review_commit_id": "reviewed-head",
    }
    payload = {
        "pr": {"headRefOid": "fixed-head"},
        "terminal": True,
        "terminal_reason": "approved",
        "outcome": "approved",
        "needs_caller_decision": False,
        "review_decision": "CHANGES_REQUESTED",
        "generation": generation,
        "iterations": [],
        "resolved_conversations": [{"thread_id": "thread-42"}],
        "all_conversations_resolved": False,
        "approval_signal": {
            "decision": "APPROVED",
            "review_id": 9,
            "commit_id": "fixed-head",
            "author_login": BOT_LOGIN,
        },
    }
    approval_error = (
        "single-review completion requires resolved conversations and "
        "exact-current-head CodeRabbit approval"
    )
    with pytest.raises(driver.DriverError, match=rf"^{approval_error}$"):
        driver.save_single_review_completion(REPO, 198, payload)

    payload["all_conversations_resolved"] = True
    payload["approval_signal"]["commit_id"] = "prior-head"
    with pytest.raises(driver.DriverError, match=rf"^{approval_error}$"):
        driver.save_single_review_completion(REPO, 198, payload)

    payload["approval_signal"]["commit_id"] = "fixed-head"
    payload["approval_signal"]["author_login"] = "human-reviewer"
    with pytest.raises(driver.DriverError, match=rf"^{approval_error}$"):
        driver.save_single_review_completion(REPO, 198, payload)

    payload["approval_signal"]["author_login"] = BOT_LOGIN
    missing_review_id = {
        **payload,
        "approval_signal": {**payload["approval_signal"], "review_id": None},
    }
    with pytest.raises(driver.DriverError, match=rf"^{approval_error}$"):
        driver.save_single_review_completion(REPO, 198, missing_review_id)

    incomplete_generation = {
        **payload,
        "generation": {**generation, "result": "WAITING_FOR_REVIEW"},
    }
    with pytest.raises(
        driver.DriverError,
        match="^single-review completion requires a completed review generation$",
    ):
        driver.save_single_review_completion(REPO, 198, incomplete_generation)

    completion = driver.save_single_review_completion(REPO, 198, payload)
    assert completion["approval_review_id"] == 9
    assert completion["all_conversations_resolved"] is True


def test_poll_preserves_unrelated_state_and_open_findings_projection_is_read_only(
    monkeypatch, tmp_path
) -> None:
    initial_state = {
        "active_generation": _generation(),
        "last_loop_poll_at": "2026-08-07T09:59:00Z",
        "custom_future_key": {"preserve": True},
        "seen_comment_hashes": {},
        "comment_status": {},
    }
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(REPO, 198, initial_state)
    monkeypatch.setattr(driver, "gh_paginated_array", lambda *args: [])
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(driver, "graphql_review_threads", lambda *args: {})
    monkeypatch.setattr(driver, "rate_limit_check_evidence", lambda *args: [])
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: {"headRefOid": "head-sha"})

    driver.poll(REPO, 198, head_oid="head-sha")
    persisted = driver.load_state(REPO, 198)

    assert persisted["last_loop_poll_at"] == "2026-08-07T09:59:00Z"
    assert persisted["custom_future_key"] == {"preserve": True}

    before_read_only_poll = driver.state_path(REPO, 198).read_bytes()
    driver.poll(REPO, 198, head_oid="head-sha", persist_state=False)
    assert driver.state_path(REPO, 198).read_bytes() == before_read_only_poll


def test_locally_replied_out_of_diff_finding_is_not_reopened(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.mark_out_of_diff_disposition(
        REPO,
        198,
        _issue_comment(50, "Outside diff finding"),
        {"id": 100, "url": "https://github.test/comments/100"},
    )
    record = driver.collect_comment_records(
        REPO,
        198,
        [],
        [],
        [_issue_comment(50, "Outside diff finding")],
        {},
        BOT_LOGIN,
    )[0]
    dispositions = driver.load_state(REPO, 198)["out_of_diff_dispositions"]

    assert driver.is_open_finding_record(record, "head-sha", dispositions) is False

    record["metadata"]["body_sha256"] = driver.hashlib_sha256(
        "Edited outside diff finding"
    )
    record["metadata"]["updated_at"] = "2026-08-07T10:02:00Z"
    assert driver.is_open_finding_record(record, "head-sha", dispositions) is True


def test_fixed_out_of_diff_finding_is_bound_to_exact_body_revision(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    finding = {
        "comment_id": 50,
        "kind": "out-of-diff",
        "body_sha256": driver.hashlib_sha256("Outside diff finding"),
        "updated_at": "2026-08-07T10:01:00Z",
    }
    driver.mark_out_of_diff_fixed_disposition(
        REPO,
        198,
        finding,
        {"outcome": "fixed", "commit_sha": "fixed-head"},
    )
    disposition = driver.load_state(REPO, 198)["out_of_diff_dispositions"]["50"]

    assert disposition["status"] == "fixed"
    assert disposition["commit_sha"] == "fixed-head"
    assert disposition["body_sha256"] == finding["body_sha256"]
    assert disposition["updated_at"] == finding["updated_at"]

    with pytest.raises(driver.DriverError, match="exact binding evidence"):
        driver.mark_out_of_diff_fixed_disposition(
            REPO,
            198,
            {**finding, "updated_at": None},
            {"outcome": "fixed", "commit_sha": "fixed-head"},
        )


def test_reply_posts_to_exact_review_thread_and_reads_back_identity(
    monkeypatch, tmp_path
) -> None:
    body_file = tmp_path / "reply.md"
    body_file.write_text("Applied the requested fix.\n", encoding="utf-8")
    target = {
        "id": 42,
        "body": "finding",
        "user": {"login": BOT_LOGIN},
    }
    posted = {
        "id": 99,
        "body": "Applied the requested fix.\n",
        "in_reply_to_id": 42,
        "html_url": "https://github.test/replies/99",
        "user": {"login": "nestharus"},
    }
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(driver, "gh_paginated_array", lambda *args: [target])
    calls: list[list[str]] = []

    def fake_gh_json(args: list[str]) -> dict:
        calls.append(args)
        return {"id": 99} if "POST" in args else posted

    monkeypatch.setattr(driver, "gh_json", fake_gh_json)

    result = driver.post_reply(REPO, 198, 42, str(body_file))

    assert calls[0][3] == "/repos/nestharus/agent-core/pulls/198/comments/42/replies"
    assert calls[1][-1] == "/repos/nestharus/agent-core/pulls/comments/99"
    assert result["posted"] is True
    assert result["readback"]["id"] == 99
    assert result["readback"]["in_reply_to_id"] == 42


def test_reply_to_outside_diff_comment_is_exact_and_read_back(
    monkeypatch, tmp_path
) -> None:
    body_file = tmp_path / "reply.md"
    body_file.write_text("Acknowledged.\n", encoding="utf-8")
    target = _issue_comment(50, "Outside diff finding")
    expected_body = f"@coderabbitai re: {target['html_url']}\n\nAcknowledged.\n"
    posted = {
        "id": 100,
        "body": expected_body,
        "html_url": "https://github.test/comments/100",
        "user": {"login": "nestharus"},
    }
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    responses = iter([[], [target]])
    monkeypatch.setattr(driver, "gh_paginated_array", lambda *args: next(responses))
    monkeypatch.setattr(
        driver,
        "gh_json",
        lambda args: {"id": 100} if "POST" in args else posted,
    )

    result = driver.post_reply(REPO, 198, 50, str(body_file))

    assert result["reply_kind"] == "issue-comment"
    assert result["readback"]["id"] == 100
    assert (
        driver.load_state(REPO, 198)["out_of_diff_dispositions"]["50"]["reply_id"]
        == 100
    )
    assert driver.load_state(REPO, 198)["out_of_diff_dispositions"]["50"][
        "body_sha256"
    ] == driver.hashlib_sha256("Outside diff finding")


def test_duplicate_review_reply_is_idempotent(monkeypatch, tmp_path) -> None:
    body_file = tmp_path / "reply.md"
    body_file.write_text("Already posted.\n", encoding="utf-8")
    target = {"id": 42, "body": "finding", "user": {"login": BOT_LOGIN}}
    duplicate = {
        "id": 99,
        "body": "Already posted.",
        "in_reply_to_id": 42,
        "html_url": "https://github.test/replies/99",
        "user": {"login": "nestharus"},
    }
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(driver, "gh_paginated_array", lambda *args: [target, duplicate])
    monkeypatch.setattr(
        driver,
        "gh_json",
        lambda *args: pytest.fail("duplicate reply must not post"),
    )

    result = driver.post_reply(REPO, 198, 42, str(body_file))

    assert result["posted"] is False
    assert result["reason"] == "reply-already-present"
    assert result["reply_id"] == 99


def test_missing_fixed_reply_is_recovered_once_from_durable_outcome(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(
        REPO,
        198,
        {
            "conversation_actions": {
                "42": {
                    "root_comment_id": 42,
                    "thread_id": "thread-42",
                    "status": "awaiting_coderabbit",
                    "outcome": "fixed",
                    "commit_sha": "fixed-head",
                    "reply_id": None,
                    "reply_url": None,
                }
            }
        },
    )
    iteration_dir = driver.cache_dir(REPO, 198) / "iter-3"
    iteration_dir.mkdir(parents=True)
    outcome_path = iteration_dir / "agent-42.prompt.outcome.json"
    outcome_path.write_text(
        driver.json.dumps(
            {
                "comment_id": 42,
                "outcome": "fixed",
                "commit_sha": "fixed-head",
                "reply_body_file": None,
                "rationale": "Applied the requested fix.",
                "files_touched": ["tools/example.py"],
            }
        ),
        encoding="utf-8",
    )
    reply_calls: list[tuple[int, str]] = []

    def fake_post_reply(repo, pr_num, comment_id, body_file):
        reply_calls.append((comment_id, pathlib.Path(body_file).read_text()))
        return {
            "posted": True,
            "comment_id": comment_id,
            "reply_id": 99,
            "reply_url": "https://github.test/replies/99",
        }

    monkeypatch.setattr(driver, "post_reply", fake_post_reply)

    recovered = driver.recover_missing_conversation_replies(REPO, 198)

    assert len(recovered) == 1
    assert reply_calls == [
        (42, "Fixed in `fixed-head`.\n\nApplied the requested fix.\n")
    ]
    action = driver.load_state(REPO, 198)["conversation_actions"]["42"]
    assert action["reply_id"] == 99
    assert action["reply_url"] == "https://github.test/replies/99"
    persisted_outcome = driver.json.loads(outcome_path.read_text())
    assert pathlib.Path(persisted_outcome["reply_body_file"]).is_file()

    assert driver.recover_missing_conversation_replies(REPO, 198) == []
    assert len(reply_calls) == 1


def test_conversation_cannot_wait_without_exact_reply_readback(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    finding = {
        "comment_id": 42,
        "root_comment_id": 42,
        "thread_id": "thread-42",
        "kind": "in-diff",
    }

    with pytest.raises(driver.DriverError, match="without an exact reply readback"):
        driver.mark_conversation_awaiting(
            REPO,
            198,
            finding,
            {"outcome": "fixed", "commit_sha": "fixed-head"},
            None,
            "fixed-head",
        )


def test_reply_body_identity_normalizes_line_endings() -> None:
    readback = driver.reply_readback(
        {
            "id": 99,
            "body": "Applied.\nVerified.\n",
            "in_reply_to_id": 42,
            "html_url": "https://github.test/replies/99",
            "user": {"login": "nestharus"},
        },
        "Applied.\r\nVerified.\r\n",
        42,
    )

    assert readback["id"] == 99


def test_reply_rejects_wrong_author_and_missing_exact_comment(
    monkeypatch, tmp_path
) -> None:
    body_file = tmp_path / "reply.md"
    body_file.write_text("Reply.\n", encoding="utf-8")
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args, **kwargs: BOT_LOGIN)
    monkeypatch.setattr(
        driver,
        "gh_paginated_array",
        lambda *args: [{"id": 42, "body": "x", "user": {"login": "human"}}],
    )
    with pytest.raises(driver.DriverError, match="not authored by CodeRabbit"):
        driver.post_reply(REPO, 198, 42, str(body_file))

    responses = iter([[], [_issue_comment(50, "unrelated")]])
    monkeypatch.setattr(driver, "gh_paginated_array", lambda *args: next(responses))
    with pytest.raises(driver.DriverError, match="refusing top-level fallback"):
        driver.post_reply(REPO, 198, 42, str(body_file))


def test_review_loop_does_not_redispatch_handled_comment_ids() -> None:
    first = {"comment_id": 42, "kind": "in-diff", "resolved": False}
    second = {"comment_id": 43, "kind": "out-of-diff", "resolved": False}
    poll_result = {
        "new_comments": [first],
        "actionable_comments": [first, second],
    }

    assert driver.select_actionable_comments(poll_result) == [first, second]
    assert driver.select_actionable_comments(poll_result, {42}) == [second]


def test_out_of_diff_finding_is_bound_to_current_review_generation() -> None:
    generation = _generation(baseline_issue_comment_ids=[50])
    generation["triggered_at"] = "2026-08-07T10:00:00Z"
    record = driver.collect_comment_records(
        REPO,
        198,
        [],
        [],
        [
            _issue_comment(
                51, "Outside diff finding", observed_at="2026-08-07T10:01:00Z"
            )
        ],
        {},
        BOT_LOGIN,
    )[0]

    assert driver.is_actionable_finding_record(record, "head-sha", {}, generation)

    generation["baseline_issue_comment_ids"].append(51)
    assert not driver.is_actionable_finding_record(record, "head-sha", {}, generation)

    generation["baseline_issue_comment_ids"].remove(51)
    record["metadata"]["posted_at"] = "2026-08-07T09:59:59Z"
    assert not driver.is_actionable_finding_record(record, "head-sha", {}, generation)


@pytest.mark.parametrize(
    ("include_caller_decision", "terminal_reason", "poll_count"),
    [
        (False, "approved", 2),
        (True, "caller_decision_required", 1),
    ],
)
def test_review_loop_applies_one_review_and_reuses_persisted_completion(
    monkeypatch,
    tmp_path,
    include_caller_decision: bool,
    terminal_reason: str,
    poll_count: int,
) -> None:
    head = {"oid": "reviewed-head"}
    review_generation = {
        **_generation(head_oid="reviewed-head"),
        "result": "REVIEW_COMPLETED",
        "accepted_review_id": 2,
        "accepted_review_state": "CHANGES_REQUESTED",
        "accepted_review_commit_id": "reviewed-head",
    }
    comments = [
        {
            "comment_id": 42,
            "kind": "in-diff",
            "resolved": False,
            "body_path": str(tmp_path / "comment-42.md"),
            "root_comment_id": 42,
            "thread_id": "thread-42",
            "conversation_revision": "revision-1",
            "latest_bot_comment_id": 42,
        },
        {
            "comment_id": 44,
            "kind": "out-of-diff",
            "resolved": False,
            "body_path": str(tmp_path / "comment-44.md"),
        },
    ]
    if include_caller_decision:
        comments.append(
            {
                "comment_id": 43,
                "kind": "in-diff",
                "resolved": False,
                "body_path": str(tmp_path / "comment-43.md"),
                "root_comment_id": 43,
                "thread_id": "thread-43",
                "conversation_revision": "revision-1",
                "latest_bot_comment_id": 43,
            }
        )
    trigger_calls: list[str] = []
    poll_calls: list[str] = []
    reply_calls: list[int] = []
    reply_path = tmp_path / "reply-44.md"
    reply_path.write_text(
        "No code change is appropriate because the existing contract is exact.\n"
    )

    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path / "cache")
    monkeypatch.setattr(driver, "repo_label_enabled", lambda *args: (True, {}))
    monkeypatch.setattr(
        driver,
        "pr_metadata",
        lambda *args: {
            "headRefName": "fix/review",
            "headRefOid": head["oid"],
            "isDraft": True,
        },
    )
    monkeypatch.setattr(driver, "require_worktree_branch", lambda *args: None)
    monkeypatch.setattr(driver, "git_head", lambda *args: head["oid"])
    monkeypatch.setattr(
        driver,
        "validated_pr_head_identity",
        lambda *args, **kwargs: (
            "fix/review",
            head["oid"],
            driver.utc_now_dt(),
        ),
    )
    monkeypatch.setattr(
        driver,
        "trigger_review",
        lambda *args, **kwargs: (
            trigger_calls.append(head["oid"]),
            driver.save_review_generation(REPO, 198, review_generation),
        )[1],
    )
    monkeypatch.setattr(
        driver,
        "wait_for_loop_poll_cadence",
        lambda *args: {
            "waited_seconds": 0,
            "last_poll_at": None,
            "min_interval_seconds": 300,
        },
    )

    def fake_poll(*args):
        poll_calls.append(head["oid"])
        if len(poll_calls) > 1:
            approval = {
                "decision": "APPROVED",
                "source": "github_review",
                "review_id": 9,
                "commit_id": "fixed-head",
                "submitted_at": "2026-08-07T10:05:00Z",
                "author_login": BOT_LOGIN,
            }
            return (
                {
                    "generation": review_generation,
                    "review_decision": "CHANGES_REQUESTED",
                    "aggregate_review_decision": "APPROVED",
                    "approval_signal": approval,
                    "all_conversations_resolved": True,
                    "resolved_conversations": [
                        {"root_comment_id": 42, "thread_id": "thread-42"}
                    ],
                    "unresolved_findings": [],
                    "actionable_comments": [],
                    "conversation_statuses": [],
                    "outcome": "changes_requested",
                    "review_completed": True,
                },
                "fixed-head",
                driver.utc_now_dt(),
            )
        return (
            {
                "generation": review_generation,
                "review_decision": "CHANGES_REQUESTED",
                "aggregate_review_decision": "CHANGES_REQUESTED",
                "approval_signal": {
                    "decision": "CHANGES_REQUESTED",
                    "review_id": 2,
                    "commit_id": "reviewed-head",
                },
                "all_conversations_resolved": False,
                "resolved_conversations": [],
                "unresolved_findings": comments,
                "conversation_statuses": [],
                "outcome": "changes_requested",
                "review_decision_source": "review_generation",
                "new_comments": comments,
                "actionable_comments": comments,
                "resolved_since_last_poll": [],
                "bot_login": BOT_LOGIN,
                "review_completed": True,
            },
            "reviewed-head",
            driver.utc_now_dt(),
        )

    monkeypatch.setattr(driver, "poll_current_pr_head", fake_poll)
    monkeypatch.setattr(driver, "git_dirty_paths", lambda *args: [])

    def fake_dispatch(**kwargs):
        comment_id = kwargs["comment"]["comment_id"]
        if comment_id == 43:
            return {
                "comment_id": 43,
                "outcome": "deferred",
                "commit_sha": None,
                "reply_body_file": None,
                "rationale": "Caller disposition required.",
                "files_touched": [],
            }
        if comment_id == 44:
            return {
                "comment_id": 44,
                "outcome": "replied",
                "commit_sha": None,
                "reply_body_file": str(reply_path),
                "rationale": "Resolved with an exact rationale reply.",
                "files_touched": [],
            }
        return {
            "comment_id": 42,
            "outcome": "fixed",
            "commit_sha": "fixed-head",
            "reply_body_file": None,
            "rationale": "Applied the review finding.",
            "files_touched": ["tools/example.py"],
        }

    monkeypatch.setattr(driver, "dispatch_comment_agent", fake_dispatch)

    def fake_push(*args):
        head["oid"] = "fixed-head"
        return {"head_sha": "fixed-head"}

    monkeypatch.setattr(driver, "push_branch", fake_push)
    monkeypatch.setattr(
        driver,
        "wait_for_provider_pr_head",
        lambda *args: ("fixed-head", driver.utc_now_dt()),
    )
    monkeypatch.setattr(
        driver,
        "post_reply",
        lambda repo, pr_num, comment_id, body_file: (
            reply_calls.append(comment_id),
            {"posted": True, "comment_id": comment_id, "reply_id": 99},
        )[1],
    )

    first = driver.review_loop(_review_loop_args(tmp_path))

    assert first["terminal_reason"] == terminal_reason
    assert first["needs_caller_decision"] is include_caller_decision
    assert first["terminal"] is (not include_caller_decision)
    assert first["generation_result"] == "REVIEW_COMPLETED"
    assert len(trigger_calls) == 1
    assert len(poll_calls) == poll_count
    assert reply_calls == [42, 44]
    if include_caller_decision:
        assert "single_review_completion" not in first
    else:
        assert first["single_review_completion"]["reviewed_head_oid"] == "reviewed-head"
        assert first["single_review_completion"]["final_head_oid"] == "fixed-head"
        assert first["single_review_completion"]["approval_review_id"] == 9
        second = driver.review_loop(_review_loop_args(tmp_path))
        assert second["completion_reused"] is True
        assert second["terminal_reason"] == "approved"
        assert second["approval_signal"]["review_id"] == 9
        assert second["approval_signal"]["commit_id"] == "fixed-head"
        assert second["all_conversations_resolved"] is True
        assert len(trigger_calls) == 1
        assert len(poll_calls) == poll_count


def test_review_loop_refreshes_metadata_for_approved_external_head(
    monkeypatch, tmp_path
) -> None:
    old_head = "old-head"
    current_head = "external-head"
    generation = {
        **_generation(head_oid=current_head),
        "result": "REVIEW_COMPLETED",
        "accepted_review_id": 9,
        "accepted_review_state": "APPROVED",
        "accepted_review_commit_id": current_head,
    }
    metadata_calls = 0

    def fake_metadata(*args):
        nonlocal metadata_calls
        metadata_calls += 1
        return {
            "headRefName": "fix/review",
            "headRefOid": old_head if metadata_calls == 1 else current_head,
        }

    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path / "cache")
    monkeypatch.setattr(driver, "repo_label_enabled", lambda *args: (True, {}))
    monkeypatch.setattr(driver, "pr_metadata", fake_metadata)
    monkeypatch.setattr(driver, "require_worktree_branch", lambda *args: None)
    monkeypatch.setattr(driver, "git_head", lambda *args: old_head)
    monkeypatch.setattr(
        driver,
        "validated_pr_head_identity",
        lambda *args, **kwargs: ("fix/review", old_head, driver.utc_now_dt()),
    )
    monkeypatch.setattr(
        driver,
        "initial_trigger_decision",
        lambda *args: {"trigger": False, "reason": "test"},
    )
    monkeypatch.setattr(
        driver,
        "wait_for_loop_poll_cadence",
        lambda *args: {
            "waited_seconds": 0,
            "last_poll_at": None,
            "min_interval_seconds": 300,
        },
    )
    monkeypatch.setattr(
        driver,
        "poll_current_pr_head",
        lambda *args: (
            {
                "generation": generation,
                "review_decision": "APPROVED",
                "approval_signal": {
                    "decision": "APPROVED",
                    "review_id": 9,
                    "commit_id": current_head,
                    "submitted_at": "2026-08-07T10:05:00Z",
                    "author_login": BOT_LOGIN,
                },
                "all_conversations_resolved": True,
                "resolved_conversations": [],
                "unresolved_findings": [],
                "actionable_comments": [],
                "outcome": "approved",
            },
            current_head,
            driver.utc_now_dt(),
        ),
    )
    monkeypatch.setattr(driver, "active_review_generation", lambda *args: generation)

    result = driver.review_loop(_review_loop_args(tmp_path))

    assert result["terminal_reason"] == "approved"
    assert result["pr"]["headRefOid"] == current_head
    assert result["single_review_completion"]["final_head_oid"] == current_head
    assert metadata_calls == 2


def test_review_loop_stops_before_dispatching_beyond_remediation_limit(
    monkeypatch, tmp_path
) -> None:
    generation = {
        **_generation(),
        "result": "REVIEW_COMPLETED",
        "accepted_review_id": 2,
        "accepted_review_state": "CHANGES_REQUESTED",
        "accepted_review_commit_id": "head-sha",
    }
    comment = {
        "comment_id": 42,
        "kind": "in-diff",
        "resolved": False,
        "body_path": str(tmp_path / "comment-42.md"),
        "root_comment_id": 42,
        "thread_id": "thread-42",
        "conversation_revision": "revision-1",
        "latest_bot_comment_id": 42,
    }
    poll_calls: list[None] = []
    dispatch_calls: list[None] = []
    (tmp_path / "reply.md").write_text("Addressed.\n", encoding="utf-8")

    monkeypatch.setattr(driver, "MAX_REMEDIATION_PASSES", 1)
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path / "cache")
    monkeypatch.setattr(driver, "repo_label_enabled", lambda *args: (True, {}))
    monkeypatch.setattr(
        driver,
        "pr_metadata",
        lambda *args: {"headRefName": "fix/review", "headRefOid": "head-sha"},
    )
    monkeypatch.setattr(driver, "require_worktree_branch", lambda *args: None)
    monkeypatch.setattr(driver, "git_head", lambda *args: "head-sha")
    monkeypatch.setattr(
        driver,
        "validated_pr_head_identity",
        lambda *args, **kwargs: (
            "fix/review",
            "head-sha",
            driver.utc_now_dt(),
        ),
    )
    monkeypatch.setattr(
        driver,
        "initial_trigger_decision",
        lambda *args: {"trigger": False, "reason": "test"},
    )
    monkeypatch.setattr(
        driver,
        "wait_for_loop_poll_cadence",
        lambda *args: {
            "waited_seconds": 0,
            "last_poll_at": None,
            "min_interval_seconds": 300,
        },
    )

    def fake_poll(*args):
        poll_calls.append(None)
        return (
            {
                "generation": generation,
                "review_decision": "CHANGES_REQUESTED",
                "approval_signal": {"decision": "CHANGES_REQUESTED"},
                "all_conversations_resolved": False,
                "unresolved_findings": [comment],
                "actionable_comments": [comment],
                "outcome": "changes_requested",
            },
            "head-sha",
            driver.utc_now_dt(),
        )

    monkeypatch.setattr(driver, "poll_current_pr_head", fake_poll)
    monkeypatch.setattr(driver, "git_dirty_paths", lambda *args: [])
    monkeypatch.setattr(
        driver,
        "dispatch_comment_agent",
        lambda **kwargs: (
            dispatch_calls.append(None),
            {
                "comment_id": 42,
                "outcome": "replied",
                "commit_sha": None,
                "reply_body_file": str(tmp_path / "reply.md"),
                "rationale": "Addressed.",
                "files_touched": [],
            },
        )[1],
    )
    monkeypatch.setattr(driver, "post_reply", lambda *args: {"posted": True})
    monkeypatch.setattr(driver, "mark_conversation_awaiting", lambda *args: None)
    monkeypatch.setattr(
        driver, "mark_out_of_diff_fixed_disposition", lambda *args: None
    )
    monkeypatch.setattr(driver, "active_review_generation", lambda *args: generation)

    result = driver.review_loop(_review_loop_args(tmp_path))

    assert len(poll_calls) == 2
    assert len(dispatch_calls) == 1
    assert result["terminal"] is True
    assert result["terminal_reason"] == "max_passes_reached"
    assert result["outcome"] == "MAX_PASSES_REACHED"
    assert result["decomposition_required"] is True
    assert result["iterations"][-1]["actionable_comments"] == [comment]
    assert result["iterations"][-1]["decomposition_required"] is True


def test_review_loop_command_returns_nonzero_at_remediation_limit(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        driver,
        "review_loop",
        lambda args: {
            "generation_result": "REVIEW_COMPLETED",
            "outcome": "MAX_PASSES_REACHED",
            "needs_caller_decision": False,
        },
    )

    assert driver.command_review_loop(object()) == 3
    assert "MAX_PASSES_REACHED" in capsys.readouterr().out


def test_completed_pr_suppresses_even_forced_direct_trigger(
    monkeypatch, tmp_path
) -> None:
    generation = {
        **_generation(),
        "result": "REVIEW_COMPLETED",
        "accepted_review_id": 2,
        "accepted_review_state": "APPROVED",
        "accepted_review_commit_id": "head-sha",
    }
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_review_generation(REPO, 198, generation)
    driver.save_single_review_completion(
        REPO,
        198,
        {
            "pr": {"headRefOid": "head-sha"},
            "terminal": True,
            "terminal_reason": "approved",
            "outcome": "approved",
            "needs_caller_decision": False,
            "review_decision": "APPROVED",
            "approval_signal": {
                "decision": "APPROVED",
                "review_id": 7,
                "commit_id": "head-sha",
                "submitted_at": "2026-08-07T10:01:00Z",
                "author_login": BOT_LOGIN,
            },
            "all_conversations_resolved": True,
            "resolved_conversations": [],
            "generation": generation,
            "iterations": [],
        },
    )
    monkeypatch.setattr(driver, "repo_label_enabled", lambda *args: (True, {}))
    monkeypatch.setattr(
        driver,
        "pr_metadata",
        lambda *args: pytest.fail("completed PR must not be queried for a new trigger"),
    )

    result = driver.trigger_review(
        REPO, 198, "incremental", driver.DEFAULT_LABEL, force=True
    )

    assert result["posted"] is False
    assert result["suppressed"] is True
    assert (
        result["suppression_reason"]
        == "single-review-policy:pr-review-already-completed"
    )


def test_rate_limit_capacity_does_not_trigger_again_in_same_pass(
    monkeypatch, tmp_path
) -> None:
    generation = {
        **_generation(),
        "result": "RATE_LIMITED_NO_REVIEW",
        "next_permitted_action": "query_capacity",
    }
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path / "cache")
    driver.save_review_generation(REPO, 198, generation)
    monkeypatch.setattr(driver, "repo_label_enabled", lambda *args: (True, {}))
    monkeypatch.setattr(
        driver,
        "pr_metadata",
        lambda *args: {"headRefName": "fix/review", "headRefOid": "head-sha"},
    )
    monkeypatch.setattr(driver, "require_worktree_branch", lambda *args: None)
    monkeypatch.setattr(driver, "git_head", lambda *args: "head-sha")
    monkeypatch.setattr(
        driver,
        "validated_pr_head_identity",
        lambda *args, **kwargs: (
            "fix/review",
            "head-sha",
            driver.utc_now_dt(),
        ),
    )
    monkeypatch.setattr(
        driver,
        "trigger_review",
        lambda *args, **kwargs: pytest.fail(
            "one pass must not auto-trigger after a capacity response"
        ),
    )
    monkeypatch.setattr(
        driver,
        "wait_for_loop_poll_cadence",
        lambda *args: {
            "waited_seconds": 0,
            "last_poll_at": None,
            "min_interval_seconds": 300,
        },
    )
    monkeypatch.setattr(
        driver,
        "poll_current_pr_head",
        lambda *args: (
            {
                "generation": generation,
                "review_decision": "NONE",
                "outcome": None,
                "new_comments": [],
                "actionable_comments": [],
            },
            "head-sha",
            driver.utc_now_dt(),
        ),
    )
    monkeypatch.setattr(
        driver,
        "capacity_query",
        lambda *args: {
            **generation,
            "capacity_query": {"response": {"capacity_available": True}},
        },
    )
    args = _review_loop_args(tmp_path)
    args.initial_trigger = "skip"

    result = driver.review_loop(args)

    assert result["generation_result"] == "RATE_LIMITED_NO_REVIEW"
    assert result["terminal_reason"] == "rate_limited_no_review"
    assert "single_review_completion" not in result


def test_new_outcome_rejects_value_judgment_and_unresolved_rejection(tmp_path) -> None:
    reply_path = tmp_path / "reply.md"
    reply_path.write_text(
        "The finding is resolved by this rationale.\n", encoding="utf-8"
    )

    with pytest.raises(driver.DriverError, match="unexpected=.*review_provided_value"):
        driver.validate_outcome(
            {
                "comment_id": 42,
                "outcome": "replied",
                "commit_sha": None,
                "reply_body_file": str(reply_path),
                "rationale": "Obsolete value judgment.",
                "files_touched": [],
                "review_provided_value": False,
            },
            42,
        )

    with pytest.raises(driver.DriverError, match="invalid outcome 'rejected'"):
        driver.validate_outcome(
            {
                "comment_id": 42,
                "outcome": "rejected",
                "commit_sha": None,
                "reply_body_file": None,
                "rationale": "Unresolved rejection is forbidden.",
                "files_touched": [],
            },
            42,
        )


def test_rationale_only_resolution_requires_exact_reply_file(tmp_path) -> None:
    missing_reply = tmp_path / "missing.md"

    with pytest.raises(driver.DriverError, match="does not exist"):
        driver.validate_outcome(
            {
                "comment_id": 42,
                "outcome": "replied",
                "commit_sha": None,
                "reply_body_file": str(missing_reply),
                "rationale": "No code change is appropriate.",
                "files_touched": [],
            },
            42,
        )


def test_loop_cadence_ignores_standalone_poll_timestamp(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(driver, "CACHE_ROOT", tmp_path)
    driver.save_state(
        REPO,
        198,
        {
            "last_polled_at": driver.utc_now(),
            "seen_comment_hashes": {},
            "comment_status": {},
        },
    )

    cadence = driver.wait_for_loop_poll_cadence(REPO, 198, 300)

    assert cadence["waited_seconds"] == 0
    assert cadence["last_poll_at"] is None


def test_dispatch_comment_agent_backfills_missing_fix_commit_sha(
    monkeypatch, tmp_path
) -> None:
    iteration_dir = tmp_path / "iteration"
    template_path = tmp_path / "fix-prompt.md"
    template_path.write_text("Fix comment $comment_id", encoding="utf-8")
    iteration_dir.mkdir()
    outcome_path = iteration_dir / "agent-123.prompt.outcome.json"
    outcome_path.write_text(
        driver.json.dumps(
            {
                "comment_id": 123,
                "outcome": "fixed",
                "commit_sha": "stale-commit-sha",
                "reply_body_file": None,
                "rationale": "Stale outcome from an earlier invocation.",
                "files_touched": ["tools/stale.py"],
            }
        ),
        encoding="utf-8",
    )
    raw_outcome = {
        "comment_id": 123,
        "outcome": "fixed",
        "commit_sha": None,
        "reply_body_file": None,
        "rationale": "Applied the focused fix.",
        "files_touched": ["tools/example.py"],
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
        repo=REPO,
        pr_num=198,
        pr_branch="fix/review",
        worktree_path=tmp_path,
        iteration_dir=iteration_dir,
        template_path=template_path,
        fixer_agent=None,
        fixer_model="gpt-high",
    )

    persisted = driver.json.loads(outcome_path.read_text(encoding="utf-8"))
    assert outcome["commit_sha"] == "agent-commit-sha"
    assert persisted["commit_sha"] == "agent-commit-sha"
    assert persisted["reply_body_file"] == outcome["reply_body_file"]
    assert pathlib.Path(outcome["reply_body_file"]).read_text() == (
        "Fixed in `agent-commit-sha`.\n\nApplied the focused fix.\n"
    )


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
            repo=REPO,
            pr_num=198,
            pr_branch="fix/review",
            worktree_path=tmp_path,
            iteration_dir=iteration_dir,
            template_path=template_path,
            fixer_agent=None,
            fixer_model="gpt-high",
        )


def test_dispatch_comment_agent_rejects_reported_commit_that_is_not_head(
    monkeypatch, tmp_path
) -> None:
    iteration_dir = tmp_path / "iteration"
    template_path = tmp_path / "fix-prompt.md"
    template_path.write_text("Fix comment $comment_id", encoding="utf-8")
    raw_outcome = {
        "comment_id": 123,
        "outcome": "fixed",
        "commit_sha": "reported-stale-sha",
        "reply_body_file": None,
        "rationale": "Applied the focused fix.",
        "files_touched": ["tools/example.py"],
    }
    monkeypatch.setattr(
        driver.subprocess,
        "run",
        lambda *args, **kwargs: driver.subprocess.CompletedProcess(
            args=[], returncode=0, stdout=driver.json.dumps(raw_outcome)
        ),
    )
    monkeypatch.setattr(driver, "git_dirty_paths", lambda *args: [])
    heads = iter(["head-before", "head-after"])
    monkeypatch.setattr(driver, "git_head", lambda *args: next(heads))

    with pytest.raises(driver.DriverError, match="worktree HEAD is head-after"):
        driver.dispatch_comment_agent(
            comment={"comment_id": 123, "file_path": "/tmp/comment.md"},
            repo=REPO,
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
    monkeypatch.setattr(driver, "git_output", lambda *args: "2026-07-30T10:10:56-07:00")

    branch, head_oid, committed_at = driver.validated_pr_head_identity(
        metadata,
        REPO,
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
    monkeypatch.setattr(driver, "git_output", lambda *args: "2026-07-31T18:00:00Z")

    _, _, evidence_cutoff = driver.validated_pr_head_identity(
        metadata,
        REPO,
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
            REPO,
            198,
            tmp_path,
            expected_branch="fix/review",
            expected_oid="new-sha",
        )


def test_poll_revalidation_rejects_external_head_change(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        driver,
        "pr_metadata",
        lambda *args: {"headRefName": "fix/review", "headRefOid": "external-sha"},
    )
    monkeypatch.setattr(driver, "git_head", lambda *args: "local-sha")
    monkeypatch.setattr(driver, "remote_branch_oid", lambda *args: "local-sha")

    with pytest.raises(driver.DriverError, match="did not match pushed commit"):
        driver.revalidate_current_pr_head(REPO, 198, tmp_path, "fix/review")


def test_poll_aborts_when_external_head_changes_during_poll(
    monkeypatch, tmp_path
) -> None:
    metadata = iter(
        [
            {"headRefName": "fix/review", "headRefOid": "local-sha"},
            {"headRefName": "fix/review", "headRefOid": "external-sha"},
        ]
    )
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: next(metadata))
    monkeypatch.setattr(driver, "git_head", lambda *args: "local-sha")
    monkeypatch.setattr(driver, "remote_branch_oid", lambda *args: "local-sha")
    monkeypatch.setattr(driver, "git_output", lambda *args: "2026-07-30T10:10:56-07:00")
    monkeypatch.setattr(driver, "poll", lambda *args: {"outcome": "approved"})

    with pytest.raises(driver.DriverError, match="did not match pushed commit"):
        driver.poll_current_pr_head(REPO, 198, tmp_path, "fix/review")


def test_command_poll_defaults_to_current_pr_head(monkeypatch, capsys) -> None:
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: {"headRefOid": "head-sha"})
    observed: dict[str, str] = {}

    def fake_poll(repo, pr_num, head_oid):
        observed["repo"] = repo.slug
        observed["pr_num"] = pr_num
        observed["head_oid"] = head_oid
        return {"generation": {"result": "WAITING_FOR_REVIEW"}}

    monkeypatch.setattr(driver, "poll", fake_poll)
    args = driver.argparse.Namespace(
        repo=REPO.slug,
        pr_num=198,
    )

    assert driver.command_poll(args) == 0
    assert observed == {
        "repo": REPO.slug,
        "pr_num": 198,
        "head_oid": "head-sha",
    }
    assert "WAITING_FOR_REVIEW" in capsys.readouterr().out


def test_wait_for_provider_pr_head_allows_metadata_propagation(
    monkeypatch, tmp_path
) -> None:
    metadata = iter(
        [
            {"headRefName": "fix/review", "headRefOid": "old-sha"},
            {"headRefName": "fix/review", "headRefOid": "new-sha"},
        ]
    )
    sleeps = []
    monkeypatch.delenv("CODERABBIT_POLL_INTERVAL_SECONDS", raising=False)
    monkeypatch.setattr(driver, "remote_branch_oid", lambda *args: "new-sha")
    monkeypatch.setattr(driver, "pr_metadata", lambda *args: next(metadata))
    monkeypatch.setattr(driver, "git_output", lambda *args: "2026-07-30T10:10:56-07:00")
    monkeypatch.setattr(driver.time, "sleep", sleeps.append)

    head_oid, _ = driver.wait_for_provider_pr_head(
        REPO, 198, tmp_path, "fix/review", "new-sha"
    )

    assert head_oid == "new-sha"
    assert sleeps == [driver.DEFAULT_POLL_INTERVAL_SECONDS]


def test_wait_for_provider_pr_head_rejects_remote_branch_change(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(driver, "remote_branch_oid", lambda *args: "external-sha")

    with pytest.raises(driver.DriverError, match="remote PR branch changed after push"):
        driver.wait_for_provider_pr_head(REPO, 198, tmp_path, "fix/review", "new-sha")
