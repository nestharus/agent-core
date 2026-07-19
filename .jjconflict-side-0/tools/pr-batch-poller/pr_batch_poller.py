from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


DEFAULT_CHUNK_SIZE = 50
GH_GRAPHQL_TIMEOUT_SECONDS = 60
SCHEMA_VERSION = 1

ERR_REPO_NOT_FOUND = "repo_not_found_or_forbidden"
ERR_PR_NOT_FOUND = "pr_not_found_or_forbidden"
ERR_GRAPHQL_PARTIAL = "graphql_partial_error"
ERR_COMMENT_WINDOW = "comment_window_exceeded"

PR_TOKEN_RE = re.compile(
    r"^(?P<owner>[A-Za-z0-9][A-Za-z0-9-]*)/"
    r"(?P<repo>[A-Za-z0-9._-]+)#"
    r"(?P<number>[1-9][0-9]*)$"
)

STATUS_FIELDS = (
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
)


class CliError(ValueError):
    pass


class PollerArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliError(message)


@dataclass(frozen=True)
class PrIdentifier:
    owner: str
    repo: str
    number: int

    @property
    def canonical(self) -> str:
        return f"{self.owner}/{self.repo}#{self.number}"


@dataclass(frozen=True)
class QueryChunk:
    prs: tuple[PrIdentifier, ...]


@dataclass(frozen=True)
class GraphQLRequest:
    query: str
    alias_map: dict[tuple[str, str], PrIdentifier]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = PollerArgumentParser(prog="pr-batch-poller", add_help=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--prs", help="Comma-separated owner/repo#number identifiers.")
    source.add_argument("--prs-file", type=Path, help="File containing one owner/repo#number per line.")
    parser.add_argument("--since", help="Offset-aware ISO-8601 timestamp; Z is accepted.")
    parser.add_argument("--format", choices=("jsonl", "json", "table"), default="jsonl")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
        prs = parse_prs_file(args.prs_file) if args.prs_file is not None else parse_prs_arg(args.prs)
        prs = dedupe_prs(prs)
        if not prs:
            raise CliError("at least one PR identifier is required")
        since = parse_since(args.since)
    except CliError as exc:
        print(f"pr-batch-poller: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"pr-batch-poller: {exc}", file=sys.stderr)
        return 2

    try:
        rows: list[dict[str, Any]] = []
        for chunk in plan_chunks(prs):
            request = build_graphql_request(chunk)
            response = run_gh_graphql(request.query)
            rows.extend(map_graphql_response(request, response, since))
        rows = filter_rows_since(rows, since)
        if args.format == "jsonl":
            output = render_jsonl(rows)
        elif args.format == "json":
            output = render_json(rows)
        else:
            output = render_table(rows)
        if output:
            sys.stdout.write(output)
    except Exception as exc:
        print(f"pr-batch-poller: {exc}", file=sys.stderr)
        return 1
    return 0


def parse_pr_token(token: str) -> PrIdentifier:
    match = PR_TOKEN_RE.match(token)
    if not match:
        raise CliError(f"invalid PR identifier: {token!r}")
    number = int(match.group("number"))
    return PrIdentifier(owner=match.group("owner"), repo=match.group("repo"), number=number)


def parse_prs_arg(value: str) -> list[PrIdentifier]:
    prs: list[PrIdentifier] = []
    for raw_token in value.split(","):
        token = raw_token.strip()
        if not token:
            raise CliError("empty PR identifier in --prs")
        prs.append(parse_pr_token(token))
    return prs


def parse_prs_file(path: Path) -> list[PrIdentifier]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CliError(f"could not read --prs-file: {path}") from exc

    prs: list[PrIdentifier] = []
    for line_number, raw_line in enumerate(lines, start=1):
        token = raw_line.strip()
        if not token:
            continue
        try:
            prs.append(parse_pr_token(token))
        except CliError as exc:
            raise CliError(f"{path}:{line_number}: {exc}") from exc
    return prs


def dedupe_prs(prs: Iterable[PrIdentifier]) -> list[PrIdentifier]:
    seen: set[str] = set()
    unique: list[PrIdentifier] = []
    for pr in prs:
        if pr.canonical in seen:
            continue
        seen.add(pr.canonical)
        unique.append(pr)
    return unique


def parse_since(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = _parse_iso_datetime(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CliError("--since must be offset-aware")
    return parsed.astimezone(timezone.utc)


def is_changed_since(row: dict, since: datetime | None) -> bool:
    if since is None:
        return True
    if row.get("row_type") == "error":
        return True
    last_event_at = row.get("last_event_at")
    if last_event_at is None:
        return False
    return _parse_iso_datetime(last_event_at).astimezone(timezone.utc) > since


def filter_rows_since(rows: Iterable[dict], since: datetime | None) -> list[dict]:
    return [row for row in rows if is_changed_since(row, since)]


def plan_chunks(prs: Sequence[PrIdentifier], chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[QueryChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    return [
        QueryChunk(tuple(prs[index : index + chunk_size]))
        for index in range(0, len(prs), chunk_size)
    ]


def build_graphql_request(chunk: QueryChunk) -> GraphQLRequest:
    repo_alias_by_key: dict[tuple[str, str], str] = {}
    repo_order: list[tuple[str, str]] = []
    prs_by_repo: dict[tuple[str, str], list[tuple[str, PrIdentifier]]] = {}
    alias_map: dict[tuple[str, str], PrIdentifier] = {}

    for pr_index, pr in enumerate(chunk.prs):
        repo_key = (pr.owner, pr.repo)
        if repo_key not in repo_alias_by_key:
            repo_alias_by_key[repo_key] = f"repo_{len(repo_alias_by_key)}"
            repo_order.append(repo_key)
        repo_alias = repo_alias_by_key[repo_key]
        pr_alias = f"pr_{pr_index}"
        prs_by_repo.setdefault(repo_key, []).append((pr_alias, pr))
        alias_map[(repo_alias, pr_alias)] = pr

    blocks: list[str] = ["query PrBatchPoller {"]
    for repo_key in repo_order:
        owner, repo = repo_key
        repo_alias = repo_alias_by_key[repo_key]
        blocks.append(
            f'  {repo_alias}: repository(owner: "{_graphql_string(owner)}", name: "{_graphql_string(repo)}") {{'
        )
        for pr_alias, pr in prs_by_repo[repo_key]:
            blocks.extend(
                [
                    f"    {pr_alias}: pullRequest(number: {pr.number}) {{",
                    "      number",
                    "      url",
                    "      state",
                    "      merged",
                    "      mergedAt",
                    "      mergeCommit { oid }",
                    "      headRefName",
                    "      headRefOid",
                    "      baseRefName",
                    "      baseRefOid",
                    "      updatedAt",
                    "      comments(first: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {",
                    "        nodes { updatedAt }",
                    "        pageInfo { hasNextPage }",
                    "      }",
                    "    }",
                ]
            )
        blocks.append("  }")
    blocks.append("}")
    return GraphQLRequest(query="\n".join(blocks), alias_map=alias_map)


def run_gh_graphql(query: str) -> Mapping[str, Any]:
    try:
        completed = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=GH_GRAPHQL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("gh api graphql timed out") from exc
    except FileNotFoundError as exc:
        raise RuntimeError("gh executable not found") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        message = "gh api graphql exited non-zero"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message)

    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("gh api graphql returned malformed JSON") from exc
    if not isinstance(parsed, Mapping):
        raise RuntimeError("gh api graphql returned malformed JSON")
    return parsed


def map_graphql_response(
    request: GraphQLRequest, response: Mapping[str, Any], since: datetime | None
) -> list[dict]:
    partial_errors = _mapped_graphql_errors(request, response.get("errors", []))
    data = response.get("data")
    if not isinstance(data, Mapping):
        raise RuntimeError("GraphQL response missing data object")

    rows: list[dict[str, Any]] = []
    for repo_alias, pr_alias in request.alias_map:
        pr = request.alias_map[(repo_alias, pr_alias)]
        partial_message = partial_errors.get((repo_alias, pr_alias))
        if partial_message is not None:
            rows.append(make_error_row(pr, ERR_GRAPHQL_PARTIAL, partial_message))
            continue

        repo_data = data.get(repo_alias)
        if repo_data is None:
            rows.append(
                make_error_row(
                    pr,
                    ERR_REPO_NOT_FOUND,
                    f"repository {pr.owner}/{pr.repo} was not found or is forbidden",
                )
            )
            continue
        if not isinstance(repo_data, Mapping):
            raise RuntimeError(f"GraphQL repository alias {repo_alias} was not an object")

        node = repo_data.get(pr_alias)
        if node is None:
            rows.append(
                make_error_row(
                    pr,
                    ERR_PR_NOT_FOUND,
                    f"pull request {pr.canonical} was not found or is forbidden",
                )
            )
            continue
        if not isinstance(node, Mapping):
            raise RuntimeError(f"GraphQL PR alias {pr_alias} was not an object")

        if _comment_window_exceeded(node, since):
            rows.append(
                make_error_row(
                    pr,
                    ERR_COMMENT_WINDOW,
                    f"conversation comment count for {pr.canonical} exceeded the fetched window",
                    trusted=node,
                )
            )
        else:
            rows.append(make_success_row(pr, node, since))
    return rows


def make_success_row(pr: PrIdentifier, node: Mapping[str, Any], since: datetime | None) -> dict:
    row = _identity_row(pr, "pr_status")
    row.update(_status_values(node, since, include_new_comments=True))
    row["error"] = None
    return row


def make_error_row(
    pr: PrIdentifier,
    code: str,
    message: str,
    trusted: Mapping[str, Any] | None = None,
) -> dict:
    row = _identity_row(pr, "error")
    if trusted is None:
        row.update({field: None for field in STATUS_FIELDS})
    else:
        row.update(_status_values(trusted, since=None, include_new_comments=False))
    row["error"] = {"code": code, "message": message}
    return row


def render_jsonl(rows: Sequence[dict]) -> str:
    if not rows:
        return ""
    return "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows)


def render_json(rows: Sequence[dict]) -> str:
    return json.dumps(list(rows), separators=(",", ":"))


def render_table(rows: Sequence[dict]) -> str:
    lines = ["pr\trow_type\tstate\tmerged\tlast_event_at\terror"]
    for row in rows:
        error = row["error"]["code"] if row.get("error") else ""
        lines.append(
            "\t".join(
                str(value) if value is not None else ""
                for value in (
                    row.get("pr"),
                    row.get("row_type"),
                    row.get("state"),
                    row.get("merged"),
                    row.get("last_event_at"),
                    error,
                )
            )
        )
    return "\n".join(lines) + "\n"


def _identity_row(pr: PrIdentifier, row_type: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": row_type,
        "pr": pr.canonical,
        "owner": pr.owner,
        "repo": pr.repo,
        "number": pr.number,
    }


def _status_values(
    node: Mapping[str, Any],
    since: datetime | None,
    *,
    include_new_comments: bool,
) -> dict[str, Any]:
    comments = node.get("comments") if isinstance(node.get("comments"), Mapping) else {}
    comment_nodes = comments.get("nodes", []) if isinstance(comments, Mapping) else []
    if not isinstance(comment_nodes, Sequence):
        comment_nodes = []
    comment_timestamps = [
        comment.get("updatedAt")
        for comment in comment_nodes
        if isinstance(comment, Mapping) and comment.get("updatedAt") is not None
    ]
    merge_commit = node.get("mergeCommit")
    return {
        "pr_url": node.get("url"),
        "state": node.get("state"),
        "merged": node.get("merged"),
        "merged_at": node.get("mergedAt"),
        "merge_sha": merge_commit.get("oid") if isinstance(merge_commit, Mapping) else None,
        "head_sha": node.get("headRefOid"),
        "head_ref_name": node.get("headRefName"),
        "base_ref_name": node.get("baseRefName"),
        "base_ref_oid": node.get("baseRefOid"),
        "updated_at": node.get("updatedAt"),
        "last_event_at": node.get("updatedAt"),
        "last_comment_at": _latest_timestamp(comment_timestamps),
        "new_comments_since": (
            _count_comments_since(comment_timestamps, since)
            if include_new_comments and since is not None
            else None
        ),
    }


def _latest_timestamp(values: Sequence[str]) -> str | None:
    if not values:
        return None
    return max(values, key=lambda value: _parse_iso_datetime(value).astimezone(timezone.utc))


def _count_comments_since(values: Sequence[str], since: datetime) -> int:
    return sum(1 for value in values if _parse_iso_datetime(value).astimezone(timezone.utc) > since)


def _comment_window_exceeded(node: Mapping[str, Any], since: datetime | None) -> bool:
    if since is None:
        return False
    comments = node.get("comments")
    if not isinstance(comments, Mapping):
        return False
    page_info = comments.get("pageInfo")
    nodes = comments.get("nodes", [])
    if not isinstance(page_info, Mapping) or not isinstance(nodes, Sequence):
        return False
    if page_info.get("hasNextPage") is not True or len(nodes) < 100:
        return False
    timestamps = [
        comment.get("updatedAt")
        for comment in nodes
        if isinstance(comment, Mapping) and comment.get("updatedAt") is not None
    ]
    return len(timestamps) == len(nodes) and all(
        _parse_iso_datetime(value).astimezone(timezone.utc) > since for value in timestamps
    )


def _mapped_graphql_errors(
    request: GraphQLRequest,
    errors: Any,
) -> dict[tuple[str, str], str]:
    if not errors:
        return {}
    if not isinstance(errors, Sequence):
        raise RuntimeError("GraphQL response errors was not a list")

    mapped: dict[tuple[str, str], str] = {}
    for error in errors:
        if not isinstance(error, Mapping):
            raise RuntimeError("GraphQL response contained an unmapped error")
        path = error.get("path")
        key = _alias_key_from_path(request, path)
        if key is None:
            raise RuntimeError(str(error.get("message") or "unmapped GraphQL error"))
        mapped[key] = str(error.get("message") or "GraphQL partial error")
    return mapped


def _alias_key_from_path(
    request: GraphQLRequest,
    path: Any,
) -> tuple[str, str] | None:
    if not isinstance(path, Sequence) or isinstance(path, (str, bytes)):
        return None
    path_parts = [str(part) for part in path]
    for key in request.alias_map:
        repo_alias, pr_alias = key
        for index in range(0, len(path_parts) - 1):
            if path_parts[index] == repo_alias and path_parts[index + 1] == pr_alias:
                return key
    return None


def _parse_iso_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise CliError(f"invalid ISO-8601 timestamp: {value!r}") from exc


def _graphql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
