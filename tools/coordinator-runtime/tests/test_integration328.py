"""Joined source boundaries in private fictional Git/SQLite fixtures only.

No native/provider encounter or profile/session/turn identity is observed.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from coordinator_runtime import coding, configuration
from coordinator_runtime.contracts import Refusal, encode
import test_configuration308 as config_fixture


class JoinedConfiguration(unittest.TestCase):
    def test_risk_consumer_manifest_is_current_after_original_service_transition(self):
        f = config_fixture.CurrentConfiguration(methodName='runTest')
        self.addCleanup(f.doCleanups)
        f.setUp()
        selected = f.selection()['basis']['release']['files']
        root = Path('/src')
        expected = configuration.branch_release_sources(root)
        for source in expected:
            self.assertEqual(selected[str(source)], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertIn(str(source), f.value['tasks']['bi']['effect_authority']['read_roots'])
            self.assertNotIn(str(source), f.value['tasks']['qe']['effect_authority']['read_roots'])
        f.transition(); f.issue()
        f.runtime.processing.current()
        # Model changed consumer bytes at the acquisition seam. The transition,
        # manifest/currentness and authority validators remain production code.
        changed = f.directory/'fictional-changed-consumer.py'
        changed.write_bytes(expected[0].read_bytes()+b'\n# fictional source change\n')
        original = configuration.regular_path
        def acquire(path):
            return changed if str(path) == str(expected[0]) else original(path)
        with patch.object(configuration, 'regular_path', side_effect=acquire):
            with self.assertRaisesRegex(Refusal, 'source|release'):
                f.runtime.processing.current()
        f.runtime.processing.current()
        self.assertEqual(f.runtime.one('SELECT COUNT(*) AS n FROM events')['n'], 4)
        self.assertIsNone(f.runtime.attempt('fictional-original-attempt')['profile'])

    def test_exact_branch_sources_compose_with_prospective_cwd_capacity_and_neutral_startup(self):
        f = config_fixture.CurrentConfiguration(methodName='runTest')
        self.addCleanup(f.doCleanups)
        f.setUp()
        original = copy.deepcopy(f.runtime.config)
        grants = [tuple(r) for r in f.conn.execute('SELECT * FROM coordinator_grants_v1')]
        root = Path('/src')
        sources = [str(p) for p in configuration.branch_release_sources(root)]
        options = {'cwd': {'ri': str(f.directory/'new-report-work'/'narrow')},
                   'neutral_startup': ['bi', 'qe', 'ri'],
                   'read_roots': {'bi': [str(root/'tools/coordinator-runtime'), *sources]},
                   'capacity': {'authority': 'fictional Work prospective entitlement',
                                'evidence': 'fictional owned account', 'limits': {'max_alerts':256, 'max_alert_debt':512}}}
        value = configuration.candidate(f.runtime, str(f.directory/'joined-current.json'),
                                        ['bi', 'qe'], scope_options=options)
        configuration.validate_changes(f.runtime, value, ['bi','qe','ri'])
        self.assertEqual(value['tasks']['bi']['effect_authority']['read_roots'],options['read_roots']['bi'])
        self.assertEqual(value['tasks']['ri']['cwd'], options['cwd']['ri'])
        self.assertEqual(value['limits']['max_alert_debt'],512)
        self.assertEqual(f.runtime.config, original)
        self.assertEqual([tuple(r) for r in f.conn.execute('SELECT * FROM coordinator_grants_v1')],grants)
        self.assertNotIn('max_alert_debt',f.runtime.config['limits'])
        self.assertNotIn('/src/tools',value['tasks']['bi']['effect_authority']['read_roots'])
        self.assertEqual(value['tasks']['bi']['effect_authority']['write_roots'],
                         original['tasks']['bi']['effect_authority']['write_roots'])


class GitMaintenance(unittest.TestCase):
    def setUp(self):
        self.area=Path(tempfile.mkdtemp(dir='/fixtures',prefix='git328-'))
        self.repo=self.area/'repo';self.repo.mkdir()
        self.remote=self.area/'remote.git'
        self.command('git','init','--bare','-q',str(self.remote))
        self.git('init','-q','-b','fictional-existing')
        self.git('config','user.name','Fictional signing fixture')
        self.git('config','user.email','fixture@example.invalid')
        self.key=self.area/'key'
        self.command('ssh-keygen','-q','-t','ed25519','-N','','-f',str(self.key))
        self.trust=self.area/'allowed-signers'
        self.trust.write_text('fixture@example.invalid '+self.key.with_suffix('.pub').read_text())
        for key,value in [('gpg.format','ssh'),('user.signingkey',str(self.key)),
                          ('gpg.ssh.allowedSignersFile',str(self.trust)),('commit.gpgsign','true')]:
            self.git('config',key,value)
        self.git('remote','add','origin',str(self.remote))
        self.module=self.repo/'module.py';self.module.write_text('value = 1\n')
        self.git('add','module.py');self.git('commit','-qm','fictional signed baseline')
        self.base=self.git('rev-parse','HEAD').stdout.decode().strip()
        # Finite positive-control objects in Git's sampled loose-object bucket.
        count=0
        for value in range(10000):
            body=str(value).encode()
            oid=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
            if oid.startswith('17'):
                self.git('hash-object','-w','--stdin',input=body);count+=1
                if count==3:break
        self.assertEqual(count,3)
        for key,value in [('gc.auto','1'),('gc.autoDetach','false'),('maintenance.auto','true')]:self.git('config',key,value)
        self.marker=self.area/'auto-gc-marker'
        self.hook('pre-auto-gc','echo prohibited > '+str(self.marker)+'\nexit 1\n')

    def command(self,*argv,**kwargs):
        result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25,**kwargs)
        with (self.area/'commands.jsonl').open('a') as out:
            out.write(json.dumps({'argv':argv,'actual_END':result.returncode,
                                  'stdout':result.stdout.decode(errors='backslashreplace'),
                                  'stderr':result.stderr.decode(errors='backslashreplace')})+'\n')
        result.check_returncode();return result

    def git(self,*args,**kwargs):
        return self.command('git','-c','gc.auto=0','-c','maintenance.auto=false','-C',str(self.repo),*args,**kwargs)

    def hook(self,name,body):
        path=self.repo/'.git/hooks'/name;path.write_text('#!/bin/sh\n'+body);path.chmod(0o700)

    def publish(self,name):
        answer=coding.publish(str(self.repo),'fictional-existing',['module.py'],'fictional signed partial',self.area/name,partial=True)
        self.assertTrue(answer['partial'])
        self.assertTrue(all(type(r['actual_END']) is int for r in answer['attempts']))
        self.assertTrue(all('--force' not in r['argv'] and '--no-verify' not in r['argv'] for r in answer['attempts']))
        return answer

    def test_child_maintenance_suppressed_hooks_signing_partial_and_exact_readback(self):
        self.git('-c','gc.auto=1','-c','maintenance.auto=true','gc','--auto')
        self.assertTrue(self.marker.exists());self.marker.unlink()
        for hook in ('pre-commit','pre-push'):
            witness=self.area/hook
            self.hook(hook,'git config --get gc.auto > '+str(witness)+
                      '\ngit config --get maintenance.auto >> '+str(witness)+'\ngit gc --auto\n')
        self.module.write_text('value = 2\n');answer=self.publish('success')
        self.assertEqual(answer['errors'],[])
        for hook in ('pre-commit','pre-push'):self.assertEqual((self.area/hook).read_text(),'0\nfalse\n')
        self.assertFalse(self.marker.exists())
        self.assertEqual(answer['head'],answer['remote_head'])
        self.git('fetch','origin','refs/heads/fictional-existing:refs/remotes/origin/fictional-existing')
        self.git('verify-commit','refs/remotes/origin/fictional-existing')
        fetched=self.git('show','-s','--format=%H%n%T%n%P','refs/remotes/origin/fictional-existing').stdout.decode().splitlines()
        self.assertEqual(fetched,[answer['head'],answer['tree'],' '.join(answer['ALLparents'])])
        self.assertTrue(all(r['capture']=='complete' for r in answer['attempts']))
        # Repository policy remains enabled; suppression is command scoped.
        self.assertEqual(self.git('config','--local','--get','gc.auto').stdout,b'1\n')

    def test_hook_and_signing_errors_keep_dirty_state_and_nonforce_competition(self):
        self.module.write_text('value = 2\n');first=self.publish('first');self.assertEqual(first['errors'],[])
        self.module.write_text('value = 3\n');self.hook('pre-commit','exit 7\n')
        refused=self.publish('hook-refusal')
        self.assertEqual(refused['head'],first['head']);self.assertEqual(refused['remote_head'],first['head'])
        self.assertTrue(any('signed commit failed' in e for e in refused['errors']))
        self.assertTrue(any('dirty/unpublished' in e for e in refused['errors']))
        self.hook('pre-commit','exit 0\n');self.git('config','user.signingkey',str(self.area/'absent-signer'))
        unsigned=self.publish('signer-refusal')
        self.assertEqual(unsigned['head'],first['head']);self.assertTrue(any('signed commit failed' in e for e in unsigned['errors']))
        self.git('config','user.signingkey',str(self.key))
        # A signed sibling remote tip prevents nonforce publication.
        tree=self.git('rev-parse',first['head']+'^{tree}').stdout.decode().strip()
        sibling=self.git('commit-tree','-S',tree,'-p',first['head'],input=b'fictional competing tip\n').stdout.decode().strip()
        self.git('push','origin',sibling+':refs/heads/fictional-existing')
        competed=self.publish('nonforce-refusal')
        self.assertNotEqual(competed['head'],sibling);self.assertEqual(competed['remote_head'],sibling)
        self.assertTrue(any('normal push failed' in e for e in competed['errors']))
        self.assertTrue(any('differs' in e for e in competed['errors']))
        self.trust.write_text('')
        untrusted=self.publish('trust-refusal')
        self.assertTrue(any('signed source readback failed' in e for e in untrusted['errors']))
        self.assertFalse(self.marker.exists())

    def test_numeric_error_and_incomplete_capture_remain_observable(self):
        git=coding.Git(str(self.repo),self.area/'capture')
        code,_=git.run('-c','alias.fixture-end=!exit 19','fixture-end');self.assertEqual(code,19)
        code,body=git.run('-c','alias.fixture-bound=!/usr/bin/python3 -c \'import sys; sys.stdout.write("x"*262144)\'','fixture-bound')
        self.assertEqual(git.records[-1]['actual_END'],code)
        self.assertEqual(git.records[-1]['capture'],'incomplete')
        self.assertLessEqual(len(body),131072)
        self.assertIn('bound exceeded',git.records[-1]['error'])


if __name__=='__main__':unittest.main()
