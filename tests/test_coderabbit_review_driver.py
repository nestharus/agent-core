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
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args: BOT_LOGIN)
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
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args: BOT_LOGIN)
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
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args: BOT_LOGIN)
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


def test_capacity_projection_does_not_capture_number_from_later_line() -> None:
    projection = driver.capacity_response_projection(
        _issue_comment(201, "Remaining reviews:\nUnrelated issue 99")
    )

    assert projection["remaining_reviews"] is None
    assert projection["capacity_available"] is None


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


def test_trigger_returns_waiting_after_one_observation_without_ack(
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
    observations = 0

    def observe_once(repo, pr_num, generation):
        nonlocal observations
        observations += 1
        return {**generation, "result": "WAITING_FOR_REVIEW"}

    monkeypatch.setattr(driver, "poll_review_generation", observe_once)

    result = driver.trigger_review(REPO, 198, "incremental", driver.DEFAULT_LABEL)

    assert observations == 1
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
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args: BOT_LOGIN)
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
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args: BOT_LOGIN)
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
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args: BOT_LOGIN)
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
    monkeypatch.setattr(driver, "discover_bot_login", lambda *args: BOT_LOGIN)
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
    second = {"comment_id": 43, "kind": "in-diff", "resolved": False}
    poll_result = {
        "new_comments": [first],
        "actionable_comments": [first, second],
    }

    assert driver.select_actionable_comments(poll_result) == [first, second]
    assert driver.select_actionable_comments(poll_result, {42}) == [second]


def test_non_value_outcome_must_use_rejected_contract() -> None:
    with pytest.raises(driver.DriverError, match="must reject non-value feedback"):
        driver.validate_outcome(
            {
                "comment_id": 42,
                "outcome": "fixed",
                "commit_sha": None,
                "reply_body_file": None,
                "rationale": "Incorrectly marked a fix as non-value.",
                "files_touched": [],
                "review_provided_value": False,
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
                "review_provided_value": True,
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
