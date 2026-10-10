#!/usr/bin/env python3
"""Catchable-signal custody for the dispatcher's native attempts.

The module keeps its name from the retired Codex profile lease. No profile
lock is taken any more: concurrent launches on one profile run side by side.
Nothing here reads, renews or copies credentials.
"""

import signal


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
