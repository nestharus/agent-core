"""C1/C2: bounded receipt diagnostics and independent surviving evidence.

Intent: root decisions.md and consequence-result.md's exact fake CLI FIFO witness.
No live providers, semantic policy oracle or historical settlement mutation.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from test_mutable_workflow_runner import setup, agent, launches, mode

ENTRY = Path(__file__).resolve().parents[1] / 'tools/mutable-workflow/inspection_cli.py'
sys.path.insert(0, str(ENTRY.parent))
import evidence_view


def cli_evidence(run, verify=False):
    options = ['--verify'] if verify else []
    result = subprocess.run([sys.executable, str(ENTRY), 'evidence', str(run), '--key', 'one', *options],
                            capture_output=True, text=True, timeout=3)
    assert result.returncode == 0, (result.stdout, result.stderr)
    return json.loads(result.stdout)


def receipt_path(log):
    return log.with_suffix(log.suffix + '.capture.json')


def historical_unchanged(run, original, report, calls):
    assert report['historical_state'] == 'returned'
    assert report['historical_application'] == original['application']
    assert report['historical_capture'] == original['capture_receipt']
    assert agent(run, 'show') == original == agent(run, 'collect')
    assert len(launches(run.parent)) == 1
    assert (run.parent / 'runner-calls.jsonl').read_bytes() == calls


def damage_receipt(path, damage):
    if damage == 'fifo':
        path.unlink()
        os.mkfifo(path)
        return
    if damage == 'directory':
        path.unlink()
        path.mkdir()
        return
    if damage == 'oversized':
        with_sparse_size(path, 1024 ** 3)
        return
    if damage == 'nested':
        path.write_bytes(b'[' * 1500 + b']' * 1500)
        return
    if damage == 'invalid_utf8':
        path.write_bytes(b'\xff')
        return
    if damage == 'malformed':
        path.write_text('{PRIVATE-MALFORMED-RECEIPT')
        return
    if damage == 'missing':
        path.unlink()


def with_sparse_size(path, size):
    with path.open('wb') as stream:
        stream.truncate(size)


@pytest.mark.parametrize('verify', [False, True])
@pytest.mark.parametrize('damage,expected', [
    ('fifo', 'unsupported_file_type'), ('directory', 'unsupported_file_type'),
    ('oversized', 'oversized'), ('nested', ('malformed', 'malformed_or_unreadable')),
    ('invalid_utf8', 'malformed_or_unreadable'), ('malformed', 'malformed_or_unreadable')])
def test_damaged_receipt_cli_completes_and_preserves_history(setup, damage, expected, verify):
    run, request = setup
    # Same successful fake edit + real evidence CLI setup as the original C1 witness.
    mode(run.parent, kind='edit', operations=[dict(op='abort')])
    original = agent(run, 'ask', request)
    calls = (run.parent / 'runner-calls.jsonl').read_bytes()
    assert cli_evidence(run)['logs'][0]['receipt'] == 'available'
    damage_receipt(receipt_path(Path(original['log'])), damage)
    report = cli_evidence(run, verify)
    diagnostics = expected if isinstance(expected, tuple) else (expected,)
    assert report['logs'][0]['receipt'] in diagnostics
    assert report['logs'][0]['availability'] == ('matches_capture' if verify else 'available_unverified')
    assert len(report['logs']) > 1 and report['logs'][1]['receipt'] == 'available'
    assert 'PRIVATE-MALFORMED-RECEIPT' not in json.dumps(report)
    historical_unchanged(run, original, report, calls)


@pytest.mark.parametrize('log_damage,availability', [
    ('missing', 'missing'), ('directory', 'unsupported_file_type'),
    ('fifo', 'unsupported_file_type'), ('external', 'restricted')])
@pytest.mark.parametrize('receipt_damage,expected', [
    ('intact', 'available'), ('missing', 'missing'), ('fifo', 'unsupported_file_type')])
def test_unusable_log_still_reports_independent_receipt(setup, log_damage, availability, receipt_damage, expected):
    run, request = setup
    original = agent(run, 'ask', request)
    calls = (run.parent / 'runner-calls.jsonl').read_bytes()
    log = Path(original['log'])
    log.unlink()
    replace_log(log, log_damage, run.parent)
    damage_receipt(receipt_path(log), receipt_damage)
    report = cli_evidence(run, verify=True)
    assert report['logs'][0]['availability'] == availability
    assert report['logs'][0]['receipt'] == expected
    assert 'EXTERNAL-PRIVATE-CANARY' not in json.dumps(report)
    historical_unchanged(run, original, report, calls)


def replace_log(log, damage, parent):
    if damage == 'directory':
        log.mkdir()
    if damage == 'fifo':
        os.mkfifo(log)
    if damage == 'external':
        external = parent / 'private-outside-run'
        external.write_text('EXTERNAL-PRIVATE-CANARY')
        log.symlink_to(external)


def test_external_receipt_is_restricted_even_when_log_missing(setup):
    run, request = setup
    original = agent(run, 'ask', request)
    log = Path(original['log'])
    log.unlink()
    receipt = receipt_path(log)
    receipt.unlink()
    external = run.parent / 'external-receipt'
    external.write_text('PRIVATE-RECEIPT-CANARY')
    receipt.symlink_to(external)
    report = cli_evidence(run)
    assert report['logs'][0]['availability'] == 'missing'
    assert report['logs'][0]['receipt'] == 'restricted'
    assert 'PRIVATE-RECEIPT-CANARY' not in json.dumps(report)


@pytest.mark.parametrize('denied', ['log', 'receipt'])
def test_permission_gap_does_not_hide_other_sample(setup, monkeypatch, denied):
    run, request = setup
    original = agent(run, 'ask', request)
    log = Path(original['log'])
    real_path_open, real_os_open = Path.open, os.open

    def log_open(path, *args, **kwargs):
        if path == log and denied == 'log':
            raise PermissionError('fixture log denied')
        return real_path_open(path, *args, **kwargs)

    def receipt_open(path, *args, **kwargs):
        if Path(path) == receipt_path(log) and denied == 'receipt':
            raise PermissionError('fixture receipt denied')
        return real_os_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', log_open)
    monkeypatch.setattr(os, 'open', receipt_open)
    report = evidence_view.evidence(run, 'one', verify=True)
    assert report['logs'][0]['availability'] == ('inaccessible' if denied == 'log' else 'matches_capture')
    assert report['logs'][0]['receipt'] == ('available' if denied == 'log' else 'inaccessible')
    assert report['historical_state'] == 'returned'


def test_valid_receipt_at_limit_and_oversized_receipt_never_read(tmp_path, monkeypatch):
    log = tmp_path / 'log'
    receipt = receipt_path(log)
    value = dict(version=1, bytes=0, sha256='0' * 64, returncode=0)
    receipt.write_bytes(json.dumps(value).encode().ljust(4096, b' '))
    assert evidence_view.receipt_status(tmp_path, log) == ('available', value)
    with_sparse_size(receipt, 1024 ** 3)

    def forbidden_read(*args):
        raise AssertionError('oversized receipt contents must not be read')

    monkeypatch.setattr(os, 'read', forbidden_read)
    assert evidence_view.receipt_status(tmp_path, log) == ('oversized', None)


def test_receipt_growth_after_size_sample_is_bounded(tmp_path, monkeypatch):
    log = tmp_path / 'log'
    receipt = receipt_path(log)
    receipt.write_bytes(b'{}')
    real_fstat, real_read = os.fstat, os.read
    reads = []

    def grow_after_sample(descriptor):
        sample = real_fstat(descriptor)
        with_sparse_size(receipt, 1024 ** 3)
        return sample

    def measured_read(descriptor, count):
        reads.append(count)
        return real_read(descriptor, count)

    monkeypatch.setattr(os, 'fstat', grow_after_sample)
    monkeypatch.setattr(os, 'read', measured_read)
    assert evidence_view.receipt_status(tmp_path, log) == ('oversized', None)
    assert reads == [4097]


def test_open_descriptor_rechecks_fifo_type_without_reading(tmp_path, monkeypatch):
    fifo = tmp_path / 'fifo'
    os.mkfifo(fifo)
    descriptor = os.open(fifo, os.O_RDONLY | os.O_NONBLOCK)

    def forbidden_read(*args):
        raise AssertionError('nonregular descriptor must not be read')

    monkeypatch.setattr(os, 'read', forbidden_read)
    try:
        assert evidence_view.read_receipt(descriptor) == ('unsupported_file_type', None)
    finally:
        os.close(descriptor)


def test_receipt_mismatch_survives_missing_log(setup):
    run, request = setup
    original = agent(run, 'ask', request)
    log = Path(original['log'])
    log.unlink()
    receipt = receipt_path(log)
    value = json.loads(receipt.read_text())
    value['bytes'] += 1
    receipt.write_text(json.dumps(value))
    result = cli_evidence(run)['logs'][0]
    assert result['availability'] == 'missing'
    assert result['receipt'] == 'mismatch_with_historical_receipt'


def test_decoder_recursion_limit_is_a_diagnostic(tmp_path, monkeypatch):
    log = tmp_path / 'log'
    receipt_path(log).write_bytes(b'{}')

    def exhausted_decoder(*args):
        raise RecursionError('fixture decoder depth exhausted')

    monkeypatch.setattr(json, 'loads', exhausted_decoder)
    assert evidence_view.receipt_status(tmp_path, log) == ('malformed_or_unreadable', None)
