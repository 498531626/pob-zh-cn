"""Read-only comparison of an already fetched official tag and this localization fork."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    result = subprocess.run(
        ['git', *args], cwd=ROOT, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, encoding='utf-8', errors='replace',
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'git command failed')
    return result.stdout.strip()


def paths(base, tip):
    output = git('diff', '--name-only', '-z', base, tip, '--')
    return set(filter(None, output.split('\0')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag', nargs='?', help='Fetched official tag, e.g. v2.67.2')
    args = parser.parse_args()
    base = json.loads((ROOT / 'upstream-base.json').read_text('utf-8'))
    tag = args.tag or base['tag']
    # Resolve tags explicitly: do not accidentally compare with a local branch.
    candidate = git('rev-parse', '--verify', f'refs/tags/{tag}^{{commit}}')
    recorded = git('rev-parse', '--verify', base['commit'] + '^{commit}')
    if git('merge-base', recorded, candidate) != recorded:
        raise RuntimeError('Candidate does not descend from the recorded upstream base.')
    integrated = git('merge-base', recorded, 'HEAD') == recorded
    upstream = paths(recorded, candidate)
    local = paths(recorded, 'HEAD')
    sensitive = (
        'src/Classes/', 'src/Modules/', 'src/Localization/',
        'src/Data/', 'src/TreeData/', 'src/GameVersions.lua',
        'src/Launch', 'runtime/', 'runtime-win32.zip',
    )
    report = {
        'recorded_base': base,
        'base_is_ancestor_of_head': integrated,
        'candidate_tag': tag,
        'candidate_commit': candidate,
        'working_tree_clean': not bool(git('status', '--porcelain')),
        'upstream_changed_count': len(upstream),
        'upstream_changed_files': sorted(upstream),
        'local_delta_count': len(local),
        'local_delta_files': sorted(local),
        'overlapping_files': sorted(upstream & local),
        'review_for_localization_or_runtime': sorted(
            path for path in upstream if path.startswith(sensitive)
        ),
        'note': 'File overlap is a review hint, not a compatibility test. No files changed.',
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not integrated:
        raise RuntimeError('Official baseline has not been connected to HEAD history.')


if __name__ == '__main__':
    # Keep machine-readable reports UTF-8 even when redirected on Windows.
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        main()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
