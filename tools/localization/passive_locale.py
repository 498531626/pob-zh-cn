"""Match PoEDB 3.29 text by stable node/effect ID, never by list position alone."""
import collections
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def clean(text):
    text = re.sub(r'\[([^\[\]]+)\]', lambda m: m[1].split('|')[-1], text)
    return html.unescape(re.sub(r'<[^>]+>', '', text)).replace('\r', '').strip()


def build_passives():
    cn = json.loads((HERE / 'poedb-tree-cn.json').read_text('utf8'))
    en = json.loads((HERE / 'poedb-tree-us.json').read_text('utf8'))
    pob = json.loads((HERE / 'pob-tree-en.json').read_text('utf8'))
    candidates = collections.defaultdict(dict)
    counts = collections.Counter()
    contexts = collections.defaultdict(dict)
    misses = []
    def add(english, chinese, kind, node_id):
        english, chinese = clean(english), clean(chinese)
        if not english or not re.search('[\u4e00-\u9fff]', chinese):
            return False
        if kind != 'passive-name' and sorted(re.findall(r'-?\d+(?:\.\d+)?', english)) != sorted(re.findall(r'-?\d+(?:\.\d+)?', chinese)):
            counts['number_mismatch_skipped'] += 1
            return False
        candidates[english][chinese] = {'zh': chinese, 'kind': kind, 'node_id': node_id,
            'source': 'https://poedb.tw/data/passive-skill-tree/3.29/data_cn.json?5',
            'english_source': 'https://poedb.tw/data/passive-skill-tree/3.29/data_us.json?5',
            'status': 'paired-id-english-and-numbers-checked'}
        contexts[node_id][english] = chinese
        counts[kind + '_occurrences'] += 1
        return True
    def lines(local_lines, english_lines, chinese_lines, node_id, kind):
        if len(english_lines) != len(chinese_lines):
            return
        matched = dict(zip(map(clean, english_lines), chinese_lines))
        for line in local_lines:
            text = clean(line)
            if text in matched:
                add(text, matched[text], kind, node_id)
            else:
                misses.append({'node_id': node_id, 'kind': kind, 'english': line})
    for node_id, node in pob['nodes'].items():
        english = en['nodes'].get(node_id)
        chinese = cn['nodes'].get(node_id)
        if not english or not chinese:
            misses.append({'node_id': node_id, 'kind': 'node', 'english': node.get('name')})
            continue
        counts['matched_node_ids'] += 1
        if clean(node.get('name', '')) == clean(english.get('name', '')):
            if add(node.get('name', ''), chinese.get('name', ''), 'passive-name', node_id):
                counts['nodes_with_name'] += 1
        lines(node.get('stats', []), english.get('stats', []), chinese.get('stats', []), node_id, 'passive-stat')
        lines(node.get('reminderText', []), english.get('reminderText', []), chinese.get('reminderText', []), node_id, 'passive-reminder')
        ee = {v['effect']: v for v in english.get('masteryEffects', [])}
        ze = {v['effect']: v for v in chinese.get('masteryEffects', [])}
        for effect in node.get('masteryEffects', []):
            effect_id = effect['effect']
            if effect_id in ee and effect_id in ze:
                lines(effect['stats'], ee[effect_id]['stats'], ze[effect_id]['stats'], node_id, 'mastery-stat')
    entries = {}
    conflicts = []
    for english, options in candidates.items():
        if len(options) == 1:
            entries[english] = next(iter(options.values()))
        else:
            conflicts.append({'english': english, 'translations': list(options)})
    counts['unique_translations'] = len(entries)
    counts['ambiguous_texts_skipped'] = len(conflicts)
    counts['local_nodes'] = len(pob['nodes'])
    report = {'counts': dict(counts), 'unmatched': misses, 'conflicts': conflicts}
    (HERE / 'passive-coverage.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
    return entries, dict(counts), dict(contexts)
