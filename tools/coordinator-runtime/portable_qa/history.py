"""Validate caller-supplied public history, preserving absence without a hash.

Declared roles: validator, mapper.
The preparer authenticates Git origin and absence outside this offline adapter.
"""
from common import require, verify_pin

OLD_COMMIT = '70425363481033cbcd9efb2caa190ca28140d444'


def historical_record(record):
    require(record.get('commit') == OLD_COMMIT, 'exact historical fixture origin required')
    if set(record) == {'commit', 'absent'}:
        require(record['absent'] is True, 'explicit genuine historical absence required')
        return None
    require(set(record) == {'commit', 'path', 'pin'}, 'exact historical blob or absence record required')
    verify_pin(record['path'], record['pin'])
    return record['pin']['sha256']


def production_history(production, records):
    require(set(production) == set(records), 'complete old704 history or explicit absence required')
    hashes = {name: historical_record(record) for name, record in records.items()}
    return {'original': {name: value for name, value in hashes.items() if value is not None},
            'candidate': production,
            'absent': {name: records[name] for name, value in hashes.items() if value is None}}
