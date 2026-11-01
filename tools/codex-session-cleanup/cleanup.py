#!/usr/bin/env python3
"""Conservative, metadata-only Codex exec-session cleanup for CLI 0.166.0."""

import argparse
import base64
import hashlib
import json
import os
import re
import socket
import sqlite3
import stat
import subprocess
import sys
import time
import uuid
from pathlib import Path

VERSION = "0.166.0"
THREAD_PAGE_SIZE = 10
DAEMON_RUNTIME_BASE = Path("/tmp")
SOURCES = ["cli", "vscode", "exec", "appServer", "subAgent", "subAgentReview",
           "subAgentCompact", "subAgentThreadSpawn", "subAgentOther", "unknown"]
CHILD_SOURCES = {"exec", "subAgent", "subAgentReview", "subAgentCompact",
                 "subAgentThreadSpawn", "subAgentOther"}
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
FIELDS = ("id", "source", "sourceParentThreadId", "createdAt", "updatedAt", "recencyAt",
          "parentThreadId", "sessionId", "forkedFromId", "ephemeral", "status", "historyMode")


class Refuse(Exception):
    pass


def require(ok, why):
    if not ok:
        raise Refuse(why)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def valid_uuid(value):
    return isinstance(value, str) and UUID.fullmatch(value) is not None and str(uuid.UUID(value)) == value


def file_identity(path, kind):
    path = Path(path).absolute()
    resolved = path.resolve(strict=True)
    logical = path.lstat()
    link_identity = {}
    if kind == "socket" and resolved != path:
        require(stat.S_ISLNK(logical.st_mode) and path.parent.resolve(strict=True) == path.parent,
                "socket path crosses an unexpected parent alias")
        runtime = DAEMON_RUNTIME_BASE / f"codex-daemon-{os.geteuid()}"
        require(resolved.parent == runtime and re.fullmatch(r"[0-9a-f]{64}", resolved.name),
                "socket symlink is outside the managed daemon runtime")
        directory = runtime.lstat()
        require(stat.S_ISDIR(directory.st_mode) and directory.st_uid == os.geteuid() and
                directory.st_mode & 0o077 == 0 and runtime.resolve(strict=True) == runtime,
                "managed daemon runtime ownership or permissions invalid")
        require(logical.st_uid == os.geteuid(), "socket link owner changed")
        link_identity = {"canonicalPath": str(resolved), "linkDevice": logical.st_dev,
                         "linkInode": logical.st_ino}
    else:
        require(resolved == path, "identity path crosses a symlink or alias")
    st = resolved.lstat()
    require(st.st_uid == os.geteuid(), "identity path owner differs from current user")
    if kind == "dir":
        require(stat.S_ISDIR(st.st_mode), "profile is not a directory")
    elif kind == "socket":
        require(stat.S_ISSOCK(st.st_mode), "socket is not a Unix socket")
    elif kind == "file":
        require(stat.S_ISREG(st.st_mode), "state database is not a regular file")
    require(not stat.S_ISLNK(st.st_mode), "identity target is a symlink")
    return {"path": str(path), "device": st.st_dev, "inode": st.st_ino, **link_identity}


def profile_identity(profile, sock):
    profile = Path(profile).absolute()
    return {"profile": file_identity(profile, "dir"),
            "socket": file_identity(sock, "socket"),
            "stateDb": file_identity(profile / "state_5.sqlite", "file")}


class Rpc:
    """JSON-RPC WebSocket client for an existing app-server Unix control socket."""

    def __init__(self, codex, profile, sock, deadline):
        self.deadline = deadline
        self.next_id = 1
        self.buffer = b""
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.sock.settimeout(self.remaining("socket connection"))
            # Managed control links can exceed Unix sun_path even when their
            # verified runtime target fits. A long custom path can also be
            # reached through a directory descriptor without changing cwd.
            target = Path(sock).resolve(strict=True)
            if len(os.fsencode(target)) < 108:
                self.sock.connect(str(target))
            else:
                parent = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    alias = f"/proc/self/fd/{parent}/{target.name}"
                    require(len(os.fsencode(alias)) < 108, "socket path too long")
                    self.sock.connect(alias)
                finally:
                    os.close(parent)
            self.handshake()
            reply = self.request("initialize", {"clientInfo": {
                "name": "codex_session_cleanup", "title": "Codex Session Cleanup", "version": "1.0"}})
            require(isinstance(reply, dict) and reply.get("codexHome") == profile,
                    "daemon profile identity does not match selected profile")
            self.send({"method": "initialized", "params": {}})
        except (OSError, socket.timeout):
            self.close()
            raise Refuse("app-server socket transport failed") from None
        except Exception:
            self.close()
            raise

    def remaining(self, action):
        left = self.deadline - time.monotonic()
        require(left > 0, f"{action} timed out")
        return left

    def recv_exact(self, count, action):
        while len(self.buffer) < count:
            self.sock.settimeout(self.remaining(action))
            try:
                data = self.sock.recv(min(65536, count - len(self.buffer)))
            except socket.timeout:
                raise Refuse(f"{action} timed out") from None
            except OSError:
                raise Refuse("app-server socket transport failed") from None
            require(data, "app-server socket closed before response")
            self.buffer += data
        result, self.buffer = self.buffer[:count], self.buffer[count:]
        return result

    def handshake(self):
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = ("GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n"
                   "Connection: Upgrade\r\nSec-WebSocket-Version: 13\r\n"
                   f"Sec-WebSocket-Key: {key}\r\n\r\n").encode("ascii")
        self.sock.settimeout(self.remaining("WebSocket handshake"))
        self.sock.sendall(request)
        while b"\r\n\r\n" not in self.buffer:
            require(len(self.buffer) < 16384, "WebSocket handshake too large")
            self.sock.settimeout(self.remaining("WebSocket handshake"))
            try:
                data = self.sock.recv(4096)
            except socket.timeout:
                raise Refuse("WebSocket handshake timed out") from None
            require(data, "app-server socket closed during handshake")
            self.buffer += data
        header, self.buffer = self.buffer.split(b"\r\n\r\n", 1)
        require(len(header) <= 16384, "WebSocket handshake too large")
        try:
            lines = header.decode("ascii").split("\r\n")
            fields = {}
            for line in lines[1:]:
                name, value = line.split(":", 1)
                name = name.strip().lower()
                require(name not in fields, "duplicate WebSocket handshake header")
                fields[name] = value.strip()
        except (UnicodeDecodeError, ValueError):
            raise Refuse("invalid WebSocket handshake") from None
        expected = base64.b64encode(hashlib.sha1(
            (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()).decode("ascii")
        require(lines[0] == "HTTP/1.1 101 Switching Protocols" and
                fields.get("upgrade", "").lower() == "websocket" and
                "upgrade" in {x.strip().lower() for x in fields.get("connection", "").split(",")} and
                fields.get("sec-websocket-accept") == expected,
                "app-server socket did not accept WebSocket upgrade")

    def frame(self, opcode, payload):
        require(len(payload) <= 8_000_000, "protocol message too large")
        mask = os.urandom(4)
        length = len(payload)
        header = bytes([0x80 | opcode, 0x80 | length]) if length < 126 else (
            bytes([0x80 | opcode, 0x80 | 126]) + length.to_bytes(2, "big") if length < 65536 else
            bytes([0x80 | opcode, 0x80 | 127]) + length.to_bytes(8, "big"))
        masked = bytes(value ^ mask[i % 4] for i, value in enumerate(payload))
        self.sock.settimeout(self.remaining("WebSocket send"))
        try:
            self.sock.sendall(header + mask + masked)
        except socket.timeout:
            raise Refuse("WebSocket send timed out") from None
        except OSError:
            raise Refuse("app-server socket transport failed") from None

    def message(self, action):
        parts = []
        size = 0
        fragmented = False
        while True:
            header = self.recv_exact(2, action)
            fin, opcode = bool(header[0] & 0x80), header[0] & 0x0f
            require(header[0] & 0x70 == 0 and header[1] & 0x80 == 0,
                    "invalid WebSocket frame flags")
            length = header[1] & 0x7f
            if length == 126:
                length = int.from_bytes(self.recv_exact(2, action), "big")
            elif length == 127:
                length = int.from_bytes(self.recv_exact(8, action), "big")
            require(length <= 8_000_000 - size, f"{action} protocol response too large")
            payload = self.recv_exact(length, action)
            if opcode == 0x9:
                require(fin and length <= 125, "invalid WebSocket ping")
                self.frame(0xA, payload)
                continue
            if opcode == 0xA:
                require(fin and length <= 125, "invalid WebSocket pong")
                continue
            if opcode == 0x8:
                raise Refuse("app-server closed WebSocket before RPC response")
            require(opcode == (0 if fragmented else 1), "unexpected WebSocket frame type")
            size += length
            parts.append(payload)
            if fin:
                return b"".join(parts)
            fragmented = True

    def send(self, obj):
        self.frame(1, canonical(obj))

    def request(self, method, params=None):
        request_id = self.next_id
        self.next_id += 1
        obj = {"id": request_id, "method": method}
        if params is not None:
            obj["params"] = params
        self.send(obj)
        while True:
            try:
                msg = json.loads(self.message(method))
            except (UnicodeDecodeError, ValueError):
                raise Refuse("invalid app-server protocol response") from None
            if not isinstance(msg, dict) or msg.get("id") != request_id:
                continue  # Notifications may contain conversation text. Never emit them.
            if "error" in msg:
                code = msg["error"].get("code") if isinstance(msg["error"], dict) else None
                raise Refuse(f"{method} refused (RPC code {code if isinstance(code, int) else 'unknown'})")
            require("result" in msg, "RPC response lacks result")
            return msg["result"]

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def pages(rpc, method, params, max_pages, project=None):
    seen_cursors = set()
    cursor = None
    out = []
    for _ in range(max_pages):
        p = dict(params)
        if cursor is not None:
            p["cursor"] = cursor
        result = rpc.request(method, p)
        require(isinstance(result, dict) and isinstance(result.get("data"), list),
                f"{method} pagination data unavailable")
        require(len(result["data"]) <= params["limit"], f"{method} exceeded requested page size")
        # Discard unneeded reply fields on each page rather than retaining
        # server previews for the whole profile while gathering the index.
        out.extend(project(item) if project else item for item in result["data"])
        if "nextCursor" not in result:
            require(len(result["data"]) < params["limit"],
                    f"{method} pagination metadata unavailable at full page")
        cursor = result.get("nextCursor")
        if cursor is None:
            return out
        require(isinstance(cursor, str) and cursor and cursor not in seen_cursors,
                f"{method} pagination cursor invalid or repeated")
        seen_cursors.add(cursor)
    raise Refuse(f"{method} exceeded page limit; graph incomplete")


def source_kind(raw):
    if isinstance(raw, str):
        return raw if raw in SOURCES else "unknown", None
    if not isinstance(raw, dict) or set(raw) != {"subAgent"}:
        return "unknown", None
    sub = raw["subAgent"]
    if sub == "review":
        return "subAgentReview", None
    if sub == "compact":
        return "subAgentCompact", None
    if sub == "memory_consolidation":
        return "subAgentOther", None
    if isinstance(sub, dict) and set(sub) == {"thread_spawn"} and isinstance(sub["thread_spawn"], dict):
        parent = sub["thread_spawn"].get("parent_thread_id")
        return ("subAgentThreadSpawn", parent) if valid_uuid(parent) else ("unknown", None)
    if isinstance(sub, dict) and set(sub) == {"other"}:
        return "subAgentOther", None
    return "unknown", None


def thread_record(t):
    require(isinstance(t, dict), "thread metadata invalid")
    require(valid_uuid(t.get("id")) and valid_uuid(t.get("sessionId")), "thread ID invalid")
    kind, source_parent = source_kind(t.get("source"))
    for key in ("parentThreadId", "forkedFromId"):
        require(t.get(key) is None or valid_uuid(t[key]), f"{key} invalid")
    for key in ("createdAt", "updatedAt"):
        require(type(t.get(key)) is int and t[key] >= 0, f"{key} unavailable")
    recency = t.get("recencyAt")
    require(recency is None or (type(recency) is int and recency >= 0), "recencyAt invalid")
    require(type(t.get("ephemeral")) is bool, "ephemeral state unavailable")
    status = t.get("status")
    require(isinstance(status, dict) and status.get("type") in
            ("notLoaded", "idle", "active", "systemError"), "status unavailable")
    require(t.get("historyMode") in ("legacy", "paginated"), "history mode unavailable")
    # This whitelist excludes preview, name, cwd, turns, and all instruction text.
    result = {key: t.get(key) for key in FIELDS}
    result["source"] = kind
    result["sourceParentThreadId"] = source_parent
    result["status"] = {"type": status["type"]}
    return result


def state_metadata(profile):
    """Read only the pin bit and structural edges absent from 0.166.0 RPC schema."""
    db = Path(profile) / "state_5.sqlite"
    connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(threads)")}
        require({"id", "is_pinned", "attached_thread_parent_id"} <= columns,
                "pin or lineage state schema unavailable")
        rows = connection.execute("SELECT id,is_pinned,attached_thread_parent_id FROM threads").fetchall()
        edges = connection.execute("SELECT parent_thread_id,child_thread_id,status FROM thread_spawn_edges").fetchall()
        connection.execute("COMMIT")
    except sqlite3.Error:
        raise Refuse("state metadata read failed") from None
    finally:
        connection.close()
    pins = {}
    attached = {}
    for thread_id, pin, parent in rows:
        require(valid_uuid(thread_id) and pin in (0, 1) and
                (parent is None or valid_uuid(parent)), "pin or lineage state invalid")
        require(thread_id not in pins, "duplicate state thread ID")
        pins[thread_id] = bool(pin)
        attached[thread_id] = parent
    graph_edges = set()
    for parent, child, status in edges:
        require(valid_uuid(parent) and valid_uuid(child) and isinstance(status, str) and status,
                "spawn edge state invalid")
        graph_edges.add((parent, child))
    return pins, attached, graph_edges


def snapshot(rpc, profile, max_pages, allow_unlisted=False):
    threads = {}
    for archived in (False, True):
        entries = pages(rpc, "thread/list", {"archived": archived, "sourceKinds": SOURCES,
                                            "useStateDbOnly": True,
                                            "limit": THREAD_PAGE_SIZE}, max_pages,
                        project=thread_record)
        for entry in entries:
            t = entry
            require(t["id"] not in threads, "duplicate thread across pages or archive states")
            t["archived"] = archived
            threads[t["id"]] = t
    loaded = pages(rpc, "thread/loaded/list", {"limit": 100}, max_pages)
    require(all(valid_uuid(x) for x in loaded), "loaded thread ID invalid")
    loaded = set(loaded)
    pins, attached, stored_edges = state_metadata(profile)
    state_only = set(pins) - set(threads)
    require(set(threads) <= set(pins) and (allow_unlisted or not state_only),
            f"state DB and RPC thread inventories differ (RPC {len(threads)}, state {len(pins)}, "
            f"state-only {len(set(pins) - set(threads))}, RPC-only {len(set(threads) - set(pins))})")
    # Planning can show a provisional draft while preserving every entry that
    # lacks RPC metadata. Apply still requires an exact, complete inventory.
    for tid in state_only:
        threads[tid] = {"id": tid, "metadataUnavailable": True}
    edges = set(stored_edges)
    for tid, t in threads.items():
        t["isPinned"] = pins[tid]
        t["loaded"] = tid in loaded
        for parent in (t.get("parentThreadId"), t.get("sourceParentThreadId"),
                       t.get("forkedFromId"), attached[tid]):
            if parent is not None:
                edges.add((parent, tid))
        if t.get("sessionId") is not None and t["sessionId"] != tid:
            edges.add((t["sessionId"], tid))
    require(loaded <= set(threads), "loaded inventory contains an unlisted thread")
    require(all(p in threads and c in threads and p != c for p, c in edges),
            "lineage graph has missing or invalid members")
    # A cycle makes cascade extent ambiguous.
    children = {tid: set() for tid in threads}
    for parent, child in edges:
        children[parent].add(child)
    def visit(node, active, done):
        require(node not in active, "lineage graph cycle")
        if node in done:
            return
        active.add(node)
        for child in children[node]:
            visit(child, active, done)
        active.remove(node)
        done.add(node)
    done = set()
    for tid in children:
        visit(tid, set(), done)
    return threads, children


def descendants(root, children):
    found = set()
    todo = [root]
    while todo:
        node = todo.pop()
        if node not in found:
            found.add(node)
            todo.extend(children[node])
    return found


def age_ok(t, now, min_age):
    last = max(v for v in (t["createdAt"], t["updatedAt"], t["recencyAt"]) if v is not None)
    return last <= now and now - last >= min_age


def qualified(t, now, min_age, retain, root=False):
    if t.get("metadataUnavailable"):
        return False
    if t["id"] in retain:
        return False
    if t["isPinned"] or t["loaded"] or t["status"]["type"] != "notLoaded":
        return False
    if t["ephemeral"] or not age_ok(t, now, min_age):
        return False
    if root:
        return t["source"] == "exec" and t["parentThreadId"] is None and t["sessionId"] == t["id"]
    return isinstance(t["source"], str) and t["source"] in CHILD_SOURCES


def make_plan(identity, threads, children, retain, now, min_age):
    require(all(x in threads for x in retain), "retained ID missing from complete inventory")
    candidates = []
    for tid in sorted(threads):
        if not qualified(threads[tid], now, min_age, retain, root=True):
            continue
        cascade = descendants(tid, children)
        if not all(qualified(threads[x], now, min_age, retain) for x in cascade):
            continue
        candidates.append({"root": tid, "cascade": [threads[x] for x in sorted(cascade)]})
    # Do not select overlapping cascades.
    selected = set()
    for candidate in candidates:
        ids = {t["id"] for t in candidate["cascade"]}
        require(not selected.intersection(ids), "overlapping deletion cascades")
        selected.update(ids)
    plan = {"format": 1, "codexVersion": VERSION, "profile": identity,
            "generatedAt": now, "minAgeSeconds": min_age,
            "retainedIds": sorted(retain), "candidates": candidates,
            "inventoryCount": len(threads)}
    plan["planId"] = digest(plan)
    return plan


def goal_state(rpc, thread_id):
    result = rpc.request("thread/goal/get", {"threadId": thread_id})
    require(isinstance(result, dict) and "goal" in result, "goal metadata unavailable")
    goal = result["goal"]
    if goal is None:
        return None
    require(isinstance(goal, dict), "goal metadata invalid")
    # Never retain objective text or an unrecognized server value.
    return "complete" if goal.get("status") == "complete" else "unfinished"


def prepare_plan(rpc, identity, threads, children, retain, now, min_age, batch_limit):
    plan = make_plan(identity, threads, children, retain, now, min_age)
    ordered = sorted(plan["candidates"], key=lambda candidate: (
        max(max(t["createdAt"], t["updatedAt"], t["recencyAt"] or 0)
            for t in candidate["cascade"]), candidate["root"]))
    selected = []
    protected = 0
    examined = 0
    for candidate in ordered:
        if len(selected) >= batch_limit:
            break
        examined += 1
        goals = {member["id"]: goal_state(rpc, member["id"])
                 for member in candidate["cascade"]}
        if any(value == "unfinished" for value in goals.values()):
            protected += 1
            continue
        selected.append({**candidate, "goalStates": goals})
    index_only = sum(bool(t.get("metadataUnavailable")) for t in threads.values())
    plan.update(format=3, candidates=selected, batchLimit=batch_limit,
                indexOnlyRetainedCount=index_only, inventoryCompleteForApply=index_only == 0,
                preliminaryRootCount=len(ordered), goalProtectedRootsExamined=protected,
                unexaminedRootCount=len(ordered) - examined)
    plan.pop("planId")
    plan["planId"] = digest(plan)
    return plan


def exact_read(rpc, member):
    result = rpc.request("thread/read", {"threadId": member["id"], "includeTurns": False})
    require(isinstance(result, dict) and "thread" in result, "thread/read metadata unavailable")
    read = thread_record(result["thread"])
    for key in FIELDS:
        require(read[key] == member[key], "thread/read disagrees with current inventory")


def write_new(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        write_all(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    sync_parent(path)


def sync_parent(path):
    fd = os.open(Path(path).absolute().parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def receipt(fd, event):
    write_all(fd, canonical(event) + b"\n")
    os.fsync(fd)


def write_all(fd, data):
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


def read_retained(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as source:
        require(stat.S_ISREG(os.fstat(source.fileno()).st_mode), "retention input is not a regular file")
        content = source.read(1_000_001)
    require(len(content) <= 1_000_000, "retention file too large")
    values = json.loads(content)
    require(isinstance(values, list) and all(valid_uuid(v) for v in values) and
            len(values) == len(set(values)), "retention file must be a unique UUID JSON array")
    return set(values)


def check_cli(codex):
    try:
        r = subprocess.run([codex, "--version"], text=True, capture_output=True, timeout=5,
                           env={"HOME": str(Path.home()), "PATH": "/usr/bin:/bin"})
    except (OSError, subprocess.TimeoutExpired):
        raise Refuse("Codex CLI unavailable or timed out") from None
    require(r.returncode == 0 and r.stdout.strip() == f"codex-cli {VERSION}",
            f"requires Codex CLI {VERSION}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", choices=("plan", "apply"), default="plan")
    parser.add_argument("--profile", required=True, help="exact CODEX_HOME profile directory")
    parser.add_argument("--socket", help="existing daemon control socket; defaults to the selected profile's standard path")
    parser.add_argument("--retain", help="JSON array of explicitly retained UUIDs; required for apply")
    parser.add_argument("--plan", required=True, help="new plan path for plan; existing path for apply")
    parser.add_argument("--receipt", help="new append-only receipt path for apply")
    parser.add_argument("--codex", default="/home/nes/.npm-global/bin/codex")
    parser.add_argument("--min-age-hours", type=int, default=24)
    parser.add_argument("--max-pages", type=int, default=1000)
    parser.add_argument("--max-delete", type=int, default=10)
    parser.add_argument("--deadline-seconds", type=int, default=60)
    parser.add_argument("--exclusive-maintenance", action="store_true",
                        help="assert every client is quiesced and new profile access prevented for the entire apply")
    parser.add_argument("--complete-index", action="store_true",
                        help="assert all persistent rollouts and descendant links are indexed in state_5.sqlite")
    args = parser.parse_args(argv)
    require(args.min_age_hours >= 24, "minimum age must be at least 24 hours")
    require(1 <= args.max_pages <= 1000 and 1 <= args.max_delete <= 100 and
            1 <= args.deadline_seconds <= 600, "invalid bounded work limit")
    require(args.mode != "apply" or (args.receipt and args.exclusive_maintenance and args.complete_index),
            "apply requires --receipt, --exclusive-maintenance and --complete-index")
    require(args.mode != "apply" or args.retain, "apply requires explicit --retain preservation input")
    require(args.mode != "plan" or not args.receipt, "receipt is for apply only")
    check_cli(args.codex)
    if args.socket is None:
        args.socket = str(Path(args.profile).absolute() / "app-server-control" / "app-server-control.sock")
    identity = profile_identity(args.profile, args.socket)
    retain = read_retained(args.retain) if args.retain else set()
    profile = identity["profile"]["path"]
    deadline = time.monotonic() + args.deadline_seconds
    # Bind this connection to the target captured in the verified identity.
    # Later apply checks still compare the logical link and target in full.
    rpc_socket = identity["socket"].get("canonicalPath", identity["socket"]["path"])
    rpc = Rpc(args.codex, profile, rpc_socket, deadline)
    try:
        if args.mode == "plan":
            threads, children = snapshot(rpc, profile, args.max_pages, allow_unlisted=True)
            plan = prepare_plan(rpc, identity, threads, children, retain, int(time.time()),
                                args.min_age_hours * 3600, args.max_delete)
            write_new(args.plan, canonical(plan) + b"\n")
            print(json.dumps({"plan": args.plan, "planId": plan["planId"],
                              "candidates": len(plan["candidates"]), "mutated": False,
                              "provisional": not plan["inventoryCompleteForApply"],
                              "indexOnlyRetainedCount": plan["indexOnlyRetainedCount"]}, sort_keys=True))
            return 0
        plan = json.loads(Path(args.plan).read_bytes())
        require(isinstance(plan, dict) and plan.get("format") == 3, "plan format invalid")
        plan_id = plan.pop("planId", None)
        require(plan_id == digest(plan), "plan changed or corrupt")
        plan["planId"] = plan_id
        require(plan.get("inventoryCompleteForApply") is True and
                plan.get("indexOnlyRetainedCount") == 0,
                "provisional plan cannot be applied; complete RPC/state inventory required")
        require(plan["codexVersion"] == VERSION and plan["profile"] == identity and
                plan["retainedIds"] == sorted(retain) and
                plan["minAgeSeconds"] == args.min_age_hours * 3600 and
                plan["batchLimit"] == args.max_delete,
                "profile, retention, age or version changed since plan")
        require(0 <= len(plan["candidates"]) <= args.max_delete,
                "plan exceeds --max-delete batch limit")
        fd = os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        completed = 0
        try:
            receipt(fd, {"event": "begin", "planId": plan_id, "profile": identity,
                         "candidateCount": len(plan["candidates"])})
            sync_parent(args.receipt)
            # Recompute the whole plan. No effect if any metadata or graph member changed.
            current, children = snapshot(rpc, profile, args.max_pages)
            rebuilt = prepare_plan(rpc, identity, current, children, retain, plan["generatedAt"],
                                   plan["minAgeSeconds"], plan["batchLimit"])
            require(rebuilt == plan, "inventory, lineage or eligibility changed since plan")
            for candidate in plan["candidates"]:
                require(time.monotonic() < deadline, "deadline exceeded before next deletion")
                require(profile_identity(profile, args.socket) == identity, "profile identity changed")
                fresh, fresh_children = snapshot(rpc, profile, args.max_pages)
                require(descendants(candidate["root"], fresh_children) ==
                        {m["id"] for m in candidate["cascade"]}, "cascade changed")
                now = int(time.time())
                for member in candidate["cascade"]:
                    require(fresh.get(member["id"]) == member, "candidate metadata changed")
                    require(qualified(member, now, plan["minAgeSeconds"], retain,
                                      root=member["id"] == candidate["root"]),
                            "candidate no longer qualifies")
                    exact_read(rpc, member)
                    require(goal_state(rpc, member["id"]) == candidate["goalStates"][member["id"]],
                            "goal state changed since plan")
                receipt(fd, {"event": "intent", "root": candidate["root"],
                             "cascadeIds": [m["id"] for m in candidate["cascade"]]})
                # A timeout after intent is uncertain, never replayed automatically.
                result = rpc.request("thread/delete", {"threadId": candidate["root"]})
                require(result == {}, "thread/delete returned unexpected result")
                after, _ = snapshot(rpc, profile, args.max_pages)
                require(not ({m["id"] for m in candidate["cascade"]} & set(after)),
                        "delete response succeeded but cascade remains in inventory")
                receipt(fd, {"event": "success", "root": candidate["root"],
                             "cascadeIds": [m["id"] for m in candidate["cascade"]]})
                completed += 1
            receipt(fd, {"event": "complete", "succeeded": completed})
        except Exception as exc:
            receipt(fd, {"event": "stopped", "succeeded": completed,
                         "reason": str(exc) if isinstance(exc, Refuse) else "unexpected failure"})
            raise
        finally:
            os.close(fd)
        print(json.dumps({"receipt": args.receipt, "planId": plan_id,
                          "succeeded": completed, "mutated": bool(completed)}, sort_keys=True))
        return 0
    finally:
        rpc.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Refuse, OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        # Avoid echoing protocol messages, conversation text, paths from server, or credentials.
        detail = str(exc) if isinstance(exc, Refuse) else "invalid or unavailable local input"
        print(f"refused: {detail}", file=sys.stderr)
        sys.exit(2)
