"""Inventory current Wickerman parts and derive only their actual tier names."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def build_viscera():
    names = json.loads((HERE / 'viscera-names.json').read_text('utf8'))
    bases = set(re.findall(r'itemBases\["(.*?)"\]',
                          (ROOT / 'src/Data/Bases/wickerman.lua').read_text('utf8')))
    assert bases == names.keys(), 'Refresh Wickerman base translations for current data'
    entries = {}
    def add(en, zh):
        entries[en] = {'zh': zh, 'kind': 'viscera-name', 'status': 'literal-translation-pending-reference',
                       'source': 'Data/Viscera.lua; Data/Bases/wickerman.lua; tools/localization/viscera-names.json'}
    for en, zh in names.items():
        add(en, zh)
    for raw in re.findall(r'\[\[(.*?)\]\]', (ROOT / 'src/Data/Viscera.lua').read_text('utf8'), re.S):
        name, base, *_ = raw.strip().splitlines()
        assert base in names, base
        numbered = re.search(r' (\d+)$', name)
        suffix = numbered.group(0) if numbered else ''
        stem = name[:-len(suffix)] if suffix else name
        if stem == base:
            add(name, names[base] + suffix)
        else:
            prefix = next((tier for tier in ('Lesser ', 'Greater ') if stem == tier + base), None)
            assert prefix, 'Unknown viscera tier: ' + name
            add(name, ('低阶' if prefix == 'Lesser ' else '高阶') + names[base] + suffix)
    return entries
