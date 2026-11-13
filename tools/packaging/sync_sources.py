"""Sync source contents; optionally keep a separate, compact Gitee history."""
import argparse
import json
from pathlib import Path
import subprocess


def git(repository, *arguments, input=None):
    return subprocess.check_output(['git', '-C', str(repository), *arguments],
                                   input=input, encoding='utf-8').strip()


def push_snapshot(repository, branch):
    source = git(repository, 'rev-parse', 'refs/heads/' + branch)
    tree = git(repository, 'rev-parse', source + '^{tree}')
    heads = git(repository, 'ls-remote', 'gitee', 'refs/heads/' + branch)
    parent = None
    if heads:
        git(repository, 'fetch', '--no-tags', 'gitee', 'refs/heads/' + branch)
        parent = git(repository, 'rev-parse', 'FETCH_HEAD')
        message = git(repository, 'show', '-s', '--format=%B', parent)
        if 'Mirror-Policy: snapshot-v1' not in message.splitlines():
            raise ValueError('Existing Gitee branch is not a snapshot mirror; refusing to replace its history.')
        if git(repository, 'rev-parse', parent + '^{tree}') == tree:
            print('Gitee source contents already match ' + source[:9], flush=True)
            return
    message = ('Sync localization source ' + source[:9] + '\n\n'
               'Source-Commit: ' + source + '\nMirror-Policy: snapshot-v1\n')
    arguments = ['commit-tree', tree]
    if parent:
        arguments.extend(['-p', parent])
    mirror = git(repository, *arguments, input=message)
    # A concurrent remote change causes a normal non-fast-forward rejection.
    # The original source commit is metadata, never a parent of this mirror.
    git(repository, 'push', 'gitee', mirror + ':refs/heads/' + branch)
    print('Gitee mirror ' + mirror[:9] + ': identical tree for source ' + source[:9], flush=True)


def sync(repository, execute=False):
    branch = 'localization'
    remotes = subprocess.check_output(['git', '-C', str(repository), 'remote'], text=True).split()
    if not all(remote in remotes for remote in ('origin', 'gitee')):
        raise ValueError('Configure both origin (GitHub) and gitee remotes first; upstream is never pushed.')
    subprocess.run(['git', '-C', str(repository), 'rev-parse', '--verify', 'refs/heads/' + branch],
                   check=True, stdout=subprocess.DEVNULL)
    policy_file = Path(repository) / 'gitee-mirror.json'
    snapshot = False
    if policy_file.exists():
        policy = json.loads(policy_file.read_text(encoding='utf-8'))
        if policy.get('history') != 'snapshot-v1':
            raise ValueError('Unknown Gitee mirror policy; refusing to push full history.')
        snapshot = True
    failures = []
    for remote in ('origin', 'gitee'):
        print(f'{remote}: ' + ('sync identical source tree with compact history'
                              if remote == 'gitee' and snapshot else f'git push {remote} {branch}'), flush=True)
        if execute:
            try:
                if remote == 'gitee' and snapshot:
                    push_snapshot(repository, branch)
                else:
                    subprocess.run(['git', '-C', str(repository), 'push', remote, branch], check=True)
            except (subprocess.CalledProcessError, ValueError) as error:
                print(str(error), flush=True)
                failures.append(remote)
    if failures:
        raise RuntimeError('Push failed for: ' + ', '.join(failures) + '. Other destinations may have succeeded.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--execute', action='store_true', help='Actually push; default prints the two commands')
    args = parser.parse_args()
    sync(args.repository, args.execute)
