"""Caller-owned dialogue over an explicitly supplied opaque endpoint.

This port does not resolve selectors, start a CLI, acquire source, or attach to
saved sessions. Its endpoint must supply those separately admitted capabilities.
The material channel mediates its own API only; it is not an in-process sandbox
for endpoint code. See opaque-dialogue.md for the remaining integration contract.

Declared roles: orchestration, validator, accessor, mapper.
"""
from dataclasses import dataclass
import asyncio
import hashlib
import math
import time
from types import MappingProxyType
from uuid import uuid4


class Refusal(ValueError):
    pass


def sha256(body):
    return hashlib.sha256(body).hexdigest()


@dataclass(frozen=True)
class Ownership:
    """Caller association, never an account or underlying-model attestation."""
    context: str
    selector: str
    profile: str
    collector: str
    created: float
    expires: float


@dataclass(frozen=True)
class Reply:
    thread: str
    answer: str
    complete: bool


class MaterialChannel:
    """Only already-admitted bytes; requests never name filesystem operands.

    Parent code/interpreter are trusted. Unknown tools, including path reads,
    writes, process starts and network requests, have no effect implementation.
    Events record actual API operations, not model assertions or OS telemetry.
    """
    def __init__(self, materials, authorize, *, max_events=4096, chunk_bytes=12000):
        if not isinstance(materials, dict) or not 1 <= len(materials) <= 1024:
            raise Refusal('bounded positive material mapping required')
        if any(type(k) is not str or not k or type(v) is not bytes for k, v in materials.items()):
            raise Refusal('material labels and immutable bytes required')
        if sum(map(len, materials.values())) > 32 * 1024 * 1024:
            raise Refusal('selected material exceeds admission')
        if type(max_events) is not int or not 1 <= max_events <= 65536:
            raise Refusal('bounded operation evidence required')
        if type(chunk_bytes) is not int or not 1 <= chunk_bytes <= 12000:
            raise Refusal('bounded read response required')
        self._items = MappingProxyType({f'm{i:04d}': (k, v) for i, (k, v) in enumerate(materials.items())})
        self._authorize, self._maximum, self._chunk = authorize, max_events, chunk_bytes
        self._events = []
        self._closed = False

    @property
    def events(self):
        return tuple(MappingProxyType(dict(row)) for row in self._events)

    def close(self):
        self._closed = True

    def _admit(self):
        if self._closed or len(self._events) >= self._maximum:
            raise Refusal('channel closed or complete operation-evidence budget exhausted')
        self._authorize()

    def _record(self, outcome, **detail):
        self._events.append(dict(sequence=len(self._events), outcome=outcome, **detail))

    def _denied(self):
        # Do not retain arbitrary denied arguments, target paths or diagnostics.
        self._record('denied')
        raise Refusal('operation outside admitted material-read API')

    def manifest(self):
        self._admit()
        result = tuple(dict(item=k, label=v[0], bytes=len(v[1]), sha256=sha256(v[1]))
                       for k, v in self._items.items())
        self._record('manifest', items=len(result))
        return result

    def request(self, operation):
        self._admit()
        if type(operation) is not dict or set(operation) != {'op', 'item', 'offset', 'limit'}:
            return self._denied()
        if operation['op'] != 'read' or type(operation['item']) is not str:
            return self._denied()
        if operation['item'] not in self._items:
            return self._denied()
        return self._read(operation)

    def _read(self, operation):
        start, limit = operation['offset'], operation['limit']
        body = self._items[operation['item']][1]
        if type(start) is not int or type(limit) is not int:
            return self._denied()
        if not 0 <= start <= len(body) or not 1 <= limit <= self._chunk:
            return self._denied()
        result = body[start:start + limit]
        self._record('read', item=operation['item'], offset=start, bytes=len(result), sha256=sha256(result))
        return result


class Dialogue:
    """One owned endpoint handle, no reopen/replay/migration after failure.

    endpoint.open(ownership) creates one handle under caller-supplied admission.
    endpoint.exchange(handle, ownership, thread, text, channel) returns Reply.
    endpoint.close(handle, ownership) performs its own real collection duties.
    A close receipt is retained as endpoint testimony, not fabricated process END.
    """
    def __init__(self, endpoint, profile, collector, authority, admission, *, lifetime=7200,
                 clock=time.monotonic, answer_bytes=1024 * 1024):
        if profile not in {'.codex', '.codex2', '.codex3', '.codex4', '.codex5'}:
            raise Refusal('supported original account association required')
        if type(collector) is not str or not collector:
            raise Refusal('original collector required')
        if type(lifetime) is not int or not 1 <= lifetime <= 7200:
            raise Refusal('whole original lifetime must be within 7200 seconds')
        if type(answer_bytes) is not int or not 1 <= answer_bytes <= 32 * 1024 * 1024:
            raise Refusal('bounded complete answer required')
        created = clock()
        if not math.isfinite(created):
            raise Refusal('finite monotonic origin required')
        self._ownership = Ownership(str(uuid4()), 'gpt-xhigh', profile, collector, created, created + lifetime)
        self._endpoint, self._authority, self._admission, self._clock = endpoint, authority, admission, clock
        self._answer_bytes = answer_bytes
        self._state, self._handle, self._thread, self._turns = 'new', None, None, 0
        self._active, self._channels, self._close_receipt = False, [], None
        self._creation, self._returns = 'not-attempted', []
        self._material_bytes, self._input_bytes = 0, 0
        self._retained_bytes = 0

    @property
    def ownership(self):
        return self._ownership

    @property
    def status(self):
        return dict(state=self._state, thread=self._thread, turns=self._turns,
                    active=self._active, close_receipt=self._close_receipt, creation=self._creation)

    def _authorize(self):
        now = self._clock()
        if not math.isfinite(now) or now < self._ownership.created or now >= self._ownership.expires:
            raise Refusal('original lifetime elapsed or clock origin changed')
        self._authority(self._ownership)

    async def _open(self):
        async with self._admission(self._ownership.profile):
            self._authorize()
            await self._create()
        self._authorize()

    async def _create(self):
        self._creation = 'attempted'
        # Retain a returned handle even if admission exit raises.
        self._handle = await self._within_lifetime(self._endpoint.open(self._ownership))
        if self._handle is None:
            raise Refusal('endpoint returned no owned handle')
        self._creation = 'handle-returned'

    async def _within_lifetime(self, operation):
        return await asyncio.wait_for(operation, max(0, self._ownership.expires - self._clock()))

    def _input(self, collector, text):
        if collector != self._ownership.collector or self._active or self._state not in {'new', 'live'}:
            raise Refusal('original unavailable or collector changed; no replacement')
        if type(text) is not str or not text or len(text.encode()) > 32 * 1024 * 1024:
            raise Refusal('bounded nonempty input required')
        self._authorize()

    def _reply(self, reply):
        if type(reply) is not Reply or type(reply.thread) is not str or not 1 <= len(reply.thread) <= 256:
            raise Refusal('explicit original thread required')
        if self._thread is not None and reply.thread != self._thread:
            raise Refusal('endpoint changed original thread')
        if type(reply.complete) is not bool or not reply.complete:
            raise Refusal('endpoint returned incomplete work; preserve partial evidence')
        if type(reply.answer) is not str or not reply.answer or len(reply.answer.encode()) > self._answer_bytes:
            raise Refusal('complete answer unavailable within admitted bound')
        return reply

    async def turn(self, collector, text, materials):
        self._input(collector, text)
        channel = self._channel(materials, text)
        self._active = True
        self._channels.append(channel)
        try:
            return await self._exchange(text, channel)
        except BaseException:
            self._state = 'interrupted'
            raise
        finally:
            channel.close()
            self._active = False

    def _channel(self, materials, text):
        channel = MaterialChannel(materials, self._authorize)
        size = sum(map(len, materials.values()))
        if (len(self._channels) >= 128 or self._material_bytes + size > 32 * 1024 * 1024
                or self._input_bytes + len(text.encode()) > 32 * 1024 * 1024):
            raise Refusal('whole-dialogue input/material retention budget exhausted')
        self._material_bytes += size
        self._input_bytes += len(text.encode())
        return channel

    async def _exchange(self, text, channel):
        if self._state == 'new':
            await self._open()
        self._authorize()
        reply = await self._within_lifetime(
            self._endpoint.exchange(self._handle, self._ownership, self._thread, text, channel))
        # Retain bounded typed partial answers before validation; transport still
        # owns raw/malformed/oversized returns and their complete captures.
        self._retain(reply)
        self._authorize()
        reply = self._reply(reply)
        self._thread, self._state, self._turns = reply.thread, 'live', self._turns + 1
        return reply

    def _retain(self, reply):
        if type(reply) is Reply and type(reply.answer) is str and len(reply.answer.encode()) <= self._answer_bytes:
            self._retain_bounded(reply)

    def _retain_bounded(self, reply):
        size = len(reply.answer.encode())
        if self._retained_bytes + size > 32 * 1024 * 1024:
            raise Refusal('whole answer retention exceeds bound; original endpoint capture remains owed')
        self._returns.append(reply)
        self._retained_bytes += size

    @property
    def returns(self):
        return tuple(self._returns)

    @property
    def operations(self):
        return tuple(channel.events for channel in self._channels)

    async def close(self, collector):
        if collector != self._ownership.collector or self._active:
            raise Refusal('close requires idle original collector')
        if self._state == 'closed':
            return self._close_receipt
        self._state = 'closing'
        self._active = True
        try:
            self._close_receipt = await self._close_endpoint()
        finally:
            self._active = False
        self._state = 'closed'
        return self._close_receipt

    async def _close_endpoint(self):
        if self._handle is None:
            return {'endpoint_handle_returned': False, 'creation': self._creation,
                    'creation_effects': 'not-attempted' if self._creation == 'not-attempted' else 'unknown'}
        return await self._endpoint.close(self._handle, self._ownership)
