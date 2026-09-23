"""Bounded, enqueue-only Codex transport for shared board notices.

The board owner first commits a per-recipient outbox row, then can call::

    notice = render_new_thread(row["thread_id"], row["title"], row["notification_id"],
                               board_id=board_id, board_home=board_home)
    result = queue_notice(row["recipient"], recipient_profile, notice)

Use ``render_reply`` for a reply row. Persist the structured status and queue
message ID on that outbox row; handle timeout/ambiguous states without blind
retry. ``queued`` means the local CLI accepted the enqueue request. A separate
recipient action must acknowledge the notification.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
import pwd
import re
import shlex
import selectors
import signal
import subprocess
import time
from typing import Callable, Literal, Mapping, Sequence
import unicodedata
import uuid


PROFILE_NAMES = frozenset({".codex", ".codex2", ".codex3", ".codex4", ".codex5"})
CODEX_COMMAND = "codex"
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_TIMEOUT_SECONDS = 60.0
MAX_CAPTURE_BYTES = 4096
MAX_NOTICE_CHARS = 700
MAX_TITLE_CHARS = 160
BOARD_SCRIPT = Path(__file__).with_name("board.py")

_UUID_TEXT = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z")
_QUEUED_LINE = re.compile(r"(?im)^\s*Queued message\b[^\r\n]*$")
_REJECTED_LINE = re.compile(r"(?im)^\s*unable to enqueue message\b[^\r\n]*$")
_UUID_IN_LINE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}(?![0-9a-fA-F])")


@dataclass(frozen=True)
class CommandOutcome:
    """The bounded subprocess observation, without any delivery claim."""

    returncode: int | None
    output: str
    timed_out: bool = False
    output_truncated: bool = False


@dataclass(frozen=True)
class EnqueueResult:
    """Transport result; ``queue_message_id`` is never a recipient receipt."""

    status: Literal["queued", "failed", "timeout", "ambiguous"]
    queue_message_id: str | None
    returncode: int | None
    output: str
    output_truncated: bool = False
    reason: str | None = None


Runner = Callable[[Sequence[str], Mapping[str, str], float, int], CommandOutcome]


class LaunchError(Exception):
    """The queue subprocess could not start; no request was sent."""


class ProfileError(ValueError):
    """The selected recipient home cannot be used before launching queue."""


def _uuid(value: str, label: str) -> str:
    if not isinstance(value, str) or _UUID_TEXT.fullmatch(value) is None:
        raise ValueError(f"{label} must be a canonical UUID")
    return str(uuid.UUID(value))


def profile_root() -> Path:
    """Use the current Unix account, independent of a caller-supplied HOME."""
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def _profile_home(profile: str) -> Path:
    if not isinstance(profile, str) or profile not in PROFILE_NAMES:
        raise ProfileError("profile must be an allowed local Codex profile name")
    path = profile_root() / profile
    if not path.is_dir() or path.is_symlink():
        raise ProfileError("allowed local Codex profile directory does not exist")
    return path


def _safe_text(value: str, label: str, maximum: int, *, multiline: bool = False) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must contain 1 to {maximum} characters")
    if any((unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Zl", "Zp"})
           and (not multiline or ch != "\n") for ch in value):
        raise ValueError(f"{label} contains a control character")
    return value


def _positive_id(value: int, label: str) -> int:
    if type(value) is not int or value <= 0 or value > 9_223_372_036_854_775_807:
        raise ValueError(f"{label} must be a positive 64-bit integer")
    return value


def run_bounded(argv: Sequence[str], env: Mapping[str, str],
                timeout_seconds: float, max_output_bytes: int) -> CommandOutcome:
    """Drain one combined pipe while retaining at most ``max_output_bytes``.

    The caller supplies an argv list. No shell is involved. On timeout the
    direct process is killed and reaped. A timeout remains an unknown enqueue
    outcome even if partial output resembles a success message.
    """

    if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise ValueError("timeout_seconds must be between 0 and 60 seconds")
    if type(max_output_bytes) is not int or max_output_bytes <= 0:
        raise ValueError("max_output_bytes must be positive")

    captured = bytearray()
    truncated = False
    try:
        proc = subprocess.Popen(list(argv), env=dict(env), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, shell=False,
                                start_new_session=True)
    except OSError as exc:
        raise LaunchError from exc
    with proc:
        assert proc.stdout is not None
        deadline = time.monotonic() + timeout_seconds
        timed_out = False
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                events = selector.select(remaining)
                if not events:
                    timed_out = True
                    break
                for key, _ in events:
                    chunk = os.read(key.fileobj.fileno(), 4096)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    available = max_output_bytes - len(captured)
                    captured.extend(chunk[:available])
                    truncated |= len(chunk) > available
        if timed_out:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            returncode = proc.wait(timeout=max(0.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            returncode = proc.wait()

    return CommandOutcome(
        returncode=None if timed_out else returncode,
        output=captured.decode("utf-8", errors="replace"),
        timed_out=timed_out,
        output_truncated=truncated,
    )


def queue_notice(thread_uuid: str, profile: str, notice: str, *,
                 timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
                 runner: Runner = run_bounded) -> EnqueueResult:
    """Queue a short notice to an existing UUID through an allowed local profile.

    ``profile`` is the recipient's exact registered profile, supplied by the
    board claim rather than inferred from the target UUID. Only trusted integration code should
    supply the optional runner; board data cannot choose an executable.
    """

    thread_uuid = _uuid(thread_uuid, "thread_uuid")
    home = _profile_home(profile)
    notice = _safe_text(notice, "notice", MAX_NOTICE_CHARS, multiline=True)
    if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise ValueError("timeout_seconds must be between 0 and 60 seconds")

    argv = [CODEX_COMMAND, "queue", "--thread", thread_uuid, "--message", notice,
            "-m", "gpt-6-sol", "-c", 'model_reasoning_effort="xhigh"',
            "-c", "mcp_servers={}"]
    env = os.environ.copy()
    env["CODEX_HOME"] = str(home)
    try:
        outcome = runner(argv, env, timeout_seconds, MAX_CAPTURE_BYTES)
    except LaunchError:
        return EnqueueResult("failed", None, None, "", reason="runner_launch_failed")
    except (OSError, subprocess.SubprocessError):
        # A runner error after Popen may have followed an enqueue request.
        return EnqueueResult("ambiguous", None, None, "", reason="sender_exception")

    match = _QUEUED_LINE.search(outcome.output)
    message_id = None
    if match:
        id_match = _UUID_IN_LINE.search(match.group())
        if id_match:
            message_id = _uuid(id_match.group(), "queue_message_id")

    if outcome.timed_out:
        status = "timeout"
    elif outcome.returncode == 0 and match:
        status = "queued"
    elif outcome.returncode != 0 and _REJECTED_LINE.search(outcome.output) and not match:
        status = "failed"
    else:
        status = "ambiguous"
    reason = {"queued": "queue_accepted", "failed": "queue_rejected",
              "timeout": "sender_timeout", "ambiguous": "unrecognized_queue_response"}[status]
    return EnqueueResult(status, message_id, outcome.returncode,
                         outcome.output, outcome.output_truncated, reason)


def _render_notice(event: Literal["new thread", "reply on"], thread_id: int,
                   title: str, notification_id: int, post_seq: int | None = None,
                   *, board_id: str, board_home: str | Path) -> str:
    board_id = _uuid(board_id, "board_id")
    board_home = Path(board_home)
    if not board_home.is_absolute():
        raise ValueError("board_home must be absolute")
    thread_id = _positive_id(thread_id, "thread_id")
    notification_id = _positive_id(notification_id, "notification_id")
    title = _safe_text(title, "title", MAX_TITLE_CHARS)
    if post_seq is None:
        heading = f"{event} {thread_id}: {title}"
        read = f"thread --id {thread_id}"
    else:
        post_seq = _positive_id(post_seq, "post_seq")
        heading = f"{event} {thread_id} post {post_seq}: {title}"
        read = f"thread --id {thread_id} --after {post_seq - 1}"
    return (f"{heading}\n"
            f"board ID: {board_id}\n"
            f"notification ID: {notification_id}\n"
            f"Read: python3 {shlex.quote(str(BOARD_SCRIPT))} --home {shlex.quote(str(board_home))} --board {board_id} {read}\n"
            "Advisory: A title is not an ownership decision; check the thread and owner acknowledgment.")


def render_new_thread(thread_id: int, title: str, notification_id: int,
                      *, board_id: str, board_home: str | Path) -> str:
    """Pure title/ID pointer for a newly opened public thread."""

    return _render_notice("new thread", thread_id, title, notification_id,
                          board_id=board_id, board_home=board_home)


def render_reply(thread_id: int, title: str, notification_id: int, post_seq: int,
                 *, board_id: str, board_home: str | Path) -> str:
    """Pure title/ID pointer for a reply routed by the board outbox."""

    return _render_notice("reply on", thread_id, title, notification_id,
                          post_seq, board_id=board_id, board_home=board_home)
