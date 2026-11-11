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
            if kind == 'passive-flavour' and list(map(clean, local_lines)) == list(map(clean, english_lines)):
                add('\n'.join(local_lines), '\n'.join(chinese_lines), kind, node_id)
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
        lines(node.get('flavourText', []), english.get('flavourText', []), chinese.get('flavourText', []), node_id, 'passive-flavour')
        ee = {v['effect']: v for v in english.get('masteryEffects', [])}
        ze = {v['effect']: v for v in chinese.get('masteryEffects', [])}
        for effect in node.get('masteryEffects', []):
            effect_id = effect['effect']
            if effect_id in ee and effect_id in ze:
                lines(effect['stats'], ee[effect_id]['stats'], ze[effect_id]['stats'], node_id, 'mastery-stat')
    reviewed = json.loads((HERE / 'passive-reviewed.json').read_text('utf8'))
    for english, meta in reviewed.items():
        matched = 0
        for node_id, node in pob['nodes'].items():
            texts = [node.get('name', ''), *node.get('stats', []), *node.get('reminderText', [])]
            texts.extend(s for effect in node.get('masteryEffects', []) for s in effect['stats'])
            if english in texts:
                contexts[node_id][english] = meta['zh']
                matched += 1
        if not matched:
            raise ValueError('Reviewed passive no longer exists: ' + english)
        candidates[english] = {meta['zh']: meta}
    misses = [m for m in misses if m.get('english') not in reviewed]
    counts['reviewed_translations'] = len(reviewed)
    entries = {}
    conflicts = []
    for english, options in candidates.items():
        if len(options) == 1:
            entries[english] = next(iter(options.values()))
        else:
            conflicts.append({'english': english, 'translations': list(options)})
    # Class and bloodline dropdowns are tree metadata, not named passive nodes.
    # Match ascendancies by ID and check against the local metadata as well.
    def ascendancies(tree):
        groups = tree.get('alternate_ascendancies', [])[:]
        for group in tree.get('classes', []):
            groups.extend(group.get('ascendancies', []))
        return {v['id']: v for v in groups}
    ea, za, pa = ascendancies(en), ascendancies(cn), ascendancies(pob)
    for class_id in ea.keys() & za.keys() & pa.keys():
        english, chinese, local = ea[class_id], za[class_id], pa[class_id]
        for field in ('name', 'flavourText'):
            if local.get(field) and local[field] == english.get(field) and chinese.get(field):
                for old, new in [(local[field], chinese[field]),
                                 (local[field].replace('\\n','\n'),chinese[field].replace('\\n','\n'))]:
                    entries[old] = {'zh': new, 'kind':'ascendancy-'+field, 'status':'paired-id-local-english-checked',
                        'source':'https://poedb.tw/data/passive-skill-tree/3.29/data_cn.json?5',
                        'english_source':'https://poedb.tw/data/passive-skill-tree/3.29/data_us.json?5'}
    counts['unique_translations'] = len(entries)
    counts['ambiguous_texts_context_only'] = len(conflicts)
    counts['local_nodes'] = len(pob['nodes'])
    for node_id, node in pob['nodes'].items():
        texts = contexts.get(node_id, {})
        if node.get('name'):
            counts['named_nodes_total'] += 1
            counts['named_nodes_translated'] += clean(node['name']) in texts
        for stat in node.get('stats', []):
            counts['stat_lines_total'] += 1
            counts['stat_lines_translated'] += clean(stat) in texts
        for effect in node.get('masteryEffects', []):
            for stat in effect['stats']:
                counts['mastery_lines_total'] += 1
                counts['mastery_lines_translated'] += clean(stat) in texts
    report = {'counts': dict(counts), 'unmatched': misses, 'conflicts': conflicts}
    (HERE / 'passive-coverage.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
    return entries, dict(counts), dict(contexts)
