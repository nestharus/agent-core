"""Opt-in, finite, identity-only hints for the existing guarded service intake.

No subscription table, board migration, native watch, membership change or new
receiver is installed. Kernel bindings are exclusive per exact managed recipient
and board inode; their lifetime belongs to this original service incarnation.
"""
import asyncio
import math
import socket

from .board import module_at
from .contracts import Refusal


def validate(runtime, selection, *, selecting=True):
    policy = selection.get('service', {}).get('wake')
    if policy is None:
        return None
    admission = selection['service'].get('admission')
    if (not isinstance(policy, dict) or set(policy) != {'protocol', 'roles', 'until'}
            or policy['protocol'] != 'managed-hint-v1'
            or not isinstance(policy['roles'], list) or not policy['roles']
            or any(not isinstance(r, str) for r in policy['roles'])
            or len(set(policy['roles'])) != len(policy['roles'])
            or set(policy['roles']) - set(selection['basis']['roles'])
            or set(policy['roles']) - set(runtime.config['roles'])
            or not selection['future_intake'] or not isinstance(admission, dict) or 'until' not in admission
            or type(policy['until']) not in {int, float} or not math.isfinite(policy['until'])
            or policy['until'] != admission['until']
            or (selecting and not runtime.clock() < policy['until'] <= runtime.clock() + 3600)):
        raise Refusal('wake needs exact managed roles and the selected finite admission deadline')
    return policy


class ServiceWake:
    def __init__(self, runtime, boards, dispatcher):
        self.runtime, self.boards, self.dispatcher = runtime, boards, dispatcher
        self.loop = asyncio.get_running_loop()
        self.receivers = []
        self.expiry = None
        self.state = 'disabled'
        self.hints = 0
        self.until = None
        self.roles = []

    def start(self):
        _, selection = self.runtime.processing.current()
        policy = validate(self.runtime, selection, selecting=False)
        if policy is None:
            return
        self.until, self.roles = policy['until'], list(policy['roles'])
        if self.runtime.clock() >= self.until:
            self.state = 'expired'
            return
        helper = module_at(self.runtime.config['board_library'], 'active_listener')
        if getattr(helper, 'MANAGED_HINT_PROTOCOL', None) != 1:
            raise Refusal('selected board helper lacks managed-hint-v1; deploy the compatible producer/consumer closure')
        helper._linux()
        try:
            # Bind ALL selected endpoints before the dispatcher's first scan.
            for role in self.roles:
                board = self.boards[role]
                board.verify_authority(self.runtime)
                with board.opened() as conn:
                    member = conn.execute('SELECT route FROM sessions WHERE session=?',
                                          (board.selected['owner'],)).fetchone()
                    if not member or member['route'] != 'managed':
                        raise Refusal('wake cannot acquire a native/queue recipient lane')
                    identity = helper._db_identity(conn)
                    receiver = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                    self.receivers.append((receiver, board, identity, helper))
                    receiver.setblocking(False)
                    try:
                        receiver.bind(helper.managed_address(board.selected['owner'], identity))
                    except OSError as exc:
                        raise Refusal('managed service hint receiver conflict; no takeover or unlink') from exc
                    if helper._db_identity(conn) != identity:
                        raise Refusal('board identity changed while binding managed wake')
                self.loop.add_reader(receiver.fileno(), self._ready, receiver, identity, helper)
            self.state = 'bound'
            self.expiry = self.loop.call_later(max(0, self.until - self.runtime.clock()),
                                               self.close, 'expired')
        except BaseException:
            self.close('refused')
            raise

    def _ready(self, receiver, identity, helper):
        # Bounded draining coalesces traffic and yields to the guarded dispatcher.
        # Even an authentic hint supplies no role, payload or execution authority.
        for _ in range(32):
            try:
                packet = receiver.recv(256)
            except BlockingIOError:
                break
            except OSError:
                self.close('receiver-error')
                self.dispatcher.wakeup.set()
                return
            if packet == helper._packet(identity):
                self.hints += 1
                self.dispatcher.wakeup.set()

    def check(self):
        if self.state != 'bound':
            return
        try:
            _, selection = self.runtime.processing.current()
            policy = validate(self.runtime, selection, selecting=False)
            if (not policy or policy['roles'] != self.roles or policy['until'] != self.until
                    or self.runtime.clock() >= self.until):
                raise Refusal('selected wake expired or changed; original duties retained')
            for _, board, identity, helper in self.receivers:
                board.verify_authority(self.runtime)
                with board.opened() as conn:
                    member = conn.execute('SELECT route FROM sessions WHERE session=?',
                                          (board.selected['owner'],)).fetchone()
                    if not member or member['route'] != 'managed' or helper._db_identity(conn) != identity:
                        raise Refusal('managed wake board/recipient binding changed')
        except Exception:
            self.close('authority-held')
            raise

    def close(self, state='closed'):
        if self.expiry is not None:
            self.expiry.cancel()
            self.expiry = None
        for receiver, *_ in self.receivers:
            self.loop.remove_reader(receiver.fileno())
            receiver.close()  # Abstract endpoint disappears with this exact handle.
        self.receivers.clear()
        self.state = state

    def status(self):
        return {'protocol': 'managed-hint-v1', 'state': self.state, 'roles': self.roles,
                'until': self.until, 'observed_hints': self.hints,
                'meaning': 'advisory software wake only; no receipt, pickup, processing or semantic-response proof'}
