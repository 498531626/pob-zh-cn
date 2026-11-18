"""Build display names for the current Spectres.lua inventory."""
import html
import json
import re
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
    translations = {}
    for english in sorted(names):
        if english in paired:
            translations[english] = paired[english]
        elif english in literals:
            translations[english] = literals[english]
        else:
            prefix, _, base = english.partition(' ')
            tier = {'Imperfect': '残次', 'Perfect': '完美'}.get(prefix)
            if not tier or base not in literals.keys() | paired.keys():
                raise ValueError(f'Untranslated spectre: {english}')
            translations[english] = tier + paired.get(base, literals.get(base, ''))

    return translations, {'names': len(names), 'paired': len(paired),
                          'literal_pending_review': len(names) - len(paired)}
