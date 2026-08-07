#!/usr/bin/env python3
"""Drive generation-aware GitHub PR-mode CodeRabbit reviews."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from string import Template
from typing import Any


DEFAULT_LABEL = "coderabbit"
CACHE_ROOT = Path.home() / ".cache" / "coderabbit"
DEFAULT_ENABLED_TTL_SECONDS = 3600
DEFAULT_POLL_INTERVAL_SECONDS = 15
DEFAULT_REVIEW_LOOP_POLL_INTERVAL_SECONDS = 300
DEFAULT_CAPACITY_QUERY_ATTEMPTS = 4
AI_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIX_BRIEF_TEMPLATE = AI_ROOT / "templates" / "coderabbit-fix-brief.md"
DEFAULT_FIXER_AGENT = AI_ROOT / "agents" / "coderabbit-comment-fixer.md"
TRIGGER_BODIES = {
    "incremental": "@coderabbitai review",
    "full": "@coderabbitai full review",
}
ACK_MARKERS = {
    "incremental": "Review triggered.",
    "full": "Full review triggered.",
}
ACK_COMPLETION_MARKERS = {
    "incremental": "Review finished.",
    "full": "Full review finished.",
}
ACK_ACTION_MARKERS = ("Action performed", "Actions performed")
FIX_OUTCOMES = {"fixed", "fixed_and_replied"}
REPLY_OUTCOMES = {"replied", "fixed_and_replied"}
CALLER_DECISION_OUTCOMES = {"rejected", "deferred"}
VALID_OUTCOMES = FIX_OUTCOMES | REPLY_OUTCOMES | CALLER_DECISION_OUTCOMES
TERMINAL_REVIEW_STATES = {"APPROVED", "CHANGES_REQUESTED"}
REVIEW_STATES = TERMINAL_REVIEW_STATES | {"COMMENTED"}
SUMMARY_COMMENT_MARKER = (
    "<!-- This is an auto-generated comment: summarize by coderabbit.ai -->"
)
GENERATION_SCHEMA = "coderabbit-review-generation-v1"
GENERATION_RESULTS = {
    "REVIEW_COMPLETED",
    "RATE_LIMITED_NO_REVIEW",
    "WAITING_FOR_REVIEW",
    "BLOCKED",
}
CAPACITY_QUERY_BODY = "@coderabbitai rate limit"
RATE_LIMIT_MARKERS = (
    "review limit reached",
    "reached your pr review limit",
    "couldn't start this review",
    "review rate limited",
)
CAPACITY_RESPONSE_MARKERS = (
    "review rate limit",
    "review remaining",
    "reviews remaining",
    "review available",
    "review limit",
)


class DriverError(Exception):
    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class Repo:
    owner: str
    name: str

    @classmethod
    def parse(cls, value: str) -> "Repo":
        if "/" not in value:
            raise DriverError(f"repo must be owner/name, got {value!r}")
        owner, name = value.split("/", 1)
        if not owner or not name:
            raise DriverError(f"repo must be owner/name, got {value!r}")
        return cls(owner=owner, name=name)

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as err:
        raise DriverError(f"{name} must be an integer, got {raw!r}") from err
    if value <= 0:
        raise DriverError(f"{name} must be positive, got {raw!r}")
    return value


def run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def gh_json(args: list[str]) -> Any:
    result = run_gh(args)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise DriverError(f"gh {' '.join(args)} failed: {detail}")
    output = result.stdout.strip()
    if not output:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError as err:
        raise DriverError(f"gh {' '.join(args)} returned invalid JSON: {err}") from err


def gh_paginated_array(endpoint: str) -> list[dict[str, Any]]:
    data = gh_json(["api", "--paginate", "--slurp", endpoint])
    if data is None:
        return []
    if isinstance(data, list) and all(isinstance(page, list) for page in data):
        flattened: list[dict[str, Any]] = []
        for page in data:
            flattened.extend(page)
        return flattened
    if isinstance(data, list):
        return data
    raise DriverError(f"expected array response from {endpoint}")


def utc_now_dt() -> datetime:
    return datetime.now(UTC)


def utc_now() -> str:
    return utc_now_dt().isoformat()


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def read_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise DriverError(f"cache file is invalid JSON: {path}: {err}") from err
    if not isinstance(data, dict):
        raise DriverError(f"cache file must contain a JSON object: {path}")
    return data


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def repo_cache_dir(repo: Repo) -> Path:
    return CACHE_ROOT / repo.owner / repo.name


def enabled_cache_path(repo: Repo) -> Path:
    return repo_cache_dir(repo) / "enabled.json"


def bot_cache_path(repo: Repo) -> Path:
    return repo_cache_dir(repo) / "bot_login.json"


def cache_dir(repo: Repo, pr_num: int) -> Path:
    return repo_cache_dir(repo) / f"pr-{pr_num}"


def state_path(repo: Repo, pr_num: int) -> Path:
    return cache_dir(repo, pr_num) / "state.json"


def load_state(repo: Repo, pr_num: int) -> dict[str, Any]:
    data = read_json_file(state_path(repo, pr_num))
    if data is None:
        return {
            "seen_comment_hashes": {},
            "comment_status": {},
            "last_review_decision": "NONE",
            "last_bot_login": None,
        }
    data.setdefault("seen_comment_hashes", {})
    data.setdefault("comment_status", {})
    data.setdefault("last_review_decision", "NONE")
    data.setdefault("last_bot_login", None)
    return data


def save_state(repo: Repo, pr_num: int, state: dict[str, Any]) -> None:
    write_json_file(state_path(repo, pr_num), state)


def load_cached_bot_login(repo: Repo, pr_num: int | None = None) -> str | None:
    repo_cache = read_json_file(bot_cache_path(repo))
    if repo_cache and isinstance(repo_cache.get("bot_login"), str):
        return repo_cache["bot_login"]
    if pr_num is not None:
        state = load_state(repo, pr_num)
        if isinstance(state.get("last_bot_login"), str):
            return state["last_bot_login"]
    return None


def save_bot_login(repo: Repo, bot_login: str, pr_num: int | None = None) -> None:
    write_json_file(
        bot_cache_path(repo),
        {
            "bot_login": bot_login,
            "cached_at": utc_now(),
            "source": f"pr-{pr_num}" if pr_num is not None else "unknown",
        },
    )
    if pr_num is not None:
        state = load_state(repo, pr_num)
        state["last_bot_login"] = bot_login
        save_state(repo, pr_num, state)


def repo_label_exists_uncached(repo: Repo, label: str) -> bool:
    result = run_gh(
        ["label", "list", "--repo", repo.slug, "--search", label, "--json", "name"]
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise DriverError(f"failed to list labels for {repo.slug}: {detail}")
    try:
        labels = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as err:
        raise DriverError(f"gh label list returned invalid JSON: {err}") from err
    if not isinstance(labels, list):
        raise DriverError("gh label list returned non-array JSON")
    return any(
        label_info.get("name") == label
        for label_info in labels
        if isinstance(label_info, dict)
    )


def repo_label_enabled(repo: Repo, label: str) -> tuple[bool, dict[str, Any]]:
    ttl_seconds = env_int("CODERABBIT_ENABLED_TTL_SECONDS", DEFAULT_ENABLED_TTL_SECONDS)
    path = enabled_cache_path(repo)
    cached = read_json_file(path)
    now = utc_now_dt()
    if cached and cached.get("label") == label:
        expires_at = parse_time(cached.get("expires_at"))
        if expires_at and expires_at > now:
            payload = dict(cached)
            payload["cache_hit"] = True
            return bool(payload.get("enabled")), payload

    enabled = repo_label_exists_uncached(repo, label)
    expires_at = now + timedelta(seconds=ttl_seconds)
    payload = {
        "repo": repo.slug,
        "label": label,
        "enabled": enabled,
        "checked_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "ttl_seconds": ttl_seconds,
        "source": "github-repo-label-marker",
        "cache_hit": False,
    }
    write_json_file(path, payload)
    return enabled, payload


def is_coderabbit_login(login: str | None) -> bool:
    if not login:
        return False
    normalized = login.lower()
    return normalized.startswith("coderabbitai") or normalized.startswith(
        "coderabbit-ai"
    )


def is_bot_login(login: str | None, bot_login: str | None) -> bool:
    if not login:
        return False
    if bot_login:
        return login == bot_login
    return is_coderabbit_login(login)


def first_coderabbit_login(*collections: list[dict[str, Any]]) -> str | None:
    for collection in collections:
        for item in collection:
            login = (item.get("user") or {}).get("login")
            if is_coderabbit_login(login):
                return login
    return None


def discover_bot_login(
    repo: Repo,
    pr_num: int,
    reviews: list[dict[str, Any]] | None = None,
    review_comments: list[dict[str, Any]] | None = None,
    issue_comments: list[dict[str, Any]] | None = None,
) -> str | None:
    cached = load_cached_bot_login(repo, pr_num)
    if cached:
        return cached

    reviews = (
        reviews
        if reviews is not None
        else gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/reviews")
    )
    review_comments = (
        review_comments
        if review_comments is not None
        else gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/comments")
    )
    issue_comments = (
        issue_comments
        if issue_comments is not None
        else gh_paginated_array(f"/repos/{repo.slug}/issues/{pr_num}/comments")
    )
    login = first_coderabbit_login(reviews, review_comments, issue_comments)
    if login:
        save_bot_login(repo, login, pr_num)
    return login


def latest_coderabbit_review(
    reviews: list[dict[str, Any]], bot_login: str | None
) -> dict[str, Any] | None:
    cr_reviews = [
        review
        for review in reviews
        if is_bot_login((review.get("user") or {}).get("login"), bot_login)
    ]
    if not cr_reviews:
        return None
    return max(cr_reviews, key=review_sort_key)


def review_sort_key(review: dict[str, Any]) -> tuple[str, int]:
    return (review.get("submitted_at") or "", int(review.get("id") or 0))


def review_follows_trigger(
    review: dict[str, Any], triggered_at: datetime | None
) -> bool:
    submitted_at = parse_time(review.get("submitted_at"))
    return (
        triggered_at is not None
        and submitted_at is not None
        and submitted_at >= triggered_at
    )


def issue_comment_sort_key(comment: dict[str, Any]) -> tuple[str, int]:
    return (
        comment.get("updated_at") or comment.get("created_at") or "",
        int(comment.get("id") or 0),
    )


def object_id(item: dict[str, Any]) -> int:
    try:
        return int(item.get("id") or 0)
    except (TypeError, ValueError):
        return 0


def coderabbit_review_ids(
    reviews: list[dict[str, Any]], bot_login: str | None
) -> list[int]:
    return sorted(
        object_id(review)
        for review in reviews
        if object_id(review)
        and is_bot_login((review.get("user") or {}).get("login"), bot_login)
    )


def is_rate_limit_comment_body(body: str) -> bool:
    normalized = body.lower()
    return any(marker in normalized for marker in RATE_LIMIT_MARKERS)


def is_capacity_response_body(body: str) -> bool:
    normalized = body.lower()
    return any(marker in normalized for marker in CAPACITY_RESPONSE_MARKERS)


def capacity_response_projection(comment: dict[str, Any]) -> dict[str, Any]:
    body = str(comment.get("body") or "")
    normalized = body.lower()
    remaining_match = re.search(
        r"(?P<count>\d+)\s+(?:pr\s+)?reviews?\s+(?:are\s+)?remaining", normalized
    ) or re.search(r"remaining(?:\s+pr)?\s+reviews?\D+(?P<count>\d+)", normalized)
    remaining = int(remaining_match.group("count")) if remaining_match else None
    retry_match = re.search(
        r"next review available in:\s*\*{0,2}(?P<guidance>[^\n<]+)",
        body,
        flags=re.IGNORECASE,
    )
    retry_guidance = retry_match.group("guidance").strip(" *") if retry_match else None
    one_at_a_time = "one review at a time" in normalized
    active_review = any(
        marker in normalized
        for marker in ("review in progress", "review is in progress", "active review")
    )
    exhausted = is_rate_limit_comment_body(body) or any(
        marker in normalized
        for marker in ("no reviews available", "0 reviews remaining")
    )
    capacity_available: bool | None
    if remaining is not None:
        capacity_available = remaining > 0 and not (one_at_a_time and active_review)
    elif exhausted or retry_guidance or (one_at_a_time and active_review):
        capacity_available = False
    else:
        capacity_available = None
    return {
        "comment_id": object_id(comment),
        "comment_url": comment.get("html_url"),
        "observed_at": comment.get("updated_at") or comment.get("created_at"),
        "remaining_reviews": remaining,
        "retry_guidance": retry_guidance,
        "one_review_at_a_time": one_at_a_time,
        "active_review": active_review,
        "capacity_available": capacity_available,
    }


def active_review_generation(repo: Repo, pr_num: int) -> dict[str, Any] | None:
    generation = load_state(repo, pr_num).get("active_generation")
    return dict(generation) if isinstance(generation, dict) else None


def generation_evidence_path(repo: Repo, pr_num: int) -> str:
    return str(state_path(repo, pr_num))


def save_review_generation(
    repo: Repo, pr_num: int, generation: dict[str, Any]
) -> dict[str, Any]:
    result = generation.get("result")
    if (
        generation.get("schema") != GENERATION_SCHEMA
        or result not in GENERATION_RESULTS
    ):
        raise DriverError("refusing to persist malformed CodeRabbit review generation")
    generation["evidence_path"] = generation_evidence_path(repo, pr_num)
    state = load_state(repo, pr_num)
    state["active_generation"] = generation
    save_state(repo, pr_num, state)
    return generation


def activate_review_generation(
    repo: Repo, pr_num: int, generation: dict[str, Any]
) -> dict[str, Any]:
    state = load_state(repo, pr_num)
    active = state.get("active_generation")
    if isinstance(active, dict) and active.get("generation_id") != generation.get(
        "generation_id"
    ):
        history = state.setdefault("review_generation_history", [])
        history.append(active)
    generation["evidence_path"] = generation_evidence_path(repo, pr_num)
    state["active_generation"] = generation
    save_state(repo, pr_num, state)
    return generation


def new_review_generation(
    repo: Repo,
    pr_num: int,
    mode: str,
    expected_head_oid: str,
    reviews: list[dict[str, Any]],
    issue_comments: list[dict[str, Any]],
    bot_login: str | None,
    trigger_comment: dict[str, Any],
) -> dict[str, Any]:
    triggered_at = (
        trigger_comment.get("created_at")
        or trigger_comment.get("updated_at")
        or utc_now()
    )
    return {
        "schema": GENERATION_SCHEMA,
        "generation_id": object_id(trigger_comment),
        "result": "WAITING_FOR_REVIEW",
        "repo": repo.slug,
        "pr_num": pr_num,
        "mode": mode,
        "baseline_review_ids": coderabbit_review_ids(reviews, bot_login),
        "baseline_issue_comment_ids": sorted(
            object_id(comment) for comment in issue_comments if object_id(comment)
        ),
        "trigger_comment_id": object_id(trigger_comment),
        "trigger_comment_url": trigger_comment.get("html_url"),
        "triggered_at": triggered_at,
        "expected_head_oid": expected_head_oid,
        "current_head_oid": expected_head_oid,
        "ack_comment_id": None,
        "ack_comment_url": None,
        "accepted_review_id": None,
        "accepted_review_state": None,
        "accepted_review_commit_id": None,
        "accepted_review_submitted_at": None,
        "rate_limit": None,
        "capacity_query": None,
        "next_permitted_action": "poll",
        "blocked_reason": None,
    }


def rate_limit_check_evidence(repo: Repo, head_oid: str) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    check_data = gh_json(["api", f"/repos/{repo.slug}/commits/{head_oid}/check-runs"])
    check_runs = (
        check_data.get("check_runs", []) if isinstance(check_data, dict) else []
    )
    for check in check_runs:
        output = check.get("output") or {}
        text = " ".join(
            str(value or "")
            for value in (check.get("name"), output.get("title"), output.get("summary"))
        )
        if "review rate limited" not in text.lower():
            continue
        evidence.append(
            {
                "kind": "check_run",
                "id": check.get("id"),
                "name": check.get("name"),
                "status": check.get("status"),
                "conclusion": check.get("conclusion"),
                "url": check.get("html_url") or check.get("details_url"),
            }
        )
    status_data = gh_json(["api", f"/repos/{repo.slug}/commits/{head_oid}/status"])
    statuses = status_data.get("statuses", []) if isinstance(status_data, dict) else []
    for status in statuses:
        status_text = " ".join(
            str(value or "")
            for value in (status.get("context"), status.get("description"))
        )
        if "review rate limited" not in status_text.lower():
            continue
        evidence.append(
            {
                "kind": "status_context",
                "id": status.get("id"),
                "name": status.get("context"),
                "status": status.get("state"),
                "description": status.get("description"),
                "url": status.get("target_url"),
            }
        )
    return evidence


def generation_rate_limit_comments(
    generation: dict[str, Any],
    issue_comments: list[dict[str, Any]],
    bot_login: str | None,
) -> list[dict[str, Any]]:
    baseline = {
        int(value) for value in generation.get("baseline_issue_comment_ids", [])
    }
    triggered_at = parse_time(generation.get("triggered_at"))
    candidates: list[dict[str, Any]] = []
    for comment in issue_comments:
        if object_id(comment) in baseline:
            continue
        if not is_bot_login((comment.get("user") or {}).get("login"), bot_login):
            continue
        if not is_rate_limit_comment_body(str(comment.get("body") or "")):
            continue
        observed_at = parse_time(comment.get("created_at") or comment.get("updated_at"))
        if triggered_at and (observed_at is None or observed_at < triggered_at):
            continue
        candidates.append(comment)
    return sorted(candidates, key=issue_comment_sort_key)


def classify_review_generation(
    generation: dict[str, Any],
    current_head_oid: str,
    reviews: list[dict[str, Any]],
    issue_comments: list[dict[str, Any]],
    bot_login: str | None,
) -> dict[str, Any]:
    classified = dict(generation)
    expected_head_oid = str(classified.get("expected_head_oid") or "")
    classified["current_head_oid"] = current_head_oid
    if not current_head_oid or current_head_oid != expected_head_oid:
        classified.update(
            {
                "result": "BLOCKED",
                "blocked_reason": "PR head changed during review generation",
                "next_permitted_action": "start_new_generation_for_current_head",
            }
        )
        return classified

    baseline_reviews = {
        int(value) for value in classified.get("baseline_review_ids", [])
    }
    triggered_at = parse_time(classified.get("triggered_at"))
    accepted = [
        review
        for review in reviews
        if object_id(review)
        and object_id(review) not in baseline_reviews
        and is_bot_login((review.get("user") or {}).get("login"), bot_login)
        and review.get("commit_id") == expected_head_oid
        and review_follows_trigger(review, triggered_at)
    ]
    if accepted:
        review = max(accepted, key=review_sort_key)
        classified.update(
            {
                "result": "REVIEW_COMPLETED",
                "blocked_reason": None,
                "accepted_review_id": object_id(review),
                "accepted_review_state": str(review.get("state") or "NONE").upper(),
                "accepted_review_commit_id": review.get("commit_id"),
                "accepted_review_submitted_at": review.get("submitted_at"),
                "rate_limit": None,
                "next_permitted_action": "inspect_open_findings",
            }
        )
        return classified

    if classified.get("result") == "BLOCKED" and isinstance(
        classified.get("capacity_query"), dict
    ):
        return classified

    bound_rate_limit = classified.get("rate_limit")
    if (
        isinstance(bound_rate_limit, dict)
        and object_id({"id": bound_rate_limit.get("comment_id")})
        and bound_rate_limit.get("trigger_comment_id")
        == classified.get("trigger_comment_id")
    ):
        classified.update(
            {
                "result": "RATE_LIMITED_NO_REVIEW",
                "blocked_reason": None,
                "next_permitted_action": classified.get("next_permitted_action")
                or "query_capacity",
            }
        )
        return classified

    rate_limit_comments = generation_rate_limit_comments(
        classified, issue_comments, bot_login
    )
    if len(rate_limit_comments) > 1:
        classified.update(
            {
                "result": "BLOCKED",
                "blocked_reason": "ambiguous rate-limit evidence for trigger generation",
                "next_permitted_action": "inspect_rate_limit_comments",
            }
        )
        return classified
    if rate_limit_comments:
        comment = rate_limit_comments[0]
        classified.update(
            {
                "result": "RATE_LIMITED_NO_REVIEW",
                "blocked_reason": None,
                "rate_limit": {
                    "comment_id": object_id(comment),
                    "comment_url": comment.get("html_url"),
                    "observed_at": comment.get("created_at")
                    or comment.get("updated_at"),
                    "trigger_comment_id": classified.get("trigger_comment_id"),
                    "expected_head_oid": expected_head_oid,
                    "check_evidence": [],
                },
                "next_permitted_action": "query_capacity",
            }
        )
        return classified

    classified.update(
        {
            "result": "WAITING_FOR_REVIEW",
            "blocked_reason": None,
            "next_permitted_action": "poll",
        }
    )
    return classified


def record_review_generation_observation(
    repo: Repo,
    pr_num: int,
    generation: dict[str, Any],
    current_head_oid: str,
    reviews: list[dict[str, Any]],
    issue_comments: list[dict[str, Any]],
    bot_login: str | None,
) -> dict[str, Any]:
    if generation.get("schema") != GENERATION_SCHEMA:
        return {
            "schema": GENERATION_SCHEMA,
            "result": "BLOCKED",
            "repo": repo.slug,
            "pr_num": pr_num,
            "next_permitted_action": "trigger",
            "blocked_reason": "no active review generation",
        }
    generation = classify_review_generation(
        generation, current_head_oid, reviews, issue_comments, bot_login
    )
    if generation["result"] == "RATE_LIMITED_NO_REVIEW":
        generation["rate_limit"]["check_evidence"] = rate_limit_check_evidence(
            repo, current_head_oid
        )
    return save_review_generation(repo, pr_num, generation)


def poll_review_generation(
    repo: Repo,
    pr_num: int,
    generation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generation = dict(generation or active_review_generation(repo, pr_num) or {})
    if generation.get("schema") != GENERATION_SCHEMA:
        return {
            "schema": GENERATION_SCHEMA,
            "result": "BLOCKED",
            "repo": repo.slug,
            "pr_num": pr_num,
            "next_permitted_action": "trigger",
            "blocked_reason": "no active review generation",
        }

    current_head_oid = str(pr_metadata(repo, pr_num).get("headRefOid") or "")
    reviews = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/reviews")
    issue_comments = gh_paginated_array(f"/repos/{repo.slug}/issues/{pr_num}/comments")
    bot_login = discover_bot_login(
        repo, pr_num, reviews=reviews, issue_comments=issue_comments
    )
    return record_review_generation_observation(
        repo,
        pr_num,
        generation,
        current_head_oid,
        reviews,
        issue_comments,
        bot_login,
    )


def normalized_review_decision(latest_review: dict[str, Any] | None) -> str:
    if not latest_review:
        return "NONE"
    state = str(latest_review.get("state") or "NONE").upper()
    if state in REVIEW_STATES:
        return state
    return "NONE"


def review_decision_outcome(decision: str) -> str | None:
    if decision == "APPROVED":
        return "approved"
    if decision == "CHANGES_REQUESTED":
        return "changes_requested"
    return None


def trigger_ack_marker(body: str, mode: str) -> str | None:
    if not any(marker in body for marker in ACK_ACTION_MARKERS):
        return None
    markers = (ACK_COMPLETION_MARKERS[mode], ACK_MARKERS[mode])
    full_markers = (ACK_COMPLETION_MARKERS["full"], ACK_MARKERS["full"])
    if mode == "incremental" and any(marker in body for marker in full_markers):
        return None
    return next((marker for marker in markers if marker in body), None)


def is_trigger_ack_body(body: str, mode: str) -> bool:
    return trigger_ack_marker(body, mode) is not None


def is_any_trigger_ack_body(body: str) -> bool:
    return is_trigger_ack_body(body, "incremental") or is_trigger_ack_body(body, "full")


def graphql_review_threads(repo: Repo, pr_num: int) -> dict[int, dict[str, Any]]:
    query = """
query($owner:String!, $name:String!, $number:Int!, $cursor:String) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$number) {
      reviewThreads(first:100, after:$cursor) {
        nodes {
          id
          isResolved
          isOutdated
          comments(first:100) {
            nodes {
              databaseId
              id
              path
              line
              originalLine
              pullRequestReview { databaseId }
              author { login }
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""
    by_comment: dict[int, dict[str, Any]] = {}
    cursor: str | None = None
    while True:
        args = [
            "api",
            "graphql",
            "-F",
            f"owner={repo.owner}",
            "-F",
            f"name={repo.name}",
            "-F",
            f"number={pr_num}",
            "-f",
            f"query={query}",
        ]
        if cursor:
            args.extend(["-F", f"cursor={cursor}"])
        data = gh_json(args)
        threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]
        for thread in threads["nodes"]:
            for comment in thread["comments"]["nodes"]:
                database_id = comment.get("databaseId")
                if database_id is None:
                    continue
                by_comment[int(database_id)] = {
                    "thread_id": thread.get("id"),
                    "is_resolved": bool(thread.get("isResolved")),
                    "is_outdated": bool(thread.get("isOutdated")),
                }
        page_info = threads["pageInfo"]
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
    return by_comment


def associate_issue_comment_review(
    issue_comment: dict[str, Any],
    reviews: list[dict[str, Any]],
    bot_login: str | None,
) -> int:
    comment_time = parse_time(
        issue_comment.get("updated_at") or issue_comment.get("created_at")
    )
    cr_reviews = [
        review
        for review in reviews
        if is_bot_login((review.get("user") or {}).get("login"), bot_login)
    ]
    if not cr_reviews:
        return 0
    latest_review = latest_coderabbit_review(cr_reviews, bot_login)
    if comment_time is None or latest_review is None:
        return int(latest_review["id"]) if latest_review else 0

    candidates: list[tuple[float, dict[str, Any]]] = []
    for review in cr_reviews:
        review_time = parse_time(review.get("submitted_at"))
        if review_time is None:
            continue
        candidates.append((abs((review_time - comment_time).total_seconds()), review))
    if not candidates:
        return int(latest_review["id"])
    _, review = min(candidates, key=lambda item: item[0])
    return int(review["id"])


def comment_file_path(repo: Repo, pr_num: int, review_id: int, comment_id: int) -> Path:
    return cache_dir(repo, pr_num) / f"review-{review_id}" / f"comment-{comment_id}.md"


def yaml_value(value: Any) -> str:
    if value is None:
        return "null"
    return json.dumps(value)


def write_comment_file(path: Path, metadata: dict[str, Any], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = "\n".join(
        f"{key}: {yaml_value(value)}" for key, value in metadata.items()
    )
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


def persist_auxiliary_issue_comment(
    repo: Repo,
    pr_num: int,
    comment: dict[str, Any],
    bot_login: str | None,
    source: str,
) -> str:
    comment_id = object_id(comment)
    body = str(comment.get("body") or "")
    path = comment_file_path(repo, pr_num, 0, comment_id)
    metadata = base_comment_metadata(
        repo, pr_num, comment_id, "out-of-diff", source, 0, body, bot_login
    )
    metadata.update(
        {
            "node_id": comment.get("node_id"),
            "posted_at": comment.get("created_at"),
            "updated_at": comment.get("updated_at"),
            "html_url": comment.get("html_url"),
        }
    )
    write_comment_file(path, metadata, body)
    return str(path)


def base_comment_metadata(
    repo: Repo,
    pr_num: int,
    comment_id: int,
    kind: str,
    source: str,
    review_id: int,
    body: str,
    bot_login: str | None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "code_path": None,
        "code_line": None,
        "resolved": False,
        "thread_parent": None,
        "review_id": review_id,
        "posted_at": None,
        "bot_login": bot_login,
        "comment_id": comment_id,
        "repo": repo.slug,
        "pr_num": pr_num,
        "source": source,
        "body_sha256": hashlib_sha256(body),
        "captured_at": utc_now(),
    }


def hashlib_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def collect_comment_records(
    repo: Repo,
    pr_num: int,
    reviews: list[dict[str, Any]],
    review_comments: list[dict[str, Any]],
    issue_comments: list[dict[str, Any]],
    thread_status: dict[int, dict[str, Any]],
    bot_login: str | None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    review_commit_ids = {
        int(review["id"]): review.get("commit_id")
        for review in reviews
        if review.get("id") is not None
    }

    for comment in review_comments:
        login = (comment.get("user") or {}).get("login")
        if not is_bot_login(login, bot_login):
            continue
        comment_id = int(comment["id"])
        review_id = int(comment.get("pull_request_review_id") or 0)
        status = thread_status.get(comment_id, {})
        position = comment.get("position")
        resolved = bool(
            status.get("is_resolved") or status.get("is_outdated") or position is None
        )
        body = comment.get("body") or ""
        metadata = base_comment_metadata(
            repo,
            pr_num,
            comment_id,
            "in-diff",
            "review-comment",
            review_id,
            body,
            login,
        )
        metadata.update(
            {
                "node_id": comment.get("node_id"),
                "code_path": comment.get("path"),
                "code_line": comment.get("line") or comment.get("original_line"),
                "line": comment.get("line"),
                "original_line": comment.get("original_line"),
                "start_line": comment.get("start_line"),
                "original_start_line": comment.get("original_start_line"),
                "side": comment.get("side"),
                "thread_parent": comment.get("in_reply_to_id"),
                "thread_id": status.get("thread_id"),
                "resolved": resolved,
                "outdated": bool(status.get("is_outdated") or position is None),
                "posted_at": comment.get("created_at"),
                "updated_at": comment.get("updated_at"),
                "commit_id": comment.get("commit_id"),
                "review_commit_id": review_commit_ids.get(review_id),
                "html_url": comment.get("html_url"),
            }
        )
        path = comment_file_path(repo, pr_num, review_id, comment_id)
        records.append(
            {
                "key": f"review-comment:{comment_id}",
                "path": path,
                "body": body,
                "metadata": metadata,
            }
        )

    for comment in issue_comments:
        login = (comment.get("user") or {}).get("login")
        if not is_bot_login(login, bot_login):
            continue
        comment_id = int(comment["id"])
        review_id = associate_issue_comment_review(comment, reviews, bot_login)
        body = comment.get("body") or ""
        is_ack = is_any_trigger_ack_body(body)
        source = "trigger-ack" if is_ack else "issue-comment"
        metadata = base_comment_metadata(
            repo, pr_num, comment_id, "out-of-diff", source, review_id, body, login
        )
        metadata.update(
            {
                "node_id": comment.get("node_id"),
                "code_path": None,
                "code_line": None,
                "thread_parent": None,
                "resolved": is_ack,
                "outdated": False,
                "posted_at": comment.get("created_at"),
                "updated_at": comment.get("updated_at"),
                "review_commit_id": review_commit_ids.get(review_id),
                "html_url": comment.get("html_url"),
            }
        )
        path = comment_file_path(repo, pr_num, review_id, comment_id)
        records.append(
            {
                "key": f"issue-comment:{comment_id}",
                "path": path,
                "body": body,
                "metadata": metadata,
            }
        )

    return records


def output_metadata(
    record: dict[str, Any], current_head_oid: str | None = None
) -> dict[str, Any]:
    metadata = record["metadata"]
    resolved = bool(metadata.get("resolved"))
    finding_head_oid = metadata.get("review_commit_id") or current_head_oid
    return {
        "comment_id": metadata["comment_id"],
        "kind": metadata["kind"],
        "file_path": str(record["path"]),
        "body_path": str(record["path"]),
        "code_path": metadata.get("code_path"),
        "code_line": metadata.get("code_line"),
        "review_id": metadata.get("review_id"),
        "review_commit_id": metadata.get("review_commit_id"),
        "head_oid": finding_head_oid,
        "thread_id": metadata.get("thread_id"),
        "thread_parent": metadata.get("thread_parent"),
        "resolved": resolved,
        "resolution_state": "resolved" if resolved else "unresolved",
        "outdated": metadata.get("outdated"),
        "source": metadata.get("source"),
        "url": metadata.get("html_url"),
    }


def comment_matches_review_head(metadata: dict[str, Any], head_oid: str | None) -> bool:
    return head_oid is None or metadata.get("review_commit_id") == head_oid


def is_open_finding_record(record: dict[str, Any], head_oid: str | None) -> bool:
    metadata = record["metadata"]
    body = str(record.get("body") or "")
    if metadata.get("resolved") or metadata.get("thread_parent") is not None:
        return False
    if metadata.get("source") == "trigger-ack":
        return False
    if metadata.get("kind") == "in-diff":
        return comment_matches_review_head(metadata, head_oid)
    informational_markers = (
        SUMMARY_COMMENT_MARKER,
        "<!-- This is an auto-generated reply by CodeRabbit -->",
        "<!-- This is an auto-generated comment: review paused by coderabbit.ai -->",
    )
    return (
        not is_rate_limit_comment_body(body)
        and not is_capacity_response_body(body)
        and not any(marker in body for marker in informational_markers)
    )


def poll(
    repo: Repo,
    pr_num: int,
    head_oid: str | None = None,
) -> dict[str, Any]:
    reviews = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/reviews")
    review_comments = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/comments")
    issue_comments = gh_paginated_array(f"/repos/{repo.slug}/issues/{pr_num}/comments")
    bot_login = discover_bot_login(
        repo, pr_num, reviews, review_comments, issue_comments
    )
    thread_status = graphql_review_threads(repo, pr_num)

    latest_review = latest_coderabbit_review(reviews, bot_login)
    decision_reviews = reviews
    if head_oid is not None:
        decision_reviews = [
            review for review in reviews if review.get("commit_id") == head_oid
        ]
    latest_scoped_review = latest_coderabbit_review(decision_reviews, bot_login)
    latest_scoped_review_at = (
        parse_time(latest_scoped_review.get("submitted_at"))
        if latest_scoped_review
        else None
    )
    aggregate_decision = normalized_review_decision(latest_scoped_review)
    aggregate_decision_signal = {
        "decision": aggregate_decision,
        "source": "github_review" if latest_scoped_review else "none",
        "review_id": latest_scoped_review.get("id") if latest_scoped_review else None,
        "commit_id": latest_scoped_review.get("commit_id")
        if latest_scoped_review
        else None,
        "submitted_at": latest_scoped_review.get("submitted_at")
        if latest_scoped_review
        else None,
    }
    records = collect_comment_records(
        repo, pr_num, reviews, review_comments, issue_comments, thread_status, bot_login
    )

    state = load_state(repo, pr_num)
    previous_hashes: dict[str, str] = state.get("seen_comment_hashes", {})
    previous_status: dict[str, dict[str, Any]] = state.get("comment_status", {})
    current_hashes: dict[str, str] = {}
    current_status: dict[str, dict[str, Any]] = {}
    seen_by_review: dict[str, list[int]] = {}

    new_comments: list[dict[str, Any]] = []
    actionable_comments: list[dict[str, Any]] = []
    unresolved_findings: list[dict[str, Any]] = []
    for record in records:
        key = record["key"]
        metadata = record["metadata"]
        digest = (
            metadata["body_sha256"]
            + ":"
            + str(metadata.get("updated_at") or metadata.get("posted_at"))
        )
        current_hashes[key] = digest
        current_status[key] = {
            "comment_id": metadata["comment_id"],
            "resolved": metadata.get("resolved"),
            "kind": metadata.get("kind"),
            "source": metadata.get("source"),
        }
        seen_by_review.setdefault(str(metadata["review_id"]), []).append(
            int(metadata["comment_id"])
        )
        write_comment_file(record["path"], metadata, record["body"])
        if is_open_finding_record(record, head_oid):
            unresolved_findings.append(output_metadata(record, head_oid))
        if (
            not metadata.get("resolved")
            and metadata.get("kind") == "in-diff"
            and metadata.get("source") != "trigger-ack"
            and comment_matches_review_head(metadata, head_oid)
        ):
            actionable_comments.append(output_metadata(record, head_oid))
        if (
            previous_hashes.get(key) != digest
            and not metadata.get("resolved")
            and metadata.get("source") != "trigger-ack"
            and (
                metadata.get("kind") != "in-diff"
                or comment_matches_review_head(metadata, head_oid)
            )
        ):
            new_comments.append(output_metadata(record, head_oid))

    resolved_since_last_poll: list[int] = []
    for key, old_status in previous_status.items():
        new_status = current_status.get(key)
        if not new_status:
            continue
        if not old_status.get("resolved") and new_status.get("resolved"):
            resolved_since_last_poll.append(int(new_status["comment_id"]))

    new_state = {
        "last_polled_at": utc_now(),
        "last_review_decision": aggregate_decision,
        "last_review_decision_source": aggregate_decision_signal.get("source"),
        "last_bot_login": bot_login,
        "latest_review_id": latest_review.get("id") if latest_review else None,
        "latest_decision_review_id": aggregate_decision_signal.get("review_id"),
        "latest_decision_comment_id": aggregate_decision_signal.get("comment_id"),
        "seen_comment_hashes": current_hashes,
        "comment_status": current_status,
        "seen_comment_ids_per_review": seen_by_review,
    }
    if isinstance(state.get("active_generation"), dict):
        new_state["active_generation"] = state["active_generation"]
    if isinstance(state.get("review_generation_history"), list):
        new_state["review_generation_history"] = state["review_generation_history"]
    save_state(repo, pr_num, new_state)
    if bot_login:
        save_bot_login(repo, bot_login, pr_num)

    generation = (
        record_review_generation_observation(
            repo,
            pr_num,
            state["active_generation"],
            head_oid
            or str(pr_metadata(repo, pr_num).get("headRefOid") or ""),
            reviews,
            issue_comments,
            bot_login,
        )
        if isinstance(state.get("active_generation"), dict)
        else {
            "schema": GENERATION_SCHEMA,
            "result": "BLOCKED",
            "repo": repo.slug,
            "pr_num": pr_num,
            "next_permitted_action": "trigger",
            "blocked_reason": "no active review generation",
        }
    )
    decision = "NONE"
    outcome = None
    decision_signal: dict[str, Any] = {"decision": "NONE", "source": "none"}
    if generation.get("result") == "REVIEW_COMPLETED":
        decision = str(generation.get("accepted_review_state") or "NONE")
        outcome = review_decision_outcome(decision)
        decision_signal = {
            "decision": decision,
            "source": "review_generation",
            "review_id": generation.get("accepted_review_id"),
            "commit_id": generation.get("accepted_review_commit_id"),
            "submitted_at": generation.get("accepted_review_submitted_at"),
        }

    return {
        "review_decision": decision,
        "aggregate_review_decision": aggregate_decision,
        "aggregate_decision_signal": aggregate_decision_signal,
        "terminal": generation.get("result") != "WAITING_FOR_REVIEW",
        "outcome": outcome,
        "decision_signal": decision_signal,
        "review_decision_source": decision_signal.get("source"),
        "latest_decision_review_id": decision_signal.get("review_id"),
        "latest_decision_comment_id": decision_signal.get("comment_id"),
        "latest_review_at": latest_scoped_review_at.isoformat()
        if latest_scoped_review_at
        else None,
        "review_completed": generation.get("result") == "REVIEW_COMPLETED",
        "generation": generation,
        "new_comments": new_comments,
        "actionable_comments": actionable_comments,
        "unresolved_findings": unresolved_findings,
        "resolved_since_last_poll": resolved_since_last_poll,
        "bot_login": bot_login,
    }


def generation_suppresses_trigger(
    generation: dict[str, Any] | None,
) -> tuple[bool, str | None]:
    if not generation or generation.get("schema") != GENERATION_SCHEMA:
        return False, None
    result = generation.get("result")
    if result == "WAITING_FOR_REVIEW":
        return True, "review request is already outstanding"
    if result == "BLOCKED":
        return True, "the active review generation is blocked"
    if result != "RATE_LIMITED_NO_REVIEW":
        return False, None
    capacity_query = generation.get("capacity_query")
    response = (
        capacity_query.get("response") if isinstance(capacity_query, dict) else None
    )
    if not isinstance(response, dict) or response.get("capacity_available") is not True:
        return True, "CodeRabbit has not reported restored review capacity"
    return False, None


def trigger_review(repo: Repo, pr_num: int, mode: str, label: str) -> dict[str, Any]:
    enabled, _ = repo_label_enabled(repo, label)
    if not enabled:
        raise DriverError(
            "CodeRabbit marker label is absent from repository", exit_code=1
        )

    metadata = pr_metadata(repo, pr_num)
    expected_head_oid = str(metadata.get("headRefOid") or "")
    if not expected_head_oid:
        raise DriverError(f"could not resolve PR head for {repo.slug}#{pr_num}")
    existing = active_review_generation(repo, pr_num)
    replaceable_head_change = bool(
        existing
        and existing.get("result") == "BLOCKED"
        and existing.get("next_permitted_action")
        == "start_new_generation_for_current_head"
        and existing.get("expected_head_oid") != expected_head_oid
    )
    suppression_generation = None if replaceable_head_change else existing
    suppressed, reason = generation_suppresses_trigger(suppression_generation)
    if suppressed:
        return {
            **(suppression_generation or {}),
            "posted": False,
            "suppressed": True,
            "suppression_reason": reason,
        }

    reviews = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/reviews")
    issue_comments = gh_paginated_array(f"/repos/{repo.slug}/issues/{pr_num}/comments")
    bot_login = discover_bot_login(
        repo, pr_num, reviews=reviews, issue_comments=issue_comments
    )
    body = TRIGGER_BODIES[mode]
    response = gh_json(
        [
            "api",
            "-X",
            "POST",
            f"/repos/{repo.slug}/issues/{pr_num}/comments",
            "-f",
            f"body={body}",
        ]
    )
    if not isinstance(response, dict) or not object_id(response):
        raise DriverError("GitHub did not return a trigger comment identity")
    command_comment_id = object_id(response)
    generation = new_review_generation(
        repo,
        pr_num,
        mode,
        expected_head_oid,
        reviews,
        issue_comments,
        bot_login,
        response,
    )
    generation.update({"posted": True, "suppressed": False, "trigger_body": body})
    activate_review_generation(repo, pr_num, generation)
    poll_interval = env_int(
        "CODERABBIT_POLL_INTERVAL_SECONDS", DEFAULT_POLL_INTERVAL_SECONDS
    )

    while True:
        generation = poll_review_generation(repo, pr_num, generation)
        if generation["result"] in {
            "REVIEW_COMPLETED",
            "RATE_LIMITED_NO_REVIEW",
            "BLOCKED",
        }:
            generation.update(
                {"posted": True, "suppressed": False, "trigger_body": body}
            )
            return save_review_generation(repo, pr_num, generation)
        issue_comments = gh_paginated_array(
            f"/repos/{repo.slug}/issues/{pr_num}/comments"
        )
        for comment in issue_comments:
            comment_id = int(comment.get("id") or 0)
            if comment_id <= command_comment_id:
                continue
            login = (comment.get("user") or {}).get("login")
            if bot_login and login != bot_login and not is_coderabbit_login(login):
                continue
            if not is_bot_login(login, bot_login) and not is_coderabbit_login(login):
                continue
            ack_body = comment.get("body") or ""
            ack_marker = trigger_ack_marker(ack_body, mode)
            if ack_marker is None:
                continue
            if login:
                bot_login = login
                save_bot_login(repo, bot_login, pr_num)
            generation.update(
                {
                    "result": "WAITING_FOR_REVIEW",
                    "ack_comment_id": comment_id,
                    "ack_comment_url": comment.get("html_url"),
                    "ack_marker": ack_marker,
                    "bot_login": bot_login,
                    "next_permitted_action": "poll",
                }
            )
            return save_review_generation(repo, pr_num, generation)
        time.sleep(poll_interval)


def capacity_query(repo: Repo, pr_num: int, refresh: bool = False) -> dict[str, Any]:
    generation = active_review_generation(repo, pr_num)
    can_resume_blocked_query = bool(
        generation
        and generation.get("result") == "BLOCKED"
        and isinstance(generation.get("capacity_query"), dict)
    )
    if not generation or (
        generation.get("result") != "RATE_LIMITED_NO_REVIEW"
        and not can_resume_blocked_query
    ):
        raise DriverError(
            "capacity query requires an active RATE_LIMITED_NO_REVIEW generation"
        )

    existing = generation.get("capacity_query")
    if isinstance(existing, dict) and not refresh:
        query = dict(existing)
    else:
        if isinstance(existing, dict):
            generation.setdefault("capacity_query_history", []).append(existing)
        issue_comments = gh_paginated_array(
            f"/repos/{repo.slug}/issues/{pr_num}/comments"
        )
        response = gh_json(
            [
                "api",
                "-X",
                "POST",
                f"/repos/{repo.slug}/issues/{pr_num}/comments",
                "-f",
                f"body={CAPACITY_QUERY_BODY}",
            ]
        )
        if not isinstance(response, dict) or not object_id(response):
            raise DriverError("GitHub did not return a capacity-query comment identity")
        query = {
            "generation_id": object_id(response),
            "query_comment_id": object_id(response),
            "query_comment_url": response.get("html_url"),
            "queried_at": response.get("created_at") or utc_now(),
            "baseline_issue_comment_ids": sorted(
                object_id(comment) for comment in issue_comments if object_id(comment)
            ),
            "response": None,
        }
        generation["capacity_query"] = query
        save_review_generation(repo, pr_num, generation)

    if isinstance(query.get("response"), dict) and not refresh:
        return generation

    attempts = env_int(
        "CODERABBIT_CAPACITY_QUERY_ATTEMPTS", DEFAULT_CAPACITY_QUERY_ATTEMPTS
    )
    poll_interval = env_int(
        "CODERABBIT_POLL_INTERVAL_SECONDS", DEFAULT_POLL_INTERVAL_SECONDS
    )
    bot_login = discover_bot_login(repo, pr_num)
    baseline = {int(value) for value in query.get("baseline_issue_comment_ids", [])}
    query_time = parse_time(query.get("queried_at"))
    for attempt in range(attempts):
        comments = gh_paginated_array(f"/repos/{repo.slug}/issues/{pr_num}/comments")
        candidates: list[dict[str, Any]] = []
        for comment in comments:
            if object_id(comment) in baseline:
                continue
            if not is_bot_login((comment.get("user") or {}).get("login"), bot_login):
                continue
            observed_at = parse_time(
                comment.get("created_at") or comment.get("updated_at")
            )
            if query_time and (observed_at is None or observed_at < query_time):
                continue
            if is_capacity_response_body(str(comment.get("body") or "")):
                candidates.append(comment)
        if len(candidates) > 1:
            generation.update(
                {
                    "result": "BLOCKED",
                    "blocked_reason": "ambiguous capacity-query response",
                    "next_permitted_action": "inspect_capacity_responses",
                }
            )
            return save_review_generation(repo, pr_num, generation)
        if candidates:
            projection = capacity_response_projection(candidates[0])
            projection["capacity_query_id"] = query.get("generation_id")
            projection["response_body_path"] = persist_auxiliary_issue_comment(
                repo,
                pr_num,
                candidates[0],
                bot_login,
                "capacity-response",
            )
            query["response"] = projection
            query["attempts"] = attempt + 1
            generation["capacity_query"] = query
            if projection["capacity_available"] is None:
                generation.update(
                    {
                        "result": "BLOCKED",
                        "blocked_reason": "capacity response did not report availability",
                        "next_permitted_action": "refresh_capacity_query",
                    }
                )
            else:
                generation.update(
                    {
                        "result": "RATE_LIMITED_NO_REVIEW",
                        "blocked_reason": None,
                        "next_permitted_action": "trigger"
                        if projection["capacity_available"]
                        else "wait_for_reported_capacity_then_refresh_query",
                    }
                )
            return save_review_generation(repo, pr_num, generation)
        if attempt + 1 < attempts:
            time.sleep(poll_interval * (attempt + 1))

    query["attempts"] = attempts
    generation["capacity_query"] = query
    generation.update(
        {
            "result": "BLOCKED",
            "blocked_reason": "capacity response unavailable after bounded backoff",
            "next_permitted_action": "poll_capacity_query",
        }
    )
    return save_review_generation(repo, pr_num, generation)


def open_findings(repo: Repo, pr_num: int) -> dict[str, Any]:
    head_oid = str(pr_metadata(repo, pr_num).get("headRefOid") or "")
    if not head_oid:
        raise DriverError(f"could not resolve PR head for {repo.slug}#{pr_num}")
    result = poll(repo, pr_num, head_oid=head_oid)
    findings = result.get("unresolved_findings", [])
    return {
        "schema": "coderabbit-open-findings-v1",
        "repo": repo.slug,
        "pr_num": pr_num,
        "head_oid": head_oid,
        "generation_result": (result.get("generation") or {}).get("result"),
        "count": len(findings),
        "findings": findings,
    }


def pr_metadata(repo: Repo, pr_num: int) -> dict[str, Any]:
    data = gh_json(
        [
            "pr",
            "view",
            str(pr_num),
            "--repo",
            repo.slug,
            "--json",
            "baseRefName,headRefName,headRefOid,isDraft,url",
        ]
    )
    if not isinstance(data, dict):
        raise DriverError(f"gh pr view returned non-object JSON for PR {pr_num}")
    return data


def initial_trigger_decision(
    repo: Repo,
    pr_num: int,
    policy: str,
    head_oid: str,
) -> dict[str, Any]:
    if policy == "always":
        return {"trigger": True, "reason": "initial-trigger-policy:always"}
    generation = active_review_generation(repo, pr_num)
    matching_generation = bool(
        generation
        and generation.get("schema") == GENERATION_SCHEMA
        and generation.get("expected_head_oid") == head_oid
    )
    if policy == "skip" and not matching_generation:
        raise DriverError(
            "initial-trigger=skip requires a persisted generation for the current PR head"
        )
    if policy == "skip":
        return {
            "trigger": False,
            "reason": "initial-trigger-policy:skip:active-generation",
            "generation_result": generation.get("result"),
        }
    if matching_generation:
        suppressed, reason = generation_suppresses_trigger(generation)
        if suppressed or generation.get("result") == "REVIEW_COMPLETED":
            return {
                "trigger": False,
                "reason": f"initial-trigger-policy:auto:{reason or 'review-completed'}",
                "generation_result": generation.get("result"),
            }
    return {
        "trigger": True,
        "reason": "initial-trigger-policy:auto:no-active-generation",
    }


def git_output(worktree_path: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(worktree_path), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise DriverError(f"git {' '.join(args)} failed in {worktree_path}: {detail}")
    return result.stdout.strip()


def require_worktree_branch(worktree_path: Path, branch: str) -> None:
    if not worktree_path.is_dir():
        raise DriverError(f"worktree_path does not exist: {worktree_path}")
    current_branch = git_output(worktree_path, ["branch", "--show-current"])
    if current_branch != branch:
        raise DriverError(
            f"worktree branch mismatch: expected {branch!r}, got {current_branch!r} in {worktree_path}"
        )


def git_dirty_paths(worktree_path: Path) -> list[str]:
    output = git_output(worktree_path, ["status", "--porcelain"])
    return [line[3:] for line in output.splitlines() if line.strip()]


def git_head(worktree_path: Path) -> str:
    return git_output(worktree_path, ["rev-parse", "HEAD"])


def remote_branch_oid(worktree_path: Path, branch: str) -> str:
    ref = f"refs/heads/{branch}"
    output = git_output(worktree_path, ["ls-remote", "--heads", "origin", ref])
    fields = output.split()
    if len(fields) != 2 or fields[1] != ref:
        raise DriverError(f"could not resolve remote branch {ref}")
    return fields[0]


def commit_dirty_agent_changes(worktree_path: Path, comment_id: int) -> str | None:
    dirty = git_dirty_paths(worktree_path)
    if not dirty:
        return None
    git_output(worktree_path, ["add", "-A"])
    git_output(
        worktree_path, ["commit", "-m", f"Address CodeRabbit comment {comment_id}"]
    )
    return git_head(worktree_path)


def push_branch(worktree_path: Path, branch: str) -> dict[str, Any]:
    result = subprocess.run(
        ["git", "-C", str(worktree_path), "push", "origin", f"HEAD:{branch}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise DriverError(f"git push origin HEAD:{branch} failed: {detail}")
    return {
        "pushed": True,
        "branch": branch,
        "head_sha": git_head(worktree_path),
    }


def test_crate_hint(code_path: str | None) -> str:
    if not code_path:
        return ""
    parts = Path(code_path).parts
    if len(parts) >= 2 and parts[0] == "crates":
        return parts[1]
    return ""


def render_fix_prompt(
    template_path: Path,
    output_path: Path,
    comment: dict[str, Any],
    repo: Repo,
    pr_num: int,
    pr_branch: str,
    worktree_path: Path,
) -> None:
    if not template_path.is_file():
        raise DriverError(f"fix brief template not found: {template_path}")
    template = Template(template_path.read_text(encoding="utf-8"))
    comment_file_path = str(comment["file_path"])
    outcome_path = output_path.with_suffix(".outcome.json")
    rendered = template.safe_substitute(
        comment_file_path=comment_file_path,
        pr_num=str(pr_num),
        pr_branch=pr_branch,
        worktree_path=str(worktree_path),
        test_crate_hint=test_crate_hint(comment.get("code_path")),
        repo=repo.slug,
        comment_id=str(comment["comment_id"]),
        outcome_file_path=str(outcome_path),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")


def extract_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def validate_outcome(raw: Any, comment_id: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DriverError(
            f"agent outcome for comment {comment_id} is not a JSON object"
        )
    outcome = raw.get("outcome")
    if outcome not in VALID_OUTCOMES:
        raise DriverError(
            f"agent outcome for comment {comment_id} has invalid outcome {outcome!r}"
        )
    try:
        raw_comment_id = int(raw.get("comment_id", -1))
    except (TypeError, ValueError) as err:
        raise DriverError(
            f"agent outcome for comment {comment_id} has invalid comment_id"
        ) from err
    if raw_comment_id != comment_id:
        raise DriverError(f"agent outcome comment_id mismatch for comment {comment_id}")
    if not isinstance(raw.get("rationale"), str) or not raw["rationale"].strip():
        raise DriverError(
            f"agent outcome for comment {comment_id} is missing rationale"
        )
    if not isinstance(raw.get("files_touched"), list) or not all(
        isinstance(item, str) for item in raw["files_touched"]
    ):
        raise DriverError(
            f"agent outcome for comment {comment_id} has invalid files_touched"
        )
    if not isinstance(raw.get("review_provided_value"), bool):
        raise DriverError(
            f"agent outcome for comment {comment_id} is missing review_provided_value"
        )
    if raw["review_provided_value"] is False and outcome != "rejected":
        raise DriverError(
            f"agent outcome for comment {comment_id} must reject non-value feedback"
        )

    commit_sha = raw.get("commit_sha")
    if commit_sha is not None and not isinstance(commit_sha, str):
        raise DriverError(
            f"agent outcome for comment {comment_id} has invalid commit_sha"
        )
    reply_body_file = raw.get("reply_body_file")
    if reply_body_file is not None and not isinstance(reply_body_file, str):
        raise DriverError(
            f"agent outcome for comment {comment_id} has invalid reply_body_file"
        )
    if outcome in REPLY_OUTCOMES:
        if not reply_body_file:
            raise DriverError(
                f"agent outcome for comment {comment_id} must include reply_body_file"
            )
        if not Path(reply_body_file).is_file():
            raise DriverError(
                f"reply body file for comment {comment_id} does not exist: {reply_body_file}"
            )

    return {
        "comment_id": comment_id,
        "outcome": outcome,
        "commit_sha": commit_sha,
        "reply_body_file": reply_body_file,
        "rationale": raw["rationale"].strip(),
        "files_touched": raw["files_touched"],
        "review_provided_value": raw["review_provided_value"],
    }


def dispatch_comment_agent(
    *,
    comment: dict[str, Any],
    repo: Repo,
    pr_num: int,
    pr_branch: str,
    worktree_path: Path,
    iteration_dir: Path,
    template_path: Path,
    fixer_agent: str | None,
    fixer_model: str | None,
) -> dict[str, Any]:
    comment_id = int(comment["comment_id"])
    prompt_path = iteration_dir / f"agent-{comment_id}.prompt.md"
    render_fix_prompt(
        template_path, prompt_path, comment, repo, pr_num, pr_branch, worktree_path
    )
    outcome_path = prompt_path.with_suffix(".outcome.json")
    log_path = prompt_path.with_suffix(".log")

    if fixer_agent and fixer_model:
        raise DriverError("pass either --fixer-agent or --fixer-model, not both")
    if fixer_agent:
        cmd = [
            "agents",
            "-a",
            fixer_agent,
            "-p",
            str(worktree_path),
            "-f",
            str(prompt_path),
        ]
        dispatch_kind = "agent-file"
        dispatch_ref = fixer_agent
    elif fixer_model:
        cmd = [
            "agents",
            "-m",
            fixer_model,
            "-p",
            str(worktree_path),
            "-f",
            str(prompt_path),
        ]
        dispatch_kind = "model"
        dispatch_ref = fixer_model
    else:
        raise DriverError("comment dispatch requires a fixer agent or fixer model")

    outcome_path.unlink(missing_ok=True)
    head_before = git_head(worktree_path)
    started_at = utc_now()
    result = subprocess.run(
        cmd,
        cwd=worktree_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.write_text(result.stdout, encoding="utf-8")
    if result.returncode != 0:
        raise DriverError(
            f"comment agent failed for comment {comment_id} with exit {result.returncode}; log={log_path}"
        )

    if outcome_path.is_file():
        raw = json.loads(outcome_path.read_text(encoding="utf-8"))
    else:
        raw = extract_json_object(result.stdout)
        if raw is None:
            raise DriverError(
                f"agent did not write parseable outcome JSON for comment {comment_id}; log={log_path}"
            )
        outcome_path.write_text(
            json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    outcome = validate_outcome(raw, comment_id)

    dirty_after = git_dirty_paths(worktree_path)
    if dirty_after and outcome["outcome"] not in FIX_OUTCOMES:
        raise DriverError(
            f"comment agent left uncommitted changes for non-fix outcome on comment {comment_id}: {dirty_after}"
        )
    if dirty_after and outcome["outcome"] in FIX_OUTCOMES:
        commit_sha = commit_dirty_agent_changes(worktree_path, comment_id)
        outcome["commit_sha"] = commit_sha
        outcome_path.write_text(
            json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if outcome["outcome"] in FIX_OUTCOMES:
        head_after = git_head(worktree_path)
        if head_after == head_before:
            raise DriverError(
                f"fix outcome for comment {comment_id} produced no commit"
            )
        if outcome["commit_sha"] and outcome["commit_sha"] != head_after:
            raise DriverError(
                f"fix outcome for comment {comment_id} reported commit "
                f"{outcome['commit_sha']} but worktree HEAD is {head_after}"
            )
        outcome["commit_sha"] = head_after
        outcome_path.write_text(
            json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    outcome.update(
        {
            "comment_file_path": comment["file_path"],
            "prompt_file": str(prompt_path),
            "outcome_file": str(outcome_path),
            "log_file": str(log_path),
            "dispatch_kind": dispatch_kind,
            "dispatch_ref": dispatch_ref,
            "dispatch_command": shlex.join(cmd),
            "started_at": started_at,
            "completed_at": utc_now(),
        }
    )
    return outcome


def reply_readback(
    reply: dict[str, Any], body: str, parent_comment_id: int | None
) -> dict[str, Any]:
    reply_id = object_id(reply)
    if not reply_id or (reply.get("body") or "").strip() != body.strip():
        raise DriverError("posted reply could not be read back with its exact identity")
    if (
        parent_comment_id is not None
        and reply.get("in_reply_to_id") != parent_comment_id
    ):
        raise DriverError(
            "posted review reply was not bound to the requested comment thread"
        )
    return {
        "id": reply_id,
        "url": reply.get("html_url"),
        "author": (reply.get("user") or {}).get("login"),
        "in_reply_to_id": reply.get("in_reply_to_id"),
    }


def reply_result(
    repo: Repo,
    pr_num: int,
    comment_id: int,
    reply_kind: str,
    posted: bool,
    readback: dict[str, Any],
) -> dict[str, Any]:
    return {
        "repo": repo.slug,
        "pr_num": pr_num,
        "comment_id": comment_id,
        "posted": posted,
        "reason": None if posted else "reply-already-present",
        "reply_kind": reply_kind,
        "reply_id": readback["id"],
        "reply_url": readback["url"],
        "readback": readback,
    }


def post_reply(
    repo: Repo, pr_num: int, comment_id: int, body_file: str
) -> dict[str, Any]:
    body = Path(body_file).read_text(encoding="utf-8")
    if not body.strip():
        raise DriverError("reply body file is empty")

    bot_login = discover_bot_login(repo, pr_num)
    review_comments = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/comments")
    target = next(
        (comment for comment in review_comments if object_id(comment) == comment_id),
        None,
    )
    if target:
        if not is_bot_login((target.get("user") or {}).get("login"), bot_login):
            raise DriverError(f"comment {comment_id} is not authored by CodeRabbit")
        duplicate = next(
            (
                comment
                for comment in review_comments
                if comment.get("in_reply_to_id") == comment_id
                and (comment.get("body") or "").strip() == body.strip()
            ),
            None,
        )
        if duplicate:
            readback = reply_readback(duplicate, body, comment_id)
            return reply_result(
                repo, pr_num, comment_id, "review-comment-reply", False, readback
            )
        response = gh_json(
            [
                "api",
                "-X",
                "POST",
                f"/repos/{repo.slug}/pulls/{pr_num}/comments/{comment_id}/replies",
                "-f",
                f"body={body}",
            ]
        )
        response_id = object_id(response) if isinstance(response, dict) else 0
        if not response_id:
            raise DriverError("GitHub returned no review-reply identity")
        posted = gh_json(["api", f"/repos/{repo.slug}/pulls/comments/{response_id}"])
        if not isinstance(posted, dict):
            raise DriverError("GitHub returned no review-reply readback")
        readback = reply_readback(posted, body, comment_id)
        return reply_result(
            repo, pr_num, comment_id, "review-comment-reply", True, readback
        )

    issue_comments = gh_paginated_array(f"/repos/{repo.slug}/issues/{pr_num}/comments")
    issue_target = next(
        (comment for comment in issue_comments if object_id(comment) == comment_id),
        None,
    )
    if not issue_target:
        raise DriverError(
            f"CodeRabbit comment {comment_id} was not found on PR {pr_num}; refusing top-level fallback"
        )
    if not is_bot_login((issue_target.get("user") or {}).get("login"), bot_login):
        raise DriverError(f"comment {comment_id} is not authored by CodeRabbit")

    target_url = issue_target.get("html_url")
    mention_login = (
        bot_login or (issue_target.get("user") or {}).get("login") or "coderabbitai"
    ).removesuffix("[bot]")
    issue_body = (
        f"@{mention_login} re: {target_url}\n\n{body}"
        if target_url
        else f"@{mention_login} re: comment-id:{comment_id}\n\n{body}"
    )
    duplicate = next(
        (
            comment
            for comment in issue_comments
            if (comment.get("body") or "").strip() == issue_body.strip()
        ),
        None,
    )
    if duplicate:
        readback = reply_readback(duplicate, issue_body, None)
        return reply_result(repo, pr_num, comment_id, "issue-comment", False, readback)

    response = gh_json(
        [
            "api",
            "-X",
            "POST",
            f"/repos/{repo.slug}/issues/{pr_num}/comments",
            "-f",
            f"body={issue_body}",
        ]
    )
    response_id = object_id(response) if isinstance(response, dict) else 0
    if not response_id:
        raise DriverError("GitHub returned no issue-reply identity")
    posted = gh_json(["api", f"/repos/{repo.slug}/issues/comments/{response_id}"])
    if not isinstance(posted, dict):
        raise DriverError("GitHub returned no issue-reply readback")
    readback = reply_readback(posted, issue_body, None)
    return reply_result(repo, pr_num, comment_id, "issue-comment", True, readback)


def wait_for_loop_poll_cadence(
    repo: Repo, pr_num: int, min_interval_seconds: int
) -> dict[str, Any]:
    state = load_state(repo, pr_num)
    last_raw = state.get("last_loop_poll_at")
    last_at = parse_time(last_raw) if isinstance(last_raw, str) else None
    if not last_at:
        return {
            "waited_seconds": 0,
            "last_poll_at": None,
            "min_interval_seconds": min_interval_seconds,
        }
    elapsed = (utc_now_dt() - last_at).total_seconds()
    remaining = min_interval_seconds - elapsed
    if remaining <= 0:
        return {
            "waited_seconds": 0,
            "last_poll_at": last_at.isoformat(),
            "min_interval_seconds": min_interval_seconds,
        }
    sleep_seconds = int(remaining) + 1
    print(
        f"CodeRabbit poll cadence: waiting {sleep_seconds}s before polling {repo.slug}#{pr_num}",
        file=sys.stderr,
        flush=True,
    )
    time.sleep(sleep_seconds)
    return {
        "waited_seconds": sleep_seconds,
        "last_poll_at": last_at.isoformat(),
        "min_interval_seconds": min_interval_seconds,
    }


def mark_loop_poll(repo: Repo, pr_num: int) -> None:
    state = load_state(repo, pr_num)
    state["last_loop_poll_at"] = utc_now()
    save_state(repo, pr_num, state)


def select_actionable_comments(
    poll_result: dict[str, Any], handled_comment_ids: set[int] | None = None
) -> list[dict[str, Any]]:
    handled_comment_ids = handled_comment_ids or set()
    candidates = [
        *poll_result.get("new_comments", []),
        *poll_result.get("actionable_comments", []),
    ]
    comments_by_id = {
        int(comment.get("comment_id") or 0): comment
        for comment in candidates
        if comment.get("kind") == "in-diff"
        and not comment.get("resolved")
        and int(comment.get("comment_id") or 0) not in handled_comment_ids
    }
    comments_by_id.pop(0, None)
    return list(comments_by_id.values())


def changes_requested_without_actionable_comments(
    review_decision: str, outcome: Any, actionable_comments: list[dict[str, Any]]
) -> bool:
    return not actionable_comments and (
        review_decision.upper() == "CHANGES_REQUESTED" or outcome == "changes_requested"
    )


def completed_review_without_terminal_decision(
    outcome: Any,
    actionable_comments: list[dict[str, Any]],
    review_completed: bool,
) -> bool:
    return review_completed and not actionable_comments and outcome is None


def validated_pr_head_identity(
    metadata: dict[str, Any],
    repo: Repo,
    pr_num: int,
    worktree_path: Path,
    expected_branch: str | None = None,
    expected_oid: str | None = None,
) -> tuple[str, str, datetime]:
    head_observed_at = utc_now_dt()
    head_branch = pr_head_branch(metadata, repo, pr_num)
    if expected_branch is not None and head_branch != expected_branch:
        raise DriverError(
            f"PR head branch changed for {repo.slug}#{pr_num}: "
            f"expected {expected_branch!r}, got {head_branch!r}"
        )
    head_oid = str(metadata.get("headRefOid") or "")
    if not head_oid:
        raise DriverError(
            f"could not resolve current head identity for {repo.slug}#{pr_num}"
        )
    if expected_oid is not None and head_oid != expected_oid:
        raise DriverError(
            f"PR head did not match pushed commit for {repo.slug}#{pr_num}: "
            f"expected {expected_oid}, got {head_oid}"
        )
    head_committed_at = parse_time(
        git_output(worktree_path, ["show", "-s", "--format=%cI", head_oid])
    )
    if head_committed_at is None:
        raise DriverError(
            f"could not resolve current head identity for {repo.slug}#{pr_num}"
        )
    return head_branch, head_oid, min(head_committed_at, head_observed_at)


def pr_head_branch(metadata: dict[str, Any], repo: Repo, pr_num: int) -> str:
    head_branch = metadata.get("headRefName")
    if not isinstance(head_branch, str) or not head_branch:
        raise DriverError(f"could not resolve PR head branch for {repo.slug}#{pr_num}")
    return head_branch


def revalidate_current_pr_head(
    repo: Repo,
    pr_num: int,
    worktree_path: Path,
    expected_branch: str,
) -> tuple[str, datetime]:
    local_oid = git_head(worktree_path)
    remote_oid = remote_branch_oid(worktree_path, expected_branch)
    if remote_oid != local_oid:
        raise DriverError(
            f"remote PR branch changed for {repo.slug}#{pr_num}: "
            f"local {local_oid}, remote {remote_oid}"
        )
    _, head_oid, head_committed_at = validated_pr_head_identity(
        pr_metadata(repo, pr_num),
        repo,
        pr_num,
        worktree_path,
        expected_branch=expected_branch,
        expected_oid=local_oid,
    )
    return head_oid, head_committed_at


def wait_for_provider_pr_head(
    repo: Repo,
    pr_num: int,
    worktree_path: Path,
    expected_branch: str,
    expected_oid: str,
) -> tuple[str, datetime]:
    poll_interval = env_int(
        "CODERABBIT_POLL_INTERVAL_SECONDS", DEFAULT_POLL_INTERVAL_SECONDS
    )
    while True:
        remote_oid = remote_branch_oid(worktree_path, expected_branch)
        if remote_oid != expected_oid:
            raise DriverError(
                f"remote PR branch changed after push for {repo.slug}#{pr_num}: "
                f"expected {expected_oid}, got {remote_oid}"
            )
        metadata = pr_metadata(repo, pr_num)
        head_branch = metadata.get("headRefName")
        if head_branch != expected_branch:
            raise DriverError(
                f"PR head branch changed for {repo.slug}#{pr_num}: "
                f"expected {expected_branch!r}, got {head_branch!r}"
            )
        if metadata.get("headRefOid") == expected_oid:
            _, head_oid, head_committed_at = validated_pr_head_identity(
                metadata,
                repo,
                pr_num,
                worktree_path,
                expected_branch=expected_branch,
                expected_oid=expected_oid,
            )
            return head_oid, head_committed_at
        print(
            f"Waiting for PR head metadata to reach {expected_oid} for {repo.slug}#{pr_num}",
            file=sys.stderr,
            flush=True,
        )
        time.sleep(poll_interval)


def poll_current_pr_head(
    repo: Repo,
    pr_num: int,
    worktree_path: Path,
    expected_branch: str,
) -> tuple[dict[str, Any], str, datetime]:
    head_oid, head_committed_at = revalidate_current_pr_head(
        repo, pr_num, worktree_path, expected_branch
    )
    poll_result = poll(repo, pr_num, head_oid)
    revalidate_current_pr_head(repo, pr_num, worktree_path, expected_branch)
    return poll_result, head_oid, head_committed_at


def review_loop(args: argparse.Namespace) -> dict[str, Any]:
    repo = Repo.parse(args.repo)
    enabled, enabled_payload = repo_label_enabled(repo, args.label)
    if not enabled:
        raise DriverError(
            "CodeRabbit marker label is absent from repository", exit_code=1
        )

    metadata = pr_metadata(repo, args.pr_num)
    worktree_path = Path(args.worktree_path).expanduser().resolve()
    pr_branch = pr_head_branch(metadata, repo, args.pr_num)
    require_worktree_branch(worktree_path, pr_branch)
    _, head_oid, head_committed_at = validated_pr_head_identity(
        metadata,
        repo,
        args.pr_num,
        worktree_path,
        expected_branch=pr_branch,
        expected_oid=git_head(worktree_path),
    )

    fixer_agent = args.fixer_agent
    fixer_model = args.fixer_model
    if fixer_agent and fixer_model:
        raise DriverError("pass either --fixer-agent or --fixer-model, not both")
    if not fixer_agent and not fixer_model:
        fixer_agent = str(DEFAULT_FIXER_AGENT)
    if fixer_agent and os.sep in fixer_agent:
        fixer_agent_path = Path(fixer_agent).expanduser()
        if not fixer_agent_path.is_file():
            raise DriverError(f"fixer agent file not found: {fixer_agent}")
        fixer_agent = str(fixer_agent_path)

    template_path = Path(args.template).expanduser().resolve()
    min_poll_interval = args.poll_interval_seconds or env_int(
        "CODERABBIT_REVIEW_LOOP_POLL_INTERVAL_SECONDS",
        DEFAULT_REVIEW_LOOP_POLL_INTERVAL_SECONDS,
    )
    if min_poll_interval < DEFAULT_REVIEW_LOOP_POLL_INTERVAL_SECONDS:
        raise DriverError(
            f"poll interval must be at least {DEFAULT_REVIEW_LOOP_POLL_INTERVAL_SECONDS}s, got {min_poll_interval}"
        )

    loop_started_at = utc_now()
    trigger_decision = initial_trigger_decision(
        repo,
        args.pr_num,
        args.initial_trigger,
        head_oid,
    )
    initial_trigger: dict[str, Any] | None = None
    if trigger_decision["trigger"]:
        print(
            f"Triggering CodeRabbit {args.mode} review for {repo.slug}#{args.pr_num}",
            file=sys.stderr,
            flush=True,
        )
        initial_trigger = trigger_review(repo, args.pr_num, args.mode, args.label)
    else:
        print(
            f"Skipping initial trigger: {trigger_decision['reason']}",
            file=sys.stderr,
            flush=True,
        )

    iterations: list[dict[str, Any]] = []
    iteration_index = 1
    terminal_reason: str | None = None
    final_review_decision = "NONE"
    rate_limit_observations: list[str] = []
    handled_comment_ids: set[int] = set()

    while True:
        iteration_dir = cache_dir(repo, args.pr_num) / f"iter-{iteration_index}"
        iteration_dir.mkdir(parents=True, exist_ok=True)
        cadence = wait_for_loop_poll_cadence(repo, args.pr_num, min_poll_interval)
        poll_started_at = utc_now()
        poll_result, head_oid, head_committed_at = poll_current_pr_head(
            repo, args.pr_num, worktree_path, pr_branch
        )
        mark_loop_poll(repo, args.pr_num)
        generation = poll_result.get("generation") or {}
        generation_result = generation.get("result")
        final_review_decision = str(poll_result.get("review_decision") or "NONE")
        final_outcome = poll_result.get("outcome")
        actionable_comments = select_actionable_comments(
            poll_result, handled_comment_ids
        )
        iteration: dict[str, Any] = {
            "iteration": iteration_index,
            "poll_started_at": poll_started_at,
            "poll_completed_at": utc_now(),
            "cadence": cadence,
            "review_decision": final_review_decision,
            "aggregate_review_decision": poll_result.get("aggregate_review_decision"),
            "generation": generation,
            "terminal": generation_result != "WAITING_FOR_REVIEW",
            "outcome": final_outcome,
            "review_decision_source": poll_result.get("review_decision_source"),
            "new_comments": poll_result.get("new_comments", []),
            "actionable_comments": actionable_comments,
            "resolved_since_last_poll": poll_result.get("resolved_since_last_poll", []),
            "bot_login": poll_result.get("bot_login"),
            "outcomes": [],
            "reply_results": [],
            "push_result": None,
            "trigger_result": None,
        }

        if generation_result == "RATE_LIMITED_NO_REVIEW":
            capacity_result = capacity_query(repo, args.pr_num)
            iteration["capacity_result"] = capacity_result
            response = (capacity_result.get("capacity_query") or {}).get("response")
            if (
                capacity_result.get("result") == "RATE_LIMITED_NO_REVIEW"
                and isinstance(response, dict)
                and response.get("capacity_available") is True
            ):
                iteration["trigger_result"] = trigger_review(
                    repo, args.pr_num, "incremental", args.label
                )
                iterations.append(iteration)
                iteration_index += 1
                continue
            terminal_reason = (
                "rate_limited_no_review"
                if capacity_result.get("result") == "RATE_LIMITED_NO_REVIEW"
                else "blocked"
            )
            iterations.append(iteration)
            break

        if generation_result == "BLOCKED":
            terminal_reason = "blocked"
            iterations.append(iteration)
            break

        if generation_result == "WAITING_FOR_REVIEW":
            iterations.append(iteration)
            print(
                f"Waiting for a new exact-head CodeRabbit review ID for "
                f"{repo.slug}#{args.pr_num}",
                file=sys.stderr,
                flush=True,
            )
            iteration_index += 1
            continue

        if final_outcome == "approved":
            terminal_reason = str(final_outcome)
            iterations.append(iteration)
            break

        if changes_requested_without_actionable_comments(
            final_review_decision, final_outcome, actionable_comments
        ):
            terminal_reason = "changes_requested_without_actionable_comments"
            iteration["needs_caller_decision"] = True
            iteration["escalation_reason"] = terminal_reason
            iterations.append(iteration)
            break

        if completed_review_without_terminal_decision(
            final_outcome,
            actionable_comments,
            bool(poll_result.get("review_completed")),
        ):
            terminal_reason = "review_completed_without_terminal_decision"
            iteration["needs_caller_decision"] = True
            iteration["escalation_reason"] = terminal_reason
            iterations.append(iteration)
            break

        if not actionable_comments:
            iterations.append(iteration)
            print(
                f"No actionable in-diff comments yet for {repo.slug}#{args.pr_num}; waiting for next poll",
                file=sys.stderr,
                flush=True,
            )
            iteration_index += 1
            continue

        if git_dirty_paths(worktree_path):
            raise DriverError(
                f"worktree is dirty before comment dispatch: {worktree_path}"
            )

        for comment in actionable_comments:
            print(
                f"Dispatching CodeRabbit comment {comment['comment_id']} to fixer",
                file=sys.stderr,
                flush=True,
            )
            outcome = dispatch_comment_agent(
                comment=comment,
                repo=repo,
                pr_num=args.pr_num,
                pr_branch=pr_branch,
                worktree_path=worktree_path,
                iteration_dir=iteration_dir,
                template_path=template_path,
                fixer_agent=fixer_agent,
                fixer_model=fixer_model,
            )
            iteration["outcomes"].append(outcome)
            handled_comment_ids.add(int(comment["comment_id"]))

        if iteration["outcomes"] and all(
            outcome["review_provided_value"] is False
            for outcome in iteration["outcomes"]
        ):
            terminal_reason = "no_value_provided"
            iterations.append(iteration)
            break

        caller_decision = [
            outcome
            for outcome in iteration["outcomes"]
            if outcome["review_provided_value"]
            and outcome["outcome"] in CALLER_DECISION_OUTCOMES
        ]
        if caller_decision:
            iteration["needs_caller_decision"] = True
            iteration["caller_decision_outcomes"] = caller_decision
            iterations.append(iteration)
            return {
                "repo": repo.slug,
                "pr_num": args.pr_num,
                "pr": metadata,
                "enabled": enabled_payload,
                "loop_started_at": loop_started_at,
                "loop_completed_at": utc_now(),
                "terminal": False,
                "terminal_reason": None,
                "needs_caller_decision": True,
                "review_decision": final_review_decision,
                "generation_result": generation_result,
                "generation": generation,
                "initial_trigger_decision": trigger_decision,
                "initial_trigger_result": initial_trigger,
                "iterations": iterations,
                "rate_limit_observations": rate_limit_observations,
            }

        if any(outcome["outcome"] in FIX_OUTCOMES for outcome in iteration["outcomes"]):
            iteration["push_result"] = push_branch(worktree_path, pr_branch)
            wait_for_provider_pr_head(
                repo,
                args.pr_num,
                worktree_path,
                pr_branch,
                iteration["push_result"]["head_sha"],
            )
            metadata = pr_metadata(repo, args.pr_num)

        for outcome in iteration["outcomes"]:
            if outcome["outcome"] in REPLY_OUTCOMES:
                reply_result = post_reply(
                    repo, args.pr_num, outcome["comment_id"], outcome["reply_body_file"]
                )
                iteration["reply_results"].append(reply_result)

        iteration["trigger_result"] = trigger_review(
            repo, args.pr_num, "incremental", args.label
        )
        iterations.append(iteration)
        iteration_index += 1

    needs_caller_decision = terminal_reason in {
        "changes_requested_without_actionable_comments",
        "review_completed_without_terminal_decision",
    }
    final_generation = active_review_generation(repo, args.pr_num) or {}
    return {
        "repo": repo.slug,
        "pr_num": args.pr_num,
        "pr": metadata,
        "enabled": enabled_payload,
        "loop_started_at": loop_started_at,
        "loop_completed_at": utc_now(),
        "terminal": final_generation.get("result")
        in {
            "REVIEW_COMPLETED",
            "RATE_LIMITED_NO_REVIEW",
            "BLOCKED",
        },
        "terminal_reason": terminal_reason,
        "outcome": terminal_reason,
        "needs_caller_decision": needs_caller_decision,
        "review_decision": final_review_decision,
        "generation_result": final_generation.get("result", "BLOCKED"),
        "generation": final_generation,
        "initial_trigger_decision": trigger_decision,
        "initial_trigger_result": initial_trigger,
        "iterations": iterations,
        "rate_limit_observations": rate_limit_observations,
        "poll_cadence_enforcement": {
            "location": "tools/coderabbit_review_driver.py review-loop wait_for_loop_poll_cadence",
            "min_interval_seconds": min_poll_interval,
        },
    }


def command_is_enabled(args: argparse.Namespace) -> int:
    repo = Repo.parse(args.repo)
    enabled, payload = repo_label_enabled(repo, args.label)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if enabled else 1


def command_trigger(args: argparse.Namespace) -> int:
    repo = Repo.parse(args.repo)
    try:
        payload = trigger_review(repo, args.pr_num, args.mode, args.label)
    except DriverError as err:
        if err.exit_code != 1:
            raise
        print(
            json.dumps(
                {
                    "repo": repo.slug,
                    "pr_num": args.pr_num,
                    "enabled": False,
                    "posted": False,
                    "reason": "CodeRabbit marker label is absent from repository",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_poll(args: argparse.Namespace) -> int:
    repo = Repo.parse(args.repo)
    print(json.dumps(poll(repo, args.pr_num), indent=2, sort_keys=True))
    return 0


def command_capacity(args: argparse.Namespace) -> int:
    repo = Repo.parse(args.repo)
    print(
        json.dumps(
            capacity_query(repo, args.pr_num, refresh=args.new_query),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_open_findings(args: argparse.Namespace) -> int:
    repo = Repo.parse(args.repo)
    print(json.dumps(open_findings(repo, args.pr_num), indent=2, sort_keys=True))
    return 0


def command_review_loop(args: argparse.Namespace) -> int:
    payload = review_loop(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload.get("generation_result") == "BLOCKED":
        return 2
    if payload.get("needs_caller_decision"):
        return 3
    if payload.get("generation_result") == "RATE_LIMITED_NO_REVIEW":
        return 3
    return 0


def command_reply(args: argparse.Namespace) -> int:
    repo = Repo.parse(args.repo)
    payload = post_reply(repo, args.pr_num, args.comment_id, args.body_file)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--label", default=os.environ.get("CODERABBIT_MARKER_LABEL", DEFAULT_LABEL)
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    enabled = subparsers.add_parser(
        "is-enabled", help="Exit 0 when the repo has the CodeRabbit marker label."
    )
    enabled.add_argument("repo")
    enabled.set_defaults(func=command_is_enabled)

    trigger = subparsers.add_parser(
        "trigger", help="Start one baseline-bound CodeRabbit review generation."
    )
    trigger.add_argument("repo")
    trigger.add_argument("pr_num", type=int)
    trigger.add_argument(
        "--mode", choices=("incremental", "full"), default="incremental"
    )
    trigger.set_defaults(func=command_trigger)

    poll_parser = subparsers.add_parser(
        "poll", help="Poll persisted generation evidence and normalized comments."
    )
    poll_parser.add_argument("repo")
    poll_parser.add_argument("pr_num", type=int)
    poll_parser.set_defaults(func=command_poll)

    capacity_parser = subparsers.add_parser(
        "capacity", help="Query authoritative CodeRabbit review capacity once."
    )
    capacity_parser.add_argument("repo")
    capacity_parser.add_argument("pr_num", type=int)
    capacity_parser.add_argument(
        "--new-query",
        action="store_true",
        help="Start a new capacity-query generation instead of polling the persisted one.",
    )
    capacity_parser.set_defaults(func=command_capacity)

    findings_parser = subparsers.add_parser(
        "open-findings",
        help="Return unresolved in-diff and outside-diff CodeRabbit findings.",
    )
    findings_parser.add_argument("repo")
    findings_parser.add_argument("pr_num", type=int)
    findings_parser.set_defaults(func=command_open_findings)

    review_loop_parser = subparsers.add_parser(
        "review-loop",
        help="Run the unbounded CodeRabbit PR review loop with centralized 5-minute poll cadence.",
    )
    review_loop_parser.add_argument("repo")
    review_loop_parser.add_argument("pr_num", type=int)
    review_loop_parser.add_argument(
        "--mode", choices=("incremental", "full"), default="incremental"
    )
    review_loop_parser.add_argument(
        "--initial-trigger",
        choices=("auto", "always", "skip"),
        default="auto",
        help="Initial trigger policy. auto resumes a matching persisted generation.",
    )
    review_loop_parser.add_argument(
        "--worktree-path",
        default=os.getcwd(),
        help="Absolute or relative worktree path for the PR head branch.",
    )
    review_loop_parser.add_argument(
        "--fixer-agent",
        default=None,
        help="Agent name or .md file for per-comment fixes. When set, no -m override is passed.",
    )
    review_loop_parser.add_argument(
        "--fixer-model",
        default=None,
        help="Model for prompt-only per-comment fixes. Mutually exclusive with --fixer-agent.",
    )
    review_loop_parser.add_argument(
        "--template",
        default=str(DEFAULT_FIX_BRIEF_TEMPLATE),
        help="Per-comment prompt template path.",
    )
    review_loop_parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=None,
        help="Minimum seconds between loop-owned poll calls; cannot be below 300.",
    )
    review_loop_parser.set_defaults(func=command_review_loop)

    reply = subparsers.add_parser(
        "reply", help="Reply to a CodeRabbit review or issue comment."
    )
    reply.add_argument("repo")
    reply.add_argument("pr_num", type=int)
    reply.add_argument("comment_id", type=int)
    reply.add_argument("body_file")
    reply.set_defaults(func=command_reply)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except DriverError as err:
        print(json.dumps({"error": str(err)}, sort_keys=True), file=sys.stderr)
        return err.exit_code


if __name__ == "__main__":
    sys.exit(main())
