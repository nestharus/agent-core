#!/usr/bin/env python3
"""Drive one generation-aware GitHub PR-mode CodeRabbit review per PR."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from contextlib import contextmanager
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
MAX_REMEDIATION_PASSES = 3
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
RESOLUTION_OUTCOMES = FIX_OUTCOMES | REPLY_OUTCOMES
CALLER_DECISION_OUTCOMES = {"deferred"}
VALID_OUTCOMES = FIX_OUTCOMES | REPLY_OUTCOMES | CALLER_DECISION_OUTCOMES
OUTCOME_FIELDS = {
    "comment_id",
    "outcome",
    "commit_sha",
    "reply_body_file",
    "rationale",
    "files_touched",
}
TERMINAL_REVIEW_STATES = {"APPROVED", "CHANGES_REQUESTED"}
REVIEW_STATES = TERMINAL_REVIEW_STATES | {"COMMENTED"}
SUMMARY_COMMENT_MARKER = (
    "<!-- This is an auto-generated comment: summarize by coderabbit.ai -->"
)
GENERATION_SCHEMA = "coderabbit-review-generation-v1"
SINGLE_REVIEW_COMPLETION_SCHEMA = "coderabbit-single-review-completion-v1"
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
    "review will be available",
    "reviews are available",
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


def authenticated_actor_login() -> str:
    actor = gh_json(["api", "/user"])
    login = actor.get("login") if isinstance(actor, dict) else None
    if not isinstance(login, str) or not login:
        raise DriverError("could not resolve the authenticated GitHub actor")
    return login


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


@contextmanager
def provider_command_lock(repo: Repo, pr_num: int):
    path = cache_dir(repo, pr_num) / "provider-command.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as err:
            raise DriverError(
                f"another provider command is already in progress for {repo.slug}#{pr_num}"
            ) from err
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


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


def single_review_completion(repo: Repo, pr_num: int) -> dict[str, Any] | None:
    completion = load_state(repo, pr_num).get("single_review_completion")
    if not isinstance(completion, dict):
        return None
    if (
        completion.get("schema") != SINGLE_REVIEW_COMPLETION_SCHEMA
        or completion.get("repo") != repo.slug
        or completion.get("pr_num") != pr_num
        or completion.get("generation_result") != "REVIEW_COMPLETED"
    ):
        raise DriverError("persisted CodeRabbit single-review completion is malformed")
    return dict(completion)


def save_single_review_completion(
    repo: Repo, pr_num: int, payload: dict[str, Any]
) -> dict[str, Any]:
    generation = payload.get("generation") or {}
    if generation.get("result") != "REVIEW_COMPLETED":
        raise DriverError(
            "single-review completion requires a completed review generation"
        )
    approval = payload.get("approval_signal") or {}
    final_head_oid = (payload.get("pr") or {}).get("headRefOid")
    if (
        payload.get("terminal_reason") != "approved"
        or payload.get("all_conversations_resolved") is not True
        or approval.get("decision") != "APPROVED"
        or approval.get("commit_id") != final_head_oid
        or not approval.get("review_id")
        or not is_coderabbit_login(approval.get("author_login"))
    ):
        raise DriverError(
            "single-review completion requires resolved conversations and exact-current-head CodeRabbit approval"
        )
    completion = {
        "schema": SINGLE_REVIEW_COMPLETION_SCHEMA,
        "repo": repo.slug,
        "pr_num": pr_num,
        "completed_at": utc_now(),
        "generation_id": generation.get("generation_id"),
        "accepted_review_id": generation.get("accepted_review_id"),
        "accepted_review_state": generation.get("accepted_review_state"),
        "reviewed_head_oid": generation.get("accepted_review_commit_id"),
        "final_head_oid": final_head_oid,
        "approval_review_id": approval.get("review_id"),
        "approval_review_state": approval.get("decision"),
        "approval_review_commit_id": approval.get("commit_id"),
        "approval_review_submitted_at": approval.get("submitted_at"),
        "approval_review_author_login": approval.get("author_login"),
        "all_conversations_resolved": True,
        "resolved_conversations": payload.get("resolved_conversations", []),
        "terminal": payload.get("terminal"),
        "terminal_reason": payload.get("terminal_reason"),
        "outcome": payload.get("outcome"),
        "needs_caller_decision": payload.get("needs_caller_decision"),
        "caller_decision_outcomes": payload.get("caller_decision_outcomes", []),
        "review_decision": payload.get("review_decision"),
        "generation_result": generation.get("result"),
        "generation": generation,
        "iterations": payload.get("iterations", []),
        "rate_limit_observations": payload.get("rate_limit_observations", []),
        "evidence_path": generation_evidence_path(repo, pr_num),
    }
    state = load_state(repo, pr_num)
    state["single_review_completion"] = completion
    save_state(repo, pr_num, state)
    return completion


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
    persist: bool = True,
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
    if login and persist:
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


def normalized_comment_body(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def capacity_response_projection(comment: dict[str, Any]) -> dict[str, Any]:
    body = str(comment.get("body") or "")
    normalized = body.lower()
    remaining_match = re.search(
        r"(?P<count>\d+)\s+(?:pr\s+)?reviews?\s+(?:are\s+)?remaining", normalized
    ) or re.search(
        r"remaining(?:\s+pr)?\s+reviews?[^\d\n]{0,20}(?P<count>\d+)", normalized
    )
    remaining = int(remaining_match.group("count")) if remaining_match else None
    retry_match = re.search(
        r"next review (?:will be )?available in:?\s*\*{0,2}(?P<guidance>[^\n<]+)",
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
    available_now = any(
        marker in normalized
        for marker in ("review is available now", "reviews are available now")
    )
    capacity_available: bool | None
    if one_at_a_time and active_review:
        capacity_available = False
    elif available_now:
        capacity_available = True
    elif remaining is not None:
        capacity_available = remaining > 0
    elif exhausted or retry_guidance:
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
    state.pop("inflight_trigger", None)
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
    *,
    baseline_review_ids: list[int] | None = None,
    baseline_issue_comment_ids: list[int] | None = None,
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
        "baseline_review_ids": baseline_review_ids
        if baseline_review_ids is not None
        else coderabbit_review_ids(reviews, bot_login),
        "baseline_issue_comment_ids": baseline_issue_comment_ids
        if baseline_issue_comment_ids is not None
        else sorted(
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
    if classified.get("result") == "REVIEW_COMPLETED":
        return classified
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
    persist: bool = True,
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
    if persist:
        return save_review_generation(repo, pr_num, generation)
    return generation


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
            comments = thread["comments"]["nodes"]
            comment_ids = [
                int(comment["databaseId"])
                for comment in comments
                if comment.get("databaseId") is not None
            ]
            root_comment_id = comment_ids[0] if comment_ids else None
            for comment in comments:
                database_id = comment.get("databaseId")
                if database_id is None:
                    continue
                by_comment[int(database_id)] = {
                    "thread_id": thread.get("id"),
                    "root_comment_id": root_comment_id,
                    "comment_ids": comment_ids,
                    "is_resolved": bool(thread.get("isResolved")),
                    "is_outdated": bool(thread.get("isOutdated")),
                }
        page_info = threads["pageInfo"]
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
    return by_comment


def comment_file_path(repo: Repo, pr_num: int, review_id: int, comment_id: int) -> Path:
    return cache_dir(repo, pr_num) / f"review-{review_id}" / f"comment-{comment_id}.md"


def conversation_file_path(
    repo: Repo, pr_num: int, review_id: int, root_comment_id: int
) -> Path:
    return (
        cache_dir(repo, pr_num)
        / f"review-{review_id}"
        / f"conversation-{root_comment_id}.md"
    )


def review_comment_sort_key(comment: dict[str, Any]) -> tuple[str, int]:
    return (
        comment.get("created_at") or comment.get("updated_at") or "",
        object_id(comment),
    )


def conversation_revision(comments: list[dict[str, Any]]) -> str:
    projection = [
        {
            "id": object_id(comment),
            "author": (comment.get("user") or {}).get("login"),
            "created_at": comment.get("created_at"),
            "updated_at": comment.get("updated_at"),
            "body": normalized_comment_body(str(comment.get("body") or "")),
        }
        for comment in comments
    ]
    return hashlib_sha256(json.dumps(projection, sort_keys=True, separators=(",", ":")))


def write_conversation_file(
    path: Path,
    *,
    repo: Repo,
    pr_num: int,
    review_id: int,
    root_comment_id: int,
    thread_id: str | None,
    resolved: bool,
    comments: list[dict[str, Any]],
) -> str:
    revision = conversation_revision(comments)
    metadata = {
        "kind": "coderabbit-review-conversation",
        "repo": repo.slug,
        "pr_num": pr_num,
        "review_id": review_id,
        "root_comment_id": root_comment_id,
        "thread_id": thread_id,
        "resolved": resolved,
        "conversation_revision": revision,
        "turn_count": len(comments),
        "captured_at": utc_now(),
    }
    turns: list[str] = []
    for index, comment in enumerate(comments, start=1):
        turns.extend(
            [
                f"## Turn {index}",
                "",
                f"- `comment_id`: `{object_id(comment)}`",
                f"- `author`: `{(comment.get('user') or {}).get('login') or ''}`",
                f"- `created_at`: `{comment.get('created_at') or ''}`",
                f"- `url`: `{comment.get('html_url') or ''}`",
                "",
                str(comment.get("body") or ""),
                "",
            ]
        )
    write_comment_file(path, metadata, "\n".join(turns).rstrip())
    return revision


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
    conversation_cache: dict[
        int, tuple[list[dict[str, Any]], dict[str, Any] | None, Path, str]
    ] = {}

    for comment in review_comments:
        login = (comment.get("user") or {}).get("login")
        if not is_bot_login(login, bot_login):
            continue
        comment_id = int(comment["id"])
        review_id = int(comment.get("pull_request_review_id") or 0)
        status = thread_status.get(comment_id, {})
        position = comment.get("position")
        resolved = bool(status.get("is_resolved"))
        root_comment_id = int(
            status.get("root_comment_id") or comment.get("in_reply_to_id") or comment_id
        )
        cached_conversation = conversation_cache.get(root_comment_id)
        if cached_conversation is None:
            thread_comment_ids = {
                int(value) for value in status.get("comment_ids", []) if int(value)
            }
            conversation_comments = sorted(
                [
                    item
                    for item in review_comments
                    if (
                        object_id(item) in thread_comment_ids
                        if thread_comment_ids
                        else object_id(item) == root_comment_id
                        or item.get("in_reply_to_id") == root_comment_id
                    )
                ],
                key=review_comment_sort_key,
            )
            latest_bot_comment = next(
                (
                    item
                    for item in reversed(conversation_comments)
                    if is_bot_login((item.get("user") or {}).get("login"), bot_login)
                ),
                None,
            )
            root_review_id = next(
                (
                    int(item.get("pull_request_review_id") or 0)
                    for item in conversation_comments
                    if object_id(item) == root_comment_id
                ),
                review_id,
            )
            conversation_path = conversation_file_path(
                repo, pr_num, root_review_id, root_comment_id
            )
            revision = write_conversation_file(
                conversation_path,
                repo=repo,
                pr_num=pr_num,
                review_id=root_review_id,
                root_comment_id=root_comment_id,
                thread_id=status.get("thread_id"),
                resolved=resolved,
                comments=conversation_comments,
            )
            conversation_cache[root_comment_id] = (
                conversation_comments,
                latest_bot_comment,
                conversation_path,
                revision,
            )
        else:
            (
                conversation_comments,
                latest_bot_comment,
                conversation_path,
                revision,
            ) = cached_conversation
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
                "root_comment_id": root_comment_id,
                "resolved": resolved,
                "outdated": bool(status.get("is_outdated") or position is None),
                "conversation_revision": revision,
                "conversation_path": str(conversation_path),
                "latest_comment_id": object_id(conversation_comments[-1])
                if conversation_comments
                else comment_id,
                "latest_bot_comment_id": object_id(latest_bot_comment)
                if latest_bot_comment
                else comment_id,
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
        review_id = 0
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
                "review_commit_id": None,
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
    finding_head_oid = metadata.get("review_commit_id") or (
        current_head_oid if metadata.get("kind") == "in-diff" else None
    )
    conversation_path = metadata.get("conversation_path")
    return {
        "comment_id": metadata["comment_id"],
        "root_comment_id": metadata.get("root_comment_id"),
        "kind": metadata["kind"],
        "file_path": conversation_path or str(record["path"]),
        "body_path": str(record["path"]),
        "conversation_path": conversation_path,
        "conversation_revision": metadata.get("conversation_revision"),
        "latest_comment_id": metadata.get("latest_comment_id"),
        "latest_bot_comment_id": metadata.get("latest_bot_comment_id"),
        "body_sha256": metadata.get("body_sha256"),
        "updated_at": metadata.get("updated_at") or metadata.get("posted_at"),
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


def in_diff_comment_matches_review_generation(
    metadata: dict[str, Any],
    head_oid: str | None,
    generation: dict[str, Any] | None,
) -> bool:
    if isinstance(generation, dict) and generation.get("schema") == GENERATION_SCHEMA:
        accepted_review_id = generation.get("accepted_review_id")
        if generation.get("result") == "REVIEW_COMPLETED" and accepted_review_id:
            return metadata.get("review_id") == accepted_review_id
        expected_head_oid = generation.get("expected_head_oid")
        if expected_head_oid:
            return metadata.get("review_commit_id") == expected_head_oid
    return comment_matches_review_head(metadata, head_oid)


def is_open_finding_record(
    record: dict[str, Any],
    head_oid: str | None,
    out_of_diff_dispositions: dict[str, dict[str, Any]] | None = None,
    generation: dict[str, Any] | None = None,
) -> bool:
    metadata = record["metadata"]
    body = str(record.get("body") or "")
    if metadata.get("resolved") or metadata.get("thread_parent") is not None:
        return False
    if metadata.get("source") == "trigger-ack":
        return False
    if metadata.get("kind") == "in-diff":
        return in_diff_comment_matches_review_generation(metadata, head_oid, generation)
    disposition = (out_of_diff_dispositions or {}).get(
        str(int(metadata.get("comment_id") or 0))
    )
    if (
        isinstance(disposition, dict)
        and disposition.get("body_sha256") == metadata.get("body_sha256")
        and disposition.get("updated_at")
        == (metadata.get("updated_at") or metadata.get("posted_at"))
    ):
        return False
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


def out_of_diff_comment_matches_review_generation(
    metadata: dict[str, Any], generation: dict[str, Any] | None
) -> bool:
    if (
        metadata.get("kind") != "out-of-diff"
        or metadata.get("source") != "issue-comment"
        or not isinstance(generation, dict)
        or generation.get("schema") != GENERATION_SCHEMA
    ):
        return False
    comment_id = int(metadata.get("comment_id") or 0)
    baseline_ids = {
        int(value) for value in generation.get("baseline_issue_comment_ids", [])
    }
    if comment_id == 0 or comment_id in baseline_ids:
        return False
    posted_at = parse_time(metadata.get("posted_at"))
    triggered_at = parse_time(generation.get("triggered_at"))
    return (
        posted_at is not None and triggered_at is not None and posted_at >= triggered_at
    )


def is_actionable_finding_record(
    record: dict[str, Any],
    head_oid: str | None,
    out_of_diff_dispositions: dict[str, dict[str, Any]],
    generation: dict[str, Any] | None,
    conversation_actions: dict[str, dict[str, Any]] | None = None,
) -> bool:
    if not is_open_finding_record(
        record, head_oid, out_of_diff_dispositions, generation
    ):
        return False
    metadata = record["metadata"]
    if metadata.get("kind") == "in-diff":
        root_comment_id = str(
            int(metadata.get("root_comment_id") or metadata.get("comment_id") or 0)
        )
        action = (conversation_actions or {}).get(root_comment_id)
        if not isinstance(action, dict):
            return True
        if action.get("status") == "resolved":
            return True
        return action.get("latest_bot_comment_id") != metadata.get(
            "latest_bot_comment_id"
        )
    return out_of_diff_comment_matches_review_generation(metadata, generation)


def conversation_resolution_state(
    record: dict[str, Any],
    conversation_actions: dict[str, dict[str, Any]],
) -> str:
    metadata = record["metadata"]
    if metadata.get("resolved"):
        return "resolved"
    root_comment_id = str(
        int(metadata.get("root_comment_id") or metadata.get("comment_id") or 0)
    )
    action = conversation_actions.get(root_comment_id)
    if not isinstance(action, dict):
        return "actionable"
    if action.get("status") == "resolved":
        return "pushback"
    if action.get("latest_bot_comment_id") != metadata.get("latest_bot_comment_id"):
        return "pushback"
    return "awaiting_coderabbit"


def mark_conversation_awaiting(
    repo: Repo,
    pr_num: int,
    finding: dict[str, Any],
    outcome: dict[str, Any],
    reply: dict[str, Any] | None,
    head_oid: str,
) -> dict[str, Any]:
    root_comment_id = int(
        finding.get("root_comment_id") or finding.get("comment_id") or 0
    )
    if finding.get("kind") != "in-diff" or not root_comment_id:
        return {}
    if not (reply or {}).get("reply_id"):
        raise DriverError(
            f"conversation {root_comment_id} cannot await CodeRabbit without an exact reply readback"
        )
    action = {
        "root_comment_id": root_comment_id,
        "thread_id": finding.get("thread_id"),
        "status": "awaiting_coderabbit",
        "conversation_revision": finding.get("conversation_revision"),
        "latest_bot_comment_id": finding.get("latest_bot_comment_id"),
        "outcome": outcome.get("outcome"),
        "commit_sha": outcome.get("commit_sha"),
        "reply_id": (reply or {}).get("reply_id"),
        "reply_url": (reply or {}).get("reply_url"),
        "head_oid": head_oid,
        "recorded_at": utc_now(),
    }
    state = load_state(repo, pr_num)
    actions = state.setdefault("conversation_actions", {})
    actions[str(root_comment_id)] = action
    save_state(repo, pr_num, state)
    return action


def mark_out_of_diff_fixed_disposition(
    repo: Repo,
    pr_num: int,
    finding: dict[str, Any],
    outcome: dict[str, Any],
    reply: dict[str, Any] | None = None,
) -> None:
    if finding.get("kind") != "out-of-diff" or outcome.get("outcome") != "fixed":
        return
    comment_id = int(finding.get("comment_id") or 0)
    body_sha256 = finding.get("body_sha256")
    updated_at = finding.get("updated_at")
    if (
        not comment_id
        or not body_sha256
        or not updated_at
        or not outcome.get("commit_sha")
    ):
        raise DriverError(
            "out-of-diff fix disposition is missing exact binding evidence"
        )
    state = load_state(repo, pr_num)
    dispositions = state.setdefault("out_of_diff_dispositions", {})
    dispositions[str(comment_id)] = {
        "status": "fixed_and_replied" if reply else "fixed",
        "body_sha256": body_sha256,
        "updated_at": updated_at,
        "commit_sha": outcome["commit_sha"],
        "reply_id": (reply or {}).get("reply_id"),
        "reply_url": (reply or {}).get("reply_url"),
        "recorded_at": utc_now(),
    }
    save_state(repo, pr_num, state)


def poll(
    repo: Repo,
    pr_num: int,
    head_oid: str | None = None,
    persist_state: bool = True,
) -> dict[str, Any]:
    reviews = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/reviews")
    review_comments = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/comments")
    issue_comments = gh_paginated_array(f"/repos/{repo.slug}/issues/{pr_num}/comments")
    bot_login = discover_bot_login(
        repo,
        pr_num,
        reviews,
        review_comments,
        issue_comments,
        persist=persist_state,
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
        "author_login": (latest_scoped_review.get("user") or {}).get("login")
        if latest_scoped_review
        else None,
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
    active_generation = state.get("active_generation")
    out_of_diff_dispositions = state.get("out_of_diff_dispositions", {})
    if not isinstance(out_of_diff_dispositions, dict):
        out_of_diff_dispositions = {}
    conversation_actions = state.get("conversation_actions", {})
    if not isinstance(conversation_actions, dict):
        conversation_actions = {}
    previous_hashes: dict[str, str] = state.get("seen_comment_hashes", {})
    previous_status: dict[str, dict[str, Any]] = state.get("comment_status", {})
    current_hashes: dict[str, str] = {}
    current_status: dict[str, dict[str, Any]] = {}
    seen_by_review: dict[str, list[int]] = {}

    new_comments: list[dict[str, Any]] = []
    actionable_comments: list[dict[str, Any]] = []
    unresolved_findings: list[dict[str, Any]] = []
    conversation_statuses: list[dict[str, Any]] = []
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
        if is_open_finding_record(
            record,
            head_oid,
            out_of_diff_dispositions,
            active_generation if isinstance(active_generation, dict) else None,
        ):
            unresolved_findings.append(output_metadata(record, head_oid))
        if is_actionable_finding_record(
            record,
            head_oid,
            out_of_diff_dispositions,
            active_generation if isinstance(active_generation, dict) else None,
            conversation_actions,
        ):
            actionable_comments.append(output_metadata(record, head_oid))
        if (
            metadata.get("kind") == "in-diff"
            and metadata.get("thread_parent") is None
            and in_diff_comment_matches_review_generation(
                metadata,
                head_oid,
                active_generation if isinstance(active_generation, dict) else None,
            )
        ):
            conversation = output_metadata(record, head_oid)
            conversation["dialogue_state"] = conversation_resolution_state(
                record, conversation_actions
            )
            conversation_statuses.append(conversation)
        if (
            previous_hashes.get(key) != digest
            and not metadata.get("resolved")
            and metadata.get("source") != "trigger-ack"
            and (
                metadata.get("kind") != "in-diff"
                or in_diff_comment_matches_review_generation(
                    metadata,
                    head_oid,
                    active_generation if isinstance(active_generation, dict) else None,
                )
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

    new_state = dict(state)
    updated_conversation_actions = dict(conversation_actions)
    for conversation in conversation_statuses:
        root_comment_id = str(int(conversation.get("root_comment_id") or 0))
        action = updated_conversation_actions.get(root_comment_id)
        if not isinstance(action, dict):
            continue
        action = dict(action)
        action["status"] = conversation["dialogue_state"]
        action["last_observed_at"] = utc_now()
        if conversation["dialogue_state"] == "resolved":
            action["resolved_thread_id"] = conversation.get("thread_id")
            action["resolved_at"] = utc_now()
        updated_conversation_actions[root_comment_id] = action
    new_state.update(
        {
            "last_polled_at": utc_now(),
            "last_review_decision": aggregate_decision,
            "last_review_decision_source": aggregate_decision_signal.get("source"),
            "last_bot_login": bot_login,
            "latest_review_id": latest_review.get("id") if latest_review else None,
            "latest_decision_review_id": aggregate_decision_signal.get("review_id"),
            "seen_comment_hashes": current_hashes,
            "comment_status": current_status,
            "seen_comment_ids_per_review": seen_by_review,
            "conversation_actions": updated_conversation_actions,
        }
    )
    if persist_state:
        save_state(repo, pr_num, new_state)
    if bot_login and persist_state:
        save_bot_login(repo, bot_login, pr_num)

    current_generation_head_oid = None
    if isinstance(active_generation, dict):
        current_generation_head_oid = str(
            pr_metadata(repo, pr_num).get("headRefOid") or ""
        )
    generation = (
        record_review_generation_observation(
            repo,
            pr_num,
            active_generation,
            current_generation_head_oid or "",
            reviews,
            issue_comments,
            bot_login,
            persist=persist_state,
        )
        if isinstance(active_generation, dict)
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
        "approval_signal": aggregate_decision_signal,
        "current_head_oid": head_oid,
        "terminal": generation.get("result") != "WAITING_FOR_REVIEW",
        "outcome": outcome,
        "decision_signal": decision_signal,
        "review_decision_source": decision_signal.get("source"),
        "latest_decision_review_id": decision_signal.get("review_id"),
        "latest_review_at": latest_scoped_review_at.isoformat()
        if latest_scoped_review_at
        else None,
        "review_completed": generation.get("result") == "REVIEW_COMPLETED",
        "generation": generation,
        "new_comments": new_comments,
        "actionable_comments": actionable_comments,
        "unresolved_findings": unresolved_findings,
        "conversation_statuses": conversation_statuses,
        "all_conversations_resolved": not unresolved_findings,
        "resolved_conversations": [
            conversation
            for conversation in conversation_statuses
            if conversation.get("dialogue_state") == "resolved"
        ],
        "resolved_since_last_poll": resolved_since_last_poll,
        "bot_login": bot_login,
    }


def generation_suppresses_trigger(
    generation: dict[str, Any] | None,
) -> tuple[bool, str | None]:
    if not generation or generation.get("schema") != GENERATION_SCHEMA:
        return False, None
    result = generation.get("result")
    if result == "REVIEW_COMPLETED":
        return True, "the single review generation is already complete"
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


def inflight_command_candidates(
    marker: dict[str, Any], issue_comments: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    baseline = {int(value) for value in marker.get("baseline_issue_comment_ids", [])}
    started_at = parse_time(marker.get("started_at"))
    expected_body = normalized_comment_body(str(marker.get("body") or ""))
    actor_login = marker.get("actor_login")
    if not expected_body:
        raise DriverError("persisted in-flight provider command is malformed")
    if not isinstance(actor_login, str) or not actor_login:
        return []
    candidates: list[dict[str, Any]] = []
    for comment in issue_comments:
        if object_id(comment) in baseline:
            continue
        if (comment.get("user") or {}).get("login") != actor_login:
            continue
        if normalized_comment_body(str(comment.get("body") or "")) != expected_body:
            continue
        observed_at = parse_time(comment.get("created_at") or comment.get("updated_at"))
        if started_at and (
            observed_at is None or observed_at < started_at - timedelta(seconds=5)
        ):
            continue
        candidates.append(comment)
    return sorted(candidates, key=issue_comment_sort_key)


def trigger_review(
    repo: Repo, pr_num: int, mode: str, label: str, force: bool = False
) -> dict[str, Any]:
    with provider_command_lock(repo, pr_num):
        return _trigger_review(repo, pr_num, mode, label, force)


def _trigger_review(
    repo: Repo, pr_num: int, mode: str, label: str, force: bool
) -> dict[str, Any]:
    enabled, _ = repo_label_enabled(repo, label)
    if not enabled:
        raise DriverError(
            "CodeRabbit marker label is absent from repository", exit_code=1
        )

    completion = single_review_completion(repo, pr_num)
    if completion:
        return {
            "posted": False,
            "suppressed": True,
            "suppression_reason": "single-review-policy:pr-review-already-completed",
            "single_review_completion": completion,
        }

    metadata = pr_metadata(repo, pr_num)
    expected_head_oid = str(metadata.get("headRefOid") or "")
    if not expected_head_oid:
        raise DriverError(f"could not resolve PR head for {repo.slug}#{pr_num}")

    state = load_state(repo, pr_num)
    inflight = state.get("inflight_trigger")
    recovered_trigger = False
    if isinstance(inflight, dict):
        reviews = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/reviews")
        issue_comments = gh_paginated_array(
            f"/repos/{repo.slug}/issues/{pr_num}/comments"
        )
        candidates = inflight_command_candidates(inflight, issue_comments)
        if len(candidates) > 1:
            raise DriverError(
                "ambiguous in-flight review trigger identity; inspect exact command comments"
            )
        if not candidates:
            if not force:
                raise DriverError(
                    "in-flight review trigger has no provider identity yet; retry reconciliation or explicitly supersede it"
                )
            abandoned = dict(inflight)
            abandoned.update(
                {
                    "abandoned_at": utc_now(),
                    "abandon_reason": "explicit-force-with-no-provider-identity",
                }
            )
            state.setdefault("inflight_trigger_history", []).append(abandoned)
            state.pop("inflight_trigger", None)
            save_state(repo, pr_num, state)
        else:
            recovered_mode = str(inflight.get("mode") or "")
            recovered_head_oid = str(inflight.get("expected_head_oid") or "")
            if recovered_mode not in TRIGGER_BODIES or not recovered_head_oid:
                raise DriverError("persisted in-flight review trigger is malformed")
            bot_login = discover_bot_login(
                repo, pr_num, reviews=reviews, issue_comments=issue_comments
            )
            body = TRIGGER_BODIES[recovered_mode]
            response = candidates[0]
            generation = new_review_generation(
                repo,
                pr_num,
                recovered_mode,
                recovered_head_oid,
                reviews,
                issue_comments,
                bot_login,
                response,
                baseline_review_ids=[
                    int(value) for value in inflight.get("baseline_review_ids", [])
                ],
                baseline_issue_comment_ids=[
                    int(value)
                    for value in inflight.get("baseline_issue_comment_ids", [])
                ],
            )
            generation.update(
                {
                    "posted": True,
                    "suppressed": False,
                    "trigger_body": body,
                    "reconciled_inflight": True,
                    "supersession_deferred_reason": "reconciled-inflight-trigger"
                    if force
                    else None,
                }
            )
            activate_review_generation(repo, pr_num, generation)
            mode = recovered_mode
            recovered_trigger = True

    if not recovered_trigger:
        existing = active_review_generation(repo, pr_num)
        if existing and existing.get("result") == "REVIEW_COMPLETED":
            return {
                **existing,
                "posted": False,
                "suppressed": True,
                "suppression_reason": "single-review-policy:generation-already-completed",
            }
        replaceable_head_change = bool(
            existing
            and existing.get("result") == "BLOCKED"
            and existing.get("next_permitted_action")
            == "start_new_generation_for_current_head"
            and existing.get("expected_head_oid") != expected_head_oid
        )
        suppression_generation = None if force or replaceable_head_change else existing
        suppressed, reason = generation_suppresses_trigger(suppression_generation)
        if suppressed:
            return {
                **(suppression_generation or {}),
                "posted": False,
                "suppressed": True,
                "suppression_reason": reason,
            }

        reviews = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/reviews")
        issue_comments = gh_paginated_array(
            f"/repos/{repo.slug}/issues/{pr_num}/comments"
        )
        bot_login = discover_bot_login(
            repo, pr_num, reviews=reviews, issue_comments=issue_comments
        )
        body = TRIGGER_BODIES[mode]
        inflight = {
            "schema": "coderabbit-inflight-trigger-v1",
            "repo": repo.slug,
            "pr_num": pr_num,
            "mode": mode,
            "body": body,
            "actor_login": authenticated_actor_login(),
            "expected_head_oid": expected_head_oid,
            "started_at": utc_now(),
            "baseline_review_ids": coderabbit_review_ids(reviews, bot_login),
            "baseline_issue_comment_ids": sorted(
                object_id(comment) for comment in issue_comments if object_id(comment)
            ),
        }
        state = load_state(repo, pr_num)
        state["inflight_trigger"] = inflight
        save_state(repo, pr_num, state)
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
    generation.update(
        {
            "result": "WAITING_FOR_REVIEW",
            "next_permitted_action": "poll",
            "posted": True,
            "suppressed": False,
            "trigger_body": body,
        }
    )
    return save_review_generation(repo, pr_num, generation)


def capacity_query(repo: Repo, pr_num: int, refresh: bool = False) -> dict[str, Any]:
    with provider_command_lock(repo, pr_num):
        return _capacity_query(repo, pr_num, refresh)


def _capacity_query(repo: Repo, pr_num: int, refresh: bool) -> dict[str, Any]:
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
    recovered_inflight = False
    if isinstance(existing, dict) and existing.get("status") == "posting":
        issue_comments = gh_paginated_array(
            f"/repos/{repo.slug}/issues/{pr_num}/comments"
        )
        candidates = inflight_command_candidates(existing, issue_comments)
        if len(candidates) > 1:
            generation.update(
                {
                    "result": "BLOCKED",
                    "blocked_reason": "ambiguous in-flight capacity-query identity",
                    "next_permitted_action": "inspect_capacity_query_comments",
                }
            )
            return save_review_generation(repo, pr_num, generation)
        if not candidates:
            if not refresh:
                raise DriverError(
                    "in-flight capacity query has no provider identity yet; retry reconciliation or use --new-query to supersede it"
                )
            abandoned = dict(existing)
            abandoned.update(
                {
                    "abandoned_at": utc_now(),
                    "abandon_reason": "explicit-refresh-with-no-provider-identity",
                }
            )
            generation.setdefault("capacity_query_history", []).append(abandoned)
            generation["capacity_query"] = None
            save_review_generation(repo, pr_num, generation)
            existing = None
        else:
            response = candidates[0]
            existing.update(
                {
                    "status": "posted",
                    "generation_id": object_id(response),
                    "query_comment_id": object_id(response),
                    "query_comment_url": response.get("html_url"),
                    "queried_at": response.get("created_at")
                    or response.get("updated_at")
                    or existing.get("started_at"),
                }
            )
            generation["capacity_query"] = existing
            save_review_generation(repo, pr_num, generation)
            recovered_inflight = True

    if isinstance(existing, dict) and (not refresh or recovered_inflight):
        query = dict(existing)
    else:
        if isinstance(existing, dict):
            generation.setdefault("capacity_query_history", []).append(existing)
        issue_comments = gh_paginated_array(
            f"/repos/{repo.slug}/issues/{pr_num}/comments"
        )
        query = {
            "status": "posting",
            "generation_id": None,
            "query_comment_id": None,
            "query_comment_url": None,
            "body": CAPACITY_QUERY_BODY,
            "actor_login": authenticated_actor_login(),
            "started_at": utc_now(),
            "queried_at": None,
            "baseline_issue_comment_ids": sorted(
                object_id(comment) for comment in issue_comments if object_id(comment)
            ),
            "response": None,
        }
        generation["capacity_query"] = query
        save_review_generation(repo, pr_num, generation)
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
        query.update(
            {
                "status": "posted",
                "generation_id": object_id(response),
                "query_comment_id": object_id(response),
                "query_comment_url": response.get("html_url"),
                "queried_at": response.get("created_at")
                or response.get("updated_at")
                or query["started_at"],
            }
        )
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
    result = poll(repo, pr_num, head_oid=head_oid, persist_state=False)
    current_head_oid = str(pr_metadata(repo, pr_num).get("headRefOid") or "")
    if current_head_oid != head_oid:
        raise DriverError("PR head changed while collecting open findings")
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
    state = load_state(repo, pr_num)
    if isinstance(state.get("inflight_trigger"), dict):
        return {
            "trigger": True,
            "reason": "initial-trigger-policy:reconcile-inflight-trigger",
        }
    active = state.get("active_generation")
    generation = active if isinstance(active, dict) else None
    if generation and generation.get("result") == "REVIEW_COMPLETED":
        return {
            "trigger": False,
            "reason": "initial-trigger-policy:single-review-generation-completed",
            "generation_result": "REVIEW_COMPLETED",
        }
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
    if set(raw) != OUTCOME_FIELDS:
        missing = sorted(OUTCOME_FIELDS - set(raw))
        unexpected = sorted(set(raw) - OUTCOME_FIELDS)
        raise DriverError(
            f"agent outcome for comment {comment_id} has invalid fields; "
            f"missing={missing}, unexpected={unexpected}"
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
    }


def ensure_resolution_reply_body(outcome: dict[str, Any], reply_path: Path) -> str:
    body_file = outcome.get("reply_body_file")
    if body_file:
        if not Path(body_file).is_file():
            raise DriverError(
                f"reply body file for comment {outcome['comment_id']} does not exist: {body_file}"
            )
        return str(body_file)
    if outcome.get("outcome") != "fixed":
        raise DriverError(
            f"resolution outcome for comment {outcome['comment_id']} is missing a reply body"
        )
    commit_sha = outcome.get("commit_sha")
    if not commit_sha:
        raise DriverError(
            f"fixed outcome for comment {outcome['comment_id']} is missing a commit SHA"
        )
    reply_path.parent.mkdir(parents=True, exist_ok=True)
    reply_path.write_text(
        f"Fixed in `{commit_sha}`.\n\n{outcome['rationale']}\n",
        encoding="utf-8",
    )
    outcome["reply_body_file"] = str(reply_path)
    return str(reply_path)


def semantic_outcome(outcome: dict[str, Any]) -> dict[str, Any]:
    return {field: outcome.get(field) for field in OUTCOME_FIELDS}


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
    if outcome["outcome"] in RESOLUTION_OUTCOMES:
        ensure_resolution_reply_body(outcome, outcome_path.with_suffix(".reply.md"))
    outcome_path.write_text(
        json.dumps(semantic_outcome(outcome), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
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
    if not reply_id or normalized_comment_body(
        str(reply.get("body") or "")
    ) != normalized_comment_body(body):
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


def mark_out_of_diff_disposition(
    repo: Repo,
    pr_num: int,
    target: dict[str, Any],
    readback: dict[str, Any],
) -> None:
    comment_id = object_id(target)
    state = load_state(repo, pr_num)
    dispositions = state.setdefault("out_of_diff_dispositions", {})
    dispositions[str(comment_id)] = {
        "status": "replied",
        "body_sha256": hashlib_sha256(str(target.get("body") or "")),
        "updated_at": target.get("updated_at") or target.get("created_at"),
        "reply_id": readback["id"],
        "reply_url": readback["url"],
        "recorded_at": utc_now(),
    }
    save_state(repo, pr_num, state)


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
                and normalized_comment_body(str(comment.get("body") or ""))
                == normalized_comment_body(body)
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
            if normalized_comment_body(str(comment.get("body") or ""))
            == normalized_comment_body(issue_body)
        ),
        None,
    )
    if duplicate:
        readback = reply_readback(duplicate, issue_body, None)
        mark_out_of_diff_disposition(repo, pr_num, issue_target, readback)
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
    mark_out_of_diff_disposition(repo, pr_num, issue_target, readback)
    return reply_result(repo, pr_num, comment_id, "issue-comment", True, readback)


def latest_outcome_artifact(repo: Repo, pr_num: int, comment_id: int) -> Path:
    candidates = list(
        cache_dir(repo, pr_num).glob(f"iter-*/agent-{comment_id}.prompt.outcome.json")
    )
    if not candidates:
        raise DriverError(
            f"conversation {comment_id} is missing its durable fixer outcome artifact"
        )

    def iteration_number(path: Path) -> int:
        try:
            return int(path.parent.name.removeprefix("iter-"))
        except ValueError:
            return -1

    return max(
        candidates, key=lambda path: (iteration_number(path), path.stat().st_mtime_ns)
    )


def recover_missing_conversation_replies(
    repo: Repo, pr_num: int
) -> list[dict[str, Any]]:
    state = load_state(repo, pr_num)
    actions = state.get("conversation_actions", {})
    if not isinstance(actions, dict):
        return []
    pending = [
        (int(root_comment_id), dict(action))
        for root_comment_id, action in actions.items()
        if isinstance(action, dict)
        and action.get("status") in {"awaiting_coderabbit", "resolved"}
        and not action.get("reply_id")
        and action.get("thread_id")
    ]
    recovered: list[dict[str, Any]] = []
    for root_comment_id, action in sorted(pending):
        outcome_path = latest_outcome_artifact(repo, pr_num, root_comment_id)
        try:
            raw = json.loads(outcome_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as err:
            raise DriverError(
                f"could not load durable fixer outcome for conversation {root_comment_id}: {outcome_path}"
            ) from err
        outcome = validate_outcome(raw, root_comment_id)
        if outcome.get("outcome") not in RESOLUTION_OUTCOMES:
            raise DriverError(
                f"conversation {root_comment_id} has non-resolution outcome {outcome.get('outcome')!r}"
            )
        if outcome.get("outcome") in FIX_OUTCOMES and action.get(
            "commit_sha"
        ) != outcome.get("commit_sha"):
            raise DriverError(
                f"conversation {root_comment_id} action/outcome commit identity mismatch"
            )
        body_file = ensure_resolution_reply_body(
            outcome, outcome_path.with_suffix(".reply.md")
        )
        outcome_path.write_text(
            json.dumps(semantic_outcome(outcome), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        reply = post_reply(repo, pr_num, root_comment_id, body_file)
        current_state = load_state(repo, pr_num)
        current_actions = current_state.setdefault("conversation_actions", {})
        current_action = current_actions.get(str(root_comment_id))
        if not isinstance(current_action, dict):
            raise DriverError(
                f"conversation {root_comment_id} action disappeared during reply recovery"
            )
        current_action["reply_id"] = reply.get("reply_id")
        current_action["reply_url"] = reply.get("reply_url")
        current_action["reply_body_file"] = body_file
        current_action["reply_recovered_at"] = utc_now()
        save_state(repo, pr_num, current_state)
        recovered.append(
            {
                "root_comment_id": root_comment_id,
                "outcome_file": str(outcome_path),
                "reply_result": reply,
            }
        )
    return recovered


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
    candidates = poll_result.get("actionable_comments", [])
    comments_by_id = {
        int(comment.get("comment_id") or 0): comment
        for comment in candidates
        if not comment.get("resolved")
        and int(comment.get("comment_id") or 0) not in handled_comment_ids
    }
    comments_by_id.pop(0, None)
    return list(comments_by_id.values())


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
    completion = single_review_completion(repo, args.pr_num)
    if completion:
        return {
            "repo": repo.slug,
            "pr_num": args.pr_num,
            "pr": metadata,
            "enabled": enabled_payload,
            "loop_started_at": loop_started_at,
            "loop_completed_at": utc_now(),
            "terminal": completion.get("terminal"),
            "terminal_reason": completion.get("terminal_reason"),
            "outcome": completion.get("outcome"),
            "needs_caller_decision": completion.get("needs_caller_decision", False),
            "caller_decision_outcomes": completion.get("caller_decision_outcomes", []),
            "review_decision": completion.get("review_decision", "NONE"),
            "approval_signal": {
                "decision": completion.get("approval_review_state"),
                "review_id": completion.get("approval_review_id"),
                "commit_id": completion.get("approval_review_commit_id"),
                "submitted_at": completion.get("approval_review_submitted_at"),
                "author_login": completion.get("approval_review_author_login"),
            },
            "all_conversations_resolved": completion.get(
                "all_conversations_resolved", False
            ),
            "resolved_conversations": completion.get("resolved_conversations", []),
            "generation_result": completion.get("generation_result"),
            "generation": completion.get("generation", {}),
            "initial_trigger_decision": {
                "trigger": False,
                "reason": "single-review-policy:pr-review-already-completed",
            },
            "initial_trigger_result": None,
            "iterations": completion.get("iterations", []),
            "rate_limit_observations": completion.get("rate_limit_observations", []),
            "completion_reused": True,
            "single_review_completion": completion,
            "poll_cadence_enforcement": {
                "location": "tools/coderabbit_review_driver.py review-loop wait_for_loop_poll_cadence",
                "min_interval_seconds": min_poll_interval,
            },
        }

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
        initial_trigger = trigger_review(
            repo,
            args.pr_num,
            args.mode,
            args.label,
        )
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
    final_approval_signal: dict[str, Any] = {
        "decision": "NONE",
        "source": "none",
    }
    final_all_conversations_resolved = False
    final_resolved_conversations: list[dict[str, Any]] = []
    rate_limit_observations: list[str] = []
    remediation_passes = 0

    while True:
        iteration_dir = cache_dir(repo, args.pr_num) / f"iter-{iteration_index}"
        iteration_dir.mkdir(parents=True, exist_ok=True)
        cadence = wait_for_loop_poll_cadence(repo, args.pr_num, min_poll_interval)
        poll_started_at = utc_now()
        poll_result, head_oid, head_committed_at = poll_current_pr_head(
            repo, args.pr_num, worktree_path, pr_branch
        )
        metadata = pr_metadata(repo, args.pr_num)
        mark_loop_poll(repo, args.pr_num)
        generation = poll_result.get("generation") or {}
        generation_result = generation.get("result")
        final_review_decision = str(poll_result.get("review_decision") or "NONE")
        final_approval_signal = dict(poll_result.get("approval_signal") or {})
        final_all_conversations_resolved = bool(
            poll_result.get("all_conversations_resolved")
        )
        final_resolved_conversations = list(
            poll_result.get("resolved_conversations") or []
        )
        final_outcome = poll_result.get("outcome")
        actionable_comments = select_actionable_comments(poll_result)
        unresolved_findings = list(poll_result.get("unresolved_findings") or [])
        iteration: dict[str, Any] = {
            "iteration": iteration_index,
            "poll_started_at": poll_started_at,
            "poll_completed_at": utc_now(),
            "cadence": cadence,
            "review_decision": final_review_decision,
            "aggregate_review_decision": poll_result.get("aggregate_review_decision"),
            "approval_signal": final_approval_signal,
            "all_conversations_resolved": final_all_conversations_resolved,
            "conversation_statuses": poll_result.get("conversation_statuses", []),
            "unresolved_findings": unresolved_findings,
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
            "recovered_reply_results": [],
            "push_result": None,
            "trigger_result": None,
        }
        iteration["recovered_reply_results"] = recover_missing_conversation_replies(
            repo, args.pr_num
        )

        if generation_result == "RATE_LIMITED_NO_REVIEW":
            capacity_result = capacity_query(repo, args.pr_num)
            iteration["capacity_result"] = capacity_result
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

        if (
            final_all_conversations_resolved
            and final_approval_signal.get("decision") == "APPROVED"
            and final_approval_signal.get("commit_id") == head_oid
            and final_approval_signal.get("review_id")
        ):
            terminal_reason = "approved"
            iterations.append(iteration)
            break

        if not actionable_comments:
            iterations.append(iteration)
            print(
                f"Waiting for CodeRabbit conversation resolution and exact-current-head approval for {repo.slug}#{args.pr_num}",
                file=sys.stderr,
                flush=True,
            )
            iteration_index += 1
            continue

        if remediation_passes >= MAX_REMEDIATION_PASSES:
            iteration["terminal"] = True
            iteration["decomposition_required"] = True
            iterations.append(iteration)
            terminal_reason = "max_passes_reached"
            break

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

        caller_decision = [
            outcome
            for outcome in iteration["outcomes"]
            if outcome["outcome"] in CALLER_DECISION_OUTCOMES
        ]
        if caller_decision:
            iteration["needs_caller_decision"] = True
            iteration["caller_decision_outcomes"] = caller_decision

        if any(outcome["outcome"] in FIX_OUTCOMES for outcome in iteration["outcomes"]):
            iteration["push_result"] = push_branch(worktree_path, pr_branch)
            wait_for_provider_pr_head(
                repo,
                args.pr_num,
                worktree_path,
                pr_branch,
                iteration["push_result"]["head_sha"],
            )
            head_oid = iteration["push_result"]["head_sha"]

        replies_by_comment: dict[int, dict[str, Any]] = {}
        for outcome in iteration["outcomes"]:
            if outcome["outcome"] in RESOLUTION_OUTCOMES:
                body_file = ensure_resolution_reply_body(
                    outcome,
                    iteration_dir / f"agent-{outcome['comment_id']}.reply.md",
                )
                reply_result = post_reply(
                    repo, args.pr_num, outcome["comment_id"], body_file
                )
                iteration["reply_results"].append(reply_result)
                replies_by_comment[int(outcome["comment_id"])] = reply_result

        findings_by_comment = {
            int(comment["comment_id"]): comment for comment in actionable_comments
        }
        for outcome in iteration["outcomes"]:
            if outcome["outcome"] in CALLER_DECISION_OUTCOMES:
                continue
            finding = findings_by_comment[int(outcome["comment_id"])]
            action = mark_conversation_awaiting(
                repo,
                args.pr_num,
                finding,
                outcome,
                replies_by_comment.get(int(outcome["comment_id"])),
                head_oid,
            )
            if action:
                iteration.setdefault("conversation_actions", []).append(action)
            mark_out_of_diff_fixed_disposition(
                repo,
                args.pr_num,
                finding,
                outcome,
                replies_by_comment.get(int(outcome["comment_id"])),
            )

        iterations.append(iteration)
        if caller_decision:
            terminal_reason = "caller_decision_required"
            break
        remediation_passes += 1
        iteration_index += 1

    needs_caller_decision = terminal_reason in {
        "caller_decision_required",
    }
    final_generation = active_review_generation(repo, args.pr_num) or {}
    caller_decision_outcomes = [
        outcome
        for iteration in iterations
        for outcome in iteration.get("caller_decision_outcomes", [])
    ]
    payload = {
        "repo": repo.slug,
        "pr_num": args.pr_num,
        "pr": metadata,
        "enabled": enabled_payload,
        "loop_started_at": loop_started_at,
        "loop_completed_at": utc_now(),
        "terminal": terminal_reason
        in {"approved", "rate_limited_no_review", "blocked", "max_passes_reached"},
        "terminal_reason": terminal_reason,
        "outcome": (
            "MAX_PASSES_REACHED"
            if terminal_reason == "max_passes_reached"
            else terminal_reason
        ),
        "decomposition_required": terminal_reason == "max_passes_reached",
        "needs_caller_decision": needs_caller_decision,
        "caller_decision_outcomes": caller_decision_outcomes,
        "review_decision": final_review_decision,
        "approval_signal": final_approval_signal,
        "all_conversations_resolved": final_all_conversations_resolved,
        "resolved_conversations": final_resolved_conversations,
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
    if terminal_reason == "approved":
        payload["single_review_completion"] = save_single_review_completion(
            repo, args.pr_num, payload
        )
    return payload


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
    head_oid = str(pr_metadata(repo, args.pr_num).get("headRefOid") or "")
    if not head_oid:
        raise DriverError(f"could not resolve PR head for {repo.slug}#{args.pr_num}")
    payload = poll(repo, args.pr_num, head_oid)
    current_head_oid = str(pr_metadata(repo, args.pr_num).get("headRefOid") or "")
    if current_head_oid != head_oid:
        raise DriverError("PR head changed while polling CodeRabbit evidence")
    print(json.dumps(payload, indent=2, sort_keys=True))
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
    if payload.get("outcome") == "MAX_PASSES_REACHED":
        return 3
    return 0


def command_reply(args: argparse.Namespace) -> int:
    repo = Repo.parse(args.repo)
    payload = post_reply(repo, args.pr_num, args.comment_id, args.body_file)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_recover_replies(args: argparse.Namespace) -> int:
    repo = Repo.parse(args.repo)
    payload = recover_missing_conversation_replies(repo, args.pr_num)
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
        help="Run one CodeRabbit review/application pass with centralized 5-minute poll cadence.",
    )
    review_loop_parser.add_argument("repo")
    review_loop_parser.add_argument("pr_num", type=int)
    review_loop_parser.add_argument(
        "--mode", choices=("incremental", "full"), default="incremental"
    )
    review_loop_parser.add_argument(
        "--initial-trigger",
        choices=("auto", "skip"),
        default="auto",
        help="Initial trigger policy. auto resumes a matching generation; skip requires one for the current head.",
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

    recover_replies = subparsers.add_parser(
        "recover-replies",
        help="Post and read back persisted conversation replies missing from GitHub.",
    )
    recover_replies.add_argument("repo")
    recover_replies.add_argument("pr_num", type=int)
    recover_replies.set_defaults(func=command_recover_replies)

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
