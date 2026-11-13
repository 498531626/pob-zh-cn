"""Build and publish from an isolated GitHub Actions Windows runner."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from probe_update_site import probe
from release_support import github_urls

ROOT = Path(__file__).resolve().parents[2]


def run(*args, cwd=ROOT, capture=False):
    result = subprocess.run(list(map(str, args)), cwd=cwd, check=True, encoding='utf-8',
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-id', required=True)
    args = parser.parse_args()
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REF') != 'refs/heads/localization':
        raise SystemExit('Run this publisher through the manual GitHub Actions workflow on localization.')
    repository = os.environ['GITHUB_REPOSITORY']
    channel_url, _ = github_urls('https://github.com/' + repository, 'release-stable', args.release_id)
    source = run('git', 'rev-parse', 'HEAD', capture=True)
    if run('git', 'ls-remote', 'origin', 'refs/tags/' + args.release_id, capture=True):
        raise SystemExit('Release tag already exists; choose a new immutable release ID.')
    output = Path(tempfile.mkdtemp(prefix='pob-portable-', dir=os.environ['RUNNER_TEMP']))
    run(sys.executable, ROOT / 'tools/packaging/test_releases.py')
    result = json.loads(run(sys.executable, ROOT / 'tools/packaging/build_portable.py',
                            '--output', output, '--github-repository', 'https://github.com/' + repository,
                            '--release-id', args.release_id, capture=True))
    archive = Path(result['archive'])
    run(sys.executable, ROOT / 'tools/packaging/check_portable.py', archive)
    site = output / (Path(result['folder']).name + '-update-site')
    publish = output / 'publish'
    previous = run('git', 'ls-remote', 'origin', 'refs/heads/release-stable', capture=True)
    if previous:
        run('git', 'fetch', '--no-tags', 'origin', 'refs/heads/release-stable')
        base = run('git', 'rev-parse', 'FETCH_HEAD', capture=True)
    else:
        base = source
    # A separate worktree shares object storage and checkout's authenticated Git
    # configuration. The development checkout and source branch stay untouched.
    run('git', 'worktree', 'add', '--detach', '--no-checkout', publish, base)
    if not previous:
        run('git', 'symbolic-ref', 'HEAD', 'refs/heads/publish-' + os.environ['GITHUB_RUN_ID'], cwd=publish)
    run('git', 'read-tree', '--empty', cwd=publish)
    shutil.copytree(site, publish, dirs_exist_ok=True)
    run('git', 'add', '.', cwd=publish)
    run('git', '-c', 'user.name=PoB Release', '-c', 'user.email=release@users.noreply.github.com',
        'commit', '-m', 'Publish ' + args.release_id + '; source ' + source, cwd=publish)
    candidate = run('git', 'rev-parse', 'HEAD', cwd=publish, capture=True)
    run('git', 'tag', args.release_id, candidate, cwd=publish)
    run('git', 'push', 'origin', 'refs/tags/' + args.release_id, cwd=publish)
    probe(channel_url.replace('/release-stable/', '/' + args.release_id + '/') + 'manifest.xml')
    notes = output / 'release.md'
    notes.write_text(
        'Path of Building Community ' + result.get('release_id', args.release_id) + ' 简体中文便携版。\n\n'
        '下载下面的 **PoB-ZH-CN-…-Windows-Portable.zip**，完整解压后运行 **Path of Building.exe**。'
        '无需 Python、Lua、Git 或开发环境；Windows 10/11 64 位。请勿下载 Source code 代替便携包。\n\n'
        '- 默认中文，F8 切换中英文；正式模式，无开发者控制项。\n'
        '- 源码、完整包和汉化更新均使用本 GitHub 仓库。仅下载变化的文件，校验后提示确认更新。\n'
        '- 迁移前备份 Builds、Settings.xml 和 Localization/language.cfg；旧开发包对应内容在 src 下。\n\n'
        '更新清单：' + channel_url + 'manifest.xml\n\n'
        '源码提交：`' + source + '`\n\nZIP SHA-256：`' + result['sha256'] + '`\n\n'
        '已通过 Windows 无界面发布测试、独立解压校验、原生库加载、八个页面、中英文切换、'
        '计算与构筑 XML 读写检查，并验证 GitHub 匿名下载。未操作用户桌面。\n', encoding='utf-8')
    run('gh', 'release', 'create', args.release_id, '--repo', repository, '--verify-tag', '--draft',
        '--title', 'PoB 简体中文便携版 · ' + args.release_id, '--notes-file', notes)
    run('gh', 'release', 'upload', args.release_id, archive, str(archive) + '.sha256', '--repo', repository)
    run('git', 'push', 'origin', candidate + ':refs/heads/release-stable', cwd=publish)
    probe(channel_url + 'manifest.xml')
    run('gh', 'release', 'edit', args.release_id, '--repo', repository, '--draft=false', '--latest')
    url = 'https://github.com/' + repository + '/releases/tag/' + args.release_id
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
        summary.write('[Download portable release](' + url + ')\n\nSHA-256: `' + result['sha256'] + '`\n')
    print(url, flush=True)


if __name__ == '__main__':
    main()
