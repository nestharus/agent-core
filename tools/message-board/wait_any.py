#!/usr/bin/env python3
"""Watch multiple boards or multiplex them with one newly launched foreground child.

Child output is saved losslessly as records: stream byte (O/E), uint32 big-endian
length, then payload. Terminal JSON lines are pointers, not notice acknowledgments.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import selectors
import signal
import struct
import subprocess
import sys
import time

import active_listener
import catalog
import multi_board_watch


PREFIX = b"MESSAGE-BOARD-WAIT/1 "
READ_SIZE = 65536


def frame(event: str, **fields) -> None:
    data = PREFIX + json.dumps({"event": event, **fields}, sort_keys=True,
                               separators=(",", ":")).encode("ascii") + b"\n"
    if len(data) > 1024:
        raise multi_board_watch.WatchError("terminal frame too large")
    while data:
        written = os.write(1, data)
        if written == 0:
            raise multi_board_watch.WatchError("terminal write failed")
        data = data[written:]


def write_all(fd: int, data: bytes) -> None:
    while data:
        count = os.write(fd, data)
        if count == 0:
            raise multi_board_watch.WatchError("log write failed")
        data = data[count:]


def emit_notices(notices: list[dict]) -> None:
    for notice in notices:
        frame("BOARD", **notice)


def child_exit(code: int) -> int:
    return code if code >= 0 else 128 - code


def run_child(feed: multi_board_watch.BoardFeed, command: list[str], log: Path) -> int:
    if not command:
        raise multi_board_watch.WatchError("run requires a child command after --")
    status = Path(str(log) + ".status.json")
    if status.exists():
        raise multi_board_watch.WatchError("status file already exists")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW
    fd = os.open(log, flags, 0o600)
    child = None
    selector = selectors.DefaultSelector()
    offset = 0
    old_handlers = {}
    interrupted = None
    try:
        initial = feed.scan()
        for board in feed.boards:
            selector.register(board["receiver"], selectors.EVENT_READ, board)

        def on_signal(signum, _frame):
            nonlocal interrupted
            if interrupted is None:
                interrupted = signum

        for signum in (signal.SIGINT, signal.SIGTERM):
            old_handlers[signum] = signal.signal(signum, on_signal)
        child_env = os.environ.copy()
        child_env.pop("CODEX_SESSION_ID", None)
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 bufsize=0, start_new_session=True, env=child_env)
        assert child.stdout is not None and child.stderr is not None
        for pipe, stream in ((child.stdout, b"O"), (child.stderr, b"E")):
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, stream)
        frame("ARMED", pid=child.pid)
        emit_notices(initial)
        next_scan = time.monotonic() + multi_board_watch.RECHECK_SECONDS
        pipes = 2
        exit_seen = None
        term_sent = None
        while True:
            now = time.monotonic()
            if interrupted is not None and term_sent is None:
                try:
                    os.killpg(child.pid, interrupted)
                except ProcessLookupError:
                    pass
                term_sent = now
                frame("INTERRUPTED", signal=interrupted)
            if term_sent is not None and child.poll() is None and now - term_sent > 2:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if child.poll() is not None and exit_seen is None:
                exit_seen = now
            if exit_seen is not None and pipes and now - exit_seen > 3:
                raise multi_board_watch.WatchError("child pipe did not close after exit")
            if now >= next_scan:
                emit_notices(feed.scan())
                next_scan = now + multi_board_watch.RECHECK_SECONDS
            if exit_seen is not None and pipes == 0:
                break
            deadline = next_scan
            if exit_seen is not None:
                deadline = min(deadline, exit_seen + 3)
            if term_sent is not None and child.poll() is None:
                deadline = min(deadline, term_sent + 2)
            for key, _ in selector.select(max(0, min(0.25, deadline - time.monotonic()))):
                if isinstance(key.data, dict):
                    board = key.data
                    packet = board["receiver"].recv(256)
                    if packet != active_listener._packet(board["identity"]):
                        raise multi_board_watch.WatchError("wrong-board socket hint")
                    emit_notices(feed.scan())
                else:
                    pipe = key.fileobj
                    chunk = os.read(pipe.fileno(), READ_SIZE)
                    if chunk:
                        record = key.data + struct.pack("!I", len(chunk)) + chunk
                        write_all(fd, record)
                        offset += len(record)
                        os.fsync(fd)
                        frame("OUTPUT", log_offset=offset)
                    else:
                        selector.unregister(pipe)
                        pipe.close()
                        pipes -= 1
        child.wait()
        emit_notices(feed.scan())
        os.fsync(fd)
        status_fd = os.open(status, flags, 0o600)
        try:
            write_all(status_fd, json.dumps({"returncode": child.returncode,
                                             "log_offset": offset}, sort_keys=True).encode() + b"\n")
            os.fsync(status_fd)
        finally:
            os.close(status_fd)
        frame("EXIT", returncode=child.returncode, log_offset=offset)
        return child_exit(child.returncode)
    finally:
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)
        selector.close()
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", help="explicit shared catalog home")
    parser.add_argument("--session", required=True, help="matching CODEX_SESSION_ID")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--board", action="append", help="exact board UUID or catalog alias; repeatable")
    selection.add_argument("--all-joined", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    sub = parser.add_subparsers(dest="mode", required=True)
    watcher = sub.add_parser("watch", help="return board-qualified durable notice pointers")
    watcher.add_argument("--timeout", type=float, required=True)
    runner = sub.add_parser("run", help="foreground child and board feed in one terminal handle")
    runner.add_argument("--log", required=True, help="new unique binary output log path")
    runner.add_argument("command", nargs=argparse.REMAINDER, help="-- child argv")
    args = parser.parse_args(argv)
    if args.mode == "run" and args.command and args.command[0] == "--":
        args.command.pop(0)
    try:
        with multi_board_watch.BoardFeed(catalog.home_path(args.home), args.session,
                                         args.board, all_joined=args.all_joined,
                                         limit=args.limit) as feed:
            if args.mode == "watch":
                notices = feed.wait(args.timeout)
                print(json.dumps(notices, sort_keys=True))
                return 0 if notices else 3
            return run_child(feed, args.command, Path(args.log))
    except (multi_board_watch.WatchError, catalog.CatalogError, OSError,
            subprocess.SubprocessError) as exc:
        print(f"wait-any: {exc}", file=sys.stderr)
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
