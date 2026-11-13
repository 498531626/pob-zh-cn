"""Push the localization branch to the already-configured origin and gitee remotes."""
import argparse
from pathlib import Path
import subprocess


def sync(repository, execute=False):
    branch = 'localization'
    remotes = subprocess.check_output(['git', '-C', str(repository), 'remote'], text=True).split()
    if not all(remote in remotes for remote in ('origin', 'gitee')):
        raise ValueError('Configure both origin (GitHub) and gitee remotes first; upstream is never pushed.')
    subprocess.run(['git', '-C', str(repository), 'rev-parse', '--verify', 'refs/heads/' + branch],
                   check=True, stdout=subprocess.DEVNULL)
    failures = []
    for remote in ('origin', 'gitee'):
        print(f'git push {remote} {branch}', flush=True)
        if execute:
            result = subprocess.run(['git', '-C', str(repository), 'push', remote, branch])
            if result.returncode:
                failures.append(remote)
    if failures:
        raise RuntimeError('Push failed for: ' + ', '.join(failures) + '. Other destinations may have succeeded.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--execute', action='store_true', help='Actually push; default prints the two commands')
    args = parser.parse_args()
    sync(args.repository, args.execute)
