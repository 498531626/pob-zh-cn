"""Build a clean, self-contained Windows archive from versioned PoB files."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args]).decode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if git('status', '--porcelain', '--untracked-files=no').strip():
        raise SystemExit('Commit or isolate tracked changes before packaging.')
    revision = git('rev-parse', 'HEAD').strip()
    date = datetime.now(timezone.utc).strftime('%Y%m%d')
    name = f'PoB-ZH-CN-2.67.2-{date}-{revision[:9]}-Windows-Portable'
    output = args.output.resolve()
    folder = output / name
    archive = output / (name + '.zip')
    if folder.exists() or archive.exists():
        raise SystemExit('Output already exists; choose a new output directory.')
    folder.mkdir(parents=True)
    files = git('ls-files', '-z', 'src', 'runtime', 'manifest.xml',
                'changelog.txt', 'help.txt', 'LICENSE.md', 'LOCALIZATION.md',
                'upstream-base.json').split('\0')
    excluded = {'src/LaunchInstall.lua', 'runtime/Update.exe',
                'runtime/lua/lua-profiler.lua', 'runtime/msvcr100.dll'}
    hashes = {}
    for relative in sorted(filter(None, files)):
        path = Path(relative)
        if (relative in excluded or relative.startswith('src/Export/')
                or path.name.lower() in {'settings.xml', 'language.cfg', 'poe_api_response.json'}
                or 'Builds' in path.parts):
            continue
        target = folder / path
        if relative == 'runtime/Path{space}of{space}Building.exe':
            target = folder / 'runtime/Path of Building.exe'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, target)
        hashes[target.relative_to(folder).as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
    # Keep the proven runtime/ + src/ layout: the runtime resolves ../src/Launch.lua.
    # The repository manifest enables devMode, which disables official updates
    # and places all saves inside src/ instead of using the recipient's Documents.
    (folder / 'Start-PoB.cmd').write_bytes(
        b'@echo off\r\ncd /d "%~dp0runtime"\r\nstart "" "Path of Building.exe"\r\n')
    (folder / '使用说明.txt').write_text('''Path of Building 简体中文便携版 2.67.2

使用方法：
1. 先把整个 ZIP 解压到有写入权限的文件夹，例如 D:\\Games\\PoB。
2. 双击 Start-PoB.cmd；也可直接进入 runtime 双击 Path of Building.exe。
3. 无需安装 Python、Lua、Git 或开发环境；所需运行库已附带。
4. 默认简体中文，F8 切换中英文。

请保留完整目录结构，不要只发送 EXE，也不要在压缩包中直接运行。
本包面向 Windows 10/11 64 位桌面系统；不提供 macOS/手机版本。
基础构筑计算可离线使用；联网导入、价格查询和远程内容需要网络。
本汉化包关闭官方自动更新。后续更新请使用同来源的新汉化整包。

个人数据：
构筑保存在 src/Builds，设置保存在 src/Settings.xml，语言选择保存在
src/Localization/language.cfg。请备份这些内容；更新时保留旧包和备份。
此初始分发包不包含制作者的个人构筑、账号信息或设置。

关于：
基于 Path of Building Community，本包为非官方简体中文显示层。
许可见 LICENSE.md；版本与文件校验信息见 package-info.json。
''', encoding='utf-8-sig')
    info = {'name': name, 'upstream_version': '2.67.2', 'source_commit': revision,
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'entry_point': 'Start-PoB.cmd', 'automatic_updates': False,
            'personal_data_included': False, 'sha256': hashes}
    (folder / 'package-info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                bundle.write(path, path.relative_to(output).as_posix())
    with zipfile.ZipFile(archive) as bundle:
        bad = bundle.testzip()
        if bad:
            raise RuntimeError(f'Archive CRC failed: {bad}')
    digest = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    print(json.dumps({'folder': str(folder), 'archive': str(archive),
                      'size_mib': round(archive.stat().st_size / 1048576, 1),
                      'sha256': digest, 'crc': 'passed'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
