"""Selected same-inode/backup method at the four collected operational file sizes."""
import asyncio
import gzip
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from support import config_at,enrolled,event,queued,result,ident
from coordinator_runtime import routine,publication,custody


class ScaleMethod(unittest.IsolatedAsyncioTestCase):
    async def test_seven_preimages_backed_up_before_same_inode_publication(self):
        with tempfile.TemporaryDirectory(prefix='correction6-scale-') as temp:
            home=Path(temp);config=config_at(home);config['limits']['max_bytes']=536870912
            targets=[];before={};sizes=[9500000,6500000,6000000,7400000,256,256,256]
            for index,size in enumerate(sizes):
                path=home/('record-'+str(index)+'.json')
                value={'total':0,'index':index,'peer_text':'KEEP','padding':''}
                value['padding']='P'*(size-len(json.dumps(value)))
                path.write_text(json.dumps(value));self.assertEqual(path.stat().st_size,size)
                targets.append(str(path));before[str(path)]=(path.stat(),path.read_bytes())
            task=config['tasks']['work-integrator']
            task.update(effects='owner-reconcile',sandbox='workspace-write',routine_completion={'kind':'file-witness','targets':targets})
            task['effect_authority'].update(write_roots=targets,operations=['write-role-records'])
            store=enrolled(config);self.addCleanup(store.close)
            queued(store,event(config));job=store.reserve();attempt=store.start_job(job['id'],job['token'])
            (store.home/'artifacts'/attempt).mkdir(parents=True)
            class Grant:
                def completion_authority(self,*args):return {'id':'own-fixture-grant','owner':config['roles']['Work']['owner']}
            board=Grant();routine.prepare(store,board,job,attempt,task)
            mapping=publication.stages(store,attempt);manifest=home/'mapping.json';manifest.write_text(json.dumps(mapping))
            code="import json,sys;from pathlib import Path;m=json.loads(Path(sys.argv[1]).read_text());[(lambda p:(lambda v:(v.update(total=51),p.write_text(json.dumps(v))))(json.loads(p.read_text())))(Path(p)) for p in m.values()]"
            store.begin(attempt,{'fixture':'real owned Python staged producer, not a provider model'})
            store.session(attempt,ident())
            child=await asyncio.create_subprocess_exec(sys.executable,'-c',code,str(manifest))
            exit_code=await child.wait();self.assertEqual(exit_code,0)
            answer={**result(),'artifacts':list(mapping.values()),'completion':{'version':1,'local':'ready','failures':[],'unknowns':[],'tools':[]}}
            store.collect(attempt,{'result':answer,'exit':exit_code,'capture':'complete','cleanup':'done','error':None,
                'detail':{'tool_completion':{'complete':True,'items':[{'id':'synthetic-stage-command','type':'commandExecution','exit_code':0,'status':'completed','completed_notification':True}],'nonzero_completions':[]}}})
            custody.inventory(store,attempt,answer,task)
            self.assertTrue(routine.reconcile(store,board,store.job(job['id'])))
            self.assertEqual(len(store.rows('SELECT * FROM canonical_backups')),7)
            for path in targets:
                original,data=before[path];after=Path(path).stat();value=json.loads(Path(path).read_text())
                self.assertEqual((after.st_dev,after.st_ino,after.st_mode,after.st_uid,after.st_gid),
                    (original.st_dev,original.st_ino,original.st_mode,original.st_uid,original.st_gid))
                self.assertEqual(value['total'],51);self.assertEqual(value['peer_text'],'KEEP')
                self.assertEqual(value['padding'],json.loads(data)['padding'])
                backup=Path(store.one('SELECT path FROM canonical_backups WHERE target=?',(path,))['path'])
                self.assertEqual(gzip.decompress(backup.read_bytes()),data)
            self.assertTrue(all(r['state']=='published' for r in store.rows('SELECT state FROM file_publications')))
