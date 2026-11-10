"""Prospective file-native Work/Branch/Reviews/QA coordination.

No legacy imports. Public pool control is the sole non-stdlib dependency.
External owners assert identity/evidence inside the same-user cooperative model.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import secrets
import time

from storage import Files, Held, MAX_STATE, check_capacity, digest, encode, read_regular

# This public helper has no provider/account-store access. Never import the old
# runtime or Board as a compatibility adapter.
_pool_path = Path(__file__).resolve().parents[1] / 'direct-child' / 'execution_pool.py'
_spec = importlib.util.spec_from_file_location('file_runtime_public_pool', _pool_path)
_pool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pool)
ROLES = {'Work', 'Branch', 'Reviews', 'QA'}
PHASES = {'classifier', 'known', 'discovery', 'qa-execute', 'qa-consolidate', 'review'}
ALLOWED_PROFILES = {'.codex2', '.codex3', '.codex4', '.codex5'}


def require(condition, message):
    if not condition:
        raise Held(message)


def text(value):
    require(isinstance(value, str) and 0 < len(value) <= 2048, 'nonempty bounded string required')
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
    check_capacity(path.parent)
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
                          before_write=lambda p: check_capacity(p if p.exists() else p.parent),
                          reader=lambda p, n: self.pool_read(p, n))

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
        with self.files.transaction() as s:
            who = s['actors'].get(actor)
            require(who and secrets.compare_digest(who['credential'], secret_hash(credential)), 'actor credential rejected')
            require(who['active'], 'actor revoked; original custody remains')
            require(who['adopted'] or operation == 'adopt', 'explicit self-adoption required')
            try:
                result = getattr(self, 'op_' + operation)(s, actor, **args)
            except TypeError as exc:
                raise Held('invalid command fields') from exc
            if operation not in {'status', 'inbox', 'recover', 'eligibility'}:
                s['audit'].append({'op': operation, 'actor': actor, 'at': self.clock()})
                require(len(s['audit']) <= 512, 'finite audit full; no truncation')
            self.files.fault('before-commit')
        self.files.fault('after-commit')
        if operation not in {'status', 'inbox', 'recover', 'eligibility'}:
            self.hint()
        return result

    def hint(self):
        import socket
        fd = os.open(self.files.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
                sock.setblocking(False)
                sock.sendto(b'changed', '/proc/self/fd/' + str(fd) + '/wake.sock')
        except OSError:
            pass  # Identity-only lossy hint. Durable state is authoritative.
        finally:
            os.close(fd)

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
        s['branches'][branch] = {'owner': actor, 'repository': text(repository), 'ref': text(ref),
                                 'incarnation': text(incarnation), 'root': text(root), 'basis': text(basis)}
        return {'branch': branch, 'prospective': True}

    def op_review(self, s, actor, review, component, branch, opaque_contract, context, history, predecessor=None):
        self.role(s, actor, {'Reviews'})
        ident(review)
        require(review not in s['reviews'] and branch in s['branches'], 'new review and bound branch required')
        if predecessor is not None:
            require(predecessor in s['reviews'], 'unknown predecessor; no invented continuity')
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
                require(executions and all(a['reconciled'] and a['end'] == 0 for a in executions), 'successful collected QA execution required before consolidation')
        if phase == 'known' and s['actors'][actor]['role'] == 'Branch':
            require(branch in s['branches'] and s['branches'][branch]['owner'] == actor, 'current branch/role binding required')
            require(resources.get('branch:' + branch) == 'write', 'branch writer must declare branch resource')
        if phase == 'review':
            require(review in s['reviews'] and s['reviews'][review]['owner'] == actor, 'opaque Reviews continuity binding required')
            require(resources.get('review:' + review) == 'write', 'review run must declare its continuity resource')
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
        require(a['state'] == 'launching' and a['launch_id'] == launch_id, 'original launch correlation required')
        require(type(end) is int and -255 <= end <= 255, 'actual numeric process END required')
        a.update(state='collected', end=end, result=result, collection_evidence=text(evidence), collected_at=self.clock())
        return {'attempt': attempt, 'end': end, 'reconciled': False}

    def op_reconcile(self, s, actor, attempt, collector, evidence, builder=None):
        a = self.attempt(s, actor, attempt, collector)
        require(a['state'] == 'collected', 'numeric END missing; original custody retained')
        require(all(x['state'] == 'settled' for x in s['effects'].values() if x['attempt'] == attempt), 'uncertain effect remains held')
        if a['branch']:
            require(isinstance(builder, dict) and set(builder) == {'commit', 'remote_readback', 'pushed', 'signed', 'effects_reconciled'}, 'builder handback requires exact commit/push/readback/effects')
            require(re.fullmatch('[0-9a-f]{40}', builder['commit']) and builder['commit'] == builder['remote_readback']
                    and builder['pushed'] is True and builder['signed'] is True and builder['effects_reconciled'] is True,
                    'builder commit/push/readback not reconciled')
            a['builder'] = builder
        a.update(reconciled=True, reconciliation=text(evidence))
        return {'attempt': attempt, 'reconciled': True, 'acceptance': 'not implied'}

    def op_integrate(self, s, actor, attempt, collector, writes):
        a = self.attempt(s, actor, attempt, collector)
        require(a['state'] == 'collected' and a['end'] == 0 and not a.get('integrated'), 'one successful collected proposal required')
        require(isinstance(writes, dict) and set(writes) <= {k for k, m in a['resources'].items() if m == 'write'}, 'write outside admitted footprint')
        require(writes and all(s['versions'].get(k, 0) == v for k, v in a['basis'].items()), 'stale proposal; reconciliation required')
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
        require(effect not in s['effects'] and not a['reconciled'] and a['state'] == 'launching', 'new pre-effect intent required')
        require(kind in {'publication', 'push', 'delivery'}, 'unsupported effect kind')
        s['effects'][effect] = {'owner': actor, 'attempt': attempt, 'kind': kind, 'intent': text(intent),
                                'state': 'intent', 'observation': None}
        return {'effect': effect, 'state': 'intent', 'replay': 'forbidden until original owner reconciles'}

    def op_observe_effect(self, s, actor, effect, outcome, evidence):
        x = s['effects'][ident(effect)]
        require(x['owner'] == actor and x['state'] == 'intent', 'original effect owner required')
        require(outcome in {'applied', 'not-applied'}, 'unknown effect must remain intent/held')
        x.update(state='settled', outcome=outcome, observation=text(evidence))
        return {'effect': effect, 'state': 'settled', 'outcome': outcome}

    def op_send(self, s, actor, packet, event, recipient, payload, correction_of=None):
        e = self.event(s, actor, event)
        require(not e['finished'], 'closed source cannot create new downstream duties')
        ident(packet)
        target = s['actors'].get(recipient)
        require(target and target['active'] and target['adopted'], 'current adopted recipient required')
        if correction_of is not None:
            require(correction_of in s['packets'] and s['packets'][correction_of]['sender'] == actor, 'correction source not owned')
        value = {'event': event, 'sender': actor, 'recipient': recipient, 'payload': payload, 'correction_of': correction_of}
        if packet in s['packets']:
            require(s['packets'][packet]['hash'] == digest(value), 'packet ID/content conflict')
        else:
            s['packets'][packet] = {**value, 'hash': digest(value), 'stage': 'pending', 'receipts': []}
        return {'packet': packet, 'stage': s['packets'][packet]['stage']}

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
        require(need in e['responsibility']['needs'] and not e['finished'], 'unknown or closed responsibility')
        e['resolutions'][need] = text(evidence)
        return {'event': event, 'need': need, 'resolved': True}

    def incomplete(self, s, event):
        e = s['events'][event]
        reasons = []
        if not e['responsibility'] or set(e['resolutions']) != set(e['responsibility']['needs']):
            reasons.append('unresolved responsibilities')
        if any(not a['reconciled'] for a in s['attempts'].values() if a['event'] == event):
            reasons.append('original attempt custody')
        if any(p['stage'] != 'settled' for p in s['packets'].values() if p['event'] == event):
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
        if enabled:
            if name not in e['holds']:
                e['holds'].append(name)
        elif name in e['holds']:
            # Named holders must authorize release; runtime records their scoped
            # evidence but performs no actual retained-data cleanup.
            e['holds'].remove(name)
        e.setdefault('hold_evidence', []).append({'name': name, 'enabled': enabled, 'evidence': evidence})
        return {'holds': e['holds'], 'deletion_authorized': False}

    def op_eligibility(self, s, actor, event):
        e = self.event(s, actor, event)
        eligible = e['processed_at'] is not None and self.clock() >= e['processed_at'] + 86400 and not e['holds'] and not self.incomplete(s, event)
        return {'eligible_metadata_only': eligible, 'holds': e['holds'], 'deletion_authorized': False}

    def op_recover(self, s, actor):
        self.role(s, actor, {'Work'})
        return {'attempts': [{'id': key, 'owner': a['owner'], 'state': a['state'], 'end': a['end'],
                               'action': 'original collector reconciliation; no timeout release'}
                              for key, a in s['attempts'].items() if not a['reconciled']],
                'effects': [{'id': key, 'owner': x['owner'], 'state': x['state']} for key, x in s['effects'].items() if x['state'] != 'settled'],
                'unacked': [key for key, e in s['events'].items() if not e['ack']],
                'incomplete': [key for key, e in s['events'].items() if not e['finished']]}

    def op_status(self, s, actor):
        return {'generation': s['generation'], 'actors': {k: {x: a[x] for x in ('role', 'active', 'adopted')} for k, a in s['actors'].items()},
                'versions': s['versions'], 'events': {k: {'ack': e['ack'], 'owner': (e['responsibility'] or {}).get('owner'),
                                                        'processed_at': e['processed_at'], 'holds': e['holds']} for k, e in s['events'].items()},
                'pool_routes': s['pool_routes'], 'fast_requested': True,
                'served_tier': 'unobserved', 'provider_launch': 'unqualified/refused', 'release': 'unsupported'}

    OPERATIONS = {'invite', 'adopt', 'revoke', 'package', 'ingest', 'classify', 'ack', 'branch', 'review', 'reserve', 'start', 'collect',
                  'reconcile', 'integrate', 'effect', 'observe_effect', 'send', 'inbox', 'receipt', 'resolve', 'finish',
                  'hold', 'eligibility', 'recover', 'status'}
