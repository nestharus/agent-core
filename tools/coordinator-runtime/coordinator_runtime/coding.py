"""Normal signed coding-worker handback, including partial/failed work.

The caller supplies its actual existing branch and exact owned source paths.
Every attempt is retained; a commit failure still returns the push/readback
attempt. No force, reset, rebase, signing bypass or branch escape is available.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import selectors
import time
import os
import signal

from .contracts import Refusal, encode, regular_path, required_text


class Git:
    def __init__(self, repository, output):
        self.repository, self.output = repository, Path(output)
        self.output.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.records = []

    def run(self, *arguments):
        # Command-scoped -c settings also reach Git children (including hooks).
        # Keep ordinary hooks/signing; this handback owns no maintenance work.
        argv = ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false',
                '-C', self.repository, *arguments]
        child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        output={'stdout':bytearray(),'stderr':bytearray()}; complete=True; reason=None
        selector=selectors.DefaultSelector()
        selector.register(child.stdout,selectors.EVENT_READ,'stdout'); selector.register(child.stderr,selectors.EVENT_READ,'stderr')
        deadline=time.monotonic()+60
        try:
            while selector.get_map():
                if time.monotonic()>deadline:
                    complete=False; reason='owned Git command/capture deadline exceeded'; break
                for key,_ in selector.select(min(.1,max(0,deadline-time.monotonic()))):
                    chunk=os.read(key.fileobj.fileno(),8192)
                    if not chunk:
                        selector.unregister(key.fileobj); continue
                    room=131072-len(output[key.data])
                    output[key.data].extend(chunk[:room])
                    if len(chunk)>room:
                        complete=False; reason='owned Git command output bound exceeded'; break
                if not complete: break
            if child.poll() is None:
                try: child.wait(timeout=max(.01,deadline-time.monotonic()) if complete else .01)
                except subprocess.TimeoutExpired:
                    complete=False; reason=reason or 'owned Git command did not exit'
            if not complete:
                try: os.killpg(child.pid,signal.SIGTERM)
                except ProcessLookupError: pass  # Already exited/reaped; retain that actual END.
                try: child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try: os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                    child.wait()
        finally:
            selector.close(); child.stdout.close(); child.stderr.close()
        code=child.wait()  # This exact owned child only; numeric END retained.
        stdout,stderr=bytes(output['stdout']),bytes(output['stderr'])
        number = len(self.records)
        for kind, body in [('stdout', stdout), ('stderr', stderr)]:
            target = self.output / (str(number) + '.' + kind)
            with target.open('xb') as stream:
                stream.write(body)
            target.chmod(0o600)
        self.records.append({'argv': argv, 'actual_END': code,'capture':'complete' if complete else 'incomplete','error':reason,
                             'stdout_sha256': hashlib.sha256(stdout).hexdigest(),
                             'stderr_sha256': hashlib.sha256(stderr).hexdigest()})
        return code,stdout


def publish(repository, branch, paths, message, output, partial=False):
    required_text(branch, 'actual existing source branch', 128)
    required_text(message, 'actual handback commit message', 4000)
    if not paths or any(Path(p).is_absolute() or '..' in Path(p).parts for p in paths):
        raise Refusal('exact repository-relative owned source paths required')
    git = Git(repository, output)
    code, actual = git.run('symbolic-ref', '--quiet', '--short', 'HEAD')
    if code or actual.decode().strip() != branch:
        raise Refusal('existing exact source branch changed; preserve it without repair')
    start_code, start = git.run('rev-parse', 'HEAD')
    if start_code:
        raise Refusal('actual source head unavailable')
    errors = []
    dirty = set()
    for arguments in [('diff', '--name-only', '-z'), ('diff', '--cached', '--name-only', '-z'), ('ls-files', '--others', '--exclude-standard', '-z')]:
        code, result = git.run(*arguments)
        if code:
            errors.append('source status unavailable; commit not attempted')
        dirty |= {p.decode() for p in result.split(b'\0') if p}
    if dirty - set(paths):
        errors.append('unselected dirty source retained; cannot commit it as this worker')
    if any(r.get('capture','complete')!='complete' for r in git.records):
        errors.append('source status capture incomplete; commit not attempted')
    if not errors and dirty:
        staged, _ = git.run('add', '--', *paths)
        if staged:
            errors.append('normal staging failed')
        else:
            committed, _ = git.run('commit', '-S', '-m', message)
            if committed:
                errors.append('normal signed commit failed; original error retained')
    # Even partial/error handback attempts normal push on its existing branch.
    pushed, _ = git.run('push', 'origin', 'HEAD:refs/heads/' + branch)
    if pushed:
        errors.append('normal push failed; no fallback/force')
    metadata_code, metadata = git.run('show', '-s', '--format=%H%n%T%n%P', 'HEAD')
    verify_code, _ = git.run('verify-commit', 'HEAD')
    if metadata_code or verify_code:
        errors.append('current exact signed source readback failed')
    remote_code, remote = git.run('ls-remote', '--exit-code', 'origin', 'refs/heads/' + branch)
    lines = metadata.decode().splitlines() if not metadata_code else []
    head = lines[0] if lines else None
    remote_head = remote.decode().split()[0] if not remote_code and remote.split() else None
    if remote_code or remote_head != head:
        errors.append('exact remote branch readback failed/differs')
    for arguments in [('diff','--name-only','-z'),('diff','--cached','--name-only','-z'),('ls-files','--others','--exclude-standard','-z')]:
        code,remaining=git.run(*arguments)
        if code or remaining:
            errors.append('dirty/unpublished source remains after handback; remote equality is insufficient')
    if any(r.get('capture','complete')!='complete' for r in git.records):
        errors.append('one or more original Git command captures incomplete; inspect retained records')
    value = {'partial': partial, 'repository': repository, 'branch': branch, 'before': start.decode().strip(),
             'head': head, 'tree': lines[1] if len(lines)>1 else None, 'ALLparents': lines[2].split() if len(lines)>2 else [],
             'remote_head': remote_head, 'errors': errors, 'attempts': git.records,
             'meaning': 'actual source handback attempts; neither product acceptance nor cutover'}
    (git.output/'RESULT.json').write_text(encode(value)+'\n')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',required=True); parser.add_argument('--branch',required=True)
    parser.add_argument('--paths',nargs='+',required=True); parser.add_argument('--message',required=True)
    parser.add_argument('--output',required=True); parser.add_argument('--partial',action='store_true')
    args=parser.parse_args()
    result=publish(args.repository,args.branch,args.paths,args.message,args.output,args.partial)
    print(encode(result))
    raise SystemExit(1 if result['errors'] else 0)
