"""Push the localization branch only to the configured GitHub origin."""
import argparse
from pathlib import Path
import subprocess


def sync(repository, execute=False):
    branch = 'localization'
    url = subprocess.check_output(['git', '-C', str(repository), 'remote', 'get-url', '--push', 'origin'],
                                  encoding='utf-8').strip()
    if not (url.startswith('https://github.com/') or url.startswith('git@github.com:')
            or url.startswith('ssh://git@github.com/')):
        if not Path(url).is_dir():
            raise ValueError('origin must point to GitHub; other hosting services are not used.')
    subprocess.run(['git', '-C', str(repository), 'rev-parse', '--verify', 'refs/heads/' + branch],
                   check=True, stdout=subprocess.DEVNULL)
    print('git push origin ' + branch, flush=True)
    if execute:
        subprocess.run(['git', '-C', str(repository), 'push', 'origin', branch], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--execute', action='store_true', help='Actually push; default only previews')
    args = parser.parse_args()
    sync(args.repository, args.execute)
