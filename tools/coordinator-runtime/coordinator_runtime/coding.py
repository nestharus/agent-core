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

from .contracts import Refusal, encode, regular_path, required_text


class Git:
    def __init__(self, repository, output):
        self.repository, self.output = repository, Path(output)
        self.output.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.records = []

    def run(self, *arguments):
        argv = ['git', '-C', self.repository, *arguments]
        completed = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        number = len(self.records)
        for kind, body in [('stdout', completed.stdout), ('stderr', completed.stderr)]:
            target = self.output / (str(number) + '.' + kind)
            with target.open('xb') as stream:
                stream.write(body)
            target.chmod(0o600)
        self.records.append({'argv': argv, 'actual_END': completed.returncode,
                             'stdout_sha256': hashlib.sha256(completed.stdout).hexdigest(),
                             'stderr_sha256': hashlib.sha256(completed.stderr).hexdigest()})
        return completed.returncode, completed.stdout


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
