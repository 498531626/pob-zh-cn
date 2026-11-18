"""Portable release metadata and immutable GitHub update payloads."""
import hashlib
import json
import re
import shutil
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


def localized_version(upstream, patch):
    if not re.fullmatch(r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)', upstream):
        raise ValueError('Official version must have three numeric components.')
    if type(patch) is not int or patch < 1:
        raise ValueError('Chinese patch number must be a positive integer.')
    return f'{upstream}.{patch}'


def release_version(upstream, release):
    """Require a canonical vX.Y.Z.N tag belonging to this official version."""
    prefix = f'v{upstream}.'
    suffix = release.removeprefix(prefix)
    if not release.startswith(prefix) or not re.fullmatch(r'[1-9][0-9]*', suffix):
        raise ValueError(f'Release tag must be v{upstream}.N (N >= 1).')
    return localized_version(upstream, int(suffix))


def source_versions(root):
    upstream = json.loads((root / 'upstream-base.json').read_text('utf-8'))['tag'].removeprefix('v')
    version = ET.parse(root / 'manifest.xml').getroot().find('Version').get('number')
    release_version(upstream, 'v' + version)
    return upstream, version


def next_release_id(upstream, tags):
    patches = []
    for tag in tags:
        try:
            patches.append(int(release_version(upstream, tag).rsplit('.', 1)[1]))
        except ValueError:
            continue  # Official tags, old date-based tags and other upstream versions.
    return 'v' + localized_version(upstream, max(patches, default=0) + 1)


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


def write_manifest(folder, version, release, channel, channel_url=None, payload_url=None, upstream=None):
    root = ET.Element('PoBVersion')
    attributes = dict(number=version, branch=channel, platform='win32',
                      release=release, updates='enabled' if channel_url else 'disabled')
    if upstream:
        attributes['upstream'] = upstream
    ET.SubElement(root, 'Version', **attributes)
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
    # Update hashes describe exact bytes, including Windows CRLF line endings.
    # Raw downloads must match the portable ZIP rather than Git's text filters.
    (destination / '.gitattributes').write_bytes(b'* -text\n')
    shutil.copy2(folder / 'manifest.xml', destination / 'manifest.xml')
    shutil.copy2(folder / 'changelog.txt', destination / 'changelog.txt')
    shutil.copytree(folder, destination / 'files')
