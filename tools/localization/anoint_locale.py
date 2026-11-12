"""Resolve homonymous passive names only among this tree's anoint recipes."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def write_anoint_names(contexts, output):
    tree = json.loads((HERE / 'pob-tree-en.json').read_text('utf8'))
    names = {}
    for node_id, node in tree['nodes'].items():
        if not node.get('recipe'):
            continue
        name = node['name']
        zh = contexts.get(node_id, {}).get(name)
        if not zh:
            raise ValueError('Missing reviewed anoint name: ' + name)
        if name in names and names[name] != zh:
            raise ValueError('Ambiguous anoint name: ' + name)
        names[name] = zh
    quote = lambda s: json.dumps(s, ensure_ascii=False)
    output.write_text('return {\n' + ''.join(
        '[' + quote(en) + ']=' + quote(zh) + ',\n' for en, zh in sorted(names.items())
    ) + '}\n', 'utf8')
    return names
