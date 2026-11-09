"""Compose the selected protected opaque review with its current caller.

The public policy binds executable/dependencies and resource allowance. All
operating rights, branch association and original collection remain with their
actual owners. Nothing here adopts a policy or supplies native proof.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
from types import ModuleType

from .contracts import Refusal, digest
from .custody import read_file
from .resource_scopes import root

VERSION = 'protected-continuing-v1'
PROGRAM_VERSION = 'protected-continuing-v2'
MODULES = ('profile_lease', 'execution_pool', 'dispatch', 'review_context',
           'opaque_dialogue', 'continuing_review')
FIELDS = {'version', 'source_files', 'pool_control', 'runtime_reads',
          'executable_sha256', 'capture_max', 'allowance_bytes', 'allowance_entries'}


def declaration(policy):
    value = policy.get('continuing')
    if not isinstance(value, dict):
        raise Refusal('selected protected continuing composition required before execution')
    fields = FIELDS | {'executable_identity'} if value.get('version') == PROGRAM_VERSION else FIELDS
    if set(value) != fields or value['version'] not in {VERSION, PROGRAM_VERSION}:
        raise Refusal('selected protected continuing composition required before execution')
    if (not isinstance(value['source_files'], dict)
            or set(value['source_files']) != {name+'.py' for name in MODULES}):
        raise Refusal('complete exact continuing source dependency pins required')
    if (not isinstance(value['runtime_reads'], list) or not value['runtime_reads']
            or len(value['runtime_reads']) > 256 or len(set(value['runtime_reads'])) != len(value['runtime_reads'])):
        raise Refusal('finite positive public runtime read dependencies required')
    if (type(value['capture_max']) is not int or not 65536 <= value['capture_max'] <= 32*1024**2
            or type(value['allowance_bytes']) is not int
            or not 2*value['capture_max']+36*1024**2 <= value['allowance_bytes'] <= 1024**3
            or type(value['allowance_entries']) is not int or not 1100 <= value['allowance_entries'] <= 32000):
        raise Refusal('full finite context output/capture allowance required')
    from .reviews import sha
    for expected in [*value['source_files'].values(), value['executable_sha256']]:
        if not isinstance(expected, str) or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
            raise Refusal('exact SHA256 dependency identity required')
    if value['version'] == PROGRAM_VERSION:
        program = value['executable_identity']
        if (not isinstance(program, dict) or set(program) != {'bytes', 'max_bytes'}
                or type(program['bytes']) is not int or type(program['max_bytes']) is not int
                or not 0 < program['bytes'] <= program['max_bytes'] <= 1024**3):
            raise Refusal('explicit finite complete executable identity allowance required')
    control = value['pool_control']
    if not isinstance(control, dict) or set(control) != {'routes', 'static_sha256'}:
        raise Refusal('public static pool control binding required')
    return value


def admitted_path(runtime, attempt, value, *, source_read=False):
    """Lexical exclusions and current typed rights precede target acquisition."""
    row = runtime.attempt(attempt)
    job = runtime.job(row['job'])
    task = runtime.config['tasks'][job['task']]
    if task.get('require_package_scope'):
        from .contracts import scoped_task
        task = scoped_task(job['task'], task, runtime.one(
            'SELECT * FROM admissions WHERE package=?', (job.get('package'),)))
    exclusions = [*runtime.config.get('artifact_exclusions', []), *task.get('scope_exclusions', [])]
    path = root(value, exclusions, metadata=False)
    if source_read and 'read-source' not in task['effect_authority']['operations']:
        raise Refusal('continuing dependencies require current typed source-read rights')
    reads = task['effect_authority']['read_roots']
    if not any(path.is_relative_to(Path(p)) for p in reads):
        raise Refusal('continuing dependency outside current delegated read authority')
    return root(value, exclusions)


def source_bodies(runtime, attempt, policy):
    value = declaration(policy)
    directory = Path(__file__).parents[2] / 'direct-child'
    # Validate every operand first, before any module is imported or measured.
    paths = {name: admitted_path(runtime, attempt, str(directory/(name+'.py'))) for name in MODULES}
    from .reviews import sha
    bodies = {name: read_file(path, 256*1024)[0] for name, path in paths.items()}
    if any(sha(body) != value['source_files'][name+'.py'] for name, body in bodies.items()):
        raise Refusal('selected continuing source dependency changed; no substitute')
    if sha(bodies['review_context']) != policy['launcher_sha256']:
        raise Refusal('launcher and continuing source selection disagree')
    return paths, bodies


def modules(paths, bodies):
    """Load the admitted bytes in one source-specific namespace, no path search."""
    name = '_owned_review_' + digest({k: hashlib.sha256(v).hexdigest() for k,v in bodies.items()})
    if name in sys.modules:
        return sys.modules[name]
    package = ModuleType(name)
    package.__path__ = []
    sys.modules[name] = package
    try:
        for leaf in MODULES:
            module = ModuleType(name+'.'+leaf)
            module.__file__, module.__package__ = str(paths[leaf]), name
            sys.modules[module.__name__] = module
            setattr(package, leaf, module)
            exec(compile(bodies[leaf], str(paths[leaf]), 'exec'), module.__dict__)
    except BaseException:
        # Keep a failed namespace unavailable; no partially loaded replacement.
        package.failed = True
        raise
    package.failed = False
    return package


def dependencies(runtime, attempt, policy, package):
    value = declaration(policy)
    if getattr(package, 'failed', True):
        raise Refusal('original source namespace failed; no partial reuse')
    executable = admitted_path(runtime, attempt, policy['executable'],
                               source_read=value['version'] == PROGRAM_VERSION)
    routes = admitted_path(runtime, attempt, value['pool_control']['routes'])
    if str(routes) != runtime.config.get('execution_pool_routes'):
        raise Refusal('execution and admission must share the selected public control')
    for path in value['runtime_reads']:
        admitted_path(runtime, attempt, path)
    from .reviews import sha
    if value['version'] == PROGRAM_VERSION:
        from .public_program import identity
        program = value['executable_identity']
        observed = identity(executable, program['bytes'], program['max_bytes'],
                            runtime.config.get('artifact_exclusions', []))
        actual = observed['sha256']
    else:
        actual = sha(read_file(executable, 32*1024**2)[0])
    if actual != value['executable_sha256']:
        raise Refusal('selected public executable changed')
    raw = read_file(routes, 256*1024)[0]
    pool = package.execution_pool.Pool(routes)
    pool.assert_control(raw, value['pool_control'])
    return routes


class SelectedOwner:
    """The same in-memory collector owns qualification, review and finalization."""
    def __init__(self, native, runtime, attempt, policy, context, package, routes):
        self.native, self.runtime, self.policy = native, runtime, policy
        self.context, self.package, self.attempt = dict(context), package, attempt
        self.task = runtime.job(runtime.attempt(attempt)['job'])['task']
        self.selection = digest(runtime.processing.current()[1]['service']['reviews'][self.task])
        self.capability = runtime.processing.key
        value = declaration(policy)
        if not 1 <= runtime.config['limits']['max_result_bytes'] <= value['capture_max']:
            raise Refusal('complete configured answer must fit selected capture allowance')
        self.root = Path(context['handle'])
        self.capacity(self.root.parent)
        execution = package.dispatch.open_opaque_execution(routes, 'gpt-xhigh', context['profile'])
        protection = package.continuing_review.SandboxProtection(
            self.root, policy['executable'], value['runtime_reads'], self.capacity)
        self.endpoint = package.continuing_review.ExecEndpoint(
            self.root, policy['executable'], native.originals.scope(), runtime.execution_pool.admission,
            self.authorize, protection, self.capacity, None, execution=execution)
        self.endpoint.clock = runtime.clock
        self.endpoint.maximum = runtime.config['limits']['max_result_bytes']
        self.endpoint.capture_max = value['capture_max']
        self.endpoint.shutdown = runtime.config['deadlines']['shutdown']
        self.review = package.continuing_review.ContinuingReview(
            self.endpoint, 'gpt-xhigh', context['profile'], runtime.controller, self.authorize,
            lifetime=policy['deadline'], clock=runtime.clock, origin=context['created'])
        self.bind(attempt)

    def capacity(self, parent):
        parent = root(str(parent), self.runtime.config.get('artifact_exclusions', []))
        if not (parent.is_relative_to(self.runtime.home)
                or parent.is_relative_to(self.runtime.artifact_root(self.attempt).parent)):
            raise Refusal('continuing output outside original runtime custody')
        value = declaration(self.policy)
        self.runtime.budget(None, value['allowance_bytes'])
        self.runtime.admit_artifact_write(self.attempt, value['allowance_bytes'], value['allowance_entries'],
            journal_incoming=value['allowance_bytes'] if parent.is_relative_to(self.runtime.home) else 0)
        fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            status = os.fstatvfs(fd)
        finally:
            os.close(fd)
        if (status.f_bavail*status.f_frsize-value['allowance_bytes'] < 100*1024**3
                or status.f_favail-value['allowance_entries'] < 1000000):
            raise Refusal('full continuing allowance would breach OS headroom')

    def authorize(self, ownership):
        runtime = self.runtime
        runtime.authorize_launch(self.attempt)
        if (ownership.profile != self.context['profile'] or ownership.collector != runtime.controller
                or ownership.created != self.context['created']
                or ownership.expires != self.context['created']+self.policy['deadline']
                or runtime.processing.key != self.capability
                or digest(runtime.processing.current()[1]['service']['reviews'][self.task]) != self.selection):
            raise Refusal('original continuing owner/current selection changed')
        paths, bodies = source_bodies(runtime, self.attempt, self.policy)
        dependencies(runtime, self.attempt, self.policy, self.package)

    def bind(self, attempt):
        self.attempt = attempt
        # Capture the originating attempt in each publisher. Pending finalizers
        # retain this callback even when a later attempt is bound.
        self.endpoint.publish = lambda observation: self.runtime.record_original_end(attempt, observation)
        self.endpoint.started = lambda: self.started(attempt)

    def started(self, attempt):
        if self.runtime.attempt(attempt)['begin'] is None:
            self.runtime.begin(attempt, {'process_handle': 'owned-asyncio-subprocess',
                'original_collector': self.runtime.controller,
                'identity_scope': 'protected opaque CLI; not native-root END'})

    def same(self, context, *, closing=False):
        keys = ('handle', 'profile', 'collector', 'created', 'capability')
        if any(context[k] != self.context[k] for k in keys):
            raise Refusal('original context/account/collector/creation unavailable; no transfer')
        if (self.endpoint.context and (not closing or context['run'] is not None)
                and self.endpoint.context.thread != context['run']):
            raise Refusal('original observed review thread changed')

    def independence(self):
        from .branches import job_branch
        branch = job_branch(self.runtime, self.runtime.job(self.runtime.attempt(self.attempt)['job']))
        thread = self.endpoint.context.thread
        if branch and (thread == branch['root'] or self.runtime.one(
                "SELECT address FROM branch_contexts WHERE branch=? AND kind='builder' AND address=?",
                (branch['id'], thread))):
            raise Refusal('qualified reviewer must remain separate from branch Root and builders')

    async def turn(self, directory, text, items):
        self.independence()
        root(str(directory), self.runtime.config.get("artifact_exclusions", []))
        self.package.review_context.make_directory(directory.parent, self.capacity)
        self.endpoint.directory = directory
        reply = await self.review.turn(text, dict(items))
        receipt = self.endpoint.receipts[-1]
        receipt['run'] = receipt['thread']
        receipt['protection'] = dict(version=VERSION, qualification_input=0,
            persisted=True, listener_finalized=True, native_owner_execution=False,
            qualification=self.endpoint.receipts[0],
            acting_proof=self.review.proof, local_controls=list(self.endpoint.protection.proofs))
        return receipt['actual_END'], receipt, reply.answer

    async def close(self):
        return await self.review.close()


async def call(native, runtime, attempt, policy, context, directory, text, opening=False, close=False):
    owner = native.public_contexts.get(context['handle'])
    if owner is not None:
        await owner.endpoint.originals.collect_pending(runtime.config['deadlines']['shutdown'])
    if close:
        if owner is None:
            raise Refusal('original protected owner unavailable; no store recovery')
        owner.same(context, closing=True)
        receipt = await owner.close()
        observed = owner.endpoint.context.thread if owner.endpoint.context else None
        return None, dict(receipt, run=context['run'], observed_thread=observed), None
    runtime.authorize_launch(attempt)
    from .opaque_review import binding, snapshot
    binding(runtime.config['tasks'][runtime.job(runtime.attempt(attempt)['job'])['task']])
    paths, bodies = source_bodies(runtime, attempt, policy)
    package = modules(paths, bodies)
    routes = dependencies(runtime, attempt, policy, package)
    if opening:
        if owner is not None:
            raise Refusal('protected context already created; no replay')
        owner = SelectedOwner(native, runtime, attempt, policy, context, package, routes)
        native.public_contexts[context['handle']] = owner
    else:
        if owner is None:
            raise Refusal('original protected owner unavailable; no new context')
        owner.same(context)
        owner.bind(attempt)
    with runtime.tx():
        runtime.db.execute("UPDATE review_calls SET state='launch-intent' WHERE attempt=?", (attempt,))
    acquired = json.loads(runtime.one('SELECT packet FROM review_calls WHERE attempt=?', (attempt,))['packet'])
    # Qualification receives only owned canaries; source bytes are delivered
    # later through the admitted immutable channel on that original thread.
    if opening:
        await owner.review.qualify()
        owner.independence()
    items = snapshot(policy, acquired)
    return await owner.turn(directory, text, items)

