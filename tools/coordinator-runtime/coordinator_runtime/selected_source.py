"""Explicit selected-retained-source metadata. No historical body acquisition.

A snapshot grants no read/effect/collector/recovery rights. The ordinary guards
still authenticate actual bytes, current mappings and downstream operations.
"""
import json
import re
from .contracts import Refusal

FIELDS = {'event', 'role', 'source_hash', 'source_birth', 'task', 'mapping_version'}
MODE = 'selected-retained-source-v1'


def operands(runtime, selected):
    if not isinstance(selected, list) or not 1 <= len(selected) <= 32:
        raise Refusal('finite explicit selected retained source pins required')
    seen = set()
    for pin in selected:
        if (not isinstance(pin, dict) or set(pin) != FIELDS
                or not isinstance(pin['event'], str) or not pin['event'] or pin['event'] in seen
                or not isinstance(pin['role'],str) or not isinstance(pin['task'],str)
                or pin['role'] not in runtime.config['roles'] or pin['task'] not in runtime.config['tasks']
                or runtime.config['tasks'][pin['task']]['role'] != pin['role']
                or not isinstance(pin['source_hash'], str) or not re.fullmatch('[0-9a-f]{64}', pin['source_hash'])
                or type(pin['source_birth']) is not int or pin['source_birth'] <= 0
                or type(pin['mapping_version']) is not int or pin['mapping_version'] <= 0):
            raise Refusal('exact distinct source/role/hash/birth/current task/mapping pins required')
        seen.add(pin['event'])
    return selected


def snapshot(runtime, pin):
    # Hold/exclusion first; never fetch a body, error or capture to diagnose it.
    state = runtime.one('SELECT hold IS NOT NULL AS held,processed_at,state FROM events WHERE id=?', (pin['event'],))
    if not state or state['held'] or state['processed_at'] is not None or state['state'] != 'queued':
        raise Refusal('selected retained source held/excluded/processed or not queued')
    source = runtime.one('SELECT id,role,hash FROM events WHERE id=?', (pin['event'],))
    birth = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (pin['event'],))
    queue = runtime.one('SELECT role,phase,task,package,state,job FROM queue WHERE event=?', (pin['event'],))
    # Only explicitly selected mapping metadata. Never fetch prior/error/result
    # bodies or any unrelated mapping, even for currentness or accounting.
    mapping = runtime.one("SELECT version,source_hash,actor,CASE WHEN json_valid(receipt) THEN json_extract(receipt,'$.mode') END AS mode,"
                          "CASE WHEN json_valid(receipt) THEN json_extract(receipt,'$.task') END AS task,"
                          "CASE WHEN json_valid(receipt) THEN json_extract(receipt,'$.package') END AS package,"
                          "CASE WHEN json_valid(prior) THEN json_extract(prior,'$.integration_observation.packet') END AS packet "
                          'FROM input_resolutions WHERE event=? ORDER BY version DESC LIMIT 1', (pin['event'],))
    task = runtime.config['tasks'][pin['task']]
    if (source != dict(id=pin['event'], role=pin['role'], hash=pin['source_hash'])
            or not birth or birth['position'] != pin['source_birth']
            or not queue or queue['role'] != pin['role'] or queue['task'] != pin['task']
            or queue['phase'] != task['phase'] or queue['state'] != 'queued' or queue['job'] is not None
            or not mapping or mapping['version'] != pin['mapping_version'] or mapping['source_hash'] != pin['source_hash']
            or mapping['mode'] != 'route' or mapping['task'] != pin['task'] or mapping['package'] != queue['package']
            or mapping['actor'] not in {runtime.config['roles'][pin['role']]['owner'], runtime.config['actor']}):
        raise Refusal('selected original identity/birth/task/current mapping changed or unknown')
    from .local_integration import selected as local_task
    if local_task(runtime, pin['task']):
        try:
            packet = json.loads(mapping['packet']) if mapping['packet'] else None
        except (ValueError,TypeError):
            raise Refusal('selected original mapping metadata malformed; no body diagnosis') from None
        if (not isinstance(packet, dict) or set(packet) != {'reads','writes','versions'}
                or not isinstance(packet['reads'],list) or not isinstance(packet['writes'],list)
                or not all(isinstance(k,str) for k in packet['reads']+packet['writes'])
                or not isinstance(packet['versions'],dict)
                or not all(isinstance(v,str) for v in packet['versions'].values())
                or not (packet['reads'] or packet['writes'])
                or set(packet['versions']) != set(packet['reads']) | set(packet['writes'])):
            raise Refusal('selected original known mapping required; no unknown/new relabeling')
    from .configuration import processing_tasks
    tasks = processing_tasks(runtime)
    if tasks is not None and pin['task'] not in tasks:
        raise Refusal('selected source task outside current Work configuration authority')
    return {**pin, 'id':source['id'], 'hash':source['hash'], 'queue':queue,
            'mapping':mapping, 'qualification':'recorded metadata only; actual source and current mapping guards still required'}


def selected_pins(selection):
    basis = selection.get('basis', {})
    return basis.get('selected_retained', []) if basis.get('mode') == MODE else []


def permits_original(runtime, event):
    if not runtime.processing:
        return False
    _, selection = runtime.processing.current()
    return any(p['event'] == event['id'] and p['source_hash'] == runtime.one(
        'SELECT hash FROM events WHERE id=?', (event['id'],))['hash'] and p['role'] == event['role']
        for p in selected_pins(selection))


def custody_budget(runtime, incoming):
    """Bound only this metadata registration without walking old captures.

    SQLite's aggregate allocated pages are not body
    measurements or a claim about all retained artifact residency. This grants
    no execution/allocation; ordinary total storage admission remains required
    at each subsequent real allocation/read/effect boundary.
    """
    size = runtime.db.execute('PRAGMA page_size').fetchone()[0]
    pages = runtime.db.execute('PRAGMA page_count').fetchone()[0]
    if size * pages + incoming + 4096 >= runtime.config['limits']['max_bytes']:
        raise Refusal('selected metadata authority journal capacity full; no old capture accounting')
