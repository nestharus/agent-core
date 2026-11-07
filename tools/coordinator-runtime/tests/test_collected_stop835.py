"""Synthetic Work/END seams; real public release and amendment CLI processes."""
import copy
import json
from unittest.mock import patch
from test_source_amendment822 import OutsideReview
from test_qa629_repairs import actor
from coordinator_runtime import report_repair as r, processing
from coordinator_runtime.contracts import Refusal, encode, ident


class CollectedStop(OutsideReview):
    def original(self, service, end):
        key, controller = ident(), ident()
        raw=self.store.one('SELECT selection FROM processing_capabilities WHERE id=?',(self.cap,))['selection']
        self.store.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,?,?,?)',
            (key,raw,self.issuer,1000.,1001.,7))
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',(controller,key,'owned',1000.))
        if service:
            self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',
                (controller,key,'unused','serving',1000.,None,'Original failed service metadata retained'))
        receipt=dict(actual_END=end,evidence=['Synthetic independently observed SAME numeric original END '+str(end)])
        return key,controller,receipt

    def test_public_release_oneoff_and_failed_service_cli_preserves_history(self):
        originals=[self.original(False,0),self.original(True,2),self.original(True,2)]
        for key,controller,receipt in originals:
            path=self.area/('END-'+controller+'.json');path.write_text(encode(receipt))
            released=self.cli_process(['processing-release',key,'--controller',controller,'--receipt',str(path)])
            self.assertEqual(released['collection'],receipt)
        tables=('owner_lease_plans','processing_capabilities','processing_runs','service_runs','jobs',
                'attempts','events','queue','prospective_authorities','processing_source_positions')
        before={t:self.store.rows('SELECT * FROM '+t) for t in tables}
        previous=self.area/'previous835.json';previous.write_text(encode(self.previous))
        manifest=self.area/'manifest835.json';manifest.write_text(encode(self.manifest))
        args=['owner-source-amendment-basis',self.cap,'--controller',self.controller,
              '--previous',str(previous),'--manifest',str(manifest),'--purpose','Synthetic collected original stop proof835']
        for module in self.delta:args+=['--module',module]
        basis=self.cli_process(args);self.assertEqual(basis,self.cli_process(args))
        witnesses=basis['counters']['original_stop_provenance']
        for key,controller,receipt in originals:
            witness=next(w for w in witnesses if w['controller']==controller)
            self.assertEqual(witness['parent_END'],receipt)
            self.assertEqual(witness['capability'],key)
            self.assertIn('Work-collected',witness['interpretation'])
        request=self.outside(basis);path=self.area/'review835.json';path.write_text(encode(request))
        collected=self.cli_process(['collect-owner-source-review','--selection',str(path)])
        selection=self.selection(request,collected);path=self.area/'select835.json';path.write_text(encode(selection))
        args=['select-owner-source-amendment','--selection',str(path)]
        self.assertEqual(self.cli_process(args),self.cli_process(args))
        for table,rows in before.items():self.assertEqual(rows,self.store.rows('SELECT * FROM '+table),table)
        sealed=json.loads(self.store.one('SELECT request FROM owner_source_amendments')['request'])
        self.assertEqual(sealed['basis']['counters']['original_stop_provenance'],witnesses)

    def test_bad_collection_foreign_uncollected_and_live_refuse_before_bodies(self):
        key,controller,receipt=self.original(True,2)
        good=encode(dict(parent_END=receipt))
        self.store.db.execute('UPDATE processing_runs SET state=? WHERE controller=?',(good,controller))
        mutations=[('processing_runs','state','controller',controller,value) for value in
            ('owned',encode(dict(parent_END=dict(actual_END='DONE',evidence=['claim']))),
             encode(dict(parent_END=dict(actual_END=True,evidence=['claim']))),
             encode(dict(parent_END=dict(actual_END=2,evidence=[]))),
             encode(dict(parent_END=dict(actual_END=2,evidence=['']))),
             encode(dict(parent_END=dict(actual_END=0,evidence=['contradicts failed service']))))]
        mutations += [('processing_capabilities','issuer','id',key,ident()),
                      ('service_runs','state','controller',controller,'running'),
                      ('service_runs','returned','controller',controller,1002.),
                      ('attempts','collected','id',self.control_attempt,None)]
        for table,column,keycol,valuekey,value in mutations:
            old=self.store.one(f'SELECT {column} FROM {table} WHERE {keycol}=?',(valuekey,))[column]
            self.store.db.execute(f'UPDATE {table} SET {column}=? WHERE {keycol}=?',(value,valuekey))
            with self.subTest(table=table,column=column,value=value),patch.object(self.store,'event',side_effect=AssertionError('BODY')):
                with self.assertRaises(Refusal):self.basis818()
            self.store.db.execute(f'UPDATE {table} SET {column}=? WHERE {keycol}=?',(old,valuekey))
        with patch.object(self.store,'event',side_effect=AssertionError('BODY')):self.basis818()

    def test_release_contradiction_and_wrong_actor_refuse(self):
        key,controller,receipt=self.original(False,0)
        with actor(self.boards['Work'].store,self.issuer):
            first=processing.release(self.store,self.boards,key,controller,receipt)
            self.assertEqual(first,processing.release(self.store,self.boards,key,controller,receipt))
            with self.assertRaises(Refusal):processing.release(self.store,self.boards,key,controller,dict(receipt,actual_END=2))
        with actor(self.boards['Work'].store,ident()):
            with self.assertRaises(self.boards['Work'].store.UserError):processing.release(self.store,self.boards,key,controller,receipt)
        self.assertEqual(json.loads(self.store.one('SELECT state FROM processing_runs WHERE controller=?',(controller,))['state']),dict(parent_END=receipt))
