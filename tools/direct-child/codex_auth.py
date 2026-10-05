#!/usr/bin/env python3
"""Codex profile lease, access-token freshness and gated official renewal.

The lease is an advisory exclusive flock on our own file inside the profile.
Every writer this tool launches takes it: the direct launcher for its whole
Codex run, and the native path for check, renewal and access snapshot. It does
not cover interactive Codex, editors, desktop apps or copies of the profile.

Renewal asks the installed Codex CLI to refresh through its own code:
`codex app-server` over stdio, `initialize`, `initialized`, then
`account/read {"refreshToken": true}`. That response does not report the
refresh result, so the outcome is judged from the profile's access-token
expiry before and after. Nothing here POSTs to the issuer, prints or records
token text, account metadata or server stderr, or repeats a refresh.

    codex_auth.py status --profile .codex4 [--lease-wait S]
    codex_auth.py renew --profile .codex4 --need-s N [--lease-wait S] [--timeout S]
"""

import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import sys
import time

LEASE_NAME = ".oulipoly-direct-child.lease"
AUTH_LIMIT = 1024 * 1024
LINE_LIMIT = 1024 * 1024
CAPTURE_LIMIT = 8 * 1024 * 1024
EXIT_GRACE_S = 5
KILL_GRACE_S = 2
CLIENT_INFO = {"name": "oulipoly_direct_child", "title": None, "version": "1"}


class LeaseTimeout(Exception):
    """Another writer we launched held the profile for the whole bound."""


class AuthUnavailable(Exception):
    """No readable file-store ChatGPT access token; the reason quotes nothing."""


# ----------------------------------------------------------------- lease

class ProfileLease:
    """Exclusive advisory lease on <profile>/LEASE_NAME, waited for at most
    wait_s. The descriptor is close-on-exec, so launched children and their
    descendants never inherit the lock."""

    def __init__(self, profile_home, wait_s, poll_s=0.1):
        self.path = Path(profile_home) / LEASE_NAME
        self.wait_s, self.poll_s = wait_s, poll_s
        self.fd = None
        self.waited_s = None

    def __enter__(self):
        start = time.monotonic()
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() - start >= self.wait_s:
                        raise LeaseTimeout(f"profile lease busy for {self.wait_s}s") from None
                    time.sleep(self.poll_s)
        except BaseException:
            os.close(fd)
            raise
        self.fd, self.waited_s = fd, round(time.monotonic() - start, 3)
        return self

    def __exit__(self, *exc):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


# ------------------------------------------------------- credential state

def _read_owned(path):
    """The caller's own regular file, without following a final symlink or
    blocking on a FIFO."""
    st = os.lstat(path)
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid():
        raise AuthUnavailable("auth.json is not the caller's own regular file")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_uid != os.getuid():
            raise AuthUnavailable("auth.json changed while opening")
        data = b""
        while chunk := os.read(fd, 65536):
            data += chunk
            if len(data) > AUTH_LIMIT:
                raise AuthUnavailable("auth.json is too large")
        return data
    finally:
        os.close(fd)


def jwt_exp(token):
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    exp = claims["exp"]
    if type(exp) is not int or exp <= 0:
        raise ValueError
    return exp


def read_access(profile_home):
    """(exp, access-only tokens) from the file store.
    Errors carry only their type, never file content."""
    path = Path(profile_home) / "auth.json"
    try:
        tokens = json.loads(_read_owned(path))["tokens"]
        access = tokens["access_token"]
        if not isinstance(access, str) or access.count(".") != 2:
            raise ValueError
        exp = jwt_exp(access)
        account = tokens.get("account_id")
    except AuthUnavailable:
        raise
    except FileNotFoundError:
        raise AuthUnavailable("no file-store auth.json (keyring or logged out)") from None
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
        raise AuthUnavailable(f"auth.json has no ChatGPT access token ({type(error).__name__})") from None
    snapshot = {"access_token": access}
    if isinstance(account, str) and account:
        snapshot["account_id"] = account
    return exp, snapshot


def write_access_snapshot(directory, snapshot):
    """Access-only profile copy for the native caller: no refresh grant, no
    id token. Private directory and file; the caller removes it."""
    directory = Path(directory)
    directory.mkdir(mode=0o700)
    fd = os.open(directory / "auth.json",
                 os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump({"tokens": snapshot}, handle)


def remove_access_snapshot(directory):
    directory = Path(directory)
    try:
        (directory / "auth.json").unlink(missing_ok=True)
        if directory.exists():
            directory.rmdir()
    except OSError as error:
        return type(error).__name__
    return None


# --------------------------------------------------------- app-server RPC

def _request(rid, method, params):
    return json.dumps({"id": rid, "method": method, "params": params}).encode() + b"\n"


def app_server_refresh(codex_home, timeout_s, codex="codex", cwd=None):
    """One bounded official refresh request. Returns a record with no message
    text, account fields or stderr: the server's stderr is discarded unread."""
    record = {"rpc": None, "stage": "launch", "error_code": None, "account_present": None,
              "requires_openai_auth": None, "server_stop": None, "server_exit": None,
              "unsolicited_lines": 0}
    start = time.monotonic()
    env = os.environ | {"CODEX_HOME": str(codex_home)}
    try:
        proc = subprocess.Popen([codex, "app-server", "--listen", "stdio://"],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, cwd=cwd, env=env,
                                start_new_session=True)
    except OSError as error:
        record.update(rpc="launch-failed", launch_error=type(error).__name__,
                      elapsed_s=round(time.monotonic() - start, 3))
        return record
    selector = selectors.DefaultSelector()
    os.set_blocking(proc.stdout.fileno(), False)
    selector.register(proc.stdout, selectors.EVENT_READ)
    buffer, total = b"", 0

    def response(rid):
        nonlocal buffer, total
        while True:
            while b"\n" in buffer:
                raw, buffer = buffer.split(b"\n", 1)
                try:
                    message = json.loads(raw)
                except ValueError:
                    raise _Protocol("unparsed-line") from None
                if not isinstance(message, dict):
                    raise _Protocol("non-object-message")
                if "method" in message or message.get("id") != rid:
                    record["unsolicited_lines"] += 1
                    continue
                return message
            if len(buffer) > LINE_LIMIT:
                raise _Protocol("line-limit")
            remaining = start + timeout_s - time.monotonic()
            if remaining <= 0:
                raise _Timeout
            if not selector.select(timeout=remaining):
                continue
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                raise _Protocol("eof-before-response")
            total += len(chunk)
            if total > CAPTURE_LIMIT:
                raise _Protocol("capture-limit")
            buffer += chunk

    try:
        record["stage"] = "initialize"
        proc.stdin.write(_request(1, "initialize", {
            "clientInfo": CLIENT_INFO,
            # Never start browser sign-in from a renewal helper.
            "capabilities": {"explicitGatewayOauth": True}}))
        proc.stdin.flush()
        reply = response(1)
        if "error" in reply:
            raise _RpcError(reply["error"])
        record["stage"] = "account/read"
        proc.stdin.write(json.dumps({"method": "initialized"}).encode() + b"\n"
                         + _request(2, "account/read", {"refreshToken": True}))
        proc.stdin.flush()
        reply = response(2)
        if "error" in reply:
            raise _RpcError(reply["error"])
        result = reply.get("result")
        if not isinstance(result, dict):
            raise _Protocol("result-not-object")
        record.update(rpc="answered", account_present=result.get("account") is not None,
                      requires_openai_auth=result.get("requiresOpenaiAuth")
                      if isinstance(result.get("requiresOpenaiAuth"), bool) else None)
    except _RpcError as error:
        code = error.args[0].get("code") if isinstance(error.args[0], dict) else None
        record.update(rpc="error", error_code=code if type(code) is int else None)
    except _Timeout:
        record["rpc"] = "timeout"
    except _Protocol as error:
        record.update(rpc="protocol-error", protocol_error=error.args[0])
    except OSError as error:
        record.update(rpc="protocol-error", protocol_error=f"pipe:{type(error).__name__}")
    finally:
        selector.close()
        record["server_stop"], record["server_exit"] = _stop(proc)
        record["elapsed_s"] = round(time.monotonic() - start, 3)
    return record


class _Protocol(Exception):
    pass


class _Timeout(Exception):
    pass


class _RpcError(Exception):
    pass


def _stop(proc):
    """Close stdin (the server's EOF shutdown), then bounded TERM and KILL of
    its session. No unbounded wait."""
    for pipe in (proc.stdin, proc.stdout):
        try:
            pipe.close()
        except OSError:
            pass
    for how, grace in (("exited", EXIT_GRACE_S), ("terminated", KILL_GRACE_S),
                       ("killed", KILL_GRACE_S)):
        if how != "exited":
            try:
                os.killpg(proc.pid, signal.SIGTERM if how == "terminated" else signal.SIGKILL)
            except OSError:
                pass
        try:
            return how, proc.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            continue
    return "unknown", None


# ------------------------------------------------------------ gated renew

def ensure_fresh(codex_home, need_s, timeout_s, codex="codex", cwd=None, now=time.time):
    """Under a lease the caller holds: refresh only when the access token has
    less than need_s left. One attempt, never repeated. Returns (record,
    snapshot or None); snapshot is set only when the token is fresh enough."""
    record = {"need_s": need_s}
    try:
        exp, snapshot = read_access(codex_home)
    except AuthUnavailable as error:
        record.update(renewal="unavailable", reason=str(error), issuer_contact="none",
                      profile_written="no")
        return record, None
    record["remaining_s_before"] = exp - int(now())
    if record["remaining_s_before"] >= need_s:
        record.update(renewal="not-needed", issuer_contact="none", profile_written="no")
        return record, snapshot
    rpc = app_server_refresh(codex_home, timeout_s, codex=codex, cwd=cwd)
    record["app_server"] = rpc
    record["issuer_contact"] = "possible" if rpc["stage"] == "account/read" else "none"
    try:
        exp_after, snapshot = read_access(codex_home)
        record["remaining_s_after"] = exp_after - int(now())
    except AuthUnavailable as error:
        exp_after, snapshot = None, None
        record["after_reason"] = str(error)
    changed = None if exp_after is None else exp_after != exp
    if rpc["rpc"] != "answered":
        # A stopped server may or may not have written; never retry or fall back.
        record.update(renewal=f"helper-{rpc['rpc']}", profile_written="unknown",
                      expiry_changed=changed)
        return record, None
    if exp_after is None:
        record.update(renewal="unreadable-after", profile_written="unknown")
        return record, None
    record["profile_written"] = "yes" if changed else "not-observed"
    if not changed:
        # account/read answers even when the refresh failed; the class
        # (expired, reused, revoked or transient) is not reported to us.
        record["renewal"] = "not-renewed"
        return record, None
    if record["remaining_s_after"] < need_s:
        record["renewal"] = "renewed-insufficient"
        return record, None
    record["renewal"] = "renewed"
    return record, snapshot


# -------------------------------------------------------------------- CLI

def main(argv):
    parser = argparse.ArgumentParser(prog="codex_auth.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("status", "renew"))
    parser.add_argument("--profile", required=True,
                        choices=(".codex", ".codex2", ".codex3", ".codex4", ".codex5"))
    parser.add_argument("--need-s", type=int)
    parser.add_argument("--lease-wait", type=float, default=120)
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args(argv)
    if (args.command == "renew") != (args.need_s is not None):
        parser.error("--need-s goes with renew, and renew needs it")
    home = Path(os.path.expanduser("~")) / args.profile
    try:
        with ProfileLease(home, args.lease_wait) as lease:
            if args.command == "status":
                try:
                    exp, _ = read_access(home)
                    record = {"remaining_s": exp - int(time.time())}
                except AuthUnavailable as error:
                    record = {"unavailable": str(error)}
            else:
                record, _ = ensure_fresh(home, args.need_s, args.timeout)
            record["lease_waited_s"] = lease.waited_s
    except LeaseTimeout as error:
        print(json.dumps({"lease": "timeout", "reason": str(error)}))
        return 75
    print(json.dumps(record, sort_keys=True))
    return 0 if record.get("renewal", "not-needed") in ("not-needed", "renewed") \
        and "unavailable" not in record else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
