"""Prospective Work/user delegation and actual software consumer receipts.

This is a separate capability from native owner grants. It does not implement
selected review launch, reconcile external effects, or migrate old journals.
"""
import json

from .contracts import Refusal, canonical_uuid, collected_task_result, digest, encode
from . import prospective

BOARD_SCHEMA = """
CREATE TABLE IF NOT EXISTS coordinator_software_grants_v1(
 grant_id TEXT PRIMARY KEY,policies TEXT NOT NULL,configuration TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS coordinator_software_deliveries_v1(
 delivery TEXT PRIMARY KEY,source_grant TEXT NOT NULL,receiver_grant TEXT NOT NULL,
 event TEXT NOT NULL,payload TEXT NOT NULL);
"""


def report_routes(runtime, job, answer):
    """Existing reporting edges only; qualification and execution are separate."""
    from .contracts import response_tasks
    source = runtime.config['tasks'][job['task']]
    routes = response_tasks(source, answer, runtime.config)
    edges = {('Work', 'proposer', 'Work', 'integrator'),
             ('Reviews', 'proposer', 'Reviews', 'integrator'),
             ('Reviews', 'integrator', 'Work', 'proposer'),
             ('QA', 'execution', 'QA', 'cleanup')}
    if source.get('routine_completion') or len(routes) != 1:
        return []
    return routes if all((job['role'], job['phase'], runtime.config['tasks'][t]['role'],
                         runtime.config['tasks'][t]['phase']) in edges for t in routes) else []


def collected_report(runtime, job, task):
    """Transfer a complete report with its adverse evidence, never accept effects.

    The caller must also authenticate the exact envelope and original rights.
    Incomplete collection, a held source or unsettled actual effects still fail.
    A failed captured command is evidence in a report, not missing capture.
    """
    proof = _processing(runtime, job, report_task=task)
    if proof:
        proof['meaning'] = 'collected report transfer only; findings, unknowns, effects and acceptance unchanged'
    return proof


def report_delivery(runtime, job, outbox):
    """Publish the already-created exact response to its same assigned reader.

    This is a routing intent, not an owner callback or settlement proof. Work
    requests, qualifications and arbitrary nested handoffs keep normal guards.
    """
    if outbox['kind'] != 'result' or not job['response']:
        return []
    event = runtime.event(job['response'])
    routes = report_routes(runtime, job, collected_task_result(runtime.attempt(job['active_attempt'])))
    if (not routes or json.loads(outbox['payload']) != event or event.get('kind') != 'response'
            or event.get('source_job') != job['id'] or event.get('source_attempt') != job['active_attempt']
            or event.get('source_members') != json.loads(job['members'])
            or event.get('allowed_tasks') != routes or event.get('role') != outbox['recipient']
            or outbox['event'] != event['id'] or not collected_report(runtime, job, routes[0])):
        return []
    return routes


def clean_processing(runtime, job):
    """Local processing, not descendant completion or semantic acceptance."""
    return _processing(runtime, job)


def _processing(runtime, job, report_task=None):
    if (not job['active_attempt'] or job['state'] not in {'awaiting-delivery', 'closed'}
            or job['hold_reason'] or job['effects'] not in {'none', 'reconciled'}):
        return None
    attempt = runtime.attempt(job['active_attempt'])
    from .reviews import collected_proof
    reviewed = collected_proof(runtime, job, attempt)
    if not reviewed:
        canonical_uuid(attempt['session'])
    answer = collected_task_result(attempt)
    if report_task is not None and report_task not in report_routes(runtime, job, answer):
        return None
    if report_task is not None:
        recorded = runtime.one('SELECT * FROM results WHERE attempt=?', (attempt['id'],))
        if (attempt['state'] != 'collected' or attempt['kind'] != 'task'
                or attempt['job'] != job['id'] or attempt['controller'] != job['controller']
                or not recorded or any(recorded[k] != attempt[k] for k in ('job','result','exit','capture','error'))):
            return None
    tools = json.loads(attempt['detail']).get('tool_completion', {})
    if (attempt['begin'] is None or attempt['ended'] is None or attempt['collected'] is None
            or attempt['exit'] != 0 or attempt['capture'] != 'complete' or attempt['error']
            or answer['semantic'] != 'DONE' or not (reviewed or tools.get('complete'))):
        return None
    members = json.loads(job['members'])
    if any(runtime.one('SELECT hold FROM events WHERE id=?', (m['event'],))['hold']
           or digest(runtime.event(m['event'])) != m['hash'] for m in members):
        return None
    if runtime.config['tasks'][job['task']].get('routine_completion'):
        from .readiness import assess
        assess(runtime, attempt)
    elif (report_task is None and not runtime.one("SELECT attempt FROM ordinary_runs WHERE attempt=? AND state='reconciled'", (attempt['id'],)) and
          (answer['failures'] or answer['unknowns'] or tools.get('nonzero_completions')
          or any(item.get('status') == 'failed' for item in tools.get('items', [])))):
        return None
    return {'attempt': attempt['id'], 'worker': attempt['session'], 'collector': attempt['controller'],
            'actual_end': attempt['exit'], 'result_hash': digest(answer),
            'effect_receipt': job['effect_receipt'], 'tool_completion': tools, 'selected_review': reviewed,
            'meaning': 'actual local processing; downstream duties and acceptance remain separate'}


class Software:
    def verify_input_delivery(self, runtime, event):
        """Revalidate an ordinary prospective receiver's exact persisted intent."""
        from .board import Board
        delivery = event.get('source_delivery', {})
        outbox = runtime.one('SELECT * FROM outboxes WHERE id=?', (delivery.get('id'),))
        if not outbox or not outbox['job']:
            raise Refusal('original software outbox required for receiver mapping')
        source = Board(self.config, outbox['role'])
        job = runtime.job(outbox['job'])
        source_grant = source._software_job_grant(runtime, job)
        receiver = self.software_authority(runtime, event['allowed_tasks'][0])
        if source.identity != self.identity:
            raise Refusal('receiver mapping cannot cross original Board identities')
        with self.opened() as conn:
            self._grant(conn, runtime)
            intent = conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?', (outbox['id'],)).fetchone()
            row = conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone()
            if (not row or not intent or json.loads(intent['payload']) != event
                    or intent['event'] != event['id'] or row['payload'] != outbox['payload']
                    or row['producer'] != outbox['producer'] or row['kind'] != outbox['kind']
                    or row['grant_id'] != source_grant['id'] or intent['source_grant'] != source_grant['id']
                    or intent['receiver_grant'] != receiver['id'] or delivery.get('source_grant') != source_grant['id']
                    or delivery.get('receiver_grant') != receiver['id']
                    or delivery.get('source_hash') != digest(json.loads(outbox['payload']))
                    or row['actor'] != self.config['actor'] or row['recipient'] != receiver['owner']
                    or event['recipient'] != receiver['owner'] or outbox['recipient'] != self.role):
                raise Refusal('receiver mapping needs exact original delivery/payload/grant/recipient intent')
            notice = conn.execute('SELECT * FROM notification_outbox WHERE notification_id=?', (row['notice'],)).fetchone()
            if (not notice or notice['route'] != 'managed' or notice['delivery_state'] in {'sending','ambiguous'}
                    or row['transport_started'] or self.control_receipt_status(conn, row)['pending']):
                raise Refusal('receiver mapping cannot waive original transport/control uncertainty')
        return True

    def software_policies(self):
        return {name: digest(task) for name, task in self.config['tasks'].items() if task['role'] == self.role}

    def grant_software(self, runtime, authority):
        selected = self.config.get('software_delegation')
        if not selected or authority != selected['authority']:
            raise Refusal('explicit current user/Work software delegation selection required')
        issuer = self.store.acting_session(selected['grantor'])
        # A new epoch never relabels an old event, job, collector or native duty.
        if (runtime.one('SELECT id FROM events LIMIT 1') or runtime.one('SELECT id FROM jobs LIMIT 1')
                or runtime.one('SELECT role FROM enrollments WHERE role=?', (self.role,))):
            raise Refusal('software delegation requires a new unused journal/role; retain old authority epochs')
        return self._issue_grant(runtime, authority, issuer, delivery=True, completion=True, software=True)

    def software_authority(self, runtime, task):
        with self.opened() as conn:
            grant = self._grant(conn, runtime)
            epoch = prospective.current(runtime, task)
            if epoch:
                return {**grant, 'delegated_by': epoch['selection']['grantor'], 'delegation_authority': epoch['selection']['authority'],
                        'prospective_epoch': epoch['id']}
            exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='coordinator_software_grants_v1'").fetchone()
            cap = conn.execute('SELECT * FROM coordinator_software_grants_v1 WHERE grant_id=?',
                               (grant['id'],)).fetchone() if exists else None
            selection = self.config.get('software_delegation', {})
            if (not cap or grant['issued_by'] != selection.get('grantor')
                    or grant['authority'] != selection.get('authority')
                    or cap['configuration'] != digest(self.config)
                    or json.loads(cap['policies']).get(task) != digest(self.config['tasks'][task])):
                raise Refusal('exact prospective software authority absent or changed; old duties remain owned')
            return grant

    def revoke_software(self, runtime, grant_id):
        selection = self.config.get('software_delegation', {})
        issuer = self.store.acting_session(selection.get('grantor'))
        with self.opened(settlement=True) as conn:
            with self.store.write(conn):
                grant = self._grant(conn, runtime)
                if grant['id'] != grant_id or grant['issued_by'] != issuer:
                    raise Refusal('actual software issuer can revoke only its exact prospective role grant')
                if not conn.execute('SELECT 1 FROM coordinator_software_grants_v1 WHERE grant_id=?', (grant_id,)).fetchone():
                    raise Refusal('native owner grants cannot be revoked through software delegation')
                conn.execute('UPDATE coordinator_grants_v1 SET revoked=? WHERE id=?', (self.store.utc_now(), grant_id))
        return {'revoked': grant_id, 'issued_by': issuer, 'existing_responsibilities': 'retained; no replay or receipt waiver'}

    def _software_proof(self, runtime, grant, job, admission):
        proof = {'grant_id': grant['id'], 'issued_by': grant['issued_by'], 'authority': grant['authority'],
                 'role_owner': grant['owner'], 'task_hash': digest(self.config['tasks'][job['task']]),
                 'admission_hash': digest(admission) if admission else None}
        if grant.get('prospective_epoch'):
            epoch = prospective.for_job(runtime, job)
            if not epoch or epoch['id'] != grant['prospective_epoch']:
                raise Refusal('historical jobs/members cannot inherit future authority')
            proof.update(prospective_epoch=epoch['id'], delegated_by=grant['delegated_by'],
                         delegation_authority=grant['delegation_authority'])
        return proof

    def bind_software_attempt(self, runtime, job, attempt, admission):
        # Bind the very admission used by scoped_task, not a later replacement.
        with runtime.tx():
            grant = self.software_authority(runtime, job['task'])
            current = runtime.one('SELECT * FROM admissions WHERE package=?', (job['package'],))
            if current != admission:
                raise Refusal('software admission changed while scoping the task; no launch')
            proof = self._software_proof(runtime, grant, job, admission)
            row = runtime.attempt(attempt)
            if row['controller'] != runtime.controller or row['state'] != 'reserved' or row['job'] != job['id']:
                raise Refusal('only the actual unstarted task collector can bind prospective authority')
            detail = json.loads(row['detail'])
            if 'software_authority' in detail:
                raise Refusal('do not replace a prior attempt authority epoch')
            runtime.db.execute('UPDATE attempts SET detail=? WHERE id=?',
                               (encode({**detail, 'software_authority': proof}), attempt))

    def _software_job_grant(self, runtime, job):
        grant = self.software_authority(runtime, job['task'])
        if not job['active_attempt']:
            raise Refusal('software processing has no actual attempt')
        proof = json.loads(runtime.attempt(job['active_attempt'])['detail']).get('software_authority', {})
        admission = runtime.one('SELECT * FROM admissions WHERE package=?', (job['package'],))
        if proof != self._software_proof(runtime, grant, job, admission):
            raise Refusal('software task authority/admission differs from its actual launch')
        return grant

    def prospective_handoff_event(self, runtime, delivery):
        """One future handoff identity, independent of which receiver sees it first.

        Existing native/queued events are not relabelled. This constructs intake
        only; original delivery grants, collection and settlement still apply.
        """
        if delivery['kind'] != 'work' or delivery['actor'] != self.config['actor']:
            return None
        outbox = runtime.one('SELECT * FROM outboxes WHERE id=?', (delivery['id'],))
        if not outbox or not outbox['job']:
            return None
        job = runtime.job(outbox['job'])
        epoch = prospective.for_job(runtime, job)
        if not epoch:
            return None
        proof = json.loads(runtime.attempt(job['active_attempt'])['detail']).get('software_authority', {})
        routes = epoch['policy']['software_handoffs'].get(self.role)
        if not routes or proof.get('prospective_epoch') != epoch['id']:
            return None
        grant = self.software_authority(runtime, routes[0])
        if (delivery['payload'] != outbox['payload'] or delivery['grant_id'] != proof.get('grant_id')
                or delivery['recipient'] != grant['owner'] or outbox['recipient'] != self.role):
            raise Refusal('prospective handoff must retain exact source delivery and receiver')
        payload = json.loads(outbox['payload'])
        return {'id': digest({'software_delivery': delivery['id'], 'receiver_grant': grant['id']}),
                'role': self.role, 'recipient': grant['owner'], 'kind': 'response',
                'author': outbox['producer'], 'body': payload, 'package': payload.get('package') or payload.get('ref'),
                'allowed_tasks': routes, 'parent': outbox['event'], 'notice': None, 'board_id': None, 'grant': None,
                'source_delivery': {'id': delivery['id'], 'post': delivery['post'], 'notice': delivery['notice'],
                                    'source_grant': delivery['grant_id'], 'receiver_grant': grant['id'],
                                    'source_hash': digest(payload)}}

    def software_delivery(self, runtime, outbox, boards):
        """Return True only for a prospectively delegated routine software duty.

        A posted receiver intent survives a crash before local ingest. Settlement
        requires the frozen receiving job's actual collected processing and known
        effects; neither enqueue nor classification is a processing receipt.
        """
        if outbox['kind'] not in {'work', 'result'} or not outbox['job']:
            return False
        job = runtime.job(outbox['job'])
        if not self.config.get('software_delegation') and not json.loads(runtime.attempt(job['active_attempt'])['detail']).get('software_authority'):
            return False
        grant = self._software_job_grant(runtime, job)
        clean = clean_processing(runtime, job)
        report = report_delivery(runtime, job, outbox) if not clean else []
        if not clean and not report:
            return False
        if clean and outbox['recipient'] == self.role and outbox['kind'] == 'result':
            # Existing callback does real collection. Do not mint a new native
            # receive duty; any already recorded control duty is still reported.
            return self.complete_own_delivery(runtime, outbox) is not None
        epoch = prospective.for_job(runtime, job)
        policy = epoch['policy'] if epoch else self.config['tasks'][job['task']]
        if report and outbox['recipient'] != self.role and set(report) - set(policy.get('software_handoffs', {}).get(outbox['recipient'], [])):
            return False  # Reporting cannot create cross-role software handoff rights.
        routes = report or policy.get('software_handoffs', {}).get(outbox['recipient'])
        receiver = boards.get(outbox['recipient'])
        if not routes or not receiver:
            return False
        receive_grant = receiver.software_authority(runtime, routes[0])
        if self.identity != receiver.identity:
            raise Refusal('software handoff needs the same exact admitted board; no cross-board receipt borrowing')
        with self.opened() as conn:
            with self.store.write(conn):
                self._delivery_grant(conn, runtime, outbox)
                if receiver._grant(conn, runtime)['id'] != receive_grant['id']:
                    raise Refusal('receiver grant changed before software intake')
                row = conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone()
                if (not row or row['grant_id'] != grant['id'] or row['payload'] != outbox['payload']
                        or row['actor'] != self.config['actor'] or row['recipient'] != receive_grant['owner']):
                    raise Refusal('software consumer must retain exact addressed source and authority')
                notice = conn.execute('SELECT * FROM notification_outbox WHERE notification_id=?', (row['notice'],)).fetchone()
                if notice['route'] != 'managed' or notice['delivery_state'] in {'sending', 'ambiguous'} or row['transport_started']:
                    raise Refusal('software cannot consume another transport or waive an unsettled send')
                prior = conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?', (row['id'],)).fetchone()
                if prior:
                    if prior['source_grant'] != grant['id'] or prior['receiver_grant'] != receive_grant['id']:
                        raise Refusal('software receiver epoch changed; retain original intent')
                    event = json.loads(prior['payload'])
                else:
                    payload = json.loads(outbox['payload'])
                    internal = runtime.event(job['response']) if job['response'] else None
                    if (outbox['kind'] == 'result' and internal and internal.get('kind') == 'response'
                            and internal.get('role') == receiver.role and internal.get('source_job') == job['id']
                            and internal.get('source_attempt') == job['active_attempt']
                            and payload.get('source_result') == internal['body']
                            and payload.get('original_handoff') in internal['body'].get('handoffs', [])):
                        # The full result already includes this exact handoff.
                        # Its board receipt and published response share ONE
                        # receiving job, without dropping either source outbox.
                        payload = internal
                    # _response already creates this exact event. Reuse it,
                    # avoiding two instances for one published internal result.
                    if payload.get('kind') == 'response' and runtime.one('SELECT id FROM events WHERE id=?', (payload.get('id'),)):
                        event = runtime.event(payload['id'])
                        if event != payload or event['role'] != receiver.role or set(event['allowed_tasks']) - set(routes):
                            raise Refusal('published response differs from selected receiver routes/source')
                    elif epoch and outbox['kind'] == 'work':
                        event = receiver.prospective_handoff_event(runtime, row)
                        if event is None:
                            raise Refusal('prospective handoff identity unavailable; retain original duty')
                    else:
                        event = {'id': digest({'software_delivery': row['id'], 'receiver_grant': receive_grant['id']}),
                                 'role': receiver.role, 'recipient': receive_grant['owner'], 'kind': 'response',
                                 'author': outbox['producer'], 'body': payload, 'package': payload.get('package') or payload.get('ref'),
                                 'allowed_tasks': routes, 'parent': outbox['event'], 'notice': None, 'board_id': None, 'grant': None,
                                 'source_delivery': {'id': row['id'], 'post': row['post'], 'notice': row['notice'],
                                                     'source_grant': grant['id'], 'receiver_grant': receive_grant['id'],
                                                     'source_hash': digest(payload)}}
                    if (runtime.processing and event.get('source_delivery')
                            and not runtime.one('SELECT id FROM events WHERE id=?', (event['id'],))):
                        # Mark only a newly constructed receiving source. A
                        # retained published response keeps its original bytes.
                        event = {**event, 'processing_capability': runtime.processing.key}
                    conn.execute('INSERT INTO coordinator_software_deliveries_v1 VALUES(?,?,?,?,?)',
                                 (row['id'], grant['id'], receive_grant['id'], event['id'], encode(event)))
        runtime.ingest(event)  # Exact intent retries only; never re-execute a result.
        if runtime.processing:
            with runtime.tx():
                link = runtime.one('SELECT event FROM processing_delivery_links WHERE delivery=?', (outbox['id'],))
                if link and link['event'] != event['id']:
                    raise Refusal('original delivery already belongs to a different whole consumer')
                runtime.db.execute('INSERT OR IGNORE INTO processing_delivery_links VALUES(?,?)', (outbox['id'], event['id']))
        state = runtime.one('SELECT * FROM events WHERE id=?', (event['id'],))
        queue = runtime.one('SELECT * FROM queue WHERE event=?', (event['id'],))
        if not state['classification'] or not queue or state['hold']:
            return True
        classifier = runtime.attempt(state['classifier'])
        canonical_uuid(classifier['session'])
        if (classifier['exit'] != 0 or classifier['capture'] != 'complete' or not classifier['collected']
                or classifier['begin'] is None or classifier['ended'] is None
                or json.loads(classifier['binding']) != self.config['classifier']['binding'] or classifier['error']):
            raise Refusal('software pickup needs actual fresh Luna LOW collection and durable queue')
        proof = {'actor': self.config['actor'], 'issued_by': receive_grant['issued_by'], 'authority': receive_grant['authority'],
                 'prospective_epoch': receive_grant.get('prospective_epoch'),
                 'delegated_by': receive_grant.get('delegated_by'), 'delegation_authority': receive_grant.get('delegation_authority'),
                 'source_grant': grant['id'], 'receiver_grant': receive_grant['id'], 'recipient': receive_grant['owner'],
                 'event': event['id'], 'event_hash': digest(event), 'classifier': classifier['id'], 'queue': queue['id'],
                 'native_receipt': False, 'genuine_owner_full_read': False}
        processed = None
        if queue['job'] and runtime.job(queue['job'])['active_attempt']:
            consumer = runtime.job(queue['job'])
            receiver._software_job_grant(runtime, consumer)
            if consumer['task'] not in routes or not any(m['event'] == event['id'] and m['hash'] == digest(event)
                                                        for m in json.loads(consumer['members'])):
                raise Refusal('receiver did not process this exact frozen source under the selected route')
            processed = clean_processing(runtime, consumer)
            if processed and runtime.processing:
                from .frontier import delivery
                if not delivery(runtime, outbox['id'])['complete']:
                    processed = None  # Delivery cannot outrun the whole receiving chain.
            if processed:
                proof.update(consumer_job=consumer['id'], processing=processed)
        with self.opened() as conn:
            with self.store.write(conn):
                self._delivery_grant(conn, runtime, outbox)
                if receiver._grant(conn, runtime)['id'] != receive_grant['id']:
                    raise Refusal('receiver grant changed before software receipt')
                row = conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone()
                notice = conn.execute('SELECT * FROM notification_outbox WHERE notification_id=?', (row['notice'],)).fetchone()
                if (notice['route'] != 'managed' or notice['delivery_state'] in {'sending', 'ambiguous'}
                        or row['transport_started']):
                    raise Refusal('software receipt cannot replace an attempted foreign send')
                if not row['pickup']:
                    conn.execute("UPDATE coordinator_deliveries_v1 SET pickup=?,state='picked-up' WHERE id=?", (encode(proof), row['id']))
                if processed and not row['settlement']:
                    conn.execute("UPDATE coordinator_deliveries_v1 SET processing=?,settlement=?,processed_at=?,state='settled' WHERE id=?",
                                 (encode(proof), encode(proof), runtime.clock(), row['id']))
                stamp = self.store.utc_now()
                conn.execute("UPDATE notification_outbox SET delivery_state='acknowledged',acknowledged_at=COALESCE(acknowledged_at,?),state_changed_at=? WHERE notification_id=?",
                             (stamp, stamp, row['notice']))
        return True
