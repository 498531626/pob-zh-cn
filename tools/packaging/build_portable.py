"""Build a clean, self-contained Windows archive from versioned PoB files."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from release_support import github_urls, write_manifest, write_update_site

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args]).decode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--github-repository', help='Public GitHub HTTPS URL; omit for an offline-only package')
    parser.add_argument('--channel', default='release-stable')
    parser.add_argument('--release-id', help='Unique immutable release tag; defaults to date and source commit')
    args = parser.parse_args()
    if git('status', '--porcelain', '--untracked-files=no').strip():
        raise SystemExit('Commit or isolate tracked changes before packaging.')
    revision = git('rev-parse', 'HEAD').strip()
    date = datetime.now(timezone.utc).strftime('%Y%m%d')
    upstream = ET.parse(ROOT / 'manifest.xml').getroot().find('Version').get('number')
    release = args.release_id or f'zh-{upstream}-{date}-{revision[:9]}'
    channel_url = payload_url = None
    if args.github_repository:
        channel_url, payload_url = github_urls(args.github_repository, args.channel, release)
    name = f'PoB-ZH-CN-{upstream}-{date}-{revision[:9]}-Windows-Portable'
    output = args.output.resolve()
    folder = output / name
    archive = output / (name + '.zip')
    if folder.exists() or archive.exists():
        raise SystemExit('Output already exists; choose a new output directory.')
    folder.mkdir(parents=True)
    files = git('ls-files', '-z', 'src', 'runtime', 'manifest.xml',
                'changelog.txt', 'help.txt', 'LICENSE.md', 'LOCALIZATION.md',
                'upstream-base.json').split('\0')
    excluded = {'src/LaunchInstall.lua', 'runtime/lua/lua-profiler.lua', 'manifest.xml'}
    if not channel_url:
        excluded.update({'runtime/Update.exe', 'runtime/msvcr100.dll'})
    hashes = {}
    for relative in sorted(filter(None, files)):
        path = Path(relative)
        if (relative in excluded or relative.startswith('src/Export/')
                or path.name.lower() in {'settings.xml', 'language.cfg', 'poe_api_response.json'}
                or 'Builds' in path.parts):
            continue
        # The official portable layout puts scripts, runtime and assets together.
        target = folder / (path.relative_to(path.parts[0]) if path.parts[0] in {'src', 'runtime'} else path)
        if relative == 'runtime/Path{space}of{space}Building.exe':
            target = folder / 'Path of Building.exe'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, target)
        hashes[target.relative_to(folder).as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
    (folder / 'Start-PoB.cmd').write_bytes(
        b'@echo off\r\ncd /d "%~dp0"\r\nstart "" "Path of Building.exe"\r\n')
    (folder / '使用说明.txt').write_text(f'''Path of Building 简体中文便携版 {upstream}

使用方法：
1. 先把整个 ZIP 解压到有写入权限的文件夹，例如 D:\\Games\\PoB。
2. 双击 Path of Building.exe 或 Start-PoB.cmd。
3. 无需安装 Python、Lua、Git 或开发环境；所需运行库已附带。
4. 默认简体中文，F8 切换中英文。

请保留完整目录结构，不要只发送 EXE，也不要在压缩包中直接运行。
本包面向 Windows 10/11 64 位桌面系统；不提供 macOS/手机版本。
基础构筑计算可离线使用；联网导入、价格查询和远程内容需要网络。
本包不连接官方更新源。{'启动时从 GitHub 检查已发布的汉化更新，下载后由你确认应用并重启。' if channel_url else '尚未配置汉化更新源，请使用同来源的新汉化整包更新。'}

个人数据：
构筑保存在 Builds，设置保存在 Settings.xml，语言选择保存在
Localization/language.cfg。请备份这些内容；更新时保留旧包和备份。
如果从旧开发模式包迁移，请先备份旧包 src/Builds、src/Settings.xml 和
src/Localization/language.cfg，再分别复制到新包的上述对应位置。
此初始分发包不包含制作者的个人构筑、账号信息或设置。

关于：
基于 Path of Building Community，本包为非官方简体中文显示层。
许可见 LICENSE.md；版本与文件校验信息见 package-info.json。
''', encoding='utf-8-sig')
    for generated in ('Start-PoB.cmd', '使用说明.txt'):
        hashes[generated] = hashlib.sha256((folder / generated).read_bytes()).hexdigest()
    info = {'name': name, 'upstream_version': upstream, 'source_commit': revision,
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'entry_point': 'Start-PoB.cmd', 'automatic_updates': bool(channel_url),
            'release_id': release, 'update_channel': args.channel,
            'update_manifest_url': channel_url + 'manifest.xml' if channel_url else None,
            'developer_mode': False,
            'personal_data_included': False, 'sha256': hashes}
    (folder / 'package-info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    write_manifest(folder, upstream, release, args.channel, channel_url, payload_url)
    if channel_url:
        write_update_site(folder, output / (name + '-update-site'))
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                bundle.write(path, path.relative_to(output).as_posix())
    with zipfile.ZipFile(archive) as bundle:
        bad = bundle.testzip()
        if bad:
            raise RuntimeError(f'Archive CRC failed: {bad}')
    with archive.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    plan = {'source_commit': revision, 'source_branch': 'localization', 'release_id': release,
            'github_assets': [archive.name, archive.name + '.sha256'],
            'github_repository': args.github_repository, 'channel': args.channel,
            'update_site_directory': name + '-update-site' if channel_url else None,
            'update_manifest_url': info['update_manifest_url'], 'remote_actions_performed': False}
    (output / (name + '-release-plan.json')).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'folder': str(folder), 'archive': str(archive),
                      'size_mib': round(archive.stat().st_size / 1048576, 1),
                      'sha256': digest, 'crc': 'passed', 'release_id': release,
                      'update_manifest_url': info['update_manifest_url']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
