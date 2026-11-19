"""Pair local cluster passive effects with cached bilingual passive cards."""
from collections import Counter, defaultdict
from pathlib import Path
import gzip
import hashlib
import json
import re
from bs4 import BeautifulSoup
from item_locale import numeric_pair, lua_pattern

HERE = Path(__file__).resolve().parent


def text(element):
    # Keep line boundaries used by the raw tree before PoB splits sd lines.
    for br in element.select('br'):
        br.replace_with('\n')
    return element.get_text().replace('\r', '').strip()


def card(path):
    soup = BeautifulSoup(gzip.decompress(path.read_bytes()), 'html.parser')
    name = text(soup.select_one('.itemName'))
    stats, reminders = [], []
    for element in soup.select('.Stats > .implicitMod'):
        (reminders if element.select_one('.item_description') else stats).append(text(element))
    return name, stats, reminders


def build_clusters():
    source_path = HERE / 'cluster-source.json'
    inventory = json.loads(source_path.read_text('utf8'))
    tree = HERE.parents[1] / 'src/TreeData' / inventory['tree_version'] / 'tree.lua'
    assert hashlib.sha256(tree.read_bytes()).hexdigest() == inventory['tree_sha256'], 'Stale cluster source; export current tree'
    manifest = json.loads((HERE / 'cluster-reference/sources.json').read_text('utf8'))
    assert inventory['tree_version'] == manifest['tree_version'], 'Stale cluster reference version'
    references = {}
    for slug, pair in manifest['sources'].items():
        cards = {}
        for lang in ('us', 'cn'):
            path = HERE / 'cluster-reference' / f'{slug}-{lang}.html.gz'
            assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest() == pair[lang]['sha256'], path
            cards[lang] = card(path)
            assert cards[lang][0] == pair[lang]['name'], 'Cluster card name mismatch: ' + slug
        references[cards['us'][0]] = (slug, cards)
    reviewed = json.loads((HERE / 'cluster-reviewed.json').read_text('utf8'))
    candidates = defaultdict(dict)
    contexts = defaultdict(dict)
    pending = []
    counts = Counter(nodes=len(inventory['nodes']))
    def add(en, zh, node, slug, kind, status='paired-cluster-card-local-english-numbers-checked'):
        if not re.search('[\u4e00-\u9fff]', zh) or not numeric_pair(en, zh):
            pending.append({'node': node['name'], 'english': en, 'chinese': zh, 'reason': 'numbers-or-chinese'})
            return
        meta = dict(zh=zh, kind=kind, status=status, source=f'https://poedb.tw/cn/{slug}',
                    english_source=f'https://poedb.tw/us/{slug}')
        if en in reviewed:
            meta.update(reviewed[en])
        candidates[en][meta['zh']] = meta
        if '\n' in en and en in reviewed:
            fragments = reviewed[en].get('line_translations', [])
            assert len(fragments) == len(en.split('\n')), 'Missing split cluster clauses: ' + en
            for english_line, chinese_line in zip(en.split('\n'), fragments):
                add(english_line, chinese_line, node, slug, kind, 'reviewed-split-cluster-clause')
        contexts[node['id']][en] = meta['zh']
        counts[kind + '_occurrences'] += 1
    for node in inventory['nodes']:
        slug, cards = references[node['name']]
        add(node['name'], cards['cn'][0], node, slug, 'cluster-passive-name')
        for key, index in [('stats', 1), ('reminders', 2)]:
            english, chinese = cards['us'][index], cards['cn'][index]
            for en in node[key]:
                if en in reviewed:
                    add(en, reviewed[en]['zh'], node, slug, 'cluster-passive-' + key, 'direct-translation-numeric-checked')
                elif len(english) == len(chinese) and en in english and english.count(en) == 1:
                    add(en, chinese[english.index(en)], node, slug, 'cluster-passive-' + key)
                else:
                    pending.append({'node': node['name'], 'english': en, 'reason': 'local-clause-or-card-shape-changed'})
    conflicts = {en: list(options) for en, options in candidates.items() if len(options) > 1}
    entries = {en: next(iter(options.values())) for en, options in candidates.items() if len(options) == 1}
    templates = {}
    for en, meta in entries.items():
        paired = numeric_pair(en, meta['zh'])
        e, z, n = paired
        if n:
            templates.setdefault(e, {})[z] = dict(meta, en=e, zh=z, values=n, pattern=lua_pattern(e))
    report = dict(tree_version=inventory['tree_version'], reference_retrieved=manifest['retrieved'],
                  source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                  counts=dict(counts), exact_entries=len(entries), pending=pending, conflicts=conflicts)
    (HERE / 'cluster-coverage.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
    if pending or conflicts:
        raise ValueError(f'{len(pending)} pending cluster clauses, {len(conflicts)} conflicts; see cluster-coverage.json')
    return entries, [next(iter(v.values())) for v in templates.values() if len(v) == 1], dict(contexts), report


if __name__ == '__main__':
    entries, templates, contexts, report = build_clusters()
    print(json.dumps(report['counts']))
