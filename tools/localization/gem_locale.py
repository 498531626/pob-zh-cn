"""Build display templates from paired PoEDB gem cards and local English text.

Only marked numeric spans become substitutions. Pairing requires the same gem
name and identical ordered numeric span contents; conflicting templates fall
back to English. Game data and the stat parser are never changed.
"""
from collections import Counter, defaultdict
from pathlib import Path
import json
import re
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PLACEHOLDER = re.compile(r'\{(?:\d+)?(?::\+?d)?\}')


def normalize(text):
    return re.sub(r'\s+', ' ', PLACEHOLDER.sub('{#}', text.replace('%%', '%').replace('\\n', '\n'))).strip()


def rendered_local_form(text, forms):
    """Validate reviewed singular strings against local numeric descriptors."""
    normalized = normalize(text)
    if normalized in forms:
        return True
    for form in forms:
        if '{#}' in form:
            parts = form.split('{#}')
            if not normalized.startswith(parts[0]) or not normalized.endswith(parts[-1]):
                continue
            pattern = re.escape(form).replace(re.escape('{#}'), r'[+\-]?(?:\d+(?:\.\d+)?|\(\d+(?:\.\d+)?-\d+(?:\.\d+)?\))')
            if re.fullmatch(pattern, normalized):
                return True
    return False


def source_texts():
    descriptions, stats = set(), set()
    for folder, field, target in (('Skills', 'description', descriptions), ('StatDescriptions', 'text', stats)):
        for path in (ROOT / 'src/Data' / folder).glob('*.lua'):
            for raw in re.findall(r'\b' + field + r'\s*=\s*"((?:\\.|[^"\\])*)"', path.read_text('utf8')):
                try:
                    value = json.loads('"' + raw + '"')
                except ValueError:
                    continue
                target.add(value)
                target.add(value.strip())
                target.update(value.replace('\\n', '\n').splitlines())
    return descriptions, {normalize(x) for x in stats}


def hybrid_gem_names():
    """Mirror Data.lua's name-only rule for actual Vaal/transfigured hybrids."""
    effects = {}
    for path in (ROOT / 'src/Data/Skills').glob('*.lua'):
        for effect, block in re.findall(r'^skills\["([^"]+)"\] = \{\n(.*?)^\}', path.read_text('utf8'), re.M | re.S):
            match = re.search(r'\bbaseTypeName = "([^"]+)"', block)
            if match:
                effects[effect] = match[1]
    names = {}
    for block in re.findall(r'^\t\["[^"]+"\] = \{\n(.*?)^\t\},', (ROOT / 'src/Data/Gems.lua').read_text('utf8'), re.M | re.S):
        if 'vaalGem = true' in block:
            base = re.search(r'secondaryGrantedEffectId = "([^"]+)"', block)
            if base:
                for alt in ('AltX', 'AltY'):
                    if base[1] + alt in effects:
                        name = effects[base[1] + alt]
                        names['Vaal ' + name] = name
    return names


def text(el):
    copy = BeautifulSoup(str(el), 'html.parser')
    for br in copy.select('br'):
        br.replace_with('\n')
    return copy.get_text('', strip=False).replace('\r', '').strip()


def template(el):
    copy = BeautifulSoup(str(el), 'html.parser')
    values = []
    for i, span in enumerate(copy.select('.mod-value')):
        values.append(text(span))
        span.replace_with('{' + str(i) + '}')
    return text(copy), values


def lua_pattern(english):
    pieces = re.split(r'(\{\d+\})', english)
    escape = lambda s: re.sub(r'([\^$()%.\[\]*+?\-])', r'%\1', s)
    return '^' + ''.join('([%+%-]?[%d%.%(%)%-]+)' if re.fullmatch(r'\{\d+\}', p) else escape(p)
                         for p in pieces) + '$'


def build_gems(known_names):
    sources = json.loads((HERE / 'gem-reference/sources.json').read_text('utf8'))
    descriptions, stat_forms = source_texts()
    local_names = set()
    for path in (ROOT / 'src/Data/Skills').glob('*.lua'):
        local_names.update(re.findall(r'\bname\s*=\s*"([^"\n]+)"', path.read_text('utf8')))
    for path in sorted((HERE / 'skill-reference').glob('*-us.html')):
        slug = path.name.removesuffix('-us.html')
        if all((HERE / 'skill-reference' / f'{slug}-{lang}.html').exists() for lang in ('us','cn')):
            sources.setdefault(slug, {})['full_page'] = True
    exact, patterns = defaultdict(dict), defaultdict(dict)
    source_urls = {}
    counts = Counter()
    rejected = []
    for slug in sorted(sources):
        cards = {}
        for lang in ('us', 'cn'):
            path = HERE / 'gem-reference' / f'{slug}-{lang}-hover.html'
            if sources[slug].get('full_page'):
                path = HERE / 'skill-reference' / f'{slug}-{lang}.html'
            document = BeautifulSoup(path.read_text('utf8'), 'html.parser')
            # Full pages expose the current canonical slug in their language
            # menu (e.g. Doryanis_Touch, without the English apostrophe).
            canonical = next((a['href'][4:] for a in document.select('a[href]')
                              if a['href'].startswith('/us/') and a.get_text(' ', strip=True) == 'US English'), slug)
            source_urls[slug, lang] = f'https://poedb.tw/{lang}/{canonical}'
            cards[lang] = document.select('.GemPopup,.gemPopup,.newItemPopup')
        if len(cards['us']) != len(cards['cn']):
            rejected.append({'slug': slug, 'reason': 'card-count'})
            continue
        counts['gem_pairs'] += 1
        for en, cn in zip(cards['us'], cards['cn']):
            en_name, cn_name = text(en.select_one('.itemName')), text(cn.select_one('.itemName'))
            known = known_names.get(en_name)
            if (not known and en_name not in local_names and en_name.removesuffix(' Support') not in local_names) or not re.search('[\u4e00-\u9fff]', cn_name):
                rejected.append({'slug': slug, 'reason': 'card-name', 'english': en_name, 'chinese': cn_name})
                continue
            meta = {'kind': 'gem-detail', 'source': source_urls[slug, 'cn'],
                    'english_source': source_urls[slug, 'us'],
                    'status': 'paired-slug-name-local-english-numeric-spans-checked'}
            exact[en_name][cn_name] = dict(meta, zh=cn_name, kind='gem')
            for selector in ('.secDescrText', '.explicitMod', '.qualityMod', '.reminderText'):
                es, zs = en.select(selector), cn.select(selector)
                if len(es) != len(zs):
                    rejected.append({'slug': slug, 'reason': 'line-count', 'selector': selector})
                    continue
                for e, z in zip(es, zs):
                    english, ev = template(e)
                    chinese, zv = template(z)
                    if ev != zv or not re.search('[\u4e00-\u9fff]', chinese) or len(PLACEHOLDER.findall(chinese)) != len(zv):
                        rejected.append({'slug': slug, 'reason': 'numeric-span-mismatch', 'english': english})
                        continue
                    pairs = [(english, chinese)]
                    if len(english.splitlines()) == len(chinese.splitlines()) and '\n' in english:
                        pairs.extend(zip(english.splitlines(), chinese.splitlines()))
                    for english_line, chinese_line in pairs:
                        # Different line wrapping can move numeric spans to a
                        # neighbouring line. Such fragments cannot be paired.
                        if set(PLACEHOLDER.findall(english_line)) != set(PLACEHOLDER.findall(chinese_line)):
                            rejected.append({'slug': slug, 'reason': 'line-numeric-span-mismatch', 'english': english_line})
                            continue
                        if not PLACEHOLDER.search(english_line):
                            if english_line in descriptions or normalize(english_line) in stat_forms:
                                exact[english_line][chinese_line] = dict(meta, zh=chinese_line)
                            continue
                        if normalize(english_line) not in stat_forms:
                            rejected.append({'slug': slug, 'reason': 'local-template-mismatch', 'english': english_line})
                            continue
                        # Keep the numeric correspondence even after splitting a multiline mod.
                        ids = PLACEHOLDER.findall(english_line)
                        if ids != PLACEHOLDER.findall(chinese_line) or len(set(ids)) != len(ids):
                            continue
                        for i, old in enumerate(ids):
                            english_line = english_line.replace(old, '@VALUE' + str(i) + '@')
                            chinese_line = chinese_line.replace(old, '@VALUE' + str(i) + '@')
                        for i in range(len(ids)):
                            english_line = english_line.replace('@VALUE' + str(i) + '@', '{' + str(i) + '}')
                            chinese_line = chinese_line.replace('@VALUE' + str(i) + '@', '{' + str(i) + '}')
                        patterns[english_line][chinese_line] = dict(meta, en=english_line, zh=chinese_line,
                            pattern=lua_pattern(english_line), values=len(ids))
            # Exact complete tag lists avoid translating fragments of free prose.
            et, zt = en.select('.GemTags'), cn.select('.GemTags')
            if len(et) == len(zt) and et:
                exact[', '.join(map(text, et))][', '.join(map(text, zt))] = dict(meta, zh=', '.join(map(text, zt)))
    entries = {en: next(iter(choices.values())) for en, choices in exact.items() if len(choices) == 1}
    templates = [next(iter(choices.values())) for choices in patterns.values() if len(choices) == 1]
    reviewed = json.loads((HERE / 'gem-reviewed.json').read_text('utf8'))
    skill_review = json.loads((HERE / 'skill-reviewed.json').read_text('utf8'))
    reviewed.update({en: meta['zh'] for en, meta in skill_review.items()})
    for english, chinese in reviewed.items():
        english, chinese = english.replace('\\n','\n'), chinese.replace('\\n','\n')
        if english not in descriptions and english not in local_names and not rendered_local_form(english, stat_forms):
            raise ValueError('Reviewed text no longer matches local source: ' + english)
        if sorted(PLACEHOLDER.findall(english)) != sorted(PLACEHOLDER.findall(chinese)):
            raise ValueError('Reviewed numeric substitutions differ: ' + english)
        candidates = exact.get(english) or patterns.get(english)
        if candidates:
            meta = dict(next(iter(candidates.values())))
        else:
            slug = next((x['slug'] for x in rejected if x.get('english') == english), None)
            meta = {'kind': 'gem-detail',
                    'source': source_urls.get((slug, 'cn'), f'https://poedb.tw/cn/{slug}') if slug else 'tools/localization/gem-reviewed.json',
                    'english_source': source_urls.get((slug, 'us'), f'https://poedb.tw/us/{slug}') if slug else 'src/Data/StatDescriptions'}
        meta.update(zh=chinese, status='paired-reference-semantic-review')
        if english in skill_review:
            meta.update(skill_review[english])
        if PLACEHOLDER.search(english):
            templates = [t for t in templates if t['en'] != english]
            templates.append(dict(meta, en=english, pattern=lua_pattern(english), values=len(PLACEHOLDER.findall(english))))
        else:
            entries[english] = meta
    # More literal text first, so a broad numeric template cannot shadow a specific one.
    for english, meta in entries.items():
        if PLACEHOLDER.search(meta['zh']):
            raise ValueError('Unbound numeric placeholder in exact display text: ' + english)
    templates.sort(key=lambda v: (-len(normalize(v['en']).replace('{#}', '')), v['en']))
    counts.update(exact_entries=len(entries), numeric_templates=len(templates),
                  reviewed_entries=len(reviewed),
                  ambiguous_exact=sum(len(v) > 1 for v in exact.values()),
                  ambiguous_templates=sum(len(v) > 1 for v in patterns.values()),
                  ambiguous_exact_resolved=sum(len(v) > 1 and en in entries for en,v in exact.items()),
                  ambiguous_templates_resolved=sum(len(v) > 1 and en in reviewed for en,v in patterns.items()))
    report = {'counts': dict(counts), 'rejected': rejected,
              'ambiguous': {en: list(v) for en, v in patterns.items() if len(v) > 1},
              'ambiguous_exact': {en: list(v) for en, v in exact.items() if len(v) > 1}}
    (HERE / 'gem-coverage.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', 'utf8')
    return entries, templates, dict(counts)
