"""Portable release metadata and immutable GitHub update payloads."""
import hashlib
import re
import shutil
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


def github_urls(repository, channel, release):
    parsed = urlsplit(repository)
    if (parsed.scheme != 'https' or parsed.netloc != 'github.com' or parsed.query
            or parsed.fragment or not re.fullmatch(r'/[\w.-]+/[\w.-]+(?:\.git)?/?', parsed.path)):
        raise ValueError('Use an HTTPS GitHub repository URL without credentials or query parameters.')
    if not all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', value) for value in (channel, release)):
        raise ValueError('Channel and release tag must use letters, digits, dot, underscore or hyphen.')
    path = parsed.path.rstrip('/').removesuffix('.git')
    base = 'https://raw.githubusercontent.com' + path + '/'
    return base + channel + '/', base + release + '/files/'


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
        ET.SubElement(root, 'File', name=relative, part=part,
                      sha1=hashlib.sha1(path.read_bytes()).hexdigest())
    ET.indent(root, '\t')
    ET.ElementTree(root).write(folder / 'manifest.xml', encoding='utf-8', xml_declaration=True)


def write_update_site(folder, destination):
    """Publish the candidate tag before promoting the stable branch."""
    destination.mkdir()
    shutil.copy2(folder / 'manifest.xml', destination / 'manifest.xml')
    shutil.copy2(folder / 'changelog.txt', destination / 'changelog.txt')
    shutil.copytree(folder, destination / 'files')
