#!/usr/bin/env python3
"""Drive GitHub PR-mode CodeRabbit review through @mentions and review state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
FIX_OUTCOMES = {"fixed", "fixed_and_replied"}
REPLY_OUTCOMES = {"replied", "fixed_and_replied"}
CALLER_DECISION_OUTCOMES = {"rejected", "deferred"}
VALID_OUTCOMES = FIX_OUTCOMES | REPLY_OUTCOMES | CALLER_DECISION_OUTCOMES


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    result = run_gh(["label", "list", "--repo", repo.slug, "--search", label, "--json", "name"])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise DriverError(f"failed to list labels for {repo.slug}: {detail}")
    try:
        labels = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as err:
        raise DriverError(f"gh label list returned invalid JSON: {err}") from err
    if not isinstance(labels, list):
        raise DriverError("gh label list returned non-array JSON")
    return any(label_info.get("name") == label for label_info in labels if isinstance(label_info, dict))


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
    return normalized.startswith("coderabbitai") or normalized.startswith("coderabbit-ai")


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

    reviews = reviews if reviews is not None else gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/reviews")
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
    return max(cr_reviews, key=lambda review: (review.get("submitted_at") or "", int(review.get("id") or 0)))


def normalized_review_decision(latest_review: dict[str, Any] | None) -> str:
    if not latest_review:
        return "NONE"
    state = latest_review.get("state") or "NONE"
    if state in {"APPROVED", "CHANGES_REQUESTED", "COMMENTED"}:
        return state
    return "NONE"


def is_trigger_ack_body(body: str, mode: str) -> bool:
    marker = ACK_MARKERS[mode]
    if mode == "incremental" and ACK_MARKERS["full"] in body:
        return False
    return "Actions performed" in body and marker in body


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
    comment_time = parse_time(issue_comment.get("updated_at") or issue_comment.get("created_at"))
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
    frontmatter = "\n".join(f"{key}: {yaml_value(value)}" for key, value in metadata.items())
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


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
    latest_review = latest_coderabbit_review(reviews, bot_login)
    latest_review_id = int(latest_review["id"]) if latest_review else 0

    for comment in review_comments:
        login = (comment.get("user") or {}).get("login")
        if not is_bot_login(login, bot_login):
            continue
        comment_id = int(comment["id"])
        review_id = int(comment.get("pull_request_review_id") or 0)
        status = thread_status.get(comment_id, {})
        position = comment.get("position")
        resolved = bool(status.get("is_resolved") or status.get("is_outdated") or position is None)
        body = comment.get("body") or ""
        metadata = base_comment_metadata(
            repo, pr_num, comment_id, "in-diff", "review-comment", review_id, body, login
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
                "html_url": comment.get("html_url"),
            }
        )
        path = comment_file_path(repo, pr_num, review_id, comment_id)
        records.append({"key": f"review-comment:{comment_id}", "path": path, "body": body, "metadata": metadata})

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
                "resolved": bool(is_ack or (review_id != 0 and review_id != latest_review_id)),
                "outdated": bool(review_id != 0 and review_id != latest_review_id),
                "posted_at": comment.get("created_at"),
                "updated_at": comment.get("updated_at"),
                "html_url": comment.get("html_url"),
            }
        )
        path = comment_file_path(repo, pr_num, review_id, comment_id)
        records.append({"key": f"issue-comment:{comment_id}", "path": path, "body": body, "metadata": metadata})

    return records


def output_metadata(record: dict[str, Any]) -> dict[str, Any]:
    metadata = record["metadata"]
    return {
        "comment_id": metadata["comment_id"],
        "kind": metadata["kind"],
        "file_path": str(record["path"]),
        "code_path": metadata.get("code_path"),
        "code_line": metadata.get("code_line"),
        "review_id": metadata.get("review_id"),
        "thread_parent": metadata.get("thread_parent"),
        "resolved": metadata.get("resolved"),
    }


def poll(repo: Repo, pr_num: int) -> dict[str, Any]:
    reviews = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/reviews")
    review_comments = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/comments")
    issue_comments = gh_paginated_array(f"/repos/{repo.slug}/issues/{pr_num}/comments")
    bot_login = discover_bot_login(repo, pr_num, reviews, review_comments, issue_comments)
    thread_status = graphql_review_threads(repo, pr_num)

    latest_review = latest_coderabbit_review(reviews, bot_login)
    decision = normalized_review_decision(latest_review)
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
    for record in records:
        key = record["key"]
        metadata = record["metadata"]
        digest = metadata["body_sha256"] + ":" + str(metadata.get("updated_at") or metadata.get("posted_at"))
        current_hashes[key] = digest
        current_status[key] = {
            "comment_id": metadata["comment_id"],
            "resolved": metadata.get("resolved"),
            "kind": metadata.get("kind"),
            "source": metadata.get("source"),
        }
        seen_by_review.setdefault(str(metadata["review_id"]), []).append(int(metadata["comment_id"]))
        write_comment_file(record["path"], metadata, record["body"])
        if (
            not metadata.get("resolved")
            and metadata.get("kind") == "in-diff"
            and metadata.get("source") != "trigger-ack"
        ):
            actionable_comments.append(output_metadata(record))
        if (
            previous_hashes.get(key) != digest
            and not metadata.get("resolved")
            and metadata.get("source") != "trigger-ack"
        ):
            new_comments.append(output_metadata(record))

    resolved_since_last_poll: list[int] = []
    for key, old_status in previous_status.items():
        new_status = current_status.get(key)
        if not new_status:
            continue
        if not old_status.get("resolved") and new_status.get("resolved"):
            resolved_since_last_poll.append(int(new_status["comment_id"]))

    new_state = {
        "last_polled_at": utc_now(),
        "last_review_decision": decision,
        "last_bot_login": bot_login,
        "latest_review_id": latest_review.get("id") if latest_review else None,
        "seen_comment_hashes": current_hashes,
        "comment_status": current_status,
        "seen_comment_ids_per_review": seen_by_review,
    }
    save_state(repo, pr_num, new_state)
    if bot_login:
        save_bot_login(repo, bot_login, pr_num)

    return {
        "review_decision": decision,
        "terminal": decision in {"APPROVED", "CHANGES_REQUESTED"},
        "new_comments": new_comments,
        "actionable_comments": actionable_comments,
        "resolved_since_last_poll": resolved_since_last_poll,
        "bot_login": bot_login,
    }


def trigger_review(repo: Repo, pr_num: int, mode: str, label: str) -> dict[str, Any]:
    enabled, _ = repo_label_enabled(repo, label)
    if not enabled:
        raise DriverError("CodeRabbit marker label is absent from repository", exit_code=1)

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
    command_comment_id = int(response["id"])
    poll_interval = env_int("CODERABBIT_POLL_INTERVAL_SECONDS", DEFAULT_POLL_INTERVAL_SECONDS)
    bot_login = discover_bot_login(repo, pr_num)

    while True:
        issue_comments = gh_paginated_array(f"/repos/{repo.slug}/issues/{pr_num}/comments")
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
            if not is_trigger_ack_body(ack_body, mode):
                continue
            if login:
                bot_login = login
                save_bot_login(repo, bot_login, pr_num)
            return {
                "repo": repo.slug,
                "pr_num": pr_num,
                "mode": mode,
                "trigger_comment_id": command_comment_id,
                "trigger_body": body,
                "ack_comment_id": comment_id,
                "ack_marker": ACK_MARKERS[mode],
                "ack_body": ack_body,
                "bot_login": bot_login,
                "triggered_at": utc_now(),
            }
        time.sleep(poll_interval)


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


def latest_trigger_ack_time(
    issue_comments: list[dict[str, Any]], mode: str, bot_login: str | None
) -> datetime | None:
    latest: datetime | None = None
    for comment in issue_comments:
        login = (comment.get("user") or {}).get("login")
        if not is_bot_login(login, bot_login) and not is_coderabbit_login(login):
            continue
        body = comment.get("body") or ""
        if not is_trigger_ack_body(body, mode):
            continue
        observed_at = parse_time(comment.get("updated_at") or comment.get("created_at"))
        if observed_at and (latest is None or observed_at > latest):
            latest = observed_at
    return latest


def initial_trigger_decision(repo: Repo, pr_num: int, mode: str, policy: str) -> dict[str, Any]:
    if policy == "always":
        return {"trigger": True, "reason": "initial-trigger-policy:always"}
    if policy == "skip":
        return {"trigger": False, "reason": "initial-trigger-policy:skip"}

    reviews = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/reviews")
    issue_comments = gh_paginated_array(f"/repos/{repo.slug}/issues/{pr_num}/comments")
    bot_login = discover_bot_login(repo, pr_num, reviews=reviews, issue_comments=issue_comments)
    latest_review = latest_coderabbit_review(reviews, bot_login)
    latest_review_at = parse_time(latest_review.get("submitted_at")) if latest_review else None
    ack_time = latest_trigger_ack_time(issue_comments, mode, bot_login)

    if ack_time and (latest_review_at is None or ack_time > latest_review_at):
        return {
            "trigger": False,
            "reason": "initial-trigger-policy:auto:pending-ack-newer-than-latest-review",
            "latest_trigger_ack_at": ack_time.isoformat(),
            "latest_review_at": latest_review_at.isoformat() if latest_review_at else None,
        }
    return {
        "trigger": True,
        "reason": "initial-trigger-policy:auto:no-pending-trigger-detected",
        "latest_trigger_ack_at": ack_time.isoformat() if ack_time else None,
        "latest_review_at": latest_review_at.isoformat() if latest_review_at else None,
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


def ensure_worktree_branch(worktree_path: Path, branch: str) -> None:
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


def commit_dirty_agent_changes(worktree_path: Path, comment_id: int) -> str | None:
    dirty = git_dirty_paths(worktree_path)
    if not dirty:
        return None
    git_output(worktree_path, ["add", "-A"])
    git_output(worktree_path, ["commit", "-m", f"Address CodeRabbit comment {comment_id}"])
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
        raise DriverError(f"agent outcome for comment {comment_id} is not a JSON object")
    outcome = raw.get("outcome")
    if outcome not in VALID_OUTCOMES:
        raise DriverError(f"agent outcome for comment {comment_id} has invalid outcome {outcome!r}")
    try:
        raw_comment_id = int(raw.get("comment_id", -1))
    except (TypeError, ValueError) as err:
        raise DriverError(f"agent outcome for comment {comment_id} has invalid comment_id") from err
    if raw_comment_id != comment_id:
        raise DriverError(f"agent outcome comment_id mismatch for comment {comment_id}")
    if not isinstance(raw.get("rationale"), str) or not raw["rationale"].strip():
        raise DriverError(f"agent outcome for comment {comment_id} is missing rationale")
    if not isinstance(raw.get("files_touched"), list) or not all(
        isinstance(item, str) for item in raw["files_touched"]
    ):
        raise DriverError(f"agent outcome for comment {comment_id} has invalid files_touched")
    if not isinstance(raw.get("review_provided_value"), bool):
        raise DriverError(f"agent outcome for comment {comment_id} is missing review_provided_value")

    commit_sha = raw.get("commit_sha")
    if commit_sha is not None and not isinstance(commit_sha, str):
        raise DriverError(f"agent outcome for comment {comment_id} has invalid commit_sha")
    reply_body_file = raw.get("reply_body_file")
    if reply_body_file is not None and not isinstance(reply_body_file, str):
        raise DriverError(f"agent outcome for comment {comment_id} has invalid reply_body_file")
    if outcome in REPLY_OUTCOMES:
        if not reply_body_file:
            raise DriverError(f"agent outcome for comment {comment_id} must include reply_body_file")
        if not Path(reply_body_file).is_file():
            raise DriverError(f"reply body file for comment {comment_id} does not exist: {reply_body_file}")

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
    render_fix_prompt(template_path, prompt_path, comment, repo, pr_num, pr_branch, worktree_path)
    outcome_path = prompt_path.with_suffix(".outcome.json")
    log_path = prompt_path.with_suffix(".log")

    if fixer_agent and fixer_model:
        raise DriverError("pass either --fixer-agent or --fixer-model, not both")
    if fixer_agent:
        cmd = ["agents", "-a", fixer_agent, "-p", str(worktree_path), "-f", str(prompt_path)]
        dispatch_kind = "agent-file"
        dispatch_ref = fixer_agent
    elif fixer_model:
        cmd = ["agents", "-m", fixer_model, "-p", str(worktree_path), "-f", str(prompt_path)]
        dispatch_kind = "model"
        dispatch_ref = fixer_model
    else:
        raise DriverError("comment dispatch requires a fixer agent or fixer model")

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
            raise DriverError(f"agent did not write parseable outcome JSON for comment {comment_id}; log={log_path}")
        outcome_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outcome = validate_outcome(raw, comment_id)

    dirty_after = git_dirty_paths(worktree_path)
    if dirty_after and outcome["outcome"] not in FIX_OUTCOMES:
        raise DriverError(
            f"comment agent left uncommitted changes for non-fix outcome on comment {comment_id}: {dirty_after}"
        )
    if dirty_after and outcome["outcome"] in FIX_OUTCOMES:
        commit_sha = commit_dirty_agent_changes(worktree_path, comment_id)
        outcome["commit_sha"] = commit_sha
        outcome_path.write_text(json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif outcome["outcome"] in FIX_OUTCOMES and not outcome["commit_sha"]:
        outcome["commit_sha"] = git_head(worktree_path)
        outcome_path.write_text(json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8")

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


def post_reply(repo: Repo, pr_num: int, comment_id: int, body_file: str) -> dict[str, Any]:
    # command_reply prints its own JSON, so keep review-loop replies quiet by using the same underlying path.
    body_path = Path(body_file)
    body = body_path.read_text(encoding="utf-8")
    if not body.strip():
        raise DriverError("reply body file is empty")

    bot_login = discover_bot_login(repo, pr_num)
    review_comments = gh_paginated_array(f"/repos/{repo.slug}/pulls/{pr_num}/comments")
    target = next((comment for comment in review_comments if int(comment.get("id")) == comment_id), None)
    if target and not is_bot_login((target.get("user") or {}).get("login"), bot_login):
        raise DriverError(f"comment {comment_id} is not authored by CodeRabbit")

    normalized_body = body.strip()
    if target:
        for comment in review_comments:
            if comment.get("in_reply_to_id") == comment_id and (comment.get("body") or "").strip() == normalized_body:
                return {
                    "repo": repo.slug,
                    "pr_num": pr_num,
                    "comment_id": comment_id,
                    "posted": False,
                    "reason": "reply-already-present",
                    "reply_kind": "review-comment-reply",
                    "reply_id": comment.get("id"),
                    "reply_url": comment.get("html_url"),
                }

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
        return {
            "repo": repo.slug,
            "pr_num": pr_num,
            "comment_id": comment_id,
            "posted": True,
            "reply_kind": "review-comment-reply",
            "reply_id": response.get("id"),
            "reply_url": response.get("html_url"),
        }

    issue_comments = gh_paginated_array(f"/repos/{repo.slug}/issues/{pr_num}/comments")
    issue_target = next((comment for comment in issue_comments if int(comment.get("id")) == comment_id), None)
    if not issue_target:
        raise DriverError(f"comment {comment_id} was not found on PR {pr_num}")
    if not is_bot_login((issue_target.get("user") or {}).get("login"), bot_login):
        raise DriverError(f"comment {comment_id} is not authored by CodeRabbit")

    target_url = issue_target.get("html_url")
    mention_login = bot_login or (issue_target.get("user") or {}).get("login") or "coderabbitai"
    issue_body = f"@{mention_login} re: {target_url}\n\n{body}" if target_url else f"@{mention_login}\n\n{body}"
    for comment in issue_comments:
        if (comment.get("body") or "").strip() == issue_body.strip():
            return {
                "repo": repo.slug,
                "pr_num": pr_num,
                "comment_id": comment_id,
                "posted": False,
                "reason": "reply-already-present",
                "reply_kind": "issue-comment",
                "reply_id": comment.get("id"),
                "reply_url": comment.get("html_url"),
            }

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
    return {
        "repo": repo.slug,
        "pr_num": pr_num,
        "comment_id": comment_id,
        "posted": True,
        "reply_kind": "issue-comment",
        "reply_id": response.get("id"),
        "reply_url": response.get("html_url"),
    }


def wait_for_loop_poll_cadence(repo: Repo, pr_num: int, min_interval_seconds: int) -> dict[str, Any]:
    state = load_state(repo, pr_num)
    last_raw = state.get("last_loop_poll_at") or state.get("last_polled_at")
    last_at = parse_time(last_raw) if isinstance(last_raw, str) else None
    if not last_at:
        return {"waited_seconds": 0, "last_poll_at": None, "min_interval_seconds": min_interval_seconds}
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


def select_actionable_comments(poll_result: dict[str, Any]) -> list[dict[str, Any]]:
    new_comments = [
        comment
        for comment in poll_result.get("new_comments", [])
        if comment.get("kind") == "in-diff" and not comment.get("resolved")
    ]
    if new_comments:
        return new_comments
    return [
        comment
        for comment in poll_result.get("actionable_comments", [])
        if comment.get("kind") == "in-diff" and not comment.get("resolved")
    ]


def review_loop(args: argparse.Namespace) -> dict[str, Any]:
    repo = Repo.parse(args.repo)
    enabled, enabled_payload = repo_label_enabled(repo, args.label)
    if not enabled:
        raise DriverError("CodeRabbit marker label is absent from repository", exit_code=1)

    metadata = pr_metadata(repo, args.pr_num)
    pr_branch = metadata.get("headRefName")
    if not isinstance(pr_branch, str) or not pr_branch:
        raise DriverError(f"could not resolve PR head branch for {repo.slug}#{args.pr_num}")
    worktree_path = Path(args.worktree_path).expanduser().resolve()
    ensure_worktree_branch(worktree_path, pr_branch)

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
        "CODERABBIT_REVIEW_LOOP_POLL_INTERVAL_SECONDS", DEFAULT_REVIEW_LOOP_POLL_INTERVAL_SECONDS
    )
    if min_poll_interval < DEFAULT_REVIEW_LOOP_POLL_INTERVAL_SECONDS:
        raise DriverError(
            f"poll interval must be at least {DEFAULT_REVIEW_LOOP_POLL_INTERVAL_SECONDS}s, got {min_poll_interval}"
        )

    loop_started_at = utc_now()
    trigger_decision = initial_trigger_decision(repo, args.pr_num, args.mode, args.initial_trigger)
    initial_trigger: dict[str, Any] | None = None
    if trigger_decision["trigger"]:
        print(f"Triggering CodeRabbit {args.mode} review for {repo.slug}#{args.pr_num}", file=sys.stderr, flush=True)
        initial_trigger = trigger_review(repo, args.pr_num, args.mode, args.label)
    else:
        print(f"Skipping initial trigger: {trigger_decision['reason']}", file=sys.stderr, flush=True)

    iterations: list[dict[str, Any]] = []
    iteration_index = 1
    terminal_reason: str | None = None
    final_review_decision = "NONE"
    rate_limit_observations: list[str] = []

    while True:
        iteration_dir = cache_dir(repo, args.pr_num) / f"iter-{iteration_index}"
        iteration_dir.mkdir(parents=True, exist_ok=True)
        cadence = wait_for_loop_poll_cadence(repo, args.pr_num, min_poll_interval)
        poll_started_at = utc_now()
        poll_result = poll(repo, args.pr_num)
        mark_loop_poll(repo, args.pr_num)
        final_review_decision = str(poll_result.get("review_decision") or "NONE")
        actionable_comments = select_actionable_comments(poll_result)
        iteration: dict[str, Any] = {
            "iteration": iteration_index,
            "poll_started_at": poll_started_at,
            "poll_completed_at": utc_now(),
            "cadence": cadence,
            "review_decision": final_review_decision,
            "terminal": poll_result.get("terminal"),
            "new_comments": poll_result.get("new_comments", []),
            "actionable_comments": actionable_comments,
            "resolved_since_last_poll": poll_result.get("resolved_since_last_poll", []),
            "bot_login": poll_result.get("bot_login"),
            "outcomes": [],
            "reply_results": [],
            "push_result": None,
            "trigger_result": None,
        }

        if final_review_decision == "APPROVED":
            terminal_reason = "approved"
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
            raise DriverError(f"worktree is dirty before comment dispatch: {worktree_path}")

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

        if iteration["outcomes"] and all(
            outcome["review_provided_value"] is False for outcome in iteration["outcomes"]
        ):
            terminal_reason = "no_value_provided"
            iterations.append(iteration)
            break

        caller_decision = [
            outcome
            for outcome in iteration["outcomes"]
            if outcome["review_provided_value"] and outcome["outcome"] in CALLER_DECISION_OUTCOMES
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
                "initial_trigger_decision": trigger_decision,
                "initial_trigger_result": initial_trigger,
                "iterations": iterations,
                "rate_limit_observations": rate_limit_observations,
            }

        if any(outcome["outcome"] in FIX_OUTCOMES for outcome in iteration["outcomes"]):
            iteration["push_result"] = push_branch(worktree_path, pr_branch)

        for outcome in iteration["outcomes"]:
            if outcome["outcome"] in REPLY_OUTCOMES:
                reply_result = post_reply(repo, args.pr_num, outcome["comment_id"], outcome["reply_body_file"])
                iteration["reply_results"].append(reply_result)

        iteration["trigger_result"] = trigger_review(repo, args.pr_num, "incremental", args.label)
        iterations.append(iteration)
        iteration_index += 1

    return {
        "repo": repo.slug,
        "pr_num": args.pr_num,
        "pr": metadata,
        "enabled": enabled_payload,
        "loop_started_at": loop_started_at,
        "loop_completed_at": utc_now(),
        "terminal": True,
        "terminal_reason": terminal_reason,
        "needs_caller_decision": False,
        "review_decision": final_review_decision,
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


def command_review_loop(args: argparse.Namespace) -> int:
    payload = review_loop(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload.get("needs_caller_decision"):
        return 3
    return 0


def command_reply(args: argparse.Namespace) -> int:
    repo = Repo.parse(args.repo)
    body_path = Path(args.body_file)
    body = body_path.read_text(encoding="utf-8")
    if not body.strip():
        raise DriverError("reply body file is empty")

    bot_login = discover_bot_login(repo, args.pr_num)
    review_comments = gh_paginated_array(f"/repos/{repo.slug}/pulls/{args.pr_num}/comments")
    target = next((comment for comment in review_comments if int(comment.get("id")) == args.comment_id), None)
    if target and not is_bot_login((target.get("user") or {}).get("login"), bot_login):
        raise DriverError(f"comment {args.comment_id} is not authored by CodeRabbit")

    normalized_body = body.strip()
    if target:
        for comment in review_comments:
            if comment.get("in_reply_to_id") == args.comment_id and (comment.get("body") or "").strip() == normalized_body:
                print(
                    json.dumps(
                        {
                            "repo": repo.slug,
                            "pr_num": args.pr_num,
                            "comment_id": args.comment_id,
                            "posted": False,
                            "reason": "reply-already-present",
                            "reply_kind": "review-comment-reply",
                            "reply_id": comment.get("id"),
                            "reply_url": comment.get("html_url"),
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 0

        response = gh_json(
            [
                "api",
                "-X",
                "POST",
                f"/repos/{repo.slug}/pulls/{args.pr_num}/comments/{args.comment_id}/replies",
                "-f",
                f"body={body}",
            ]
        )
        print(
            json.dumps(
                {
                    "repo": repo.slug,
                    "pr_num": args.pr_num,
                    "comment_id": args.comment_id,
                    "posted": True,
                    "reply_kind": "review-comment-reply",
                    "reply_id": response.get("id"),
                    "reply_url": response.get("html_url"),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    issue_comments = gh_paginated_array(f"/repos/{repo.slug}/issues/{args.pr_num}/comments")
    issue_target = next((comment for comment in issue_comments if int(comment.get("id")) == args.comment_id), None)
    if not issue_target:
        raise DriverError(f"comment {args.comment_id} was not found on PR {args.pr_num}")
    if not is_bot_login((issue_target.get("user") or {}).get("login"), bot_login):
        raise DriverError(f"comment {args.comment_id} is not authored by CodeRabbit")

    target_url = issue_target.get("html_url")
    mention_login = bot_login or (issue_target.get("user") or {}).get("login") or "coderabbitai"
    issue_body = f"@{mention_login} re: {target_url}\n\n{body}" if target_url else f"@{mention_login}\n\n{body}"
    for comment in issue_comments:
        if (comment.get("body") or "").strip() == issue_body.strip():
            print(
                json.dumps(
                    {
                        "repo": repo.slug,
                        "pr_num": args.pr_num,
                        "comment_id": args.comment_id,
                        "posted": False,
                        "reason": "reply-already-present",
                        "reply_kind": "issue-comment",
                        "reply_id": comment.get("id"),
                        "reply_url": comment.get("html_url"),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

    response = gh_json(
        [
            "api",
            "-X",
            "POST",
            f"/repos/{repo.slug}/issues/{args.pr_num}/comments",
            "-f",
            f"body={issue_body}",
        ]
    )
    print(
        json.dumps(
            {
                "repo": repo.slug,
                "pr_num": args.pr_num,
                "comment_id": args.comment_id,
                "posted": True,
                "reply_kind": "issue-comment",
                "reply_id": response.get("id"),
                "reply_url": response.get("html_url"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default=os.environ.get("CODERABBIT_MARKER_LABEL", DEFAULT_LABEL))
    subparsers = parser.add_subparsers(dest="command", required=True)

    enabled = subparsers.add_parser("is-enabled", help="Exit 0 when the repo has the CodeRabbit marker label.")
    enabled.add_argument("repo")
    enabled.set_defaults(func=command_is_enabled)

    trigger = subparsers.add_parser("trigger", help="Post a CodeRabbit review command and wait for ack.")
    trigger.add_argument("repo")
    trigger.add_argument("pr_num", type=int)
    trigger.add_argument("--mode", choices=("incremental", "full"), default="incremental")
    trigger.set_defaults(func=command_trigger)

    poll_parser = subparsers.add_parser("poll", help="Poll CodeRabbit review state and persist comment files.")
    poll_parser.add_argument("repo")
    poll_parser.add_argument("pr_num", type=int)
    poll_parser.set_defaults(func=command_poll)

    review_loop_parser = subparsers.add_parser(
        "review-loop",
        help="Run the unbounded CodeRabbit PR review loop with centralized 5-minute poll cadence.",
    )
    review_loop_parser.add_argument("repo")
    review_loop_parser.add_argument("pr_num", type=int)
    review_loop_parser.add_argument("--mode", choices=("incremental", "full"), default="incremental")
    review_loop_parser.add_argument(
        "--initial-trigger",
        choices=("auto", "always", "skip"),
        default="auto",
        help="Initial trigger policy. auto skips when a trigger ack is newer than the latest CodeRabbit review.",
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

    reply = subparsers.add_parser("reply", help="Reply to a CodeRabbit review or issue comment.")
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
