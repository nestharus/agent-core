"""Report-specific immutable custody, never a path/hash access capability.

Only same-journal event origins are supported. A reference retains an entire
canonical event, including its immediate links, without expanding those links.
The release gate stays closed until the complete consumer matrix is qualified.
"""
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
import hashlib
import json
from pathlib import Path

from .contracts import Refusal, digest, encode

VERSION = 'software-report-reference-v1'
READ_KIND = 'report-reference-read-v1'
ORIGIN_KIND = 'report-origin-v1'
RELEASED = False
_admitted = ContextVar('report_reference_admitted', default=None)


def policy(store):
    if not getattr(store, 'processing', None):
        return None
    record = store.processing.current()[1].get('service', {}).get('legacy_resources', {}).get('Reviews', {})
    return record.get('reviews_report', {}).get('transport')


def validate_policy(value, maximum):
    if (not isinstance(value, dict) or set(value) != {'version', 'max_model_bytes', 'max_origins', 'max_read_bytes'}
            or value['version'] != VERSION
            or any(type(value[k]) is not int or value[k] <= 0 for k in ('max_model_bytes', 'max_origins', 'max_read_bytes'))
            or value['max_model_bytes'] + 8192 > maximum or value['max_origins'] > 256):
        raise Refusal('explicit bounded software report reference policy required')
    if not RELEASED:
        raise Refusal('software report reference consumers are not release-qualified; preserve originals')


def _links(custody):
    if custody is None:
        return []
    if not isinstance(custody, dict) or custody.get('version') != VERSION:
        return []  # Old inline custody is frozen opaquely, never reinterpreted.
    links = custody.get('sources')
    if not isinstance(links, list) or not links:
        raise Refusal('reference custody needs exact immediate origins')
    return links


def _metadata(store, event):
    # These are selected authority/relationship fields, never an event body.
    row = store.one("SELECT id,role,hash,hold,json_extract(payload,'$.recipient') AS recipient,"
                    "json_extract(payload,'$.allowed_tasks') AS tasks,"
                    "COALESCE(json_extract(payload,'$.report_custody'),json_extract(payload,'$.body.report_custody')) AS custody "
                    "FROM events WHERE id=?", (event,))
    if not row or row['hold'] is not None:
        raise Refusal('report origin missing or held before acquisition')
    return row


def active(store, row):
    value = policy(store)
    if value is None:
        return False
    validate_policy(value, store.config['limits']['max_result_bytes'])
    if row['task'] == 'reviews-integrator':
        return True
    from .report_scope import source_metadata
    for source in source_metadata(store, row):
        meta = _metadata(store, source['id'])
        if _links(json.loads(meta['custody']) if meta['custody'] else None):
            return True
    return False


def identity(store, event):
    key = digest({'report_origin': event})
    return 'owner:report-origin:' + key, str(store.home/'artifacts'/'report-origins'/key)


def _origin(store, ref):
    if (not isinstance(ref, dict) or set(ref) != {'event', 'sha256', 'bytes', 'origin', 'owner', 'custodian'}
            or type(ref['bytes']) is not int or ref['bytes'] < 0):
        raise Refusal('exact software report origin descriptor required')
    context, path = identity(store, ref['event'])
    if ref['origin'] != context:
        raise Refusal('report origin identity contradiction')
    row = store.one('SELECT * FROM artifact_custody WHERE attempt=? AND path=?', (context, path))
    from .custody import custody_witness
    if not row or row['kind'] != ORIGIN_KIND:
        raise Refusal('unsupported origin import; exact same-journal custodian required')
    witness = custody_witness(row)
    if (encode(witness.get('reference')) != encode(ref) or row['owner'] != ref['owner']
            or row['sha256'] != ref['sha256'] or witness['size'] != ref['bytes']):
        raise Refusal('report origin descriptor contradicts immutable custody')
    return row, witness


def preflight(store, row):
    """Admit every current member and reachable origin before any body read.

    Must remain in the cooperative write transaction. No permission survives
    an await; every consumer entry starts this process again.
    """
    if not store.db.in_transaction:
        raise Refusal('report origin admission requires the source transaction')
    value = policy(store)
    validate_policy(value, store.config['limits']['max_result_bytes'])
    from .report_scope import source_metadata, validate
    selected = store.processing.current()[1]
    record = selected['service']['legacy_resources']['Reviews']
    validate(store, 'Reviews', record, selected)
    from .configuration import event_allowed
    from . import prospective
    roots = source_metadata(store, row)
    if not prospective.current(store, row['task']):
        raise Refusal('current report consumer epoch/grant required')
    store.processing.boards[row['role']].verify_authority(store)
    metadata, origins, visiting, visited = {}, [], set(), set()

    def admit(event, expected=None):
        meta = _metadata(store, event)
        if (expected is not None and meta['hash'] != expected or not event_allowed(store, meta)
                or meta['recipient'] != store.config['roles'][meta['role']]['owner']):
            raise Refusal('report origin outside current source/recipient authority')
        store.processing.boards[meta['role']].verify_authority(store)
        metadata[event] = meta
        if len(metadata) > value['max_origins']:
            raise Refusal('whole report closure exceeds selected origin bound; originals retained')
        return meta

    def visit(ref):
        event = ref.get('event') if isinstance(ref, dict) else None
        if event in visiting:
            raise Refusal('report origin cycle refused')
        meta = admit(event, ref['sha256'])
        origin, witness = _origin(store, ref)
        if witness.get('capability') != store.processing.key:
            raise Refusal('report origin import outside original selected capability')
        if (witness.get('role') != meta['role'] or witness.get('recipient') != meta['recipient']
                or witness.get('grant') != store.enrollment(meta['role'])['grant_id']):
            raise Refusal('report origin custodian/grant contradiction')
        links = _links(json.loads(meta['custody']) if meta['custody'] else None)
        if encode(links) != encode(witness.get('links')):
            raise Refusal('report origin immediate links changed')
        if event in visited:
            return
        visiting.add(event)
        for link in links:
            visit(link)
        visiting.remove(event)
        visited.add(event)
        origins.append((origin, witness))
        if len(metadata) > value['max_origins']:
            raise Refusal('whole report closure exceeds selected origin bound; originals retained')

    # All immediate members are admitted before traversing any origin.
    for source in roots:
        meta = admit(source['id'], source['hash'])
        if row['task'] not in json.loads(meta['tasks'] or '[]'):
            raise Refusal('report current task/recipient binding changed')
    for source in roots:
        meta = metadata[source['id']]
        for ref in _links(json.loads(meta['custody']) if meta['custody'] else None):
            visit(ref)
    if len(metadata) > value['max_origins'] or sum(w['size'] for _, w in origins) > value['max_read_bytes']:
        raise Refusal('whole report closure exceeds selected read bound; originals retained')
    from .custody import guard_frozen
    token = _admitted.set((id(store), frozenset(metadata)))
    try:
        for source in roots:
            context, path = identity(store, source['id'])
            guard_frozen(store, source['hash'], store.config['tasks'][row['task']], path)
        for origin, _ in origins:
            guard_frozen(store, origin['sha256'], store.config['tasks'][row['task']], origin['path'])
    finally:
        _admitted.reset(token)
    return roots, origins, metadata


@contextmanager
def admitted(store, row):
    with (nullcontext() if store.db.in_transaction else store.tx()):
        roots, origins, metadata = preflight(store, row)
        token = _admitted.set((id(store), frozenset(metadata)))
        try:
            yield roots, origins, metadata
        finally:
            _admitted.reset(token)


def guard_blob(store, witness):
    permission = _admitted.get()
    if (not store.db.in_transaction or not permission or permission[0] != id(store)
            or witness.get('reference', {}).get('event') not in permission[1]):
        raise Refusal('report blob needs current whole-group event admission; hash/parent grants nothing')


def inputs(store, row):
    from .custody import guard_frozen
    with admitted(store, row) as (roots, origins, metadata):
        result = []
        total = sum(w['size'] for _, w in origins)
        for source in roots:
            event = store.event(source['id'])
            if digest(event) != source['hash'] or not store.processing.event(event):
                raise Refusal('original canonical report changed or outside current authority')
            body = encode(event).encode()
            maximum = store.config['limits'].get('max_artifact_bytes', 33554432)
            total += len(body)
            if len(body) > maximum or total > policy(store)['max_read_bytes']:
                raise Refusal('whole report snapshot/read exceeds selected bound; original retained')
            context, path = identity(store, event['id'])
            ref = dict(event=event['id'], sha256=source['hash'], bytes=len(body), origin=context,
                       owner=store.config['roles'][event['role']]['owner'], custodian=store.config['actor'])
            existing = store.one('SELECT * FROM artifact_custody WHERE attempt=? AND path=?', (context, path))
            if existing:
                _origin(store, ref)
            else:
                meta = metadata[event['id']]
                witness = dict(sha256=ref['sha256'], size=len(body), reference=ref,
                               role=meta['role'], recipient=meta['recipient'],
                               grant=store.enrollment(meta['role'])['grant_id'], capability=store.processing.key,
                               links=_links(json.loads(meta['custody']) if meta['custody'] else None))
                # The existing origin graph guard applies to collisions too.
                guard_frozen(store, ref['sha256'], store.config['tasks'][row['task']], path)
                present = store.one('SELECT sha256 FROM artifact_blobs WHERE sha256=?', (ref['sha256'],))
                store.budget(None, (0 if present else len(body)) + len(encode(witness).encode()) + 1024)
                store.db.execute('INSERT OR IGNORE INTO artifact_blobs VALUES(?,?)', (ref['sha256'], body))
                store.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
                                 (context, path, ORIGIN_KIND, ref['owner'], encode(witness), ref['sha256']))
            result.append(ref)
        return result


def materialize(store, row, attempt):
    """Return approved frozen paths, never canonical files or journal paths."""
    from .custody import frozen_body, materialize as freeze_inputs, read_file
    roots = inputs(store, row)
    with admitted(store, row) as (_, origins, metadata):
        refs = [w['reference'] for _, w in origins] + roots
        token = _admitted.set((id(store), frozenset(metadata) | {r['event'] for r in roots}))
        try:
            witnesses, seen = [], set()
            for ref in refs:
                if ref['event'] in seen:
                    continue
                seen.add(ref['event'])
                origin, witness = _origin(store, ref)
                frozen = frozen_body(store, origin['sha256'], store.config['tasks'][row['task']], origin['path'])
                if (not frozen or len(frozen['body']) != ref['bytes']
                        or hashlib.sha256(frozen['body']).hexdigest() != ref['sha256']):
                    raise Refusal('whole canonical report blob missing or changed')
                original = json.loads(frozen['body'])
                if original.get('id') != ref['event'] or digest(original) != ref['sha256']:
                    raise Refusal('report body origin identity contradiction')
                witnesses.append(dict(path=origin['path'], sha256=ref['sha256'], size=ref['bytes'],
                                      custody='artifact_blobs', source_context=origin['attempt'], report_origin=ref))
            from .custody import safe_path
            root = store.home/'artifacts'/attempt
            safe_path(str(root), [str(store.home/'artifacts')])
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            material = freeze_inputs(store, [{'artifact_witnesses': witnesses}], attempt, store.config['tasks'][row['task']])
            # Existing copies are also authenticated; descriptor fit proves no read.
            for item in material:
                data, _ = read_file(Path(item['frozen_path']), item['size'])
                if len(data) != item['size'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                    raise Refusal('approved report materialization changed')
            return dict(version=VERSION, sources=roots, frozen_inputs=material,
                        duty='Read every whole current canonical event and every required linked origin; underlying artifact paths remain reference-only.')
        finally:
            _admitted.reset(token)


def validate_read(store, row, result, refs):
    if len(encode(result).encode()) > policy(store)['max_model_bytes']:
        raise Refusal('new model result exceeds explicit reference-mode allowance; original retained')
    reads = [f for f in result.get('findings', []) if isinstance(f, dict) and f.get('kind') == READ_KIND]
    pins = [dict(event=r['event'], sha256=r['sha256']) for r in refs]
    if not reads or set(reads[-1]) != {'kind', 'sources', 'closure', 'limits'} or encode(reads[-1]['sources']) != encode(pins):
        raise Refusal('honest whole current-input and reference-closure read declaration required')
    read = reads[-1]
    if (read['closure'] not in {'whole', 'partial', 'unread'} or not isinstance(read['limits'], list)
            or any(not isinstance(v, str) or not v for v in read['limits'])
            or read['closure'] != 'whole' and (result['semantic'] == 'DONE' or not read['limits'])):
        raise Refusal('unread/partial reference closure cannot become DONE')


def charge_transport(store, row, value):
    if active(store, row) and len(encode(value).encode()) > store.config['limits']['max_result_bytes']:
        raise Refusal('actual report response/handoff/failure wrapper exceeds selected transport budget; original retained')


def origin_pinned(store, event):
    # Conservative durable pin: no new deletion or release mechanism. Existing
    # parent/member chains and their entire cohort remain intact while recorded.
    context, path = identity(store, event)
    return bool(store.one('SELECT path FROM artifact_custody WHERE attempt=? AND path=? AND kind=?',
                          (context, path, ORIGIN_KIND)))
