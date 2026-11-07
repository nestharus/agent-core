"""Controlled fake executable identity and adapter collection regressions."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import session_retirement as sr
import test_launch as lt
import test_session_retirement as rt


class IdentityTest(unittest.TestCase):
    setUp = lt.LauncherTest.setUp
    calls_readback = lt.LauncherTest.calls_readback

    def check_identity(self, relative, optin):
        a = self.root/'origin'; a.mkdir()
        if relative:
            self.bin.rename(a/'bin'); self.bin = a/'bin'
        fake = self.bin/'codex'
        fake.write_text(fake.read_text().replace('"args": args,', '"binary": os.path.realpath(__file__), "args": args,'))
        other = self.cwd/'bin'; other.mkdir()
        b = other/'codex'
        b.write_text('#!/bin/sh\nexit 89\n'); b.chmod(0o755)
        env = self.env | {'codex_binary':str(b), 'PATH':('bin' if relative else str(self.bin))+':/usr/bin:/bin'}
        extra = []
        if optin:
            receipt = dict(owner='owner',custodian='custodian',collector='collector',caller_session_id=rt.CALLER,
                account_binding='a',context_ref='c',required_closures={'processing':'owner','context':'owner'},
                hold_owners={k:'owner' for k in sr.HOLDS})
            rp = self.root/'owner.json'; rp.write_text(json.dumps(receipt))
            extra = ['--session-lifecycle','oneoff','--session-owner-receipt',str(rp)]
        result = subprocess.run([str(lt.LAUNCHER),'--profile','.codex2','--cwd',str(self.cwd),
            '--prompt',str(self.prompt),'--runs-dir',str(self.runs),'--id','identity',*extra],
            cwd=a,env=env,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        attempt = next(self.runs.iterdir())
        self.assertIn('codex_binary='+str(fake.resolve())+'\n',(attempt/'state.txt').read_text())
        calls = self.calls_readback()
        self.assertEqual(len(calls),5)
        self.assertEqual({c['binary'] for c in calls},{str(fake.resolve())})
        self.assertEqual(calls[-1]['cwd'],str(self.cwd))
        self.assertEqual(calls[-1]['args'][0],'exec')
        if optin:
            m,_,_ = sr.read(next(self.runs.iterdir()))
            self.assertEqual(m['binding']['binary'],str(fake.resolve()))
            self.assertEqual(m['binding']['binary_sha256'],hashlib.sha256(fake.read_bytes()).hexdigest())

    def test_inherited_binary_ordinary(self): self.check_identity(False,False)
    def test_inherited_binary_optin(self): self.check_identity(False,True)
    def test_relative_path_ordinary(self): self.check_identity(True,False)
    def test_relative_path_optin(self): self.check_identity(True,True)


class BadClose:
    def __init__(self, stream): self.stream = stream
    def close(self):
        self.stream.close()
        raise BrokenPipeError('controlled stdin close failure')


class CollectionTest(unittest.TestCase):
    def test_close_error_collects_exit_terminate_and_kill(self):
        for mode, expected in [('exit',17),('terminate',-signal.SIGTERM),('kill',-signal.SIGKILL)]:
            with self.subTest(mode=mode):
                code = ('import sys; sys.exit(17)' if mode=='exit' else
                    'import signal,time; '+('signal.signal(signal.SIGTERM,signal.SIG_IGN); ' if mode=='kill' else '')+
                    'print("ready",flush=True); time.sleep(30)')
                p = subprocess.Popen([sys.executable,'-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
                adapter = object.__new__(sr.Stdio); adapter.p = p
                if mode!='exit': self.assertEqual(p.stdout.readline(),b'ready\n')
                p.stdin = BadClose(p.stdin)
                try:
                    self.assertEqual(adapter.close(),expected)
                    self.assertEqual(p.returncode,expected)
                    self.assertEqual(adapter.close_error,'BrokenPipeError')
                finally:
                    if p.poll() is None: p.kill()
                    p.wait(timeout=2); p.stdout.close()


class JournalCollectionTest(rt.RetirementTest):
    # Runner selects this method only; inherited old tests are run separately once.
    def test_close_error_retains_numeric_end_and_no_replay(self):
        class CloseServer(rt.Server):
            close = sr.Stdio.close
            def __init__(self,binding):
                super().__init__(binding)
                self.p = subprocess.Popen([sys.executable,'-c','import sys;sys.exit(17)'],stdin=subprocess.PIPE)
                self.p.stdin = BadClose(self.p.stdin)
        for lost_ack in (False,True):
            if lost_ack: self.setUp()
            rt.Server.failure = lost_ack
            result = sr.retire(self.root,'owner',self.binding,rt.CURRENT,now=rt.T+86400,factory=CloseServer)
            self.assertEqual(result['state'],'possible-send' if lost_ack else 'ack')
            self.assertEqual(result['adapter_end'],17)
            self.assertEqual(result['end_failure'],'BrokenPipeError')
            self.assertEqual(sr.read(self.root)[1]['operation'],result)
            calls = len(rt.Server.calls)
            sr.retire(self.root,'owner',self.binding,rt.CURRENT,now=rt.T+86400,factory=CloseServer)
            self.assertEqual(len(rt.Server.calls),calls)
