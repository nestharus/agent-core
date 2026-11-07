"""Exact legacy marker lifecycle; fictional isolated actors and collected results."""
import copy
import json
from unittest.mock import patch
from test_plain_control821 import Completion821
from coordinator_runtime import plain_control, processing
from coordinator_runtime.contracts import Refusal, digest

class Marker831(Completion821):
    def original(self, obligations=(), plain_scope=None):
        return super().original(obligations, plain_scope, control_task='@control')

    def returned(self):
        source,attempt,request,returned=super().returned()
        self.store.db.execute("UPDATE queue SET task='@unresolved' WHERE event=?",(source['id'],))
        return source,attempt,request,returned

    test_marker_existing_return_cli_terminal_once = Completion821.test_same869_shape_existing_return_cli_terminal_once_preserves_every_original
    test_marker_metadata_before_body = Completion821.test_tool_metadata_and_binding_refuse_before_protected_body
    test_marker_descendant_reservation_effect_guards = Completion821.test_pending_descendant_reserved_and_effect_consumers_refuse_before_source
    test_marker_unknown_owned_and_stale_guards = Completion821.test_unknown_message_owned_and_stale_source_pins_block
    test_marker_external_attestation = Completion821.test_current_work_external_conservation_attestation
    test_marker_automatic_scope = Completion821.test_automatic_delegated_collected_structured_scope_nonempty

    def test_marker_api_fresh_classifier_completion_replay(self):
        source,attempt,request=self.conserved()
        raw=self.store.attempt(attempt)
        first=self.apply817(source,attempt,request)
        self.assertTrue(plain_control.accepted(self.store,source['id']))
        self.assertEqual(first,self.apply817(source,attempt,request))
        self.fresh();self.runtime.receipts();self.store.complete_events()
        end=self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at']
        self.assertIsNotNone(end)
        self.assertEqual(self.store.one('SELECT state FROM queue WHERE event=?',(source['id'],))['state'],'done')
        resolution=self.store.input_resolution(source['id'])
        self.assertIsNone(resolution['receipt']['task'])
        self.assertEqual(resolution['receipt']['remaining_obligations'],json.loads(json.loads(raw['result'])['decision_json'])['remaining_obligations'])
        self.assertTrue(resolution['receipt']['remaining_obligations'])
        self.assertEqual(first,self.apply817(source,attempt,request))
        processing.apply_control(self.store,source['id'],attempt);self.store.complete_events()
        self.assertEqual(end,self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.assertEqual(resolution,self.store.input_resolution(source['id']))
        self.assertEqual(raw,self.store.attempt(attempt))
        self.assertEqual(first,self.store.one('SELECT * FROM plain_control_dispositions WHERE event=?',(source['id'],)))

    def test_marker_source_reservation_and_external_guards(self):
        source,attempt,request=self.conserved()
        for key,value in (('source_hash','0'*64),('received',-1),('result_hash','0'*64)):
            with self.subTest(key=key),patch.object(self.store,'event',side_effect=AssertionError('unqualified source body')):
                with self.assertRaises(Refusal):self.command(source,attempt,{**request,key:value})
        for table,column,value in (('events','hold','held'),('queue','job','reserved-real-job'),('queue','task','work-proposer')):
            original=self.store.one('SELECT '+column+' FROM '+table+' WHERE '+('id' if table=='events' else 'event')+'=?',(source['id'],))[column]
            sql='UPDATE '+table+' SET '+column+'=? WHERE '+('id' if table=='events' else 'event')+'=?'
            self.store.db.execute(sql,(value,source['id']))
            with self.subTest(column=column),patch.object(self.store,'event',side_effect=AssertionError('held or reserved source body')):
                with self.assertRaises(Refusal):self.command(source,attempt,request)
            self.store.db.execute(sql,(original,source['id']))
        for changed in (dict(observed=self.store.clock()-301),dict(observed=self.store.clock()+1),dict(observed='unknown'),dict(owner='unenrolled'),dict(source_hash='forged')):
            bad=copy.deepcopy(request);entry=bad['accounting'][0]
            entry.update(event='exact-external-original',source_hash='a'*64,attestation=dict(reference='Exact retained external source',observed=self.store.clock()))
            if 'observed' in changed:entry['attestation'].update(changed)
            else:entry.update(changed)
            with self.subTest(changed=changed),self.assertRaises(Refusal):self.command(source,attempt,bad)
        self.assertEqual(self.store.rows('SELECT * FROM plain_control_dispositions'),[])
