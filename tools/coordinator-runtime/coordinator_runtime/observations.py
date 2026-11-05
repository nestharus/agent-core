"""Finite, process-local public timings. No payloads, persistence or worker.

The owning invocation installs a record. Context follows its existing asyncio
tasks; it never identifies another process as the service custodian. Entries
expire with that invocation. Snapshots omit arbitrary arguments and exceptions.
"""
import asyncio
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from time import monotonic

LIMIT = 9007199254740991
RECENT = 64
ACTIVE = 64
WINDOW_SECONDS = 300
LABELS = frozenset('''config-load store-open current configuration-current
source-release source-implementation source-files retained-events retained-outboxes
retained-source board-authority retained-authority
board-scan retained-step receipts reconcile_completed intake
schedule_classifications schedule_classification_recovery schedule_job
schedule_recovery custodian_progress automatic_cleanup capacity delivery
alerts control-connect control-send control-reply control-close control-read
control-validate control-status control-recover control-stop control-close-review
control-write service-current service-boards rpc-send-drain rpc-reply-wait rpc-other
initialize config/read thread/start thread/read thread/unsubscribe turn/start turn/interrupt'''.split())
_record = ContextVar('public_observations', default=None)
_parent = ContextVar('public_observation_parent', default=0)


def bounded(value):
    return max(0, min(LIMIT, int(value)))


def milliseconds(start):
    return bounded(round((monotonic() - start) * 1000))


class Record:
    def __init__(self, owner):
        if owner not in {'service', 'control-client', 'runtime'}:
            raise ValueError('constant observation owner required')
        self.owner = owner
        self.sequence = self.dropped = 0
        self.recent = deque(maxlen=RECENT)
        self.active = {}
        self.totals = {}
        self.window_started = monotonic()

    def expire(self):
        if monotonic() - self.window_started < WINDOW_SECONDS:
            return
        self.dropped = bounded(self.dropped + len(self.active))
        self.active.clear()
        self.recent.clear()
        self.totals.clear()
        self.window_started = monotonic()

    def begin(self, label):
        self.expire()
        if label not in LABELS:
            raise ValueError('constant observation label required')
        if len(self.active) >= ACTIVE or self.sequence == LIMIT:
            self.dropped = bounded(self.dropped + 1)
            return 0
        self.sequence += 1
        self.active[self.sequence] = (label, monotonic(), _parent.get())
        return self.sequence

    def end(self, number, state):
        self.expire()
        if state not in {'succeeded', 'failed', 'cancelled'}:
            raise ValueError('constant observation state required')
        entry = self.active.pop(number, None)
        if entry is None:
            return
        label, start, parent = entry
        elapsed = milliseconds(start)
        row = self.totals.setdefault(label, dict(count=0, failed=0, cancelled=0, total_ms=0, max_ms=0))
        row['count'] = bounded(row['count'] + 1)
        row['failed'] = bounded(row['failed'] + (state == 'failed'))
        row['cancelled'] = bounded(row['cancelled'] + (state == 'cancelled'))
        row['total_ms'] = bounded(row['total_ms'] + elapsed)
        row['max_ms'] = max(row['max_ms'], elapsed)
        self.recent.append(dict(sequence=number, parent=parent, phase=label, state=state, elapsed_ms=elapsed))

    def snapshot(self):
        self.expire()
        return dict(owner=self.owner, sequence=self.sequence, dropped=self.dropped,
                    window_ms=WINDOW_SECONDS*1000, window_elapsed_ms=milliseconds(self.window_started),
                    totals={key: dict(row) for key, row in self.totals.items()},
                    recent=list(self.recent), active=[dict(sequence=number, parent=parent,
                        phase=label, state='inflight', elapsed_ms=milliseconds(start))
                        for number, (label, start, parent) in self.active.items()])


@contextmanager
def owning(owner):
    record = Record(owner)
    token = _record.set(record)
    parent = _parent.set(0)
    try:
        yield record
    finally:
        _parent.reset(parent)
        _record.reset(token)


@contextmanager
def span(label):
    record = _record.get()
    if record is None:
        yield 0
        return
    number = record.begin(label)
    token = _parent.set(number)
    state = 'succeeded'
    try:
        yield number
    except BaseException as exc:
        state = 'cancelled' if isinstance(exc, asyncio.CancelledError) else 'failed'
        raise
    finally:
        _parent.reset(token)
        record.end(number, state)


def observe(label):
    def decorate(function):
        @wraps(function)
        def call(*args, **kwargs):
            with span(label):
                return function(*args, **kwargs)
        return call
    return decorate


def snapshot():
    record = _record.get()
    return record.snapshot() if record else None


def count(label, value):
    record = _record.get()
    if record is None:
        return
    record.expire()
    if label not in {'source-files', 'retained-events', 'retained-outboxes'}:
        raise ValueError('constant observation label required')
    row = record.totals.setdefault(label, dict(count=0, items=0, last_items=0))
    row['count'] = bounded(row['count'] + 1)
    row['items'] = bounded(row['items'] + value)
    row['last_items'] = bounded(value)
