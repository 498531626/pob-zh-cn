"""Verify an update manifest and representative payloads without login or UI."""
import argparse
import hashlib
from urllib.parse import quote, urlsplit
from urllib.request import urlopen
import xml.etree.ElementTree as ET


def fetch(url):
    parsed = urlsplit(url)
    if (parsed.username or parsed.password or parsed.fragment or parsed.query
            or not (parsed.scheme == 'https' or (parsed.scheme == 'http' and parsed.hostname == '127.0.0.1'))):
        raise ValueError('Use credential-free HTTPS URLs (HTTP allowed only for a local fixture).')
    with urlopen(url, timeout=30) as response:
        if response.status != 200:
            raise ValueError('Download did not return HTTP 200')
        return response.read()


def probe(manifest_url, all_files=False):
    root = ET.fromstring(fetch(manifest_url))
    if root.tag != 'PoBVersion' or root.find('Version') is None:
        raise ValueError('URL did not return a PoB update manifest')
    version = root.find('Version')
    if version.get('updates') != 'enabled' or version.get('branch') != 'release-stable':
        raise ValueError('Not an enabled release-stable manifest')
    sources = {node.get('part'): node.get('url') for node in root.findall('Source')}
    files = root.findall('File')
    representative = {'Launch.lua', 'Modules/Localization.lua', 'Localization/ChineseGlyphs.png',
                      'SimpleGraphic.dll', 'Path of Building.exe', 'Update.exe', 'msvcr100.dll'}
    selected = files if all_files else [node for node in files if node.get('name') in representative]
    if not selected:
        raise ValueError('No representative payloads in the manifest')
    for node in selected:
        name = node.get('name')
        data = fetch(sources[node.get('part')] + quote(name, safe='/'))
        if hashlib.sha1(data).hexdigest() != node.get('sha1'):
            raise ValueError('Downloaded file hash mismatch: ' + name)
    print(f'Anonymous downloads passed: release={version.get("release")}, files={len(selected)}/{len(files)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest_url')
    parser.add_argument('--all-files', action='store_true')
    args = parser.parse_args()
    probe(args.manifest_url, args.all_files)
