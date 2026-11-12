"""Build display-only item names and numeric text from paired PoEDB records.

Modifier records must have the same category/key, family, level and generation
type. Numbers are paired by their value, including signs and ranges. Only
English shapes present in this checkout are enabled; ambiguity is reported.
"""
from collections import defaultdict, Counter
from functools import lru_cache
from pathlib import Path
import json
import re
import gzip
from item_rules import compose_item, AMOUNT
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
NUMBER = re.compile(r'[+\-]?(?:\(\-?\d+(?:\.\d+)?-\-?\d+(?:\.\d+)?\)|\d+(?:\.\d+)?|#)')


def plain(value):
    return plain_html(str(value))


@lru_cache(maxsize=100000)
def plain_html(value):
    if '<' not in value:
        return value.replace('—', '-').replace('–', '-').replace('\xa0', ' ').strip()
    soup = BeautifulSoup(value, 'html.parser')
    for br in soup.select('br'):
        br.replace_with('\n')
    return soup.get_text().replace('—', '-').replace('–', '-').replace('\xa0', ' ').strip()


def shape(value):
    return NUMBER.sub('{#}', re.sub(r'\s+', ' ', value).strip())


def numeric_pair(english, chinese):
    """Keep value identities when Chinese word order reorders numeric spans."""
    ev, zv = NUMBER.findall(english), NUMBER.findall(chinese)
    if Counter(ev) != Counter(zv):
        return None
    ids = defaultdict(list)
    for i, value in enumerate(ev):
        ids[value].append(i)
    en_index = iter(range(len(ev)))
    en = NUMBER.sub(lambda m: '{' + str(next(en_index)) + '}', english)
    zh = NUMBER.sub(lambda m: '{' + str(ids[m[0]].pop(0)) + '}', chinese)
    return en, zh, len(ev)


def lua_pattern(value):
    escape = lambda s: re.sub(r'([\^$()%.\[\]*+?\-])', r'%\1', s)
    return '^' + ''.join('([%+%-]?[%d%.%(%)%-%#]+)' if re.fullmatch(r'\{\d+\}', p) else
                         '%s+' if p.isspace() else escape(p)
                         for p in re.split(r'(\{\d+\}|\s+)', value)) + '$'


def mod_records(obj, path=()):
    if isinstance(obj, dict):
        if 'str' in obj and isinstance(obj['str'], str):
            yield path, obj
        else:
            for k, v in obj.items():
                if k not in ('config', 'baseitem', 'gen', 'opt'):
                    yield from mod_records(v, path + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from mod_records(v, path + (str(i),))


def read_mods(soup):
    for script in soup.select('script'):
        text = script.get_text()
        if 'new ModsView(' in text:
            return json.JSONDecoder().raw_decode(text.split('new ModsView(', 1)[1])[0]
    return {}


def build_items(known_entries=None, known_templates=()):
    source = json.loads((HERE / 'item-source.json').read_text('utf8'))
    source += json.loads((HERE / 'database-source.json').read_text('utf8'))
    source += json.loads((HERE / 'item-runtime-source.json').read_text('utf8'))
    source += json.loads((HERE / 'legion-source.json').read_text('utf8'))
    local_text = {r['english'].strip() for r in source}
    local_names = defaultdict(set)
    for row in source:
        if row['kind'] in ('unique-name', 'base-name'):
            local_names[row['english'].strip().casefold()].add(row['english'].strip())
    local_shapes = {shape(t) for t in local_text}
    exact, patterns = defaultdict(dict), defaultdict(dict)
    seen_pairs = set()
    counts, rejected = Counter(), Counter()
    def add(en, zh, slug, kind):
        en, zh = plain(en), plain(zh)
        key = en, zh, kind
        if key in seen_pairs:
            return
        seen_pairs.add(key)
        if not re.search(r'[\u4e00-\u9fff]', zh) or re.search(r'[A-Za-z]{2}', zh):
            return
        meta = {'zh': zh, 'kind': kind, 'status': 'paired-record-local-english-numbers-checked',
                'source': 'https://poedb.tw/cn/' + slug,
                'english_source': 'https://poedb.tw/us/' + slug}
        # A combined reference stat may differ in one historic clause. Still
        # validate each aligned line independently before rejecting the group.
        if '\n' in en and len(en.splitlines()) == len(zh.splitlines()):
            for e, z in zip(en.splitlines(), zh.splitlines()):
                add(e, z, slug, kind)
        if kind.endswith('name') and en not in local_text:
            aliases = local_names.get(en.casefold(), set())
            if len(aliases) == 1:
                en = next(iter(aliases))
        paired = None if kind.endswith('name') else numeric_pair(en, zh)
        if not kind.endswith('name') and not paired:
            rejected['number-correspondence'] += 1
            return
        if en in local_text:
            exact[en][zh] = meta
        if kind.endswith('name') or shape(en) not in local_shapes:
            return
        e, z, values = paired
        if values:
            patterns[e][z] = dict(meta, en=e, zh=z, values=values, pattern=lua_pattern(e))
    manifest = json.loads((HERE / 'item-reference/sources.json').read_text('utf8'))
    for slug in ['Unique_item'] + manifest['pages']:
        paths = {l: HERE / 'item-reference' / f'{slug}-{l}.html.gz' for l in ('us', 'cn')}
        if not all(p.exists() for p in paths.values()):
            continue
        raw = {l: gzip.decompress(p.read_bytes()).decode('utf8') for l, p in paths.items()}
        soups = {l: BeautifulSoup(re.sub(r'<script\b[^>]*>.*?</script>', '', v, flags=re.S), 'html.parser') for l, v in raw.items()}
        # Names share the same page/link target. Unique name and base are
        # separate spans, not split by spaces or inferred from English words.
        links = {}
        for language, soup in soups.items():
            anchors = list(soup.select('a.whiteitem[href]'))
            anchors.extend(n.find_parent('a', href=True) for n in soup.select('.uniqueName'))
            links[language] = {a['href'].removeprefix('/'+language+'/'): a for a in anchors if a}
        for target in links['us'].keys() & links['cn'].keys():
            e, z = links['us'][target], links['cn'][target]
            for selector, kind in (('.uniqueName', 'unique-name'), ('.uniqueTypeLine', 'base-name')):
                if e.select_one(selector) and z.select_one(selector):
                    add(e.select_one(selector), z.select_one(selector), target, kind)
            if 'whiteitem' in e.get('class', []):
                add(e, z, target, 'base-name')
            if e.select_one('.uniqueName'):
                for selector in ('.implicitMod', '.explicitMod', '.reminderText'):
                    es, zs = e.parent.parent.select(selector), z.parent.parent.select(selector)
                    if len(es) == len(zs):
                        for a, b in zip(es, zs):
                            add(a, b, target, 'item-stat')
        cards = {l: s.select('.newItemPopup') for l, s in soups.items()}
        if len(cards['us']) == len(cards['cn']):
            for e, z in zip(cards['us'], cards['cn']):
                en, zn = e.select_one('.itemName'), z.select_one('.itemName')
                if en and zn and plain(en) in local_text:
                    add(en, zn, slug, 'unique-name' if e.select_one('.uniqueTypeLine') else 'base-name')
                    for selector in ('.implicitMod', '.explicitMod', '.reminderText'):
                        es, zs = e.select(selector), z.select(selector)
                        if len(es) == len(zs):
                            for a, b in zip(es, zs):
                                add(a, b, slug, 'item-stat')
        mods = {l: dict(mod_records(json.JSONDecoder().raw_decode(v.split('new ModsView(', 1)[1])[0]))
                if 'new ModsView(' in v else {} for l, v in raw.items()}
        for key in mods['us'].keys() & mods['cn'].keys():
            e, z = mods['us'][key], mods['cn'][key]
            if any(e.get(k) != z.get(k) for k in ('ModFamilyList', 'Level', 'ModGenerationTypeID', 'spawn_no')):
                rejected['record-identity'] += 1
                continue
            counts['paired_mod_records'] += 1
            add(e['str'], z['str'], slug, 'item-stat')
            add(e.get('Name', ''), z.get('Name', ''), slug, 'affix-name')
    reviewed_path = HERE / 'item-reviewed.json'
    reviewed = json.loads(reviewed_path.read_text('utf8')) if reviewed_path.exists() else {}
    for en, zh in json.loads((HERE / 'unique-reviewed.json').read_text('utf8')).items():
        reviewed[en] = {'zh': zh, 'kind': 'unique-reviewed', 'status': 'source-clause-reviewed',
                        'source': 'Data/Uniques; https://poedb.tw/cn/Unique_item'}
    entries = {en: next(iter(v.values())) for en, v in exact.items() if len(v) == 1}
    templates = {en: next(iter(v.values())) for en, v in patterns.items() if len(v) == 1}
    for en, meta in reviewed.items():
        if '{' in en:
            if shape(re.sub(r'\{\d+\}', '#', en)) not in local_shapes:
                raise ValueError('Reviewed item text not found in local source: ' + en)
            ids = re.findall(r'\{\d+\}', en)
            if Counter(ids) != Counter(re.findall(r'\{\d+\}', meta['zh'])):
                raise ValueError('Item numeric substitutions differ: ' + en)
            templates[en] = dict(meta, en=en, values=len(ids), pattern=lua_pattern(en))
        else:
            if en not in local_text:
                raise ValueError('Reviewed item name/text not found: ' + en)
            entries[en] = meta
    # Compose complete, finite source clauses from already verified terms.
    # The resulting exact text and numeric template are still display-only.
    shared = dict(known_entries or {}, **entries)
    terms = {k.casefold(): v['zh'] for k, v in shared.items()
             if not re.search(r'[A-Za-z]', v['zh']) and not NUMBER.search(k)}
    expressions = defaultdict(list)
    for t in list(known_templates) + list(templates.values()):
        parts = re.split(r'(\{\d+\})', t['en'])
        expression = ''.join(AMOUNT if re.fullmatch(r'\{\d+\}', part) else re.escape(part) for part in parts)
        word = re.search(r'[A-Za-z]+', t['en'])
        expressions[word[0] if word else ''].append((re.compile('^'+expression+'$'), t['zh']))
    resolving = set()
    @lru_cache(maxsize=50000)
    def resolve(text):
        if text in shared: return shared[text]['zh']
        word = re.search(r'[A-Za-z]+', text)
        for pattern, zh in expressions[word[0] if word else '']:
            match = pattern.fullmatch(text)
            if match:
                return re.sub(r'\{(\d+)\}', lambda m: match[int(m[1])+1], zh)
        if text in resolving: return None
        resolving.add(text)
        try: return compose_item(text, resolve, terms)
        finally: resolving.remove(text)
    composed = 0
    for en in sorted(local_text):
        if en in shared: continue
        zh = resolve(en)
        paired = numeric_pair(en, zh) if zh else None
        if not paired: continue
        meta = {'zh': zh, 'kind': 'item-clause', 'status': 'reviewed-finite-clauses-known-terms',
                'source': 'tools/localization/item_rules.py; https://poedb.tw/cn/Modifiers'}
        entries[en] = meta
        e, z, values = paired
        if values and e not in templates:
            templates[e] = dict(meta, en=e, zh=z, values=values, pattern=lua_pattern(e))
        composed += 1
    counts.update(exact_entries=len(entries), numeric_templates=len(templates), composed_entries=composed,
                  ambiguous_exact_resolved=sum(k in reviewed for k,v in exact.items() if len(v)>1),
                  ambiguous_templates_resolved=sum(k in reviewed for k,v in patterns.items() if len(v)>1),
                  ambiguous_exact=sum(len(v) > 1 for v in exact.values()),
                  ambiguous_templates=sum(len(v) > 1 for v in patterns.values()))
    report = {'counts': dict(counts), 'rejected': dict(rejected),
              'ambiguous': {k: list(v) for k, v in patterns.items() if len(v) > 1},
              'ambiguous_exact': {k: list(v) for k, v in exact.items() if len(v) > 1}}
    (HERE / 'item-coverage.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', 'utf8')
    return entries, sorted(templates.values(), key=lambda t: (-len(t['en']), t['en'])), dict(counts)
