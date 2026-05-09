from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LINEAR_OPERATOR = REPO_ROOT / "agents" / "linear-operator.md"
JIRA_OPERATOR = REPO_ROOT / "agents" / "jira-operator.md"
LINEAR_CLI = REPO_ROOT / "clients" / "linear" / "cli.py"
LINEAR_CLIENT = REPO_ROOT / "clients" / "linear" / "client.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_contains_all(text: str, tokens: tuple[str, ...], *, where: str) -> None:
    missing = [token for token in tokens if token not in text]
    assert missing == [], f"{where} missing required token(s): {missing}"


def _slice_from(text: str, start_token: str, *, chars: int, where: str) -> str:
    start = text.find(start_token)
    assert start != -1, f"{where} missing anchor token: {start_token}"
    return text[start : start + chars]


def test_T_comment_ref_comment_paths_return_usable_reference() -> None:
    linear_operator = _read(LINEAR_OPERATOR)
    jira_operator = _read(JIRA_OPERATOR)
    linear_cli = _read(LINEAR_CLI)
    linear_client = _read(LINEAR_CLIENT)

    linear_create = _slice_from(
        linear_operator,
        "Returns `{\"ok\": true, \"data\": {\"id\": \"<uuid>\"",
        chars=180,
        where="T-comment-ref Linear create-comment operator return",
    )
    _assert_contains_all(
        linear_create,
        ("Parse `id` to confirm",),
        where="T-comment-ref Linear create-comment usable id",
    )
    _assert_contains_all(
        linear_operator,
        (
            "task=upsert-comment",
            "For `upsert-comment`: print the comment ID",
        ),
        where="T-comment-ref Linear upsert-comment operator return contract",
    )

    linear_cli_create = _slice_from(
        linear_cli,
        "def create_comment",
        chars=260,
        where="T-comment-ref Linear CLI create_comment",
    )
    linear_cli_upsert = _slice_from(
        linear_cli,
        "def upsert_comment",
        chars=900,
        where="T-comment-ref Linear CLI upsert_comment",
    )
    _assert_contains_all(
        linear_cli_create,
        ("print(json.dumps({\"ok\": True, \"data\": comment}",),
        where="T-comment-ref Linear CLI create_comment JSON data",
    )
    _assert_contains_all(
        linear_cli_upsert,
        ("client.upsert_comment", "print(json.dumps({\"ok\": True, \"data\": comment}"),
        where="T-comment-ref Linear CLI upsert_comment JSON data",
    )

    linear_graphql = _slice_from(
        linear_client,
        "commentCreate(input: $input)",
        chars=1200,
        where="T-comment-ref Linear client commentCreate",
    )
    linear_client_upsert = _slice_from(
        linear_client,
        "def upsert_comment",
        chars=1900,
        where="T-comment-ref Linear client upsert_comment",
    )
    _assert_contains_all(
        linear_graphql,
        ("comment {", "id", "\"id\": comment.get(\"id\")"),
        where="T-comment-ref Linear client create returns id",
    )
    _assert_contains_all(
        linear_client_upsert,
        ("\"id\": updated[\"id\"]", "\"id\": created[\"id\"]"),
        where="T-comment-ref Linear client upsert returns id",
    )

    jira_comment = _slice_from(
        jira_operator,
        "A successful POST returns `{\"id\":",
        chars=180,
        where="T-comment-ref Jira comment POST return",
    )
    _assert_contains_all(
        jira_comment,
        ("Parse `id` to confirm",),
        where="T-comment-ref Jira create-comment usable id",
    )
