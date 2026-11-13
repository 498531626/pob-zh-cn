"""Release metadata, update-site layout and Gitee-sized portable volumes."""
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

RAW_CHUNK_BYTES = 4 * 1024 * 1024


def gitee_urls(repository, channel, release):
    parsed = urlsplit(repository)
    if (parsed.scheme != 'https' or parsed.netloc != 'gitee.com' or parsed.query
            or parsed.fragment or not re.fullmatch(r'/[\w.-]+/[\w.-]+(?:\.git)?/?', parsed.path)):
        raise ValueError('Use an HTTPS Gitee repository URL without credentials or query parameters.')
    if not all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', value) for value in (channel, release)):
        raise ValueError('Channel and release tag must use letters, digits, dot, underscore or hyphen.')
    base = repository.rstrip('/').removesuffix('.git')
    return base + '/raw/' + channel + '/', base + '/raw/' + release + '/files/'


def write_manifest(folder, upstream, release, channel, channel_url=None, payload_url=None):
    root = ET.Element('PoBVersion')
    ET.SubElement(root, 'Version', number=upstream, branch=channel, platform='win32',
                  release=release, updates='enabled' if channel_url else 'disabled')
    if channel_url:
        ET.SubElement(root, 'Source', part='default', url=channel_url)
        for part in ('program', 'runtime'):
            ET.SubElement(root, 'Source', part=part, url=payload_url)
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or path.name == 'manifest.xml':
            continue
        relative = path.relative_to(folder).as_posix()
        part = 'runtime' if path.suffix.lower() in {'.exe', '.dll'} else 'program'
        node = ET.SubElement(root, 'File', name=relative, part=part,
                             sha1=hashlib.sha1(path.read_bytes()).hexdigest())
        if channel_url and path.stat().st_size > RAW_CHUNK_BYTES:
            node.set('chunks', str((path.stat().st_size + RAW_CHUNK_BYTES - 1) // RAW_CHUNK_BYTES))
    ET.indent(root, '\t')
    ET.ElementTree(root).write(folder / 'manifest.xml', encoding='utf-8', xml_declaration=True)


def write_update_site(folder, destination):
    """Commit this tree to release-stable, then tag that exact commit."""
    destination.mkdir()
    shutil.copy2(folder / 'manifest.xml', destination / 'manifest.xml')
    shutil.copy2(folder / 'changelog.txt', destination / 'changelog.txt')
    shutil.copytree(folder, destination / 'files')
    for node in ET.parse(folder / 'manifest.xml').getroot().findall('File'):
        if not node.get('chunks'):
            continue
        path = destination / 'files' / node.get('name')
        with path.open('rb') as source:
            for index in range(1, int(node.get('chunks')) + 1):
                chunk = path.with_name(path.name + f'.part{index:03d}')
                if chunk.exists():
                    raise ValueError('Update chunk path collides with a packaged file: ' + str(chunk))
                chunk.write_bytes(source.read(RAW_CHUNK_BYTES))
        path.unlink()


def split_archive(archive, destination, volume_bytes=90 * 1024 * 1024):
    if volume_bytes < 1 or volume_bytes > 90 * 1024 * 1024:
        raise ValueError('Gitee volumes must be between 1 byte and 90 MiB.')
    destination.mkdir()
    parts = []
    with archive.open('rb') as source:
        index = 1
        while chunk := source.read(volume_bytes):
            name = archive.name + f'.{index:03d}'
            (destination / name).write_bytes(chunk)
            parts.append({'name': name, 'size': len(chunk), 'sha256': hashlib.sha256(chunk).hexdigest()})
            index += 1
    with archive.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    (destination / 'volumes.json').write_text(json.dumps({
        'archive': archive.name, 'sha256': digest, 'parts': parts,
    }, indent=2), encoding='utf-8')
    # Built-in Windows copy /b reconstructs an ordinary ZIP; no Python or 7-Zip required.
    commands = ['@echo off', 'setlocal', 'cd /d "%~dp0"',
                f'if exist "{archive.name}" (echo ZIP already exists. & pause & exit /b 1)']
    commands += [f'if not exist "{part["name"]}" (echo Missing volume {i}. & pause & exit /b 1)'
                 for i, part in enumerate(parts, 1)]
    commands += ['copy /b ' + '+'.join('"' + part['name'] + '"' for part in parts) + f' "{archive.name}"',
                 'if errorlevel 1 (echo Join failed. & pause & exit /b 1)',
                 f'certutil -hashfile "{archive.name}" SHA256 | find /i "{digest}" >nul',
                 'if errorlevel 1 (echo Checksum mismatch. Do not extract. & pause & exit /b 1)',
                 'echo SHA256 verified. You can now extract the ZIP.', 'pause']
    (destination / 'Join-Portable.cmd').write_bytes(('\r\n'.join(commands) + '\r\n').encode('ascii'))
    (destination / '使用说明.txt').write_text(
        '下载本发行版的全部 .zip.001、.002 等分卷及 Join-Portable.cmd，放进同一文件夹。\n'
        '双击 Join-Portable.cmd 合成完整 ZIP，脚本自动校验 SHA256，通过后再解压 ZIP。\n'
        '分卷中的内容与 GitHub 完整便携 ZIP 完全相同，不需要安装 Python 或 7-Zip。\n', encoding='utf-8-sig')
    return parts
