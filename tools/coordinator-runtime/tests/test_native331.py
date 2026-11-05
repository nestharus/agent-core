"""Offline public-contract fixtures, never native/provider/root encounters.

/public/caller.py is the exact installed public producer mounted read-only.
Only its parsers and pure receipt/turn readers run. The subprocess below is a
fictional writer of public-shaped files, with non-UUID protocol labels. It never
calls a front door, socket, adapter, account, model or platform store.
"""
import asyncio
from contextlib import asynccontextmanager
import copy
import json
import os
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace
import unittest

from coordinator_runtime import reviews
from coordinator_runtime.contracts import Refusal, encode

PUBLIC = runpy.run_path('/public/caller.py', run_name='public_contract_fixture')

# This invokes public pure functions, not public main/Call.run/Attached.connect.
WRITER = '''#!/usr/bin/python3
import json, os, pathlib, runpy, sys
p=runpy.run_path('/public/caller.py',run_name='fictional_producer_contract')
opening='--root' not in sys.argv
args=p['parse_args'](sys.argv[1:]) if opening else p['parse_live_args'](sys.argv[1:])
out=pathlib.Path(args.out);out.mkdir()
(out/'argv.json').write_text(json.dumps(sys.argv[1:]))
run='fictional-protocol-run-not-native'
if opening:
 request,public=p['build_request'](args,0)
 (out/'request.public.json').write_text(json.dumps(public))
 handle=pathlib.Path(args.live_handle)
 handle.write_text(json.dumps({'v':1,'uid':os.getuid(),'run':run,'socket':'/fixtures/unused-fictional.sock','token':'fictional-no-credential'}))
 handle.chmod(0o600)
else:
 handle=pathlib.Path(args.root)
 p['check_handle'](json.loads(handle.read_text()))
base={'run':run,'handle':str(handle)}
if not opening and args.close:
 owner={'event':'terminal','status':'closed','async':{'accepted':0,'turn_ended':0,'owed':0,'undelivered':[]}}
 terminal={'frontdoor':'terminal','run':run,'exit':87,'entry_status':87,'killed':False,
 'retire':{'ok':True,'stop':'collected'},'live':{'backlog_dropped_total':0},
 'account_events':[owner,{'entry':'terminal','relay':'complete'}],'account_errors':[]}
 collection={'eof':True,'errors':[]}
 account=p['live_close_account'](terminal,[])
 cls=p['end_class'](terminal,account,collection,'close')
 result={**base,'class':cls,'root':p['root_end'](terminal),'physical_close':True,
 'front_door_terminal':terminal,'collection':collection,'owner_terminal':account['owner_terminal'],
 'async':account['async'],'account_errors':account['errors']}
else:
 index=0 if opening else 1
 ref=None if opening else 'fictional-correlator'
 events=[] if opening else [{'event':'follow-up-admitted','input':index,'ref':ref}]
 events += [{'event':'ack','index':index,'message_id':'fictional-message'},
 {'event':'agent-message','input':index,'parent_message_id':'fictional-message','text':'fictional complete answer'},
 {'event':'turn-end','input':index,'stop_reason':'end_turn'}]
 attached=p['Attached'].__new__(p['Attached']); iterator=iter(events)
 attached.next_event=lambda until:next(iterator,None)
 attached.eof=False;attached.signals=[]
 turn,text=attached.turn(0 if opening else None,ref,0)
 cls=p['turn_class'](turn,text)
 (out/'final.md').write_text(text)
 result={**base,'class':cls,'turn':turn,'transport':{'errors':[],
 'attached':{'frontdoor':'attached','run':run,'backlog_dropped_total':0}},
 'root':'live (detached; this exit is not the root end)'}
 if opening:result['collection']={'stdout_eof':True,'stderr_eof':True,'exit':0,'errors':[]}
(out/'result.json').write_text(json.dumps(result))
print('fictional caller stdout',flush=True)
print('fictional caller stderr',file=sys.stderr,flush=True)
sys.exit(p['LIVE_EXITS'][cls])
'''


class PublicBoundary(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.area=Path(tempfile.mkdtemp(dir='/fixtures',prefix='native331-'))
        self.writer=self.area/'fictional-caller';self.writer.write_text(WRITER);self.writer.chmod(0o700)
        self.policy={'caller':str(self.writer),'caller_sha256':reviews.sha(self.writer.read_bytes()),
                     'routes':{None:'fictional-declared-route'},'deadline':60}
        self.context={'handle':str(self.area/'fictional-handle'),'run':None,'profile':None,
                      'route':'fictional-declared-route','created':1000.}
        self.started=[]
        @asynccontextmanager
        async def admission(profile):
            self.assertIsNone(profile);yield
        class DB:
            def execute(inner,*args):pass
        @asynccontextmanager
        async def unused():yield
        from contextlib import nullcontext
        self.runtime=SimpleNamespace(config={'deadlines':{'shutdown':2},'limits':{'max_result_bytes':262144}},
            execution_pool=SimpleNamespace(admission=admission),controller='fictional-local-collector',
            authorize_launch=lambda attempt:None,tx=nullcontext,db=DB(),clock=lambda:1000.,
            attempt=lambda attempt:{'begin':1},begin=lambda *a:self.started.append(a))

    async def call(self,name,**options):
        return await reviews.Native().call(self.runtime,'fictional-attempt',self.policy,self.context,
             self.area/name,'fictional input',['/usr/bin/true'],**options)

    async def test_real_public_parsers_open_same_handle_input_close_and_original_captures(self):
        code,r,a=await self.call('open',opening=True)
        self.assertEqual(code,0);self.assertTrue(reviews.answered(code,r,a,r['run'],opening=True))
        self.assertEqual(reviews.handle_run(self.context),r['run'])
        self.context['run']=r['run']
        code,next_r,next_a=await self.call('input')
        self.assertTrue(reviews.answered(code,next_r,next_a,r['run']))
        self.assertEqual(next_r['run'],r['run']);self.assertEqual(next_r['turn']['input'],1)
        code,close_r,a=await self.call('close',close=True)
        self.assertEqual(code,0);self.assertTrue(reviews.closed(code,close_r,r['run']))
        self.assertIsNone(a)
        for name in ('open','input','close'):
            directory=self.area/name
            self.assertEqual((directory/'caller.stdout').read_text(),'fictional caller stdout\n')
            self.assertEqual((directory/'caller.stderr').read_text(),'fictional caller stderr\n')
        request=json.loads((self.area/'open/native/request.public.json').read_text())
        self.assertEqual(request['bash'],{'allow':['/usr/bin/true']})
        argv=json.loads((self.area/'input/native/argv.json').read_text())
        self.assertEqual(argv[argv.index('--root')+1],self.context['handle'])
        self.assertNotIn('--route',argv);self.assertIn('--out',argv)
        self.assertEqual(self.started,[],'no native/session evidence fabricated by fixture')

    async def test_answer_class_and_cli_zero_cannot_replace_actual_input_account(self):
        code,r,a=await self.call('open',opening=True)
        self.assertTrue(reviews.answered(code,r,a,r['run'],opening=True))
        mutations=[('class',lambda x:x.update({'class':'acknowledged'})),
          ('missing_ack',lambda x:x['turn'].update(ack=None)),
          ('request_only',lambda x:x['turn'].update(turn_end=None)),
          ('wrong_input',lambda x:x['turn']['turn_end'].update(input=4)),
          ('child_end',lambda x:x['turn']['turn_end'].update(child='fictional-child')),
          ('not_end_turn',lambda x:x['turn']['turn_end'].update(stop_reason='max_tokens')),
          ('transport_loss',lambda x:x['transport']['attached'].update(backlog_dropped_total=1)),
          ('interrupted_input',lambda x:x['transport']['attached'].update(interrupted_records_total=1)),
          ('capture_failure',lambda x:x.update(consumer_errors=['fictional incomplete capture'])),
          ('root_ended',lambda x:x['turn'].update(root_ended={'entry_status':87})),
          ('different_run',lambda x:x.update(run='fictional-other-run'))]
        for name,mutate in mutations:
            with self.subTest(name=name):
                bad=copy.deepcopy(r);mutate(bad)
                self.assertFalse(reviews.answered(0,bad,a,r['run'],opening=True))
        self.assertFalse(reviews.answered(7,r,a,r['run'],opening=True))
        self.assertFalse(reviews.answered(0,r,None,r['run'],opening=True))
        self.assertFalse(reviews.closed(0,{'class':'closed','physical_close':True},r['run']))
        self.assertFalse(reviews.closed(0,r,r['run']))

    async def test_closed_requires_public_whole_root_account_not_wrapper_END(self):
        _,r,_=await self.call('open',opening=True);self.context['run']=r['run']
        code,r,_=await self.call('close',close=True)
        self.assertTrue(reviews.closed(code,r,self.context['run']))
        for change in [lambda x:x.update(account_errors=['missing witness']),
                       lambda x:x['async'].update(undelivered=[{'work':1,'reason':'fictional loss'}]),
                       lambda x:x['collection'].update(eof=False),
                       lambda x:x['front_door_terminal'].update(entry_status=None),
                       lambda x:x['front_door_terminal']['retire'].update(stop='unknown'),
                       lambda x:x.update(run='fictional-other-run')]:
            bad=copy.deepcopy(r);change(bad);self.assertFalse(reviews.closed(0,bad,self.context['run']))

    async def test_static_bytes_route_original_handle_and_whole_lifetime_no_fallback(self):
        await self.call('open',opening=True)
        self.context['run']=reviews.handle_run(self.context)
        original=self.writer.read_text();self.writer.write_text(original+'\n# changed\n')
        with self.assertRaisesRegex(Refusal,'caller bytes'):await self.call('changed')
        self.writer.write_text(original)
        self.policy['routes']={None:'fictional-other-route'}
        with self.assertRaisesRegex(Refusal,'route unavailable'):await self.call('route')
        self.policy['routes']={None:self.context['route']}
        self.runtime.clock=lambda:1060.
        with self.assertRaisesRegex(Refusal,'whole-root lifetime'):await self.call('expired')
        # Close drains the old ownership even after the local lifetime.
        code,r,_=await self.call('close',close=True);self.assertTrue(reviews.closed(code,r,self.context['run']))
        handle=Path(self.context['handle']);body=json.loads(handle.read_text());body['run']='fictional-other'
        handle.write_text(encode(body))
        with self.assertRaisesRegex(Refusal,'handle run'):await self.call('changed-handle',close=True)

    async def test_local_failure_retains_original_END_stdout_stderr_and_partial_answer(self):
        # A real harmless local process; its diagnostic answer is never promoted.
        self.writer.write_text("#!/usr/bin/python3\nimport sys\nprint('original failure')\nprint('original diagnostic',file=sys.stderr)\nraise SystemExit(7)\n")
        self.policy['caller_sha256']=reviews.sha(self.writer.read_bytes())
        code,r,a=await self.call('failure',opening=True)
        self.assertEqual(code,7);self.assertEqual(r['class'],'incomplete');self.assertIsNone(a)
        self.assertEqual((self.area/'failure/caller.stderr').read_text(),'original diagnostic\n')
        self.assertEqual((self.area/'failure/caller.stdout').read_text(),'original failure\n')
        self.assertFalse(Path(self.context['handle']).exists())
        self.writer.write_text('''#!/usr/bin/python3
import json,pathlib,sys
out=pathlib.Path(sys.argv[sys.argv.index('--out')+1]);out.mkdir()
(out/'result.json').write_text(json.dumps({'class':'incomplete','reason':'fictional wait-bound'}))
(out/'final.md').write_text('fictional partial original answer')
raise SystemExit(6)
''')
        self.policy['caller_sha256']=reviews.sha(self.writer.read_bytes())
        code,r,a=await self.call('partial',opening=True)
        self.assertEqual(code,6);self.assertEqual(r['class'],'incomplete')
        self.assertEqual(r['reason'],'fictional wait-bound');self.assertEqual(a,'fictional partial original answer')
        self.assertEqual(json.loads((self.area/'partial/original.json').read_text())['actual_END'],6)

    async def test_bounded_original_capture_retains_bytes_and_numeric_signal_END(self):
        self.writer.write_text("#!/usr/bin/python3\nimport os\nwhile True:os.write(1,b'x'*65536)\n")
        self.policy['caller_sha256']=reviews.sha(self.writer.read_bytes())
        code,r,a=await self.call('bounded',opening=True)
        self.assertEqual(code,-15,'actual local signal wait, not a fabricated model exit')
        self.assertIsNone(a);self.assertTrue(r['consumer_errors'])
        self.assertEqual((self.area/'bounded/caller.stdout').stat().st_size,16777216)
        self.assertEqual(json.loads((self.area/'bounded/original.json').read_text())['actual_END'],-15)

    def test_allow_file_is_public_whole_command_list_and_object_refuses(self):
        prompt=self.area/'prompt';prompt.write_text('fictional prompt')
        allow=self.area/'allow.json';allow.write_text(encode(['/usr/bin/true']))
        args=PUBLIC['parse_args'](['--route','fictional','--cwd','/tmp','--out',str(self.area/'not-created'),
              '--allow-file',str(allow),'--prompt-file',str(prompt),'--live-handle',str(self.area/'not-created-handle')])
        self.assertEqual(PUBLIC['build_request'](args,0)[0]['bash'],{'allow':['/usr/bin/true']})
        allow.write_text(encode({'allow':['/usr/bin/true']}))
        with self.assertRaises(PUBLIC['LocalRefusal']):PUBLIC['build_request'](args,0)


if __name__=='__main__':unittest.main()
