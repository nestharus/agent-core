"""Operational debt views over retained journal evidence, without new access.

Historical snapshots use retained-row references. Repeated current protocol
values can use a self-contained shared-value view with explicit placements.
Every duty and unknown/unrecognized field remains represented.
References identify exact JSON values in existing rows; they neither acquire
those rows nor authorize their acquisition. No historical row is rewritten.
"""
import copy

from .contracts import Refusal, digest, encode, parse_json


FORMAT = 'integration-evidence-ref-v1'
SHARED_FORMAT = 'integration-shared-json-v1'


def reference(table, key, column, value, path=()):
    return {'format': FORMAT, 'table': table, 'key': key, 'column': column,
            'json_path': list(path), 'sha256': digest(value),
            'encoded_bytes': len(encode(value).encode())}


def expand(reference, row):
    """Verify a row independently supplied under existing authority; no I/O.

    A missing, changed or inaccessible original is not an empty/settled duty.
    The hash covers encode(value), including original text/whitespace for an
    entire TEXT column. json_path starts inside its strictly parsed JSON value.
    """
    if (not isinstance(reference, dict) or set(reference) != {
            'format', 'table', 'key', 'column', 'json_path', 'sha256', 'encoded_bytes'}
            or reference['format'] != FORMAT
            or not isinstance(reference['key'], dict) or not reference['key']
            or not isinstance(reference['json_path'], list) or not isinstance(row, dict)
            or any(row.get(k) != v for k, v in reference['key'].items())):
        raise Refusal('exact independently authorized integration evidence row required')
    try:
        value = row[reference['column']]
        if reference['json_path']:
            value = parse_json(value)
        for part in reference['json_path']:
            value = value[part]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise Refusal('retained integration evidence unavailable; retain uncertainty') from exc
    if digest(value) != reference['sha256'] or len(encode(value).encode()) != reference['encoded_bytes']:
        raise Refusal('retained integration evidence changed; fresh observation required')
    return value


def fence_view(row, table):
    """Keep attribution/reason/closures, referencing the repeated basis only.

    Unrecognized or malformed receipt bodies stay verbatim and may refuse the
    operational bound. We do not guess which unknown material is dispensable.
    """
    key = {'job': row['job']}
    try:
        basis = parse_json(row['basis'])
        receipt = parse_json(row['receipt'])
    except (ValueError, Refusal):
        return row
    if (not isinstance(basis, dict) or not isinstance(basis.get('job'), dict)
            or not isinstance(receipt, dict) or not isinstance(receipt.get('basis'), dict)):
        return row
    # A historical inconsistency must remain visible, not just hash-different.
    result = {**row, 'basis': reference(table, key, 'basis', row['basis']),
              'basis_matches_receipt': receipt['basis'] == basis}
    result['receipt'] = {**receipt, 'basis': reference(
        table, key, 'receipt', receipt['basis'], ('basis',))}
    result['original_receipt'] = reference(table, key, 'receipt', row['receipt'])
    return result


def attempt_view(row):
    """Keep every current detail except the repeated historical window debt.

    Its target/WHY, member selection, conflict and custodian assertions remain
    visible. Its old debt is a snapshot, not today's duties; those are supplied
    by integration_debt. Frozen members/enrollment remain inline. Unexpected
    window formats stay inline rather than being silently discarded.
    """
    try:
        detail = parse_json(row['detail'])
    except (ValueError, Refusal):
        return row
    if not isinstance(detail, dict) or not isinstance(detail.get('integration_window'), dict):
        return row
    window = detail['integration_window']
    if (not isinstance(window.get('basis'), dict)
            or set(window['basis']) != {'task', 'members', 'debt', 'enrollment'}
            or not {'target', 'why', 'conflict_evidence', 'custodian_evidence'} <= set(window)):
        return row
    key = {'id': row['id']}
    view = {**window, 'basis': {**window['basis'], 'debt': reference(
        'attempts', key, 'detail', window['basis']['debt'], ('integration_window', 'basis', 'debt'))}}
    return {**row, 'detail': {**detail, 'integration_window': view},
            'original_detail': reference('attempts', key, 'detail', row['detail'])}


def _at(value, path):
    for part in path:
        value = value[part]
    return value


def _shared_pack(value, paths, shared):
    """Null placeholders are interpreted only at explicitly recorded paths.

    This avoids confusing an unfamiliar original object with a reference token.
    Parent occurrences dominate their children without erasing either meaning.
    """
    result, references = copy.deepcopy(value), []
    for path in sorted(paths, key=len):
        if any(path[:len(r['json_path'])] == tuple(r['json_path']) for r in references):
            continue
        try:
            original = _at(value, path)
        except (KeyError, TypeError, IndexError):
            continue
        key = digest(original)
        if key not in shared:
            continue
        if path:
            _at(result, path[:-1])[path[-1]] = None
        else:
            result = None
        references.append({'json_path': list(path), 'sha256': key})
    return {'format': SHARED_FORMAT, 'value': result, 'references': references}


def shared_debt_view(debt):
    """Factor known repeated protocol placements, never delivery occurrences.

    Only large values at known result/detail placements are candidates, including
    historical versions that differ from today's attempt. Unknown fields in
    them remain complete. Unrecognized payloads/fields, malformed JSON and
    noncanonical TEXT stay verbatim. Placement identifies the original column
    and path, not an assertion of semantic interchangeability or read authority.
    """
    columns, candidates, counts = [], {}, {}
    for table, fields in [('attempts', ['result', 'detail']), ('outboxes', ['payload'])]:
        for row in debt[table]:
            for column in fields:
                raw = row.get(column)
                try:
                    value = parse_json(raw) if isinstance(raw, str) else raw
                except (ValueError, Refusal):
                    continue
                if not isinstance(value, dict) or isinstance(raw, str) and encode(value) != raw:
                    continue
                paths = [(), ('prior_turn_result',)] if table == 'attempts' else [
                    ('result',), ('causal_detail',), ('causal_detail', 'prior_turn_result'),
                    ('source_result',), ('informative_failure', 'original_result'),
                    ('informative_failure', 'projection'),
                    ('informative_failure', 'projection', 'invalid_result')]
                columns.append((table, row, column, value, paths))
    for _, _, _, value, paths in columns:
        for path in paths:
            try:
                original = _at(value, path)
            except (KeyError, TypeError, IndexError):
                continue
            if not isinstance(original, dict) or len(encode(original).encode()) < 4096:
                continue
            key = digest(original)
            candidates[key] = original
            counts[key] = counts.get(key, 0) + 1
    shared = {k: v for k, v in candidates.items() if counts.get(k, 0) > 1}
    if not shared:
        return debt
    result = copy.deepcopy(debt)
    result['representation'] = 'integration-debt-v2'
    result['shared_values'] = {k: _shared_pack(v, [('prior_turn_result',)], shared)
                               for k, v in sorted(shared.items())}
    for table, row, column, value, paths in columns:
        packed = _shared_pack(value, paths, shared)
        if not packed['references']:
            continue
        original = row.get('original_' + column) or reference(table, {'id': row['id']}, column, row[column])
        packed['original_column'] = original
        next(r for r in result[table] if r['id'] == row['id'])[column] = packed
    return result


def expand_shared(view, shared_values):
    """Pure reconstruction of a represented current value; no row acquisition.

    Original TEXT/whitespace still requires independently authorized expand().
    Missing, cyclic or changed shared material refuses; it never settles a duty.
    """
    def restore(packed, active):
        if (not isinstance(packed, dict) or packed.get('format') != SHARED_FORMAT
                or not isinstance(packed.get('references'), list) or 'value' not in packed):
            raise Refusal('complete integration shared value required')
        value = copy.deepcopy(packed['value'])
        seen = []
        for occurrence in packed['references']:
            path, key = occurrence['json_path'], occurrence['sha256']
            if (not isinstance(path, list) or key in active or key not in shared_values
                    or any(path[:len(p)] == p or p[:len(path)] == path for p in seen)
                    or _at(value, path) is not None):
                raise Refusal('missing, conflicting or cyclic integration shared value')
            original = restore(shared_values[key], active | {key})
            if digest(original) != key:
                raise Refusal('integration shared value changed; fresh observation required')
            if path:
                _at(value, path[:-1])[path[-1]] = original
            else:
                value = original
            seen.append(path)
        return value

    try:
        return restore(view, set())
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise Refusal('invalid integration shared value; retain uncertainty') from exc
