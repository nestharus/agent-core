"""Prospective file-native Work/Branch/Reviews/QA coordination.

No legacy imports. Only the public pool and fast-control helpers are loaded.
External owners assert identity/evidence inside the same-user cooperative model.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import secrets
import time

from storage import Files, Held, MAX_STATE, MAX_BUDGET, check_capacity, digest, encode, read_regular

# This public helper has no provider/account-store access. Never import the old
# runtime or Board as a compatibility adapter.
_pool_path = Path(__file__).resolve().parents[1] / 'direct-child' / 'execution_pool.py'
_spec = importlib.util.spec_from_file_location('file_runtime_public_pool', _pool_path)
_pool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pool)
_spec = importlib.util.spec_from_file_location('file_runtime_fast_policy', _pool_path.with_name('fast_tier.py'))
_fast = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fast)
ROLES = {'Work', 'Branch', 'Reviews', 'QA'}
PHASES = {'classifier', 'known', 'discovery', 'qa-execute', 'qa-consolidate', 'review'}
ALLOWED_PROFILES = {'.codex2', '.codex3', '.codex4', '.codex5'}
MAX_TEXT = 512  # Encoded JSON bytes, including quotes/escapes; never characters.
MAX_HISTORY = 12
COLLECTIONS = {'attempt': 'attempts', 'event': 'events', 'packet': 'packets', 'effect': 'effects',
               'branch': 'branches', 'review': 'reviews', 'package': 'packages'}


def require(condition, message):
    if not condition:
        raise Held(message)


def text(value):
    require(isinstance(value, str) and value and len(encode(value)) <= MAX_TEXT,
            'nonempty text exceeds 512 encoded JSON bytes; preserve original outside runtime')
    return value


def ident(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', value), 'invalid identifier')
    return value


def secret_hash(value):
    return hashlib.sha256(text(value).encode()).hexdigest()


def token():
    return secrets.token_hex(24)


def create(path, owner, credential, routes):
    """Exclusive new runtime only. Existing/partial initialization is held."""
    ident(owner)
    secret_hash(credential)
    path = Path(path)
    require(path.is_absolute() and path.parent.is_dir(), 'absolute state path with existing parent required')
    check_capacity(path.parent, MAX_STATE + 16384, 6)
    # Validate ancestry before creating anything. No mkdir(parents=True).
    for p in [path.parent, *path.parent.parents]:
        require(not p.is_symlink(), 'linked state ancestry refused')
    require(Path(routes).is_absolute(), 'explicit absolute public routes required')
    pool = _pool.Pool(routes)
    raw, profiles, _ = pool.read()
    require(profiles and set(profiles) <= ALLOWED_PROFILES, 'public pool incompatible with current account authority')
    require(read_regular(Path(routes).with_name('fast-tier'), 17) in (b'true', b'true\n'), 'selected all-fast policy unavailable/disabled; no fallback')
    os.mkdir(path, 0o700)
    files = Files(path)
    for name in ('lock', 'budget.jsonl', 'watch.lock'):
        fd = os.open(path / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.fsync(fd)
        os.close(fd)
    files.sync()
    state = {'schema': 1, 'generation': 0, 'created': time.time(),
             'pool_routes': str(routes), 'pool_binding': pool.control_binding(raw),
             'actors': {owner: {'role': 'Work', 'credential': secret_hash(credential), 'active': True,
                                'adopted': True, 'basis': 'creator explicit self-adoption'}},
             'events': {}, 'attempts': {}, 'packets': {}, 'effects': {},
             'branches': {}, 'reviews': {}, 'packages': {}, 'versions': {}, 'audit': []}
    with files.lock():
        files.save(state)
    return {'created': str(path), 'owner': owner, 'schema': 1, 'identity': 'cooperative self-assertion'}


class Runtime:
    def __init__(self, path, *, clock=time.time, fault=lambda phase: None):
        self.files = Files(path, clock=clock, fault=fault)
        self.clock = clock

    def pool(self, s):
        return _pool.Pool(s['pool_routes'], charge=lambda n: self.files.charge(reads=n),
                          before_write=self.pool_capacity,
                          reader=lambda p, n: self.pool_read(p, n))

    def pool_capacity(self, path):
        # Selected public control ancestry only; no profile or store traversal.
        parent = path
        missing = 0
        while not parent.exists():
            missing += 1
            parent = parent.parent
        check_capacity(parent, 16384, missing + 3)

    def fast(self, s):
        self.files.charge(reads=17)
        raw = read_regular(Path(s['pool_routes']).with_name('fast-tier'), 17)
        require(raw in (b'true', b'true\n'), 'selected all-fast policy unavailable/disabled; no fallback')
        return {'requested_service_tier': 'fast', 'features.fast_mode': True, 'served_service_tier': 'unobserved'}

    def pool_read(self, path, maximum):
        size = os.lstat(path).st_size
        require(size <= maximum, 'public control exceeds finite bound')
        self.files.charge(reads=size + 1)
        return _pool.bounded_read(path, size)

    def call(self, operation, actor, credential, **args):
        require(len(encode(args)) <= 32768, 'finite command body exceeded')
        ident(actor)
        require(operation in self.OPERATIONS, 'unsupported operation; no fallback')
        readonly = operation in {'status', 'inbox', 'recover', 'eligibility', 'readback'}
        continuation = operation in {'recover', 'readback', 'inbox', 'cancel', 'collect', 'reconcile', 'observe_effect',
                                     'classify', 'ack', 'receipt', 'resolve', 'finish', 'hold', 'integrate', 'send', 'partial'}
        with self.files.transaction(readonly=readonly, continuation=continuation) as s:
            who = s['actors'].get(actor)
            require(who and secrets.compare_digest(who['credential'], secret_hash(credential)), 'actor credential rejected')
            require(who['active'], 'actor revoked; original custody remains')
            require(who['adopted'] or operation == 'adopt', 'explicit self-adoption required')
            if not readonly and not continuation:
                require(len(s['audit']) < 448, 'work pressure hold; audit continuation headroom')
            try:
                result = getattr(self, 'op_' + operation)(s, actor, **args)
            except TypeError as exc:
                raise Held('invalid command fields') from exc
            if not readonly:
                s['audit'].append({'op': operation, 'actor': actor, 'at': self.clock()})
                require(len(s['audit']) <= 512, 'finite audit full; no truncation')
                # Exact candidate bytes plus a bounded accountable-partial tail,
                # NOT an estimate claiming every possible successful closure fits.
                # All mutations, including duplicates and continuation growth,
                # must leave this tail for existing admitted records.
                self.partial_capacity(s)
            self.files.fault('before-commit')
            receivers = tuple(s['actors'])
        self.files.fault('after-commit')
        if not readonly:
            self.hint(receivers)
        return result

    def partial_capacity(self, s):
        pending = self.partial_records(s)
        count = len(pending)
        # Each record gets two read/discovery visits and one immutable partial
        # disposition. 1024 covers its entire encoded marker (512-byte evidence,
        # 128-byte actor, finite timestamp and field syntax). Audit <=256/visit.
        # 4096 covers envelope/hash, generation and fixed syntax slack.
        visits = 5 * count + 4
        state_bound = len(encode(s)) + count * (1024 + 256) + 4096
        require(state_bound <= MAX_STATE and len(s['audit']) + count <= 512,
                'consequence pressure: use owner partial/readback; new material does not fit')
        # Tail operations do not access controls: one read charge per query,
        # read+save per disposition, <=384 encoded bytes per journal record.
        journal = os.lstat(self.files.path / 'budget.jsonl').st_size
        journal_bound = journal + (6 * count + 8) * 384
        require(journal_bound <= MAX_BUDGET, 'consequence journal pressure: owner partial required')
        future = {'bytes': (count + 1) * (state_bound + 8192),
                  'reads': visits * (state_bound + journal_bound), 'entries': count + 1}
        self.files.charge(future=future)
        self.files.future = future

    def partial_records(self, s):
        records = []
        for kind, collection in COLLECTIONS.items():
            for key, value in s[collection].items():
                if value.get('partial'):
                    continue
                pending = (kind == 'event' and not value['finished'] or
                           kind == 'attempt' and not value['reconciled'] or
                           kind == 'packet' and value['stage'] != 'settled' or
                           kind == 'effect' and value['state'] != 'settled')
                if pending:
                    records.append({'kind': kind, 'id': key})
        return records

    def authority(self, s, actor, credential):
        who = s['actors'].get(actor)
        require(who and secrets.compare_digest(who['credential'], secret_hash(credential)), 'actor credential rejected')
        require(who['active'] and who['adopted'], 'actor revoked or not adopted; original custody remains')

    def wake_address(self, actor):
        return '\0rfq-file-' + hashlib.sha256((str(self.files.path) + '\0' + actor).encode()).hexdigest()

    def hint(self, receivers):
        import socket
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.setblocking(False)
            for actor in receivers:
                try:
                    sock.sendto(b'changed', self.wake_address(actor))
                except OSError:
                    pass  # Lossy hints; durable addressed state is authoritative.

    def role(self, s, actor, roles):
        require(s['actors'][actor]['role'] in roles, 'operation outside role authority')

    def event(self, s, actor, event):
        e = s['events'][ident(event)]
        require(e['responsibility'] and e['responsibility']['owner'] == actor, 'event responsibility belongs to another owner')
        return e

    def attempt(self, s, actor, attempt, collector):
        a = s['attempts'][ident(attempt)]
        require(a['owner'] == actor and secrets.compare_digest(a['collector'], text(collector)), 'original collector required')
        return a

    def op_invite(self, s, actor, target, role, invitation_token, basis):
        self.role(s, actor, {'Work'})
        ident(target)
        require(role in ROLES and target not in s['actors'], 'unsupported role or actor already bound')
        s['actors'][target] = {'role': role, 'credential': secret_hash(invitation_token), 'active': True,
                               'adopted': False, 'basis': text(basis)}
        return {'invited': target, 'adopted': False}

    def op_adopt(self, s, actor, basis):
        require(not s['actors'][actor]['adopted'], 'already adopted; identity cannot be rebound')
        s['actors'][actor]['adopted'] = True
        s['actors'][actor]['encounter'] = text(basis)
        return {'actor': actor, 'role': s['actors'][actor]['role'], 'adopted': True,
                'identity': 'cooperative self-assertion; real-owner acceptance separately owed'}

    def op_revoke(self, s, actor, target, reason):
        self.role(s, actor, {'Work'})
        require(target != actor, 'cannot revoke last coordinating owner through this API')
        s['actors'][target]['active'] = False
        s['actors'][target]['revocation'] = text(reason)
        return {'revoked': target, 'custody': 'retained; no successor or replay authorized'}

    def op_ingest(self, s, actor, event, payload, producer, source_basis):
        self.role(s, actor, {'Work'})
        ident(event)
        require(len(encode(payload)) <= 4096, 'intake payload exceeds 4KiB; retain source, not admitted')
        value = {'payload': payload, 'producer': text(producer), 'source_basis': text(source_basis)}
        h = digest(value)
        if event in s['events']:
            require(s['events'][event]['source_hash'] == h, 'stable event ID has changed content')
            return {'event': event, 'duplicate': True, 'ack': s['events'][event]['ack']}
        s['events'][event] = {**value, 'source_hash': h, 'classification': None,
                              'responsibility': None, 'ack': False, 'processed_at': None,
                              'holds': ['original', 'source', 'effect', 'consumer', 'outbox', 'recovery', 'privacy', 'resource'],
                              'resolutions': {}, 'finished': False}
        return {'event': event, 'ack': False}

    def op_classify(self, s, actor, event, attempt, collector, classification, owner, needs):
        self.role(s, actor, {'Work'})
        e = s['events'][ident(event)]
        require(e['classification'] is None, 'classification already committed; no fresh replay')
        a = self.attempt(s, actor, attempt, collector)
        require(a['phase'] == 'classifier' and a['event'] == event and a['state'] == 'collected'
                and a['end'] == 0 and a['selector'] == 'luna-low' and a['fresh'], 'fresh collected LOW attempt required')
        require(classification in {'known', 'new', 'unresolved', 'control', 'coalesced'}, 'unsupported classification')
        require(a['result'] == {'event_hash': e['source_hash'], 'classification': classification}, 'typed classifier result/source mismatch')
        require(owner in s['actors'] and s['actors'][owner]['adopted'] and s['actors'][owner]['active'], 'current adopted responsibility owner required')
        require(isinstance(needs, list) and 0 < len(needs) <= 16 and len(set(needs)) == len(needs), 'explicit unresolved responsibilities required')
        for need in needs:
            ident(need)
        e['classification'] = {'kind': classification, 'attempt': attempt, 'capture_hash': digest(a['result']),
                               'source_hash': e['source_hash'], 'selector': a['selector'], 'provenance': a['evidence']}
        e['responsibility'] = {'owner': owner, 'needs': needs}
        return {'event': event, 'responsibility_durable_on_return': True, 'ack': False}

    def op_ack(self, s, actor, event):
        self.role(s, actor, {'Work'})
        e = s['events'][ident(event)]
        require(e['classification'] and e['responsibility'], 'no ACK before durable classification and responsibility')
        e['ack'] = True
        return {'event': event, 'ack': True, 'whole_processing_complete': e['processed_at'] is not None}

    def op_package(self, s, actor, package, event, scope, basis):
        self.role(s, actor, {'Work'})
        ident(package)
        e = s['events'][ident(event)]
        require(package not in s['packages'] and e['classification'] and e['classification']['kind'] == 'known', 'new package and classified known event required')
        require(s['actors'][e['responsibility']['owner']]['role'] == 'QA', 'package must address QA responsibility')
        s['packages'][package] = {'event': event, 'scope': text(scope), 'basis': text(basis), 'source_hash': e['source_hash']}
        return {'package': package, 'admitted': True}

    def op_branch(self, s, actor, branch, repository, ref, incarnation, root, basis):
        self.role(s, actor, {'Branch'})
        ident(branch)
        require(branch not in s['branches'], 'branch binding immutable; new incarnation needs new ID')
        require(not any((b['repository'], b['ref'], b['incarnation']) == (repository, ref, incarnation)
                        for b in s['branches'].values()), 'branch association already bound; use its existing ID')
        s['branches'][branch] = {'owner': actor, 'repository': text(repository), 'ref': text(ref),
                                 'incarnation': text(incarnation), 'root': text(root), 'basis': text(basis)}
        return {'branch': branch, 'prospective': True}

    def op_review(self, s, actor, review, component, branch, opaque_contract, context, history, predecessor=None):
        self.role(s, actor, {'Reviews'})
        ident(review)
        require(review not in s['reviews'] and branch in s['branches'], 'new review and bound branch required')
        if predecessor is not None:
            require(predecessor in s['reviews'], 'unknown predecessor; no invented continuity')
            prior = s['reviews'][predecessor]
            require((prior['owner'], prior['component'], prior['branch'], prior['opaque_contract']) ==
                    (actor, component, branch, opaque_contract), 'review predecessor association conflict')
        s['reviews'][review] = {'owner': actor, 'component': text(component), 'branch': branch,
                                'opaque_contract': text(opaque_contract), 'context': text(context),
                                'history': text(history), 'predecessor': predecessor, 'calls': []}
        return {'review': review, 'encounter': 'new', 'exact_session_resume': 'unsupported'}

    def op_reserve(self, s, actor, attempt, event, phase, resources, basis, point=None, package=None, branch=None, review=None):
        ident(attempt)
        require(attempt not in s['attempts'] and phase in PHASES, 'new attempt and supported phase required')
        e = s['events'][ident(event)]
        required = {'classifier': {'Work'}, 'discovery': {'Work'}, 'known': {'Work', 'Branch'},
                    'qa-execute': {'QA'}, 'qa-consolidate': {'QA'}, 'review': {'Reviews'}}
        self.role(s, actor, required[phase])
        if phase == 'classifier':
            require(e['classification'] is None, 'already classified')
        else:
            self.event(s, actor, event)
            require(e['ack'] and not e['finished'], 'acknowledged open responsibility required')
            require(e['classification']['kind'] in ({'new'} if phase == 'discovery' else {'known'}), 'unresolved/control/coalesced requires owner resolution; discovery only genuinely new')
        require(isinstance(resources, dict) and len(resources) <= 16, 'finite complete resource footprint required')
        for key, mode in resources.items():
            ident(key)
            require(mode in {'read', 'write'}, 'resource mode must be read/write')
        require(isinstance(basis, dict) and set(basis) == set(resources), 'version basis must cover every declared resource including absence')
        require(all(type(v) is int and v >= 0 for v in basis.values()), 'invalid version')
        require(all(s['versions'].get(k, 0) == v for k, v in basis.items()), 'stale resource version')
        if phase == 'known':
            ident(point)
            require('point:' + point in resources, 'known work requires stable point resource')
        if phase.startswith('qa-'):
            ident(package)
            require(package in s['packages'] and s['packages'][package]['event'] == event, 'Work-admitted exact QA package required')
            if phase == 'qa-consolidate':
                executions = [a for a in s['attempts'].values() if a['package'] == package and a['phase'] == 'qa-execute']
                executed = [a for a in executions if a['state'] != 'cancelled']
                require(executed and all(a['reconciled'] and a['state'] == 'collected' and type(a['end']) is int for a in executed),
                        'collected and reconciled QA execution required before consolidation; unknowns retained')
        if phase == 'known' and s['actors'][actor]['role'] == 'Branch':
            require(branch in s['branches'] and s['branches'][branch]['owner'] == actor, 'current branch/role binding required')
            require(resources.get('branch:' + branch) == 'write', 'branch writer must declare branch resource')
        if phase == 'review':
            require(review in s['reviews'] and s['reviews'][review]['owner'] == actor, 'opaque Reviews continuity binding required')
            require(resources.get('review:' + review) == 'write', 'review run must declare its continuity resource')
            associated = s['reviews'][review]['branch']
            require(branch in (None, associated), 'review branch association conflict')
            require('branch:' + associated in resources, 'review must declare its actual branch footprint')
            branch = associated
        else:
            require(review is None, 'review history accepts only owner review-phase attempts')
            require(branch is None or (phase == 'known' and s['actors'][actor]['role'] == 'Branch'),
                    'branch attempt requires Branch known authority')
        active = [a for a in s['attempts'].values() if not a['reconciled']]
        require(not any(a['event'] == event and a['phase'] == phase for a in active), 'event phase already owned')
        require(not any(any(k in a['resources'] and ('write' in (m, a['resources'][k]))
                            for k, m in resources.items()) for a in active), 'resource conflict; original owner retained')
        if phase == 'discovery':
            require(not any(a['phase'] == phase for a in active), 'single new unknown-work discovery slot occupied')
        if phase.startswith('qa-'):
            require(not any(a['package'] == package for a in active), 'same QA package already owned')
            require(sum(a['phase'] == phase for a in active) < (5 if phase == 'qa-execute' else 1), 'QA phase capacity occupied')
        fast = self.fast(s)
        pool = self.pool(s)
        reservation = pool.allocate(ALLOWED_PROFILES, blocking=False, expected_control=s['pool_binding'])
        c = token()
        s['attempts'][attempt] = {'owner': actor, 'collector': c, 'event': event, 'phase': phase,
                                 'resources': resources, 'basis': basis, 'package': package, 'branch': branch,
                                 'review': review, 'state': 'reserved', 'reconciled': False,
                                 'pool': reservation, 'fast_control': fast, 'fast_requested': True, 'served_tier': 'unobserved',
                                 'selector': 'luna-low' if phase == 'classifier' else ('opaque-reviews' if phase == 'review' else 'sol-xhigh'),
                                 'fresh': phase == 'classifier', 'end': None, 'result': None}
        if review:
            s['reviews'][review]['calls'].append(attempt)
        return {'attempt': attempt, 'collector': c, 'reservation': reservation, 'fast_requested': True}

    def op_start(self, s, actor, attempt, collector, substrate, evidence):
        a = self.attempt(s, actor, attempt, collector)
        require(a['state'] == 'reserved', 'launch already started or unknown; no replay')
        # Only the bundled fixture adapter is machine-qualified by this source.
        # Owner-supplied encounters are evidence records, not a provider launcher.
        require(substrate in {'fixture', 'owner-encounter'}, 'unqualified provider launch refused')
        text(evidence)
        self.fast(s)
        with self.pool(s).admission(a['pool']['profile'], ALLOWED_PROFILES, blocking=False, expected_control=s['pool_binding']) as admission:
            a.update(state='launching', substrate=substrate, evidence=evidence, admission=admission,
                     launch_id=token(), started_at=self.clock())
        return {'attempt': attempt, 'launch_id': a['launch_id'], 'state': 'launching',
                'custody': 'original collector; absence/timeouts authorize no replay'}

    def op_collect(self, s, actor, attempt, collector, launch_id, end, result, evidence):
        a = self.attempt(s, actor, attempt, collector)
        if a['state'] == 'collected':
            require((a['launch_id'], a['end'], a['result'], a['collection_evidence']) ==
                    (launch_id, end, result, evidence) and type(end) is int, 'collection identity/evidence conflict')
            return {'attempt': attempt, 'end': a['end'], 'reconciled': a['reconciled'], 'duplicate': True}
        require(a['state'] == 'launching' and a['launch_id'] == launch_id, 'original launch correlation required')
        require(type(end) is int and -255 <= end <= 255, 'actual numeric process END required')
        require(len(encode(result)) <= 4096, 'finite collected result exceeds 4KiB; retain original outside evidence')
        a.update(state='collected', end=end, result=result, collection_evidence=text(evidence), collected_at=self.clock())
        return {'attempt': attempt, 'end': end, 'reconciled': False}

    def op_reconcile(self, s, actor, attempt, collector, evidence, builder=None):
        a = self.attempt(s, actor, attempt, collector)
        if a['reconciled']:
            require(a.get('reconciliation') == evidence and a.get('builder') == builder,
                    'reconciliation identity/evidence conflict')
            return {'attempt': attempt, 'reconciled': True, 'acceptance': 'not implied', 'duplicate': True}
        require(a['state'] == 'collected', 'numeric END missing; original custody retained')
        require(all(x['state'] == 'settled' for x in s['effects'].values() if x['attempt'] == attempt), 'uncertain effect remains held')
        if a['branch'] and a['phase'] == 'known':
            require(isinstance(builder, dict) and set(builder) == {'commit', 'remote_readback', 'pushed', 'signed', 'effects_reconciled'}, 'builder handback requires exact commit/push/readback/effects')
            require(re.fullmatch('[0-9a-f]{40}', builder['commit']) and builder['commit'] == builder['remote_readback']
                    and builder['pushed'] is True and builder['signed'] is True and builder['effects_reconciled'] is True,
                    'builder commit/push/readback not reconciled')
            a['builder'] = builder
        else:
            require(builder is None, 'builder evidence belongs only to Branch known attempts')
        a.update(reconciled=True, reconciliation=text(evidence), reconciled_by=actor, reconciled_at=self.clock())
        return {'attempt': attempt, 'reconciled': True, 'acceptance': 'not implied'}

    def op_cancel(self, s, actor, attempt, collector, evidence):
        """Account for definitely unstarted work only; never refund a turn."""
        a = self.attempt(s, actor, attempt, collector)
        text(evidence)
        if a['state'] == 'cancelled':
            require(a['disposition']['evidence'] == evidence, 'disposition identity/evidence conflict')
            return {'attempt': attempt, 'state': 'cancelled', 'duplicate': True, 'turn_refunded': False}
        require(a['state'] in {'reserved', 'not-started'} and not any(x['attempt'] == attempt for x in s['effects'].values()),
                'only definitely unstarted reservation can be dispositioned; uncertain custody retained')
        a.update(state='cancelled', reconciled=True,
                 disposition={'actor': actor, 'evidence': evidence, 'at': self.clock(), 'launched': False})
        return {'attempt': attempt, 'state': 'cancelled', 'turn_refunded': False}

    def op_integrate(self, s, actor, attempt, collector, writes):
        a = self.attempt(s, actor, attempt, collector)
        require(a['state'] == 'collected' and a['end'] == 0 and not a.get('integrated'), 'one successful collected proposal required')
        require(isinstance(writes, dict) and set(writes) <= {k for k, m in a['resources'].items() if m == 'write'}, 'write outside admitted footprint')
        require(writes and all(s['versions'].get(k, 0) == v for k, v in a['basis'].items()), 'stale proposal; reconciliation required')
        require(len(encode(writes)) <= 4096, 'integration exceeds 4KiB; retain proposal for accountable partial return')
        require(not a['reconciled'], 'released proposal cannot integrate; new admitted attempt required')
        # These are coordinator material versions/deltas only. External files or
        # Git refs require a separately owned effect; never mutate them here.
        for k, value in writes.items():
            s['versions'][k] = s['versions'].get(k, 0) + 1
        a.update(integrated=True, delta=writes)
        return {'versions': {k: s['versions'][k] for k in writes}, 'external_effects': False}

    def op_effect(self, s, actor, effect, attempt, collector, kind, intent):
        a = self.attempt(s, actor, attempt, collector)
        ident(effect)
        if effect in s['effects']:
            x = s['effects'][effect]
            require((x['owner'], x['attempt'], x['kind'], x['intent']) == (actor, attempt, kind, intent),
                    'effect intent identity/content conflict')
            return {'effect': effect, 'state': x['state'], 'duplicate': True, 'replay': 'not authorized'}
        require(not a['reconciled'] and a['state'] == 'launching', 'new pre-effect intent required')
        require(kind in {'publication', 'push', 'delivery'}, 'unsupported effect kind')
        s['effects'][effect] = {'owner': actor, 'attempt': attempt, 'kind': kind, 'intent': text(intent),
                                'state': 'intent', 'observation': None}
        return {'effect': effect, 'state': 'intent', 'replay': 'forbidden until original owner reconciles'}

    def op_observe_effect(self, s, actor, effect, outcome, evidence):
        x = s['effects'][ident(effect)]
        require(x['owner'] == actor, 'original effect owner required')
        if x['state'] == 'settled':
            require(x['outcome'] == outcome and x['observation'] == evidence, 'effect identity/evidence conflict')
            return {'effect': effect, 'state': 'settled', 'outcome': outcome, 'duplicate': True}
        require(outcome in {'applied', 'not-applied'}, 'unknown effect must remain intent/held')
        x.update(state='settled', outcome=outcome, observation=text(evidence), observed_by=actor, observed_at=self.clock())
        return {'effect': effect, 'state': 'settled', 'outcome': outcome}

    def op_send(self, s, actor, packet, event, recipient, payload, correction_of=None):
        e = self.event(s, actor, event)
        ident(packet)
        target = s['actors'].get(recipient)
        require(target and target['active'] and target['adopted'], 'current adopted recipient required')
        if correction_of is not None:
            require(correction_of in s['packets'] and s['packets'][correction_of]['sender'] == actor, 'correction source not owned')
        value = {'event': event, 'sender': actor, 'recipient': recipient, 'payload': payload, 'correction_of': correction_of}
        require(len(encode(value)) <= 8192, 'finite packet exceeds 8KiB')
        if packet in s['packets']:
            require(s['packets'][packet]['hash'] == digest(value), 'packet ID/content conflict')
        else:
            require(not e['finished'], 'closed source cannot create new downstream duties')
            s['packets'][packet] = {**value, 'hash': digest(value), 'stage': 'pending', 'receipts': []}
            for affected in self.packet_events(s, packet):
                if s['events'][affected]['finished']:
                    s['events'][affected].update(finished=False, processed_at=None)
        return {'packet': packet, 'stage': s['packets'][packet]['stage']}

    def packet_events(self, s, packet):
        events = set()
        while packet is not None:
            p = s['packets'][packet]
            events.add(p['event'])
            packet = p['correction_of']
        return events

    def op_inbox(self, s, actor, limit=16):
        require(type(limit) is int and 1 <= limit <= 32, 'finite inbox limit required')
        return {'packets': [{k: v for k, v in p.items() if k != 'receipts'} | {'id': key}
                            for key, p in s['packets'].items() if p['recipient'] == actor and p['stage'] != 'settled'][:limit]}

    def op_receipt(self, s, actor, packet, stage, evidence):
        p = s['packets'][ident(packet)]
        require(p['recipient'] == actor, 'only actual addressed recipient can receipt')
        text(evidence)
        existing = [r for r in p['receipts'] if r['stage'] == stage]
        if existing:
            require(existing[0]['evidence'] == evidence, 'receipt identity/evidence conflict')
            return {'packet': packet, 'stage': p['stage'], 'duplicate': True}
        order = ['pending', 'picked-up', 'processed', 'settled']
        require(stage in order[1:] and order.index(stage) == order.index(p['stage']) + 1, 'receipt must advance exactly one stage')
        p['receipts'].append({'actor': actor, 'stage': stage, 'evidence': text(evidence), 'at': self.clock()})
        p['stage'] = stage
        return {'packet': packet, 'stage': stage}

    def op_resolve(self, s, actor, event, need, evidence):
        e = self.event(s, actor, event)
        require(need in e['responsibility']['needs'], 'unknown responsibility')
        if need in e['resolutions']:
            require(e['resolutions'][need] == evidence, 'resolution identity/evidence conflict; use a correction duty')
            return {'event': event, 'need': need, 'resolved': True, 'duplicate': True}
        require(not e['finished'], 'closed responsibility')
        e['resolutions'][need] = text(evidence)
        e.setdefault('resolution_history', []).append({'actor': actor, 'need': need, 'evidence': evidence, 'at': self.clock()})
        return {'event': event, 'need': need, 'resolved': True}

    def incomplete(self, s, event):
        e = s['events'][event]
        reasons = []
        if not e['responsibility'] or set(e['resolutions']) != set(e['responsibility']['needs']):
            reasons.append('unresolved responsibilities')
        if any(not a['reconciled'] for a in s['attempts'].values() if a['event'] == event):
            reasons.append('original attempt custody')
        if any(p['stage'] != 'settled' and event in self.packet_events(s, key) for key, p in s['packets'].items()):
            reasons.append('downstream unsettled')
        return reasons

    def op_finish(self, s, actor, event):
        e = self.event(s, actor, event)
        require(e['ack'] and not self.incomplete(s, event), 'whole processing incomplete: ' + ', '.join(self.incomplete(s, event)))
        if not e['finished']:
            e.update(finished=True, processed_at=self.clock())
        return {'event': event, 'processed_at': e['processed_at'], 'retention': '24h AND every hold; no deletion API'}

    def op_hold(self, s, actor, event, name, enabled, evidence):
        e = self.event(s, actor, event)
        ident(name)
        require(type(enabled) is bool, 'enabled must be boolean')
        text(evidence)
        require(len(e.get('hold_evidence', [])) < MAX_HISTORY,
                'finite 12-entry hold history; preserve new assertion outside runtime and report partial')
        if enabled:
            if name not in e['holds']:
                e['holds'].append(name)
        elif name in e['holds']:
            # Named holders must authorize release; runtime records their scoped
            # evidence but performs no actual retained-data cleanup.
            e['holds'].remove(name)
        e.setdefault('hold_evidence', []).append({'actor': actor, 'at': self.clock(), 'name': name, 'enabled': enabled, 'evidence': evidence})
        return {'holds': e['holds'], 'deletion_authorized': False}

    def op_eligibility(self, s, actor, event):
        e = self.event(s, actor, event)
        eligible = e['processed_at'] is not None and self.clock() >= e['processed_at'] + 86400 and not e['holds'] and not self.incomplete(s, event)
        return {'eligible_metadata_only': eligible, 'holds': e['holds'], 'deletion_authorized': False}

    def op_recover(self, s, actor):
        return {'attempts': [{'id': key, 'owner': a['owner'], 'state': a['state'], 'end': a['end'],
                               **({'collector': a['collector'], 'launch_id': a.get('launch_id')} if a['owner'] == actor else {}),
                               'action': 'original collector reconciliation; no timeout release'}
                              for key, a in s['attempts'].items() if not a['reconciled'] and (a['owner'] == actor or s['actors'][actor]['role'] == 'Work')],
                'effects': [{'id': key, 'owner': x['owner'], 'state': x['state']} for key, x in s['effects'].items() if x['state'] != 'settled' and (x['owner'] == actor or s['actors'][actor]['role'] == 'Work')],
                'unacked': [key for key, e in s['events'].items() if not e['ack']],
                'incomplete': [key for key, e in s['events'].items() if not e['finished']],
                'addressed': [key for key, p in s['packets'].items() if actor in {p['sender'], p['recipient']} and p['stage'] != 'settled'],
                'partial_candidates': [p for p in self.partial_records(s) if self.can_partial(s, actor, p['kind'], p['id'])]}

    def can_partial(self, s, actor, kind, id):
        value = s[COLLECTIONS[kind]][id]
        if kind == 'event':
            return (value['responsibility'] or {}).get('owner') == actor or s['actors'][actor]['role'] == 'Work'
        if kind == 'packet':
            return actor in {value['sender'], value['recipient']}
        return value.get('owner') == actor

    def op_partial(self, s, actor, kind, id, evidence):
        require(kind in {'event', 'attempt', 'packet', 'effect'}, 'partial requires an obligation record')
        ident(id)
        text(evidence)
        require(self.can_partial(s, actor, kind, id), 'partial outside actual owner/addressed authority')
        value = s[COLLECTIONS[kind]][id]
        if value.get('partial'):
            require(value['partial']['actor'] == actor and value['partial']['evidence'] == evidence,
                    'partial identity/evidence conflict')
        else:
            value['partial'] = {'actor': actor, 'at': self.clock(), 'evidence': evidence}
        return {'kind': kind, 'id': id, 'partial': value['partial'], 'completed': False,
                'custody': 'unchanged; all needs, originals, effects and holds retained'}

    def op_readback(self, s, actor, kind, id):
        """Read committed operands/results, never recover a process handle."""
        collections = {'attempt': 'attempts', 'event': 'events', 'packet': 'packets', 'effect': 'effects',
                       'branch': 'branches', 'review': 'reviews', 'package': 'packages'}
        require(kind in collections, 'unsupported readback kind')
        value = s[collections[kind]][ident(id)]
        if kind in {'attempt', 'effect', 'branch', 'review'}:
            require(value['owner'] == actor, 'only original owner can read back owned operands/results')
        elif kind == 'packet':
            require(actor in {value['sender'], value['recipient']}, 'packet readback outside addressed relationship')
        else:
            e = value if kind == 'event' else s['events'][value['event']]
            require(s['actors'][actor]['role'] == 'Work' or (e['responsibility'] or {}).get('owner') == actor,
                    'event readback outside responsibility')
        return {'kind': kind, 'id': id, 'value': value, 'custody': 'original owner; no replay or external truth implied'}

    def op_status(self, s, actor):
        return {'generation': s['generation'], 'actors': {k: {x: a[x] for x in ('role', 'active', 'adopted')} for k, a in s['actors'].items()},
                'versions': s['versions'], 'events': {k: {'ack': e['ack'], 'owner': (e['responsibility'] or {}).get('owner'),
                                                        'processed_at': e['processed_at'], 'holds': e['holds']} for k, e in s['events'].items()},
                'pool_routes': s['pool_routes'], 'fast_requested': True,
                'served_tier': 'unobserved', 'provider_launch': 'unqualified/refused', 'release': 'unsupported'}

    OPERATIONS = {'invite', 'adopt', 'revoke', 'package', 'ingest', 'classify', 'ack', 'branch', 'review', 'reserve', 'start', 'collect',
                  'reconcile', 'integrate', 'effect', 'observe_effect', 'send', 'inbox', 'receipt', 'resolve', 'finish',
                  'hold', 'eligibility', 'recover', 'status', 'readback', 'cancel', 'partial'}
