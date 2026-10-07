#!/usr/bin/env python3
"""Codex profile lease and catchable-signal custody for the dispatcher.

The lease is an advisory exclusive flock on our own file inside the original
profile. Every Codex writer this tool launches takes it: the direct launcher
for its whole Codex run, and the native path for the whole caller operation,
because the registered adapter runs native Codex on that original store and
Codex refreshes its own login there. It does not cover interactive Codex,
editors, desktop apps or copies of the profile. Nothing here reads, renews or
copies credentials.
"""

import fcntl
import os
from pathlib import Path
import signal
import time

LEASE_NAME = ".oulipoly-direct-child.lease"


class CatchSignals:
    """Keep cleanup ownership across preparation, Popen and collection.

    Handlers record cancellation rather than raising inside resource creation.
    Once a caller exists, forward cancellation and continue collecting it.
    SIGKILL and kernel-uninterruptible work cannot be handled here.
    """

    def __init__(self):
        self.received = None
        self.process = None

    def _receive(self, sig, frame):
        if self.received is None:
            self.received = sig
        self._forward(sig)

    def _forward(self, sig):
        if self.process is not None:
            try:
                self.process.send_signal(sig)
            except OSError:
                pass  # Still collect the caller; it may already have exited.

    def collect(self, process):
        self.process = process
        if self.received is not None:
            self._forward(self.received)

    def __enter__(self):
        self.previous = {sig: signal.signal(sig, self._receive)
                         for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
        return self

    def __exit__(self, *exc):
        for sig, handler in self.previous.items():
            signal.signal(sig, handler)


class LeaseTimeout(Exception):
    """Another writer we launched held the profile for the whole bound."""


class Interrupted(Exception):
    """A catchable signal arrived while waiting for the lease."""


# ----------------------------------------------------------------- lease

class ProfileLease:
    """Exclusive advisory lease on <profile>/LEASE_NAME, waited for at most
    wait_s. The descriptor is close-on-exec, so launched children and their
    descendants never inherit the lock."""

    def __init__(self, profile_home, wait_s, poll_s=0.1, interrupts=None):
        self.path = Path(profile_home) / LEASE_NAME
        self.wait_s, self.poll_s = wait_s, poll_s
        self.fd = None
        self.waited_s = None
        self.interrupts = interrupts

    def __enter__(self):
        start = time.monotonic()
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            while True:
                if self.interrupts is not None and self.interrupts.received is not None:
                    raise Interrupted
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
