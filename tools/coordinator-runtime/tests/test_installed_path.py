"""Q3-01/02 safe counterexample regressions; never launch installed app-server."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, enrolled, event, queued
from coordinator_runtime import storage, custody
from coordinator_runtime.appserver import AppServer, environment, metadata
from coordinator_runtime.contracts import Refusal, validate_config
from coordinator_runtime.store import owned_bytes


class InstalledPath(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='correction4-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.config=config_at(self.home)
        self.config['session_storage']={'mode':'producer-owned'}
        self.store=enrolled(self.config)
        self.addCleanup(self.store.close)
        queued(self.store,event(self.config))
        self.job=self.store.reserve()
        self.attempt=self.store.start_job(self.job['id'],self.job['token'])

    def metadata_cli(self, fail=False):
        # Actual subprocess diagnostic models the collected installed rejection.
        # All settings and identities are synthetic. App-server is NEVER started.
        script=self.home/'metadata-cli'
        body='''import sys,json
from pathlib import Path
args=sys.argv[1:]
with Path(__file__).with_suffix('.calls').open('a') as out:out.write(json.dumps(args)+'\\n')
if '--version' in args:print('codex-cli 0.166.0')
elif 'mcp' in args:
 if '--strict-config' in args or FAIL:sys.exit(1)
 names=['selected_server','injected_server']
 if 'mcp_servers.openaiDeveloperDocs.enabled=false' in args:names+=['openaiDeveloperDocs']
 print(json.dumps([{'name':n,'enabled':('mcp_servers.'+n+'.enabled=false') not in args} for n in names]))
elif 'features' in args:print('multi_agent stable '+('false' if 'features.multi_agent=false' in args else 'true'))
else:sys.exit(97)
'''.replace('FAIL',str(fail))
        script.write_text('#!'+sys.executable+'\n'+body)
        script.chmod(0o700)
        self.config['codex']=str(script)
        return script

    async def test_command_specific_flags_preserve_all_effective_MCP_and_runtime_strictness(self):
        script=self.metadata_cli()
        settings=storage.prepare(self.store,self.attempt)
        argv,facts=await AppServer(self.config).command('.codex3',storage.flags(settings),str(self.home))
        calls=[json.loads(x) for x in script.with_suffix('.calls').read_text().splitlines()]
        self.assertGreaterEqual(sum('mcp' in c for c in calls),2)
        self.assertTrue(all('--strict-config' not in c for c in calls))
        self.assertEqual(calls[0],['--version'])
        self.assertEqual(argv[argv.index('app-server')+1],'--strict-config')
        for name in ['selected_server','injected_server','openaiDeveloperDocs']:
            self.assertIn('mcp_servers.'+name+'.enabled=false',argv)
        self.assertEqual(facts['mcp'],'all-effective-disabled')
        self.assertEqual(facts['delegation_capability'],'not-established')
        self.assertNotIn('sqlite_home',' '.join(argv))
        self.assertNotIn('log_dir',' '.join(argv))

    async def test_metadata_reads_split_output_to_EOF_with_a_byte_bound(self):
        output=await metadata([sys.executable,'-c',
            "import sys,time;sys.stdout.write('first\\n');sys.stdout.flush();time.sleep(.08);print('last')"],
            {'PATH':os.environ['PATH']},cwd=str(self.home))
        self.assertEqual(output,'first\nlast\n')
        with self.assertRaisesRegex(Refusal,'bounded input'):
            await metadata([sys.executable,'-c',"print('x'*4096)"],{'PATH':os.environ['PATH']},limit=100,cwd=str(self.home))

    async def test_actual_metadata_failure_retains_exit_and_proved_no_start_not_capacity(self):
        self.metadata_cli(fail=True)
        answer=await AppServer(self.config).run(self.store,self.attempt,'synthetic',self.config['tasks']['work-integrator'])
        self.assertEqual(answer['detail']['metadata_failure'],{'command_kind':'MCP','exit':1,'model_started':False})
        self.assertIsNone(answer['exit'])
        self.assertEqual(answer['capture'],'not-started')
        self.assertEqual(answer['cleanup'],'no-session-created')
        self.assertFalse(answer['detail']['capacity_error'])
        self.assertEqual(answer['detail']['session_residuals']['state'],'no-runtime-start')
        self.assertIsNone(self.store.attempt(self.attempt)['begin'])
        self.assertIsNone(self.store.attempt(self.attempt)['ended'])
        self.assertFalse((self.store.home/'sessions').exists())

    def test_allocated_mode_is_explicitly_refused_not_silently_migrated(self):
        self.config['session_storage']={'mode':'owned-attempt'}
        with self.assertRaisesRegex(Refusal,'logical ownership'):validate_config(self.config)
        with self.assertRaisesRegex(Refusal,'foreign records'):storage.prepare(self.store,self.attempt)
        self.assertFalse((self.store.home/'sessions').exists())

    def test_usage_excludes_legacy_namespace_before_stat_or_traversal(self):
        path=self.store.home/'sessions';path.mkdir()
        (path/'unread-placeholder').write_text('not a runtime-owned logical record')
        original=os.scandir
        class Entry:
            def __init__(self,entry):self.entry=entry
            def __getattr__(self,key):return getattr(self.entry,key)
            def stat(self,**kw):
                if self.entry.name=='sessions':raise AssertionError('opaque entry stat attempted')
                return self.entry.stat(**kw)
        class Scan:
            def __init__(self,where):
                if Path(where)==path:raise AssertionError('opaque traversal attempted')
                self.scan=original(where)
            def __enter__(self):return self
            def __iter__(self):return (Entry(e) for e in self.scan)
            def __exit__(self,*args):self.scan.close()
        with patch('coordinator_runtime.store.os.scandir',Scan):
            self.assertGreater(owned_bytes(self.store.home,50000),0)
            self.assertIn('opaque/unmeasured',self.store.usage()['excluded_codex_store_scope'])

    def test_auxiliary_report_is_refused_before_any_path_metadata(self):
        with patch('coordinator_runtime.custody.safe_path',side_effect=AssertionError('metadata boundary reached')):
            with self.assertRaisesRegex(Refusal,'auxiliary stores'):
                custody.capture(self.store,self.attempt,str(self.store.home/'sessions'/'foreign'),self.config['tasks']['work-integrator'])

    def test_capture_settings_echo_never_proves_logical_ownership(self):
        settings=storage.prepare(self.store,self.attempt)
        storage.verify(self.store,self.attempt,settings,{'config':settings})
        self.assertEqual(self.store.rows('SELECT * FROM attempt_storage'),[])
        self.assertFalse((self.store.home/'sessions').exists())
        self.assertEqual(settings,{'history':{'persistence':'none'},'feedback':{'enabled':False},'features':{'shell_snapshot':False}})
        changed={**settings,'feedback':{'enabled':True}}
        with self.assertRaisesRegex(Refusal,'effective producer setting'):storage.verify(self.store,self.attempt,settings,{'config':changed})

    def test_account_identity_unchanged_no_inherited_session_impersonation(self):
        with patch.dict(os.environ,{'CODEX_SESSION_ID':'foreign','CODEX_THREAD_ID':'foreign'}):
            selected=environment('.codex3')
        self.assertEqual(selected['CODEX_HOME'],str(Path.home()/'.codex3'))
        self.assertNotIn('CODEX_SESSION_ID',selected)
        self.assertNotIn('CODEX_THREAD_ID',selected)
