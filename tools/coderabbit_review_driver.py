#!/usr/bin/env python3
"""Drive GitHub PR-mode CodeRabbit review through @mentions and review state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


DEFAULT_LABEL = "coderabbit"
CACHE_ROOT = Path.home() / ".cache" / "coderabbit"
DEFAULT_ENABLED_TTL_SECONDS = 3600
DEFAULT_POLL_INTERVAL_SECONDS = 15
TRIGGER_BODIES = {
    "incremental": "@coderabbitai review",
    "full": "@coderabbitai full review",
}
ACK_MARKERS = {
    "incremental": "Review triggered.",
    "full": "Full review triggered.",
}


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
        "resolved_since_last_poll": resolved_since_last_poll,
        "bot_login": bot_login,
    }


def command_is_enabled(args: argparse.Namespace) -> int:
    repo = Repo.parse(args.repo)
    enabled, payload = repo_label_enabled(repo, args.label)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if enabled else 1


def command_trigger(args: argparse.Namespace) -> int:
    repo = Repo.parse(args.repo)
    enabled, _ = repo_label_enabled(repo, args.label)
    if not enabled:
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
    mode = args.mode
    body = TRIGGER_BODIES[mode]
    response = gh_json(
        [
            "api",
            "-X",
            "POST",
            f"/repos/{repo.slug}/issues/{args.pr_num}/comments",
            "-f",
            f"body={body}",
        ]
    )
    command_comment_id = int(response["id"])
    poll_interval = env_int("CODERABBIT_POLL_INTERVAL_SECONDS", DEFAULT_POLL_INTERVAL_SECONDS)
    bot_login = discover_bot_login(repo, args.pr_num)

    while True:
        issue_comments = gh_paginated_array(f"/repos/{repo.slug}/issues/{args.pr_num}/comments")
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
                save_bot_login(repo, bot_login, args.pr_num)
            print(
                json.dumps(
                    {
                        "repo": repo.slug,
                        "pr_num": args.pr_num,
                        "mode": mode,
                        "trigger_comment_id": command_comment_id,
                        "trigger_body": body,
                        "ack_comment_id": comment_id,
                        "ack_marker": ACK_MARKERS[mode],
                        "ack_body": ack_body,
                        "bot_login": bot_login,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        time.sleep(poll_interval)


def command_poll(args: argparse.Namespace) -> int:
    repo = Repo.parse(args.repo)
    print(json.dumps(poll(repo, args.pr_num), indent=2, sort_keys=True))
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
