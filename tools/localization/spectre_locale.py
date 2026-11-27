"""Build display names for the current Spectres.lua inventory."""
import html
import json
import re
import gzip
from collections import defaultdict
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def monster_links(language):
    snapshot = HERE / 'skill-reference' / f'Default_Attack-{language}.html'
    pattern = rf'data-hover="[^"]*/Poe_Data_MonsterVarieties_hover/[^"]*"\s+href="/{language}/([^"#?]+)"[^>]*>([^<>]+)</a>'
    return [(unquote(slug), html.unescape(name.strip()))
            for slug, name in re.findall(pattern, snapshot.read_text('utf8'))]


def build_spectres(database_entries):
    source = (ROOT / 'src/Data/Spectres.lua').read_text('utf8')
    names = set(re.findall(r'^\tname = "([^"\n]+)",', source, re.M))
    if not names:
        raise ValueError('No spectre names found in Spectres.lua')

    chinese = dict(monster_links('cn'))
    candidates = {}
    for slug, english in monster_links('us'):
        translation = chinese.get(slug, '')
        if english in names and re.search(r'[\u4e00-\u9fff]', translation):
            candidates.setdefault(english, set()).add(translation)
    paired = {english: next(iter(translations)) for english, translations in candidates.items()
              if len(translations) == 1}
    for english in names & database_entries.keys():
        entry = database_entries[english]
        if (entry['status'] == 'reviewed-monster-variant-id-card'
                or (english.startswith('Perfect ') and entry['status'] == 'paired-local-source')):
            paired[english] = entry['zh']

    literals = json.loads((HERE / 'spectre-literal-names.json').read_text('utf8'))
    reviewed_path = HERE / 'spectre-reference-reviewed.json'
    reviewed = json.loads(reviewed_path.read_text('utf8')) if reviewed_path.exists() else {}
    translations = {}
    for english in sorted(names):
        if english in reviewed:
            translations[english] = reviewed[english]['zh']
        elif english in paired:
            translations[english] = paired[english]
        elif english in literals:
            translations[english] = literals[english]
        else:
            prefix, _, base = english.partition(' ')
            tier = {'Imperfect': '残次', 'Perfect': '完美'}.get(prefix)
            if not tier or base not in literals.keys() | paired.keys():
                raise ValueError(f'Untranslated spectre: {english}')
            translations[english] = tier + paired.get(base, literals.get(base, ''))

    verified = set(paired)
    verified.update(en for en, row in reviewed.items() if row['status'].startswith('paired'))
    return translations, {'names': len(names), 'paired': len(names & verified),
                          'literal_pending_review': len(names - verified)}


def build_areas(entries):
    """Pair the locations actually shown by this release, keeping area IDs intact."""
    pairs = defaultdict(set)
    for en_path in sorted((HERE / 'area-reference').glob('*-us.html.gz')):
        if not re.fullmatch(r'(?:Act_\d+|Maps|Atlas_of_Worlds)-us.html.gz', en_path.name):
            continue
        zh_path = en_path.with_name(en_path.name.replace('-us.', '-cn.'))
        maps = []
        for language, path in (('us', en_path), ('cn', zh_path)):
            links = defaultdict(set)
            soup = BeautifulSoup(gzip.decompress(path.read_bytes()).decode('utf8'), 'html.parser')
            for link in soup.select('a[href][data-hover]'):
                hover = link['data-hover']
                name = link.get_text(' ', strip=True)
                if name and ('WorldAreas' in hover or 'AtlasNode' in hover):
                    links[link['href'].removeprefix('/' + language + '/')].add(name)
            maps.append({slug: next(iter(names)) for slug, names in links.items() if len(names) == 1})
        for slug in maps[0].keys() & maps[1].keys():
            if re.search('[\u4e00-\u9fff]', maps[1][slug]):
                pairs[maps[0][slug]].add(maps[1][slug])
    paired = {en: next(iter(names)) for en, names in pairs.items() if len(names) == 1}
    literals = json.loads((HERE / 'spectre-area-literals.json').read_text('utf8'))
    reviewed_path = HERE / 'spectre-area-reviewed.json'
    reviewed = json.loads(reviewed_path.read_text('utf8')) if reviewed_path.exists() else {}
    source = (ROOT / 'src/Data/Spectres.lua').read_text('utf8')
    locations = set()
    for block in re.findall(r'spawnLocation = \{(.*?)\}', source, re.S):
        locations.update(re.findall(r'"([^"\n]+)"', block))
    names = {re.sub(r' \([^)]*\)$', '', location) for location in locations}
    translations = {}
    literal_count = 0
    for name in sorted(names):
        if name in reviewed and 'zh' in reviewed[name]:
            translations[name] = reviewed[name]['zh']
        elif name in paired:
            translations[name] = paired[name]
        elif name in entries:
            translations[name] = entries[name]['zh']
        elif name + ' Map' in entries:
            translations[name] = entries[name + ' Map']['zh']
        elif name in literals:
            translations[name] = literals[name]
            literal_count += 1
        else:
            raise ValueError('Untranslated spectre location: ' + name)
    return translations, {'locations': len(locations), 'base_names': len(names),
                          'literal_pending_review': literal_count,
                          'reference_retrieved': '2026-11-27'}
