"""Invocation-owned binding to admitted immutable runtime source; no executable provider CLI.

The invoking owner supplies authenticated CURRENT scope, not a role grant or a
UUID-as-proof. Importing this module creates no context, control or allocation.
Only an explicit Question.create/run by that owner can perform those effects.
"""
import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
import hashlib
import importlib.abc
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import sys
import time
from types import ModuleType
from uuid import uuid4

COMMIT = '82de20aa281af40f25e0186babde1db19bebd8e7'
TREE = '5e0858014e293727470a7334f11f10d9391826f6'
PINSET = '549689839c32191eb51a7157ac40b2e2c6f2021700e6eed2b0cc3b02783b22aa'
DIRECT = ('profile_lease', 'execution_pool', 'fast_tier', 'dispatch',
          'review_context', 'opaque_dialogue', 'continuing_review')
PROFILES = ('.codex2', '.codex3', '.codex4', '.codex5')
MIB = 1024**2
CONTROL_EFFECTS = ('allowed-read-canary', 'owned-outside-read-attempt',
                   'owned-material-write-attempt', 'owned-loopback-connect-attempt')


class Refusal(ValueError):
    pass


def digest(body):
    return hashlib.sha256(body).hexdigest()


def authenticate_invoker(owner):
    """Read the CURRENT invocation only; never set IDs or inspect a store.

    This is a finite host-environment association, not cryptographic provider
    identity. A missing identity refuses; there is no CLI/default-role fallback.
    """
    if not owner or os.environ.get('CODEX_THREAD_ID') != owner:
        raise Refusal('actual invoking caller differs from scoped owner')


def positive(path, exclusions=(), *, public_pool_parent=False):
    """Lexical admission before any metadata; never seek excluded aliases."""
    path = Path(path)
    if not path.is_absolute() or path.anchor != '/' or '..' in path.parts:
        raise Refusal('absolute lexical operand required')
    if any(path == Path(p) or path.is_relative_to(Path(p)) for p in exclusions):
        raise Refusal('held operand excluded before acquisition')
    private = {'.ssh', '.aws', '.config'} | (set() if public_pool_parent else {'.local'})
    if (set(path.parts) & private
            or any(p.startswith(('.codex', '.claude')) for p in path.parts)):
        raise Refusal('private namespace excluded before acquisition')
    return path


def directory(path):
    """Anchor every component; O_NOFOLLOW on only the leaf is insufficient."""
    path = Path(path)
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def read(path, maximum, exclusions=(), *, charge=lambda amount: None):
    path = positive(path, exclusions)
    parent = directory(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb', buffering=0) as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
                raise Refusal('finite regular public input required')
            # Bound this acquisition to the admitted descriptor extent, not
            # a growing file. Charge before reading, including failed reads.
            charge(before.st_size + 1)
            body = stream.read(before.st_size + 1)
            after = os.fstat(stream.fileno())
            current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            stable = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mode,
                                s.st_mtime_ns, s.st_ctime_ns, s.st_nlink)
            if len(body) > maximum or stable(before) != stable(after) or stable(after) != stable(current):
                raise Refusal('public input changed during acquisition')
            return body
    finally:
        os.close(parent)


def scope_reader(path, owner, exclusions):
    """Current owner-controlled nonsecret scope, explicitly issued by caller.

    No file is created here. The genuine caller alone supplies/maintains it;
    its existence does not issue permission. Every check rereads current bytes.
    """
    path = positive(path, exclusions)
    def current(action):
        authenticate_invoker(owner)
        parent = directory(path.parent)
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(fd, 'rb', buffering=0) as stream:
                info = os.fstat(stream.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                        or info.st_mode & 0o077 or info.st_nlink != 1 or info.st_size > 65536):
                    raise Refusal('exact private-mode caller-owned finite scope required')
                body = stream.read(65537)
                after = os.fstat(stream.fileno())
                if len(body) > 65536 or (info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
                        after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                    raise Refusal('current scope changed during read')
        finally:
            os.close(parent)
        return json.loads(body)
    return current


def footprint(path, exclusions):
    """Only the positively NEW owned question tree; no old/global census."""
    size, entries = 0, 1
    fd = directory(positive(path, exclusions))
    try:
        for name in os.listdir(fd):
            child = positive(Path(path) / name, exclusions)
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                amount, count = footprint(child, exclusions)
                size += amount
                entries += count
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                size += info.st_size
                entries += 1
            else:
                raise Refusal('unknown/linked member in owned custody')
            if entries > 8192 or size > 512 * MIB:
                raise Refusal('whole owned footprint exceeds finite question bound')
        return size, entries
    finally:
        os.close(fd)


class Budget:
    def __init__(self, home, exclusions):
        self.home, self.exclusions = positive(home, exclusions), tuple(exclusions)
        self.created = False
        self.last = None

    def check(self, parent):
        parent = positive(parent, self.exclusions)
        if not (parent.is_relative_to(self.home)
                or not self.created and parent == self.home.parent):
            raise Refusal('write outside positively owned question')
        fd = directory(parent)
        try:
            status = os.fstatvfs(fd)
        finally:
            os.close(fd)
        if (status.f_bavail * status.f_frsize - 512 * MIB < 100 * 1024**3
                or status.f_favail - 8192 < 1000000):
            raise Refusal('whole question allowance would breach OS headroom')
        if self.created:
            size, entries = footprint(self.home, self.exclusions)
            # Largest bound on a single next runtime write, plus entry margin.
            if size + 32 * MIB > 512 * MIB or entries + 16 > 8192:
                raise Refusal('retained and next-write demand does not fit whole allowance')
            context = self.home / 'context'
            try:
                amount, count = footprint(context, self.exclusions)
            except FileNotFoundError:
                amount, count = 0, 0
            if amount + 32 * MIB > 256 * MIB or count + 16 > 4096:
                raise Refusal('context preparation/capture envelope exhausted')
        self.last = dict(available_bytes=status.f_bavail * status.f_frsize,
                         available_entries=status.f_favail, charge_bytes=512 * MIB,
                         charge_entries=8192, prior_concurrent='UNKNOWN; not reservation/quota/census')


class Publisher:
    """Durable exclusive receiving; failed names stay reserved and conserved."""
    def __init__(self, home, capacity, custody):
        self.home, self.capacity, self.custody = Path(home), capacity, custody
        self.attempts = []

    def __call__(self, observation):
        self.custody()
        body = json.dumps(observation, ensure_ascii=False, sort_keys=True).encode()
        if len(body) > 8 * MIB:
            raise Refusal('whole publication exceeds finite receiving bound')
        name = 'publication-%04d.json' % len(self.attempts)
        self.attempts.append(dict(file=name, persisted=False, bytes=len(body), sha256=digest(body)))
        self.capacity(self.home)
        parent = directory(self.home)
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(parent)
        finally:
            os.close(parent)
        self.attempts[-1]['persisted'] = True
        # Returning None follows actual checks and durable receiving.


class PinnedRuntime(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Use admitted runtime bytes and APIs, admitting imports only from the finite pin set."""
    def __init__(self, repo, pins, admit, reader=read):
        if (pins['commit'] != COMMIT or pins['tree'] != TREE
                or digest(json.dumps(pins, sort_keys=True).encode()) != PINSET):
            raise Refusal('runtime must match the published immutable pin set')
        self.repo, self.pins, self.admit = Path(repo), dict(pins['files']), admit
        self.reader = reader
        self.name = '_invocation_runtime_' + digest(json.dumps(pins, sort_keys=True).encode()) + '_' + uuid4().hex
        self.loaded = {}

    def body(self, relative):
        if relative not in self.pins:
            raise Refusal('source outside finite runtime pin selection')
        path = positive(self.repo / relative)
        self.admit('source', [str(path)])
        body = self.reader(path, 1024 * 1024)
        if digest(body) != self.pins[relative]:
            raise Refusal('selected runtime source changed or unpinned import')
        self.loaded[relative] = digest(body)
        return path, body

    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith(self.name + '.'):
            return None
        leaf = fullname[len(self.name) + 1:]
        relative = 'tools/coordinator-runtime/coordinator_runtime/' + leaf.replace('.', '/') + '.py'
        if relative not in self.pins:
            raise Refusal('import outside admitted runtime closure')
        return importlib.util.spec_from_loader(fullname, self, origin=str(self.repo / relative))

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        relative = 'tools/coordinator-runtime/coordinator_runtime/' + module.__name__.split('.')[-1] + '.py'
        path, body = self.body(relative)
        module.__file__ = str(path)
        exec(compile(body, str(path), 'exec'), module.__dict__)

    def load(self):
        if self.name in sys.modules:
            raise Refusal('one admitted runtime namespace per owner process; no replacement')
        package = ModuleType(self.name)
        package.__path__ = []
        sys.modules[self.name] = package
        sys.meta_path.insert(0, self)
        # No package startup discovery or sys.path search. __init__.py is empty
        # in this exact pin, but still admitted and executed explicitly.
        path, body = self.body('tools/coordinator-runtime/coordinator_runtime/__init__.py')
        package.__file__ = str(path)
        exec(compile(body, str(path), 'exec'), package.__dict__)
        def module(leaf):
            return __import__(self.name + '.' + leaf, fromlist=[leaf])
        self.composition = module('review_composition')
        self.appserver = module('appserver')
        self.program = module('public_program')
        self.public_runtime = module('public_runtime')
        paths, bodies = {}, {}
        for leaf in DIRECT:
            paths[leaf], bodies[leaf] = self.body('tools/direct-child/' + leaf + '.py')
        # Adapter import is inert. Inject the Pool compiled from these exact
        # admitted direct bytes at construction; never reopen via SourceFileLoader.
        self.pool_module = module('execution_pool')
        self.direct = self.composition.modules(paths, bodies)
        if self.direct.failed:
            raise Refusal('original frozen source import failed')
        return self


@dataclass(frozen=True)
class Material:
    label: str
    path: str
    bytes: int
    sha256: str


class Question:
    """Small caller contribution. Current authority and identity are external.

    current(action) returns the actual owner's current positive scope. The real
    owner supplies authenticate(), which CHECKS that owner and may return None.
    The actual invocation ID is also checked directly, without an override.
    Neither callable is an authority minted by this module. See README for the
    exact scope and the remaining actual-caller bindings.
    """
    def __init__(self, *, owner, authenticate, current, home, runtime, pins,
                 caller_pins, program, helper, runtime_reads, pool_control,
                 fast_control, exclusions, io_budget, clock=time.monotonic):
        self.owner, self.authenticate, self.current = owner, authenticate, current
        self.home, self.exclusions = positive(home, exclusions), tuple(exclusions)
        self.program, self.helper = dict(program), dict(helper)
        self.pool_control, self.fast_control = dict(pool_control), dict(fast_control)
        self.caller_pins = dict(caller_pins)
        if str(Path(__file__)) not in self.caller_pins or not self.exclusions:
            raise Refusal('published caller source pin and all operating exclusions required')
        self.runtime_reads = tuple(runtime_reads)
        expected = {helper['path'], *helper['runtime_directories']}
        if set(runtime_reads) != expected or len(runtime_reads) != len(expected):
            raise Refusal('control0 runtime reads must contain only canonical helper and named OS runtime')
        if type(io_budget) is not int or not 0 < io_budget <= 1024**4:
            raise Refusal('finite total complete-identity read I/O admission required')
        self.io_remaining = io_budget
        self.clock, self.origin = clock, clock()
        if not math.isfinite(self.origin):
            raise Refusal('finite original monotonic creation required')
        self.budget = Budget(self.home, exclusions)
        self.runtime = PinnedRuntime(runtime, pins, self.check, self.acquire)
        self.review = self.endpoint = self.originals = self.publisher = None
        self.started = False
        self.profile = None
        self.materials = ()
        self.answers = []
        self.error = None
        self.questions = None
        self.binding = self.describe_binding()

    def describe_binding(self):
        return json.loads(json.dumps(dict(home=str(self.home), runtime=str(self.runtime.repo),
            runtime_commit=COMMIT, runtime_tree=TREE, pinset=PINSET,
            caller_pins=self.caller_pins, program=self.program, helper=self.helper,
            runtime_reads=self.runtime_reads, pool_control=self.pool_control,
            fast_control=self.fast_control, whole_lifetime=7200)))

    def check(self, action, paths=(), ownership=None):
        authenticate_invoker(self.owner)
        self.authenticate()  # Real owner-sensitive checker; None is conventional.
        scope = self.current(action)
        now = time.time()
        if (scope['owner'] != self.owner or action not in scope['operations']
                or str(self.home) not in scope['write_roots']):
            raise Refusal('actual current owner/action/custody scope mismatch')
        if scope['binding'] != self.binding or self.describe_binding() != self.binding:
            raise Refusal('current actual source/program/helper/control/caller binding changed')
        if scope['control_effects'] != list(CONTROL_EFFECTS):
            raise Refusal('actual nonsecret qualification effects are not currently scoped')
        if self.started and (scope['questions'] != list(self.questions)
                or scope['materials'] != [asdict(m) for m in self.materials]):
            raise Refusal('current question or exact selected material authority changed')
        custody = action in {'collect', 'publish'} and scope.get('custody_allowed') is True
        if not custody and (scope['revoked'] or not now < scope['expires_at']
                            or not 0 <= self.clock() - self.origin < 7200):
            raise Refusal('current processing authority or whole lifetime unavailable')
        for p in paths:
            path = positive(p, self.exclusions)
            if str(path) not in scope['read_files'] and str(path) not in scope['runtime_directories']:
                raise Refusal('actual operand outside current positive read authority')
        if ownership is not None:
            if (ownership.collector != self.owner or ownership.profile != self.profile
                    or ownership.created != self.origin or ownership.expires != self.origin + 7200):
                raise Refusal('original collector/profile/origin/lifetime changed')
            if self.endpoint and self.endpoint.context:
                context = self.endpoint.context
                if (context.collector != self.owner or context.profile != self.profile
                        or context.created != self.origin or context.lifetime != 7200):
                    raise Refusal('actual endpoint association changed')
        return scope

    def capacity(self, parent):
        self.check('collect')
        self.budget.check(parent)

    def charge(self, amount):
        if type(amount) is not int or not 0 <= amount <= self.io_remaining:
            raise Refusal('finite cumulative acquisition I/O exhausted before read')
        self.io_remaining -= amount

    def acquire(self, path, maximum):
        return read(path, maximum, self.exclusions, charge=self.charge)

    def control_read(self, path, maximum):
        self.check('control', [str(path)])
        return self.acquire(path, maximum)

    def fast_enabled(self):
        # Preserve the shared parser/Boolean contract while charging its bounded
        # public acquisition. It never changes the original request snapshot.
        self.check('control', [self.fast_control['path']])
        self.charge(17)
        return self.runtime.direct.fast_tier.enabled(self.fast_control['path'])

    def identities(self):
        operands = [self.program['path'], self.helper['path'], *self.helper['runtime_directories']]
        self.check('dependencies', operands)
        charge = 2 * (self.program['max_bytes'] + self.helper['max_bytes'])
        self.charge(charge)
        actual = self.runtime.program.identity(self.program['path'], self.program['bytes'],
                                               self.program['max_bytes'], self.exclusions)
        if actual['sha256'] != self.program['sha256']:
            raise Refusal('actual selected complete program changed')
        self.runtime.public_runtime.check_helper(self.helper, self.exclusions)

    def authorize(self, ownership, *, complete_identity=True):
        self.check('analysis', ownership=ownership)
        self.budget.check(self.home)
        for relative in self.runtime.loaded.copy():
            self.runtime.body(relative)
        self.check_caller()
        for item in self.materials:
            self.check('material', [item.path])
        self.check('control', [self.pool_control['routes'], self.fast_control['path']])
        raw = self.control_read(self.pool_control['routes'], MIB)
        self.pool.pool.assert_control(raw, self.pool_control)
        # A later global value is validated, never applied to an old context.
        self.fast_enabled()
        if complete_identity:
            self.identities()

    def authorize_material(self, ownership):
        # Immutable bytes move synchronously within the host. Rights, source,
        # controls and lifetime remain current per chunk; complete program/helper
        # identity is checked around export and again immediately before feed.
        self.authorize(ownership, complete_identity=False)

    def probe_helper(self):
        self.check('qualify')
        self.budget.check(self.home)
        self.identities()
        return self.helper['path']

    def create(self):
        """Only the authenticated invoking owner calls this; no provider yet."""
        self.check('prepare')
        if self.budget.created:
            raise Refusal('one positively new question home only')
        self.budget.check(self.home.parent)
        self.check_caller()
        parent = directory(self.home.parent)
        try:
            os.mkdir(self.home.name, 0o700, dir_fd=parent)  # exclusive, no adoption
            os.fsync(parent)
        finally:
            os.close(parent)
        self.budget.created = True
        self.runtime.load()
        self.identities()
        self.check('control', [self.pool_control['routes'], self.fast_control['path']])
        public_pool = self.runtime.direct.execution_pool
        self.pool = self.runtime.pool_module.ExecutionPool(dict(profiles=list(PROFILES),
            execution_pool_routes=self.pool_control['routes'], deadlines={'bind': 30}),
            pool=public_pool.Pool(self.pool_control['routes'], reader=self.control_read, charge=self.charge,
                                  before_write=self.pool_parent_guard),
            pool_module=public_pool, expected_control=self.pool_control)
        self.pool.pool.assert_control(self.control_read(self.pool_control['routes'], MIB), self.pool_control)
        helper_hash = self.runtime.pins['tools/direct-child/fast_tier.py']
        if self.fast_control['helper_sha256'] != helper_hash:
            raise Refusal('actual global control/helper correspondence changed')
        self.force_fast = self.fast_enabled()
        self.check('allocate')
        # Pool mutations use the ACTUAL supported pool; their public state
        # parent is separately authorized/guarded before each allocation/admit.
        self.pool_guard()
        self.reservation = self.pool.pool.allocate(list(PROFILES), blocking=False,
                                                   expected_control=self.pool_control)
        self.profile = self.reservation['profile']
        execution = self.runtime.direct.dispatch.open_opaque_execution(
            self.pool_control['routes'], 'gpt-xhigh', self.profile, force_fast=self.force_fast, config_reader=self.control_read)
        self.originals = self.runtime.appserver.Originals().scope()
        self.publisher = Publisher(self.home, self.capacity, lambda: self.check('publish'))
        protection = self.runtime.direct.continuing_review.SandboxProtection(
            self.home / 'context', self.program['path'], self.runtime_reads,
            self.capacity, probe_helper=self.probe_helper)
        self.endpoint = self.runtime.direct.continuing_review.ExecEndpoint(
            self.home / 'context', self.program['path'], self.originals, self.admission,
            self.authorize, protection, self.capacity, self.publisher, execution=execution)
        self.endpoint.clock = self.clock
        self.endpoint.capture_max = 8 * MIB
        self.review = self.runtime.direct.continuing_review.ContinuingReview(
            self.endpoint, 'gpt-xhigh', self.profile, self.owner, self.authorize,
            lifetime=7200, clock=self.clock, origin=self.origin, material_authority=self.authorize_material)
        self.authorize(self.review.ownership)
        return self

    def check_caller(self):
        for path, expected in self.caller_pins.items():
            self.check('source', [path])
            if digest(self.acquire(path, MIB)) != expected:
                raise Refusal('published caller source changed')

    def pool_guard(self):
        scope = self.check('allocate', [self.pool_control['routes']])
        _, _, counter = self.pool.pool.read()
        # The supported public rotation control may live under .local. Only
        # its EXACT routes-declared, currently authorized counter/lock parent
        # receives this narrow exception; no private store/read root is added.
        self.pool_parent_guard(counter.parent)

    def pool_parent_guard(self, parent):
        # Pool invokes this anew before each lock/counter write, including each
        # retry after awaited busy admission; no earlier placement grant is reused.
        scope = self.check('allocate')
        parent = positive(parent, self.exclusions, public_pool_parent=True)
        if str(parent) not in scope.get('pool_write_parents', []):
            raise Refusal('actual public pool state destination not currently admitted')
        fd = directory(parent)
        try:
            info = os.fstatvfs(fd)
        finally:
            os.close(fd)
        if info.f_bavail * info.f_frsize - 512 * MIB < 100 * 1024**3 or info.f_favail - 8192 < 1000000:
            raise Refusal('actual pool control persistence lacks full question headroom')

    @asynccontextmanager
    async def admission(self, profile):
        self.pool_guard()
        # ExecutionPool supplies the asynchronous bounded wait and actual
        # cooperative fence. Recheck static control after its awaited admission
        # and before Context's spawn; do not substitute a membership snapshot.
        async with self.pool.admission(profile) as witness:
            self.authorize(self.review.ownership)
            yield witness

    def selected(self):
        if not self.review.status['protection_qualified']:
            raise Refusal('no selected source/material before qualified proof')
        if not 1 <= len(self.materials) <= 128 or sum(m.bytes for m in self.materials) > 2 * MIB:
            raise Refusal('finite positive selected snapshot required')
        result = {}
        for item in self.materials:
            self.check('material', [item.path])
            body = self.acquire(item.path, item.bytes)
            if len(body) != item.bytes or digest(body) != item.sha256 or item.label in result:
                raise Refusal('selected source snapshot changed or label duplicated')
            body.decode('utf-8')
            result[item.label] = body
        return result

    def report(self):
        return dict(runtime_commit=COMMIT, runtime_tree=TREE,
            status=self.review.status if self.review else 'not-created',
            owner=self.owner, ownership=asdict(self.review.ownership) if self.review else None,
            force_fast=getattr(self, 'force_fast', None), served_tier='UNOBSERVED',
            source_imports=dict(self.runtime.loaded), answers=list(self.answers),
            protection=self.review.proof if self.review else None,
            turn_receipts=list(self.endpoint.receipts) if self.endpoint else [],
            local_controls=list(self.endpoint.protection.proofs) if self.endpoint else [],
            material=[asdict(m) for m in self.materials], error=self.error,
            pending_originals=list(self.originals.owned) if self.originals else [],
            publications=list(self.publisher.attempts) if self.publisher else [],
            semantic_assessment='OWED to genuine caller; transport answers are not substantive acceptance',
            whole_processing=False, acceptance=False, native_owner_execution=False,
            io_remaining=self.io_remaining, resources=self.budget.last)

    async def run(self, first, continuation, materials):
        if self.started or self.review is None:
            raise Refusal('one run on this original only; create before run')
        self.started = True
        self.materials = tuple(materials)
        self.questions = (first, continuation)
        try:
            self.authorize(self.review.ownership)
            self.check('qualify')
            await self.review.qualify()
            for index, question in enumerate((first, continuation), 1):
                self.authorize(self.review.ownership)
                self.check('qualify')  # actual local controls recur each turn
                reply = await self.review.turn(question, self.selected())
                self.answers.append(dict(input=index, thread=reply.thread, answer=reply.answer,
                                         complete=reply.complete, substantive='UNASSESSED'))
                self.publisher(self.report())
            await self.close()
            self.publisher(self.report())
        except BaseException as exc:
            self.error = type(exc).__name__  # raw diagnostics stay in own captures
            self.publisher(self.report())  # may itself fail; exact owner retained
            raise
        return self.report()

    async def close(self):
        self.check('collect')
        return await self.review.close()
