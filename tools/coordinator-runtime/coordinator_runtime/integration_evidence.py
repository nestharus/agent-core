"""Operational debt views over retained journal evidence, without new access.

Only redundant historical snapshots are referenced. Current duty fields and
all other attempt detail remain inline, including unknown/unrecognized fields.
References identify exact JSON values in existing rows; they neither acquire
those rows nor authorize their acquisition. No historical row is rewritten.
"""
from .contracts import Refusal, digest, encode, parse_json


FORMAT = 'integration-evidence-ref-v1'


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
