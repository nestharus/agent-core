"""Consumer-owned policy publications; shared code never interprets policy credit.

Declared roles: orchestration, validator, mapper.
"""
from contextlib import closing
import json

import inspection_store as store
from inspection_view import metadata
from runtime import connect, exclusive, fields, require, text


def validate(value):
    fields(value, ('source', 'revision', 'run_id', 'status', 'owner', 'basis', 'detail'))
    for key in ('source', 'run_id', 'owner'):
        text(value[key])
    require(type(value['revision']) is int and value['revision'] > 0, 'positive policy revision required')
    require(value['status'] in ('current', 'blocked', 'pending', 'complete', 'unknown'), 'invalid publication status')
    require(isinstance(value['basis'], dict) and isinstance(value['detail'], dict), 'policy basis/detail objects required')


def publish(directory, value):
    validate(value)
    with exclusive(directory):
        return publish_connected(directory, value)


def publish_connected(directory, value):
    with closing(connect(directory)) as db:
        return publish_owned(db, value)


def publish_owned(db, value):
    db.execute('BEGIN IMMEDIATE')
    _, _, _, current = metadata(db)
    require(value['run_id'] == current['run_id'], 'foreign policy publication')
    source = 'policy:' + value['source']
    prior = db.execute('SELECT reference,detail,sequence FROM inspection_events WHERE source=? ORDER BY sequence DESC LIMIT 1',
                       (source,)).fetchone()
    if prior and int(prior[0]) == value['revision']:
        require(json.loads(prior[1]) == value, 'policy revision already bound to different publication')
        return dict(sequence=prior[2], outcome='already_published')
    require(value['revision'] == (int(prior[0]) + 1 if prior else 1), 'policy revision gap or stale publication')
    summary = {key: value[key] for key in ('source', 'revision', 'status', 'owner')}
    summary['meaning'] = 'consumer assertion; shared provider grants no qualification or effects'
    sequence = store.append(db, source, value['revision'], summary, value)
    db.commit()
    return dict(sequence=sequence, outcome='published')
